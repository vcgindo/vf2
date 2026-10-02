import unittest
from mta.presentation.expedite_custom import custom_rows
from mta.presentation.permissions import PermissionCodes


class ExpediteCustomTest(unittest.TestCase):
    def setUp(self):
        self.row = dict(SKUCode='S', WhCode='W', ParentWhCode='P', IsReceiving=True,
                        RationedQty=7, GIT=0, PhysicalInventoryColor='Black',
                        PipelineInventoryColor='Red', PhysicalInventoryPen='100.00',
                        PipelineInventoryPen='90.00')

    def read(self, **kwargs):
        args = dict(rows=[self.row], nms=[], products=None, locations=None, paging=None)
        args.update(kwargs)
        return custom_rows(**args)

    def test_native_empty_retains_values_and_omits_identity(self):
        self.assertEqual(self.read(), [dict(RN=1, pt='Black', tpp=100, git=0, ep='Red', epp=90, rq=7)])

    def test_scope_is_parent_and_duplicate_bag_is_preserved(self):
        self.assertEqual(self.read(locations={'W'}), [])
        values = self.read(locations=PermissionCodes({'P':3}), paging=(2,1))
        self.assertEqual([r['RN'] for r in values], [2])

    def test_conflicting_tie_denied_but_out_of_range_is_empty(self):
        rows = [self.row,dict(self.row,RationedQty=8)]
        with self.assertRaisesRegex(ValueError,'UNORDERED-NMS'):
            self.read(rows=rows)
        self.assertEqual(self.read(rows=rows,paging=(3,1)), [])

    def test_nonreceiving_nonpositive_and_nonempty_nms(self):
        self.assertEqual(self.read(rows=[dict(self.row,IsReceiving=False),dict(self.row,RationedQty=0)]), [])
        with self.assertRaisesRegex(ValueError,'nonempty_nms'):
            self.read(nms=[{}])
