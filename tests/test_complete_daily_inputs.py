"""Pure native-shape bridge probes; no business-day/database invocation."""
from copy import deepcopy
from decimal import Decimal
import unittest

from mta.application.complete_daily_inputs import (
    BOR_FIELDS, PICK_FIELDS, REQ_FIELDS, field_maps, materialize_inputs, supplier_dispatch,
    pick_report, requirement_projection, bor_oa_projection)
from mta.runtime.relational_state import CATALOG


def equal(left, right):
    return str(left).rstrip(' ').casefold() == str(right).rstrip(' ').casefold()


class CompleteDailyInputTests(unittest.TestCase):
    def setUp(self):
        self.master = [dict(SKUCode='S', WHCode='W', ParentWhCode='P')]
        self.attrs = [dict(SKUCode='S', LocCode='W', **{f'c{i}': None for i in range(1, 16)})]
        self.sourcing = [dict(sku_code='S', location_code='W', supplier='P')]
        self.bor = [dict(case='r1_bor_1', sku='S', location='W', supplier='P',
            original_requirement='10', dispatch_requirement='12', to_red='2', to_yellow='3',
            to_green='7', to_blue='0')]
        self.rationed = {name: 0 for name, _ in CATALOG['tables']['BPR/vf_RationedReqReport']}
        self.rationed.update(SKUCode='S', WhCode='W', ParentWhCode='P', SKUName=None,
            WhName=None, ParentWhName=None, Norm=9, VirtualNorm=None, ParentNorm=None,
            TechPen=None, EcoPen=None, DispatchPen=None, TechColor=None, EcoColor=None,
            TechPenParent=None, EcoPenParent=None, TechColorParent=None, EcoColorParent=None,
            PhysicalInventoryPen=None, PhysicalInventoryColor=None, DispatchColor=None,
            Req=10, RationedReq=7, PackSize=2, ParentPackSize=4, IsNormed=True,
            AllocatedForDirectOrders=3, LeftoverStock=5, StockPercentageForRationing=75,
            NormPercentReservation=20, ParentStockPercentageForRationing=100,
            ParentNormPercentReservation=0)
        self.band = dict(sku_code='S', location_code='W', parent_location_code='P',
            to_black='0', to_red='2', to_yellow='3', to_green='2', to_blue='0')
        self.source = dict(schema='r1-current-day-input-v5', sourcing=self.sourcing,
            supplier_openings=self.sourcing,
            foundation=dict(inventory_positions=[dict(sku_code='S', location_code='W',
                              stock_quantity=4, goods_in_transit_quantity=2)]))
        self.requirement = dict(sku_code='S', location_code='W', effective_norm=dict(value='9'),
                                virtual_norm=dict(value=None))
        self.bor_oa = dict(case='r1_bor_oa_1', sku='S', location='W', supplier='P', dispatch_colour='BLACK')

    def test_full_supplier_shape_nulls_duplicates_and_occurrence_lineage(self):
        sourcing = self.sourcing + [dict(self.sourcing[0])]
        bor = self.bor + [dict(self.bor[0], case='r1_bor_2')]
        master = self.master * 2
        attrs = self.attrs * 2
        before = deepcopy((sourcing, bor, master, attrs))
        rows, lineage = supplier_dispatch(sourcing=sourcing, bor=bor, bpr_master=master,
                                         sku_loc_attributes=attrs, equal=equal)
        self.assertEqual(len(rows), 8)
        self.assertEqual(len(rows[0]), 28)
        self.assertEqual(set(rows[0]), set(field_maps()['SupplierDispatchReq']))
        self.assertIsNone(rows[0]['SKULocAtt03'])
        self.assertEqual([rows[0][f'Cumulative{name}'] for name in ('TOR', 'TOY', 'TOG', 'TOB')], [2, 5, 12, 12])
        self.assertEqual([r['sourcing_ordinal'] for r in lineage], [0]*4 + [1]*4)
        self.assertEqual([r['attribute_ordinal'] for r in lineage], [0, 1]*4)
        self.assertEqual((sourcing, bor, master, attrs), before)

    def test_supplier_topmost_and_attribute_left_join_null_semantics(self):
        rows, lineage = supplier_dispatch(sourcing=self.sourcing, bor=self.bor, bpr_master=self.master,
                                         sku_loc_attributes=[], equal=equal)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(lineage[0]['attribute_ordinal'])
        self.assertTrue(all(rows[0][f'SKULocAtt{i:02}'] is None for i in range(1, 16)))
        parents = self.master + [dict(SKUCode='S', WHCode='P', ParentWhCode=None)]
        rows, _ = supplier_dispatch(sourcing=self.sourcing, bor=self.bor, bpr_master=parents,
                                   sku_loc_attributes=self.attrs, equal=equal)
        self.assertEqual(rows, [])

    def test_supplier_lineage_and_fractional_quantity_denials(self):
        duplicate_case = [dict(self.sourcing[0], case='same')] * 2
        with self.assertRaisesRegex(ValueError, 'Ambiguous supplier'):
            supplier_dispatch(sourcing=duplicate_case, bor=[], bpr_master=self.master,
                              sku_loc_attributes=self.attrs, equal=equal)
        with self.assertRaisesRegex(ValueError, 'lineage'):
            supplier_dispatch(sourcing=self.sourcing, bor=[dict(self.bor[0], case='unknown')],
                              bpr_master=self.master, sku_loc_attributes=self.attrs, equal=equal)
        with self.assertRaisesRegex(ValueError, 'SQL int'):
            supplier_dispatch(sourcing=self.sourcing, bor=[dict(self.bor[0], to_red='1.5')],
                              bpr_master=self.master, sku_loc_attributes=self.attrs, equal=equal)

    def test_full_pick_shape_and_actual_null_duplicate_bands(self):
        before = deepcopy(self.rationed)
        rows = pick_report(rationed=[self.rationed], bands=[self.band, self.band])
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows[0]), set(PICK_FIELDS))
        self.assertEqual(rows[0], rows[1])
        self.assertIsNone(rows[0]['VirtualNorm'])
        self.assertIsNone(rows[0]['TechPen'])
        self.assertIsNone(rows[0]['PostPipelineInventoryPen'])
        self.assertEqual(rows[0]['AllocatedForDirectOrders'], 0)
        self.assertIs(rows[0]['IsNormed'], True)
        self.assertEqual(self.rationed, before)

    def test_virtual_pick_uses_exact_receiving_node_aliases(self):
        band = dict(self.band, parent_location_code='W', to_red='0', to_yellow='0', to_green='0')
        row = pick_report(rationed=[self.rationed], bands=[band])[0]
        self.assertEqual((row['ParentPackSize'], row['LeftoverParentStock']), (2, 5))
        self.assertEqual((row['ParentStockPercentageForRationing'], row['ParentNormPercentReservation']), (75, 20))
        self.assertEqual((row['RationedReq'], row['Req'], row['AllocatedForDirectOrders']), (0, 0, 3))
        self.assertIs(row['IsNormed'], False)

    def test_req_partial_native_projection_preserves_null_and_order(self):
        rows = requirement_projection(source=self.source, requirements=[self.requirement]*2,
                                      bpr_master=self.master, equal=equal)
        self.assertEqual(len(rows), 2)
        self.assertEqual(tuple(rows[0]), REQ_FIELDS)
        self.assertEqual((rows[0]['Norm'], rows[0]['Stock'], rows[0]['GIT']), (9, 4, 2))
        self.assertIsNone(rows[0]['VirtualNorm'])
        with self.assertRaisesRegex(ValueError, 'unique actual'):
            requirement_projection(source=self.source, requirements=[self.requirement], bpr_master=self.master*2, equal=equal)

    def test_bor_partial_colour_and_separate_opening_lineage(self):
        source = self.sourcing * 2
        rows, lineage = bor_oa_projection(supplier_openings=source,
            bor=[self.bor_oa, dict(self.bor_oa, case='r1_bor_oa_2')])
        self.assertEqual(rows, [dict(SKUCode='S', WhCode='W', DispatchColor='Black')]*2)
        self.assertEqual(tuple(rows[0]), BOR_FIELDS)
        self.assertEqual([r['supplier_opening_ordinal'] for r in lineage], [0, 1])

    def test_aggregate_marks_partial_coverage_and_requires_own_opening(self):
        calculated = dict(r1_bor=self.bor, r1_bor_oa=[self.bor_oa], r1_requirement=[self.requirement],
                          r1_ration_bifurcation=[self.band])
        result = materialize_inputs(source=self.source, calculated=calculated, rationed=[self.rationed],
                                    bpr_master=self.master, sku_loc_attributes=self.attrs, equal=equal)
        self.assertEqual(set(result['missing_full_native_owners']), {'vf_ReqCalculation', 'BORWithOrderAllocation'})
        for name, rows in result['populations'].items():
            self.assertEqual(set(rows[0]), set(result['field_maps'][name]))
            self.assertTrue(all(len(field['source_sha256']) == 64 for field in result['field_maps'][name].values()))
        source = dict(self.source)
        del source['supplier_openings']
        with self.assertRaisesRegex(ValueError, 'own supplier opening'):
            materialize_inputs(source=source, calculated=calculated, rationed=[self.rationed],
                                bpr_master=self.master, sku_loc_attributes=self.attrs, equal=equal)


if __name__ == '__main__':
    unittest.main()
