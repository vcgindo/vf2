"""Parent consumer boundary checks; retained SQL comparison is separate."""
import unittest

from mta.presentation.expedite_parent import parent_rows
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


if __name__ == '__main__':
    unittest.main()
