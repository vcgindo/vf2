"""Digest reuse never replaces current readiness or an unqualified schema read."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from contextlib import ExitStack
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from django.db import DatabaseError
from mta.presentation import schema_reuse as reuse


class SchemaReuseTests(unittest.TestCase):
    def setUp(self):
        reuse.clear()
        self.addCleanup(reuse.clear)
        self.database = NS(connection=object(), in_atomic_block=True, get_autocommit=lambda: False)
        self.cursor = NS(db=self.database)
        self.ticket = dict(database=self.database, physical=self.database.connection,
            pid=os.getpid(), wal='wal', session='session', key=('catalogue', 'settings', 'migrations'))
        self.function = Mock(return_value='digest')
        self.read = reuse.schema_read(self.function)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.session = self.stack.enter_context(patch.object(reuse, '_session',
            return_value=('wal', 'session', ('repeatable read', 'on'))))

    def activate(self):
        token = reuse._active.set(self.ticket)
        self.addCleanup(reuse._active.reset, token)

    def test_offline_calls_always_verify(self):
        self.read(self.cursor)
        self.read(self.cursor)
        self.assertEqual(self.function.call_count, 2)
        self.session.assert_not_called()

    def test_qualified_hit_reuses_only_digest_and_checks_both_sides(self):
        self.activate()
        self.assertEqual(self.read(self.cursor), 'digest')
        self.assertEqual(self.read(self.cursor), 'digest')
        self.assertEqual(self.function.call_count, 1)
        self.assertEqual(self.session.call_count, 4)

    def test_security_digest_keeps_distinct_role_rosters(self):
        self.activate()
        for roles in (('owner', 'installer', 'runtime'), ('owner', 'installer', 'another')):
            self.read(self.cursor, roles)
            self.read(self.cursor, roles)
        self.assertEqual(self.function.call_count, 2)

    def test_changed_catalogue_settings_or_migrations_get_full_digest(self):
        self.activate()
        self.read(self.cursor)
        for key in (('new catalogue', 'settings', 'migrations'),
                    ('catalogue', 'new settings', 'migrations'),
                    ('catalogue', 'settings', 'new migrations')):
            self.ticket['key'] = key
            self.read(self.cursor)
        self.assertEqual(self.function.call_count, 4)

    def test_concurrent_write_before_hit_falls_back_without_filling(self):
        self.activate()
        self.read(self.cursor)
        self.session.return_value = ('new WAL', 'session', ('repeatable read', 'on'))
        self.read(self.cursor)
        self.read(self.cursor)
        self.assertEqual(self.function.call_count, 3)

    def test_concurrent_write_during_hit_runs_original_check(self):
        self.activate()
        self.read(self.cursor)
        self.session.side_effect = [('wal', 'session', ('repeatable read', 'on')),
                                    ('changed', 'session', ('repeatable read', 'on'))]
        self.read(self.cursor)
        self.assertEqual(self.function.call_count, 2)

    def test_changed_wal_during_fill_is_not_cached(self):
        self.activate()
        self.session.side_effect = [('wal', 'session', ('repeatable read', 'on')),
                                    ('changed', 'session', ('repeatable read', 'on'))]
        self.read(self.cursor)
        self.assertEqual(reuse._local.entries, {})

    def test_wrong_cursor_connection_process_snapshot_or_settings_bypasses(self):
        self.activate()
        self.read(NS(db=NS()))
        old = self.database.connection
        self.database.connection = object()
        self.read(self.cursor)
        self.database.connection = old
        with patch.object(reuse.os, 'getpid', return_value=self.ticket['pid'] + 1):
            self.read(self.cursor)
        for state in (('wal', 'changed settings', ('repeatable read', 'on')),
                      ('wal', 'session', ('read committed', 'on')),
                      ('wal', 'session', ('repeatable read', 'off'))):
            self.session.return_value = state
            self.read(self.cursor)
        self.assertEqual(self.function.call_count, 6)
        self.assertEqual(reuse._local.entries, {})

    def test_failed_digest_clears_entries(self):
        self.activate()
        self.function.side_effect = ValueError('schema unavailable')
        with self.assertRaisesRegex(ValueError, 'schema unavailable'):
            self.read(self.cursor)
        self.assertEqual(reuse._local.entries, {})

    def test_four_entry_bound(self):
        self.activate()
        for number in range(8):
            self.ticket['key'] = (number,)
            self.read(self.cursor)
            self.assertLessEqual(len(reuse._local.entries), 4)

    def test_verification_ticket_lifetime_and_unsupported_wal_fallback(self):
        from mta.presentation import admission, request_scope
        database = NS(vendor='postgresql', in_atomic_block=False, get_autocommit=lambda: True,
                      connection=NS(closed=False))
        with patch.object(reuse, 'connections', {'default': database}), \
                patch.object(admission, '_admitted', 'admitted'), \
                patch.object(reuse, '_ticket', return_value=self.ticket) as capture, \
                request_scope.read_request('/api/mta/DBMData'):
            with reuse.verification():
                self.assertIs(reuse._active.get(), self.ticket)
            self.assertIsNone(reuse._active.get())
            capture.side_effect = DatabaseError('WAL not supported')
            with reuse.verification():
                self.assertIsNone(reuse._active.get())
            capture.side_effect = None
            with self.assertRaisesRegex(ValueError, 'failed readiness'):
                with reuse.verification():
                    raise ValueError('failed readiness')
            self.assertIsNone(reuse._active.get())

    def test_catalogue_roster_includes_shared_and_deparser_dependencies(self):
        self.assertTrue({'pg_auth_members', 'pg_database', 'pg_range', 'pg_ts_config',
                         'pg_ts_dict', 'pg_depend', 'pg_attribute', 'pg_rewrite'} <= set(reuse.CATALOGUES))
        self.assertEqual(len(reuse.CATALOGUES), len(set(reuse.CATALOGUES)))
        self.assertNotIn('mta_state', reuse.VERSION_SQL)


if __name__ == '__main__':
    unittest.main()
