"""Approved lower-Norm/location ranking and explicitly qualified weight-only Pick.

Focused components only: no execute_day, database, build or serving operation.
"""
from collections import defaultdict
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
from itertools import permutations
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mta.domain.rrr import RationChild, allocate_rrr
from mta.application.complete_daily_pick import calculate_native_pick
from mta.application.complete_daily_batch_files import (
    PICK_NAMES, reports_from_pick_state, sqlcmd_bytes, write_run_pick_files)
from mta.serialization import storage
from tests.test_pick_vehicle_options import source


class ApprovedRationRankingTests(unittest.TestCase):
    def child(self, location, norm=10, stock=0, rlt=1, priority=1):
        return RationChild("S", location, "P", D(norm), D(stock), D(0), rlt, priority)

    def winner(self, children):
        before = deepcopy(children)
        rows = allocate_rrr(parent_stock=D(5), parent_pack_size=D(5), children=children)
        self.assertEqual(children, before)
        self.assertEqual(sum(row.final_quantity for row in rows), 5)
        self.assertTrue(all(row.final_quantity % 5 == 0 for row in rows))
        return next(row.location_code for row in rows if row.residual_allocation)

    def test_lower_norm_wins_equal_penetration_before_location(self):
        for children in permutations((self.child("Z", 10), self.child("A", 20))):
            self.assertEqual(self.winner(children), "Z")

    def test_penetration_still_precedes_lower_norm(self):
        for children in permutations((self.child("A", 10, stock=1), self.child("Z", 20))):
            self.assertEqual(self.winner(children), "Z")

    def test_rlt_and_priority_still_precede_final_location(self):
        for children in (
            (self.child("A", rlt=2), self.child("Z", rlt=1)),
            (self.child("A", priority=2), self.child("Z", priority=1)),
        ):
            for ordered in permutations(children):
                self.assertEqual(self.winner(ordered), "Z")

    def test_final_location_tie_is_independent_of_input_order(self):
        for children in permutations(tuple(self.child(loc) for loc in ("Z", "B", "A"))):
            self.assertEqual(self.winner(children), "A")

    def test_virtual_child_exclusion_and_duplicate_guard_unchanged(self):
        children = (replace(self.child("A"), virtual=True), self.child("Z"))
        self.assertEqual(self.winner(children), "Z")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.winner((self.child("A"), self.child("A")))


