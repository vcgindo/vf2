"""Native continuation control flow; no native acceptance claim from mocks."""
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock


class ProductionPostBprTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'local-unit-check-only')
        import django
        django.setup()

    def test_request_pins_approved_owner_actions_profile_and_test_dispositions(self):
        from mta.runtime.production_post_bpr import request, DISPOSITIONS
        from mta.runtime.bpr_history_completion import AUTHORITY
        run = SimpleNamespace(pk=AUTHORITY['run'], input_digest=AUTHORITY['input_digest'])
        with patch('release.native_identity.require_current', return_value={'commit': 'a'*40}), \
                patch('mta.runtime.phase_state.recipe_digest', return_value='b'*64):
            args = dict(expected_bpr_digest=AUTHORITY['phase_digest'], expected_action_revision=12, command_key='post-bpr')
            value = request(run, **args)
            self.assertEqual(value['dispositions'], DISPOSITIONS)
            self.assertIsNot(value['dispositions'], DISPOSITIONS)
            self.assertNotIn('worker_reference', value)
            for key, changed in (('expected_action_revision', 13), ('expected_action_revision', True),
                                 ('expected_bpr_digest', 'c'*64), ('command_key', '')):
                with self.assertRaises(ValueError): request(run, **dict(args, **{key: changed}))
            with self.assertRaises(ValueError):
                request(SimpleNamespace(pk='other', input_digest=run.input_digest), **args)

    def harness(self, *, head='BPR', recovering=False):
        from mta.runtime import production_post_bpr as entry
        stack = ExitStack()
        self.addCleanup(stack.close)
        value = dict(compatibility_digest='b'*64, bpr_digest='a'*64, action_revision=12, command_key='post-bpr')
        attempt = SimpleNamespace(pk='attempt', worker_token='token', action_revision=12,
            scope='PostBPR', command_key='post-bpr', compatibility_digest='b'*64, status='FAILED')
        run = SimpleNamespace(pk='run', status='RUNNING', phase_acceptances=MagicMock())
        run.phase_acceptances.select_related.return_value.get.return_value = SimpleNamespace(attempt=attempt)
        def mock(name, **kwargs): return stack.enter_context(patch(name, **kwargs))
        mock('mta.runtime.production_post_bpr.transaction.get_autocommit', return_value=True)
        mock('mta.runtime.production_post_bpr.transaction.atomic')
        mock('mta.runtime.production_scope.authorize')
        runs = mock('mta.runtime.models.CalculationRun.objects')
        runs.select_related.return_value.get.return_value = run
        attempts = mock('mta.runtime.models.RunScopeAttempt.objects')
        attempts.filter.return_value.order_by.return_value.first.return_value = attempt if recovering else None
        mock('mta.runtime.production_post_bpr.request', return_value=value)
        mock('mta.runtime.production_post_bpr._entry', return_value=SimpleNamespace(pk='bpr'))
        mock('mta.runtime.scope_execution.head', return_value=(head, 'a'*64))
        complete = mock('mta.runtime.bpr_history_completion.complete')
        claim = mock('mta.runtime.scope_execution._claim', return_value=attempt)
        dbm = mock('mta.runtime.scoped_actions.calculate_dbm')
        finish = mock('mta.runtime.scoped_final._finish_accepted_day', return_value=run)
        result = mock('mta.runtime.production_post_bpr._completed', return_value={'business_complete': True})
        fail = mock('mta.runtime.scope_execution.fail')
        replay = mock('mta.runtime.production_scope._produce', side_effect=AssertionError('PRE/BPR replay'))
        arguments = dict(expected_bpr_digest='a'*64, expected_action_revision=12, command_key='post-bpr',
                         worker_reference='test', recovery_of='attempt' if recovering else None)
        return entry, arguments, SimpleNamespace(complete=complete, claim=claim, dbm=dbm, finish=finish,
            result=result, fail=fail, replay=replay, attempt=attempt, run=run, mock=mock)

    def test_bpr_runs_only_dbm_and_final_after_history_completion(self):
        entry, args, calls = self.harness()
        order = []
        calls.complete.side_effect = lambda *a: order.append('history')
        calls.claim.side_effect = lambda *a, **kw: order.append('claim') or calls.attempt
        calls.dbm.side_effect = lambda *a, **kw: order.append('DBM')
        calls.finish.side_effect = lambda *a, **kw: order.append('final') or SimpleNamespace()
        self.assertEqual(entry.execute('run', **args), {'business_complete': True})
        self.assertEqual(order, ['history', 'claim', 'DBM', 'final'])
        calls.replay.assert_not_called()
        calls.fail.assert_not_called()

    def test_failed_tail_recovery_never_recalculates_accepted_dbm(self):
        entry, args, calls = self.harness(head='DBM', recovering=True)
        entry.execute('run', **args)
        calls.dbm.assert_not_called()
        calls.finish.assert_called_once()
        calls.replay.assert_not_called()

    def test_final_failure_is_recorded_on_attempt(self):
        entry, args, calls = self.harness()
        error = ValueError('terminal write failure')
        calls.finish.side_effect = error
        with self.assertRaisesRegex(ValueError, 'terminal write failure'):
            entry.execute('run', **args)
        calls.fail.assert_called_once_with('attempt', 'token', compatibility_digest='b'*64, error=error)

    def test_completed_repeat_does_not_claim_or_run_business_work(self):
        entry, args, calls = self.harness()
        calls.run.status = 'SUCCEEDED'
        self.assertEqual(entry.execute('run', **args), {'business_complete': True})
        calls.result.assert_called_once()
        calls.complete.assert_not_called()
        calls.claim.assert_not_called()
        calls.dbm.assert_not_called()
        calls.finish.assert_not_called()

    def test_wrong_recovery_or_dbm_owner_rejected_before_any_mutation(self):
        entry, args, calls = self.harness(head='DBM', recovering=True)
        with self.assertRaisesRegex(ValueError, 'explicit recovery'):
            entry.execute('run', **dict(args, recovery_of='different'))
        wrong = SimpleNamespace(scope='UptoDBM', command_key='post-bpr', compatibility_digest='b'*64)
        calls.run.phase_acceptances.select_related.return_value.get.return_value = SimpleNamespace(attempt=wrong)
        with self.assertRaisesRegex(ValueError, 'different DBM command'):
            entry.execute('run', **args)
        calls.complete.assert_not_called()
        calls.claim.assert_not_called()
        calls.dbm.assert_not_called()

    def test_changed_action_revision_rejects_claim_before_dbm(self):
        entry, args, calls = self.harness()
        calls.attempt.action_revision = 13
        with self.assertRaisesRegex(ValueError, 'action revision changed'):
            entry.execute('run', **args)
        calls.dbm.assert_not_called()
        calls.finish.assert_not_called()

    def test_inspection_has_no_completion_claim_or_calculation(self):
        entry, args, calls = self.harness()
        owners = calls.mock('mta.runtime.models.BprHistoryCompletion.objects')
        owners.filter.return_value.exists.return_value = False
        result = entry.execute('run', **args, inspect_only=True)
        self.assertFalse(result['mutation'])
        calls.complete.assert_not_called()
        calls.claim.assert_not_called()
        calls.dbm.assert_not_called()
        calls.finish.assert_not_called()

    def test_command_accepts_no_recapture_or_pick_repair_arguments(self):
        from mta.runtime.management.commands.run_production_post_bpr import Command
        parser = Command().create_parser('manage.py', 'run_production_post_bpr')
        for name in ('--input', '--retry-capture', '--repair-files', '--pick-output-root'):
            self.assertNotIn(name, parser._option_string_actions)
        for name in ('--run', '--expected-bpr-digest', '--expected-action-revision', '--recovery-of', '--inspect'):
            self.assertIn(name, parser._option_string_actions)
