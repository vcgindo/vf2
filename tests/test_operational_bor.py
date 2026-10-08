from copy import deepcopy
from datetime import date
from decimal import Decimal
import unittest

from mta.application.operational_bor import (
    BOR_COLUMNS, BOR_REPORT_HEADER, NATIVE_SCHEMAS, ORDER_QUALIFICATION, RRR_COLUMNS, SOURCES,
    LegacyBorAmbiguity, collect_bor_order_allocation, collect_bor_order_allocation_history,
    collect_rrr_order_allocation_history, generate_bor_order_allocation,
)


def equal(left, right):
    return str(left).rstrip(" ").casefold() == str(right).rstrip(" ").casefold()


def requirement(**changes):
    row = dict(SKUCode="S", WhCode="W", ParentWhCode="P",
        OrderReqBlack=1, OrderReqRed=2, OrderReqYellow=3, OrderReqGreen=4, OrderReqBlue=5,
        NormReqBlack=0, NormReqRed=0, NormReqYellow=0, NormReqGreen=0,
        OrderBlackBand=2, OrderRedBand=4, OrderYellowBand=4, OrderGreenBand=8)
    row.update(changes)
    return row


def rationed(**changes):
    row = dict(SKUCode="S", WhCode="W", Norm=10, VirtualNorm=12, Stock=3, GIT=2,
               LeftOverParentStock=7, DispatchPen=Decimal("50.00"))
    row.update(changes)
    return row


def bor_row(**changes):
    row = dict(zip(BOR_COLUMNS, (
        "S", "W", "P", 10, 12, 3, 2, 7, 15, 1, 2, 3, 4, 5, 15, 1, 2, 3, 4, 5,
        "Black", Decimal("50.00"), Decimal("50.00"), Decimal("75.00"), Decimal("50.00"),
        Decimal("50.00"))))
    row.update(changes)
    return row


def rrr_row(**changes):
    values = ("S", "W", "P", None, 10, None, 3, 2, None, None, 1, 2, 3, 4, 5,
              None, None, 1, 2, 3, 4, 5, None, 0)
    row = dict(zip(RRR_COLUMNS, values)); row.update(changes); return row


