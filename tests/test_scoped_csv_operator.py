"""Scope operator identity, no-replay and command-routing boundaries; no DB/day."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
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
}
'''
            (root / 'release/run_csv_scope.ps1').write_text(source[:start] + boundary + source[end:])
            (root / 'runner.ps1').write_text('''
function docker { $global:LASTEXITCODE=0; Get-Content -LiteralPath (Join-Path $env:VECTORFLOW_OPERATOR_ROOT 'config.json') -Raw }
if ($env:VECTORFLOW_OPERATOR_CASE -eq 'existing-invalid') {
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


if __name__ == '__main__':
    unittest.main()
