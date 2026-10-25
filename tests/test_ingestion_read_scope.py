"""Coverage verification is shared only within one physical read connection."""
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from mta.presentation.request_scope import read_request, metadata_operation
from mta.runtime import ingestion_ownership as module


class Physical:
    closed = False


class Database:
    def __init__(self): self.connection = Physical()

    @contextmanager
    def cursor(self): yield SimpleNamespace(db=self)


class IngestionReadScopeTests(unittest.TestCase):
    def test_same_connection_reuses_but_each_request_and_startup_revalidates(self):
        database = Database()
        with patch.object(module, '_verify_guard_coverage') as verify:
            with read_request('/api/GetPlanningDataCount'):
                module.require_guard_coverage(SimpleNamespace(db=database))
                module.require_guard_coverage(SimpleNamespace(db=database))
            self.assertEqual(verify.call_count, 1)
            with read_request('/api/GetPlanningDataCount'):
                module.require_guard_coverage(SimpleNamespace(db=database))
            self.assertEqual(verify.call_count, 2)
            with metadata_operation():
                module.require_guard_coverage(SimpleNamespace(db=database))
                module.require_guard_coverage(SimpleNamespace(db=database))
            self.assertEqual(verify.call_count, 4)

    def test_other_reopened_and_closed_connections_do_not_reuse_verification(self):
        database = Database(); other = Database()
        with patch.object(module, '_verify_guard_coverage') as verify, read_request('/api/GetBPRData'):
            module.require_guard_coverage(SimpleNamespace(db=database))
            module.require_guard_coverage(SimpleNamespace(db=other))
            database.connection = Physical()
            module.require_guard_coverage(SimpleNamespace(db=database))
            database.connection.closed = True
            module.require_guard_coverage(SimpleNamespace(db=database))
            self.assertEqual(verify.call_count, 4)

    def test_failed_guard_check_is_never_cached(self):
        database = Database()
        with patch.object(module, '_verify_guard_coverage', side_effect=[ValueError('guard changed'), None]) as verify, \
                read_request('/api/GetBPRData'):
            with self.assertRaisesRegex(ValueError, 'guard changed'):
                module.require_guard_coverage(SimpleNamespace(db=database))
            module.require_guard_coverage(SimpleNamespace(db=database))
            module.require_guard_coverage(SimpleNamespace(db=database))
            self.assertEqual(verify.call_count, 2)

    def test_writer_offline_and_unknown_cursor_keep_original_validation(self):
        database = Database(); cursor = SimpleNamespace(db=database)
        with patch.object(module, '_verify_guard_coverage') as verify:
            with read_request('/api/AddRemark'):
                module.require_guard_coverage(cursor); module.require_guard_coverage(cursor)
            module.require_guard_coverage(cursor)
            self.assertEqual(verify.call_count, 3)
            with read_request('/api/GetBPRData'):
                module.require_guard_coverage(object()); module.require_guard_coverage(object())
            self.assertEqual(verify.call_count, 5)


class StartupGuardScopeTests(unittest.TestCase):
    def setUp(self):
        self.database = Database()
        self.cursor = SimpleNamespace(db=self.database)
        self.enterContext(patch('django.db.connection', self.database))
        self.enterContext(patch('django.db.connections', {'default': self.database}))
        self.stamp = self.enterContext(patch('mta.presentation.identity_reuse.stamp',
                                            return_value=('snapshot', 'role', 'settings')))
        self.verify = self.enterContext(patch.object(module, '_verify_guard_coverage'))

    def check(self):
        return module.require_guard_coverage(self.cursor)

    def test_success_reused_only_within_one_startup_and_live_stamp(self):
        with metadata_operation():
            self.check(); self.check()
            self.assertEqual(self.verify.call_count, 1)
            for stamp in (('new snapshot', 'role', 'settings'),
                          ('new snapshot', 'new role', 'settings'),
                          ('new snapshot', 'new role', 'new settings')):
                self.stamp.return_value = stamp
                self.check(); self.check()
            self.assertEqual(self.verify.call_count, 4)
        with metadata_operation():
            self.check()
        self.assertEqual(self.verify.call_count, 5)
        self.check(); self.check()
        self.assertEqual(self.verify.call_count, 7)

    def test_transaction_or_unusable_stamp_never_seeds_startup_cache(self):
        with metadata_operation():
            self.stamp.return_value = None
            self.check(); self.check()
            self.assertEqual(self.verify.call_count, 2)
            self.stamp.return_value = ('autocommit snapshot',)
            self.check(); self.check()
            self.assertEqual(self.verify.call_count, 3)

    def test_changed_stamp_during_fill_is_not_reused(self):
        self.stamp.side_effect = [('before',), ('after',), ('before',), ('before',), ('before',)]
        with metadata_operation():
            self.check(); self.check(); self.check()
        self.assertEqual(self.verify.call_count, 2)

    def test_failures_are_never_cached(self):
        self.verify.side_effect = [ValueError('guard changed'), ValueError('guard changed'), None]
        with metadata_operation():
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'guard changed'):
                    self.check()
            self.check(); self.check()
        self.assertEqual(self.verify.call_count, 3)

    def test_other_reopened_and_closed_connections_do_not_share_entry(self):
        with metadata_operation():
            self.check(); self.check()
            self.database.connection = Physical()
            self.check(); self.check()
            self.database.connection.closed = True
            self.check(); self.check()
            other = SimpleNamespace(db=Database())
            module.require_guard_coverage(other); module.require_guard_coverage(other)
        self.assertEqual(self.verify.call_count, 6)

    def test_connection_changed_during_fill_is_not_cached(self):
        def reconnect(cursor):
            self.database.connection = Physical()
        self.verify.side_effect = reconnect
        with metadata_operation():
            self.check(); self.check()
        self.assertEqual(self.verify.call_count, 2)
