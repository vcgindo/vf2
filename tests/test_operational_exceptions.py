from copy import deepcopy
import unittest

from mta.application.operational_exceptions import (
    BPR_EXCEPTION_FIELDS, BPR_MASTER_FIELDS, DAILY_CONSUMPTION_FIELDS, MIN_PENETRATION,
    NATIVE_SCHEMAS, NO_NORM_PARENT_FIELDS, ORDER_QUALIFICATION, PHASE_OUT_FIELDS, SOURCES,
    bpr_exception_rows, no_norm_at_parent_rows,
    bpr_exception_resultsets,
)
from mta.application.r1_importer_master import MASTER_COLUMNS


def equal(left, right):
    return str(left).rstrip(" ").casefold() == str(right).rstrip(" ").casefold()


def master(**changes):
    row = dict(SKUCode="S", WHCode="W", Norm=1, ParentWhCode="P", SKUIntroDate=None)
    row.update(changes); return row


def daily(**changes):
    row = dict(SKUCode="S", WHCode="W", Stock=100000100, Consumption=0, GIT=0,
               Receipts=0, PSO=0, BlueZone=0, ReportDate="2026-06-06")
    row.update(changes); return row


def processed(**changes):
    row = dict(SKUCode="S", WhCode="C", Norm=5, MinNorm=0, RLT=1, RCP=1,
               GCP=1, OCP=None, MinOrderCount=None, ParentWhCode="P",
               SKUIntroDate=None)
    row.update(changes); return row


def phase(**changes):
    row = dict(SKUCode="S", WHCode="C", OldNorm=1, NewNorm=0, PhaseOutFinished=0,
               PhaseOutStartDate="2026-06-01", LastProcessedDate=None, PhaseInSKUCode=None)
    row.update(changes); return row


