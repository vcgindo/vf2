"""Private current-write dispatch; no database, day or service execution."""
from importlib import import_module
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.application import accepted_inputs
from mta.runtime import accepted_current_write as runtime

migration = import_module('mta.runtime.migrations.0244_accepted_current_write_context')


class AcceptedCurrentMigrationTests(unittest.TestCase):
    def test_exact_bodies_are_preserved_after_owner_transaction_dispatch(self):
        self.assertEqual({entry[0] for entry in migration.ORIGINALS}, set(runtime.GUARDS))
        for name, original, delimiter, kind in migration.ORIGINALS:
            with self.subTest(function=name):
                result = migration.admitted_definition(original, delimiter, kind, "private'owner")
                original_body = original.split(delimiter)[1]
                new_body = result.split(delimiter)[1]
                prefix, suffix = original_body.split('\nBEGIN\n', 1)
                self.assertTrue(new_body.startswith(prefix + '\nBEGIN\n IF '))
                self.assertTrue(new_body.endswith(suffix))
                self.assertIn("CURRENT_USER='private''owner'", result)
                self.assertIn('pg_catalog.txid_current()::text', result)
                self.assertIn("pg_catalog.current_setting('fresh.accepted_current_run',true)", result)
                self.assertEqual(original.split(delimiter)[0], result.split(delimiter)[0])
                dispatch = new_body[len(prefix):].split(' END IF;\n', 1)[0]
                self.assertNotIn('SELECT ', dispatch)
                self.assertNotIn('NEW.source_id', dispatch)
                self.assertNotIn('NEW.ordinal', dispatch)
                if kind == 'current':
                    self.assertIn("TG_ARGV[0]='current'", dispatch)
                if kind == 'row':
                    self.assertIn("TG_OP<>'TRUNCATE'", dispatch)

    def test_forward_and_reverse_require_exact_predecessors(self):
        for reverse in (False, True):
            owner = 'guard_owner'
            current = []
            expected_writes = []
            for _, original, delimiter, kind in migration.ORIGINALS:
                admitted = migration.admitted_definition(original, delimiter, kind, owner)
                before, after = (admitted, original) if reverse else (original, admitted)
                current.append((before.split(delimiter)[1], owner))
                expected_writes.append(after)
            cursor = MagicMock()
            cursor.fetchone.side_effect = current
            connection = MagicMock()
            connection.cursor.return_value.__enter__.return_value = cursor
            migration.replace(SimpleNamespace(connection=connection), reverse=reverse)
            self.assertEqual([call.args[0] for call in cursor.execute.call_args_list[1::2]], expected_writes)
        cursor.fetchone.side_effect = None
        cursor.fetchone.return_value = ('unexpected-body', owner)
        with self.assertRaisesRegex(ValueError, 'predecessor differs'):
            migration.replace(SimpleNamespace(connection=connection))


