"""Fresh-scope dispatch and recovery controls; mocks do not certify native parity."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tests.test_scope_runtime_reports import reference


def dispositions():
    from mta.runtime.production_upto_dbm import DISPOSITION
    return dict(schema=DISPOSITION, purpose='owned-scoped-test', site_code='SUPPLIED-INSTANCE',
        hooks={name:'explicit-test-no-op' for name in ('PostBPR','PreDBM','PostDBM')},
        input_download='enabled-five-file-four-table-archive', authority='Explicit unit fixture; no runtime approval')


class ProductionUptoDbmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'local-unit-check-only')
        import django
        django.setup()

    def test_request_binds_release_config_and_command_without_worker_identity(self):
        from mta.runtime import production_upto_dbm as entry, production_scope as fresh
        with patch('release.native_identity.require_current', return_value={'source_commit':'a'*40}), \
                patch('mta.runtime.phase_state.recipe_digest', return_value='b'*64):
            args = dict(runtime_reports=reference(), dispositions=dispositions())
            value = entry.request('command', **args)
            self.assertEqual(fresh.validate_request(value), value)
            self.assertNotIn('worker_reference', value)
            for changes in (dict(scope='UptoBPR'), dict(schema='other'),
                            dict(compatibility_digest='f'*64), dict(extra=True)):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    entry.validate_request(dict(value, **changes))
            altered = deepcopy(args)
            altered['dispositions']['authority'] = 'Different applicability'
            self.assertNotEqual(entry.request('command', **altered)['compatibility_digest'], value['compatibility_digest'])
            self.assertNotEqual(entry.request('other', **args)['compatibility_digest'], value['compatibility_digest'])
            for hooks in ({}, dict(args['dispositions']['hooks'], PostBTR='explicit-test-no-op')):
                with self.assertRaises(ValueError):
                    entry.request('command', **dict(args, dispositions=dict(dispositions(), hooks=hooks)))
            with self.assertRaises(ValueError): entry.request('command', **dict(args, runtime_reports=None))
            args['dispositions']['authority'] = 'Caller mutation'
            self.assertNotEqual(value['dispositions'], args['dispositions'])

    def test_disposition_file_is_pinned_duplicate_safe_and_never_partially_published(self):
        from mta.runtime import production_upto_dbm as entry
        with TemporaryDirectory() as folder:
            path = Path(folder)/'nested'/'config.json'
            raw = json.dumps(dispositions()).encode()
            with patch.object(entry.os, 'link', side_effect=OSError('publication interrupted')):
                with self.assertRaisesRegex(OSError, 'interrupted'): entry._disposition_file(path, raw)
            self.assertFalse(path.exists())
            self.assertEqual(list(path.parent.iterdir()), [])
            entry._disposition_file(path, raw)
            entry._disposition_file(path, raw)
            pin = hashlib.sha256(raw).hexdigest()
            self.assertEqual(entry.load_disposition(path, pin), dispositions())
            with self.assertRaisesRegex(ValueError, 'changed'): entry._disposition_file(path, b'different')
            self.assertEqual(path.read_bytes(), raw)
            duplicate = raw[:-1]+b',"authority":"duplicate"}'
            path.write_bytes(duplicate)
            with self.assertRaises(ValueError): entry.load_disposition(path, hashlib.sha256(duplicate).hexdigest())
            with self.assertRaises(ValueError): entry.load_disposition(path, pin)

    def test_configuration_requires_publication_and_real_history_policy(self):
        from mta.runtime.production_upto_dbm import configuration
        from mta.application.production_source_inputs import SCHEMA
        profile = dict(delivery=dict(site_code='SUPPLIED-INSTANCE'), daily_publication=True)
        day = dict(production_report_policy=dict(bor_history_horizon=90, rrr_history_horizon=90),
                   production_report_opening=None, production_report_schema=SCHEMA)
        value = dict(dispositions=dispositions())
        configuration(profile, day, value)
        for changes in (dict(daily_publication=False), dict(delivery=dict(site_code='OTHER'))):
            with self.assertRaises(ValueError): configuration(dict(profile, **changes), day, value)
        for changes in (dict(production_report_policy={}), dict(production_report_schema='other')):
            with self.assertRaises(ValueError): configuration(profile, dict(day, **changes), value)
        with self.assertRaises(ValueError): configuration(profile, {}, value)

    def test_native_preflight_aggregates_missing_history_before_capture(self):
        from mta.runtime.production_daily import inspect_execution
        owner = SimpleNamespace(source=SimpleNamespace(digest='a'*64), configuration_digest='b'*64)
        frame = dict(profile=dict(delivery=dict(site_code='SUPPLIED-INSTANCE'), daily_publication=True))
        with ExitStack() as stack:
            def mock(name, **kw): return stack.enter_context(patch(name, **kw))
            mock('mta.runtime.production_scope.validate_request')
            mock('mta.runtime.models.ProductionInitialization.objects').select_related.return_value.get.return_value = owner
            mock('mta.runtime.production_daily._inspection_frame', return_value=frame)
            mock('mta.mdm.production_families.require_initialization')
            mock('mta.runtime.mdm_integration_models.MdmSourceIntegration.objects').filter.return_value.exists.return_value = False
            mock('mta.runtime.production_daily.decode', return_value={})
            mock('mta.runtime.production_daily.working_day', return_value={})
            aggregate = mock('mta.runtime.production_preflight.daily', side_effect=lambda *a, **kw:kw['context_issues'])
            capture = mock('mta.runtime.temporal.execute_day', side_effect=AssertionError('capture forbidden'))
            report, *_ = inspect_execution(b'input','c'*64,
                initialization_id='8efa9227-6805-487d-b38a-4344f33f7179', source_digest='a'*64,
                configuration_digest='b'*64, pick_output_root='/owned', execution_revision='trial',
                scope_request=dict(scope='UptoDBM', dispositions=dispositions()))
            self.assertEqual(len(report), 1)
            self.assertEqual(report[0]['path'], '/scope_request')
            self.assertIn('configured BPR allocation histories', report[0]['message'])
            aggregate.assert_called_once()
            capture.assert_not_called()

    def test_non_test_database_is_rejected_before_retry_or_capture(self):
        from mta.runtime import production_upto_dbm as entry
        with patch.object(entry.transaction,'get_autocommit',return_value=True), \
                patch.object(entry,'request',return_value={}), \
                patch('mta.runtime.production_scope.authorize'), \
                patch('mta.runtime.scope_runtime_reports.require_test_database',side_effect=ValueError('test database required')), \
                patch('mta.runtime.production_scope.repeated') as repeated, \
                patch('mta.runtime.production_daily.execute') as capture:
            with self.assertRaisesRegex(ValueError,'test database required'):
                entry.execute(b'input','a'*64,command_key='command',worker_reference='worker',
                    runtime_reports=reference(),dispositions=dispositions())
            repeated.assert_not_called()
            capture.assert_not_called()

    def test_v3_capture_round_trips_complete_new_request(self):
        from tests.test_input_storage_v3 import MemoryImages, run_identity, OWNER
        from mta.runtime import input_storage, production_upto_dbm as entry
        from mta.serialization import digest
        with patch('release.native_identity.require_current', return_value={'source_commit':'a'*40}), \
                patch('mta.runtime.phase_state.recipe_digest', return_value='b'*64):
            value = entry.request('command', runtime_reports=reference(), dispositions=dispositions())
        raw = dict(profile=dict(delivery=dict(site_code='SUPPLIED-INSTANCE')), scope_request=value)
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw), kind='DAILY_CHAIN')
        images = MemoryImages()
        owner.input_payload = input_storage.save_input(owner, raw, version=3, image_writer=images.write,
            table_selector=lambda *args:None, identity_resolver=run_identity)
        owner.input_manifest_digest = digest(owner.input_payload)
        self.assertEqual(input_storage.read_input(owner, image_reader=images.read, identity_resolver=run_identity), raw)
        self.assertEqual(images.writes, [])

    def harness(self, *, head='START', status=None):
        from mta.runtime import production_upto_dbm as entry
        stack = ExitStack()
        self.addCleanup(stack.close)
        def mock(name, **kw): return stack.enter_context(patch(name, **kw))
        value = dict(scope='UptoDBM', compatibility_digest='b'*64, command_key='upto-dbm')
        attempt = SimpleNamespace(pk='attempt', worker_token='token', action_revision=0,
            scope='UptoDBM', command_key='upto-dbm', compatibility_digest='b'*64, status=status)
        run = SimpleNamespace(pk='run', status='RUNNING', business_date=SimpleNamespace(isoformat=lambda:'2037-04-10'),
            phase_acceptances=MagicMock(), scope_attempts=MagicMock())
        receipt = SimpleNamespace(pk='dbm', digest='a'*64, snapshot=SimpleNamespace(state_digest='c'*64), attempt=attempt)
        run.phase_acceptances.select_related.return_value.get.return_value = receipt
        run.scope_attempts.order_by.return_value.first.return_value = attempt
        runs = mock('mta.runtime.models.CalculationRun.objects')
        runs.get.return_value = run
        runs.select_for_update.return_value.get.return_value = run
        attempts = mock('mta.runtime.models.RunScopeAttempt.objects')
        attempts.filter.return_value.order_by.return_value.first.return_value = attempt if status else None
        mock('mta.runtime.production_upto_dbm.transaction.atomic')
        mock('mta.runtime.production_scope.captured_run')
        mock('mta.runtime.production_upto_dbm._configuration')
        mock('mta.runtime.scope_execution._source_lock')
        mock('mta.runtime.scope_execution._frozen')
        mock('mta.runtime.scope_execution.head', return_value=(head,'a'*64))
        phase = mock('mta.runtime.production_scope._phase', return_value=receipt)
        produce = mock('mta.runtime.production_scope._produce', return_value=SimpleNamespace(pk='bpr'))
        files = mock('mta.runtime.production_upto_dbm._bpr_files',
            return_value=(SimpleNamespace(digest='files'), dict(receipt_sha256='archive')))
        claim = mock('mta.runtime.scope_execution.claim', return_value=attempt)
        dbm = mock('mta.runtime.scoped_actions.calculate_dbm', return_value=receipt)
        release = mock('mta.runtime.scope_execution.release')
        fail = mock('mta.runtime.scope_execution.fail')
        final = mock('mta.runtime.scoped_final._finish_accepted_day', side_effect=AssertionError('BTR/final forbidden'))
        return entry, run, value, SimpleNamespace(mock=mock, attempt=attempt, produce=produce, files=files,
            claim=claim, dbm=dbm, release=release, fail=fail, final=final, phase=phase, receipt=receipt)

    def test_fresh_order_is_bpr_files_dbm_release_with_no_final_success(self):
        entry, run, value, calls = self.harness()
        events = []
        calls.produce.side_effect = lambda *a: events.append('BPR') or SimpleNamespace(pk='bpr')
        calls.files.side_effect = lambda *a, **kw: events.append('files') or (SimpleNamespace(digest='f'), dict(receipt_sha256='a'))
        calls.dbm.side_effect = lambda *a, **kw: events.append('DBM') or calls.receipt
        calls.release.side_effect = lambda *a, **kw: events.append('release')
        result = entry.advance(run, value, worker_reference='worker')
        self.assertEqual(events, ['BPR','files','DBM','release'])
        self.assertEqual(result['status'], 'RUNNING')
        self.assertTrue(result['calculation_accepted'])
        self.assertFalse(result['scope_ready'])
        self.assertFalse(result['serving_selected'])
        calls.final.assert_not_called()
        calls.fail.assert_not_called()

    def test_after_dbm_failure_recovery_does_not_repeat_calculation(self):
        entry, run, value, calls = self.harness(head='DBM', status='FAILED')
        entry.advance(run, value, worker_reference='new-worker', recovery_of='attempt')
        self.assertEqual(calls.claim.call_args.kwargs['recovery_of'], 'attempt')
        calls.produce.assert_not_called()
        calls.dbm.assert_not_called()
        calls.files.assert_called_once()
        calls.release.assert_called_once()
        calls.final.assert_not_called()

    def test_file_failure_records_attempt_and_never_starts_dbm(self):
        entry, run, value, calls = self.harness(head='BPR')
        error = ValueError('archive failure')
        calls.files.side_effect = error
        with self.assertRaisesRegex(ValueError, 'archive failure'):
            entry.advance(run, value, worker_reference='worker')
        calls.fail.assert_called_once_with('attempt','token', compatibility_digest='b'*64, error=error)
        calls.dbm.assert_not_called()
        calls.release.assert_not_called()

    def test_completed_repeat_never_claims_or_recalculates_and_blocks_new_owner(self):
        entry, run, value, calls = self.harness(head='DBM', status='RELEASED')
        entry.advance(run, value, worker_reference='reader')
        calls.claim.assert_not_called()
        calls.produce.assert_not_called()
        calls.dbm.assert_not_called()
        calls.release.assert_not_called()
        calls.files.reset_mock()
        run.scope_attempts.order_by.return_value.first.return_value = SimpleNamespace(pk='new-command')
        with self.assertRaisesRegex(ValueError, 'latest released'):
            entry.advance(run, value, worker_reference='reader')
        calls.files.assert_not_called()

    def test_other_scope_dbm_and_terminal_day_rejected_before_claim(self):
        entry, run, value, calls = self.harness(head='DBM', status='FAILED')
        calls.attempt.scope = 'PostBPR'
        with self.assertRaises(ValueError): entry.advance(run, value, worker_reference='worker')
        calls.attempt.scope = 'UptoDBM'
        run.phase_acceptances.select_related.return_value.get.return_value = SimpleNamespace(
            attempt=SimpleNamespace(scope='PostBPR', command_key='other', compatibility_digest='b'*64))
        with self.assertRaisesRegex(ValueError, 'different DBM command'):
            entry.advance(run, value, worker_reference='worker')
        run.status = 'SUCCEEDED'
        with self.assertRaisesRegex(ValueError, 'completed day'):
            entry.advance(run, value, worker_reference='worker')
        calls.claim.assert_not_called()
        calls.files.assert_not_called()

    def test_command_requires_explicit_config_and_uses_existing_capture_for_recovery(self):
        from mta.runtime.management.commands.run_production_upto_dbm import Command
        parser = Command().create_parser('manage.py','run_production_upto_dbm')
        for name in ('runtime-reports-file','runtime-reports-sha256','dispositions-file','dispositions-sha256'):
            self.assertTrue(parser._option_string_actions['--'+name].required)
        for name in ('--retry-capture','--report-disposition','--delivery-file'):
            self.assertNotIn(name, parser._option_string_actions)
        self.assertIn('--recovery-of', parser._option_string_actions)


if __name__ == '__main__': unittest.main()
