"""Exercise the real PowerShell operator script at its Docker process boundary.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell7 required for operator boundary checks')
class CsvLauncherTests(unittest.TestCase):
    shell = 'pwsh'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'release').mkdir()
        shutil.copyfile(ROOT / 'vf.ps1', self.root / 'vf.ps1')
        shutil.copyfile(ROOT / 'release/powershell_compat.ps1', self.root / 'release/powershell_compat.ps1')
        (self.root / '.env').write_text('VF_PROJECT=test\nCOMPOSE_FILE="compose.yaml;extra.json"\nEMAIL_PASS=preserve-this-exactly\n')
        shutil.copyfile(ROOT / 'release/csv_onboarding.py', self.root / 'release/csv_onboarding.py')
        self.pack = self.root / 'pack';self.pack.mkdir();(self.pack / 'opening').mkdir()
        native=b'original-opening';consumer=b'original-consumer-opening'
        (self.pack / 'native-opening.json').write_bytes(native)
        (self.pack / 'consumer-opening.json').write_bytes(consumer)
        sha=hashlib.sha256(native).hexdigest()
        (self.pack / 'opening/opening-manifest.json').write_text(json.dumps(dict(native_input_sha256=sha,configuration_digest='c'*64,recipe_digest='d'*64)))
        (self.pack / 'binding-template.json').write_text(json.dumps(dict(opening_file='native-opening.json',opening_sha256=sha,consumer_opening_file='consumer-opening.json',consumer_opening_sha256=hashlib.sha256(consumer).hexdigest(),configuration_digest='c'*64,initialization_id='replace',source_digest='replace')))
        (self.pack / 'permissions.json').write_text('{}')
        self.state=self.root/'state';self.state.mkdir()
        cfg={'name':'test','x-vectorflow-csv':{'input_dir':str(self.pack)},'x-vectorflow-daily':{'state_dir':str(self.state)}}
        (self.root / 'config.json').write_text(json.dumps(cfg))
        (self.root / 'initial.json').write_text(json.dumps(dict(status='INITIALIZED',input_sha256=sha,opening_id='new-opening',source_digest='e'*64)))
        (self.root / 'validated.json').write_text(json.dumps(dict(status='INPUT_VALIDATED_NO_DATABASE_CHANGE',input_sha256=sha)))
        # Only the unchanged child daily operator is stubbed: prove argument
        # delegation rather than running a second native day campaign here.
        (self.root / 'release/run_daily.ps1').write_text("param($BusinessDate,[switch]$InspectOnly,[switch]$Resume)\n@{date=$BusinessDate;inspect=[bool]$InspectOnly;resume=[bool]$Resume}|ConvertTo-Json|Set-Content ./daily-call.json\n")
        (self.root / 'driver.ps1').write_text('''
param($Failure='', $Operation='csv-init', $Date='', [switch]$Resume)
$ErrorActionPreference='Stop'
function global:docker {
    $call=@($args)
    ConvertTo-Json -InputObject $call -Compress | Add-Content ./calls.jsonl
    $global:LASTEXITCODE=0
    if ($call -contains 'release.initialize_csv') {
        $receipt=Get-Content ./state/onboarding.json -Raw|ConvertFrom-Json
        if ($Failure -eq 'wrong-database') { $global:LASTEXITCODE=1; return }
        if ($Failure -eq 'validation') { $global:LASTEXITCODE=1; '{"issue":"CSV column invalid"}'; return }
        $receipt.phase='REGISTRATION'
        if ($Failure -eq 'registration') { $receipt|ConvertTo-Json -Depth 30|Set-Content ./state/onboarding.json; $global:LASTEXITCODE=1; return }
        $receipt|Add-Member -Force -NotePropertyName registration -NotePropertyValue @{status='registered'}
        $receipt.phase='INITIALIZATION'
        if ($Failure -eq 'families') { $receipt|ConvertTo-Json -Depth 30|Set-Content ./state/onboarding.json; $global:LASTEXITCODE=1; return }
        $receipt|Add-Member -Force -NotePropertyName initialization -NotePropertyValue (Get-Content ./initial.json -Raw|ConvertFrom-Json)
        $receipt|Add-Member -Force -NotePropertyName families -NotePropertyValue @{status='MDM_FAMILIES_READY'}
        $receipt.phase='CONFIGURATION'
        $receipt|ConvertTo-Json -Depth 30|Set-Content ./state/onboarding.json
        $receipt|ConvertTo-Json -Depth 30
        return
    }
    if ($Failure -eq 'configuration' -and $call -contains '--env-file') { $global:LASTEXITCODE=1; return }
    if ($call -contains '/helper.py') {
        $path=(Get-Content ./config.json -Raw|ConvertFrom-Json).'x-vectorflow-csv'.input_dir
        $null=New-Item -ItemType Directory -Force "$path/opening"
        '{}'|Set-Content "$path/opening/opening-manifest.json"
        return
    }
    if ($call -contains 'complete') { if ($Failure -eq 'families') { $global:LASTEXITCODE=1; return }; '{"status":"MDM_FAMILIES_READY"}'; return }
    if ($call -contains 'check') { '{"status":"INITIALIZED_MASTER_SERVING_READY"}'; return }
    if ($call -contains 'inspect') { if ($Failure -eq 'wrong-database') { $global:LASTEXITCODE=1; return }; '{"status":"OPENING_RECONCILED"}'; return }
    if ($call -contains '--quiet') { return }
    if ($call -contains 'config') { Get-Content ./config.json -Raw; return }
    if ($call -contains '--validate-only') { Get-Content ./validated.json -Raw; return }
    if ($call -contains '--inspect') { '{"status":"INPUT_CONTRACT_VALIDATED_NOT_INSTALLED"}'; return }
    if ($call -contains 'release.register_mta') { '{"status":"registered"}'; return }
    if ($call -contains 'initialize_production') { Get-Content ./initial.json -Raw; return }
}
if ($Operation -eq 'csv-day') { & ./vf.ps1 $Operation $Date -Resume }
else { & ./vf.ps1 $Operation -Resume:$Resume }
''')

    def tearDown(self):
        self.temp.cleanup()

    def run_launcher(self, failure='', operation='csv-init', date='', resume=False):
        env=dict(os.environ)
        for key in ('COMPOSE_FILE','COMPOSE_PATH_SEPARATOR'):
            env.pop(key,None)
        if self.shell == 'powershell.exe':
            # Do not load PS7 modules inherited from this test runner into PS5.
            env.pop('PSModulePath', None)
            env.pop('PSMODULEPATH', None)
        return subprocess.run([self.shell,'-NoProfile','-File',str(self.root/'driver.ps1'),'-Failure',failure,'-Operation',operation,'-Date',date] + (['-Resume'] if resume else []),cwd=self.root,env=env,capture_output=True,text=True)

    def calls(self):
        p=self.root/'calls.jsonl'
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def test_initialization_hides_bindings_and_preserves_existing_configuration(self):
        r=self.run_launcher();self.assertEqual(r.returncode,0,r.stderr)
        calls=self.calls()
        self.assertEqual(sum('release.initialize_csv' in c for c in calls),1)
        self.assertFalse(any('--validate-only' in c or '--inspect' in c or 'complete' in c for c in calls))
        self.assertEqual(sum('release.initialize_csv' in c for c in calls),1)
        self.assertEqual(sum('stop' in c for c in calls),1)
        self.assertEqual(sum('up' in c for c in calls),1)
        self.assertFalse(any('build' in c or 'install' in c for c in calls))
        self.assertLess(next(i for i,c in enumerate(calls) if 'release.initialize_csv' in c), next(i for i,c in enumerate(calls) if 'up' in c))
        receipt=json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(receipt['status'],'INITIALIZED')
        env=(self.root/'.env').read_text()
        self.assertIn('EMAIL_PASS=preserve-this-exactly',env)
        self.assertIn('compose.yaml;extra.json;',env)
        self.assertIn('MTA_SELECTION_FILE=""',env)
        binding=json.loads((self.pack/'binding.json').read_text(encoding='utf-8-sig'))
        self.assertFalse((self.pack/'binding.json').read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertEqual(binding['initialization_id'],'new-opening')
        override=json.loads((self.pack/'compose.csv.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(set(override['services']),{'mta','mta-install'})
        self.assertEqual(override['services']['mta']['environment']['VF_MDM_SOURCE_DIGEST'],'e'*64)
        before=len(calls)
        r=self.run_launcher();self.assertNotEqual(r.returncode,0)
        self.assertFalse(any('stop' in c or 'release.register_mta' in c for c in self.calls()[before:]))

    def test_project_relative_input_and_operations_resolve_to_this_checkout(self):
        cfg=json.loads((self.root/'config.json').read_text())
        cfg['x-vectorflow-csv']['input_dir']='./pack'
        cfg['x-vectorflow-daily']['state_dir']='./state'
        (self.root/'config.json').write_text(json.dumps(cfg))
        result=self.run_launcher()
        self.assertEqual(result.returncode,0,result.stderr)
        receipt=json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(receipt['input_dir'],str(self.pack).replace('\\','/'))
        env=(self.root/'.env').read_text()
        self.assertIn('VF_DAILY_INPUT_DIR="'+str(self.pack).replace('\\','/')+'"',env)
        self.assertIn('VF_DAILY_STATE_DIR="'+str(self.state).replace('\\','/')+'"',env)
        self.assertEqual(sum('release.initialize_csv' in c for c in self.calls()),1)

    def test_resume_finishes_same_opening_without_registration_or_loading(self):
        self.assertNotEqual(self.run_launcher('configuration').returncode,0)
        before=len(self.calls())
        result=self.run_launcher(resume=True)
        self.assertEqual(result.returncode,0,result.stderr)
        calls=self.calls()[before:]
        self.assertFalse(any('release.register_mta' in c or 'initialize_production' in c for c in calls))
        self.assertLess(next(i for i,c in enumerate(calls) if 'release.initialize_csv' in c), next(i for i,c in enumerate(calls) if 'stop' in c))
        self.assertTrue(any('--resume' in c for c in calls))

    def test_resume_wrong_database_never_stops_or_bootstraps(self):
        self.assertEqual(self.run_launcher().returncode,0)
        before=len(self.calls())
        old=(self.state/'onboarding.json').read_bytes()
        self.assertNotEqual(self.run_launcher('wrong-database',resume=True).returncode,0)
        self.assertFalse(any('stop' in c or 'complete' in c for c in self.calls()[before:]))
        self.assertEqual(json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))['initialization'],json.loads(old)['initialization'])

    def test_family_failure_never_starts_metadata_or_claims_initialized(self):
        self.assertNotEqual(self.run_launcher('families').returncode,0)
        self.assertFalse(any('up' in c for c in self.calls()))
        receipt=json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))
        self.assertEqual((receipt['status'],receipt['phase']),('STOPPED','INITIALIZATION'))

    def test_bad_csv_validation_never_stops_api_or_registers_namespace(self):
        r=self.run_launcher('validation');self.assertNotEqual(r.returncode,0)
        self.assertFalse(any('stop' in c or 'release.register_mta' in c for c in self.calls()))
        self.assertEqual(json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))['phase'],'CSV')
        self.assertNotIn('VF_DAILY_INPUT_DIR', (self.root/'.env').read_text())
        self.assertIn('CSV column invalid',(self.state/'onboarding-docker.log').read_text(encoding='utf-8-sig'))
        r=self.run_launcher();self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(len(list(self.state.glob('onboarding-rejected-*.json'))),1)

    def test_registration_failure_preserves_checkpoint_and_never_initializes_or_retries(self):
        r=self.run_launcher('registration');self.assertNotEqual(r.returncode,0)
        self.assertFalse(any('initialize_production' in c and '--validate-only' not in c for c in self.calls()))
        self.assertEqual(json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))['phase'],'REGISTRATION')
        before=len(self.calls());self.assertNotEqual(self.run_launcher().returncode,0)
        self.assertFalse(any('release.register_mta' in c for c in self.calls()[before:]))

    def test_explicit_resume_can_reconcile_registration_commit_before_receipt_field(self):
        self.assertNotEqual(self.run_launcher('registration').returncode,0)
        receipt=json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(receipt['phase'],'REGISTRATION')
        self.assertNotIn('registration',receipt)
        before=len(self.calls())
        result=self.run_launcher(resume=True)
        self.assertEqual(result.returncode,0,result.stderr)
        calls=self.calls()[before:]
        self.assertTrue(any('release.initialize_csv' in c and '--resume' in c for c in calls))
        self.assertFalse(any('release.register_mta' in c or 'initialize_production' in c for c in calls))

    def test_daily_entry_delegates_to_existing_repository_orchestrator(self):
        r=self.run_launcher(operation='csv-day',date='2026-10-19');self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads((self.root/'daily-call.json').read_text(encoding='utf-8-sig')),dict(date='2026-10-19',inspect=False,resume=True))
        self.assertFalse(any('stop' in c or 'release.register_mta' in c for c in self.calls()))

    def test_configuration_failure_preserves_original_env_and_committed_receipt(self):
        original=(self.root/'.env').read_bytes()
        r=self.run_launcher('configuration');self.assertNotEqual(r.returncode,0)
        self.assertEqual((self.root/'.env').read_bytes(),original)
        self.assertEqual(list(self.root.glob('.env.csv-*')),[])
        receipt=json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(receipt['phase'],'CONFIGURATION')
        self.assertEqual(receipt['initialization']['opening_id'],'new-opening')

    def test_new_sample_pairs_its_receipts_when_no_state_directory_was_selected(self):
        cfg=json.loads((self.root/'config.json').read_text())
        cfg['x-vectorflow-csv']['input_dir']=str(self.root/'new-pack')
        cfg['x-vectorflow-daily']['state_dir']=''
        (self.root/'config.json').write_text(json.dumps(cfg))
        result=self.run_launcher(operation='csv-sample')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('VF_DAILY_STATE_DIR="'+str(self.root/'new-pack').replace('\\','/')+'-operations"',(self.root/'.env').read_text())

    def test_sample_generation_is_explicit_and_never_touches_business_services(self):
        target=self.root/'fresh-sample'
        cfg=json.loads((self.root/'config.json').read_text());cfg['x-vectorflow-csv']['input_dir']=str(target)
        (self.root/'config.json').write_text(json.dumps(cfg))
        r=self.run_launcher(operation='csv-sample');self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue((target/'opening/opening-manifest.json').exists())
        self.assertIn('VF_CSV_INPUT_DIR="'+str(target).replace('\\','/')+'"',(self.root/'.env').read_text())
        self.assertFalse(any('stop' in c or 'release.register_mta' in c for c in self.calls()))


@unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'), 'Windows PowerShell5.1 required')
class WindowsPowerShellCsvLauncherTests(CsvLauncherTests):
    shell = 'powershell.exe'


if __name__=='__main__':unittest.main()
