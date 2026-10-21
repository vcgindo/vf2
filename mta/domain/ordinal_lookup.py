"""Disposable, bounded-heap candidate index; PostgreSQL remains operational truth.

The source owner retains the rows. This file contains only typed keys and source
ordinals. Queries stream in original order, so duplicate joins are unchanged.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import ExitStack
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
import os
import sqlite3
import tempfile
from weakref import WeakSet
from mta.row_sequences import RecordRows
from mta.domain.sql_identity_keys import join_key

_indexes = ContextVar('dbm_ordinal_indexes', default=None)


def pair(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode'))


def encode(value):
    if value is None:return b'n'
    if isinstance(value, str):return b's' + value.encode('utf-8', 'surrogatepass')
    raise TypeError('Canonical DBM identity must be text or NULL')


class OrdinalLookup:
    batch_size = 256
    cache_kib = 2048

    def __init__(self, rows, key=pair, key_contract=join_key):
        self.owner = rows
        self.rows = rows.ordinal_source() if isinstance(rows,RecordRows) else rows
        self.key = key
        self.key_contract = key_contract
        self.count = len(rows)
        self.candidate_rows = 0
        self._closed = False
        self._iterators = WeakSet()
        self._cursors = set()
        base = Path(os.environ.get('VF_WORK_ROOT',
            'D:/freshvcf-build/tmp' if os.name == 'nt' else '/tmp'))
        base.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='fresh-dbm-index-', dir=base)
        try:
            self.db = sqlite3.connect(str(Path(self.directory.name)/'ordinals.sqlite'))
            self.db.execute('PRAGMA cache_size=-2048')
            self.db.execute('PRAGMA temp_store=FILE')
            self.db.execute('PRAGMA journal_mode=OFF')
            self.db.execute('PRAGMA synchronous=OFF')
            self.db.execute('CREATE TABLE candidate(sku BLOB NOT NULL, loc BLOB NOT NULL, '
                            'raw_sku BLOB NOT NULL, raw_loc BLOB NOT NULL, ordinal INTEGER NOT NULL)')
            self.db.executemany('INSERT INTO candidate VALUES(?,?,?,?,?)',
                ((encode(contract.normalized[0]), encode(contract.normalized[1]),
                  encode(raw_key[0]), encode(raw_key[1]), ordinal)
                 for ordinal, row in enumerate(self.rows)
                 for raw_key in (tuple(self.key(row)),)
                 for contract in (self.key_contract(*raw_key),)
                 if None not in contract or getattr(contract, 'group_nulls', False)))
            self.db.execute('CREATE INDEX candidate_pair ON candidate(sku,loc,ordinal)')
            self.db.commit()
        except BaseException:
            self.close()
            raise

    def close(self):
        if self._closed:return
        self._closed = True
        # Consumers may retain a short-circuited iterator in a traceback. Close
        # that iterator and its cursor while the connection is still live.
        for iterator in tuple(self._iterators):iterator.close()
        self._iterators.clear()
        for cursor in tuple(self._cursors):cursor.close()
        self._cursors.clear()
        if hasattr(self, 'db'):self.db.close()
        self.directory.cleanup()
        self.owner = self.rows = None

    def __enter__(self):return self

    def __exit__(self, *args):self.close()

    def matching(self, rows, key):
        return self._manage(row for _, row in self.matching_items(rows, key))

    def matching_items(self, rows, key):
        if self._closed:raise ValueError('Ordinal lookup has been released')
        return self._manage(self._matching_items(rows, key))

    def _manage(self, inner):
        def managed():
            try:yield from inner
            finally:
                inner.close()
        iterator = managed()
        self._iterators.add(iterator)
        return iterator

    def _matching_items(self, rows, key):
        if rows is not self.owner or len(rows) != self.count:
            raise ValueError('Ordinal lookup owner changed')
        contract = self.key_contract(*key)
        if None in contract and not getattr(contract, 'group_nulls', False):
            return
        cursor = self.db.execute('SELECT ordinal,raw_sku,raw_loc FROM candidate '
                                 'WHERE sku=? AND loc=? ORDER BY ordinal',
                                 (encode(contract.normalized[0]), encode(contract.normalized[1])))
        self._cursors.add(cursor)
        try:
            while batch := cursor.fetchmany(self.batch_size):
                for ordinal, raw_sku, raw_loc in batch:
                    row = self.rows[ordinal]
                    raw_key = tuple(self.key(row))
                    if (encode(raw_key[0]), encode(raw_key[1])) != (raw_sku, raw_loc):
                        raise ValueError('Ordinal lookup source reordered or mutated')
                    if self.key_contract(*raw_key) != contract:
                        raise ValueError('Ordinal lookup source reordered or mutated')
                    self.candidate_rows += 1
                    yield ordinal, row
        finally:
            if cursor in self._cursors:
                self._cursors.remove(cursor)
                cursor.close()


def indexed_state(*tables):
    def decorate(function):
        @wraps(function)
        def call(today, state, *args, **kwargs):
            with ExitStack() as stack:
                indexes = {name:stack.enter_context(OrdinalLookup(state[name])) for name in tables}
                token = _indexes.set(indexes)
                try:return function(today, state, *args, **kwargs)
                finally:_indexes.reset(token)
        return call
    return decorate


def matching(state, table, key):
    return _indexes.get()[table].matching(state[table], key)


class OrderedIndex:
    """Lazy execution-local candidate bags, never a replacement predicate.

    Callers retain their existing comparison/filter and scalar-winner checks.
    Only keys and ordinals are indexed; immutable rows retain their owner and
    file-backed representation. Unsupported keys fall back to the original
    ordered candidate bag so validation/error ownership is not moved here.
    """
    def __init__(self, rows, key=pair, *, key_contract=join_key, enabled=True):
        self.owner = rows
        self.count = len(rows)
        self.key = key
        self.key_contract = key_contract
        self.enabled = enabled
        self._source = None
        self._disk = None
        self._buckets = None
        self._built = False
        self._fallback = False
        self._closed = False
        self.builds = self.indexed_rows = self.probes = self.candidate_rows = 0

    def __enter__(self):return self

    def __exit__(self, *args):self.close()

    def close(self):
        if self._disk is not None:self._disk.close()
        self._disk = None
        self.owner = self._source = self._buckets = None
        self._closed = True

    def _build(self):
        self._built = True
        self.builds += 1
        self._source = self.owner.ordinal_source() if isinstance(self.owner, RecordRows) else self.owner
        buckets = {}
        try:
            if len(self._source):
                first = self.key_contract(*tuple(self.key(self._source[0])))
                contract = self.key_contract
                if isinstance(first, tuple):
                    # Exact Python pair joins (Rule12) retain case and NULL
                    # equality; they must not inherit the SQL CI comparator.
                    contract = lambda *values:_ExactPair(self.key_contract(*values))
                if len(first) == 2 and all(value is None or isinstance(value,str) for value in first):
                    self._disk = OrdinalLookup(self.owner, key=self.key, key_contract=contract)
                    self.indexed_rows = len(self.owner)
                    return
            for ordinal, row in enumerate(self._source):
                raw = tuple(self.key(row))
                contract = self.key_contract(*raw)
                buckets.setdefault(contract, []).append((ordinal, raw))
                self.indexed_rows += 1
        except (KeyError, TypeError, ValueError, ArithmeticError):
            # The old residual predicate still owns any invalid-key error,
            # including whether an unreferenced row is examined at all.
            self._fallback = True
            buckets = None
        self._buckets = buckets

    def candidate_items(self, key):
        if self._closed:raise ValueError('Ordered index has been released')
        if len(self.owner) != self.count:raise ValueError('Ordered index owner changed')
        self.probes += 1
        if not self.enabled:
            for ordinal, row in enumerate(self.owner):
                self.candidate_rows += 1
                yield ordinal, row
            return
        try:
            raw_query = tuple(key)
            contract = self.key_contract(*raw_query)
            hash(contract)
        except (KeyError, TypeError, ValueError, ArithmeticError):
            for ordinal, row in enumerate(self.owner):
                self.candidate_rows += 1
                yield ordinal, row
            return
        if not self._built:self._build()
        if self._fallback:
            for ordinal, row in enumerate(self.owner):
                self.candidate_rows += 1
                yield ordinal, row
            return
        if self._disk is not None:
            disk_key = self._disk.key_contract(*raw_query)
            if any(value is not None and not isinstance(value,str) for value in disk_key.normalized):
                # Raw Python tuple predicates can compare a numeric query to
                # text without error. Leave that decision with the residual.
                for ordinal, row in enumerate(self.owner):
                    self.candidate_rows += 1
                    yield ordinal, row
                return
            for ordinal, row in self._disk.matching_items(self.owner, raw_query):
                self.candidate_rows += 1
                yield ordinal, row
            return
        for ordinal, raw in self._buckets.get(contract, ()):
            row = self._source[ordinal]
            if tuple(self.key(row)) != raw:
                raise ValueError('Ordered index source reordered or mutated')
            self.candidate_rows += 1
            yield ordinal, row

    def candidates(self, key):
        for _, row in self.candidate_items(key):yield row

    def candidates_for(self, row, *fields):
        # A missing query field belongs to the original residual predicate.
        # Full fallback preserves empty-source and short-circuit error order.
        key = tuple(row[field] for field in fields) if all(field in row for field in fields) else None
        return self.candidates(key)


class _ExactPair(tuple):
    """Existing raw tuple equality adapted to the bounded ordinal store."""
    group_nulls = True

    @property
    def normalized(self):return self
