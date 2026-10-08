from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import unittest

from mta.application.operational_upload_logs import (
    ACTION_SCHEMA, LOG_BINDINGS, NATIVE_FORMATTER_REQUIREMENTS, NATIVE_SCHEMAS,
    SCHEMA_SHA256, SOURCES, clear_ui_upload_log_history, export_ui_upload_log,
)


def value(column):
    kind = column["type"]
    if kind in ("varchar", "nvarchar", "char", "nchar", "xml"):
        return "X"
    if kind in ("int", "bigint", "smallint", "tinyint"):
        return 1
    if kind == "bit":
        return True
    if kind in ("decimal", "numeric"):
        scale = int(column["parameters"].split(",")[1])
        return Decimal(1).quantize(Decimal(1).scaleb(-scale))
    if kind in ("float", "real"):
        return 1.5
    if kind == "date":
        return "2026-06-06"
    if kind in ("datetime", "datetime2"):
        return "2026-06-06T12:00:00"
    raise AssertionError(kind)


def row(table_name, **changes):
    result = {column["name"]: value(column) for column in NATIVE_SCHEMAS[table_name]}
    result.update(ActionId=1, ActionTimeStamp="2026-06-06T12:00:00")
    result.update(changes)
    return result


def action(**changes):
    result = {"ActionId": 1, "ActionDesc": "Request uploaded"}
    result.update(changes)
    return result


class OperationalUploadLogTests(unittest.TestCase):
    def test_physical_null_token_is_ordinary_native_log_text(self):
        table = 'UIUploadLogNMSSKUs'
        source = row(table, SKUCode='\\N')
        result = export_ui_upload_log(table_name=table, rows=[source], action_types=[action()])
        position = result['data_columns'].index('SKUCode')
        self.assertEqual(result['data_result_set'][0][position]['value'], '\\N')

    def test_all_eight_bindings_and_schemas_are_exact(self):
        self.assertEqual(LOG_BINDINGS, (
            ("UIUploadLogNMSNewItem", "NMSAddNewSKULocLog"),
            ("UIUploadLogNMSModifyItem", "NMSModifySKULocLog"),
            ("UIUploadLogNMSRemoveItem", "NMSRemoveSKULocLog"),
            ("UIUploadLogNMSLocations", "NMSLocMasterLog"),
            ("UIUploadLogNMSSKUs", "NMSSKUMasterLog"),
            ("UIUploadLogNMSSOB", "NMSSOBMasterLog"),
            ("UIUploadLogNMSMOQ", "NMSMOQMasterLog"),
            ("UIUploadLogFNC", "ForceNormChangeUploadLog"),
        ))
        self.assertEqual(len(NATIVE_SCHEMAS), 8)
        self.assertEqual(tuple(column["name"] for column in ACTION_SCHEMA),
                         ("ActionId", "ActionDesc"))
        self.assertEqual(len(SCHEMA_SHA256), 64)
        self.assertEqual({len(pin) for _, pin in SOURCES.values()}, {64})
        for table_name, report_name in LOG_BINDINGS:
            result = export_ui_upload_log(table_name=table_name, rows=[row(table_name)],
                                          action_types=[action()])
            expected = tuple(column["name"] for column in NATIVE_SCHEMAS[table_name]
                             if column["name"] != "ActionId") + ("Action",)
            self.assertEqual(result["report_name"], report_name)
            self.assertEqual(result["data_columns"], expected)
            self.assertEqual(result["header_result_set"][0][0]["value"], ",".join(expected))
            self.assertEqual(len(result["data_result_set"]), 1)
            empty = export_ui_upload_log(table_name=table_name, rows=[], action_types=[])
            self.assertEqual(empty["data_result_set"], ())

    def test_export_null_empty_and_native_conversion_cells(self):
        source = row("UIUploadLogNMSMOQ", WhCode=None, MOQ=None, SupplierCode="")
        result = export_ui_upload_log(table_name="UIUploadLogNMSMOQ",
                                      rows=[source], action_types=[action()])
        cells = result["data_result_set"][0]
        self.assertEqual([cell["value"] for cell in cells[:4]], ["X", "-", "-", "-"])
        self.assertIsInstance(cells[-2]["value"], datetime)
        self.assertEqual(cells[-1]["value"], "Request uploaded")
        numeric = export_ui_upload_log(table_name="UIUploadLogNMSMOQ",
            rows=[row("UIUploadLogNMSMOQ", MOQ=7)], action_types=[action()])
        self.assertEqual(numeric["data_result_set"][0][3]["native_conversion"],
                         "CONVERT(nvarchar(256), source_value)")
        self.assertIn("no Python byte spelling", NATIVE_FORMATTER_REQUIREMENTS["bytes"])

    def test_action_inner_join_preserves_duplicates_and_unmatched_rows_vanish(self):
        source = row("UIUploadLogNMSRemoveItem")
        before = deepcopy(source)
        result = export_ui_upload_log(table_name="UIUploadLogNMSRemoveItem", rows=[source],
            action_types=[action(ActionDesc="first"), action(ActionDesc="second"),
                          action(ActionId=2, ActionDesc="other")])
        self.assertEqual([cells[-1]["value"] for cells in result["data_result_set"]],
                         ["first", "second"])
        self.assertEqual(source, before)
        unmatched = export_ui_upload_log(table_name="UIUploadLogNMSRemoveItem",
                                         rows=[source], action_types=[])
        self.assertEqual(unmatched["data_result_set"], ())

    def test_seven_day_retention_uses_date_and_inclusive_delete_boundary(self):
        rows = [row("UIUploadLogNMSRemoveItem", SKUCode="old",
                    ActionTimeStamp="2026-06-02T23:59:59"),
                row("UIUploadLogNMSRemoveItem", SKUCode="edge",
                    ActionTimeStamp="2026-06-03T00:00:00"),
                row("UIUploadLogNMSRemoveItem", SKUCode="future",
                    ActionTimeStamp="2026-06-11T00:00:00")]
        before = deepcopy(rows)
        kept = clear_ui_upload_log_history(table_name="UIUploadLogNMSRemoveItem",
            rows=rows, today="2026-06-10", history_horizon=7)
        self.assertEqual([item["SKUCode"] for item in kept], ["edge", "future"])
        self.assertEqual(rows, before)

    def test_complete_inputs_and_native_types_are_required(self):
        with self.assertRaisesRegex(ValueError, "fields differ"):
            export_ui_upload_log(table_name="UIUploadLogFNC", rows=[{"SKUCode": "S"}],
                                 action_types=[])
        with self.assertRaisesRegex(ValueError, "NULL in required"):
            export_ui_upload_log(table_name="UIUploadLogFNC",
                rows=[row("UIUploadLogFNC", RequestedBy=None)], action_types=[])
        with self.assertRaisesRegex(ValueError, "explicit row list"):
            export_ui_upload_log(table_name="UIUploadLogFNC", rows=None, action_types=[])
        with self.assertRaisesRegex(ValueError, "Unknown canonical"):
            export_ui_upload_log(table_name="Other", rows=[], action_types=[])
        with self.assertRaisesRegex(ValueError, "Horizon"):
            clear_ui_upload_log_history(table_name="UIUploadLogFNC", rows=[],
                                        today="2026-06-10", history_horizon=None)


if __name__ == "__main__":
    unittest.main()
