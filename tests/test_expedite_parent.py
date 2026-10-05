"""Parent consumer boundary checks; retained SQL comparison is separate."""
import unittest

from mta.presentation.expedite_parent import parent_rows, parent_transit_rows
from mta.presentation.permissions import PermissionCodes


class ParentExpediteTest(unittest.TestCase):
    def setUp(self):
        self.row = dict(SKUCode='S', WhCode='W', ParentWhCode='P', Norm=10,
                        VirtualNorm=10, Stock=0, GIT=0, PhysicalInventoryPen='100.00',
                        PhysicalInventoryColor='Black', PipelineInventoryPen='100.00',
                        PipelineInventoryColor='Red', Req=10, RationedQty=5, BRAge=2)
        self.imp = {name: [] for name in ('SKUDescriptionTbl', 'SiteDescriptionTbl',
                                         'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData')}

    def read(self, **changes):
        args = dict(rows=[self.row], importer=self.imp, standards=[], masters=[],
                    nms=[], products=None, locations=None, paging=(1, 20))
        args.update(changes)
        return parent_rows(**args)

    def test_left_metadata_and_string_scale(self):
        row = self.read()['expediteDispatches'][0]
        self.assertEqual((row['rn'], row['pip'], row['rtq']), ('1', '100.00', '5'))
        self.assertNotIn('sd', row)
        self.assertNotIn('p', row)

    def test_corrected_unpaged_is_explicit_and_keeps_complete_population(self):
        self.assertEqual(self.read(paging=None)['expediteDispatches'],[])
        all_rows=self.read(rows=[self.row]*25,paging=None,corrected_unpaged=True)['expediteDispatches']
        self.assertEqual(len(all_rows),25)
        self.assertEqual(all_rows[:20],self.read(rows=[self.row]*25)['expediteDispatches'])
        self.assertEqual([r['rn'] for r in all_rows],[str(i) for i in range(1,26)])

    def test_zero_ration_requires_parent_master_and_keeps_duplicates(self):
        self.row['RationedQty'] = 0
        self.assertEqual(self.read()['createAvailabilityAtParent'], [])
        values = self.read(masters=[dict(SKUCode='S', WHCode='P')]*2,
                           products=PermissionCodes({'S': 2}))['createAvailabilityAtParent']
        self.assertEqual([r['rn'] for r in values], ['1', '2', '3', '4'])

    def test_distinct_metadata_ties_are_not_given_invented_order(self):
        self.imp['SKUDescriptionTbl'] = [dict(SKUCode='S', SKUDescription=s) for s in ('one', 'two')]
        with self.assertRaisesRegex(ValueError, 'ambiguous_row_number'):
            self.read()

    def test_nonempty_transit_cannot_be_dropped(self):
        with self.assertRaisesRegex(ValueError, 'nonempty_transit'):
            self.read(nms=[dict(SKUCode='S', WhCode='W')])

    def test_transit_dispatch_retains_unselected_nms_but_availability_does_not(self):
        nms = [dict(SKUCode='S', WhCode='W', RLT=3)]
        self.assertEqual(parent_transit_rows(nms, [], [], []),
                         [dict(skucode='S', whcode='W', eta='3', remarks=' ')])
        self.assertEqual(parent_transit_rows(nms, [], [], [], availability=True), [])

    def test_transit_joins_through_remark_then_groups_duplicate_occurrences(self):
        nms = [dict(SKUCode='S', WhCode='W', RLT=3)] * 2
        selected = [dict(sc='s ', wc='w')] * 3
        pick = [dict(SKUCode='S', WhCode='W', ParentStockForRationing=7)] * 2
        # A matching selected row alone cannot connect pick to NMS.
        self.assertNotIn('slt', parent_transit_rows(nms, [], pick, selected)[0])
        remarks = [dict(SKUCode='S', WhCode='W', Remark='ready')]
        self.assertEqual(parent_transit_rows(nms, remarks, pick, selected, availability=True),
                         [dict(skucode='S', whcode='W', slt='7', eta='3', remarks='ready')])

    def test_null_and_space_remark_are_distinct_groups_before_default(self):
        nms = [dict(SKUCode='S', WhCode='W', RLT=None)]
        remarks = [dict(SKUCode='S', WhCode='W', Remark=value) for value in (None, ' ')]
        rows = parent_transit_rows(nms, remarks, [], [])
        self.assertEqual(rows, [dict(skucode='S', whcode='W', remarks=' ')] * 2)

    def test_transit_uses_complete_cte_before_grid_paging(self):
        nms = [dict(SKUCode='S', WhCode='W', RLT=3)]
        remarks = [dict(SKUCode='S', WhCode='W', Remark='ready')]
        pick = [dict(SKUCode='S', WhCode='W', ParentStockForRationing=7)]
        result = self.read(nms=nms, remarks=remarks, pick=pick, paging=(2, 20))
        self.assertEqual(result['expediteDispatches'], [])
        self.assertEqual(result['expediteDispatchestransit'][0]['slt'], '7')


if __name__ == '__main__':
    unittest.main()
