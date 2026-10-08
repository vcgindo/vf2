from copy import deepcopy
import unittest

from mta.application.operational_norm_reports import (
    DBM_HEADER, HISTORY_HEADER, NATIVE_FORMATTER_REQUIREMENTS, NORM_HEADER,
    REPORT_BINDINGS, REQUIRED_CONFIGURATION, SOURCES, norm_report_resultsets,
)


def stage(name, header, rows):
    return {"stage": name, "tables": {
        "ReportHeader": [{"values": list(header)}],
        "ReportRows": [{"values": list(row)} for row in rows],
    }}


def reports(dbm_rows=(), history_rows=(), norm1_rows=(), norm2_rows=()):
    return [
        stage("norm-change-export", DBM_HEADER, dbm_rows),
        stage("norm-change-history", HISTORY_HEADER, history_rows),
        stage("norm1-export", NORM_HEADER, norm1_rows),
        stage("norm2-export", NORM_HEADER, norm2_rows),
        {"stage": "controls", "tables": {}},
    ]


class OperationalNormReportTests(unittest.TestCase):
    def test_source_pins_bind_four_generic_outputs_and_explicit_profile(self):
        self.assertEqual({len(pin) for _, pin in SOURCES.values()}, {64})
        self.assertEqual([(row[0], row[1], row[3]) for row in REPORT_BINDINGS], [
            ("DBMNormChange", "norm-change-export", 1),
            ("NormChangeLog", "norm-change-history", 7),
            ("Norm1_30days", "norm1-export", 30),
            ("Norm2_30days", "norm2-export", 30),
        ])
        self.assertEqual(REQUIRED_CONFIGURATION["ActivateNorm0Report30Days"], 0)
        self.assertEqual(REQUIRED_CONFIGURATION["ActivateNorm1Report30Days"], 1)
        self.assertEqual(REQUIRED_CONFIGURATION["ActivateNorm2Report30Days"], 1)

    def test_nonempty_typed_cells_nulls_and_duplicates_are_preserved(self):
        dbm = ["S", "W", 2, 1, "2026-06-06", None]
        history_new = ["S", None, "W", None, 1, 2, "2026-06-06", None]
        history_old = ["S", "Name", "W", "Site", 0, 1, "2026-06-05", "Reason"]
        norm = ["S", '"Name"', "W", '"Site"', "P", "1", "2", "3", '"[01/06/26 - 3]"']
        source = reports([dbm, dbm], [history_new, history_old], [norm, norm], [norm])
        before = deepcopy(source)
        result = norm_report_resultsets(reports=source, configuration=REQUIRED_CONFIGURATION.copy())
        self.assertEqual([cell["value"] for cell in result["DBMNormChange"]["data_result_set"][0]], dbm)
        self.assertEqual(len(result["DBMNormChange"]["data_result_set"]), 2)
        self.assertIsNone(result["NormChangeLog"]["data_result_set"][0][1]["value"])
        self.assertEqual(len(result["Norm1_30days"]["data_result_set"]), 2)
        self.assertEqual(source, before)

    def test_empty_reports_still_require_and_return_exact_headers(self):
        result = norm_report_resultsets(reports=reports(), configuration=REQUIRED_CONFIGURATION.copy())
        for name, _, _, _, header, _ in REPORT_BINDINGS:
            self.assertEqual(tuple(cell["value"] for cell in result[name]["header_result_set"]), header)
            self.assertEqual(result[name]["data_result_set"], ())
        self.assertIn("SQL Server/sqlcmd", NATIVE_FORMATTER_REQUIREMENTS["bytes"])

    def test_missing_or_duplicate_required_source_fails(self):
        missing = reports()[:-2] + reports()[-1:]
        with self.assertRaisesRegex(ValueError, "exactly once"):
            norm_report_resultsets(reports=missing, configuration=REQUIRED_CONFIGURATION.copy())
        duplicate = reports() + [stage("norm1-export", NORM_HEADER, [])]
        with self.assertRaisesRegex(ValueError, "exactly once"):
            norm_report_resultsets(reports=duplicate, configuration=REQUIRED_CONFIGURATION.copy())

    def test_retained_norm0_stage_is_ignored_while_norm0_file_activation_is_rejected(self):
        source = reports() + [stage("norm0-export", NORM_HEADER, [["retained"] * 9])]
        before = deepcopy(source)
        result = norm_report_resultsets(reports=source, configuration=REQUIRED_CONFIGURATION.copy())
        self.assertEqual(set(result), {"DBMNormChange", "NormChangeLog",
                                       "Norm1_30days", "Norm2_30days"})
        self.assertEqual(source, before)
        enabled = REQUIRED_CONFIGURATION.copy(); enabled["ActivateNorm0Report30Days"] = 1
        with self.assertRaisesRegex(ValueError, "source identity"):
            norm_report_resultsets(reports=source, configuration=enabled)

    def test_horizon_source_identity_and_full_native_shape_are_enforced(self):
        wrong = REQUIRED_CONFIGURATION.copy(); wrong["NormChangeLogHorizon"] = 8
        with self.assertRaisesRegex(ValueError, "source identity"):
            norm_report_resultsets(reports=reports(), configuration=wrong)
        malformed = reports(); malformed[0]["tables"].pop("ReportRows")
        with self.assertRaisesRegex(ValueError, "source absent"):
            norm_report_resultsets(reports=malformed, configuration=REQUIRED_CONFIGURATION.copy())
        bad_type = reports(dbm_rows=[["S", "W", True, 1, "2026-06-06", None]])
        with self.assertRaisesRegex(ValueError, "Native int"):
            norm_report_resultsets(reports=bad_type, configuration=REQUIRED_CONFIGURATION.copy())
        bad_width = reports(norm1_rows=[["S"] * 8])
        with self.assertRaisesRegex(ValueError, "width differs"):
            norm_report_resultsets(reports=bad_width, configuration=REQUIRED_CONFIGURATION.copy())

    def test_history_requires_owned_date_descending_order_without_resorting(self):
        ascending = reports(history_rows=[
            ["S", None, "W", None, 1, 2, "2026-06-05", None],
            ["S", None, "W", None, 2, 3, "2026-06-06", None],
        ])
        with self.assertRaisesRegex(ValueError, "date-descending"):
            norm_report_resultsets(reports=ascending, configuration=REQUIRED_CONFIGURATION.copy())


if __name__ == "__main__":
    unittest.main()
