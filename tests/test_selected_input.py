"""Input borrowing cannot survive a write pass or hide an ordinary failure."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from contextlib import ExitStack
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from uuid import uuid4

from mta.presentation import selected_input as inputs, request_scope


class SelectedInputTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.database = NS(vendor='postgresql', connection=NS(closed=False))
        self.stack.enter_context(patch.object(inputs, 'connections', {'default': self.database}))
        self.original_stamp = inputs._stamp
        self.stamp = self.stack.enter_context(patch.object(inputs, '_stamp', return_value=('unchanged',)))
        self.reader = self.stack.enter_context(patch('mta.runtime.input_reader.read_input', side_effect=self.read))
        self.parent = self.make_run()
        self.current = self.make_run(self.parent.pk)
        self.raw = dict(lineage={'run_id': str(self.parent.pk)}, initialization_binding={'id': 'owner'},
                        profile={'nested': [1, None, 1]}, scope_request={'scope': 'UptoDBM'})

    def make_run(self, parent=None):
        from mta.runtime.models import CalculationRun
        run = CalculationRun(id=uuid4(), predecessor_id=parent, kind='DAILY_CHAIN', status='RUNNING',
            input_payload={'schema': 'fresh-daily-input-manifest-v3'}, input_digest='input',
            input_manifest_digest='manifest')
        run._state.db = 'default'
        run._state.adding = False
        return run

    def read(self, run, *, components):
        return deepcopy({k: v for k, v in self.raw.items() if k in components})

    def scope(self):
        token = request_scope._validation.set({})
        self.stack.callback(request_scope._validation.reset, token)
        return inputs.selection(self.current.pk)

    def test_one_current_read_and_separate_predecessor_with_independent_copies(self):
        with self.scope():
            first = inputs.read_input(self.current, components=('profile',))
            first['profile']['nested'].clear()
            self.assertEqual(inputs.read_input(self.current, components=('profile',)), {'profile': self.raw['profile']})
            owner = inputs.physical(self.current)
            owner.input_payload['changed'] = True
            self.assertNotIn('changed', inputs.physical(self.current).input_payload)
            inputs.read_input(self.parent, components=('initialization_binding',))
            inputs.read_input(self.parent, components=('profile',))
            self.assertEqual([c.kwargs['components'] for c in self.reader.call_args_list], [inputs.CURRENT, inputs.PREDECESSOR])
        self.assertIsNone(inputs._active.get())

    def test_each_selection_revalidates_after_action_boundary(self):
        with self.scope():
            inputs.read_input(self.current, components=('profile',))
        self.raw['profile'] = {'new': True}
        with self.scope():
            self.assertEqual(inputs.read_input(self.current, components=('profile',)), {'profile': {'new': True}})
        self.assertEqual(self.reader.call_count, 2)

    def test_changed_stamp_or_owner_metadata_forces_complete_read(self):
        with self.scope():
            inputs.read_input(self.current, components=('profile',))
            self.stamp.return_value = ('write',)
            inputs.read_input(self.current, components=('profile',))
            self.current.input_payload['new'] = 1
            inputs.read_input(self.current, components=('profile',))
        self.assertEqual(self.reader.call_count, 3)

    def test_write_during_copy_uses_original_requested_reader(self):
        with self.scope():
            inputs.read_input(self.current, components=('profile',))
            self.reader.reset_mock()
            self.stamp.side_effect = [('unchanged',), ('write',)]
            inputs.read_input(self.current, components=('profile',))
        self.assertEqual(self.reader.call_args.kwargs['components'], ('profile',))

    def test_eager_failure_preserves_original_component_failure_boundary(self):
        def read(run, *, components):
            if 'profile' in components:
                raise ValueError('actual profile error')
            return {'lineage': {'valid': True}}
        self.reader.side_effect = read
        with self.scope():
            self.assertEqual(inputs.read_input(self.current, components=('lineage',)), {'lineage': {'valid': True}})
            with self.assertRaisesRegex(ValueError, 'actual profile error'):
                inputs.read_input(self.current, components=('profile',))
        self.assertEqual([c.kwargs['components'] for c in self.reader.call_args_list], [inputs.CURRENT, ('lineage',), ('profile',)])

    def test_partial_offline_foreign_and_unsupported_reads_keep_original_path(self):
        with inputs.selection(self.current.pk):
            inputs.read_input(self.current, components=('profile',))
            self.assertIsNone(inputs._active.get())
        with self.scope():
            inputs.read_input(self.make_run(), components=('profile',))
            inputs.read_input(self.current, components=('opening',))
        self.assertEqual([c.kwargs['components'] for c in self.reader.call_args_list], [('profile',), ('profile',), ('opening',)])

    def test_original_physical_reader_runs_for_standalone_metadata(self):
        with patch('mta.runtime.input_storage.read_input') as read:
            self.assertIs(inputs.physical(self.current), self.current)
            read.assert_called_once_with(self.current, components=())

    def test_streaming_and_large_values_are_not_retained(self):
        from mta.row_sequences import RecordRows
        rows = RecordRows(1, lambda: (_ for _ in ()).throw(AssertionError('must not consume')))
        self.assertFalse(inputs._finite(rows))
        self.assertFalse(inputs._finite({'value': 'x' * 300000}))
        self.assertTrue(inputs._finite({'value': [None, 1, 1, self.current.pk]}))

    def test_scalar_type_and_representation_changes_do_not_reuse_metadata(self):
        from decimal import Decimal
        for old, new in ((True, 1), (1, 1.0), (0.0, -0.0), (Decimal('1.0'), Decimal('1.00'))):
            with self.subTest(old=old, new=new), self.scope():
                self.current.input_payload['typed'] = old
                inputs.read_input(self.current, components=('profile',))
                n = self.reader.call_count
                self.current.input_payload['typed'] = new
                inputs.read_input(self.current, components=('profile',))
                self.assertEqual(self.reader.call_count, n + 1)

    def test_nested_selection_cannot_borrow_outer_inputs(self):
        with self.scope():
            inputs.read_input(self.current, components=('profile',))
            with inputs.selection(self.current.pk):
                self.assertIsNone(inputs._active.get())
                inputs.read_input(self.current, components=('profile',))
            inputs.read_input(self.current, components=('profile',))
        self.assertEqual([c.kwargs['components'] for c in self.reader.call_args_list], [inputs.CURRENT, ('profile',)])

    def test_physical_carrier_excludes_related_objects_and_parent_bound_is_two(self):
        self.current._state.fields_cache['unrelated'] = object()
        with self.scope():
            owner = inputs.physical(self.current)
            self.assertEqual(owner._state.fields_cache, {})
            for _ in range(3):
                parent = self.make_run()
                self.current.predecessor_id = parent.pk
                inputs.read_input(self.current, components=('profile',))
                inputs.read_input(parent, components=('profile',))
                self.assertEqual(set(inputs._active.get()['entries']), {str(self.current.pk), str(parent.pk)})

    def test_real_stamp_checks_pass_connection_and_isolation(self):
        from unittest.mock import MagicMock
        cursor = MagicMock()
        cursor.fetchone.return_value = ('snapshot', 'wal', 1, 'db', 'session', 'user', 'read committed')
        self.database.cursor = MagicMock()
        self.database.cursor.return_value.__enter__.return_value = cursor
        with self.scope():
            context = inputs._active.get()
            self.assertEqual(self.original_stamp(context), cursor.fetchone.return_value)
            self.database.connection = NS(closed=False)
            self.assertIsNone(self.original_stamp(context))
            self.database.connection = context['physical']
            cursor.fetchone.return_value = ('snapshot', 'wal', 1, 'db', 'session', 'user', 'repeatable read')
            self.assertIsNone(self.original_stamp(context))
            token = request_scope._validation.set({})
            try:self.assertIsNone(self.original_stamp(context))
            finally:request_scope._validation.reset(token)