class AcceptedCurrentContextTests(unittest.TestCase):
    def setUp(self):
        self.run = SimpleNamespace(pk=uuid4())
        self.source = SimpleNamespace(pk=17)
        self.context = SimpleNamespace(native_daily=True, identity=str(self.run.pk), accepted_inputs=None)
        accepted_inputs._complete(self.context)
        self.cursor = MagicMock()
        cursor_context = MagicMock()
        cursor_context.__enter__.return_value = self.cursor
        self.db = SimpleNamespace(vendor='postgresql', in_atomic_block=True,
            needs_rollback=False, closed_in_transaction=False, cursor=lambda: cursor_context)
        self.patch = patch.object(runtime, 'connection', self.db)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def state(self, *, phase=None, scoped=False):
        return ('DAILY_CHAIN', 'RUNNING',
            'CAPTURED' if phase in ('PRE_BPR', 'BPR', 'DBM') else 'CONSUMED',
            self.source.pk, 'fresh-production-mdm-source-v1', str(self.run.pk),
            str(self.run.pk) if phase in (None, 'PRE_BPR') else None, phase, scoped)

    def test_full_context_validates_once_and_restores_transaction_markers(self):
        self.cursor.fetchone.side_effect = [(True,), self.state(), ('PENDING', True), ('123', 'old-xid', 'old-run')]
        with accepted_inputs.consume(self.context):
            with runtime._accepted_current_write(self.run, self.source):
                pass
        self.assertEqual(self.cursor.fetchone.call_count, 4)
        calls = self.cursor.execute.call_args_list
        self.assertEqual(calls[-2].args[1], [runtime.SETTINGS[0], '123', runtime.SETTINGS[1], str(self.run.pk)])
        self.assertEqual(calls[-1].args[1], [runtime.SETTINGS[0], 'old-xid', runtime.SETTINGS[1], 'old-run'])
        self.assertIn('FOR UPDATE OF R,C,S', calls[1].args[0])
        self.assertIn('FOR UPDATE OF P', calls[2].args[0])
        self.assertTrue(all('true)' in call.args[0] for call in calls[-2:]))

    def test_each_scoped_phase_reuses_its_pending_command_not_full_receipt(self):
        for phase in ('PRE_BPR', 'BPR', 'DBM', 'DAY_FINAL'):
            self.cursor.reset_mock()
            self.cursor.fetchone.side_effect = [(True,), self.state(phase=phase, scoped=True), ('123', None, None)]
            with accepted_inputs.consume(self.context), runtime._accepted_current_write(self.run, self.source):
                pass
            self.assertEqual(self.cursor.fetchone.call_count, 3)
            self.assertFalse(any('valid_closing_projection' in call.args[0]
                                 for call in self.cursor.execute.call_args_list))

    def test_public_boolean_missing_or_foreign_admission_cannot_enable_context(self):
        for admitted in (None, True, SimpleNamespace(owner=str(self.run.pk))):
            token = accepted_inputs._current.set(admitted)
            try:
                with self.assertRaisesRegex(ValueError, 'joint daily intake owner'):
                    with runtime._accepted_current_write(self.run, self.source):
                        self.fail('must not enter')
            finally:
                accepted_inputs._current.reset(token)
        self.cursor.execute.assert_not_called()
        with accepted_inputs.consume(self.context):
            with self.assertRaisesRegex(ValueError, 'joint daily intake owner'):
                with runtime._accepted_current_write(SimpleNamespace(pk=uuid4()), self.source):
                    self.fail('must not enter')

    def test_non_owner_role_and_invalid_pending_command_are_denied(self):
        for answers, message in (([(False,)], 'guard owner role'),
                ([(True,), self.state(phase=None, scoped=True)], 'pending producing phase'),
                ([(True,), self.state(), ('SEALED', True)], 'pending closing receipt')):
            self.cursor.reset_mock()
            self.cursor.fetchone.side_effect = answers
            with accepted_inputs.consume(self.context):
                with self.assertRaisesRegex(ValueError, message):
                    with runtime._accepted_current_write(self.run, self.source):
                        self.fail('must not enter')
            self.assertFalse(any('set_config(' in call.args[0] for call in self.cursor.execute.call_args_list))

    def test_transaction_is_required_and_failed_transaction_does_not_mask_error(self):
        self.db.in_atomic_block = False
        with accepted_inputs.consume(self.context):
            with self.assertRaisesRegex(ValueError, 'PostgreSQL transaction'):
                with runtime._accepted_current_write(self.run, self.source):
                    self.fail('must not enter')
        self.cursor.execute.assert_not_called()
        self.db.in_atomic_block = True
        self.cursor.fetchone.side_effect = [(True,), self.state(), ('PENDING', True), ('123', None, None)]
        with accepted_inputs.consume(self.context):
            with self.assertRaisesRegex(RuntimeError, 'original error'):
                with runtime._accepted_current_write(self.run, self.source):
                    self.db.needs_rollback = True
                    raise RuntimeError('original error')
        self.assertEqual(sum('set_config(' in call.args[0] for call in self.cursor.execute.call_args_list), 1)

    def test_raw_database_failures_on_entry_and_body_mark_rollback(self):
        for entering in (True, False):
            with self.subTest(entering=entering):
                self.db.needs_rollback = False
                self.cursor.reset_mock()
                self.cursor.fetchone.side_effect = [(True,), self.state(), ('PENDING', True), ('123', None, None)]
                original = runtime.DatabaseError('original raw SQL error')
                self.cursor.execute.side_effect = original if entering else None
                def mark_rollback(value):
                    self.assertTrue(value)
                    self.db.needs_rollback = value
                with accepted_inputs.consume(self.context), \
                        patch.object(runtime.transaction, 'set_rollback', side_effect=mark_rollback) as rollback:
                    with self.assertRaises(runtime.DatabaseError) as raised:
                        with runtime._accepted_current_write(self.run, self.source):
                            raise original
                    self.assertIs(raised.exception, original)
                    self.assertTrue(self.db.needs_rollback)
                    self.assertGreaterEqual(rollback.call_count, 1)
                self.assertEqual(sum('set_config(' in call.args[0]
                    for call in self.cursor.execute.call_args_list), 0 if entering else 1)
