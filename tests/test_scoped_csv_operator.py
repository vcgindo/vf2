"""Scope operator identity, no-replay and command-routing boundaries; no DB/day."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
from contextlib import ExitStack
from types import SimpleNamespace
from uuid import UUID
from django.apps import apps

from mta.runtime.csv_scope_operator import check_request, profile_reference, require_selection, require_profile_site

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(apps.ready, 'Django model bootstrap required; no database connections are used')
class ScopeRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'scope'
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.owner = SimpleNamespace(pk=UUID('00000000-0000-4000-8000-000000000001'), source=SimpleNamespace(digest='source'))
        self.cert = SimpleNamespace(pk=UUID('00000000-0000-4000-8000-000000000002'), receipt_digest='certificate')
        self.guard = self.stack.enter_context(patch('mta.runtime.scope_runtime_reports.require_test_database'))
        self.stack.enter_context(patch('mta.runtime.csv_scope_operator.ROOT',self.root))
        self.stack.enter_context(patch('mta.runtime.daily_feed.binding_owner',return_value=({},self.owner)))
        self.stack.enter_context(patch('mta.runtime.models.InitializationCertification.objects.get',return_value=self.cert))
        self.stack.enter_context(patch('mta.runtime.csv_scope_operator.profile_reference',return_value={'actual-initialization':'new'}))
        self.site = self.stack.enter_context(patch('mta.runtime.csv_scope_operator.initialized_profile',return_value={'delivery':{'site_code':'SUPPLIED-INSTANCE'}}))
        self.stack.enter_context(patch('mta.runtime.report_definition_registration.encode',return_value={'registration_digest':'registered'}))
        self.writer = self.stack.enter_context(patch('mta.runtime.report_definition_registration.register',return_value=SimpleNamespace(pk='registered')))
        profile = Path(self.temp.name)/'profile.json'
        profile.write_text(json.dumps({'hook':{'site_code':'SUPPLIED-INSTANCE'},'disposition':{'site_code':'SUPPLIED-INSTANCE'}}))
        self.args = SimpleNamespace(binding='owned-binding',profile=profile)

    def test_registration_uses_actual_certified_owner_and_source(self):
        from mta.runtime.csv_scope_operator import register
        self.assertEqual(register(self.args),{'status':'SCOPE_PROFILE_REGISTERED'})
        self.guard.assert_called_once_with()
        self.writer.assert_called_once_with({'actual-initialization':'new'},initialization_id=str(self.owner.pk),source_digest='source',certificate_digest='certificate')
        self.assertEqual(json.loads((self.root/'registration.json').read_text())['registration_digest'],'registered')

    def test_foreign_receipt_refused_before_native_metadata_write(self):
        from mta.runtime.csv_scope_operator import register
        self.root.mkdir()
        target=self.root/'registration.json'
        target.write_bytes(b'{"registration_digest":"another-instance"}')
        before=target.read_bytes()
        with self.assertRaisesRegex(ValueError,'no replacement'):
            register(self.args)
        self.writer.assert_not_called()
        self.assertEqual(target.read_bytes(),before)

    def test_captured_continuation_keeps_original_registration_without_live_registration(self):
        from mta.runtime.csv_scope_operator import register
        self.root.mkdir()
        captured = dict(registration_digest='original-captured-registration',
                        reference={'actual-initialization': 'new'})
        (self.root / 'registration.json').write_text(json.dumps(captured))
        with patch('mta.runtime.csv_scope_operator.captured_registration', return_value=captured):
            self.assertEqual(register(self.args, inspect_only=True)['status'], 'SCOPE_REGISTRATION_PREFLIGHT_READY')
            self.assertEqual(register(self.args)['status'], 'SCOPE_PROFILE_REGISTERED')
        self.writer.assert_not_called()

    def test_captured_registration_cannot_be_replaced_by_a_different_local_receipt(self):
        from mta.runtime.csv_scope_operator import register
        self.root.mkdir()
        (self.root / 'registration.json').write_text('{"registration_digest":"foreign"}')
        with patch('mta.runtime.csv_scope_operator.captured_registration', return_value={
                'registration_digest': 'original', 'reference': {'actual-initialization': 'new'}}):
            with self.assertRaisesRegex(ValueError, 'Original captured'):
                register(self.args, inspect_only=True)
        self.writer.assert_not_called()

    def test_native_database_restriction_is_checked_before_registration(self):
        from mta.runtime.csv_scope_operator import register
        self.guard.side_effect=ValueError('owned validation database required')
        with self.assertRaisesRegex(ValueError,'owned validation'):
            register(self.args)
        self.writer.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_actual_opening_site_mismatch_prevents_registration(self):
        from mta.runtime.csv_scope_operator import register
        self.site.return_value={'delivery':{'site_code':'GulfOil'}}
        with self.assertRaisesRegex(ValueError,'GulfOil'):
            register(self.args)
        self.writer.assert_not_called()
        self.assertFalse(self.root.exists())


class ScopeRequestTests(unittest.TestCase):
    def test_large_pack_site_cannot_be_relabelled_as_the_supplied_instance(self):
        actual={'delivery':{'site_code':'GulfOil'}}
        profile={'hook':{'site_code':'SUPPLIED-INSTANCE'},'disposition':{'site_code':'SUPPLIED-INSTANCE'}}
        with self.assertRaisesRegex(ValueError,'contract extension'):
            require_profile_site(profile,actual)
        self.assertEqual(actual['delivery']['site_code'],'GulfOil')
        self.assertIsNone(require_profile_site(profile,{'delivery':{'site_code':'SUPPLIED-INSTANCE'}}))

    def test_scope_adapter_is_in_both_source_and_native_image_rosters(self):
        from release.export import included
        from release.native_identity import _native
        self.assertTrue(included('mta/runtime/csv_scope_operator.py'))
        self.assertTrue(_native('mta/runtime/csv_scope_operator.py'))
        self.assertTrue(_native('mta/runtime/csv_scope_operator.py'))

    def test_same_run_wrong_phase_cannot_pass_terminal_serving_verification(self):
        with self.assertRaisesRegex(ValueError, 'selection differs'):
            require_selection('same-run', {'selection_digest':'old-bpr'}, 'same-run', 'terminal')
        with self.assertRaises(ValueError):
            require_selection('other-run', {'selection_digest':'terminal'}, 'same-run', 'terminal')
        self.assertIsNone(require_selection('same-run', {'selection_digest':'terminal'}, 'same-run', 'terminal'))

    def gate(self, stored=None, scope='Full', resume=False, **changes):
        args = dict(scope=scope, binding_digest='opening', batch_digest='facts',
                    profile_digest='profile', resume=resume)
        args.update(changes)
        return check_request(stored, **args)

    def stored(self, scope='UptoBPR', status='PUBLISHED'):
        return dict(initial_scope=scope, scope=scope, status=status,
                    binding_digest='opening', batch_digest='facts', profile_digest='profile')

    def test_first_entry_and_tail_requirements(self):
        for scope in ('Full', 'UptoBPR', 'UptoDBM'):
            with self.subTest(scope=scope):
                self.assertEqual(self.gate(scope=scope), 'START')
        for scope in ('PostBPR', 'PostDBM'):
            with self.subTest(scope=scope), self.assertRaisesRegex(ValueError, 'own recorded'):
                self.gate(scope=scope)
        with self.assertRaises(ValueError):
            self.gate(resume=True)

    def test_only_own_accepted_prefix_can_continue(self):
        for prefix, tail in [('UptoBPR', 'PostBPR'), ('UptoDBM', 'PostDBM')]:
            original = self.stored(prefix)
            self.assertEqual(self.gate(original, tail), 'CONTINUE')
            self.assertEqual(original, self.stored(prefix))
            for other in ('Full', 'UptoBPR', 'UptoDBM', 'PostBPR', 'PostDBM'):
                if other not in (prefix, tail):
                    with self.subTest(prefix=prefix, other=other), self.assertRaises(ValueError):
                        self.gate(original, other)
            with self.assertRaises(ValueError):
                self.gate(original, tail, resume=True)

    def test_changed_opening_facts_or_profile_fail_before_any_action(self):
        for field in ('binding_digest', 'batch_digest', 'profile_digest'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'differs'):
                self.gate(self.stored(), 'UptoBPR', **{field: 'changed'})

    def test_native_failure_or_interruption_never_becomes_automatic_retry(self):
        for status in ('EXECUTING', 'FAILED'):
            for resume in (False, True):
                with self.subTest(status=status, resume=resume), self.assertRaisesRegex(ValueError, 'reconciliation'):
                    self.gate(self.stored(status=status), 'UptoBPR', resume=resume)

    def test_only_explicit_nonproducing_preparation_resume(self):
        for status, decision in [('CALCULATED', 'PREPARE'), ('PREPARED', 'SELECT')]:
            stored = self.stored(status=status)
            with self.assertRaisesRegex(ValueError, 'Resume'):
                self.gate(stored, 'UptoBPR')
            self.assertEqual(self.gate(stored, 'UptoBPR', resume=True), decision)

    def test_published_retry_does_not_reselect_an_old_prefix(self):
        stored = self.stored()
        self.assertEqual(self.gate(stored, 'UptoBPR'), 'EXISTING')
        stored['scope'] = 'PostBPR'
        before = deepcopy(stored)
        self.assertEqual(self.gate(stored, 'PostBPR'), 'EXISTING')
        self.assertEqual(self.gate(stored, 'UptoBPR'), 'EXISTING')
        self.assertEqual(stored, before)

    def test_profile_rebinding_does_not_adopt_fixture_identity(self):
        from mta.application.runtime_report_configuration import SCHEMA
        profile = dict(schema='vectorflow-scope-validation-profile-v1',
            configuration=dict(schema=SCHEMA, RuntimeReports=[], DownloadableUIReportSettings=[]),
            hook={'site_code': 'explicit'}, disposition={'hooks': {}}, authority='Human validation')
        # Native exact-definition validation is separate and remains mandatory.
        with patch('mta.runtime.runtime_report_request.validate_reference') as validate:
            result = profile_reference(profile, '00000000-0000-4000-8000-000000000001', 'a' * 64)
            validate.assert_called_once_with(result)
        anchor = json.loads(result['catalogue_anchor_json'])
        self.assertEqual(anchor['identity'], '00000000-0000-4000-8000-000000000001')
        self.assertEqual(anchor['catalogue'], {})
        self.assertIsNone(anchor['output_digest'])
        self.assertEqual(anchor['evidence']['source'], 'a' * 64)
        with self.assertRaisesRegex(ValueError, 'Explicit offline'):
            profile_reference({**profile, 'run_id': 'old-fixture'}, 'unused', 'a' * 64)

    def test_native_profile_restriction_is_not_bypassed(self):
        from mta.application.runtime_report_configuration import SCHEMA
        invalid = dict(schema='vectorflow-scope-validation-profile-v1',
            configuration=dict(schema=SCHEMA, RuntimeReports=[], DownloadableUIReportSettings=[]),
            hook={}, disposition={}, authority='Human validation')
        with self.assertRaisesRegex(ValueError, 'retained eight-report'):
            profile_reference(invalid, '00000000-0000-4000-8000-000000000001', 'a' * 64)


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell7 required')
class ScopeLauncherTests(unittest.TestCase):
    shell = 'pwsh'
    def invoke_scope(self, case):
        """Run the real host flow with only its Docker process boundary mocked."""
        import os
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'release').mkdir()
            (root / 'pack/config').mkdir(parents=True)
            (root / 'pack/binding.json').write_text('{}')
            (root / 'pack/config/scope-validation.json').write_text('{}')
            (root / '.env').write_text('COMPOSE_FILE=compose.yaml;extra.json\nEMAIL_PASS=private-value-preserved\n')
            config = dict(name='vectorflow', services={
                'mta': dict(image='vectorflow/mta:source', environment={'VF_MTA_NATIVE_PUBLICATION':'1'}, volumes=[]),
                'daily': dict(environment={}, volumes=[]), 'provision': dict(environment={}, volumes=[])},
                **{'x-vectorflow-daily':dict(input_dir=str(root/'pack'), binding_file=str(root/'pack/binding.json'), state_dir=str(root/'state'))})
            (root / 'config.json').write_text(json.dumps(config))
            shutil.copyfile(ROOT / 'release/powershell_compat.ps1', root / 'release/powershell_compat.ps1')
            source = (ROOT / 'release/run_csv_scope.ps1').read_text()
            start, end = source.index('function ComposeCall('), source.index('function Worker(')
            boundary = r'''
function ComposeCall([string[]]$Arguments,[switch]$Json) {
    Add-Content -LiteralPath (Join-Path $env:VECTORFLOW_OPERATOR_ROOT 'trace.jsonl') -Value (ConvertTo-Json -InputObject $Arguments -Compress)
    $mode=$env:VECTORFLOW_OPERATOR_CASE
    $pin='a'*64
    if ($Arguments -contains 'inspect') {
        if ($mode -eq 'preflight-failure') { throw 'Preflight refused' }
        return @{status=$(if($mode.StartsWith('existing')){'EXISTING'}else{'SCOPE_PREFLIGHT_READY'});run_id='owned-run';selection_digest=$pin}
    }
    if ($Arguments -contains 'register') { return @{status='SCOPE_PROFILE_REGISTERED'} }
    if ($Arguments -contains 'execute') {
        if ($mode -eq 'native-failure') { throw 'Native failure; preserve' }
        return @{status='PREPARED';run_id='owned-run';selection_digest=$pin;environment=@{VF_MTA_PHASE_SELECTION_FILE='/prepared/phase.json';VF_MTA_SELECTION_FILE=''}}
    }
    if ($Arguments -contains 'serving') {
        if ($mode -in @('readiness-failure','existing-invalid')) { throw 'Wrong actual selection' }
        if ($Arguments -notcontains '--selection-digest') { throw 'Selection digest missing' }
        return @{ready=$true;run_id='owned-run';selection_digest=$pin;admission_digest=('b'*64)}
    }
    if ($Arguments -contains 'acknowledge') {
        foreach($required in @('--run','--selection-digest','--proof')) {if($Arguments -notcontains $required){throw "Missing $required"}}
        return @{status='PUBLISHED';run_id='owned-run'}
    }
    if ($Arguments -contains 'reconcile') { return @{status='RECOVERABLE';run_id='owned-run'} }
}
'''
            (root / 'release/run_csv_scope.ps1').write_text(source[:start] + boundary + source[end:])
            (root / 'runner.ps1').write_text('''
function docker { $global:LASTEXITCODE=0; Get-Content -LiteralPath (Join-Path $env:VECTORFLOW_OPERATOR_ROOT 'config.json') -Raw }
if ($env:VECTORFLOW_OPERATOR_CASE -eq 'reconcile') {
 & ./release/run_csv_scope.ps1 -BusinessDate 2026-04-09 -Scope PostBPR -Reconcile
} elseif ($env:VECTORFLOW_OPERATOR_CASE -eq 'existing-invalid') {
 & ./release/run_csv_scope.ps1 -BusinessDate 2026-04-09 -Scope UptoBPR -Resume
} else { & ./release/run_csv_scope.ps1 -BusinessDate 2026-04-09 -Scope UptoBPR }
''')
            result = subprocess.run([self.shell,'-NoProfile','-File',str(root/'runner.ps1')], cwd=root,
                env={**os.environ, 'VECTORFLOW_OPERATOR_ROOT':str(root), 'VECTORFLOW_OPERATOR_CASE':case}, capture_output=True,text=True)
            calls = [json.loads(line) for line in (root/'trace.jsonl').read_text(encoding='utf-8-sig').splitlines()]
            overlay = root/'state/vectorflow.scope.json'
            return result, calls, (root/'.env').read_text(), overlay.read_text() if overlay.exists() else None, list((root/'state').rglob('compose.private.json'))

    def test_host_publishes_only_after_exact_serving_check(self):
        result,calls,env,overlay,private = self.invoke_scope('success')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'PUBLISHED')
        self.assertEqual(sum('execute' in c for c in calls),1)
        self.assertLess(next(i for i,c in enumerate(calls) if 'serving' in c),next(i for i,c in enumerate(calls) if 'acknowledge' in c))
        self.assertTrue(all(c[-1]=='mta' and '--no-deps' in c for c in calls if c[0]=='up'))
        self.assertIn('EMAIL_PASS=private-value-preserved',env)
        self.assertNotIn('private-value-preserved',overlay)
        self.assertEqual(private,[])

    def test_preflight_failure_does_not_stop_a_serving_application(self):
        result,calls,_,overlay,private = self.invoke_scope('preflight-failure')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(any(c[0] in ('stop','up') or 'execute' in c or 'register' in c for c in calls))
        self.assertIsNone(overlay)
        self.assertEqual(private,[])

    def test_reconcile_is_separate_and_never_changes_serving_or_runs_a_producer(self):
        result,calls,env,overlay,private=self.invoke_scope('reconcile')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'RECOVERABLE')
        self.assertEqual(len(calls),1)
        self.assertIn('reconcile',calls[0])
        self.assertFalse(any(x in calls[0] for x in ('preflight','register','inspect','execute','stop','up')))
        self.assertIsNone(overlay)
        self.assertEqual(env,'COMPOSE_FILE=compose.yaml;extra.json\nEMAIL_PASS=private-value-preserved\n')
        self.assertEqual(private,[])

    def test_native_or_readiness_failure_is_not_acknowledged_or_replayed(self):
        for case in ('native-failure','readiness-failure'):
            result,calls,_,_,private = self.invoke_scope(case)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(sum('execute' in c for c in calls),1)
            self.assertFalse(any('acknowledge' in c for c in calls))
            self.assertEqual(calls[-1],['stop','mta'])
            self.assertEqual(private,[])

    def test_existing_operation_is_read_only_and_wrong_selection_cannot_restart(self):
        for case in ('existing','existing-invalid'):
            result,calls,_,overlay,private = self.invoke_scope(case)
            self.assertEqual(result.returncode==0,case=='existing',result.stderr)
            self.assertFalse(any(c[0] in ('stop','up') or 'execute' in c or 'register' in c for c in calls))
            self.assertIsNone(overlay)
            self.assertEqual(private,[])

    def test_real_launcher_routes_all_scopes_without_docker_or_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'release').mkdir()
            shutil.copyfile(ROOT / 'vf.ps1', root / 'vf.ps1')
            shutil.copyfile(ROOT / 'release/powershell_compat.ps1', root / 'release/powershell_compat.ps1')
            (root / 'release/run_csv_scope.ps1').write_text(
                'param($BusinessDate,$Scope,[switch]$InspectOnly,[switch]$Resume)\n'
                '@{date=$BusinessDate;scope=$Scope;inspect=[bool]$InspectOnly;resume=[bool]$Resume}|ConvertTo-Json -Compress\n')
            for scope in ('Full', 'UptoBPR', 'PostBPR', 'UptoDBM', 'PostDBM'):
                result = subprocess.run([self.shell, '-NoProfile', '-File', str(root / 'vf.ps1'),
                    'csv-scope', '2026-04-09', '-Scope', scope, '-InspectOnly'],
                    capture_output=True, text=True, cwd=root)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout),
                                 dict(date='2026-04-09', scope=scope, inspect=True, resume=False))

    def test_real_powershell_scripts_parse(self):
        for relative in ('vf.ps1', 'release/run_csv_scope.ps1'):
            script = "$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile($args[0],[ref]$t,[ref]$e);if($e){$e|Out-String|Write-Error;exit 1}"
            with tempfile.TemporaryDirectory() as temporary:
                runner = Path(temporary) / 'parse.ps1'
                runner.write_text(script)
                result = subprocess.run([self.shell, '-NoProfile', '-File', str(runner), str(ROOT / relative)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(shutil.which('powershell'), 'Windows PowerShell5.1 required')
class WindowsPowerShellScopeLauncherTests(ScopeLauncherTests):
    shell = 'powershell'


@unittest.skipUnless(apps.ready, 'Django model bootstrap required; no database connections are used')
class ScopeNativePreflightTests(unittest.TestCase):
    def setUp(self):
        self.stack = self.enterContext(ExitStack())
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = root / 'csv-scopes'
        self.stack.enter_context(patch('mta.runtime.csv_scope_operator.ROOT', self.root))
        self.stack.enter_context(patch.dict('os.environ', {'VF_WORK_ROOT': str(root / 'work')}))
        self.args = SimpleNamespace(scope='UptoBPR', date='2026-10-18')
        self.raw = SimpleNamespace(sha256='a' * 64)
        self.csv = SimpleNamespace(predecessor=Mock(return_value=None),
            assemble=Mock(return_value=(self.raw, {})), _parameters=Mock(return_value={'initialization_id': 'owned'}))
        self.report = {'stage_eligibility': {'day': True}}
        self.inspection = self.stack.enter_context(patch('mta.runtime.production_daily.inspect_execution',
            return_value=(self.report, None, None, None)))
        self.stack.enter_context(patch('mta.runtime.daily_preparation.prepare', return_value='prepared'))
        self.request = self.stack.enter_context(patch('mta.runtime.runtime_report_request.request', return_value='placement'))
        self.execute = self.stack.enter_context(patch('mta.runtime.production_report_placement.execute'))
        self.continue_run = self.stack.enter_context(patch('mta.runtime.production_report_placement.continue_run'))

    def inspect(self, decision='START', receipt=None):
        from mta.runtime.csv_scope_operator import inspect_native
        return inspect_native(self.args, self.csv, {}, 'owner', 'reference', {}, {'digest': 'batch'},
            {}, receipt, decision)

    def test_new_input_reaches_native_readiness_with_owned_output_and_streamed_transport(self):
        def check(*args, **kwargs):
            self.assertTrue((self.root.parent / 'pick').is_dir())
            self.assertEqual(args, ('prepared', self.raw.sha256))
            self.assertEqual(kwargs, {'scope_request': 'placement', 'initialization_id': 'owned'})
            return self.report, None, None, None
        self.inspection.side_effect = check
        self.inspect()
        self.assertTrue(self.csv.assemble.call_args.kwargs['_transfer'])
        self.assertFalse(self.csv.assemble.call_args.kwargs['output_file'].parent.exists())
        self.request.assert_called_once_with('UptoBPR', 'csv-UptoBPR-batch', runtime_reports='reference')
        self.assertFalse(self.root.exists())
        self.execute.assert_not_called()
        self.continue_run.assert_not_called()

    def test_native_readiness_failure_is_propagated_without_calculation_or_operation_receipt(self):
        from mta.runtime.production_preflight import PreflightError
        self.report['stage_eligibility']['day'] = False
        with self.assertRaises(PreflightError): self.inspect()
        self.execute.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_continuation_rechecks_the_actual_phase_and_action_cut_without_reassembly(self):
        self.args.scope = 'PostBPR'
        run = SimpleNamespace(pk='owned-run', phase_acceptances=Mock())
        run.phase_acceptances.get.return_value = SimpleNamespace(digest='accepted-bpr')
        with patch('mta.runtime.models.CalculationRun.objects.get', return_value=run), \
                patch('mta.runtime.scoped_actions.revision', return_value=3):
            self.inspect('CONTINUE', {'run_id': 'owned-run'})
        self.continue_run.assert_called_once_with('owned-run', scope='PostBPR',
            expected_phase_digest='accepted-bpr', expected_action_revision=3,
            command_key='csv-PostBPR-batch', worker_reference='vectorflow-csv-scope', inspect_only=True)
        self.csv.assemble.assert_not_called()
        self.inspection.assert_not_called()

    def test_existing_and_prepared_recovery_do_not_reinspect_or_recalculate_accepted_input(self):
        for decision in ('EXISTING', 'RESUME'):
            self.inspect(decision)
        self.csv.assemble.assert_not_called()
        self.inspection.assert_not_called()
        self.continue_run.assert_not_called()
        self.execute.assert_not_called()
        self.assertFalse((self.root.parent / 'pick').exists())

    def test_recover_inspects_the_native_failed_owner_before_any_stop(self):
        self.args.scope='PostBPR'
        run=SimpleNamespace(pk='owned-run',phase_acceptances=Mock())
        run.phase_acceptances.get.return_value=SimpleNamespace(digest='source-bpr')
        receipt=dict(run_id='owned-run',reconciliation={'verification':{
            'recovery_of':'failed','source_phase_digest':'source-bpr','action_revision':3}})
        with patch('mta.runtime.models.CalculationRun.objects.get',return_value=run):
            self.inspect('RECOVER',receipt)
        self.continue_run.assert_called_once_with('owned-run',scope='PostBPR',
            expected_phase_digest='source-bpr',expected_action_revision=3,
            command_key='csv-PostBPR-batch',worker_reference='vectorflow-csv-scope',
            inspect_only=True,recovery_of='failed')
        self.csv.assemble.assert_not_called()
        self.execute.assert_not_called()



@unittest.skipUnless(apps.ready, 'Django bootstrap required; no database connection')
class TerminalArchivePreparationTests(unittest.TestCase):
    def prepare(self, scope, failure=None):
        from mta.runtime.csv_scope_operator import _prepare
        run = SimpleNamespace(pk='owned-run', output_digest='output',
            mdm_input_capture=SimpleNamespace(source=SimpleNamespace(digest='source')))
        csv = Mock()
        root = Path('/frozen-operation')
        receipt = dict(run_id='owned-run', scope=scope, status='CALCULATED')
        events = []
        with ExitStack() as stack:
            stack.enter_context(patch('mta.runtime.models.CalculationRun.objects.get', return_value=run))
            stack.enter_context(patch('mta.presentation.native_publication.identity', return_value={}))
            stack.enter_context(patch('mta.presentation.daily_publication.prepare_reporting_generation', return_value=('publication', 'summary')))
            archive = stack.enter_context(patch('mta.application.native_input_archive.prepare'))
            def archive_call(*args):
                events.append('archive')
                if failure: raise failure
            archive.side_effect = archive_call
            candidate = stack.enter_context(patch('mta.presentation.native_selection.candidate', return_value={}))
            write = stack.enter_context(patch('mta.presentation.native_selection.write', side_effect=lambda *a: events.append('selection')))
            stack.enter_context(patch('mta.presentation.native_selection.read', return_value={'btr_generation': 'generation'}))
            stack.enter_context(patch('mta.runtime.csv_scope_operator.read_json', return_value={'selection_digest': 'selection'}))
            if failure:
                with self.assertRaisesRegex(ValueError, 'original hash differs'):
                    _prepare(csv, root, receipt, binding={'_opening_path': '/opening/original.json'})
                candidate.assert_not_called()
                write.assert_not_called()
                csv.atomic_json.assert_not_called()
                self.assertEqual(receipt['status'], 'CALCULATED')
            else:
                value = _prepare(csv, root, receipt, binding={'_opening_path': '/opening/original.json'})
                self.assertEqual(value['status'], 'PREPARED')
                self.assertEqual(events, ['archive', 'selection'])
            archive.assert_called_once_with(run, '/opening/original.json', root / 'native-day.json')

    def test_full_and_both_completed_tails_prepare_archive_before_selection(self):
        for scope in ('Full', 'PostBPR', 'PostDBM'):
            with self.subTest(scope=scope): self.prepare(scope)

    def test_archive_identity_failure_keeps_calculated_owner_without_selection(self):
        for scope in ('Full', 'PostBPR', 'PostDBM'):
            with self.subTest(scope=scope): self.prepare(scope, ValueError('original hash differs'))


@unittest.skipUnless(apps.ready, 'Django bootstrap required; mocks and temporary files only')
class ScopeReconciliationTests(unittest.TestCase):
    def setUp(self):
        from mta.runtime import csv_scope_operator as operator
        from mta.serialization import digest
        from datetime import date, datetime, timezone
        self.op = operator
        self.stack = self.enterContext(ExitStack())
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.object(operator, 'ROOT', self.root))
        self.args = SimpleNamespace(scope='PostBPR', date='2026-10-18', resume=False,
                                    _batch_digest='batch')
        self.owner = SimpleNamespace(pk='init', source=SimpleNamespace(pk=3, digest='source'))
        self.binding = dict(_binding_digest='binding', configuration_digest='configuration')
        self.reference = {'reference': 'original'}
        self.receipt = dict(schema='vectorflow-csv-scope-operation-v1', date=self.args.date,
            initial_scope='UptoBPR', scope='PostBPR', status='FAILED', run_id='run',
            binding_digest='binding', batch_digest='batch', profile_digest=digest(self.reference),
            native_sha256='native', error='original failure', results={'UptoBPR': {'run_id': 'run'}},
            parameters=dict(initialization_id='init', source_digest='source', configuration_digest='configuration',
                execution_revision='csv-scope-batch', pick_output_root='pick', predecessor_id=None,
                predecessor_output_digest=None))
        self.attempt = SimpleNamespace(id='failed', pk='failed', run_id='run', scope='PostBPR',
            command_key='csv-PostBPR-batch', attempt_no=1, recovery_of_id=None, expected_phase='BPR',
            expected_receipt_digest='bpr', input_digest='input', input_manifest_digest='manifest',
            compatibility_digest='compat', action_revision=0, worker_reference='vectorflow-csv-scope',
            status='FAILED', failure={'message': 'retained'}, revision_before=[0]*5,
            revision_after=[0,0,0,1,0], revision_closed=[0,0,0,2,0],
            created_at=datetime(2026,10,18,tzinfo=timezone.utc), finished_at=None)
        self.source_attempt = SimpleNamespace(pk='source-attempt', status='RELEASED', scope='UptoBPR',
            command_key='csv-UptoBPR-batch', compatibility_digest='compat')
        self.phase = SimpleNamespace(pk='bpr-id', digest='bpr', attempt=self.source_attempt,
                                     snapshot=SimpleNamespace(state_digest='snapshot'))
        self.run = SimpleNamespace(pk='run', status='RUNNING', business_date=date(2026,10,18),
            predecessor_id=None, mdm_input_capture=SimpleNamespace(source_id=3),
            input_digest='input', input_manifest_digest='manifest', phase_acceptances=Mock(), scope_attempts=Mock())
        self.run.phase_acceptances.select_related.return_value.get.return_value = self.phase
        self.run.phase_acceptances.get.return_value = self.phase
        self.run.scope_attempts.select_for_update.return_value.order_by.return_value.first.return_value = self.attempt
        self.run.scope_attempts.filter.return_value.exists.return_value = False
        self.captured = dict(scope='UptoBPR', command_key='csv-UptoBPR-batch', runtime_reports=self.reference,
                             compatibility_digest='compat')
        self.raw = dict(scope_request=self.captured, initialization_binding=dict(id='init', source_digest='source',
            configuration_digest='configuration'), daily_input_sha256='native', pick_output_root='pick', lineage={})
        self.outer = dict(registration=dict(registration_digest='registration', initialization_id='init', source_digest='source'))
        self.stack.enter_context(patch.object(operator, 'read_json', wraps=operator.read_json))
        (self.root/'registration.json').write_text(json.dumps(dict(reference=self.reference, registration_digest='registration')))
        self.manager = self.stack.enter_context(patch('mta.runtime.models.CalculationRun.objects'))
        self.manager.filter.return_value.__getitem__.return_value = [self.run]
        self.manager.select_for_update.return_value.get.return_value = self.run
        self.lock = self.stack.enter_context(patch('mta.runtime.scope_execution._source_lock'))
        self.stack.enter_context(patch('mta.runtime.input_reader.read_input', return_value=self.raw))
        self.stack.enter_context(patch('mta.runtime.runtime_report_request.validate_request', side_effect=lambda value, **kw:value))
        self.stack.enter_context(patch('mta.runtime.runtime_report_registered_request.read_captured', return_value=self.outer))
        self.stack.enter_context(patch('mta.runtime.production_scope.captured_run'))
        self.stack.enter_context(patch('mta.runtime.temporal.resolved_pick_root', side_effect=lambda value:value))
        self.stack.enter_context(patch('mta.runtime.scope_execution.head', return_value=('DBM','dbm')))
        self.stack.enter_context(patch('mta.runtime.scoped_actions.revision', return_value=0))
        self.stack.enter_context(patch('mta.runtime.scope_revisions.require_current'))
        self.phase_reader = self.stack.enter_context(patch('mta.runtime.production_scope._phase', return_value=self.phase))
        self.producer = self.stack.enter_context(patch('mta.runtime.production_report_placement.execute', side_effect=AssertionError('producer')))
        self.continuation = self.stack.enter_context(patch('mta.runtime.production_report_placement.continue_run'))
        self.manifest = {'digest':'batch','files':{'READY':{'sha256':'native','bytes':0}}}
        (self.root/'original').mkdir()
        (self.root/'original'/'READY').write_bytes(b'')
        (self.root/'original'/'snapshot.json').write_text(json.dumps(self.manifest))
        (self.root/'native-day.json').write_bytes(b'{}')
        self.csv = SimpleNamespace(file_identity=Mock(return_value={'sha256':'native','bytes':0}))
        from mta.runtime.daily_feed import atomic_json
        self.csv.atomic_json = atomic_json

    def authenticate(self):
        return self.op._reconciliation_owner(self.args,self.binding,self.owner,self.reference,self.receipt)

    def state(self):
        return self.op._reconciliation_state(self.args,self.run,self.captured)

    def test_frozen_and_captured_identity_negatives(self):
        self.assertEqual(self.authenticate(), (self.run,self.captured))
        for changes in ({'date':'2026-10-19'}, {'binding_digest':'foreign'}, {'batch_digest':'foreign'}):
            invalid=deepcopy(self.receipt);invalid.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.op._frozen_operation(self.args,self.csv,self.binding,self.manifest,self.root,invalid)
        for component,field in (('initialization_binding','id'),('initialization_binding','source_digest'),
                ('initialization_binding','configuration_digest'),('scope_request','scope'),
                ('scope_request','command_key'),('scope_request','runtime_reports')):
            previous=self.raw[component][field];self.raw[component][field]='foreign'
            with self.subTest(component=component,field=field),self.assertRaises(ValueError):self.authenticate()
            self.raw[component][field]=previous
        for field in ('daily_input_sha256','pick_output_root'):
            previous=self.raw[field];self.raw[field]='foreign'
            with self.subTest(field=field),self.assertRaises(ValueError):self.authenticate()
            self.raw[field]=previous
        self.outer['registration']['registration_digest']='foreign'
        with self.assertRaises(ValueError):self.authenticate()
        self.csv.file_identity.side_effect=lambda path: (
            {'sha256':'foreign','bytes':0} if Path(path).name=='native-day.json'
            else {'sha256':'native','bytes':0})
        with self.assertRaisesRegex(ValueError,'native input'):
            self.op._frozen_operation(self.args,self.csv,self.binding,self.manifest,self.root,self.receipt)
        self.csv.file_identity.side_effect=None
        (self.root/'original'/'snapshot.json').write_text('{"digest":"foreign"}')
        with self.assertRaisesRegex(ValueError,'originals'):
            self.op._frozen_operation(self.args,self.csv,self.binding,self.manifest,self.root,self.receipt)
        self.producer.assert_not_called();self.continuation.assert_not_called()

    def test_real_snapshot_owned_roster_receipt_and_every_file_are_authenticated(self):
        from mta.runtime import daily_feed as csv
        from mta.application.production_csv_contract import SCHEMA_VERSION
        incoming=self.root/'incoming';incoming.mkdir()
        (incoming/'READY').write_bytes(b'')
        (incoming/'batch.json').write_text(json.dumps(dict(schema=SCHEMA_VERSION,
            feeds={'facts.csv':'PRESENT'})))
        (incoming/'facts.csv').write_bytes(b'SKUCode,Value\nA,1\n')
        root=self.root/'real-frozen'
        _,manifest=csv.snapshot(incoming,root/'original',self.root)
        (root/'native-day.json').write_bytes(b'{"frozen":"native"}')
        receipt=deepcopy(self.receipt)
        receipt.update(batch_digest=manifest['digest'],
                       native_sha256=csv.file_identity(root/'native-day.json')['sha256'])
        # The incoming reader stays strict: snapshot.json belongs only to the frozen reader.
        with patch('mta.runtime.daily_feed.batch_contract'):
            with self.assertRaisesRegex(ValueError,'file roster'):
                csv._batch(root/'original',self.binding,self.args.date,root)
        self.op._frozen_operation(self.args,csv,self.binding,manifest,root,receipt)
        original={path.name:path.read_bytes() for path in (root/'original').iterdir()}
        for name in ('READY','batch.json','facts.csv','snapshot.json'):
            target=root/'original'/name
            target.write_bytes(json.dumps({**manifest,'digest':'foreign'}).encode()
                               if name=='snapshot.json' else original[name]+b' ')
            with self.subTest(name=name),self.assertRaises(ValueError):
                self.op._frozen_operation(self.args,csv,self.binding,manifest,root,receipt)
            target.write_bytes(original[name])
        extra=root/'original'/'extra.json';extra.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'originals'):
            self.op._frozen_operation(self.args,csv,self.binding,manifest,root,receipt)
        extra.unlink()
        (root/'native-day.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'native input'):
            self.op._frozen_operation(self.args,csv,self.binding,manifest,root,receipt)
        self.assertEqual({path.name:path.read_bytes() for path in (root/'original').iterdir()},original)
        self.producer.assert_not_called();self.continuation.assert_not_called()

    def test_exact_failed_tail_and_worker_action_head_negatives(self):
        proof,result=self.state()
        self.assertEqual(proof['outcome'],'RECOVERABLE');self.assertEqual(proof['recovery_of'],'failed')
        self.assertEqual(proof['accepted_head'],['DBM','dbm']);self.assertIsNone(result)
        for field,value in (('scope','PostDBM'),('status','ACTIVE'),('command_key','foreign'),
                ('compatibility_digest','foreign'),('action_revision',1),('input_digest','foreign'),
                ('input_manifest_digest','foreign'),('worker_reference','foreign'),('recovery','already-claimed')):
            prior=getattr(self.attempt,field,None);setattr(self.attempt,field,value)
            with self.subTest(field=field),self.assertRaises(ValueError):self.state()
            if field=='recovery':delattr(self.attempt,field)
            else:setattr(self.attempt,field,prior)
        with patch('mta.runtime.scope_execution.head',return_value=('DAY_FINAL','foreign')):
            with self.assertRaises(ValueError):self.state()
        self.run.scope_attempts.filter.return_value.exists.return_value=True
        with self.assertRaisesRegex(ValueError,'active worker'):self.state()

    def test_append_before_change_crash_reuse_and_idempotent_reconciliation(self):
        from contextlib import nullcontext
        self.csv.atomic_json(self.root/'operation.json',self.receipt)
        with patch('django.db.transaction.atomic',side_effect=nullcontext), \
                patch.object(self.op,'_reconciliation_owner',return_value=(self.run,self.captured)):
            with patch.object(self.op,'_save',side_effect=RuntimeError('journal crash')):
                with self.assertRaisesRegex(RuntimeError,'journal crash'):
                    self.op._reconcile(self.args,self.csv,self.binding,self.owner,self.reference,
                        self.manifest,self.root,self.receipt,lambda:None)
            self.assertEqual(self.op.read_json(self.root/'operation.json'),self.receipt)
            self.assertEqual(len(list((self.root/'reconciliations').glob('*.json'))),1)
            repaired=self.op._reconcile(self.args,self.csv,self.binding,self.owner,self.reference,
                self.manifest,self.root,self.receipt,lambda:None)
            again=self.op._reconcile(self.args,self.csv,self.binding,self.owner,self.reference,
                self.manifest,self.root,repaired,lambda:None)
            self.assertEqual(again,repaired)
            self.assertEqual(self.op._verify_recovery(self.args,self.csv,self.binding,self.owner,self.reference,
                self.manifest,self.root,repaired)['recovery_of'],'failed')
            with patch('mta.runtime.scope_execution.head',return_value=('BPR','changed')):
                with self.assertRaisesRegex(ValueError,'changed'):
                    self.op._verify_recovery(self.args,self.csv,self.binding,self.owner,self.reference,
                        self.manifest,self.root,repaired)
        self.producer.assert_not_called();self.continuation.assert_not_called()
        evidence=self.op.read_json(next((self.root/'reconciliations').glob('*.json')))
        self.assertEqual(evidence['original_operation'],self.receipt)
        self.assertEqual(evidence['verification']['latest_attempt']['failure'],{'message':'retained'})

    def test_committed_reader_repairs_journal_without_execution(self):
        from contextlib import nullcontext
        self.run.status='SUCCEEDED';self.attempt.status='RELEASED'
        result=dict(run_id='run',scope='PostBPR',attempt_id='failed',output_digest='terminal')
        with patch('mta.runtime.production_report_placement._continued',return_value=result) as reader, \
                patch('django.db.transaction.atomic',side_effect=nullcontext), \
                patch.object(self.op,'_reconciliation_owner',return_value=(self.run,self.captured)):
            repaired=self.op._reconcile(self.args,self.csv,self.binding,self.owner,self.reference,
                self.manifest,self.root,self.receipt,lambda:None)
            self.assertEqual(repaired['status'],'CALCULATED')
            self.assertEqual(repaired['results']['PostBPR'],result)
            self.assertEqual(self.op._reconcile(self.args,self.csv,self.binding,self.owner,self.reference,
                self.manifest,self.root,repaired,lambda:None),repaired)
            reader.assert_called()
        self.producer.assert_not_called();self.continuation.assert_not_called()

    def test_gate_requires_explicit_resume_and_exact_identity(self):
        from mta.serialization import digest
        receipt=deepcopy(self.receipt);receipt['status']='RECOVERABLE'
        options=dict(scope='PostBPR',binding_digest='binding',batch_digest='batch',
                     profile_digest=digest(self.reference),resume=True)
        self.assertEqual(check_request(receipt,**options),'RECOVER')
        for field,value in (('resume',False),('profile_digest','foreign'),('batch_digest','foreign'),
                ('binding_digest','foreign'),('scope','PostDBM')):
            with self.subTest(field=field),self.assertRaises(ValueError):
                check_request(receipt,**{**options,field:value})
        self.args.scope='Full'
        with self.assertRaises(ValueError):
            self.op._frozen_operation(self.args,self.csv,self.binding,self.manifest,self.root,self.receipt)

    def test_recovery_routes_exact_failed_identity_only_to_continuation(self):
        proof,_=self.state()
        receipt=deepcopy(self.receipt);receipt['status']='RECOVERABLE'
        self.continuation.return_value=dict(run_id='run',scope='PostBPR',status='SUCCEEDED')
        with patch.object(self.op,'_verify_recovery',return_value=proof) as verify, \
                patch('mta.runtime.models.CalculationRun.objects.get',return_value=self.run), \
                patch('mta.runtime.scoped_actions.revision',return_value=99):
            result=self.op._calculate(self.args,self.csv,self.binding,self.owner,self.reference,{},
                self.manifest,self.root,receipt,'RECOVER')
        verify.assert_called_once()
        self.continuation.assert_called_once_with('run',scope='PostBPR',expected_phase_digest='bpr',
            expected_action_revision=0,command_key='csv-PostBPR-batch',
            worker_reference='vectorflow-csv-scope',recovery_of='failed')
        self.assertEqual(result['status'],'CALCULATED')
        self.producer.assert_not_called()

    def test_released_prefix_uses_existing_readers_and_no_producer(self):
        self.args.scope='UptoBPR';self.attempt=self.source_attempt
        # Supply the full finite worker evidence while retaining released ownership.
        for name,value in vars(self.run.scope_attempts.select_for_update.return_value.order_by.return_value.first.return_value).copy().items():
            if not hasattr(self.attempt,name):setattr(self.attempt,name,value)
        self.attempt.id=self.attempt.pk;self.attempt.status='RELEASED'
        self.run.scope_attempts.select_for_update.return_value.order_by.return_value.first.return_value=self.attempt
        with patch('mta.runtime.scope_execution.head',return_value=('BPR','bpr')), \
                patch('mta.runtime.scoped_pick_files.read',return_value=SimpleNamespace(digest='pick')) as pick, \
                patch('mta.runtime.runtime_report_placement_publication.read',
                    return_value=SimpleNamespace(pk='publication',digest='published')) as publication:
            proof,result=self.state()
        self.assertEqual(proof['outcome'],'CALCULATED')
        self.assertEqual(result['phase_acceptance_digest'],'bpr')
        pick.assert_called_once_with('bpr-id',expected_digest='bpr')
        publication.assert_called_once_with('run',placement='PostBPR',verify_bytes=True)
        self.producer.assert_not_called();self.continuation.assert_not_called()

    def test_public_reconcile_parser_dispatches_without_execute_entry(self):
        from io import StringIO
        with patch('sys.argv',['scope-operator','reconcile','--date',self.args.date,'--scope','PostBPR']), \
                patch.object(self.op,'operation',return_value={'status':'RECOVERABLE'}) as operation, \
                patch('django.setup'),patch('sys.stdout',new_callable=StringIO) as output:
            self.op.main()
        self.assertEqual(operation.call_args.args[0].operation,'reconcile')
        self.assertFalse(operation.call_args.args[0].resume)
        self.assertEqual(json.loads(output.getvalue()),{'status':'RECOVERABLE'})
        self.producer.assert_not_called();self.continuation.assert_not_called()


if __name__ == '__main__':
    unittest.main()
