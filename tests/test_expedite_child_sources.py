from datetime import date
import json
import unittest
from mta.presentation.expedite_child_sources import projections


class ChildSourceTests(unittest.TestCase):
    def test_latest_request_parent_scope_and_all_shipment_occurrences(self):
        requests = [dict(SKUCode='A', WhCode='L', ParentWhCode='P', Request='old',
                         RequestDate='2026-06-01T08:00:00'),
                    dict(SKUCode='A', WhCode='L', ParentWhCode='P', Request='new',
                         RequestDate='2026-06-02T08:00:00')]
        row = dict(SKUCode='A', WhCode='L', ParentWhCode='OTHER', OrderNo='O',
                   CreationDate=date(2026,6,1), SLT=None, TLT=2, Ageing=3, ETA=None,
                   CurrentLocationCode=None, InTransitQty=4, Remark=None)
        lookup = projections(requests, [row, dict(row)])
        result = lookup('a ', 'l', 'p')
        self.assertEqual(result['remark'], 'new')
        rows = json.loads(result['intransit'])
        self.assertEqual(rows, [dict(lc='O', cd='2026-06-01', slt=None, tlt=2, ag=3,
                                    eta=None, cl=None, qty=4, remarks=None)] * 2)
        self.assertIsNone(lookup('A', 'L', 'OTHER')['remark'])
        self.assertEqual(lookup(None, 'L', 'P'), dict(remark=None, intransit='[]'))

    def test_top_tie_disagreement_is_not_silently_resolved(self):
        row = dict(SKUCode='A', WhCode='L', ParentWhCode='P', Request='one', RequestDate=None)
        with self.assertRaisesRegex(ValueError, 'ambiguous_latest_request'):
            projections([row, dict(row, Request='two')], [])
        self.assertEqual(projections([row, dict(row)], [])('A', 'L', 'P')['remark'], 'one')

    def test_native_json_escapes_forward_slashes(self):
        from mta.presentation.expedite_child_sources import TRANSIT_ALIASES
        row = dict.fromkeys(TRANSIT_ALIASES.values())
        row.update(SKUCode='A', WhCode='L', OrderNo='A/B', Remark='one/two')
        wire = projections([], [row])('A', 'L', 'P')['intransit']
        self.assertIn('A\\/B', wire)
        self.assertEqual(json.loads(wire)[0]['remarks'], 'one/two')