class ApprovedWeightOnlyPickTests(unittest.TestCase):
    def raw(self, qty=7, capacities=(3, 4)):
        raw = source(qty, capacities)
        raw["sku_attributes"][0]["Volume"] = None
        return raw

    def verify_conservation(self, raw, state):
        totals = defaultdict(int)
        for table in ("LogisticPickList", "PickListDataForTruckFormation"):
            for row in state[table]:
                self.assertGreaterEqual(row["ColorWiseAlloction"], 0)
                totals[row["VehicleName"], row["SKUCode"]] += row["ColorWiseAlloction"]
        for vehicle in raw["vehicles"]:
            for row in raw["pick_rows"]:
                self.assertEqual(totals[vehicle["VehicleName"], row["SKUCode"]], row["RationedReq"])
        trucks = defaultdict(D)
        capacities = {}
        for row in state["LogisticPickList"]:
            key = (row["VehicleName"], row["TruckCount"], row["ParentWHCode"], row["LogisticLocation"])
            trucks[key] += row["TotalWeight"]
            capacities[key] = row["VehicleWeightCapacity"]
            self.assertEqual(row["TransportLoadType"], "WEIGHT_ONLY")
            self.assertIsNone(row["CumulativeVolume"])
        for key, weight in trucks.items():
            self.assertLessEqual(weight, capacities[key])

    def test_underfill_exact_fit_overflow_and_multiple_vehicles(self):
        for qty in (1, 3, 7, 13):
            raw = self.raw(qty)
            before = deepcopy(raw)
            state = calculate_native_pick(**raw)
            self.verify_conservation(raw, state)
            self.assertEqual(raw, before)
            self.assertTrue(all(row["TotalVolume"] is None for row in state["LogisticPickList"]))
            self.assertTrue(all(row["RemainingVolume"] is None
                                for row in state["PickListDataForTruckFormation"]))

    def mixed(self):
        raw = self.raw(7, (3,))
        raw["pick_rows"].append(dict(raw["pick_rows"][0], SKUCode="B", RationedReq=2,
                                    TOR_B=0, TOR_R=2))
        # Deliberately large known volume: the entire incomplete queue uses
        # weight only, rather than treating the partial volume SUM as complete.
        raw["sku_attributes"].append(dict(SKUCode="B", Weight="1.000", Volume="500.000"))
        return raw

    def test_mixed_queue_conserves_both_items_and_keeps_known_dimensions(self):
        raw = self.mixed()
        state = calculate_native_pick(**raw)
        self.verify_conservation(raw, state)
        b_rows = [row for row in state["LogisticPickList"] if row["SKUCode"] == "B"]
        self.assertTrue(b_rows)
        self.assertTrue(all(row["TotalVolume"] == row["ColorWiseAlloction"] * 500 for row in b_rows))

    def test_warning_survives_typed_wire_roundtrip_and_all_four_file_writes(self):
        raw = self.mixed()
        raw["pick_rows"][1].update(RationedReq=3, TOR_R=3)  # also retain partial queue
        state = calculate_native_pick(**raw)
        persisted = storage(state)
        before = deepcopy(persisted)
        reports = reports_from_pick_state(persisted)
        self.assertEqual(reports, reports_from_pick_state(state))
        for report in reports.values():
            header, body = report["resultsets"]
            self.assertEqual(header["rows"][0][-1], "Capacity Validation")
            self.assertTrue(body["rows"])
            for values in body["rows"]:
                self.assertIn("WEIGHT_ONLY: VOLUME UNVERIFIED", values[-1])
                for i, name in enumerate(body["fields"]):
                    if name in ("TotalVolume", "TotalRemVolume", "RemainingTotalVol"):
                        self.assertIsNone(values[i])
        with TemporaryDirectory() as folder:
            run = "00000000-0000-0000-0000-000000000123"
            write_run_pick_files(run, persisted, folder)
            for kind, name in PICK_NAMES.items():
                for subdir in ("output", "download"):
                    self.assertEqual((Path(folder)/run/subdir/name).read_bytes(),
                                     sqlcmd_bytes(reports[kind]["resultsets"]))
            # Regeneration uses saved rows only; no recalculation is needed.
            write_run_pick_files(run, persisted, folder)
        self.assertEqual(persisted, before)

    def test_underfilled_only_queue_has_visible_warning(self):
        state = calculate_native_pick(**self.raw(1, (3,)))
        reports = reports_from_pick_state(storage(state))
        for kind in ("remaining_summary", "remaining_details"):
            self.assertIn("VOLUME UNVERIFIED", reports[kind]["resultsets"][1]["rows"][0][-1])

    def test_historical_null_volume_without_policy_marker_is_not_relabelled(self):
        state = calculate_native_pick(**self.raw(1, (3,)))
        # Older successful mixed-prefix results used zero RemainingVolume.
        # Regenerating them must not assert that today's fallback was executed.
        state["PickListDataForTruckFormation"][0]["RemainingVolume"] = D("0.000")
        reports = reports_from_pick_state(storage(state))
        self.assertTrue(all("CapacityValidation" not in r["resultsets"][1]["fields"]
                            for r in reports.values()))

    def test_identical_attribute_occurrences_keep_multiplicity_without_negative_growth(self):
        raw = self.raw(7, (3,))
        raw["sku_attributes"].append(dict(raw["sku_attributes"][0]))
        before = deepcopy(raw)
        state = calculate_native_pick(**raw)
        self.assertEqual(raw, before)
        rows = state["LogisticPickList"] + state["PickListDataForTruckFormation"]
        self.assertEqual(sum(r["ColorWiseAlloction"] for r in rows), 14)
        self.assertTrue(all(r["ColorWiseAlloction"] >= 0 for r in rows))
        effective_weights = defaultdict(D)
        for row in state["LogisticPickList"]:
            effective_weights[row["TruckCount"]] += row["TotalWeight"] * 2
        self.assertTrue(effective_weights)
        self.assertTrue(all(weight <= 3 for weight in effective_weights.values()))

    def test_missing_weight_zero_weight_and_overweight_unit_do_not_gain_a_default(self):
        for weight in (None, "0.000", "-1.000", "NaN", "4.000"):
            raw = self.raw(7, (3,))
            if weight is None:
                # The source join excludes both-NULL rows; a mixed queue with
                # a volume-only member must fail, not pretend its weight is zero.
                raw = self.mixed()
                raw["sku_attributes"][1]["Weight"] = None
            else:
                raw["sku_attributes"][0]["Weight"] = weight
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                calculate_native_pick(**raw)

    def test_complete_volume_queue_and_files_stay_unchanged_when_other_queue_falls_back(self):
        known = source(7, (3,))
        expected = calculate_native_pick(**known)
        raw = deepcopy(known)
        raw["pick_rows"].append(dict(raw["pick_rows"][0], SKUCode="B", WhCode="OTHER"))
        raw["sku_attributes"].append(dict(SKUCode="B", Weight="1.000", Volume=None))
        raw["location_attributes"].append(dict(WHCode="OTHER", LogisticsLocation="OTHER"))
        actual = calculate_native_pick(**raw)
        for table in ("LogisticPickList", "PickListDataForTruckFormation"):
            self.assertEqual([r for r in actual[table] if r["SKUCode"] == "A"], expected[table])
        reports = reports_from_pick_state(expected)
        self.assertTrue(all("CapacityValidation" not in r["resultsets"][1]["fields"]
                            for r in reports.values()))
        self.assertTrue(all(row["TransportLoadType"] != "WEIGHT_ONLY"
                            for row in expected["LogisticPickList"]))


if __name__ == "__main__":
    unittest.main()
