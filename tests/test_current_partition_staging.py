"""Admitted typed staging preserves original statement and revision grain."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.db import connection
from mta.application import accepted_inputs
from mta.mdm import daily_current as writer
from mta.mdm.master_owners import business_fields
from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent as Model
from tests.test_bulk_current_postgres import fixture_rows

FIELDS = [field.name for field in business_fields(Model)]
NORM, DESCRIPTION = FIELDS.index('Norm'), FIELDS.index('SKUDescription')


def metadata(count, signature=lambda ordinal: ()):
    return [(10000+ordinal, ordinal, list(signature(ordinal))) for ordinal in range(1, count+1)]


class CurrentPartitionStagingTests(unittest.TestCase):
    def run_staged(self, rows, current, *, atomic=True, copy_error=None):
        executed, copied = [], {}
        cursor, reader = MagicMock(), MagicMock()
        cursor.execute.side_effect = lambda sql, parameters=None: executed.append((sql, deepcopy(parameters)))
        reader.fetchmany.side_effect = [current[i:i+500] for i in range(0, len(current), 500)] + [[]]
        cursor_context, reader_context = MagicMock(), MagicMock()
        cursor_context.__enter__.return_value = cursor
        reader_context.__enter__.return_value = reader
        db = SimpleNamespace(vendor='postgresql', in_atomic_block=atomic,
            ops=connection.ops, features=connection.features, cursor=lambda: cursor_context,
            chunked_cursor=lambda: reader_context)

        def copy(table, columns, records):
            if copy_error:
                raise copy_error
            self.assertNotIsInstance(records, (list, tuple))
            copied.update(table=table, columns=columns, rows=list(records))

        context = SimpleNamespace(native_daily=True, identity=str(uuid4()), accepted_inputs=None)
        accepted_inputs._complete(context)
        with accepted_inputs.consume(context), patch.object(writer, 'connection', db), \
                patch('mta.runtime.relational_state.copy_rows', side_effect=copy), \
                patch.object(writer, '_verify_written', side_effect=AssertionError('automatic readback')):
            if copy_error or not atomic:
                with self.assertRaisesRegex(type(copy_error) if copy_error else ValueError,
                        str(copy_error) if copy_error else 'requires the day transaction'):
                    writer._write_partition(SimpleNamespace(pk=31), Model, {'owner': 'Importer'}, rows, '/current')
                counts = None
            else:
                counts = writer._write_partition(SimpleNamespace(pk=31), Model, {'owner': 'Importer'}, rows, '/current')
        return counts, executed, copied, reader

    def dml(self, executed):
        return [(sql.split(' ', 1)[0], parameters, sql) for sql, parameters in executed
                if sql.startswith(('UPDATE ', 'INSERT ', 'DELETE '))]

    def test_typed_copy_1003_to_1004_keeps_values_pk_order_and_counts(self):
        rows = fixture_rows(Model, count=1004)
        rows[1].update(Norm=-7, SpikeThreshold=Decimal('2.30'),
            SKUDescription='Unicode snowman', SKUIntroDate=date(2026, 4, 9))
        rows[2] = deepcopy(rows[1])
        frozen = deepcopy(rows)
        counts, executed, copied, reader = self.run_staged(rows,
            metadata(1003, lambda ordinal: (NORM,) if ordinal<=936 else ()))
        self.assertEqual(counts, {'updated': 936, 'inserted': 1, 'deleted': 0})
        self.assertEqual(rows, frozen)
        self.assertEqual(copied['columns'][:3], ['source_id', 'owner', 'ordinal'])
        self.assertNotIn('id', copied['columns'])
        actual = [dict(zip(copied['columns'], row)) for row in copied['rows']]
        for index, row in enumerate(actual):
            self.assertEqual(row, dict(source_id=31, owner='Importer', ordinal=index+1, **rows[index]))
        self.assertIsNone(actual[0]['SpikeThreshold'])
        self.assertEqual(actual[1]['SpikeThreshold'], Decimal('2.30'))
        self.assertIsInstance(actual[1]['SKUIntroDate'], date)
        dml = self.dml(executed)
        self.assertEqual([(op, len(params[0]) if op=='UPDATE' else params) for op, params, _ in dml],
                         [('UPDATE', 500), ('UPDATE', 436), ('INSERT', [1004, 1004])])
        for _, _, update in dml[:2]:
            self.assertEqual(update.split(' SET ', 1)[1].split(' FROM ', 1)[0], '"Norm"=incoming."Norm"')
            self.assertIn('target."id"=ANY(%s)', update)
            for name in ('source_id', 'owner', 'ordinal'):
                self.assertIn('target."'+name+'"=incoming."'+name+'"', update)
        self.assertIn('ORDER BY incoming."ordinal"', dml[-1][2])
        self.assertIn('ON COMMIT DROP AS SELECT', executed[0][0])
        self.assertNotIn('DEFAULT', executed[0][0])
        self.assertTrue(executed[1][0].startswith('CREATE UNIQUE INDEX ON pg_temp.'))
        self.assertIn('("ordinal")', executed[1][0])
        query, params = reader.execute.call_args.args
        self.assertEqual(params, [31, 'Importer'])
        self.assertTrue(query.startswith('SELECT target."id",target."ordinal",pg_catalog.array_remove(ARRAY['))
        self.assertIn(' IS DISTINCT FROM incoming."Norm"', query)
        self.assertTrue(query.endswith('ORDER BY target."ordinal"'))
        self.assertNotIn('SELECT target.*', query)

    def test_501_same_signature_keeps_two_updates(self):
        counts, executed, *_ = self.run_staged(fixture_rows(Model, count=501), metadata(501, lambda _: (NORM,)))
        updates = self.dml(executed)
        self.assertEqual([(op, len(params[0])) for op, params, _ in updates], [('UPDATE', 500), ('UPDATE', 1)])
        self.assertEqual(updates[0][1][0], list(range(10001, 10501)))
        self.assertEqual(updates[1][1][0], [10501])
        self.assertEqual(counts, {'updated': 501, 'inserted': 0, 'deleted': 0})

    def test_interleaved_signatures_preserve_threshold_and_first_seen_order(self):
        counts, executed, *_ = self.run_staged(fixture_rows(Model, count=503),
            metadata(503, lambda ordinal: (NORM,) if ordinal%2 else (DESCRIPTION,)))
        updates = self.dml(executed)
        self.assertEqual([len(params[0]) for _, params, _ in updates], [250, 250, 2, 1])
        self.assertEqual([sql.split(' SET ', 1)[1].split(' FROM ', 1)[0] for _, _, sql in updates],
            ['"Norm"=incoming."Norm"', '"SKUDescription"=incoming."SKUDescription"']*2)
        self.assertEqual(updates[2][1][0], [10501, 10503])
        self.assertEqual(updates[3][1][0], [10502])
        self.assertEqual(counts['updated'], 503)

    def test_unchanged_occurrences_do_not_consume_pending_update_threshold(self):
        counts, executed, *_ = self.run_staged(fixture_rows(Model),
            metadata(1003, lambda ordinal: (NORM,) if ordinal%2 else ()))
        updates = self.dml(executed)
        self.assertEqual([len(params[0]) for _, params, _ in updates], [500, 2])
        self.assertEqual(updates[0][1][0], list(range(10001, 11000, 2)))
        self.assertEqual(updates[1][1][0], [11001, 11003])
        self.assertEqual(counts['updated'], 502)

    def test_late_tail_deletes_precede_residual_updates_as_before(self):
        counts, executed, *_ = self.run_staged(fixture_rows(Model, count=501),
            metadata(1504, lambda ordinal: (NORM,) if ordinal<=501 else ()))
        self.assertEqual([(op, len(params[0])) for op, params, _ in self.dml(executed)],
            [('UPDATE', 500), ('DELETE', 500), ('DELETE', 500), ('UPDATE', 1), ('DELETE', 3)])
        self.assertEqual(counts, {'updated': 501, 'inserted': 0, 'deleted': 1003})

    def test_insert_growth_keeps_original_500_chunks(self):
        counts, executed, *_ = self.run_staged(fixture_rows(Model, count=2004), metadata(1003))
        self.assertEqual([(op, params) for op, params, _ in self.dml(executed)],
            [('INSERT', [1004, 1503]), ('INSERT', [1504, 2003]), ('INSERT', [2004, 2004])])
        self.assertEqual(counts, {'updated': 0, 'inserted': 1001, 'deleted': 0})

    def test_equal_population_issues_no_dml(self):
        counts, executed, *_ = self.run_staged(fixture_rows(Model), metadata(1003))
        self.assertEqual(self.dml(executed), [])
        self.assertEqual(counts, {'updated': 0, 'inserted': 0, 'deleted': 0})

    def test_missing_or_boolean_admission_keeps_original_roster_check(self):
        for token in (None, True):
            with self.subTest(token=token), \
                    patch('mta.application.accepted_inputs.current', return_value=token), \
                    patch.object(writer.connection, 'vendor', 'postgresql'), \
                    patch.object(writer, '_replace_large_partition') as staged:
                with self.assertRaisesRegex(ValueError, 'projected fields differ'):
                    writer._write_partition(SimpleNamespace(pk=31), Model, {'owner': 'Importer'}, [{}]*500, '/current')
                staged.assert_not_called()

    def test_transaction_required_and_copy_failure_never_retries(self):
        rows = fixture_rows(Model, count=500)
        _, executed, *_ = self.run_staged(rows, [], atomic=False)
        self.assertEqual(executed, [])
        _, executed, _, reader = self.run_staged(rows, [], copy_error=RuntimeError('COPY failure'))
        self.assertEqual(len(executed), 1)
        reader.execute.assert_not_called()
