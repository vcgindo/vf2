"""Actual PostgreSQL stream lifecycle; no persisted business writes."""
import os
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.db import connection, transaction, DatabaseError
from mta.presentation import btr_sql


@unittest.skipUnless(os.environ.get('VF_IR2_PROJECTION_POSTGRES') == '1',
                     'Owned isolated PostgreSQL only')
class BtrExportCompilePostgresTests(unittest.TestCase):
    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database(),current_user')
            database, role = cursor.fetchone()
            self.assertIn(database, ('vftest_fresh_ir2_dated1_20261103',
                                     'vftest_fresh_ir2_dated6_20261103'))
            self.assertIn(role, ('vectorflow_mta_owner', 'vectorflow_mta_runtime'))

    def setting(self):
        with connection.cursor() as cursor:
            cursor.execute('SHOW jit')
            return cursor.fetchone()[0]

    def portals(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM pg_cursors WHERE name LIKE '_django_curs_%'")
            return set(row[0] for row in cursor.fetchall())

    def test_complete_stream_restores_original_setting_and_cursor(self):
        before = self.setting()
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SET LOCAL jit=on')
            opened = self.portals()
            rows = list(btr_sql._export_rows(
                "SELECT current_setting('jit') AS jit,n FROM generate_series(1,600) n", [], dated=True))
            self.assertEqual(rows, [{'jit': 'off', 'n': n} for n in range(1,601)])
            self.assertEqual(self.setting(), 'on')
            self.assertEqual(self.portals(), opened)
        self.assertEqual(self.setting(), before)

    def test_disconnect_and_query_failure_restore_outer_transaction(self):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SET LOCAL jit=on')
            opened = self.portals()
            stream = btr_sql._export_rows(
                "SELECT current_setting('jit') AS jit,n FROM generate_series(1,600) n", [], dated=True)
            self.assertEqual(next(stream), {'jit': 'off', 'n': 1})
            stream.close()
            self.assertEqual(self.setting(), 'on')
            self.assertEqual(self.portals(), opened)
            self.assertFalse(connection.needs_rollback)
            with self.assertRaises(DatabaseError):
                list(btr_sql._export_rows('SELECT 1/0 AS value', [], dated=True))
            self.assertEqual(self.setting(), 'on')
            self.assertEqual(self.portals(), opened)
            self.assertFalse(connection.needs_rollback)

    def test_old_export_and_existing_off_policy_are_unchanged(self):
        with transaction.atomic(), connection.cursor() as cursor:
            for setting in ('on','off'):
                cursor.execute("SELECT set_config('jit',%s,true)", [setting])
                self.assertEqual(list(btr_sql._export_rows(
                    "SELECT current_setting('jit') AS jit", [], dated=False)), [{'jit': setting}])
                self.assertEqual(self.setting(), setting)
            self.assertEqual(list(btr_sql._export_rows(
                "SELECT current_setting('jit') AS jit", [], dated=True)), [{'jit': 'off'}])
            self.assertEqual(self.setting(), 'off')
