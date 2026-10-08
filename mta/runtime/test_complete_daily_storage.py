"""Migration-enabled PostgreSQL proof for complete-day typed populations."""
from copy import deepcopy
from datetime import date

from django.db import connection, IntegrityError, transaction
from django.test import TransactionTestCase

from mta.runtime.complete_daily_state import BINDINGS, TABLES
from mta.runtime.input_storage import save_input, read_input
from mta.runtime.models import CalculationRun
from mta.runtime.relational_state import save_image, load_image, table_sql
from mta.serialization import digest


class CompleteDailyStorageTests(TransactionTestCase):
    def setUp(self):
        self.owners = []

    def run_owner(self, identity):
        run = CalculationRun.objects.create(
            input_digest=digest(identity), execution_revision='complete-storage-proof',
            business_date=date(2026, 6, 6), input_payload={}, kind='DAILY')
        self.owners.append(run.pk)
        return run

    def rows(self, columns):
        values = {'int': 17, 'bigint': 2147483649, 'bit': True,
                  'date': '2026-06-06', 'datetime': '2026-06-06T12:34:56.003000',
                  'decimal': '123.125', 'numeric': '123.125',
                  'float': 0.125, 'real': 0.125,
                  'nchar': 'Text ', 'nvarchar': 'Text ', 'varchar': 'Text ', 'xml': '<x/>'}
        row = {name: values[kind] for name, kind in columns}
        return [row, deepcopy(row), {name: None for name, _ in columns}]

    def test_all_native_columns_duplicates_nulls_and_run_isolation(self):
        first, second = self.run_owner('first'), self.run_owner('second')
        for binding, key in BINDINGS.items():
            rows = self.rows(TABLES[key])
            metadata = save_image(first, binding, binding, rows)
            self.assertEqual(load_image(first, metadata), rows)
            other = save_image(second, binding, binding, rows[::-1])
            self.assertEqual(load_image(second, other), rows[::-1])
            with self.assertRaisesRegex(ValueError, 'drift'):
                load_image(second, metadata)
            with connection.cursor() as cursor:
                cursor.execute('SELECT count(*), count(DISTINCT vf_ordinal) FROM '
                               + table_sql(key) + ' WHERE vf_run_id=%s', [first.pk])
                self.assertEqual(cursor.fetchone(), (3, 3))

    def test_own_complete_opening_reconstructs_from_typed_rows(self):
        complete = {binding.rsplit('/', 1)[-1]: self.rows(TABLES[key])
                    for binding, key in BINDINGS.items()}
        raw = dict(profile={'delivery': {'site_code': 'VECTORFLOW-DEMO'}},
                   opening={'state': {'complete': complete}})
        run = self.run_owner('opening')
        run.input_digest = digest(raw)
        run.input_payload = save_input(run, raw)
        run.input_manifest_digest = digest(run.input_payload)
        run.save()
        run.refresh_from_db()
        self.assertEqual(read_input(run), raw)
        self.assertNotIn('Text ', str(run.input_payload))

    def test_database_rollback_and_restrict_are_real(self):
        run = self.run_owner('rollback')
        binding, key = next(iter(BINDINGS.items()))
        rows = self.rows(TABLES[key])
        with self.assertRaisesRegex(RuntimeError, 'deliberate'):
            with transaction.atomic():
                save_image(run, binding, binding, rows)
                raise RuntimeError('deliberate rollback')
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM ' + table_sql(key) + ' WHERE vf_run_id=%s', [run.pk])
            self.assertEqual(cursor.fetchone()[0], 0)
        save_image(run, binding, binding, rows)
        with self.assertRaises(IntegrityError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM mta.fresh_mta_calculationrun WHERE id=%s', [run.pk])

    def _fixture_teardown(self):
        # Generic flush cannot include raw-SQL state FKs and must not truncate
        # unrelated immutable source tables. Remove precisely this test's rows.
        if connection.settings_dict['NAME'] != 'test_freshvcf':
            raise RuntimeError('Storage-test cleanup requires the isolated test database')
        with connection.cursor() as cursor:
            for owner in self.owners:
                for key in (*TABLES, 'input/row_shape'):
                    cursor.execute('DELETE FROM ' + table_sql(key) + ' WHERE vf_run_id=%s', [owner])
                cursor.execute('DELETE FROM mta.fresh_mta_calculationrun WHERE id=%s', [owner])
