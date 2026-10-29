"""Real host-shell checks; Docker calls are replaced by a local test executable.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'), 'Windows shell compatibility')
class PowerShellCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='vf shell ')
        cls.root = Path(cls.temp.name)
        cls.env = dict(os.environ)
        for key in ('PSModulePath', 'PSMODULEPATH', 'COMPOSE_FILE', 'COMPOSE_PATH_SEPARATOR'):
            cls.env.pop(key, None)
        source = cls.root / 'DockerStub.cs'
        source.write_text(r'''
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;
class DockerStub {
    static int Main(string[] args) {
        var json = new JavaScriptSerializer();
        File.AppendAllText(Environment.GetEnvironmentVariable("VF_TEST_LOG"), json.Serialize(args) + "\n", new UTF8Encoding(false));
        Console.Error.WriteLine("ordinary Docker progress");
        if (args.Contains("config")) {
            if (!args.Contains("--quiet")) Console.WriteLine(File.ReadAllText(Environment.GetEnvironmentVariable("VF_TEST_CONFIG")));
        }
        else if (args.Contains("release.initialize_csv")) {
            string state = Path.Combine(Environment.CurrentDirectory,"state","onboarding.json");
            var receipt = json.Deserialize<System.Collections.Generic.Dictionary<string, object>>(File.ReadAllText(state));
            receipt["registration"] = new {status="registered"};
            receipt["initialization"] = json.DeserializeObject(File.ReadAllText(Environment.GetEnvironmentVariable("VF_TEST_INITIAL")));
            receipt["families"] = new {status="MDM_FAMILIES_READY"};
            receipt["phase"] = "CONFIGURATION";
            File.WriteAllText(state,json.Serialize(receipt),new UTF8Encoding(false));
            Console.WriteLine(json.Serialize(receipt));
        }
        else if (args.Contains("check")) {Console.In.ReadToEnd(); Console.WriteLine("{\"status\":\"INITIALIZED_MASTER_SERVING_READY\"}");}
        else if (args.Contains("process_daily_csv")) {
            if (args.Contains("stage") && Environment.GetEnvironmentVariable("VF_TEST_PUBLISHED") == "1") Console.WriteLine("{\"status\":\"PUBLISHED\",\"phase\":\"FINISHED\",\"attempt_id\":\"test\",\"run_id\":\"test\",\"output_digest\":\"test\"}");
            else if (args.Contains("inspect")) Console.WriteLine("{\"status\":\"VALIDATED\"}");
            else if (args.Contains("stage") && Environment.GetEnvironmentVariable("VF_TEST_PREPARED") == "1") Console.WriteLine("{\"status\":\"PREPARED\",\"phase\":\"SERVE\",\"attempt_id\":\"test\",\"run_id\":\"test\",\"output_digest\":\"test\"}");
            else if (args.Contains("stage")) Console.WriteLine("{\"status\":\"VALIDATED\",\"phase\":\"VALIDATED\",\"attempt_id\":\"test\"}");
            else if (args.Contains("acknowledge")) Console.WriteLine("{\"status\":\"PUBLISHED\"}");
            else Console.WriteLine("{\"status\":\"PREPARED\",\"run_id\":\"test\",\"output_digest\":\"test\"}");
        }
        else if (args.Contains("-") && args.Contains("--run-id")) {
            if (args.Contains("--admission-only") && Environment.GetEnvironmentVariable("VF_TEST_BAD_SELECTION") == "1") return 1;
            if (!args.Contains("--admission-only") && Environment.GetEnvironmentVariable("VF_TEST_SERVING_FAIL") == "1") return 1;
            File.WriteAllText(Environment.GetEnvironmentVariable("VF_TEST_LOG") + ".stdin", Console.In.ReadToEnd(), new UTF8Encoding(false));
            Console.WriteLine("{\"test\":\"quote \\\" and space\"}");
        }
        return 0;
    }
}''', encoding='utf-8')
        compile_script = cls.root / 'compile.ps1'
        compile_script.write_text("$ErrorActionPreference='Stop'\nAdd-Type -Path $args[0] -ReferencedAssemblies System.Core,System.Web.Extensions -OutputAssembly $args[1] -OutputType ConsoleApplication\n")
        result = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(compile_script), str(source), str(cls.root / 'docker.exe')], env=cls.env, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.env['PATH'] = str(cls.root) + os.pathsep + cls.env['PATH']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_shell(self, shell, script, *args, env=None, cwd=None):
        return subprocess.run([shell, '-NoProfile', '-File', str(script), *map(str, args)], env=env or self.env, cwd=cwd, capture_output=True, text=True)

    def test_json_paths_encoding_and_native_arguments_in_both_shells(self):
        script = self.root / 'compat.ps1'
        script.write_text(r'''
param($Helper,$Output)
$ErrorActionPreference='Stop'
. $Helper
$data=ConvertFrom-VfJson '{"empty":[],"single":[{"name":"001"}],"ordered":[null,1,null],"flag":false}'
if ($data.empty.Count -ne 0 -or $data.single.Count -ne 1 -or $data.single[0].name -ne '001' -or $data.ordered.Count -ne 3 -or $null -ne $data.ordered[0] -or $data.flag -ne $false) {throw 'JSON shape changed'}
if ((Test-VfAbsolutePath 'C:relative') -or (Test-VfAbsolutePath '\relative') -or -not (Test-VfAbsolutePath 'C:\absolute') -or -not (Test-VfAbsolutePath '\\server\share\path')) {throw 'absolute path check'}
if ((Get-VfRelativePath 'C:\input' 'C:\input\2026-10-19') -ne '2026-10-19') {throw 'relative path check'}
if ((Resolve-VfProjectPath 'C:\clone' './data/input') -ne 'C:\clone\data\input') {throw 'project path check'}
if ((Resolve-VfProjectPath 'C:\clone' 'D:\external\input') -ne 'D:\external\input') {throw 'external path check'}
foreach ($ambiguous in @('C:relative','\relative')) {
    $denied=$false
    try {Resolve-VfProjectPath 'C:\clone' $ambiguous} catch {$denied=$true}
    if (-not $denied) {throw 'ambiguous project path accepted'}
}
$rejected=$false
try {Get-VfRelativePath 'C:\input' 'C:\input-sibling\date'} catch {$rejected=$true}
if (-not $rejected) {throw 'sibling escaped containment'}
Write-VfUtf8 $Output ($data|ConvertTo-Json -Depth 20)
$expected=@('two words','','{"quote":"escaped \" value","tail":"C:\\path\\"}','C:\trailing\')
$start=New-Object Diagnostics.ProcessStartInfo
$start.FileName='docker.exe';$start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
Set-VfProcessArguments $start $expected
$process=New-Object Diagnostics.Process
$process.StartInfo=$start;$null=$process.Start()
$out=$process.StandardOutput.ReadToEndAsync();$err=$process.StandardError.ReadToEndAsync()
$process.WaitForExit();$null=$out.GetAwaiter().GetResult();$null=$err.GetAwaiter().GetResult()
if ($process.ExitCode -ne 0) {throw 'native process failed'}
$process.Dispose()
Write-VfUtf8 ($Output+'.args') (ConvertTo-Json -InputObject $expected)
''')
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                output = self.root / (shell + '.json')
                log = self.root / (shell + '.args.log')
                env = dict(self.env, VF_TEST_LOG=str(log))
                result = self.run_shell(shell, script, ROOT / 'release/powershell_compat.ps1', output, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(output.read_bytes().startswith(b'\xef\xbb\xbf'))
                self.assertEqual(json.loads(output.read_text())['ordered'], [None, 1, None])
                self.assertEqual(json.loads(log.read_text()), json.loads(Path(str(output)+'.args').read_text()))

    def test_actual_daily_script_process_boundary_in_both_shells(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                folder = self.root / shell
                folder.mkdir()
                incoming = folder / 'incoming data'; incoming.mkdir()
                binding = folder / 'binding.json'; binding.write_text('{}')
                state = folder / 'state'
                config = dict(name='test', services={
                    'mta': dict(image='test-only', environment=dict(VF_MTA_SELECTION_FILE=''), volumes=[]),
                    'daily': dict(image='test-only', environment={}, volumes=[], build={}),
                }, **{'x-vectorflow-daily': dict(input_dir=str(incoming), binding_file=str(binding), state_dir=str(state))})
                (folder/'.env').write_text('MTA_SELECTION_FILE=\nKEEP=unchanged\n')
                config_file = folder / 'config.json'; config_file.write_text(json.dumps(config))
                log = folder / 'calls.jsonl'
                env = dict(self.env, VF_TEST_LOG=str(log), VF_TEST_CONFIG=str(config_file))
                result = self.run_shell(shell, ROOT / 'release/run_daily.ps1', '-BusinessDate', '2026-10-19', env=env, cwd=folder)
                self.assertEqual(result.returncode, 0, result.stderr)
                operations = list(state.glob('*/operation.json'))
                self.assertEqual(len(operations), 1)
                self.assertEqual(json.loads(operations[0].read_text())['status'], 'PUBLISHED')
                self.assertFalse(list(state.glob('*/compose.daily.json')))
                self.assertIn('MTA_SELECTION_FILE="/var/lib/vectorflow/selection.json"',(folder/'.env').read_text())
                self.assertIn('KEEP=unchanged',(folder/'.env').read_text())
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                self.assertEqual(calls[0][:3], ['compose', '--profile', '*'])
                self.assertIn('--quiet', calls[1])
                self.assertTrue(all(call[call.index('--profile')+1] == 'daily' for call in calls[1:] if '--profile' in call))
                self.assertEqual(sum('execute' in call for call in calls), 1)
                self.assertIn('--force-recreate',next(c for c in calls if 'up' in c))
                acknowledge = next(call for call in calls if 'acknowledge' in call)
                self.assertEqual(json.loads(acknowledge[acknowledge.index('--proof')+1]), {'test': 'quote " and space'})
                self.assertEqual(Path(str(log)+'.stdin').read_bytes(), (ROOT/'release/daily_serving_check.py').read_bytes())
                # The same committed PREPARED attempt resumes verification only.
                env['VF_TEST_PREPARED'] = '1'
                result = self.run_shell(shell, ROOT/'release/run_daily.ps1', '-BusinessDate', '2026-10-19', '-Resume', env=env, cwd=folder)
                self.assertEqual(result.returncode, 0, result.stderr)
                resumed = [json.loads(line) for line in log.read_text().splitlines()][len(calls):]
                self.assertFalse(any('execute' in call for call in resumed))
                self.assertEqual(sum('acknowledge' in call for call in resumed), 1)
                # A published latest day can recover serving without selecting
                # or calculating again; an old/nonmatching selection cannot.
                for bad in (False, True):
                    before=len(log.read_text().splitlines())
                    env['VF_TEST_PUBLISHED']='1'
                    env['VF_TEST_BAD_SELECTION']='1' if bad else '0'
                    result=self.run_shell(shell,ROOT/'release/run_daily.ps1','-BusinessDate','2026-10-19','-Resume',env=env,cwd=folder)
                    self.assertEqual(result.returncode == 0,not bad,result.stderr)
                    recovery=[json.loads(line) for line in log.read_text().splitlines()][before:]
                    self.assertFalse(any('execute' in c or 'select' in c or 'acknowledge' in c for c in recovery))
                    self.assertEqual(sum('up' in c for c in recovery),0 if bad else 1)
                before=len(log.read_text().splitlines())
                env['VF_TEST_BAD_SELECTION']='0'; env['VF_TEST_SERVING_FAIL']='1'
                result=self.run_shell(shell,ROOT/'release/run_daily.ps1','-BusinessDate','2026-10-19','-Resume',env=env,cwd=folder)
                self.assertNotEqual(result.returncode,0)
                failed=[json.loads(line) for line in log.read_text().splitlines()][before:]
                self.assertEqual(sum('stop' in c for c in failed),1)
                self.assertFalse(any('execute' in c or 'select' in c for c in failed))



    def test_launcher_accepts_real_native_progress_on_stderr_in_both_shells(self):
        from tests.test_csv_launcher import CsvLauncherTests
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                fixture = CsvLauncherTests('test_initialization_hides_bindings_and_preserves_existing_configuration')
                fixture.setUp()
                try:
                    env = dict(self.env, VF_TEST_LOG=str(fixture.root/'native-calls.jsonl'),
                               VF_TEST_CONFIG=str(fixture.root/'config.json'),
                               VF_TEST_VALIDATED=str(fixture.root/'validated.json'),
                               VF_TEST_INITIAL=str(fixture.root/'initial.json'))
                    result = self.run_shell(shell, fixture.root/'vf.ps1', 'csv-init', env=env, cwd=fixture.root)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads((fixture.state/'onboarding.json').read_text())['status'], 'INITIALIZED')
                    log_bytes = (fixture.state/'onboarding-docker.log').read_bytes()
                    encoding = 'utf-16' if log_bytes.startswith(b'\xff\xfe') else 'utf-8-sig'
                    self.assertIn('ordinary Docker progress', log_bytes.decode(encoding))
                finally:
                    fixture.tearDown()


if __name__ == '__main__':
    unittest.main()
