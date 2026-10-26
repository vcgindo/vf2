"""Entry admission/recovery checks; mocks do not certify native publication."""
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class ProductionPostDbmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'local-unit-check-only')
        import django
        django.setup()

    def test_request_binds_only_released_test_cut(self):
        from mta.runtime.production_post_dbm import request, AUTHORITY, DISPOSITIONS
        run = SimpleNamespace(pk=AUTHORITY['run'], input_digest=AUTHORITY['input_digest'],
                              input_manifest_digest=AUTHORITY['input_manifest_digest'])
        args = dict(expected_dbm_digest=AUTHORITY['dbm_digest'], expected_action_revision=177,
                    command_key='post-dbm')
        with patch('release.native_identity.require_current', return_value={'commit': 'a'*40}), \
                patch('mta.runtime.phase_state.recipe_digest', return_value='b'*64):
            value = request(run, **args)
            self.assertEqual(value['dispositions'], DISPOSITIONS)
            self.assertIsNot(value['dispositions'], DISPOSITIONS)
            for key, changed in [('expected_dbm_digest', '0'*64), ('expected_action_revision', 176),
                                 ('expected_action_revision', True), ('command_key', '')]:
                with self.assertRaises(ValueError): request(run, **dict(args, **{key: changed}))
            for key in ('pk', 'input_digest', 'input_manifest_digest'):
                bad = SimpleNamespace(**dict(vars(run), **{key: 'other'}))
                with self.assertRaises(ValueError): request(bad, **args)

    def harness(self, *, head='DBM', recovering=False):
        from mta.runtime import production_post_dbm as entry
        stack = ExitStack()
        self.addCleanup(stack.close)
        def mock(name, **kwargs): return stack.enter_context(patch(name, **kwargs))
        value = dict(compatibility_digest='b'*64, dbm_digest='a'*64, action_revision=177,
                     command_key='post-dbm')
        attempt = SimpleNamespace(pk='attempt', worker_token='token', action_revision=177,
            scope='PostDBM', command_key='post-dbm', compatibility_digest='b'*64, status='FAILED')
        run = SimpleNamespace(pk='run', status='RUNNING', scope_attempts=MagicMock())
        initial = SimpleNamespace(pk=entry.AUTHORITY['dbm_attempt'], status='RELEASED')
        run.scope_attempts.order_by.return_value.first.return_value = attempt if recovering else initial
        mock('mta.runtime.production_post_dbm.transaction.get_autocommit', return_value=True)
        mock('mta.runtime.production_post_dbm.transaction.atomic')
        mock('mta.runtime.production_scope.authorize')
        runs = mock('mta.runtime.models.CalculationRun.objects')
        runs.select_related.return_value.get.return_value = run
        runs.select_for_update.return_value.get.return_value = run
        mock('mta.runtime.scope_execution._source_lock')
        mock('mta.runtime.production_post_dbm.request', return_value=value)
        mock('mta.runtime.production_post_dbm._entry', return_value=SimpleNamespace(pk='dbm', digest='a'*64))
        mock('mta.runtime.scope_execution.head', return_value=(head, 'a'*64))
        claim = mock('mta.runtime.scope_execution._claim', return_value=attempt)
        finish = mock('mta.runtime.scoped_final._finish_accepted_day', return_value=run)
        result = mock('mta.runtime.production_post_dbm._completed', return_value={'business_complete': True})
        fail = mock('mta.runtime.scope_execution.fail')
        earlier = [mock(name, side_effect=AssertionError('earlier work replay')) for name in (
            'mta.runtime.production_scope._produce', 'mta.runtime.scoped_actions.calculate_dbm',
            'mta.runtime.bpr_history_completion.complete', 'mta.runtime.production_upto_dbm._bpr_files')]
        args = dict(expected_dbm_digest='a'*64, expected_action_revision=177, command_key='post-dbm',
                    worker_reference='test', recovery_of='attempt' if recovering else None)
        return entry, args, SimpleNamespace(attempt=attempt, run=run, claim=claim, finish=finish,
            result=result, fail=fail, earlier=earlier, mock=mock)

    def test_only_existing_final_owner_is_called(self):
        for recovering in (False, True):
            with self.subTest(recovering=recovering):
                entry, args, calls = self.harness(recovering=recovering)
                self.assertEqual(entry.execute('run', **args), {'business_complete': True})
                calls.finish.assert_called_once_with('attempt', 'token', compatibility_digest='b'*64)
                self.assertEqual(calls.claim.call_args.kwargs['expected_phase'], 'DBM')
                for earlier in calls.earlier: earlier.assert_not_called()

    def test_completed_repeat_has_no_claim_or_calculation(self):
        entry, args, calls = self.harness()
        calls.run.status = 'SUCCEEDED'
        entry.execute('run', **args)
        calls.result.assert_called_once()
        calls.claim.assert_not_called()
        calls.finish.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'requires no recovery'):
            entry.execute('run', **dict(args, recovery_of='attempt'))

    def test_failed_latest_attempt_required_for_recovery(self):
        entry, args, calls = self.harness(recovering=True)
        for changed in (None, 'wrong-attempt'):
            with self.assertRaisesRegex(ValueError, 'explicit recovery'):
                entry.execute('run', **dict(args, recovery_of=changed))
        calls.attempt.status = 'ACTIVE'
        with self.assertRaisesRegex(ValueError, 'explicit recovery'):
            entry.execute('run', **args)
        calls.attempt.status = 'FAILED'
        calls.attempt.scope = 'PostBPR'
        with self.assertRaisesRegex(ValueError, 'continuation command owner'):
            entry.execute('run', **args)
        calls.claim.assert_not_called()
        calls.finish.assert_not_called()

    def test_fresh_key_cannot_abandon_failed_continuation(self):
        entry, args, calls = self.harness(recovering=True)
        calls.attempt.command_key = 'previous-command'
        with self.assertRaisesRegex(ValueError, 'continuation command owner'):
            entry.execute('run', **dict(args, recovery_of=None))
        calls.claim.assert_not_called()
        calls.finish.assert_not_called()

    def test_owner_is_rechecked_under_claim_lock(self):
        entry, args, calls = self.harness()
        initial = calls.run.scope_attempts.order_by.return_value.first.return_value
        raced = SimpleNamespace(pk='other', scope='PostDBM', command_key='raced',
                                compatibility_digest='b'*64, status='FAILED')
        calls.run.scope_attempts.order_by.return_value.first.side_effect = [initial, raced]
        with self.assertRaisesRegex(ValueError, 'continuation command owner'):
            entry.execute('run', **args)
        calls.claim.assert_not_called()

    def test_absent_recovery_and_wrong_head_are_denied(self):
        entry, args, calls = self.harness()
        with self.assertRaisesRegex(ValueError, 'recovery owner is absent'):
            entry.execute('run', **dict(args, recovery_of='attempt'))
        calls.mock('mta.runtime.scope_execution.head', return_value=('BPR', 'a'*64))
        with self.assertRaisesRegex(ValueError, 'pre-BTR DBM head'):
            entry.execute('run', **args)
        calls.claim.assert_not_called()

    def test_action_race_denied_inside_claim_transaction(self):
        entry, args, calls = self.harness()
        calls.attempt.action_revision = 178
        with self.assertRaisesRegex(ValueError, 'action revision changed'):
            entry.execute('run', **args)
        calls.finish.assert_not_called()

    def test_final_failure_records_failed_attempt(self):
        entry, args, calls = self.harness()
        error = ValueError('injected terminal failure')
        calls.finish.side_effect = error
        with self.assertRaisesRegex(ValueError, 'injected terminal failure'):
            entry.execute('run', **args)
        calls.fail.assert_called_once_with('attempt', 'token', compatibility_digest='b'*64, error=error)

    def test_inspection_does_not_claim_or_finalize(self):
        entry, args, calls = self.harness()
        report = entry.execute('run', **args, inspect_only=True)
        self.assertFalse(report['mutation'])
        self.assertFalse(report['business_complete'])
        calls.claim.assert_not_called()
        calls.finish.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'inspection flag'):
            entry.execute('run', **args, inspect_only=1)

    def test_entry_checks_frozen_request_profile_and_released_dbm_owner(self):
        from mta.runtime import production_post_dbm as entry
        from mta.serialization import digest
        raw = dict(profile={'delivery': 'test'}, scope_request=dict(scope='UptoDBM',
            command_key='uptodbm', compatibility_digest='old-release', runtime_reports={}))
        authority = dict(entry.AUTHORITY, profile_digest=digest(raw['profile']),
                         scope_request_digest=digest(raw['scope_request']))
        owner = SimpleNamespace(pk=authority['dbm_attempt'], status='RELEASED', scope='UptoDBM',
                                command_key='uptodbm', compatibility_digest='old-release')
        phase = SimpleNamespace(pk=authority['dbm'], attempt=owner)
        value = dict(command_key='post-dbm', dbm_digest='a'*64, action_revision=177)
        with patch.object(entry, 'AUTHORITY', authority), \
                patch('mta.runtime.scope_runtime_reports.require_test_database'), \
                patch('mta.runtime.scope_runtime_reports.validate'), \
                patch('mta.runtime.input_reader.read_input', return_value=raw), \
                patch('mta.runtime.production_scope.captured_run'), \
                patch('mta.runtime.production_scope._phase', return_value=phase), \
                patch('mta.runtime.scoped_actions.revision', return_value=177):
            self.assertIs(entry._entry(SimpleNamespace(), value), phase)
            for key, bad in [('status','ACTIVE'), ('scope','PostBPR'), ('pk','other'),
                             ('command_key','different'), ('compatibility_digest','changed')]:
                old = getattr(owner, key)
                setattr(owner, key, bad)
                with self.assertRaisesRegex(ValueError, 'owner changed'):
                    entry._entry(SimpleNamespace(), value)
                setattr(owner, key, old)
            raw['profile']['delivery'] = 'different'
            with self.assertRaisesRegex(ValueError, 'captured UptoDBM'):
                entry._entry(SimpleNamespace(), value)

    def test_command_has_no_recapture_or_earlier_phase_arguments(self):
        from mta.runtime.management.commands.run_production_post_dbm import Command
        parser = Command().create_parser('manage.py', 'run_production_post_dbm')
        for name in ('--input', '--retry-capture', '--repair-files', '--pick-output-root', '--expected-bpr-digest'):
            self.assertNotIn(name, parser._option_string_actions)
        for name in ('--run', '--expected-dbm-digest', '--expected-action-revision', '--recovery-of', '--inspect'):
            self.assertIn(name, parser._option_string_actions)

    def test_fencing_rejects_foreign_owner_before_fence_mutation(self):
        from mta.runtime import production_post_dbm as entry
        attempt = SimpleNamespace(pk='attempt', run=SimpleNamespace(), expected_receipt_digest='a'*64,
            action_revision=177, command_key='post-dbm', scope='PostDBM', expected_phase='DBM',
            compatibility_digest='b'*64)
        with patch('mta.runtime.production_scope.authorize'), \
                patch('mta.runtime.models.RunScopeAttempt.objects') as attempts, \
                patch.object(entry, 'request', return_value={'compatibility_digest': 'b'*64}), \
                patch.object(entry, '_entry'), patch('mta.runtime.scope_execution.fence') as fence:
            attempts.select_related.return_value.get.return_value = attempt
            entry.fence('attempt', expected_worker_token='exact-token', reason='verified exited worker')
            fence.assert_called_once_with('attempt', expected_worker_token='exact-token', reason='verified exited worker')
            fence.reset_mock()
            attempt.scope = 'PostBPR'
            with self.assertRaisesRegex(ValueError, 'exact native command owner'):
                entry.fence('attempt', expected_worker_token='exact-token', reason='wrong owner')
            fence.assert_not_called()

    def test_completed_result_requires_exact_terminal_owner(self):
        from mta.runtime import production_post_dbm as entry
        attempt = SimpleNamespace(pk='attempt', scope='PostDBM', command_key='post-dbm',
            compatibility_digest='b'*64, status='RELEASED', action_revision=177,
            expected_phase='DBM', expected_receipt_digest='a'*64)
        final = SimpleNamespace(pk='final', digest='c'*64, attempt=attempt, metadata={'output_digest':'d'*64})
        run = SimpleNamespace(pk='run', status='SUCCEEDED', output_digest='d'*64,
            business_date=SimpleNamespace(isoformat=lambda:'2026-10-25'), phase_acceptances=MagicMock())
        run.phase_acceptances.select_related.return_value.get.return_value = final
        value = dict(command_key='post-dbm', compatibility_digest='b'*64, action_revision=177,
                     dbm_digest='a'*64, dispositions={})
        with patch('mta.runtime.scope_execution.head', return_value=('DAY_FINAL','c'*64)), \
                patch('mta.runtime.scope_execution.receipt_digest', return_value='c'*64), \
                patch('mta.runtime.receipt_integrity.verify_root') as verify:
            result = entry._completed(run, value)
            self.assertTrue(result['business_complete'])
            self.assertFalse(result['scope_ready'])
            self.assertFalse(result['serving_selected'])
            verify.assert_called_once_with(run)
            attempt.expected_receipt_digest = 'wrong-parent'
            with self.assertRaisesRegex(ValueError, 'completed owner differs'):
                entry._completed(run, value)
