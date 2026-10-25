"""Accepted phase reuse stays inside one existing read traversal."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
import unittest
from uuid import uuid4
from unittest.mock import patch
from mta.presentation import request_scope, scoped_dbm_stop, scoped_dbm_view
from test_remark_validation_scope import Database


class ScopedPhaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.database = Database()
        self.connection = patch('django.db.connection', self.database)
        self.connection.start()
        self.addCleanup(self.connection.stop)
        self.phase_id = uuid4()

    def test_view_and_dbm_share_uuid_and_text_only_inside_one_traversal(self):
        with patch('mta.runtime.scoped_pick_files._accepted', side_effect=lambda *args: object()) as verify:
            with request_scope.remark_validation():
                with request_scope.validation_reads():
                    before = scoped_dbm_view._accepted(str(self.phase_id), 'digest')
                    self.assertIs(scoped_dbm_stop._accepted(self.phase_id, 'digest'), before)
                    self.assertEqual(verify.call_count, 1)
                self.database.execute('UPDATE command SET revision=2')
                with request_scope.validation_reads():
                    after = scoped_dbm_stop._accepted(self.phase_id, 'digest')
                    self.assertIsNot(after, before)
                    self.assertIs(scoped_dbm_view._accepted(str(self.phase_id), 'digest'), after)
                    self.assertEqual(verify.call_count, 2)
            self.assertEqual(verify.call_args.args, (self.phase_id, 'digest'))

    def test_digest_owner_and_physical_connection_are_distinct(self):
        with patch('mta.runtime.scoped_pick_files._accepted', side_effect=lambda *args: object()) as verify:
            with request_scope.remark_validation(), request_scope.validation_reads():
                original = scoped_dbm_view._accepted(self.phase_id, 'digest')
                self.assertIsNot(scoped_dbm_view._accepted(self.phase_id, 'changed'), original)
                self.assertIsNot(scoped_dbm_view._accepted(uuid4(), 'digest'), original)
                self.database.connection = type('Physical', (), {'closed': False})()
                self.assertIsNot(scoped_dbm_stop._accepted(self.phase_id, 'digest'), original)
                self.assertEqual(verify.call_count, 4)

    def test_failed_validation_is_retried_and_invalid_ids_never_resolve(self):
        with patch('mta.runtime.scoped_pick_files._accepted', side_effect=ValueError('owner changed')) as verify:
            with request_scope.remark_validation(), request_scope.validation_reads():
                for phase_id in (self.phase_id, str(self.phase_id)):
                    with self.assertRaisesRegex(ValueError, 'owner changed'):
                        scoped_dbm_view._accepted(phase_id, 'digest')
                self.assertEqual(verify.call_count, 2)
                for phase_id in ('not-an-id', None, 1):
                    with self.assertRaises(ValueError):
                        scoped_dbm_stop._accepted(phase_id, 'digest')
                self.assertEqual(verify.call_count, 2)

    def test_offline_and_separate_requests_never_share_acceptance(self):
        with patch('mta.runtime.scoped_pick_files._accepted', side_effect=lambda *args: object()) as verify:
            scoped_dbm_view._accepted(str(self.phase_id), 'digest')
            scoped_dbm_stop._accepted(self.phase_id, 'digest')
            self.assertEqual(verify.call_count, 2)
            previous = None
            for _ in range(2):
                with request_scope.read_request('/api/DBMData'):
                    current = scoped_dbm_view._accepted(str(self.phase_id), 'digest')
                    self.assertIsNot(current, previous)
                    self.assertIs(scoped_dbm_stop._accepted(self.phase_id, 'digest'), current)
                    previous = current
            self.assertEqual(verify.call_count, 4)

    def test_shared_reader_cannot_write_inside_validation(self):
        with patch('mta.runtime.scoped_pick_files._accepted',
                   side_effect=lambda *args: self.database.execute('UPDATE phase SET digest=1')):
            with request_scope.remark_validation(), request_scope.validation_reads():
                with self.assertRaisesRegex(ValueError, 'SQL write'):
                    scoped_dbm_view._accepted(self.phase_id, 'digest')
        self.assertEqual(self.database.executed, [])
