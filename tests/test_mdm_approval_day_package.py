import tempfile
from pathlib import Path
import unittest

from mta.serialization import digest
from parity.temporal_ledger import validate
from tools.prepare_mdm_approval_day import (
    ARTIFACT_NAME,
    CATALOGUE,
    DECISION,
    D0_PHASE_REQUEST,
    D0_SEASON_REQUEST,
    MANIFEST_NAME,
    PARENT_LOCATIONS,
    PROPOSED_EXECUTION_DATES,
    REQUEST_MAP,
    SOURCE,
    SUPPLIER_REFERENCE,
    TARGET_LOCATIONS,
    TARGET_PAIRS,
    TARGET_SKUS,
    build_package,
    prepare,
)


class MdmApprovalDayPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_raw = SOURCE.read_bytes()
        cls.catalogue_raw = CATALOGUE.read_bytes()
        cls.supplier_raw = SUPPLIER_REFERENCE.read_bytes()
        cls.request_raw = REQUEST_MAP.read_bytes()
        cls.decision_raw = DECISION.read_bytes()
        (
            cls.artifact,
            cls.receipt,
            cls.hierarchy,
            cls.workflow_requests,
        ) = build_package(
            cls.source_raw,
            cls.catalogue_raw,
            cls.supplier_raw,
            cls.request_raw,
            cls.decision_raw,
        )

    def test_exact_pair_order_horizon_and_physical_closure(self):
        case = self.artifact["case"]
        raw_master = case["static_day"]["raw_master"]
        pairs = [(str(row["SKUCode"]), str(row["WhCode"])) for row in raw_master]
        self.assertEqual(pairs, list(TARGET_PAIRS))
        self.assertEqual(case["opening_date"], "2026-06-05")
        dates = [day["business_date"] for day in case["days"]]
        self.assertEqual(dates[:3], list(PROPOSED_EXECUTION_DATES))
        self.assertEqual(len(dates), 12)
        parents = {
            str(row["ParentWhCode"])
            for row in raw_master
            if (str(row["SKUCode"]), str(row["ParentWhCode"])) not in set(TARGET_PAIRS)
        }
        self.assertEqual(parents, set(PARENT_LOCATIONS))
        self.assertEqual(
            {
                sku: {
                    str(row["ParentWhCode"])
                    for row in raw_master
                    if str(row["SKUCode"]) == sku
                    and str(row["WhCode"]) in {"LDC001", "LDC002", "LDC006"}
                }
                for sku in TARGET_SKUS
            },
            {"337": {"PL002"}, "6120": {"PL001"}},
        )
        self.assertEqual(validate(self.artifact), self.receipt["ledger_validation"])

    def test_flags_and_only_the_approved_d0_bootstrap_are_present(self):
        case = self.artifact["case"]
        self.assertEqual(
            case["profile"]["force_flags"],
            {"from_ui": True, "ignore_master_norm": True, "nms_active": True},
        )
        for rows in (
            case["opening"]["importer_settings"],
            case["opening"]["controls"]["importer_settings"],
        ):
            values = {row["Parameter"]: row["Value"] for row in rows}
            self.assertEqual(values["NMSActive"], "1")
            self.assertEqual(values["PI_PO_UploadApproved"], "0")
            self.assertEqual(values["NMSMOQInputDataFormat"], "WithoutDestLoc")
            self.assertEqual(values["ActivateNMSUIUploadLogs"], "1")
        for rows in (
            case["opening"]["controls"]["dbm_settings"],
            case["opening"]["dbm"]["DBMSettingsTbl"],
        ):
            values = {row["Parameter"]: row["Value"] for row in rows}
            self.assertEqual(values["FNC_MatchMasterNorm"], "0")
        self.assertEqual(case["commands"], [])
        day0 = case["days"][0]
        self.assertEqual(day0["control_requests"]["phase_requests"], [D0_PHASE_REQUEST])
        self.assertEqual(day0["control_requests"]["season_requests"], [D0_SEASON_REQUEST])
        self.assertEqual(day0["control_requests"]["phase_in_requests"], [])
        self.assertEqual(day0["control_requests"]["phase_stops"], [])
        self.assertEqual(day0["new_force_requests"], [])
        self.assertEqual(day0["order_feed"], [])
        for day in case["days"][1:]:
            self.assertTrue(all(not rows for rows in day["control_requests"].values()))
            self.assertEqual(day["new_force_requests"], [])
            self.assertEqual(day["order_feed"], [])
        order_classification = self.receipt["classifications"]["case/days/*/order_feed"]
        self.assertEqual(order_classification["strategy"], "exact-pair")
        self.assertEqual(order_classification["source_rows"], 4)
        self.assertEqual(order_classification["derived_rows"], 0)
        self.assertEqual(
            self.receipt["classifications"]["case/days/*/new_force_requests"]["strategy"],
            "exact-pair-assert-empty-approved-bootstrap",
        )

    def test_supplier_is_exact_registered_6120_only_reference(self):
        case = self.artifact["case"]
        raw = case["static_day"]["supplier_feeds"]
        opening = case["opening"]["supplier"]
        self.assertEqual(
            raw["MOQDataRaw1"],
            [{
                "MOQ": 10,
                "SKUCode": "6120",
                "SupplierCode": "PL001",
                "SupplierDescription": "Plant Jakarta & Karawang",
            }],
        )
        self.assertEqual(raw["MOQDataRaw2"], [])
        self.assertEqual([row["WHCode"] for row in raw["SOBDataRaw"]], [
            "LDC001", "LDC002", "LDC006",
        ])
        self.assertEqual([row["SOB"] for row in raw["SOBDataRaw"]], [100, 100, 100])
        for population in (
            raw["MOQDataRaw1"], raw["SOBDataRaw"],
            opening["MOQData"], opening["SOBData"],
        ):
            self.assertFalse(any(str(row["SKUCode"]) == "337" for row in population))

    def test_hierarchy_and_workflow_sidecars_are_bounded(self):
        self.assertEqual([row["code"] for row in self.hierarchy["products"]], list(TARGET_SKUS))
        self.assertEqual(
            {row["code"] for row in self.hierarchy["locations"]},
            set(TARGET_LOCATIONS) | set(PARENT_LOCATIONS),
        )
        for row in self.hierarchy["products"] + self.hierarchy["locations"]:
            self.assertEqual(set(row), {"code", "level_1", "level_2", "level_3"})
        self.assertEqual(len(self.workflow_requests["families"]), 13)
        self.assertFalse(self.workflow_requests["boundary"]["engine_day_feed"])
        self.assertEqual(self.workflow_requests["boundary"]["new_days_authorized"], 0)
        self.assertFalse(self.workflow_requests["boundary"]["registration_authorized"])
        self.assertFalse(self.workflow_requests["boundary"]["runtime_mutation_authorized"])
        self.assertEqual(
            digest(self.workflow_requests),
            self.artifact["derivative_provenance"]["post_d0_request_plan_digest"],
        )

    def test_authority_identity_and_exclusive_output_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "source identity differs"):
            build_package(
                self.source_raw + b" ",
                self.catalogue_raw,
                self.supplier_raw,
                self.request_raw,
                self.decision_raw,
            )
        with tempfile.TemporaryDirectory() as parent:
            destination = Path(parent) / "package"
            result = prepare(
                destination, SOURCE, CATALOGUE, SUPPLIER_REFERENCE, REQUEST_MAP, DECISION
            )
            self.assertTrue((destination / ARTIFACT_NAME).is_file())
            self.assertTrue((destination / MANIFEST_NAME).is_file())
            self.assertEqual(result["output_dir"], str(destination))
            with self.assertRaises(FileExistsError):
                prepare(
                    destination, SOURCE, CATALOGUE, SUPPLIER_REFERENCE,
                    REQUEST_MAP, DECISION,
                )


if __name__ == "__main__":
    unittest.main()
