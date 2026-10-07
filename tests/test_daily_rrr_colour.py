"""Bounded connector cases for the pure pinned Norm RRR colour producer."""
import unittest

from mta.presentation.daily_rrr_colour import (
    APPROVED_SMOKE_RUN_IDS, OUTPUT_FIELDS, SOURCE_SQL_SHA256,
    norm_rrr_colour_rows,
)


class DailyRrrColourTests(unittest.TestCase):
    def context(self, **changes):
        value = dict(run_id=next(iter(APPROVED_SMOKE_RUN_IDS)), instance_port=3006,
                     synthetic=True, is_mto_environment=0,
                     order_capabilities_complete=True)
        value.update(changes)
        return value

    def report(self, **changes):
        value = dict(SKUCode="A", WhCode="L", ParentWhCode="P", Req=100,
                     Norm=90, VirtualNorm=90, Stock=10, GIT=0,
                     LeftoverParentStock=7, NormReq=80,
                     AllocatedForVirtualNormReq=65, ParentPackSize=10,
                     DispatchColor="Red")
        value.update(changes)
        return value

    def band(self, **changes):
        value = dict(sku_code="A", location_code="L", parent_location_code="P",
                     norm_req_black=20, norm_req_red=20, norm_req_yellow=20,
                     norm_req_green=20, order_req_black=0, order_req_red=0,
                     order_req_yellow=0, order_req_green=0, order_req_blue=0)
        value.update(changes)
        return value

    def produce(self, reports=None, bands=None, masters=None, advances=None,
                capabilities=None, context=None):
        return norm_rrr_colour_rows(
            rationed_report=reports if reports is not None else [self.report()],
            requirement_bands=bands if bands is not None else [self.band()],
            bpr_master=masters if masters is not None else [{"SKUCode": "A", "WHCode": "P"}],
            advance_stock_allocations=advances if advances is not None else [],
            order_capabilities=capabilities if capabilities is not None else {
                "r1_order_route": [], "r1_order_bpp": [], "AllocatedOrders": []},
            context=context if context is not None else self.context())

    def test_exact_norm_formula_and_complete_native_shape(self):
        row = self.produce(advances=[
            dict(sku_code="A", source_location_code="L", allocated_quantity="3",
                 allocation_type="advance-stock"),
            dict(sku_code="A", source_location_code="L", allocated_quantity=2,
                 allocation_type="advance-stock"),
        ])[0]
        self.assertEqual(tuple(row), OUTPUT_FIELDS)
        self.assertEqual(SOURCE_SQL_SHA256,
                         "4f034a2fab598d87683d5ab0457cf6af49460de67dbf42ad856a1dc3cdd26e7b")
        # TOR=20, TOY=30, TOG=15 and Blue=0 for allocated quantity 65.
        self.assertEqual((row["TOBlack_AllocQty"], row["TOR_AllocQty"],
                          row["TOY_AllocQty"], row["TOGreen_AllocQty"],
                          row["TOBlue_AllocQty"]), (0, 20, 30, 15, 0))
        self.assertEqual(row["RationedCasePacks"], 6)
        self.assertEqual(row["AdvAllocDone"], 5)
        self.assertEqual(row["DispatchColor"], "Black")
        self.assertEqual(row["Requirement"], 80)

    def test_black_allocation_virtual_norm_one_and_negative_bands(self):
        black = self.produce(reports=[self.report(VirtualNorm=1, Stock=0, GIT=0,
                                                   AllocatedForVirtualNormReq=5,
                                                   ParentPackSize=2)])[0]
        self.assertEqual((black["TOBlack_AllocQty"], black["TOR_AllocQty"],
                          black["TOY_AllocQty"], black["TOGreen_AllocQty"],
                          black["TOBlue_AllocQty"]), (5, 0, 0, 0, 0))
        clamped = self.produce(reports=[self.report(VirtualNorm=90, Stock=0, GIT=0,
                                                     AllocatedForVirtualNormReq=10)])[0]
        self.assertEqual((clamped["TOY_AllocQty"], clamped["TOGreen_AllocQty"]), (0, 0))
        self.assertEqual(clamped["TOBlue_AllocQty"], 0)

    def test_join_multiplicity_and_union_duplicate_elimination(self):
        # Two BPR parent occurrences and two identical band occurrences create
        # multiplicity in every CTE, but UNION collapses identical final rows.
        row = self.report()
        rows = self.produce(reports=[row], bands=[self.band(), self.band()],
                            masters=[{"SKUCode": "A", "WHCode": "P"}] * 2)
        self.assertEqual(len(rows), 1)
        unequal = self.produce(bands=[self.band(), self.band(norm_req_black=21)])
        self.assertEqual(len(unequal), 2)
        self.assertEqual({r["Requirement"] for r in unequal}, {80, 81})

    def test_sql_null_and_population_filters(self):
        self.assertEqual(self.produce(reports=[self.report(Req=None)]), [])
        self.assertEqual(self.produce(reports=[self.report(Req=0)]), [])
        self.assertEqual(self.produce(reports=[self.report(WhCode="P")]), [])
        self.assertEqual(self.produce(bands=[self.band(norm_req_black=None)]), [])
        self.assertEqual(self.produce(masters=[]), [])
        with self.assertRaisesRegex(ValueError, "divide by zero"):
            self.produce(reports=[self.report(ParentPackSize=0)])

    def test_order_and_smoke_boundaries_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "outside the approved"):
            self.produce(context=self.context(run_id="not-approved"))
        with self.assertRaisesRegex(ValueError, "complete order capability"):
            self.produce(context=self.context(order_capabilities_complete=False))
        with self.assertRaisesRegex(ValueError, "non-empty order inputs"):
            self.produce(capabilities={"r1_order_route": [], "r1_order_bpp": [],
                                       "AllocatedOrders": [{"Qty": 1}]})
        with self.assertRaisesRegex(ValueError, "order requirements"):
            self.produce(bands=[self.band(order_req_red=1)])
        with self.assertRaisesRegex(ValueError, "order requirements"):
            self.produce(bands=[self.band(order_req_red=None)])

    def test_required_fields_and_native_types_are_not_defaulted(self):
        report = self.report(); del report["ParentPackSize"]
        with self.assertRaisesRegex(ValueError, "canonical fields"):
            self.produce(reports=[report])
        with self.assertRaisesRegex(ValueError, "native int"):
            self.produce(reports=[self.report(VirtualNorm="1.5")])
        with self.assertRaisesRegex(ValueError, "canonical fields"):
            self.produce(advances=[{"sku_code": "A"}])
        with self.assertRaisesRegex(ValueError, "non-stock"):
            self.produce(advances=[dict(sku_code="A", source_location_code="L",
                                        allocated_quantity=1, allocation_type="advance-git")])


if __name__ == "__main__":
    unittest.main()
