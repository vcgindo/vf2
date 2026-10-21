"""Ordered candidate bags preserve SQL keys and immutable row ownership.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import gc
import unittest
import weakref
import sys
from unittest.mock import patch
from pathlib import Path
from mta.domain.ordinal_lookup import OrdinalLookup, OrderedIndex
from mta.domain.sql_identity_keys import group_key
from mta.row_sequences import RecordRows


class OrderedIndexTests(unittest.TestCase):
    def test_lazy_order_duplicates_null_join_group_and_nonmutation(self):
        rows = [dict(SKUCode='S', WhCode='W', value=1),
                dict(SKUCode=None, WhCode='W', value=2),
                dict(SKUCode='s ', WhCode='w ', value=3)]
        with OrderedIndex(rows) as index:
            self.assertEqual(index.builds, 0)
            self.assertEqual(list(index.candidate_items(('s', 'W'))), [(0, rows[0]), (2, rows[2])])
            self.assertEqual(list(index.candidates((None, 'W'))), [])
            self.assertEqual((index.builds, index.indexed_rows, index.probes, index.candidate_rows), (1, 3, 2, 2))
        self.assertIsNone(index.owner)
        with self.assertRaisesRegex(ValueError, 'released'):list(index.candidates(('S', 'W')))
        with OrderedIndex(rows, key_contract=group_key) as index:
            self.assertEqual(list(index.candidate_items((None, 'w '))), [(1, rows[1])])
        self.assertEqual(rows[0], dict(SKUCode='S', WhCode='W', value=1))

    def test_invalid_and_disabled_candidates_retain_original_error_owner(self):
        rows = [dict(SKUCode='S', WhCode='W'), dict(SKUCode=7, WhCode='W')]
        with OrderedIndex(rows) as index:
            self.assertEqual(list(index.candidates(('S', 'W'))), rows)
        with OrderedIndex(rows, enabled=False) as index:
            self.assertEqual(list(index.candidates(('S', 'W'))), rows)
            self.assertEqual(index.builds, 0)
        with OrderedIndex(rows[:1]) as index:
            self.assertEqual(list(index.candidates((7, 'W'))), rows[:1])
        with OrderedIndex([dict(SKUCode='S')], key=lambda r: (r['SKUCode'], r['WhCode'])) as index:
            self.assertEqual(list(index.candidates(('S', 'W'))), [dict(SKUCode='S')])
        with OrderedIndex(rows[:1],key_contract=lambda *values:tuple(values)) as index:
            self.assertEqual(list(index.candidates((7,'W'))),rows[:1])

    def test_mutation_and_reordering_are_rejected(self):
        rows = [dict(SKUCode='S', WhCode='W')]
        with OrderedIndex(rows) as index:
            list(index.candidates(('S', 'W')))
            rows[0]['WhCode'] = 'X'
            with self.assertRaisesRegex(ValueError, 'mutated'):list(index.candidates(('S', 'W')))
        with OrderedIndex(rows) as index:
            rows.append(dict(SKUCode='T', WhCode='W'))
            with self.assertRaisesRegex(ValueError, 'owner changed'):list(index.candidates(('S', 'W')))

    def test_missing_query_fields_retain_the_residual_and_empty_source(self):
        rows=[dict(SKUCode='S',WhCode='W')]
        with OrderedIndex(rows) as index:
            self.assertEqual(list(index.candidates_for({},'SKUCode','WhCode')),rows)
            self.assertIsNone(index._buckets)
        with OrderedIndex([]) as index:
            self.assertEqual(list(index.candidates_for({},'SKUCode','WhCode')),[])

    def test_file_backed_and_factory_rows_have_one_generation_lifetime(self):
        for factory in (False, True):
            original = [dict(SKUCode='S', WhCode='W', value=i) for i in range(5)]
            rows = RecordRows(5, lambda: iter(original)) if factory else RecordRows.from_rows(original)
            ref = weakref.ref(rows)
            with OrderedIndex(rows) as index:
                self.assertEqual(list(index.candidates(('s ', 'w'))), original)
                self.assertEqual(list(index.candidates(('S', 'W'))), original)
                self.assertEqual(index.builds, 1)
            self.assertEqual(list(rows), original)
            del rows
            gc.collect()
            self.assertIsNone(ref())

    def test_many_key_and_wide_key_growth_counts_real_candidate_visits(self):
        for n in (80, 160, 320):
            rows = RecordRows.from_rows(dict(SKUCode=str(i), WhCode='W') for i in range(n))
            with OrderedIndex(rows) as index:
                for i in range(n):self.assertEqual(len(list(index.candidates((str(i), 'W')))), 1)
                self.assertEqual((index.indexed_rows, index.probes, index.candidate_rows), (n, n, n))
            wide = RecordRows.from_rows(dict(SKUCode='S', WhCode='W', value=i) for i in range(n))
            with OrderedIndex(wide) as index:
                self.assertEqual(len(list(index.candidates(('S', 'W')))), n)
                self.assertEqual((index.indexed_rows, index.candidate_rows), (n, n))

    def test_short_circuit_and_retained_exception_close_owned_iterators_before_database(self):
        rows=RecordRows.from_rows(dict(SKUCode='S',WhCode='W',value=i) for i in range(4))
        unraisable=[]
        with patch.object(sys,'unraisablehook',unraisable.append):
            for ordered in (False,True):
                held=[];owners=[]
                class BusinessError(ValueError):pass
                with self.assertRaisesRegex(BusinessError,'original business exception'):
                    with (OrderedIndex(rows) if ordered else OrdinalLookup(rows)) as index:
                        candidates=index.candidates(('S','W')) if ordered else index.matching(rows,('S','W'))
                        held.append(candidates)
                        self.assertEqual(next(candidates)['value'],0)
                        owner=index._disk if ordered else index
                        owners=list(owner._iterators)
                        self.assertTrue(owner._cursors)
                        directory=Path(owner.directory.name)
                        raise BusinessError('original business exception')
                self.assertTrue(owner._closed)
                self.assertEqual(owner._cursors,set())
                self.assertFalse(owner._iterators)
                self.assertTrue(all(iterator.gi_frame is None for iterator in owners))
                self.assertFalse(directory.exists())
                # The consumer may retain its iterator/traceback past exit.
                held.clear();owners.clear();gc.collect()
                with OrdinalLookup(rows) as index:
                    self.assertTrue(any(row['value']==0 for row in index.matching(rows,('S','W'))))
                self.assertFalse(index._cursors)
                self.assertFalse(index._iterators)
            gc.collect()
        self.assertEqual(unraisable,[])

    def test_unstarted_and_partially_consumed_iterators_release_idempotently(self):
        rows=[dict(SKUCode='S',WhCode='W')]*3
        index=OrdinalLookup(rows)
        unstarted=index.matching_items(rows,('S','W'))
        started=index.matching_items(rows,('S','W'));next(started)
        owned=list(index._iterators)
        index.close();index.close()
        self.assertTrue(all(iterator.gi_frame is None for iterator in owned))
        self.assertEqual(list(started),[]);self.assertEqual(list(unstarted),[])
        self.assertFalse(index._cursors)
        with self.assertRaisesRegex(ValueError,'released'):index.matching_items(rows,('S','W'))

    def test_many_early_probes_do_not_retain_generators_or_cursor_batches(self):
        rows=RecordRows.from_rows(dict(SKUCode='S',WhCode='W',value=i) for i in range(300))
        with OrderedIndex(rows) as index:
            for _ in range(100):
                self.assertTrue(any(row['value']==0 for row in index.candidates(('S','W'))))
                self.assertFalse(index._disk._iterators)
                self.assertFalse(index._disk._cursors)


if __name__ == '__main__':unittest.main()
