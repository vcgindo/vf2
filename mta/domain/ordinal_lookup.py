"""Disposable, bounded-heap candidate index; PostgreSQL remains operational truth.

The source owner retains the rows. This file contains only typed keys and source
ordinals. Queries stream in original order, so duplicate joins are unchanged.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import ExitStack
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
import os
import sqlite3
import tempfile
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
                 if None not in contract))
            self.db.execute('CREATE INDEX candidate_pair ON candidate(sku,loc,ordinal)')
            self.db.commit()
        except BaseException:
            self.close()
            raise

    def close(self):
        if hasattr(self, 'db'):self.db.close()
        self.directory.cleanup()

    def __enter__(self):return self

    def __exit__(self, *args):self.close()

    def matching(self, rows, key):
        if rows is not self.owner or len(rows) != self.count:
            raise ValueError('Ordinal lookup owner changed')
        contract = self.key_contract(*key)
        if None in contract:
            return
        cursor = self.db.execute('SELECT ordinal,raw_sku,raw_loc FROM candidate '
                                 'WHERE sku=? AND loc=? ORDER BY ordinal',
                                 (encode(contract.normalized[0]), encode(contract.normalized[1])))
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
                    yield row
        finally:
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
