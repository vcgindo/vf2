"""An unchanged snapshot permits metadata reuse, never a stale authority check."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import uuid4

from mta.presentation import admission, identity_reuse as reuse
from mta.presentation.request_scope import read_request


class NativeIdentityReuseTests(TestCase):
    def setUp(self):
        reuse.clear()
        self.addCleanup(reuse.clear)
        self.old = admission._admitted
        self.addCleanup(setattr, admission, '_admitted', self.old)
        admission._admitted = 'admitted'
        values = dict(pk='run', business_date='2026-04-08', predecessor_id=None,
                      input_payload={'reference': 'origin'}, input_manifest_digest='input',
                      production_manifest={'generation': 'accepted'}, status='SUCCEEDED')
        self.run = NS(**values, _meta=NS(concrete_fields=[NS(attname=k) for k in values]))
        self.audit = Mock(return_value={'initialization': {'id': 'owner'}})
        self.read = reuse.native_identity(self.audit)
        self.snapshot = self.enterContext(patch.object(reuse, 'stamp', return_value=('snapshot',)))

    def request(self, route='GetBPRData', **kwargs):
        with read_request('/api/mta/' + route):
            return self.read(self.run, **kwargs)

    def test_success_reused_across_reads_and_caller_cannot_modify_it(self):
        self.request()['initialization']['id'] = 'forged'
        self.assertEqual(self.request()['initialization']['id'], 'owner')
        self.assertEqual(self.audit.call_count, 1)

    def test_snapshot_and_complete_run_metadata_changes_revalidate(self):
        for field in ('business_date', 'predecessor_id', 'input_payload', 'production_manifest'):
            reuse.clear()
            self.audit.reset_mock()
            original = deepcopy(getattr(self.run, field))
            self.request()
            setattr(self.run, field, 'changed')
            self.request()
            self.assertEqual(self.audit.call_count, 2, field)
            setattr(self.run, field, original)
        self.snapshot.return_value = ('new snapshot',)
        self.audit.side_effect = ValueError('ancestor changed')
        with self.assertRaisesRegex(ValueError, 'ancestor changed'):
            self.request()
        self.assertFalse(reuse._entries)

    def test_real_uuid_run_and_predecessor_fields_are_supported(self):
        self.run.pk = uuid4()
        self.run.predecessor_id = uuid4()
        self.request()
        self.request()
        self.assertEqual(self.audit.call_count, 1)

    def test_mutation_during_fill_never_creates_entry(self):
        self.snapshot.side_effect = [('before',), ('after',)]
        self.request()
        self.assertFalse(reuse._entries)

    def test_full_audit_offline_writes_and_unadmitted_process_bypass(self):
        self.request()
        self.request(verify_rows=True)
        self.read(self.run)
        self.request('DBMApplySelectedNorms')
        admission._admitted = None
        self.request()
        self.assertEqual(self.audit.call_count, 5)

    def test_transactions_bypass_and_errors_clear_entries(self):
        self.request()
        self.snapshot.return_value = None
        self.request()
        self.assertEqual(self.audit.call_count, 2)
        self.snapshot.side_effect = RuntimeError('connection lost')
        with self.assertRaisesRegex(RuntimeError, 'connection lost'):
            self.request()
        self.assertFalse(reuse._entries)

    def test_failed_startup_clears_previous_worker_identity(self):
        self.request()
        with patch.object(admission, 'binding', side_effect=ValueError('bad startup')):
            with self.assertRaisesRegex(ValueError, 'bad startup'):
                admission.admit()
        self.assertIsNone(admission._admitted)
        self.assertFalse(reuse._entries)
