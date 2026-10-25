"""Real PostgreSQL predicate, exact guard drift and retained-reference rollback."""
from importlib import import_module
import os
import unittest
from tests import test_scoped_view_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class CasefoldPostgresTests(unittest.TestCase):
    for name in ('setUp', 'rollback', 'owner', 'accept', 'bpr', 'parents', 'fetch', 'positive', 'start',
            'scopes', 'reads', 'prepare_dbm', 'finish', 'publication_opening', 'prepare', 'binding'):
        locals()[name] = getattr(fixtures.ScopedViewTests, name)
    row = staticmethod(fixtures.ScopedViewTests.row)

    def test_postgresql_prefix_predicate_matches_python_guard_and_actual_database(self):
        from django.db import connection
        from unittest.mock import patch
        from mta.runtime import scope_runtime_reports
        module = import_module('mta.runtime.migrations.0219_scope_read_test_database_casefold')
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            actual = cursor.fetchone()[0]
            self.assertTrue(actual.lower().startswith('vftest_fresh_'))
            for name, allowed in ((actual, True), ('VFTEST_Fresh_Case', True), ('vftest_fresh_case', True),
                    ('vectorflow_mta', False), ('vftest_fresh', False), ('vftest_freshness_case', False),
                    ('other_vftest_fresh_case', False)):
                cursor.execute('SELECT NOT (' + module.PREDICATE.replace('current_database()', '%s') + ')', [name])
                self.assertIs(cursor.fetchone()[0], allowed)
                with patch('django.db.connection') as mock:
                    mock.cursor.return_value.__enter__.return_value.fetchone.return_value = (name,)
                    if allowed: scope_runtime_reports.require_test_database()
                    else:
                        with self.assertRaises(ValueError): scope_runtime_reports.require_test_database()

    def test_actual_reference_blocks_downgrade_and_original_guard_body_is_denied(self):
        from django.db import connection, transaction, DatabaseError
        from mta.presentation import scoped_view
        from mta.presentation.context import PublicationUnavailable
        self.start(); view = self.prepare()
        module = import_module('mta.runtime.migrations.0219_scope_read_test_database_casefold')
        with self.assertRaisesRegex(DatabaseError, 'compatible forward release'), transaction.atomic():
            with connection.cursor() as cursor: cursor.execute(module.REVERSE)
        self.assertEqual(self.binding(view).read_identity, view.read_identity)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(module.REPLACE + ' ' + module.OLD_DEFINITION)
            with self.assertRaisesRegex(PublicationUnavailable, 'guard_body_differs'): scoped_view.verify_guards()
            transaction.set_rollback(True)
        scoped_view.verify_guards()
