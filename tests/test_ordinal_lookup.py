import tracemalloc
import unittest
from pathlib import Path

from mta.domain.ordinal_lookup import OrdinalLookup, pair


class OrdinalLookupTests(unittest.TestCase):
    def test_duplicates_nulls_type_distinctions_and_order(self):
        rows = [{'SKUCode': s, 'WhCode': w, 'payload': i}
                for i, (s, w) in enumerate([('01','a'), (None,'a'), ('1','a'),
                                            ('01','a'), ('None','a'), (None,None)])]
        with OrdinalLookup(rows) as lookup:
            folder = Path(lookup.directory.name)
            for key in [('01','a'), (None,'a'), ('1','a'), ('None','a'), (None,None), ('X','a')]:
                expected = [] if None in key else [r for r in rows if pair(r)==key]
                self.assertEqual(list(lookup.matching(rows, key)), expected)
            with self.assertRaises(TypeError):list(lookup.matching(rows, (1,'a')))
            with self.assertRaises(ValueError):list(lookup.matching(list(rows), ('01','a')))
            rows[0], rows[1] = rows[1], rows[0]
            with self.assertRaises(ValueError):list(lookup.matching(rows, ('01','a')))
        self.assertFalse(folder.exists())

    def test_cleanup_on_failure(self):
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            with OrdinalLookup([]) as lookup:
                folder = Path(lookup.directory.name)
                raise RuntimeError('injected')
        self.assertFalse(folder.exists())

    def test_bounded_component_cardinality(self):
        # The input owner is excluded; measure only additional Python index heap.
        rows = [{'SKUCode': str(i % 500), 'WhCode': 'W', 'ordinal': i} for i in range(50000)]
        tracemalloc.start()
        try:
            with OrdinalLookup(rows) as lookup:
                self.assertEqual(lookup.db.execute('PRAGMA cache_size').fetchone()[0], -2048)
                self.assertEqual([c[1] for c in lookup.db.execute('PRAGMA table_info(candidate)')],
                                 ['sku','loc','raw_sku','raw_loc','ordinal'])
                self.assertEqual(sum(1 for _ in lookup.matching(rows, ('7','W'))), 100)
                self.assertEqual(lookup.candidate_rows, 100)
                _, peak = tracemalloc.get_traced_memory()
                self.assertLess(peak, 2*1024*1024)
                print('ordinal-index: rows=50000 matches=100 Python-index-peak-bytes='+str(peak))
        finally:
            tracemalloc.stop()
