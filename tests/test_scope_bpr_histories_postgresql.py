"""Allocation histories share BPR's actual typed transaction and DBM inheritance.

Rollback-only component proof; no native registration or legacy parity claim.
"""
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tests import test_prepared_effects_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1', 'Owned PostgreSQL required')
class ScopeBprHistoryPostgresTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner'):
        locals()[_name] = getattr(fixtures.PreparedEffectsPostgresTests, _name)

    def setup_scope(self, scope='UptoDBM'):
        from mta.runtime.scope_execution import _claim
        self.value = dict(scope=scope, command_key='history-component', compatibility_digest='a'*64)
        root = self.enterContext(TemporaryDirectory())
        self.owner(claim=False, report_mode='expanded', pick_root=root, scope_request=self.value)
        self.attempt = _claim(self.run.pk, scope=scope, command_key=self.value['command_key'],
            worker_reference='rollback-only-history-proof', compatibility_digest='a'*64,
            expected_phase='START', expected_receipt_digest='')

    def assert_history(self, receipt):
        from mta.runtime.scoped_actions import restore
        from mta.serialization import storage
        from mta.runtime.scope_bpr_histories import NAMES
        _, sources = restore(self.run, receipt)
        values = sources.production_reports
        for current, history in zip(('BORWithOrderAllocation','RRR_OrderAllocation'), NAMES):
            self.assertTrue(values[current], 'This component must exercise nonempty current allocations')
            self.assertEqual(values[history], storage([
                dict(row, ReportDate=str(self.run.business_date)) for row in values[current]]))
        return {name:values[name] for name in NAMES}

    def test_history_is_accepted_with_bpr_and_inherited_once_by_dbm(self):
        from mta.runtime.production_scope import _produce
        from mta.runtime.scoped_actions import calculate_dbm
        self.setup_scope()
        bpr = _produce(self.attempt, self.value)
        expected = self.assert_history(bpr)
        dbm = calculate_dbm(self.attempt.pk, self.attempt.worker_token, compatibility_digest='a'*64)
        self.assertEqual(self.assert_history(dbm), expected)
        self.run.refresh_from_db(); self.capture.refresh_from_db()
        self.assertEqual((self.run.status,self.capture.status), ('RUNNING','CAPTURED'))
        self.assertEqual(list(self.run.phase_acceptances.order_by('accepted_at').values_list('phase',flat=True)),
                         ['PRE_BPR','BPR','DBM'])
        self.assertFalse(self.run.output_digest)
        self.assertFalse(self.run.checkpoints.exists())

    def test_upto_bpr_histories_survive_release_and_post_bpr_without_recollection(self):
        from mta.runtime.production_scope import _produce
        from mta.runtime.scope_execution import _claim, _close_attempt, _setting
        from mta.runtime.scoped_actions import calculate_dbm
        from mta.application import operational_bor
        self.setup_scope('UptoBPR')
        bpr = _produce(self.attempt, self.value)
        expected = self.assert_history(bpr)
        with _setting('fresh.scope_worker', self.attempt.worker_token):
            _close_attempt(self.attempt, self.run, 'RELEASED', {})
        continuation = _claim(self.run.pk, scope='PostBPR', command_key='history-continuation',
            worker_reference='rollback-only-history-proof', compatibility_digest='b'*64,
            expected_phase='BPR', expected_receipt_digest=bpr.digest)
        with patch.object(operational_bor, 'collect_bor_order_allocation_history',
                          side_effect=AssertionError('accepted BOR history recollected')), \
                patch.object(operational_bor, 'collect_rrr_order_allocation_history',
                             side_effect=AssertionError('accepted RRR history recollected')):
            dbm = calculate_dbm(continuation.pk, continuation.worker_token, compatibility_digest='b'*64)
        self.assertEqual(self.assert_history(dbm), expected)
        self.assertEqual(self.run.phase_acceptances.filter(phase='BPR').count(), 1)
        self.assertEqual(dbm.attempt_id, continuation.pk)
        self.capture.refresh_from_db()
        self.assertEqual(self.capture.status, 'CAPTURED')

    def check_late_failure_and_retry(self, scope):
        from mta.runtime import phase_state
        from mta.runtime.production_scope import _produce
        self.setup_scope(scope)
        original = phase_state.save
        def fail_after_snapshot(*args, **kwargs):
            image = original(*args, **kwargs)
            if image.phase == 'BPR': raise ValueError('injected late BPR history failure')
            return image
        with patch.object(phase_state, 'save', side_effect=fail_after_snapshot):
            with self.assertRaisesRegex(ValueError, 'late BPR history failure'):
                _produce(self.attempt, self.value)
        self.assertEqual(list(self.run.phase_acceptances.values_list('phase',flat=True)), ['PRE_BPR'])
        with patch('mta.temporal.chain.prepare_day', side_effect=AssertionError('accepted PRE replay')):
            bpr = _produce(self.attempt, self.value)
        self.assert_history(bpr)
        with patch('mta.temporal.chain.produce_bpr', side_effect=AssertionError('accepted BPR replay')):
            repeated = _produce(self.attempt, self.value)
        self.assertEqual(repeated.pk, bpr.pk)
        self.assertEqual(self.run.phase_acceptances.filter(phase='BPR').count(), 1)

    def test_late_bpr_snapshot_failure_rolls_back_history_and_retry_does_not_duplicate(self):
        self.check_late_failure_and_retry('UptoDBM')

    def test_upto_bpr_late_failure_retains_pre_and_retry_accepts_histories_once(self):
        self.check_late_failure_and_retry('UptoBPR')