class OperationalExceptionTests(unittest.TestCase):
    def test_exception_export_left_join_multiplicity_and_native_null_conversion(self):
        rows = [dict(SKUCode='S', WhCode='W', Norm=None, Stock=None, GIT=None)]
        result = bpr_exception_resultsets(exceptions=rows,
            sku_descriptions=[dict(SKUCode='S', SKUDescription='A,B'), dict(SKUCode='S', SKUDescription=None)],
            site_descriptions=[], equal=equal)
        self.assertEqual(result[1]['rows'], [
            ['S', 'AB', 'W', 'Not defined', None, 0, 0],
            ['S', 'Not Defined', 'W', 'Not defined', None, 0, 0]])
        self.assertEqual(rows[0]['Stock'], None)

    def test_sources_and_native_shapes_are_pinned(self):
        self.assertEqual({len(digest) for _, digest in SOURCES.values()}, {64})
        self.assertEqual(tuple(row[0] for row in NATIVE_SCHEMAS["BPRExceptions"]), BPR_EXCEPTION_FIELDS)
        self.assertEqual(tuple(row[0] for row in NATIVE_SCHEMAS["NoNormAtParentReport"]), NO_NORM_PARENT_FIELDS)
        self.assertEqual(str(MIN_PENETRATION), "-99999999.00")

    def test_bpr_current_date_stock_filter_and_exact_strict_boundary(self):
        rows = bpr_exception_rows(bpr_master=[master(Norm=100)], daily_consumption=[
            daily(Stock=100000099),             # exactly the sentinel: excluded
            daily(Stock=100000100),             # below the sentinel: included
            daily(Stock=None),                  # source WHERE excludes NULL Stock
            daily(Stock=100000100, ReportDate="2026-06-05"),
        ], business_date="2026-06-06", equal=equal)
        self.assertEqual(rows, [dict(SKUCode="S", WhCode="W", Norm=100,
                                     Stock=100000100, GIT=0)])

    def test_bpr_norm_zero_equals_sentinel_and_eco_can_trigger(self):
        self.assertEqual(bpr_exception_rows(bpr_master=[master(Norm=0)],
            daily_consumption=[daily(Stock=2147483647, GIT=2147483647)],
            business_date="2026-06-06", equal=equal), [])
        rows = bpr_exception_rows(bpr_master=[master(Norm=1)],
            daily_consumption=[daily(Stock=0, GIT=1000001)],
            business_date="2026-06-06", equal=equal)
        self.assertEqual(len(rows), 1)

    def test_bpr_retains_both_join_multipliers_and_second_master_spelling(self):
        masters = [master(SKUCode="s", WHCode="w"), master(SKUCode="S", WHCode="W")]
        inputs = [daily(SKUCode="S ", WHCode="W ")]
        before = deepcopy((masters, inputs))
        rows = bpr_exception_rows(bpr_master=masters, daily_consumption=inputs,
                                  business_date="2026-06-06", equal=equal)
        self.assertEqual(len(rows), 4)
        self.assertEqual([row["SKUCode"] for row in rows], ["s", "S", "s", "S"])
        self.assertEqual((masters, inputs), before)
        self.assertIn("join-bag", ORDER_QUALIFICATION["BPRExceptions"])

    def test_bpr_requires_complete_typed_closing_populations(self):
        with self.assertRaisesRegex(ValueError, "typed source"):
            bpr_exception_rows(bpr_master=[{"SKUCode": "S"}], daily_consumption=[],
                               business_date="2026-06-06", equal=equal)
        with self.assertRaisesRegex(ValueError, "Explicit SQL equality"):
            bpr_exception_rows(bpr_master=[], daily_consumption=[],
                               business_date="2026-06-06", equal=None)

    def test_no_norm_self_join_preserves_duplicate_product(self):
        rows = [processed(), processed(), processed(WhCode="P", Norm=0, ParentWhCode="ROOT"),
                processed(WhCode="P", Norm=0, ParentWhCode="ROOT")]
        before = deepcopy(rows)
        result = no_norm_at_parent_rows(master_data=rows, phase_out=[], equal=equal)
        self.assertEqual(len(result), 4)
        self.assertTrue(all(tuple(row) == NO_NORM_PARENT_FIELDS for row in result))
        self.assertEqual(rows, before)

    def test_no_norm_processed_nullability_and_norm_predicates(self):
        rows = [processed(Norm=0), processed(ParentWhCode=None),
                processed(WhCode="P", Norm=0, ParentWhCode="ROOT")]
        self.assertEqual(no_norm_at_parent_rows(master_data=rows, phase_out=[], equal=equal), [])
        with self.assertRaisesRegex(ValueError, "Native SQL int"):
            no_norm_at_parent_rows(master_data=[processed(Norm=None)], phase_out=[], equal=equal)
        with self.assertRaisesRegex(ValueError, "Native nvarchar"):
            no_norm_at_parent_rows(master_data=[processed(WhCode=None)], phase_out=[], equal=equal)

    def test_no_norm_removes_child_or_parent_phase_out_with_null_safe_join(self):
        rows = [processed(), processed(WhCode="P", Norm=0, ParentWhCode="ROOT")]
        self.assertEqual(no_norm_at_parent_rows(master_data=rows,
            phase_out=[phase(WHCode="C")], equal=equal), [])
        self.assertEqual(no_norm_at_parent_rows(master_data=rows,
            phase_out=[phase(WHCode="P")], equal=equal), [])
        kept = no_norm_at_parent_rows(master_data=rows,
            phase_out=[phase(SKUCode="OTHER", WHCode="C")], equal=equal)
        self.assertEqual(kept, [dict(SKUCode="S", WhCode="C", Norm=5, ParentWhCode="P")])

    def test_no_norm_requires_full_processed_master_and_phase_types(self):
        with self.assertRaisesRegex(ValueError, "MasterData fields"):
            no_norm_at_parent_rows(master_data=[{"SKUCode": "S"}], phase_out=[], equal=equal)
        broken = phase(); broken.pop("OldNorm")
        with self.assertRaisesRegex(ValueError, "PhaseOutTbl fields"):
            no_norm_at_parent_rows(master_data=[], phase_out=[broken], equal=equal)
        self.assertEqual(tuple(master().keys()), BPR_MASTER_FIELDS)
        self.assertEqual(tuple(daily().keys()), DAILY_CONSUMPTION_FIELDS)
        self.assertEqual(tuple(phase().keys()), PHASE_OUT_FIELDS)
        self.assertEqual(tuple(processed().keys()), MASTER_COLUMNS)


if __name__ == "__main__":
    unittest.main()
