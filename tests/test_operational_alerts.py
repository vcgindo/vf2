from __future__ import annotations

import unittest

from mta.application.operational_alerts import (
    ALERT_SEEDS,
    SEED_SOURCE_SHA256,
    AlertInputError,
    evaluate_alert,
    seed_settings,
)


class OperationalAlertTests(unittest.TestCase):
    def setUp(self):
        self.settings = seed_settings()
        self.config = {
            "recipient": "Not-Defined",
            "cc_recipient": "support@vectorconsulting.in",
            "profile": "Not-Defined",
            "site": "VECTORFLOW-DEMO",
            "business_date": "2026-06-06",
            "run_datetime": "2026-06-06 12:00AM",
            "auto_dbm_active": "0",
            "distributor_system_active": "0",
            "attach_invalid_data_report_zip": "0",
            "critical_data_available": "1",
            "fnc_match_master_norm": "1",
            "nms_active": "0",
            "dbm_norm_change_report_horizon": 30,
        }

    def evaluate(self, name, populations=None, artifacts=None, config=None, settings=None):
        return evaluate_alert(
            name,
            settings=self.settings if settings is None else settings,
            configuration=self.config if config is None else config,
            populations={} if populations is None else populations,
            artifacts={} if artifacts is None else artifacts,
        )

    def test_exact_seed_roster_order_activation_stage_and_hash(self):
        self.assertEqual(14, len(ALERT_SEEDS))
        self.assertEqual(
            [
                ("NoNormParentAlert", "1", "parent-norm"),
                ("InvalidDataAlert", "1", "input-validation"),
                ("DailyDataUnavailabilityAlert", "1", "fullkit"),
                ("AutoNormAcceptanceAlert", "1", "dbm-core"),
                ("MissingMasterDataForDistributorsAlert", "1", "input-validation"),
                ("LocationInventoryMissingAlert", "0", "input-validation"),
                ("UnapprovedPhaseinPhaseoutAlert", "1", "input-validation"),
                ("FailedForceNormAlert", "1", "norm-controls"),
                ("PhaseInPhaseOutExceptionAlert", "1", "norm-controls"),
                ("RejectedInvoiceAlert", "1", "distributor"),
                ("DBMNormChangeAlert", "0", "dbm-files"),
                ("RunFinishAlert", "0", "run-finish"),
                ("BPRExceptionAlert", "1", "bpr-exception-files"),
                ("DailyDataValidationErrorAlert", "1", "sanitation"),
            ],
            [(row["name"], row["active"], row["stage"]) for row in ALERT_SEEDS],
        )
        self.assertEqual("11c004b7d790bf560549bcad8e3342c3bed15972a63d9e0f26458392edea6309", SEED_SOURCE_SHA256)

    def test_settings_are_exact_and_missing_populations_are_not_empty(self):
        incomplete = dict(self.settings)
        incomplete.pop("InvalidDataAlert")
        with self.assertRaisesRegex(AlertInputError, "exact 14-row roster"):
            self.evaluate("InvalidDataAlert", settings=incomplete)
        with self.assertRaisesRegex(AlertInputError, "missing source population: RejectedMaster"):
            self.evaluate("InvalidDataAlert")

    def test_generic_disabled_operation_branches_do_not_claim_ready(self):
        auto = self.evaluate("AutoNormAcceptanceAlert")
        missing = self.evaluate("MissingMasterDataForDistributorsAlert")
        rejected = self.evaluate("RejectedInvoiceAlert")
        self.assertEqual(("DISABLED_OPERATION", "auto-dbm-disabled"), (auto["status"], auto["reason"]))
        self.assertEqual("DISABLED_OPERATION", missing["status"])
        self.assertEqual("DISABLED_OPERATION", rejected["status"])
        self.assertTrue(all(not row["send_performed"] for row in (auto, missing, rejected)))

    def test_seed_disabled_branches_preserve_exact_source_positions(self):
        expected = {
            "LocationInventoryMissingAlert": "input-validation",
            "DBMNormChangeAlert": "dbm-files",
            "RunFinishAlert": "run-finish",
        }
        for name, stage in expected.items():
            with self.subTest(name=name):
                result = self.evaluate(name)
                self.assertEqual("DISABLED_SETTING", result["status"])
                self.assertEqual(stage, result["stage"])

    def test_not_defined_recipient_suppresses_positive_non_attachment_alert(self):
        result = self.evaluate(
            "UnapprovedPhaseinPhaseoutAlert",
            populations={"PhaseOut": [{"Approved": 0}], "PhaseInNorms": []},
        )
        self.assertEqual("RECIPIENT_SUPPRESSED", result["status"])
        self.assertEqual("unapproved-requests", result["branch"])
        self.assertEqual({"phaseout_count": 1, "phasein_count": 0}, result["values"])
        self.assertIsNone(result["subject"])
        self.assertIsNone(result["body"])

    def test_local_fixture_recipient_can_form_ready_intent_without_send(self):
        config = dict(self.config, recipient="fixture@example.invalid")
        result = self.evaluate(
            "InvalidDataAlert",
            config=config,
            populations={"RejectedMaster": [{"ReasonCode": 2, "RejectionDate": "2026-06-06T00:00:00"}]},
            artifacts={"InvalidDataReport.csv": {"available": True, "members": []}},
        )
        self.assertEqual("READY", result["status"])
        self.assertEqual("invalid-data-present", result["branch"])
        self.assertEqual("InvalidDataReport.csv", result["attachment"]["name"])
        self.assertEqual("VECTORFLOW-DEMO|VectorFLOW : Invalid Data Alert [06 Jun 2026]", result["subject"])
        self.assertEqual(
            "\r\nOne or many of the input files/database tables have invalid data.\r\n"
            "'Invalid Data Report' attached.\r\n\t\t\t\t\t\t\r\n"
            "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support.",
            result["body"],
        )
        self.assertFalse(result["send_performed"])

    def test_no_norm_parent_preserves_native_header_only_size_predicate(self):
        result = self.evaluate(
            "NoNormParentAlert",
            artifacts={
                "NoNormParentReport.csv": {"available": True, "byte_size": 21, "members": []},
                "NoNormParentReport.zip": {"available": True, "members": ["NoNormParentReport.csv"]},
            },
        )
        self.assertEqual("RECIPIENT_SUPPRESSED", result["status"])
        self.assertEqual("file-size-positive", result["branch"])

    def test_daily_unavailability_requires_both_outer_and_sql_predicates(self):
        config = dict(self.config, critical_data_available="0")
        result = self.evaluate(
            "DailyDataUnavailabilityAlert",
            config=config,
            populations={"RunAbortReasons": [{"RunDateTime": "2026-06-06T00:00:00"}]},
            artifacts={"DailyDataUnavailabilityReport.zip": {"available": True, "members": ["DailyDataUnavailabilityReport.csv"]}},
        )
        self.assertEqual("RECIPIENT_SUPPRESSED", result["status"])
        self.assertEqual("critical-data-unavailable", result["branch"])

    def test_force_norm_branch_order_matches_sql(self):
        result = self.evaluate(
            "FailedForceNormAlert",
            populations={
                "ForceNormChange": [{"SKUCode": "S", "WhCode": "W", "NewNorm": 3, "Approved": 0}],
                "FailedForceNormChange": [{"SKUCode": "S"}],
                "DBMMaster": [],
                "MasterDataRaw": [],
            },
        )
        self.assertEqual("force-norm-blocked", result["branch"])
        self.assertEqual("RECIPIENT_SUPPRESSED", result["status"])

    def test_sanitation_clean_requires_explicit_empty_population(self):
        with self.assertRaisesRegex(AlertInputError, "DataSanitizationResult"):
            self.evaluate("DailyDataValidationErrorAlert")
        result = self.evaluate("DailyDataValidationErrorAlert", populations={"DataSanitizationResult": []})
        self.assertEqual("PREDICATE_FALSE", result["status"])
        self.assertEqual("sanitation-clean", result["branch"])

    def test_positive_sanitation_can_never_be_ready(self):
        config = dict(self.config, recipient="fixture@example.invalid")
        result = self.evaluate(
            "DailyDataValidationErrorAlert",
            config=config,
            populations={"DataSanitizationResult": [{"Critical_Flag": "False", "Non_Critical_Flag": "True"}]},
        )
        self.assertEqual("UNAVAILABLE", result["status"])
        self.assertEqual("sanitation-errors", result["branch"])
        self.assertEqual("DailyDataValidationErrorReport.zip", result["attachment"]["name"])
        self.assertEqual("native-attachment-writer-commented-out", result["attachment"]["source_reason"])
        self.assertEqual(
            "VECTORFLOW-DEMO|VectorFLOW : Data Validation error Exceptions Alert [06 Jun 2026]",
            result["subject"],
        )
        self.assertTrue(result["body"].startswith("\r\nDuring the execution"))

    def test_attachment_members_are_exact(self):
        with self.assertRaisesRegex(AlertInputError, "members must be exactly"):
            self.evaluate(
                "PhaseInPhaseOutExceptionAlert",
                populations={"PhaseInPhaseOutExceptionLog": [{"Log_Date": "2026-06-06T00:00:00"}]},
                artifacts={"PhaseInPhaseOutExceptionReport.zip": {"available": True, "members": ["wrong.csv"]}},
            )

    def test_sql_nulls_do_not_match_zero_or_null_join_keys(self):
        result = self.evaluate(
            "UnapprovedPhaseinPhaseoutAlert",
            populations={"PhaseOut": [{"Approved": None}], "PhaseInNorms": []},
        )
        self.assertEqual("PREDICATE_FALSE", result["status"])

        config = dict(self.config, distributor_system_active="1")
        result = self.evaluate(
            "RejectedInvoiceAlert",
            config=config,
            populations={
                "InvoiceDataRaw": [{"SKUCode": None, "WHCode": "W"}],
                "DistributorDBMNorms": [{"SKUCode": None, "WarehouseCode": "W"}],
            },
            artifacts={"RejectedInvoiceList.zip": {"available": True, "members": ["06-RejectedInvoiceList.csv"]}},
        )
        self.assertEqual("rejected-invoices", result["branch"])

    def test_run_finish_reads_source_parameter_value_rows(self):
        settings = dict(self.settings, RunFinishAlert="1")
        config = dict(self.config, recipient="fixture@example.invalid")
        result = self.evaluate(
            "RunFinishAlert",
            settings=settings,
            config=config,
            populations={
                "ImporterSettingsTbl": [
                    {"Parameter": "BatchFileExecutionDate", "Value": "2026-06-06T00:00:00"},
                    {"Parameter": "IsBatchFileExecuted", "Value": "1"},
                ],
                "DailyDataRaw": [{"SKUCode": "S"}],
            },
        )
        self.assertEqual("run-finish", result["branch"])
        self.assertEqual("READY", result["status"])
        self.assertEqual("VECTORFLOW-DEMO|VectorFLOW : Run Finish Alert [06 Jun 2026]", result["subject"])
        self.assertEqual(
            "\r\nVectorFLOW run is over.\r\n\t\t\r\nThis mail is automatically generated.\r\n"
            "\t\t\t\t\t\r\nRegards,\r\nVector Support.",
            result["body"],
        )

    def test_dynamic_force_norm_message_preserves_native_order_and_whitespace(self):
        config = dict(self.config, recipient="fixture@example.invalid")
        result = self.evaluate(
            "FailedForceNormAlert",
            config=config,
            populations={
                "ForceNormChange": [{"SKUCode": "S", "WhCode": "W", "NewNorm": 3, "Approved": 0}],
                "FailedForceNormChange": [{"SKUCode": "S"}],
                "DBMMaster": [],
                "MasterDataRaw": [],
            },
        )
        self.assertEqual("READY", result["status"])
        self.assertEqual("VECTORFLOW-DEMO|VectorFLOW : Force Norm Change Status -06 Jun 2026", result["subject"])
        self.assertEqual(
            "Force norm changes have not been done as\r\n\tThere is no approval from Vector consultant."
            "\r\n\tMaster file/table is invalid.\r\n\r\n\tThis mail is automatically generated."
            "\r\n\t\t\t\t\t\r\n\tRegards,\r\n\tVector Support.",
            result["body"],
        )

    def test_dynamic_phase_approval_message_preserves_native_typo_and_counts(self):
        config = dict(self.config, recipient="fixture@example.invalid")
        result = self.evaluate(
            "UnapprovedPhaseinPhaseoutAlert",
            config=config,
            populations={
                "PhaseOut": [{"Approved": 0}, {"Approved": 0}],
                "PhaseInNorms": [{"Approved": 0}],
            },
        )
        self.assertEqual("READY", result["status"])
        self.assertEqual("VECTORFLOW-DEMO|VectorFLOW : PhaseIn-PhaseOut Approval Status -06 Jun 2026", result["subject"])
        self.assertEqual(
            "\r\nFollowing number of PhaseIn-PhaseOut itesms are waiting for approval. \r\n"
            "PhaseIn-PhaseOut process can not be started without approval.\r\n\t\r\n"
            "Unapproved Phase-Out Item(s) : 2\r\nUnapproved Phase-In Item(s) : 1\r\n\r\n\r\n"
            "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support.",
            result["body"],
        )

    def test_unqualified_subject_sqlcmd_input_fails_closed(self):
        config = dict(self.config, recipient="fixture@example.invalid", site="VECTORFLOW-DEMO'Broken")
        with self.assertRaisesRegex(AlertInputError, "UNQUALIFIED_SCALAR_DOMAIN"):
            self.evaluate(
                "UnapprovedPhaseinPhaseoutAlert",
                config=config,
                populations={"PhaseOut": [{"Approved": 0}], "PhaseInNorms": []},
            )

    def test_all_seeded_alerts_have_source_and_typed_intent_fields(self):
        for seed in ALERT_SEEDS:
            self.assertTrue(seed["wrapper"])
            self.assertTrue(seed["sql"])
            self.assertTrue(seed["branch"])


if __name__ == "__main__":
    unittest.main()
