"""Pure proof for fixed attempt-owned daily feed staging.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date, timezone
from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from mta.application.native_daily_contract import (SCHEMA, FEED_SCHEMA,
    STOCK_FEED_SCHEMA, ACTIVE_STOCK_SCHEMA)
from mta.runtime import batch_storage as storage
from mta.runtime import ingestion_ownership


SOURCE = 'a' * 64


def attempt():
    return SimpleNamespace(pk=9, attempt_id=uuid4(), initialization_id=uuid4())


def identity(owner):
    return dict(database_name='pure_batch', database_oid=37, source_id=4,
        source_digest=SOURCE, initialization_id=str(owner.initialization_id),
        attempt_id=str(owner.attempt_id))


def empty(intake, *, internal=False):
    result = {name: [] for name in storage.DECLARATION['intakes'][intake]}
    if internal:
        result.update({name: [] for name in storage.DECLARATION['internal_roster']})
    return result


class Cursor:
    def __init__(self, records):
        self.records = records

    def execute(self, sql, params):
        table = sql.split(' FROM mta_state."', 1)[1].split('"', 1)[0]
        self.rows = list(self.records.get(table, ()))

    def fetchmany(self, size):
        result, self.rows = self.rows[:size], self.rows[size:]
        return result

    def __enter__(self): return self
    def __exit__(self, *args): pass


class BatchStorageTests(TestCase):
    def test_all_declared_intake_rosters_and_optional_consumer_group(self):
        owner = attempt()
        for intake, expected in ((SCHEMA, 10), (FEED_SCHEMA, 14),
                                 (STOCK_FEED_SCHEMA, 15), (ACTIVE_STOCK_SCHEMA, 11)):
            with patch.object(storage, 'bulk'):
                manifest = storage.save_populations(owner, intake, empty(intake),
                    _identity_resolver=identity)
            self.assertEqual(len(manifest['feeds']), expected)
        with patch.object(storage, 'bulk'):
            manifest = storage.save_populations(owner, SCHEMA, empty(SCHEMA, internal=True),
                _identity_resolver=identity)
        self.assertEqual([x['filename'] for x in manifest['feeds']][-4:],
                         storage.DECLARATION['internal_roster'])

    def test_typed_duplicate_null_order_round_trip(self):
        owner = attempt()
        populations = empty(SCHEMA)
        row = dict(SKUCode='A', WhCode=None, Stock=7, Consumption=0, GIT=None,
            Receipts=2, PSO=1, ReportDate='2026-10-21')
        populations['DailyDataRaw.csv'] = [row, deepcopy(row)]
        inserted = {}
        def capture(sql, records):
            table = sql.split('INSERT INTO mta_state."', 1)[1].split('"', 1)[0]
            inserted[table] = list(records)
        with patch.object(storage, 'bulk', side_effect=capture):
            manifest = storage.save_populations(owner, SCHEMA, populations,
                _identity_resolver=identity)
        daily = next(x for x in manifest['feeds'] if x['filename'] == 'DailyDataRaw.csv')
        self.assertEqual([x[1] for x in inserted[daily['table']]], [0, 1])
        records = {daily['table']: [record[1:] for record in inserted[daily['table']]]}
        fake = SimpleNamespace(chunked_cursor=lambda: Cursor(records))
        with patch.object(storage, 'connection', fake):
            actual = storage.read_populations(owner, manifest,
                _identity_resolver=identity)
        self.assertEqual(actual['DailyDataRaw.csv'], [row, row])

    def test_decimal_datetime_and_timezone_are_database_typed(self):
        owner = attempt()
        populations = empty(SCHEMA, internal=True)
        request = {name: None for name, _ in storage.TABLES['@consumer/requests']['columns']}
        request.update(SKUCode='S', WhCode='W', ParentWhCode='P', Request='R',
            RequestDate='2026-10-20T12:01:02', Action='A', UserId='U')
        populations['@consumer/requests'] = [request]
        remark = {name: None for name, _ in storage.TABLES['@consumer/remarks/bpr']['columns']}
        remark.update(SKUCode='S', WhCode='W', Remark='x', Username='u',
            RemarkDate='2026-10-20T12:01:02+05:30')
        populations['@consumer/remarks/bpr'] = [remark]
        captured = []
        with patch.object(storage, 'bulk', side_effect=lambda sql, rows: captured.extend(rows)):
            storage.save_populations(owner, SCHEMA, populations, _identity_resolver=identity)
        values = [value for record in captured for value in record]
        self.assertIn(date(2026, 10, 20), [v.date() if hasattr(v, 'date') else v for v in values])
        self.assertTrue(any(getattr(v, 'tzinfo', None) is not None for v in values))

    def test_timestamp_wire_text_survives_database_normalization_exactly(self):
        owner = attempt()
        populations = empty(SCHEMA, internal=True)
        request = {name: None for name, _ in storage.TABLES['@consumer/requests']['columns']}
        request.update(SKUCode='S', WhCode='W', ParentWhCode='P', Request='R',
            RequestDate='2026-10-20T12:01:02.123400', Action='A',
            ActionDate='2026-10-20T12:01', UserId='U')
        populations['@consumer/requests'] = [request]
        stamps = {'bpr': '2026-10-20T06:31:02.123400Z',
                  'bor': '2026-10-20T12:01+05:30',
                  'boroa': '2026-10-20T02:31:02-04:00'}
        for family, stamp in stamps.items():
            filename = '@consumer/remarks/' + family
            row = {name: None for name, _ in storage.TABLES[filename]['columns']}
            row.update(SKUCode='S', WhCode='W', Remark='x', Username='u', RemarkDate=stamp)
            if family != 'bpr': row['SupplierCode'] = 'P'
            populations[filename] = [row]
        inserted = {}
        def capture(sql, records):
            table = sql.split('INSERT INTO mta_state."', 1)[1].split('"', 1)[0]
            inserted[table] = list(records)
        with patch.object(storage, 'bulk', side_effect=capture):
            manifest = storage.save_populations(owner, SCHEMA, populations,
                _identity_resolver=identity)
        # Simulate PostgreSQL returning timestamptz values normalized to UTC;
        # companion wire columns retain the accepted lexical representation.
        for entry in manifest['feeds']:
            if not entry['filename'].startswith('@consumer/remarks/') or not entry['count']:
                continue
            record = list(inserted[entry['table']][0])
            position = 2 + [field[0] for field in entry['fields']].index('RemarkDate')
            record[position] = record[position].astimezone(timezone.utc)
            inserted[entry['table']][0] = tuple(record)
        records = {table: [record[1:] for record in rows]
                   for table, rows in inserted.items()}
        fake = SimpleNamespace(chunked_cursor=lambda: Cursor(records))
        with patch.object(storage, 'connection', fake):
            actual = storage.read_populations(owner, manifest, _identity_resolver=identity)
        self.assertEqual(actual['@consumer/requests'][0], request)
        for family, stamp in stamps.items():
            self.assertEqual(actual['@consumer/remarks/' + family][0]['RemarkDate'], stamp)

    def test_missing_foreign_mutable_and_incomplete_identities_fail(self):
        owner = attempt()
        populations = empty(SCHEMA)
        del populations['OrderFeed.csv']
        with self.assertRaises(ValueError):
            storage.save_populations(owner, SCHEMA, populations, _identity_resolver=identity)
        partial = empty(SCHEMA)
        partial['@consumer/requests'] = []
        with self.assertRaises(ValueError):
            storage.save_populations(owner, SCHEMA, partial, _identity_resolver=identity)
        foreign = identity(owner); foreign['attempt_id'] = str(uuid4())
        with self.assertRaises(ValueError):
            storage.save_populations(owner, SCHEMA, empty(SCHEMA),
                _identity_resolver=lambda _: foreign)
        bad = identity(owner); bad['database_oid'] += 1
        with patch.object(storage, 'bulk'):
            manifest = storage.save_populations(owner, SCHEMA, empty(SCHEMA),
                _identity_resolver=identity)
        with self.assertRaises(ValueError):
            storage.read_populations(owner, manifest, _identity_resolver=lambda _: bad)
        changed = deepcopy(manifest); changed['feeds'][0]['columns'].append(['Future', 'int'])
        with self.assertRaises(ValueError):
            storage.read_populations(owner, changed, _identity_resolver=identity)

        live = deepcopy(storage.feeds(SCHEMA))
        live['DailyDataRaw.csv']['columns'].append({'name': 'Future', 'type': 'int'})
        with patch.object(storage, 'feeds', return_value=live):
            with self.assertRaises(ValueError):
                storage.save_populations(owner, SCHEMA, empty(SCHEMA),
                    _identity_resolver=identity)

    def test_migration_has_fixed_typed_tables_and_immutable_guards(self):
        migration = import_module('mta.runtime.migrations.0149_ingestion_typed_batches')
        sql = migration.statements()
        self.assertEqual(sql.count('CREATE TABLE mta_state."batch_'), len(storage.TABLES))
        self.assertEqual(sql.count('REFERENCES mta.fresh_mta_dailyfeedattempt(attempt_id)'),
                         len(storage.TABLES))
        for operation in ('insert', 'update', 'delete', 'truncate'):
            self.assertEqual(sql.count('CREATE TRIGGER daily_batch_' + operation + ' '),
                             len(storage.TABLES))
        self.assertIn('"RequestDate" timestamp without time zone', sql)
        self.assertIn('"RemarkDate" timestamp with time zone', sql)
        self.assertNotIn('row_shape', sql)

        temporal = import_module('mta.runtime.migrations.0152_batch_temporal_wire')
        wire_sql = temporal.forward()
        self.assertEqual(wire_sql.count(' ADD COLUMN "vf_wire_'), 6)
        self.assertEqual(wire_sql.count(' IS NOT DISTINCT FROM '), 6)

        guards = import_module('mta.runtime.migrations.0150_ingestion_typed_batch_guards')
        self.assertEqual(guards.TABLES, tuple(item['table'] for item in storage.TABLES.values()))
        self.assertTrue(all(ingestion_ownership.domain('mta_state', table) == 'fact'
                            for table in guards.TABLES))

    def test_live_sealed_read_rejects_failed_and_rejected_attempts(self):
        manifest = {'sealed': True}
        initialization_id = uuid4()
        source = SimpleNamespace(pk=3, digest=SOURCE)
        initialization = SimpleNamespace(source=source)

        class Attempt:
            pass
        class Manager:
            def select_related(self, *args): return self
            def get(self, **kwargs): return current
        Attempt.objects = Manager()
        candidate = Attempt()
        candidate.pk = 8
        candidate.attempt_id = uuid4()
        candidate.initialization_id = initialization_id
        current = Attempt()
        current.pk = candidate.pk
        current.attempt_id = candidate.attempt_id
        current.initialization_id = initialization_id
        current.initialization = initialization
        current.phase = 'SEALED'
        current.accepted_facts = manifest
        with patch.object(storage, '_database_identity', return_value=('db', 9)):
            for status in ('FAILED', 'REJECTED'):
                current.status = status
                with self.assertRaises(ValueError):
                    storage._live_identity(candidate, reading=True, manifest=manifest)
            current.status = 'FAILED'
            self.assertEqual(storage._live_identity(candidate, reading=True, manifest=manifest,
                allow_owned_failed=True)['attempt_id'], str(candidate.attempt_id))
            current.status = 'REJECTED'
            with self.assertRaises(ValueError):
                storage._live_identity(candidate, reading=True, manifest=manifest,
                    allow_owned_failed=True)
            for status in ('RUNNING', 'COMMITTED', 'PREPARED', 'PUBLISHED'):
                current.status = status
                self.assertEqual(storage._live_identity(candidate, reading=True,
                    manifest=manifest)['attempt_id'], str(candidate.attempt_id))
