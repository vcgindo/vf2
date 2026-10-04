import unittest
from decimal import Decimal

from mta.presentation.expedite_custom import custom_rows
from mta.presentation.permissions import PermissionCodes


class ExpediteCustomPopulatedTest(unittest.TestCase):
    def setUp(self):
        self.expedite = dict(
            SKUCode='Sku ', WhCode='Wh ', ParentWhCode='Parent ', IsReceiving=True,
            RationedQty=7, GIT=3, PhysicalInventoryColor='Black',
            PipelineInventoryColor='Red', PhysicalInventoryPen='100.00',
            PipelineInventoryPen='90.50')
        self.nms = dict(
            SKUCode='SKU', WhCode='WH', SKUDescription='Item', ParentWhCode='P1',
            WHDescription='Location', Norm=10, MinNorm=2, RLT=4, RCP=5, GCP=6,
            OCP=7, MinOrderCount=8, PackSize=9, FGRMFlag='FG', DBMActive=True,
            SL1='Business', SL2=None, SL3='Family', SL4=None, SL5='Leaf',
            LL1='Zone', LL2=None, LL3='Type', LL4=None, LL5='Store')

    def read(self, **kwargs):
        args = dict(
            rows=[self.expedite], nms=[self.nms], bpr_rows=[], site_descriptions=[],
            visible_dynamic_attributes=(), products=None, locations=None, paging=None)
        args.update(kwargs)
        return custom_rows(**args)

    def test_normalized_left_joins_preserve_duplicate_bags(self):
        result = self.read(
            nms=[self.nms, dict(self.nms)],
            bpr_rows=[dict(SKUCode='sku', WhCode='wh', Stock=12),
                      dict(SKUCode='SKU ', WhCode='WH ', Stock=12)],
            site_descriptions=[dict(WHCode='p1 ', WHDescription='Parent'),
                               dict(WHCode='P1', WHDescription='Parent')])
        self.assertEqual(len(result), 8)
        self.assertEqual([row['RN'] for row in result], list(range(1, 9)))
        self.assertTrue(all(row['sc'] == 'SKU' and row['sk'] == 12 and row['pn'] == 'Parent'
                            for row in result))
        self.assertTrue(all(row['acp'] == 6 and 'gcp' not in row for row in result))

    def test_missing_optional_join_rows_and_nulls_are_omitted(self):
        result = self.read(nms=[dict(self.nms, SKUDescription=None, SL2=None)])[0]
        self.assertNotIn('sd', result)
        self.assertNotIn('sk', result)
        self.assertNotIn('pn', result)
        self.assertNotIn('sl2', result)
        self.assertEqual(result['tpp'], Decimal('100.00'))
        self.assertEqual(result['epp'], Decimal('90.50'))

        unmatched = self.read(nms=[dict(self.nms, SKUCode='OTHER')])[0]
        self.assertNotIn('sc', unmatched)
        self.assertEqual(unmatched['rq'], 7)

    def test_permission_scope_uses_expedite_parent_and_retains_multiplicity(self):
        self.assertEqual(self.read(locations={'WH'}), [])
        result = self.read(products=PermissionCodes({'Sku ': 2}),
                           locations=PermissionCodes({'Parent ': 3}))
        self.assertEqual(len(result), 6)

    def test_paging_uses_normalized_nms_keys_and_nulls_first(self):
        other = dict(self.expedite, SKUCode='B', WhCode='2', RationedQty=9)
        nms_other = dict(self.nms, SKUCode='b', WhCode='2', SKUDescription='Second')
        unmatched = dict(self.expedite, SKUCode='Missing', WhCode='0', RationedQty=5)
        result = self.read(rows=[other, unmatched, self.expedite],
                           nms=[nms_other, self.nms], paging=(2, 1))
        expected = self.read(rows=[other], nms=[nms_other])[0]
        self.assertEqual(result, [dict(expected, RN=2)])

    def test_conflicting_tied_keys_are_unavailable_but_identical_ties_survive(self):
        with self.assertRaisesRegex(ValueError, 'conflicting_row_number_key'):
            self.read(bpr_rows=[dict(SKUCode='SKU', WhCode='WH', Stock=1),
                                dict(SKUCode='sku ', WhCode='wh ', Stock=2)])
        duplicated = self.read(bpr_rows=[dict(SKUCode='SKU', WhCode='WH', Stock=1),
                                         dict(SKUCode='sku ', WhCode='wh ', Stock=1)])
        self.assertEqual(len(duplicated), 2)

    def test_join_inputs_and_visible_dynamic_config_are_explicit(self):
        with self.assertRaisesRegex(ValueError, 'nonempty_nms_dynamic_config_not_verified'):
            custom_rows(rows=[self.expedite], nms=[self.nms], products=None,
                        locations=None, paging=None)
        with self.assertRaisesRegex(ValueError, 'visible_dynamic_attributes_unsupported'):
            self.read(visible_dynamic_attributes=['SKUAttr1'])
        with self.assertRaisesRegex(ValueError, 'bpr_table_not_available'):
            self.read(bpr_rows=None)
        with self.assertRaisesRegex(ValueError, 'site_descriptions_not_available'):
            self.read(site_descriptions=None)


if __name__ == '__main__':
    unittest.main()
