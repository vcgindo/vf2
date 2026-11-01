"""Real PowerShell 5.1/7 process boundaries with a deterministic Docker stub.

No Docker daemon, service or database is accessed by these tests.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK.
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
OLD = 'sha256:' + 'a' * 64
TARGET = 'sha256:' + 'b' * 64


@unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'), 'Windows shell compatibility')
class UpgradeOperatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='vf upgrade shell ')
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
  string folder = Environment.GetEnvironmentVariable("VF_UPGRADE_FIXTURE");
  File.AppendAllText(Path.Combine(folder,"calls.jsonl"),json.Serialize(args)+"\n",new UTF8Encoding(false));
  Console.Error.WriteLine("ordinary Docker progress");
  string oldImage = "sha256:" + new string('a',64), target = "sha256:" + new string('b',64);
  if (args.Contains("config")) {
   if (!args.Contains("--quiet")) Console.WriteLine(File.ReadAllText(Path.Combine(folder,"config.json")));
  } else if (args.Length > 1 && args[0] == "image" && args[1] == "inspect") {
   Console.WriteLine(json.Serialize(new[]{new {Id=target}}));
  } else if (args[0] == "inspect") {
   string image = File.Exists(Path.Combine(folder,"started")) ? target : oldImage;
   Console.WriteLine(json.Serialize(new[]{new {Image=image,State=new {Running=true}}}));
  } else if (args.Contains("--network")) {
   if (args.Contains(oldImage)) Console.WriteLine(json.Serialize(new {schema="vectorflow-native-release-source-v1",source_commit=new string('c',40),manifest_sha256=new string('e',64),source_files_digest=new string('f',64),migrations_digest=new string('1',64),implementation_sha256=new string('2',64)}));
   else Console.WriteLine("{\"schema\":\"vectorflow-native-release-source-v1\",\"source_commit\":\""+new string('d',40)+"\",\"files\":{}}");
  } else if (args.Contains("release.upgrade_database")) {
   string phase = args[Array.IndexOf(args,"--phase")+1];
   string mount = args.First(a=>a.EndsWith(":/upgrade"));
   string operation = mount.Substring(0,mount.Length-9);
   if (phase == "apply" && Environment.GetEnvironmentVariable("VF_UPGRADE_FAIL_APPLY") == "before") {
    File.WriteAllText(Path.Combine(folder,"rolledback"),"proved rollback"); return 1;
   }
   bool rolledback = phase == "verify" && !File.Exists(Path.Combine(folder,"applied")) && File.Exists(Path.Combine(folder,"rolledback"));
   if (phase == "verify" && !File.Exists(Path.Combine(folder,"applied")) && !rolledback) return 1;
   if (phase == "apply") File.WriteAllText(Path.Combine(folder,"applied"),"committed");
   string status = rolledback ? "APPLY_REQUIRED" : phase == "inspect" ? "INSPECTED" : phase == "apply" ? "APPLIED" : "VERIFIED";
   string receipt = "{\"status\":\"UPGRADE_DATABASE_"+status+"\",\"selected\":{\"run_id\":\"run-existing\",\"output_digest\":\"digest-existing\",\"business_date\":\"2026-10-19\"},\"pending_migrations\":[]}";
   File.WriteAllText(Path.Combine(operation,"database.json"),receipt,new UTF8Encoding(false));
   Console.WriteLine(receipt);
   if (phase == "apply" && Environment.GetEnvironmentVariable("VF_UPGRADE_FAIL_APPLY") == "after") return 1;
  } else if (args[0] == "cp") {
   Directory.CreateDirectory(args[2]);
   File.WriteAllBytes(Path.Combine(args[2],"base.tar.gz"),new byte[]{31,139,8,0,1,2,10});
   File.WriteAllText(Path.Combine(args[2],"backup_manifest"),"{\"PostgreSQL-Backup-Manifest-Version\":2}",new UTF8Encoding(false));
  } else if (args.Contains("up")) {
   File.WriteAllText(Path.Combine(folder,"started"),target);
   if (Environment.GetEnvironmentVariable("VF_UPGRADE_FAIL_START") == "1") return 1;
  } else if (args.Contains("release.daily_serving_check")) {
   Console.WriteLine("{\"ready\":true,\"run_id\":\"run-existing\",\"output_digest\":\"digest-existing\"}");
  } else if (args.Contains("ps")) { Console.WriteLine(args.Last()+"-container"); }
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

    def fixture(self):
        temp = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / 'deployment'
        root.mkdir()
        (root / 'release').mkdir()
        shutil.copyfile(ROOT / 'vf.ps1', root / 'vf.ps1')
        for name in ('run_upgrade.ps1', 'powershell_compat.ps1'):
            shutil.copyfile(ROOT / 'release' / name, root / 'release' / name)
        (root.parent / 'state').mkdir()
        (root / 'binding.json').write_text(json.dumps({'initialization_id': 'owned-initialization'}))
        (root / '.env').write_text('COMPOSE_FILE="compose.yaml;private-original.json"\nCOMPOSE_PATH_SEPARATOR=";"\nKEEP="private unchanged"\n')
        services = {name: dict(image='original:source', environment={}, volumes=[]) for name in ('mta', 'daily', 'mta-install', 'provision')}
        services['mta']['build'] = {'context': str(root), 'dockerfile': 'release/compose.Dockerfile', 'target': 'mta'}
        services['provision']['environment'] = dict(PG_ADMIN_USER='postgres', MTA_DB_NAME='owned_mta')
        config = dict(name='owned-project', services=services, **{'x-vectorflow-daily': dict(state_dir=str(root.parent / 'state'), binding_file=str(root / 'binding.json'))})
        (root / 'config.json').write_text(json.dumps(config))
        return root

    def run_upgrade(self, shell, root, *args, **env):
        return subprocess.run([shell, '-NoProfile', '-File', str(root / 'vf.ps1'), 'upgrade', *args],
                              env=dict(self.env, VF_UPGRADE_FIXTURE=str(root), **env), cwd=root, capture_output=True, text=True)

    def calls(self, root):
        return [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()]

    def journal(self, root):
        return json.loads((root.parent / 'state/upgrade.json').read_text())

    def test_build_backup_apply_and_only_mta_replacement_in_both_shells(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                root = self.fixture()
                result = self.run_upgrade(shell, root, '-Build', '-BackupDirectory', str(root.parent / 'external backup'))
                self.assertEqual(result.returncode, 0, result.stderr)
                journal = self.journal(root)
                self.assertEqual(journal['status'], 'COMPLETE')
                self.assertEqual(journal['previous_image'], OLD)
                self.assertEqual(journal['target_image'], TARGET)
                previous = json.loads(Path(journal['operation_root'], 'previous-native.json').read_text())
                self.assertEqual(set(previous), {'schema','source_commit','manifest_sha256','source_files_digest','migrations_digest','implementation_sha256'})
                backup = Path(journal['backup']['path'])
                self.assertEqual(backup.parent, root.parent / 'external backup')
                self.assertEqual(journal['backup']['format'], 'postgres-basebackup-tar-gzip-fetch-v1')
                self.assertEqual(set(journal['backup']['files']), {'base.tar.gz','backup_manifest'})
                for name, record in journal['backup']['files'].items():
                    raw = (backup / name).read_bytes()
                    self.assertEqual(record, dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
                self.assertFalse(list((root.parent / 'state').glob('*/compose.private.json')))
                calls = self.calls(root)
                build = next(c for c in calls if 'build' in c)
                self.assertEqual(build[-2:], ['build', 'mta'])
                self.assertLess(next(i for i,c in enumerate(calls) if c[0]=='inspect'), calls.index(build))
                old_admission = next(c for c in calls if '--network' in c and OLD in c)
                self.assertIn('json.dumps(require_current()', old_admission[-1])
                self.assertEqual([c[c.index('--phase')+1] for c in calls if '--phase' in c], ['inspect','apply','verify'])
                backup_call = next(c for c in calls if any('pg_basebackup ' in a for a in c))
                self.assertIn('--wal-method=fetch', ' '.join(backup_call))
                self.assertFalse(any('pg_dump ' in a for c in calls for a in c))
                for call in calls:
                    if 'run' in call and 'provision' in call:
                        self.assertIn('--no-deps', call)
                    if 'up' in call or 'stop' in call:
                        self.assertEqual(call[-1], 'mta')
                    if 'up' in call:
                        self.assertIn('--no-deps', call)
                        self.assertIn('--no-build', call)
                self.assertFalse(any('install' == c[-1] or 'process_daily_csv' in c for c in calls))
                self.assertTrue(all(c[:5] == ['compose','--profile','install','--profile','daily'] for c in calls if 'config' in c))
                descriptor = json.loads((root.parent / 'state/compose.deployment.json').read_text())
                self.assertEqual({s['image'] for s in descriptor['services'].values()}, {TARGET})
                env_text = (root / '.env').read_text()
                self.assertIn('compose.yaml;private-original.json;', env_text)
                self.assertEqual(env_text.count('compose.deployment.json'), 1)
                self.assertIn('KEEP="private unchanged"', env_text)
                # Actual Compose parses the generated fixed override. This is
                # configuration validation only; it never contacts a daemon.
                if shutil.which('docker'):
                    resolved = subprocess.run(['docker', 'compose', '--profile', 'install', '--profile', 'daily',
                                               '-f', str(root / 'config.json'), '-f', str(root.parent / 'state/compose.deployment.json'),
                                               'config', '--format', 'json'], cwd=root, capture_output=True, text=True)
                    self.assertEqual(resolved.returncode, 0, resolved.stderr)
                    actual = json.loads(resolved.stdout)
                    self.assertEqual(actual['services']['mta']['image'], TARGET)
                    self.assertEqual(actual['services']['provision']['environment']['PG_ADMIN_USER'], 'postgres')

    def test_inspection_stages_image_without_backup_stop_or_apply_and_resumes(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                root = self.fixture()
                original = (root / '.env').read_bytes()
                result = self.run_upgrade(shell, root, '-Build', '-InspectOnly')
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.calls(root)
                self.assertFalse(any('stop' in c or 'up' in c or c[0] == 'cp' or 'apply' in c for c in calls))
                self.assertEqual(self.journal(root)['status'], 'INSPECTED')
                self.assertEqual((root / '.env').read_bytes(), original)
                before = len(calls)
                result = self.run_upgrade(shell, root, '-Resume')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(any('build' in c for c in self.calls(root)[before:]))
                self.assertEqual(self.journal(root)['status'], 'COMPLETE')

    def test_resume_reconciles_committed_apply_without_reapplying(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                root = self.fixture()
                result = self.run_upgrade(shell, root, '-Image', 'supplied:target', VF_UPGRADE_FAIL_APPLY='after')
                self.assertNotEqual(result.returncode, 0)
                journal = self.journal(root)
                self.assertTrue(journal['maintenance'])
                # Simulate lost post-commit file response too; real verify must
                # reconcile the actual DB state instead of replaying apply.
                Path(journal['operation_root'], 'database.json').unlink()
                before = len(self.calls(root))
                result = self.run_upgrade(shell, root, '-Resume')
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.calls(root)[before:]
                self.assertFalse(any('apply' in c for c in calls))
                self.assertFalse(any(c[0] == 'cp' or any('pg_basebackup ' in a for a in c) for c in calls))
                self.assertEqual([c[c.index('--phase')+1] for c in calls if '--phase' in c], ['verify'])
                self.assertEqual(self.journal(root)['status'], 'COMPLETE')

    def test_resume_rejects_changed_backup_and_different_target(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                root = self.fixture()
                result = self.run_upgrade(shell, root, '-Image', 'supplied:target', VF_UPGRADE_FAIL_START='1')
                self.assertNotEqual(result.returncode, 0)
                original = (root.parent / 'state/upgrade.json').read_bytes()
                result = self.run_upgrade(shell, root, '-Resume', '-Image', 'other:target')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((root.parent / 'state/upgrade.json').read_bytes(), original)
                journal = self.journal(root)
                Path(journal['backup']['path'], 'base.tar.gz').write_bytes(b'tampered')
                before = len(self.calls(root))
                result = self.run_upgrade(shell, root, '-Resume')
                self.assertNotEqual(result.returncode, 0)
                calls = self.calls(root)[before:]
                self.assertFalse(any('--phase' in c or 'up' in c for c in calls))

    def test_explicit_resume_after_proved_atomic_rollback_applies_once_without_new_backup(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                root = self.fixture()
                result = self.run_upgrade(shell, root, '-Image', 'supplied:target', VF_UPGRADE_FAIL_APPLY='before')
                self.assertNotEqual(result.returncode, 0)
                previous_backup = self.journal(root)['backup']
                before = len(self.calls(root))
                result = self.run_upgrade(shell, root, '-Resume')
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.calls(root)[before:]
                self.assertEqual([c[c.index('--phase')+1] for c in calls if '--phase' in c], ['verify','apply','verify'])
                self.assertFalse(any(c[0] == 'cp' or any('pg_basebackup ' in a for a in c) for c in calls))
                self.assertEqual(self.journal(root)['backup'], previous_backup)
                self.assertEqual(self.journal(root)['status'], 'COMPLETE')

    def test_backup_extra_file_blocks_resume_before_database_or_start(self):
        for shell in ('powershell.exe', 'pwsh'):
            with self.subTest(shell=shell):
                root = self.fixture()
                result = self.run_upgrade(shell, root, '-Image', 'supplied:target', VF_UPGRADE_FAIL_START='1')
                self.assertNotEqual(result.returncode, 0)
                Path(self.journal(root)['backup']['path'], 'unexpected.tar.gz').write_bytes(b'extra')
                before = len(self.calls(root))
                result = self.run_upgrade(shell, root, '-Resume')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any('--phase' in c or 'up' in c for c in self.calls(root)[before:]))


if __name__ == '__main__':
    unittest.main()
