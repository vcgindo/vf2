"""Windows operator syntax/argument/maintenance boundary in both supported shells."""
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]

FAKE = r'''
function global:docker {
    $call = @($args)
    Add-Content -LiteralPath (Join-Path $env:VF_SETTINGS_TEST_ROOT 'calls.jsonl') -Value ($call | ConvertTo-Json -Compress)
    $global:LASTEXITCODE = 0
    if ($call -contains 'config') { Get-Content -Raw (Join-Path $env:VF_SETTINGS_TEST_ROOT 'config.json'); return }
    if ($call -notcontains 'release.execution_settings_command') { throw 'Unexpected Docker operation' }
    if ($call -contains 'show') {
        '{"status":"SETTINGS","business_date":"2026-10-20","date_basis":"next date after own accepted closing/opening","effective":{"revision":2},"scheduled":[{"revision":3,"effective_date":"2026-11-08"}],"rows":[]}'
    } elseif ($call -contains 'export') {
        '{"status":"EXPORTED","message":"Edit only Value"}'
    } else {
        '{"status":"APPLIED","settings":{"revision":3}}'
    }
}
& (Join-Path $env:VF_SETTINGS_TEST_ROOT 'vf.ps1') @args
'''


@unittest.skipUnless(shutil.which('powershell.exe') and shutil.which('pwsh'), 'Windows PowerShell5.1 and7 required')
class SettingsOperatorTests(unittest.TestCase):
    def fixture(self, root):
        (root/'release').mkdir(); (root/'state').mkdir()
        for name in ('vf.ps1', 'release/run_settings.ps1', 'release/powershell_compat.ps1'):
            shutil.copyfile(ROOT/name, root/name)
        (root/'driver.ps1').write_text(FAKE, encoding='utf-8-sig')
        (root/'config.json').write_text(json.dumps({'x-vectorflow-daily': {'state_dir': str(root/'state')}}))

    def run_command(self, root, shell, *args):
        import os
        env = dict(os.environ, VF_SETTINGS_TEST_ROOT=str(root))
        return subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(root/'driver.ps1'), *args],
                              cwd=root, env=env, capture_output=True, text=True)

    def calls(self, root):
        p = root/'calls.jsonl'
        return [json.loads(line) for line in p.read_text(encoding='utf-8-sig').splitlines()] if p.exists() else []

    def test_show_schedules_and_apply_keep_all_services_untouched(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell), TemporaryDirectory(prefix='vf settings ') as tmp:
                root = Path(tmp); self.fixture(root)
                result = self.run_command(root, shell, 'settings')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('business date 2026-10-20', result.stdout)
                self.assertIn('Scheduled revision 3, effective 2026-11-08', result.stdout)
                target = root/'export with spaces.csv'
                target.write_text('retained operator export')
                result = self.run_command(root, shell, 'settings', '-Apply', str(target),
                                          '-EffectiveDate', '2026-11-09', '-Reason', 'Supported future DBM choice')
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.calls(root)
                commands = [c for c in calls if 'release.execution_settings_command' in c]
                self.assertEqual(len(commands), 2)
                self.assertTrue(all('mta-install' in c and '--no-deps' in c for c in commands))
                self.assertIn('/settings-transfer/export with spaces.csv', commands[-1])
                self.assertIn('Supported future DBM choice', commands[-1])
                self.assertFalse(any(x in c for c in calls for x in ('up','stop','build','migrate','provision','csv-day')))
                self.assertEqual(target.read_text(), 'retained operator export')

    def test_invalid_apply_and_existing_export_fail_before_worker(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell), TemporaryDirectory(prefix='vf settings ') as tmp:
                root = Path(tmp); self.fixture(root)
                target = root/'retained.csv'; target.write_text('retained')
                result = self.run_command(root, shell, 'settings', '-Apply', str(target))
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.calls(root))
                result = self.run_command(root, shell, 'settings', '-Export', str(target))
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any('release.execution_settings_command' in c for c in self.calls(root)))
                self.assertEqual(target.read_text(), 'retained')


if __name__ == '__main__':
    unittest.main()
