from unittest import TestCase
from unittest.mock import patch

from mta.domain import btr_finalization as btr
from mta.presentation import btr_incremental_xml as xml


class SnapshotAdvanceTests(TestCase):
    def test_rolling_dates_escaping_new_keys_and_latest_multiplicity(self):
        for gap in (1, 30, 60, 89, 90, 120):
            with self.subTest(gap=gap):
                state = {name: [] for name in xml.FAMILIES}
                old = dict.fromkeys(btr.DAYS)
                for slot in (1, 30, 60, 89, 90):
                    old[f'D{slot}'] = 'a<&"\'\n/>'
                parent = btr._xml_rows([old]*3)
                prefixes = (xml.shifted(parent, gap),)*8
                for name in xml.FAMILIES:
                    for sku in ('A', 'B', 'C'):
                        row = dict(SKUCode=sku, WhCode='L', ParentWhCode=None, WhType=None,
                                   ParentWhType=None, Norm=8, Age=2)
                        row.update({colour+'Count': 0 for colour in btr.COLOURS})
                        row.update({k: old.get('D'+str(i+gap)) for i,k in enumerate(btr.DAYS,1)})
                        row['D90'] = '' if name.startswith('BPP') else None
                        state[name].extend([row]*(2 if name.startswith('BPP') else 1))
                expected = btr._snapshot(state, _owned=True)['BTRSnapshotForUI']
                prior = iter([(('A','L'), 0, prefixes), (('C','L'), 0, prefixes)])
                with patch.object(xml, 'summary') as summary:
                    actual = xml._advance_snapshot(state, prior, gap)['BTRSnapshotForUI']
                self.assertEqual(actual, expected)
                counters = summary.call_args.kwargs
                self.assertEqual(counters['full_row_fallbacks'], int(gap < 90))
                self.assertGreater(counters['reused_transitions'], 0)

    def test_unmatched_or_mixed_fragments_do_not_supply_a_previous_window(self):
        self.assertIsNone(xml.shifted('', 1))
        self.assertIsNone(xml.shifted('<X/><X D90="2"/>', 1))
        self.assertEqual(xml.shifted('<X/>', 1), '<X')
