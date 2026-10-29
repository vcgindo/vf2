"""Cursor-only accepted decoding proofs; these fixtures confer no admission."""
from contextlib import ExitStack
from datetime import date, datetime, timezone
from decimal import Decimal
from itertools import islice
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'accepted-state-reader-unit-only')
import django
django.setup()

from mta.row_sequences import RecordRows
from mta.runtime import accepted_state_read as reader, relational_state


class Cursor:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.database.closed += 1

    def execute(self, sql, params):
        self.database.queries.append((sql, params))
        self.rows = iter(self.database.source(sql, params))

    def fetchmany(self, size):
        self.database.fetch_sizes.append(size)
        return list(islice(self.rows, size))


class Database:
    def __init__(self, source):
        self.source = source
        self.queries, self.fetch_sizes = [], []
        self.closed = 0

    def chunked_cursor(self):
        return Cursor(self)


def export_cells(values):
    result = []
    for value in values:
        kind = ('null' if value is None else 'bool' if type(value) is bool else
                'int' if type(value) is int else 'float' if type(value) is float else 'str')
        typed = [None] * 4
        if kind != 'null':
            typed[('str', 'int', 'float', 'bool').index(kind)] = value
        result.append((kind, *typed))
    return result


class AcceptedStateReadTests(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk='selected-owned-run')
        self.registry = {'registered/table': []}

    def no_audits(self):
        stack = ExitStack()
        for name in ('canonical_parts', 'digest', 'iter_image', 'iter_export'):
            stack.enter_context(patch.object(relational_state, name,
                side_effect=AssertionError('Diagnostic reader or hash called')))
        stack.enter_context(patch.object(RecordRows, 'from_rows',
            side_effect=AssertionError('Accepted reads must not spool')))
        return stack

    def test_image_preserves_typed_values_duplicates_fields_and_owned_sql(self):
        stamp = datetime(2037, 4, 10, 9, 8, tzinfo=timezone.utc)
        fields = [['text', 'Quoted"Column', 'str'], ['null', 'nil', 'str'],
                  ['integer', 'number', 'int'], ['boolean', 'enabled', 'bool'],
                  ['decimal', 'price', 'str'], ['day', 'day', 'str'],
                  ['stamp', 'stamp', 'str'], ['real', 'real', 'float']]
        values = ('雪\t\n\\', None, 0, False, Decimal('1.230'), date(2037, 4, 10), stamp, -0.5)
        # Deliberately noncanonical ordinal/count/digest proves absence of an
        # audit only. It is not evidence that corrupt rows are admissible.
        item = dict(table='registered/table', image='owned/image', fields=fields,
                    count=19, digest='unchecked-fixture')
        database = Database(lambda *_: [(8, *values), (22, *values)])
        with patch.object(reader, 'connection', database), self.no_audits():
            rows = reader.load_accepted_image(self.run, item, table_registry=self.registry)
        expected = dict(text='雪\t\n\\', null=None, integer=0, boolean=False,
                        decimal='1.230', day='2037-04-10', stamp=stamp.isoformat(), real=-0.5)
        self.assertEqual(rows, [expected, expected])
        self.assertIs(type(rows[0]['integer']), int)
        self.assertIs(type(rows[0]['boolean']), bool)
        self.assertEqual(list(rows[0]), [field for field, *_ in fields])
        sql, params = database.queries[0]
        self.assertIn('"Quoted""Column"', sql)
        self.assertIn('WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal', sql)
        self.assertEqual(params, [self.run.pk, item['image']])
        self.assertEqual(set(database.fetch_sizes), {500})
        self.assertEqual(database.closed, 1)

    def test_unregistered_tables_still_deny_before_sql(self):
        database = Database(lambda *_: [])
        with patch.object(reader, 'connection', database), self.assertRaisesRegex(ValueError, 'Unknown operational table'):
            list(reader.iter_accepted_image(self.run,
                dict(table='foreign/table', fields=[]), table_registry=self.registry))
        self.assertEqual(database.queries, [])

    def test_large_image_has_no_eager_pass_or_spool_even_with_work_root(self):
        item = dict(table='registered/table', image='large', count=10001,
                    fields=[['code', 'code', 'str']])
        database = Database(lambda *_: ((ordinal, 'same') for ordinal in range(10001)))
        with patch.object(reader, 'connection', database), self.no_audits(), \
                patch.dict(os.environ, {'VF_WORK_ROOT': 'unused-spool-root'}):
            rows = reader.load_accepted_image(self.run, item, table_registry=self.registry)
            self.assertIsInstance(rows, RecordRows)
            self.assertEqual(len(rows), 10001)
            self.assertEqual(database.queries, [])
            self.assertEqual(sum(1 for _ in rows), 10001)
            self.assertEqual(len(database.queries), 1)
            self.assertEqual(next(iter(rows)), {'code': 'same'})
            self.assertEqual(len(database.queries), 2)

    def test_empty_field_images_and_exact_materialization_threshold(self):
        for count in (0, 10000, 10001):
            with self.subTest(count=count):
                item = dict(table='registered/table', image='empty-fields', count=count, fields=[])
                database = Database(lambda *_: ((ordinal,) for ordinal in range(count)))
                with patch.object(reader, 'connection', database), self.no_audits():
                    rows = reader.load_accepted_image(self.run, item, table_registry=self.registry)
                    self.assertEqual(isinstance(rows, RecordRows), count > 10000)
                    self.assertEqual(len(database.queries), 0 if count > 10000 else 1)
                    self.assertEqual(list(rows), [{} for _ in range(count)])
                    self.assertEqual(len(database.queries), 1)

    def test_export_versions_preserve_empty_rows_null_and_each_cell_type(self):
        values = [None, '', '雪\t\n\\', 0, False, -1.25]
        expected = [{'values': []}, {'values': values}, {'values': values}, {'values': []}]
        for version in (1, 2):
            with self.subTest(version=version):
                item = dict(version=version, image='report/export', count=4,
                            lengths=[0, 6, 6, 0], digest='not-a-read-time-check')
                raw = []
                for ordinal, row in enumerate(expected):
                    if version == 2:
                        raw.append((ordinal, 0, len(row['values']), None, None, None, None, None, None))
                    for column, cell in enumerate(export_cells(row['values'])):
                        raw.append((ordinal, 1, None, column, *cell) if version == 2 else
                                   (ordinal, column, *cell))
                database = Database(lambda *_: raw)
                with patch.object(reader, 'connection', database), self.no_audits():
                    rows = reader.load_accepted_export(self.run, item)
                self.assertEqual(rows, expected)
                self.assertIs(type(rows[1]['values'][3]), int)
                self.assertIs(type(rows[1]['values'][4]), bool)
                self.assertEqual(len(database.queries), 1)
                self.assertEqual(database.queries[0][1],
                    [self.run.pk, item['image']] * (2 if version == 2 else 1))
                self.assertEqual(set(database.fetch_sizes), {500})

    def test_large_exports_are_lazy_single_pass_and_span_cursor_chunks(self):
        for version in (1, 2):
            with self.subTest(version=version):
                item = dict(version=version, image='large/export', count=10001, lengths=[1] * 10001)
                def raw(*_):
                    for ordinal in range(10001):
                        if version == 2:
                            yield (ordinal, 0, 1, None, None, None, None, None, None)
                            yield (ordinal, 1, None, 0, 'int', None, ordinal, None, None)
                        else:
                            yield (ordinal, 0, 'int', None, ordinal, None, None)
                database = Database(raw)
                with patch.object(reader, 'connection', database), self.no_audits():
                    rows = reader.load_accepted_export(self.run, item)
                    self.assertIsInstance(rows, RecordRows)
                    self.assertEqual(database.queries, [])
                    for ordinal, row in enumerate(rows):
                        self.assertEqual(row, {'values': [ordinal]})
                    self.assertEqual(len(database.queries), 1)
                    self.assertGreater(len(database.fetch_sizes), 2)

    def test_graph_matches_existing_shape_and_leaves_deferred_reports_deferred(self):
        image = lambda name: {'image': name}
        self.run.production_manifest = dict(
            images={name: {'image': name} for name in ('dbm', 'scratch', 'btr', 'bpr', 'facts')},
            closing={'dbm': {'tables': {'DBMMaster': image('dbm'),
                'IntermediateTables': {'scratch_kind': 'dict', 'items': [['X', image('scratch')]]}}},
                'btr': {'tables': {'IntermediateTables': {'scratch_kind': 'list',
                    'items': [['Y', image('btr')]]}}}, 'importer_settings': image('facts'),
                'publication_context': {'metadata': {'label': 'accepted'}}},
            reports=[{'stage': 'norm0-export', 'tables': {'ReportRows': {'export': {'image': 'export'}}},
                'deferred': {'kind': 'owned-deferred'}, 'sources': {'SourceFacts': image('facts')}}],
            bpr={'BPR_Table': image('bpr')}, lineage=[{'run_id': 'own-parent'}], publication=[{'scope': 'Full'}])
        def load(_run, item):
            return [{'value': item['image'], 'nullable': None}, {'value': item['image'], 'nullable': None}]
        for reports in (False, True):
            with self.subTest(include_reports=reports), \
                    patch.object(relational_state, 'load_image', side_effect=load), \
                    patch.object(relational_state, 'load_export', side_effect=load):
                expected = relational_state.read_daily(self.run, include_reports=reports)
                with patch.object(reader, 'load_accepted_image', side_effect=load), \
                        patch.object(reader, 'load_accepted_export', side_effect=load) as exports, self.no_audits():
                    observed = reader.read_accepted_daily(self.run, include_reports=reports)
                self.assertEqual(observed, expected)
                self.assertEqual(exports.call_count, int(reports))
                self.assertIs(observed['DBMFinal'][0], observed['ClosingState'][0]['dbm'])


if __name__ == '__main__':
    unittest.main()
