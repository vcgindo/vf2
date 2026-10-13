"""Focused source-contract proofs for the native AllocatedOrders producer."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import unittest

from mta.application.production_order_allocation import (
    INPUT_TABLE_FIELDS, OUTPUT_FIELDS, allocated_orders,
)


TODAY = date(2026, 6, 17)


def order(key=1, qty=5, wh="C", due=TODAY):
    return dict(SKUCode="A", WhCode=wh, OrderKey=key, DueDate=due, Qty=qty,
                CustomerOrderId=f"O{key}", IsSpike=1, CustomerExpectedDate=None)


def daily(wh, stock=0, git=0):
    return dict(SKUCode="A", WHCode=wh, Stock=stock, GIT=git, ReportDate=TODAY)


def master(wh, norm=10, rlt=1):
    return dict(SKUCode="A", WHCode=wh, Norm=norm, RLT=rlt)


def band(wh, parent="P", **changes):
    value = dict(SKUCode="A", WhCode=wh, ParentWhCode=parent, Norm=10, RelCNR=0, RelPSO=0,
                OrderBlackBand=10, ResidualChildrenSnP=0)
    value.update(changes)
    return value


def colour(key, dest, source, value="Black", bpp=100):
    return dict(SKUCode="A", DestWhCode=dest, SrcWhCode=source, OrderKey=key,
                DueDate=TODAY, BPP=bpp, OrderColor=value)


def route(key, dest, source):
    return dict(OrderKey=key, DestWhCode=dest, SrcWhCode=source, DueDate=TODAY)


def daily_route(key, dest, source, qty, kind):
    return dict(OrderKey=key, DestWhCode=dest, SrcWhCode=source, DueDate=TODAY,
                Qty=qty, Type=kind)


def inputs(**changes):
    value = dict(business_date=TODAY, daily_consumption=[], stock_calculation=[],
                 spike_orders=[], route_original=[], route_daily=[], requirement_bands=[],
                 order_colours=[], dbm_master=[], sku_loc_attributes=[])
    value.update(changes)
    return value


class ProductionOrderAllocationTests(unittest.TestCase):
    def test_declares_exact_connector_tables_and_native_output(self):
        self.assertEqual(tuple(INPUT_TABLE_FIELDS), (
            "DailyConsumption", "Vf_StockCalculation", "SpikeOrderData",
            "SpikeOrderRouteOriginal", "SpikeOrderRouteDaily",
            "RequirementInColorBand", "OrderRequirementColor", "DBMMaster",
            "SkuLocAttributeData"))
        self.assertEqual(OUTPUT_FIELDS[-5:], ("OrderWiseAllocatedQty", "BPP", "OrderColor",
                                              "DueDateAtDest", "PackSizeWiseAllocatedQty"))

    def test_final_rows_normalize_source_bit_dates_and_decimal_to_native_ddl(self):
        source_order = order()
        source_order["IsSpike"] = True
        rows = allocated_orders(**inputs(
            daily_consumption=[daily("C", stock=5)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=5)],
            spike_orders=[source_order], route_original=[route(1, "C", "C")],
            order_colours=[colour(1, "C", "C", value="Red", bpp=Decimal("33.1"))],
        ))
        self.assertEqual(tuple(rows[0]), OUTPUT_FIELDS)
        self.assertIs(type(rows[0]["IsSpike"]), int)
        self.assertEqual(rows[0]["IsSpike"], 1)
        self.assertEqual((rows[0]["DueDate"], rows[0]["DueDateAtDest"]),
                         (TODAY.isoformat(), TODAY.isoformat()))
        self.assertEqual(rows[0]["BPP"], Decimal("33.10"))

    def test_self_node_partial_allocation_retains_full_qty_stock_defect(self):
        rows = allocated_orders(**inputs(
            daily_consumption=[daily("C", stock=5)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=5)],
            spike_orders=[order(qty=8)],
        ))
        self.assertEqual(len(rows), 1)
        self.assertEqual(tuple(rows[0]), OUTPUT_FIELDS)
        # Native row keeps original Qty while allocating only the available five.
        self.assertEqual((rows[0]["DestWhCode"], rows[0]["SrcWhCode"], rows[0]["Qty"],
                          rows[0]["OrderWiseAllocatedQty"], rows[0]["PackSizeWiseAllocatedQty"],
                          rows[0]["BPP"], rows[0]["OrderColor"]),
                         ("C", "C", 8, 5, 5, Decimal("100.00"), "Black"))
        # A routed child proves the source's SUM(Qty), not SUM(allocation),
        # deduction: StockForRationing starts at ten, then falls to two (10-8),
        # so only two units remain for the child instead of five (10-5).
        two = allocated_orders(**inputs(
            daily_consumption=[daily("C", stock=5), daily("D")],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=10),
                               dict(SKUCode="A", WHCode="D", StockForRationing=0)],
            spike_orders=[order(1, 8), order(2, 5, wh="D")],
            route_original=[route(2, "D", "C")], requirement_bands=[band("D")],
            order_colours=[colour(2, "D", "C")], dbm_master=[master("D")],
            sku_loc_attributes=[dict(SKUCode="A", LocCode="C", PackSize=1)],
        ))
        self.assertEqual([(row["OrderKey"], row["OrderWiseAllocatedQty"]) for row in two],
                         [(1, 5), (2, 2)])

    def test_parent_stock_allocation_retains_integer_division_pack_defect(self):
        rows = allocated_orders(**inputs(
            daily_consumption=[daily("C"), daily("P", stock=20)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=0),
                               dict(SKUCode="A", WHCode="P", StockForRationing=20)],
            spike_orders=[order(qty=12)], route_original=[route(1, "C", "P")],
            requirement_bands=[band("C")], order_colours=[colour(1, "C", "P")],
            dbm_master=[master("C")],
            sku_loc_attributes=[dict(SKUCode="A", LocCode="P", PackSize=10)],
        ))
        self.assertEqual(len(rows), 1)
        # Canonical CEILING(int / int) produces one ten-unit pack, not twenty.
        self.assertEqual((rows[0]["DestWhCode"], rows[0]["SrcWhCode"], rows[0]["Qty"],
                          rows[0]["OrderWiseAllocatedQty"], rows[0]["PackSizeWiseAllocatedQty"]),
                         ("C", "P", 12, 10, 10))
        self.assertEqual((rows[0]["BPP"], rows[0]["OrderColor"], rows[0]["DueDateAtDest"]),
                         (Decimal("100.00"), "Black", None))

    def test_git_route_is_netted_and_marks_matching_allocation_white(self):
        rows = allocated_orders(**inputs(
            daily_consumption=[daily("C", stock=5, git=3)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=5)],
            spike_orders=[order(qty=5)], route_original=[route(1, "C", "C")],
            route_daily=[daily_route(1, None, "C", 3, "GIT")],
            order_colours=[colour(1, "C", "C", value="Black")],
        ))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["OrderWiseAllocatedQty"], rows[0]["OrderColor"]), (5, "White"))

    def test_advance_stock_is_added_to_existing_and_standalone_orders(self):
        existing = allocated_orders(**inputs(
            daily_consumption=[daily("C", stock=3)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=3)],
            spike_orders=[order(qty=5)], route_original=[route(1, "C", "C")],
            route_daily=[daily_route(1, None, "C", 2, "adv-stock")],
            order_colours=[colour(1, "C", "C")],
        ))
        self.assertEqual((existing[0]["Qty"], existing[0]["OrderWiseAllocatedQty"],
                          existing[0]["PackSizeWiseAllocatedQty"], existing[0]["OrderColor"]),
                         (7, 3, 3, "White"))
        standalone = allocated_orders(**inputs(
            daily_consumption=[daily("C")],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=0)],
            spike_orders=[order(qty=5)],
            route_daily=[daily_route(1, None, "C", 2, "adv-stock")],
        ))
        self.assertEqual((standalone[0]["Qty"], standalone[0]["OrderWiseAllocatedQty"],
                          standalone[0]["PackSizeWiseAllocatedQty"]), (5, 2, 2))

    def test_join_multiplicity_is_retained_but_undefined_updates_are_denied(self):
        with self.assertRaisesRegex(ValueError, "differing UPDATE winners"):
            allocated_orders(**inputs(
                daily_consumption=[daily("C", stock=5)],
                stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=5),
                                   dict(SKUCode="A", WHCode="C", StockForRationing=6)],
                spike_orders=[order()],
            ))
        bag = allocated_orders(**inputs(
            daily_consumption=[daily("C"), daily("P", stock=20)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=0),
                               dict(SKUCode="A", WHCode="P", StockForRationing=20)],
            spike_orders=[order(qty=12)], route_original=[route(1, "C", "P")],
            requirement_bands=[band("C")], order_colours=[colour(1, "C", "P")],
            dbm_master=[master("C")],
            sku_loc_attributes=[dict(SKUCode="A", LocCode="P", PackSize=5),
                                dict(SKUCode="A", LocCode="P", PackSize=10)],
        ))
        self.assertEqual([(row["OrderWiseAllocatedQty"], row["PackSizeWiseAllocatedQty"])
                          for row in bag], [(10, 10), (10, 10)])
        # The same bag on the inter-node UPDATE path produces different
        # quantities (10 and 6), so the source has no defined winner.
        ambiguous = inputs(
            daily_consumption=[daily("C", stock=20), daily("P", stock=20)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=20),
                               dict(SKUCode="A", WHCode="P", StockForRationing=20)],
            spike_orders=[order(qty=13, wh="X")], route_original=[route(1, "C", "P")],
            requirement_bands=[band("C", Norm=20, OrderBlackBand=13)],
            order_colours=[colour(1, "C", "P")], dbm_master=[master("C", norm=20)],
            sku_loc_attributes=[dict(SKUCode="A", LocCode="P", PackSize=5),
                                dict(SKUCode="A", LocCode="P", PackSize=6)],
        )
        with self.assertRaisesRegex(ValueError, "InterNode stock allocation.*differing"):
            allocated_orders(**ambiguous)

    def test_residual_rows_use_band_parent_retain_duplicates_and_null_source_ced_defect(self):
        source_order = order(qty=6, wh="X")
        source_order["CustomerExpectedDate"] = date(2026, 6, 20)
        residual_colour = colour(1, "IGNORED-DEST", "C")
        rows = allocated_orders(**inputs(
            daily_consumption=[daily("C"), daily("P", stock=10)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=0),
                               dict(SKUCode="A", WHCode="P", StockForRationing=10)],
            spike_orders=[source_order], requirement_bands=[band("C", parent="P", ResidualChildrenSnP=5)],
            order_colours=[residual_colour, deepcopy(residual_colour)],
            dbm_master=[master("C", rlt=0)],
            sku_loc_attributes=[dict(SKUCode="A", LocCode="P", PackSize=5)],
        ))
        self.assertEqual([(row["DestWhCode"], row["SrcWhCode"], row["OrderWiseAllocatedQty"])
                          for row in rows], [("C", "P", 5), ("C", "P", 5)])
        second = order(2, qty=5, wh="X")
        ced_order = order(1, qty=5, wh="X")
        ced_order["CustomerExpectedDate"] = date(2026, 6, 20)
        ordered = allocated_orders(**inputs(
            daily_consumption=[daily("C"), daily("P", stock=5)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=0),
                               dict(SKUCode="A", WHCode="P", StockForRationing=5)],
            spike_orders=[ced_order, second],
            requirement_bands=[band("C", parent="P", ResidualChildrenSnP=5)],
            order_colours=[colour(1, "IGNORED", "C"), colour(2, "IGNORED", "C")],
            dbm_master=[master("C", rlt=0)],
            sku_loc_attributes=[dict(SKUCode="A", LocCode="P", PackSize=1)],
        ))
        # The residual INSERT reads CustomerExpectedDate from the unmatched
        # eligible alias, so both are NULL and OrderKey 1 wins the five units.
        self.assertEqual([row["OrderKey"] for row in ordered], [1])

    def test_git_without_requirement_colour_does_not_force_white(self):
        rows = allocated_orders(**inputs(
            daily_consumption=[daily("C", stock=5, git=3)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=5)],
            spike_orders=[order(qty=5)], route_original=[route(1, "C", "C")],
            route_daily=[daily_route(1, None, "C", 3, "GIT")],
        ))
        self.assertEqual(rows[0]["OrderColor"], "Black")

    def test_nullable_order_due_date_is_filtered_by_sql_predicate(self):
        nullable = order()
        nullable["DueDate"] = None
        rows = allocated_orders(**inputs(
            daily_consumption=[daily("C", stock=5)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=5)],
            spike_orders=[nullable],
        ))
        self.assertEqual(rows, [])

    def test_missing_fields_inputs_are_not_mutated_and_not_null_source_is_enforced(self):
        malformed = daily("C"); del malformed["GIT"]
        with self.assertRaisesRegex(ValueError, "lacks canonical fields"):
            allocated_orders(**inputs(daily_consumption=[malformed]))
        source = inputs(
            daily_consumption=[daily("C", stock=5)],
            stock_calculation=[dict(SKUCode="A", WHCode="C", StockForRationing=5)],
            spike_orders=[order()],
            route_daily=[daily_route(1, None, "C", 2, "adv-stock")],
        )
        before = deepcopy(source)
        rows = allocated_orders(**source)
        self.assertEqual(source, before)
        self.assertEqual(rows[0]["OrderWiseAllocatedQty"], 5)
        denied = deepcopy(source)
        denied["route_daily"][0]["SrcWhCode"] = None
        with self.assertRaisesRegex(ValueError, "SrcWhCode is NOT NULL"):
            allocated_orders(**denied)


if __name__ == "__main__":
    unittest.main()
