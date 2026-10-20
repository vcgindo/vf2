"""Legacy boundary regressions; no database, daily runner or service changes."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal as D
import unittest

from mta.domain.dbm_daily_cleanup import daily_cleanup
from mta.domain.dbm_norm012 import data_stage, AmbiguousReport
from mta.domain.r1_current_day import PsoRationInput, allocate_spike_pso
from mta.domain.rrr import RationChild, allocate_rrr
from mta.domain.remaining_capabilities import calculate_pick_cases_state


class SignedPsoStockTests(unittest.TestCase):
    def row(self, stock, demand=0):
        return PsoRationInput("S", "C", "P", D(demand), D(demand),
                             D(0), D(0), D(0), stock, D(5))

    def test_negative_adjusted_parent_allocates_zero_and_keeps_signed_leftover(self):
        for demand in (0, 10):
            source = (self.row(D(-7), demand),)
            before = deepcopy(source)
            result, = allocate_spike_pso(source)
            self.assertEqual(result.proportional_allocation, D(-7) if demand else 0)
            self.assertEqual((result.pack_allocation, result.last_casepack_allocation,
                              result.total_allocation, result.parent_leftover), (0, 0, 0, -7))
            self.assertEqual(source, before)

    def test_negative_parent_is_not_permission_for_negative_or_invalid_demand(self):
        from dataclasses import replace
        for value in (D("-0.1"), D("NaN"), D("Infinity"), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                allocate_spike_pso((self.row(value, 10),))
        for field in ("residual_spike_pso", "spike_pso_to_net_off", "norm_requirement",
                      "total_requirement", "normal_rationed_quantity", "parent_pack_size"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                allocate_spike_pso((replace(self.row(D(-7)), **{field: D(-1)}),))

    def test_zero_and_positive_stock_keep_allocation(self):
        for stock, allocated, leftover in ((0, 0, 0), (7, 5, 2), (10, 10, 0)):
            result, = allocate_spike_pso((self.row(D(stock), 10),))
            self.assertEqual((result.total_allocation, result.parent_leftover), (allocated, leftover))


class CleanupHorizonTests(unittest.TestCase):
    def test_configured_cutoff_keeps_duplicates_order_nulls_and_input(self):
        today = date(2026, 4, 8)
        for horizon in (0, 1, 30, 365, 370, -1):
            cutoff = today - timedelta(days=horizon)
            state = {"LastBatchRunTbl": [{"LastRunDate": "2026-04-08T00:00:00"}],
                     "DailyConsumption": [
                         {"ReportDate": cutoff.isoformat(), "tag": "delete"},
                         {"ReportDate": None, "tag": "null"},
                         {"ReportDate": (cutoff + timedelta(days=1)).isoformat(), "tag": "keep"},
                         {"ReportDate": (cutoff + timedelta(days=1)).isoformat(), "tag": "keep"},
                         {"ReportDate": cutoff - timedelta(days=1), "tag": "delete"}]}
            before = deepcopy(state)
            result = daily_cleanup(today, state, horizon)
            self.assertEqual([r["tag"] for r in result["DailyConsumption"]], ["null", "keep", "keep"])
            self.assertEqual(state, before)

    def test_invalid_horizon_and_ambiguous_date_fail(self):
        state = {"LastBatchRunTbl": [{"LastRunDate": "2026-04-08T00:00:00"}],
                 "DailyConsumption": []}
        for horizon in (True, "365", None, 1.5, -(2**31), 2**31, 2**31-1):
            with self.subTest(horizon=horizon), self.assertRaises(ValueError):
                daily_cleanup("2026-04-08", state, horizon)
        state["LastBatchRunTbl"] *= 2
        with self.assertRaisesRegex(ValueError, "singleton"):
            daily_cleanup("2026-04-08", state, 365)


class NormNullAggregationTests(unittest.TestCase):
    def state(self, norm, values):
        return {"LastBatchRunTbl": [{"LastRunDate": "2026-04-08T00:00:00"}],
                "DBMMaster": [{"SKUCode": "S", "WhCode": "C", "Norm": norm}],
                "SKUDescriptionTbl": [{"SKUCode": "S", "SKUDescription": "item"}],
                "DailyConsumption": [
                    {"SKUCode": "S", "WhCode": "C", "Consumption": v, "ReportDate": "2026-04-08"}
                    for v in values], "IntermediateTables": []}

    def test_mixed_null_group_keeps_sum_count_duplicate_fragments(self):
        for norm in (0, 1, 2):
            state = self.state(norm, [None, 2, 2, 0, -1])
            before = deepcopy(state)
            row, = data_stage("2026-04-08", state, norm, 30)["Norm0Norm1Norm2Report"]
            self.assertEqual((row["Count"], row["TotalSale"], row["Occurances"]),
                             (2, 3, "[08/04/26 - 2], [08/04/26 - 2]"))
            self.assertEqual(state, before)

    def test_all_null_preserves_target_not_null_failure(self):
        for norm in (0, 1, 2):
            with self.subTest(norm=norm), self.assertRaisesRegex(ValueError, "TotalSale"):
                data_stage("2026-04-08", self.state(norm, [None, None]), norm, 30)

    def test_null_date_excluded_and_no_observations_produces_no_row(self):
        state = self.state(0, [None])
        state["DailyConsumption"][0]["ReportDate"] = None
        self.assertEqual(data_stage("2026-04-08", state, 0, 30)["Norm0Norm1Norm2Report"], [])

    def test_no_occurrence_order_waiver_or_integer_overflow(self):
        with self.assertRaises(AmbiguousReport):
            data_stage("2026-04-08", self.state(0, [None, 1, 2]), 0, 30)
        with self.assertRaisesRegex(ValueError, "signed32"):
            data_stage("2026-04-08", self.state(0, [None, 2**30, 2**30]), 0, 30)


class ConditionalLegacyRiskTests(unittest.TestCase):
    def test_rrr_approved_location_tie_break_for_scarce_last_pack(self):
        children = tuple(RationChild("S", loc, "P", D(10), D(0), D(0), 1) for loc in ("A", "B"))
        for order in (children, children[::-1]):
            result = allocate_rrr(parent_stock=D(5), parent_pack_size=D(5), children=order)
            self.assertEqual({r.location_code: r.final_quantity for r in result}, {"A": 5, "B": 0})
            for stock, expected in ((0, (0, 0)), (10, (5, 5)), (20, (10, 10))):
                result = allocate_rrr(parent_stock=D(stock), parent_pack_size=D(5), children=order)
                self.assertEqual(tuple(r.final_quantity for r in result), expected)

    def case(self, volume, qty=1):
        return {"vehicle": {"name": "V", "weight_capacity": 100, "volume_capacity": 100},
                "items": [{"case": "one", "sku": "S", "from_location": "P", "to_location": "C",
                           "logistics_location": "C", "dispatch_color": "Black",
                           "weight": 1, "volume": volume, "buckets": {"to_black": qty}}]}

    def test_pick_approved_weight_only_underfilled_and_exact_fit_preserve_null(self):
        result = calculate_pick_cases_state([self.case(None)], allow_priority_ties=True)
        self.assertEqual(result["LogisticPickList"], [])
        self.assertIsNone(result["PickListDataForTruckFormation"][0]["RemainingVolume"])
        case = self.case(None, 100)
        before = deepcopy(case)
        result = calculate_pick_cases_state([case], allow_priority_ties=True)
        row, = result["LogisticPickList"]
        self.assertIsNone(row["TotalVolume"])
        self.assertEqual(row["ColorWiseAlloction"], 100)
        self.assertEqual(row["TransportLoadType"], "WEIGHT_ONLY")
        self.assertEqual(case, before)

    def test_pick_null_exclusion_and_mixed_partition_preserve_prefix_semantics(self):
        empty = calculate_pick_cases_state([self.case(None, 0)], allow_priority_ties=True)
        self.assertEqual(empty["LogisticPickList"], [])
        case = self.case(None)
        other = deepcopy(case["items"][0])
        other.update(case="two", sku="T", volume=1)
        case["items"].append(other)
        for items in (case["items"], case["items"][::-1]):
            result = calculate_pick_cases_state([{**case, "items": items}], allow_priority_ties=True)
            self.assertEqual(len(result["PickListDataForTruckFormation"]), 2)
            self.assertTrue(all(r["NoTruckFlag"] for r in result["PickListDataForTruckFormation"]))
            self.assertTrue(all(r["RemainingVolume"] is None for r in result["PickListDataForTruckFormation"]))
