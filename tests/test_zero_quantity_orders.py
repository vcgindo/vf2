"""Zero accepted quantities follow ImportSpikeOrders/CalculateReq SQL semantics.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import unittest

from mta.domain.demand import (
    AcceptedOrder, ThresholdPolicy, classify_spike, collect_orders,
)
from mta.planning.engine import calculate_current_day

TODAY = date(2026, 4, 8)
FIXTURES = Path(__file__).resolve().parents[1] / "mta/fixtures"


def fixture(name):
    return json.loads((FIXTURES / (name + ".json")).read_text())


class ZeroQuantityOrderTests(unittest.TestCase):
    def test_zero_is_not_new_spike_even_with_zero_norm_and_threshold(self):
        self.assertFalse(classify_spike(
            Decimal(0), Decimal(0), ThresholdPolicy(*([Decimal(0)] * 4))))

    def test_zero_orders_contribute_zero_but_retain_due_spike_identity(self):
        rows = (
            AcceptedOrder("pso", "SKU", "LOC", Decimal(0), TODAY, TODAY, False),
            AcceptedOrder("due", "SKU", "LOC", Decimal(0), TODAY, TODAY, True),
            AcceptedOrder("future", "SKU", "LOC", Decimal(0), TODAY, date(2026, 4, 9), True),
        )
        value = collect_orders(rows, "SKU", "LOC", TODAY)
        self.assertEqual((value.pso, value.due_spike, value.future_spike), (0, 0, 0))
        self.assertEqual(value.due_order_ids, ("due",))

    def test_invalid_quantities_still_rejected_at_both_seams(self):
        for quantity in (Decimal(-1), Decimal("0.5"), Decimal("1e14"), Decimal("NaN")):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    classify_spike(quantity, Decimal(0), ThresholdPolicy(*([Decimal(0)] * 4)))
                with self.assertRaises(ValueError):
                    collect_orders((AcceptedOrder(
                        "id", "SKU", "LOC", quantity, TODAY, TODAY, False),),
                        "SKU", "LOC", TODAY)

    def test_zero_does_not_bypass_duplicate_identity_or_closure_checks(self):
        row = AcceptedOrder("id", "SKU", "LOC", Decimal(0), TODAY, TODAY, False)
        with self.assertRaisesRegex(ValueError, "Duplicate accepted order"):
            collect_orders((row, row), "SKU", "LOC", TODAY)
        with self.assertRaisesRegex(ValueError, "outside SKU-location closure"):
            collect_orders((row,), "SKU", "OTHER", TODAY)

    def test_new_zero_pso_retains_generated_identity_through_full_flow(self):
        value = fixture("r1_order_new_nonspike")
        value["order_input"]["feed_rows"][0]["Qty"] = 0
        output = calculate_current_day(value)
        tables = {r["table"]: r["rows"] for r in output["r1_order_import_state"]}
        self.assertEqual(len(tables["orders"]), 1)
        row = tables["orders"][0]
        self.assertEqual((row["OrderKey"], row["Qty"], row["OriginalQty"], row["IsSpike"]), (92, 0, 0, 0))
        self.assertEqual(row["CustomerOrderId"], "R1-NEW-PSO")
        self.assertEqual(tables["new_spikes"], [])
        self.assertIn("r1_pick_list", output)
        self.assertIn("r1_bor", output)

    def test_empty_feed_retains_zero_pso_without_fabricating_closure(self):
        value = fixture("r1_order_empty_pso")
        value["order_input"]["opening_orders"][0]["Qty"] = 0
        original = deepcopy(value["order_input"]["opening_orders"])
        output = calculate_current_day(value)
        tables = {r["table"]: r["rows"] for r in output["r1_order_import_state"]}
        self.assertEqual(tables["orders"], original)
        self.assertEqual(tables["closure_history"], [])
        self.assertEqual(tables["new_spikes"], [])

    def test_zero_amendment_retains_spike_and_multipart_history(self):
        for name in ("r1_order_amendment", "r1_order_parts"):
            with self.subTest(fixture=name):
                value = fixture(name)
                value["order_input"]["feed_rows"][0]["Qty"] = 0
                expected = deepcopy(value["order_input"]["opening_orders"])
                for row in expected:
                    row["Qty"] = 0
                output = calculate_current_day(value)
                tables = {r["table"]: r["rows"] for r in output["r1_order_import_state"]}
                self.assertEqual(tables["orders"], expected)
                self.assertEqual(tables["closure_history"], [])
                self.assertEqual(tables["new_spikes"], [])
                self.assertIn("r1_pick_remaining", output)
                self.assertIn("r1_bor_oa", output)
