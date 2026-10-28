"""Complete-value and failure proof for the private immutable history cache."""
from copy import deepcopy
from datetime import date,datetime,timezone
from decimal import Decimal
import gc
from pathlib import Path
import unittest

from mta.row_sequences import RecordRows,history_rows,is_record_rows
from mta.serialization import canonical_parts,digest,storage


class ImmutableHistoryTests(unittest.TestCase):
    def test_cyclic_short_lived_generation_closes_readers_before_directory_finalizer(self):
        import weakref
        rows=RecordRows.from_rows([{'v':1},{'v':2}])
        directory=Path(rows._directory.name)
        rows[0]  # Exercise the mapped ordinal reader too.
        iterator=iter(rows);next(iterator)
        rows._test_cycle=iterator
        reference=weakref.ref(rows)
        del iterator,rows
        gc.collect()
        self.assertIsNone(reference())
        self.assertFalse(directory.exists())

    def test_finalizer_owns_cached_readers_from_other_threads(self):
        from concurrent.futures import ThreadPoolExecutor
        rows=RecordRows.from_rows([{'v':i} for i in range(600)])
        directory=Path(rows._directory.name)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(lambda index:rows[index]['v'],(0,599,256,1))),[0,599,256,1])
            del rows
            gc.collect()
            self.assertFalse(directory.exists())

    def test_every_scalar_kind_duplicate_null_and_order_survive(self):
        row=dict(s='001,a\n"b',n=None,b=True,i=-7,f=-0.0,d=Decimal('-2.3400'),
            day=date(2026,4,7),time=datetime(2026,4,7,1,2,tzinfo=timezone.utc))
        expected=[row,deepcopy(row),dict(row,i=8)]
        actual=RecordRows.from_rows(iter(expected))
        self.assertEqual(list(actual),expected)
        for index in (0,2,1,-1):
            self.assertEqual(actual[index],expected[index])
            self.assertEqual({k:type(v) for k,v in actual[index].items()},{k:type(v) for k,v in row.items()})
        self.assertEqual(list(actual),expected)
        self.assertEqual(list(actual[1:]),expected[1:])
        self.assertEqual(digest(actual),digest(expected))
        self.assertEqual(b''.join(canonical_parts({'history':actual})),b''.join(canonical_parts({'history':expected})))
        self.assertEqual(list(storage(actual)),storage(expected))

    def test_copy_shares_sealed_generation_but_explicit_row_copy_is_mutable(self):
        actual=RecordRows.from_rows([{'v':1},{'v':1}]);copy=deepcopy(actual)
        self.assertIs(copy,actual)
        for mutation in (lambda row:row.update(v=2),lambda row:row.clear(),lambda row:row.__setitem__('v',2)):
            with self.assertRaises(TypeError):mutation(actual[0])
        row=deepcopy(actual[0]);row['v']=2
        self.assertEqual(actual[0],{'v':1})

    def test_factory_does_not_materialize_and_ordinal_cache_is_execution_local(self):
        calls=[]
        def factory():
            calls.append('scan');yield from ({'v':i} for i in range(4))
        rows=RecordRows(4,factory)
        self.assertEqual(calls,[])
        cached=rows.ordinal_source();self.assertIs(rows.ordinal_source(),cached)
        self.assertEqual(cached[3],{'v':3})
        self.assertEqual(calls,['scan'])
        with self.assertRaises(ValueError):list(RecordRows(3,lambda:iter([{'v':1}])))

    def test_changed_cache_is_never_accepted(self):
        rows=RecordRows.from_rows([{'v':1}])
        rows._data.write_bytes(rows._data.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'cache changed'):list(rows)
        with self.assertRaisesRegex(ValueError,'cache changed'):rows[0]

    def test_ordinal_block_digest_denies_same_size_restored_timestamp_tamper(self):
        import os,struct,zlib
        from mta.row_sequences import _cache_row
        rows=RecordRows.from_rows([{'v':1}])
        info=rows._data.stat()
        compressed=zlib.compress(_cache_row({'v':2})+b'\n',level=1)
        replacement=struct.pack('<I',len(compressed))+compressed
        self.assertEqual(len(replacement),info.st_size)
        rows._data.write_bytes(replacement)
        os.utime(rows._data,ns=(info.st_atime_ns,info.st_mtime_ns))
        with self.assertRaisesRegex(ValueError,'block value/order drift'):rows[0]

    def test_empty_bad_roster_and_cleanup(self):
        self.assertEqual(list(RecordRows.from_rows([])),[])
        for rows in ([{'a':1},{'b':1}],[{'v':[]}],[1]):
            with self.assertRaises(ValueError):RecordRows.from_rows(rows)
        rows=RecordRows.from_rows([{'v':1}]);directory=Path(rows._directory.name)
        self.assertEqual(rows[0],{'v':1})
        del rows;gc.collect()
        self.assertFalse(directory.exists())
        self.assertTrue(is_record_rows([]));self.assertFalse(is_record_rows(iter([])))
        self.assertEqual(history_rows(({'v':i} for i in range(2)),like=[]),[{'v':0},{'v':1}])


if __name__=='__main__':unittest.main()
