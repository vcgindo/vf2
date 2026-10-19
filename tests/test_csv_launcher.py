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
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'release').mkdir()
        shutil.copyfile(ROOT / 'vf.ps1', self.root / 'vf.ps1')
        (self.root / '.env').write_text('VF_PROJECT=test\nCOMPOSE_FILE="compose.yaml;extra.json"\nEMAIL_PASS=preserve-this-exactly\n')
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
param($Failure='', $Operation='csv-init', $Date='')
$ErrorActionPreference='Stop'
function global:docker {
    $call=@($args)
    ConvertTo-Json -InputObject $call -Compress | Add-Content ./calls.jsonl
    $global:LASTEXITCODE=0
    if ($Failure -eq 'validation' -and $call -contains '--validate-only') { $global:LASTEXITCODE=1; '{"issue":"CSV column invalid"}'; return }
    if ($Failure -eq 'registration' -and $call -contains 'release.register_mta') { $global:LASTEXITCODE=1; return }
    if ($Failure -eq 'configuration' -and $call -contains '--env-file') { $global:LASTEXITCODE=1; return }
    if ($call -contains '/helper.py') {
        $path=(Get-Content ./config.json -Raw|ConvertFrom-Json).'x-vectorflow-csv'.input_dir
        $null=New-Item -ItemType Directory -Force "$path/opening"
        '{}'|Set-Content "$path/opening/opening-manifest.json"
        return
    }
    if ($call -contains '--quiet') { return }
    if ($call -contains 'config') { Get-Content ./config.json -Raw; return }
    if ($call -contains '--validate-only') { Get-Content ./validated.json -Raw; return }
    if ($call -contains '--inspect') { '{"status":"INPUT_CONTRACT_VALIDATED_NOT_INSTALLED"}'; return }
    if ($call -contains 'release.register_mta') { '{"status":"registered"}'; return }
    if ($call -contains 'initialize_production') { Get-Content ./initial.json -Raw; return }
}
if ($Operation -eq 'csv-day') { & ./vf.ps1 $Operation $Date -Resume }
else { & ./vf.ps1 $Operation }
''')

    def tearDown(self):
        self.temp.cleanup()

    def run_launcher(self, failure='', operation='csv-init', date=''):
        env=dict(os.environ)
        for key in ('COMPOSE_FILE','COMPOSE_PATH_SEPARATOR'):
            env.pop(key,None)
        return subprocess.run(['pwsh','-NoProfile','-File',str(self.root/'driver.ps1'),'-Failure',failure,'-Operation',operation,'-Date',date],cwd=self.root,env=env,capture_output=True,text=True)

    def calls(self):
        p=self.root/'calls.jsonl'
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def test_initialization_hides_bindings_and_preserves_existing_configuration(self):
        r=self.run_launcher();self.assertEqual(r.returncode,0,r.stderr)
        calls=self.calls()
        self.assertEqual(sum('--validate-only' in c for c in calls),1)
        self.assertEqual(sum('release.register_mta' in c for c in calls),1)
        self.assertEqual(sum('stop' in c for c in calls),1)
        self.assertFalse(any('up' in c or 'build' in c or 'install' in c for c in calls))
        receipt=json.loads((self.state/'onboarding.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(receipt['status'],'INITIALIZED')
        env=(self.root/'.env').read_text()
        self.assertIn('EMAIL_PASS=preserve-this-exactly',env)
        self.assertIn('compose.yaml;extra.json;',env)
        self.assertIn('MTA_SELECTION_FILE="/var/lib/vectorflow/selection.json"',env)
        binding=json.loads((self.pack/'binding.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(binding['initialization_id'],'new-opening')
        override=json.loads((self.pack/'compose.csv.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(set(override['services']),{'mta','mta-install'})
        self.assertEqual(override['services']['mta']['environment']['VF_MDM_SOURCE_DIGEST'],'e'*64)
        before=len(calls)
        r=self.run_launcher();self.assertNotEqual(r.returncode,0)
        self.assertFalse(any('stop' in c or 'release.register_mta' in c for c in self.calls()[before:]))

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

    def test_sample_generation_is_explicit_and_never_touches_business_services(self):
        target=self.root/'fresh-sample'
        cfg=json.loads((self.root/'config.json').read_text());cfg['x-vectorflow-csv']['input_dir']=str(target)
        (self.root/'config.json').write_text(json.dumps(cfg))
        r=self.run_launcher(operation='csv-sample');self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue((target/'opening/opening-manifest.json').exists())
        self.assertIn('VF_CSV_INPUT_DIR="'+str(target).replace('\\','/')+'"',(self.root/'.env').read_text())
        self.assertFalse(any('stop' in c or 'release.register_mta' in c for c in self.calls()))


if __name__=='__main__':unittest.main()