class OperationalBorTests(unittest.TestCase):
    def test_provenance_and_native_schema_are_exact(self):
        self.assertEqual({len(pin) for _, pin in SOURCES.values()}, {64})
        self.assertEqual(tuple(c["name"] for c in NATIVE_SCHEMAS["BORWithOrderAllocation"]), BOR_COLUMNS)
        self.assertEqual(tuple(c["name"] for c in NATIVE_SCHEMAS["RRR_OrderAllocation"]), RRR_COLUMNS)
        self.assertEqual(NATIVE_SCHEMAS["BORWithOrderAllocation"][21]["sql_type"], "decimal(10,2)")
        self.assertFalse(NATIVE_SCHEMAS["RRR_OrderAllocation"][0]["nullable"])
        self.assertTrue(NATIVE_SCHEMAS["RRR_OrderAllocation"][3]["nullable"])

    def test_collect_preserves_join_bags_moq_and_native_updates(self):
        kwargs = dict(
            bpr_master=[dict(SKUCode="S", WHCode="W", ParentWhCode="P")],
            sob_data=[dict(SKUCode="S", WHCode="W", SupplierCode="P", SOB=100.0)],
            moq_data=[dict(SKUCode="S", WHCode="W", SupplierCode="P", MOQ=20)],
            requirements=[requirement()], rationed_report=[rationed(), rationed()],
            bpr_table=[], equal=equal)
        before = deepcopy(kwargs)
        rows = collect_bor_order_allocation(**kwargs)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], rows[1])
        self.assertEqual(tuple(rows[0]), BOR_COLUMNS)
        self.assertEqual((rows[0]["Requirement"], rows[0]["DispatchQty"]), (15, 20))
        self.assertEqual(rows[0]["Dispatch_ToBlue"], 10)
        self.assertEqual(tuple(rows[0][name] for name in (
            "OrderBlackUnsatisfiedPercentage", "OrderRedUnsatisfiedPercentage",
            "OrderYellowUnsatisfiedPercentage", "OrderGreenUnsatisfiedPercentage")),
            (Decimal("50.00"), Decimal("50.00"), Decimal("75.00"), Decimal("50.00")))
        self.assertEqual(kwargs, before)
        self.assertIn("no ORDER BY", ORDER_QUALIFICATION["BORWithOrderAllocation"])

    def test_collect_sob_moq_and_topmost_insertion_order(self):
        rows = collect_bor_order_allocation(
            bpr_master=[dict(SKUCode="A", WHCode="W", ParentWhCode="PA"),
                        dict(SKUCode="B", WHCode="W", ParentWhCode="PB"),
                        dict(SKUCode="C", WHCode="W", ParentWhCode="PC")],
            sob_data=[dict(SKUCode="A", WHCode="W", SupplierCode="PA", SOB=100.0)],
            moq_data=[dict(SKUCode="B", WHCode="W", SupplierCode="PB", MOQ=0)],
            requirements=[requirement(SKUCode=s) for s in "ABC"],
            rationed_report=[rationed(SKUCode=s) for s in "ABC"], bpr_table=[], equal=equal)
        self.assertEqual([(r["SKUCode"], r["SupplierCode"]) for r in rows],
                         [("A", "PA"), ("B", "PB"), ("C", "PC")])

    def test_collect_rejects_different_multi_match_update_winners(self):
        common = dict(bpr_master=[dict(SKUCode="S", WHCode="W", ParentWhCode="P")],
            sob_data=[dict(SKUCode="S", WHCode="W", SupplierCode="P", SOB=100.0)],
            requirements=[requirement()], rationed_report=[rationed()], bpr_table=[], equal=equal)
        with self.assertRaisesRegex(LegacyBorAmbiguity, "MOQ UPDATE"):
            collect_bor_order_allocation(moq_data=[
                dict(SKUCode="S", WHCode="W", SupplierCode="P", MOQ=1),
                dict(SKUCode="S", WHCode="W", SupplierCode="P", MOQ=2)], **common)
        with self.assertRaisesRegex(LegacyBorAmbiguity, "requirement UPDATE"):
            collect_bor_order_allocation(moq_data=[], **{**common,
                "requirements": [requirement(), requirement(OrderReqBlack=2)]})

    def test_generate_returns_header_and_expanded_left_join_rows_in_partial_order(self):
        rows = [bor_row(DispatchPen=Decimal("10.00"), SKUCode="A"),
                bor_row(DispatchPen=Decimal("20.00"), SKUCode="B")]
        result = generate_bor_order_allocation(bor_rows=rows,
            color_sequence=[dict(Color="Black", SequenceNo=1)],
            sku_descriptions=[dict(SKUCode="A", SKUDescription="Alpha"),
                              dict(SKUCode="A", SKUDescription="Alpha duplicate")],
            site_descriptions=[dict(WHCode="W", WHDescription="Warehouse"),
                               dict(WHCode="P", WHDescription="Plant")],
            requirement_rows=[dict(SKUCode="A", WhCode="W", AdvAllocDone=4)],
            is_mto_environment=0, equal=equal)
        self.assertEqual(result["header_resultset"], [BOR_REPORT_HEADER])
        self.assertEqual([r[0] for r in result["data_resultset"]], ["B", "A", "A"])
        self.assertEqual(result["data_resultset"][1][1], '"Alpha"')
        self.assertIsNone(result["data_resultset"][0][-1])
        self.assertIn("ties retain source-bag order", result["order_qualification"])

    def test_generate_mto_uses_all_declared_sort_keys(self):
        result = generate_bor_order_allocation(
            bor_rows=[bor_row(SKUCode="A", OrderBlackUnsatisfiedPercentage=Decimal("10.00")),
                      bor_row(SKUCode="B", OrderBlackUnsatisfiedPercentage=Decimal("20.00"))],
            color_sequence=[dict(Color="Black", SequenceNo=1)], sku_descriptions=[],
            site_descriptions=[], requirement_rows=[], is_mto_environment=1, equal=equal)
        self.assertEqual([r[0] for r in result["data_resultset"]], ["B", "A"])

    def test_bor_history_delete_boundaries_append_duplicates_and_replace_today(self):
        opening = [dict(bor_row(SKUCode="old"), ReportDate="2026-03-08"),
                   dict(bor_row(SKUCode="keep"), ReportDate="2026-03-09"),
                   dict(bor_row(SKUCode="today-old"), ReportDate="2026-06-06")]
        current = [bor_row(SKUCode="today"), bor_row(SKUCode="today")]
        result = collect_bor_order_allocation_history(opening_history=opening, current_bor=current,
                                                       business_date="2026-06-06", horizon=90)
        self.assertEqual([r["SKUCode"] for r in result], ["keep", "today", "today"])
        self.assertTrue(all(r["ReportDate"] <= date(2026, 6, 6).isoformat() for r in result))

    def test_rrr_history_runs_with_explicit_empty_or_supplied_current(self):
        self.assertEqual(collect_rrr_order_allocation_history(opening_history=[], current_rrr=[],
            business_date="2026-06-06", horizon=90), [])
        result = collect_rrr_order_allocation_history(opening_history=[],
            current_rrr=[rrr_row(), rrr_row()], business_date="2026-06-07", horizon=90)
        self.assertEqual(len(result), 2)
        self.assertEqual([r["ReportDate"] for r in result], ["2026-06-07"] * 2)

    def test_no_population_or_horizon_defaults(self):
        with self.assertRaises(TypeError):
            collect_rrr_order_allocation_history(opening_history=[], current_rrr=[], business_date="2026-06-06")
        with self.assertRaisesRegex(ValueError, "typed source projection"):
            collect_bor_order_allocation(bpr_master=[], sob_data=[], moq_data=[], requirements=[],
                rationed_report=[], bpr_table=[{"SKUCode": "S"}], equal=equal)


if __name__ == "__main__":
    unittest.main()
