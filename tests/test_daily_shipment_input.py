import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from mta.application.daily_transit import RAW_FIELDS
from mta.presentation import daily_shipment_input as runtime
from parity.temporal_ledger import validate as validate_ledger
from tools import prepare_daily_shipment_input as generator


class DailyShipmentInputTests(unittest.TestCase):
    def test_approved_mdm_amendment_retains_ledger_but_exports_only_three_dates(self):
        root = Path('D:/freshvcf-build/evidence/mdm-approval-day-20261010-001')
        raw = (root / 'mdm-approval-day-input-initial-nms-v1.json').read_bytes()
        source = json.loads(raw)
        supplement, receipt = generator.build_derivative(raw,
            (root / 'mdm-approval-day-reduction-v1.json').read_bytes(),
            generator_sha256='1'*64)
        self.assertEqual(len(source['case']['days']), 12)
        self.assertEqual([d['business_date'] for d in supplement['days']],
                         ['2026-06-06', '2026-06-07', '2026-06-08'])
        self.assertEqual(receipt['ledger_validation'], validate_ledger(source))
        for day in supplement['days']:
            expected = [s for s in source['case']['external_fact_ledger']['shipments']
                        if s['dispatch_date'] <= day['business_date'] < s['receipt_date']]
            actual = day['shipment_input']['rows']
            self.assertEqual([(r['SKUCode'], r['ToLocationCode'], r['OrderNo'], r['InTransitQty'])
                              for r in actual],
                             [(r['SKUCode'], r['WhCode'], r['shipment_id'], r['quantity'])
                              for r in expected])
        runtime.validate_supplement(supplement,
                                   base_artifact_sha256=generator.APPROVAL_SOURCE_SHA256)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source_raw = generator.SOURCE.read_bytes()
        cls.reduction_raw = generator.REDUCTION_RECEIPT.read_bytes()
        cls.source = json.loads(cls.source_raw)
        cls.supplement, cls.receipt = generator.build_derivative(
            cls.source_raw, cls.reduction_raw, generator_sha256="1" * 64
        )

    def test_all_twelve_days_preserve_ledger_occurrences_and_quantities(self):
        shipments = self.source["case"]["external_fact_ledger"]["shipments"]
        masters = {
            (str(row["SKUCode"]), str(row["WhCode"])): row["ParentWhCode"]
            for row in self.source["case"]["static_day"]["raw_master"]
        }
        directory = self.source["case"]["opening"]["consumer_context"][
            "GoodsInTransitTransporterMaster"
        ]
        self.assertEqual(validate_ledger(self.source),
                         self.receipt["ledger_validation"])
        self.assertEqual(len(self.supplement["days"]), 12)
        for source_day, item in zip(self.source["case"]["days"],
                                    self.supplement["days"]):
            business_date = source_day["business_date"]
            expected = [row for row in shipments
                        if row["dispatch_date"] <= business_date < row["receipt_date"]]
            rows = item["shipment_input"]["rows"]
            self.assertEqual([row["OrderNo"] for row in rows],
                             [row["shipment_id"] for row in expected])
            self.assertEqual(sum(row["InTransitQty"] for row in rows),
                             sum(row["quantity"] for row in expected))
            self.assertEqual(sum(row["InTransitQty"] for row in rows),
                             sum(row["GIT"] for row in source_day["raw_daily"]))
            for raw, shipment in zip(rows, expected):
                self.assertEqual(list(raw), list(RAW_FIELDS))
                self.assertEqual(raw["FromLocationCode"], masters[
                    (str(shipment["SKUCode"]), str(shipment["WhCode"]))])
                index = int.from_bytes(hashlib.sha256(
                    shipment["shipment_id"].encode("utf-8")
                ).digest()[:8], "big") % 4
                self.assertEqual(raw["TransporterCode"],
                                 directory[index]["TransporterCode"])
                self.assertIsNone(raw["CurrentLocationCode"])
                self.assertIsNone(raw["Remark"])
                self.assertNotIn("SLT", raw)
                self.assertNotIn("Price", raw)

    def test_runtime_loader_requires_registered_identity_and_exact_date(self):
        encoded = generator.encode_derivative(self.supplement)
        sha = hashlib.sha256(encoded).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "shipment.json"
            path.write_bytes(encoded)
            day = runtime.load_day(
                path, expected_sha256=sha, business_date="2026-06-06",
                base_artifact_sha256=generator.SOURCE_SHA256,
            )
            self.assertEqual(day, self.supplement["days"][0]["shipment_input"])
            with self.assertRaisesRegex(ValueError, "identity differs"):
                runtime.load_day(path, expected_sha256="0" * 64,
                                 business_date="2026-06-06")
            with self.assertRaisesRegex(ValueError, "business date is unavailable"):
                runtime.load_day(path, expected_sha256=sha,
                                 business_date="2026-06-18")

    def test_runtime_validation_rejects_row_or_reconciliation_drift(self):
        payload = json.loads(json.dumps(self.supplement))
        payload["days"][0]["shipment_input"]["rows"][0]["Remark"] = "changed"
        with self.assertRaisesRegex(ValueError, "reconciliation differs"):
            runtime.validate_supplement(
                payload, base_artifact_sha256=generator.SOURCE_SHA256
            )
        payload = json.loads(json.dumps(self.supplement))
        payload["days"][0]["shipment_input"]["rows"][0]["SLT"] = None
        with self.assertRaisesRegex(ValueError, "fields or order differ"):
            runtime.validate_supplement(
                payload, base_artifact_sha256=generator.SOURCE_SHA256
            )

    def test_generation_fails_changed_inputs_and_ambiguous_catalogue(self):
        with self.assertRaisesRegex(ValueError, "artifact identity differs"):
            generator.build_derivative(
                self.source_raw + b" ", self.reduction_raw,
                generator_sha256="1" * 64,
            )
        case = json.loads(self.source_raw)["case"]
        case["static_day"]["raw_master"].append(
            dict(case["static_day"]["raw_master"][0])
        )
        with self.assertRaisesRegex(ValueError, "population differs"):
            generator._catalogue(case)


if __name__ == "__main__":
    unittest.main()
