"""HTTP preflight may reuse certified metadata, never handler/action authority."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from django.test import override_settings
from mta.presentation import admission, identity_reuse, request_scope, scoped_selection


class AdmissionPreflightTests(TestCase):
    def setUp(self):
        self.connection = SimpleNamespace(in_atomic_block=False, get_autocommit=lambda: True)
        self.enterContext(patch('django.db.connection', self.connection))
        self.enterContext(patch('mta.presentation.installation_metadata.publication_configured', return_value=True))
        self.enterContext(patch.object(admission.connections, 'close_all'))
        self.enterContext(override_settings(VF_MTA_PHASE_SELECTION_FILE='pinned.json',
            VF_MTA_PHASE_SELECTION={'schema': scoped_selection.DBM_SCHEMA}))
        self.addCleanup(setattr, admission, '_admitted', admission._admitted)
        admission._admitted = 'accepted'
        identity_reuse.clear()
        self.addCleanup(identity_reuse.clear)
        self.stamp = self.enterContext(patch.object(identity_reuse, 'stamp', return_value=('snapshot',)))
        self.audit = Mock(return_value={'cut': {'master': 3}})
        self.ready = identity_reuse.certified_readiness(self.audit)
        self.app = object.__new__(admission.AdmittedApplication)
        self.app.application = Mock(return_value=[b'unchanged'])

    def dispatch(self):
        return self.app({'PATH_INFO': '/api/mta/DBMApplySelectedNorms'}, Mock())

    def preflight(self):
        with request_scope.admission_preflight(enabled=True):
            return self.ready('owner')

    def test_only_admission_sees_flag_and_response_is_unchanged(self):
        observed = []
        def binding():
            observed.append(('binding', request_scope.in_admission_preflight(), request_scope.in_read_request()))
            return None, 'accepted'
        def handler(*args):
            observed.append(('handler', request_scope.in_admission_preflight(), request_scope.in_read_request()))
            return [b'unchanged']
        self.app.application.side_effect = handler
        with patch.object(admission, 'binding', side_effect=binding):
            self.assertEqual(self.dispatch(), [b'unchanged'])
        self.assertEqual(observed, [('binding', True, False), ('handler', False, False)])

    def test_failed_admission_resets_context_and_never_calls_handler(self):
        for error in (ValueError('changed'), admission.OperationalError('unavailable')):
            admission._admitted = 'accepted'
            with patch.object(admission, 'binding', side_effect=error):
                self.assertIn(b'publication_not_admitted', b''.join(self.dispatch()))
            self.assertFalse(request_scope.in_admission_preflight())
            self.app.application.assert_not_called()
            self.assertEqual(admission._admitted, 'accepted' if isinstance(error, admission.OperationalError) else None)

    def test_other_selection_modes_keep_original_admission(self):
        for path, anchor in [('', None), ('bpr.json', {'schema': scoped_selection.SCHEMA}),
                             ('bad.json', None)]:
            with self.subTest(path=path), override_settings(VF_MTA_PHASE_SELECTION_FILE=path,
                    VF_MTA_PHASE_SELECTION=anchor), patch.object(admission, 'require_admission',
                    side_effect=lambda: self.assertFalse(request_scope.in_admission_preflight())) as check:
                self.dispatch()
                check.assert_called_once()

    def test_atomic_or_non_autocommit_preflight_does_not_enable_reuse(self):
        for atomic, autocommit in [(True, False), (False, False)]:
            self.connection.in_atomic_block = atomic
            self.connection.get_autocommit = lambda: autocommit
            with request_scope.admission_preflight(enabled=True):
                self.assertFalse(request_scope.in_admission_preflight())
                self.ready('owner'); self.ready('owner')
        self.assertEqual(self.audit.call_count, 4)
        self.stamp.assert_not_called()

    def test_read_can_warm_preflight_but_handler_still_revalidates(self):
        with request_scope.read_request('/api/mta/DBMData'):
            self.ready('owner')
        self.preflight()['cut']['master'] = 99
        self.assertEqual(self.preflight()['cut']['master'], 3)
        self.assertEqual(self.audit.call_count, 1)
        self.ready('owner')
        self.assertEqual(self.audit.call_count, 2)

    def test_preflight_does_not_enable_native_identity_or_graph_cache(self):
        native = Mock(return_value={})
        read = identity_reuse.native_identity(native)
        graph = Mock(return_value={})
        cached_graph = request_scope.once_per_request(graph)
        with request_scope.admission_preflight(enabled=True):
            read(None); read(None)
            cached_graph(); cached_graph()
            self.connection.in_atomic_block = True
            with self.assertRaisesRegex(ValueError, 'own locked transaction'):
                with request_scope.remark_validation():
                    self.fail('preflight must not reach the writer')
        self.assertEqual((native.call_count, graph.call_count), (2, 2))

    def test_changed_snapshot_connection_or_release_revalidates_preflight(self):
        self.preflight()
        for changed in ('committed action', 'guard/role change', 'new connection'):
            self.stamp.return_value = (changed,)
            self.preflight()
        with patch.dict(os.environ, VF_NATIVE_RELEASE_SHA256='other'):
            self.preflight()
        self.assertEqual(self.audit.call_count, 5)

    def test_cache_hit_changed_during_copy_falls_back_without_retaining_value(self):
        self.preflight()
        self.stamp.side_effect = [('snapshot',), ('new snapshot',)]
        self.audit.return_value = {'cut': {'master': 4}}
        self.assertEqual(self.preflight()['cut']['master'], 4)
        self.assertEqual(self.audit.call_count, 2)
        self.assertFalse(identity_reuse._entries)

    def test_preflight_cannot_override_unadmitted_or_transaction_stamp(self):
        self.preflight()
        admission._admitted = None
        self.preflight()
        admission._admitted = 'accepted'
        self.stamp.return_value = None
        self.preflight()
        self.assertEqual(self.audit.call_count, 3)
        self.assertFalse(identity_reuse._entries)

    def test_failed_fresh_check_clears_cache_and_preflight_scope(self):
        self.preflight()
        self.stamp.return_value = ('new snapshot',)
        self.audit.side_effect = ValueError('certificate changed')
        with self.assertRaisesRegex(ValueError, 'certificate changed'):
            self.preflight()
        self.assertFalse(request_scope.in_admission_preflight())
        self.assertFalse(identity_reuse._entries)
