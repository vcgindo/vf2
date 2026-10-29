from unittest import TestCase
from mta.presentation.dbm import dbm_rows


class ReadBag(list):
    def __init__(self, rows):
        super().__init__(rows)
        self.traversals = 0

    def __iter__(self):
        self.traversals += 1
        return super().__iter__()


class DbmJoinOnceTests(TestCase):
    def state(self):
        return dict(Suggestions=[dict(SKUCode='S', WhCode='W', Type=1, NewNorm=i) for i in range(30)],
            NormAcceptanceTbl=[],
            DBMMaster=ReadBag([dict(SKUCode='S', WHCode='W', Norm=8, ParentWhCode=None)]),
            SKUDescriptionTbl=ReadBag([dict(SKUCode='S', SKUDescription='first '),
                                       dict(SKUCode='S', SKUDescription='second ')]),
            SiteDescriptionTbl=ReadBag([dict(WHCode='W', WHDescription='location ')]),
            ReasonCodes=ReadBag([dict(Id=1, Reason='reason ')]),
            SkuAttributeData=ReadBag([]), SkuLocAttributeData=ReadBag([]),
            LocationAttributeData=ReadBag([]))

    def test_each_join_owner_is_read_once_and_duplicate_order_is_preserved(self):
        state = self.state()
        rows = dbm_rows(state, predicate=lambda *_: 2)
        self.assertEqual(len(rows), 120)
        self.assertEqual([r['SKUName'] for r in rows[:4]], ['first', 'first', 'second', 'second'])
        self.assertEqual([r['NewNormValue'] for r in rows], [n for n in range(30) for _ in range(4)])
        self.assertEqual([r['RN'] for r in rows], list(range(1, 121)))
        self.assertTrue(all(row['SKUAttribute1'] == '' for row in rows))
        for name, values in state.items():
            if isinstance(values, ReadBag):
                self.assertEqual(values.traversals, 1, name)

    def test_all_accepted_suggestions_do_not_read_join_populations(self):
        state = self.state()
        state['NormAcceptanceTbl'] = [dict(SKUCode='S', WhCode='W')]
        self.assertEqual(dbm_rows(state), [])
        for values in state.values():
            if isinstance(values, ReadBag):
                self.assertEqual(values.traversals, 0)
