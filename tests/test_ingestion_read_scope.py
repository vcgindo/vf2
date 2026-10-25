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
