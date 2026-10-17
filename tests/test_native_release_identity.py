"""File admission negatives; no database, application or historical proof required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest.mock import patch

from release import native_identity as identity


class NativeReleaseIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.commit = 'a' * 40
        self.contents = {
            'manage.py': b'# exact native command entry\n',
            'requirements.txt': b'Django==5.2.17\n',
            'mta/mdm/initialization.py': b"IMPLEMENTATION_FILES = ('mdm/initialization.py',)\n",
            'mta/runtime/migrations/0142_native_evidence_default.py': b'# typed schema\n',
            'vectorflow/settings.py': b'# native settings\n',
            'baseline/production-state-schema.json': b'{}\n',
            'release/mta_settings.py': b'# production settings\n',
        }
        for name, raw in self.contents.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.value = identity.declaration(self.root, self.commit,
            {name: hashlib.sha256(raw).hexdigest() for name, raw in self.contents.items()})
        self.pin = self.write(self.value)

    def write(self, value):
        raw = json.dumps(value).encode()
        (self.root / identity.MANIFEST).write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def verify(self, **kwargs):
        with patch('socket.socket', side_effect=AssertionError('Network/database forbidden')):
            return identity.verify(self.root, expected_commit=kwargs.get('commit', self.commit),
                                   expected_sha256=kwargs.get('pin', self.pin))

    def test_exact_files_and_independent_pins_admit_only_release_metadata(self):
        actual = self.verify()
        self.assertEqual(actual['source_commit'], self.commit)
        self.assertEqual(actual['manifest_sha256'], self.pin)
        self.assertEqual(actual['implementation_sha256'], self.value['implementation_sha256'])
        self.assertEqual(set(actual), {'schema', 'source_commit', 'manifest_sha256',
            'source_files_digest', 'migrations_digest', 'implementation_sha256'})

    def test_no_missing_or_self_inferred_pin(self):
        for pin in ('', None, 'A' * 64, '0' * 64):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                self.verify(pin=pin)
        with self.assertRaises(ValueError):
            self.verify(commit='b' * 40)

    def test_historical_settings_fail_before_manifest_or_database_access(self):
        for name in identity.HISTORICAL_SETTINGS:
            with self.subTest(name=name), patch.dict('os.environ', {name: 'old-pin'}, clear=True):
                with patch.object(identity, 'verify', side_effect=AssertionError('Must reject first')):
                    with self.assertRaisesRegex(ValueError, 'pinned original release'):
                        identity.require_current()

    def test_runtime_pins_are_mandatory_without_historical_fallback(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaisesRegex(ValueError, 'Independent'):
            identity.require_current()

    def test_changed_bytes_missing_files_and_extra_executable_files_deny(self):
        path = self.root / 'vectorflow/settings.py'
        original = path.read_bytes()
        path.write_bytes(b'# changed\n')
        with self.assertRaises(ValueError):
            self.verify()
        path.unlink()
        with self.assertRaises(ValueError):
            self.verify()
        path.write_bytes(original)
        extra = self.root / 'mta/undeclared.py'
        extra.write_bytes(b'raise RuntimeError()\n')
        with self.assertRaises(ValueError):
            self.verify()

    def test_migration_or_implementation_manifest_tamper_denies_even_with_recomputed_pin(self):
        for key in ('migrations', 'implementation_sha256'):
            with self.subTest(key=key):
                value = dict(self.value, **{key: {} if key == 'migrations' else 'c' * 64})
                self.pin = self.write(value)
                with self.assertRaises(ValueError):
                    self.verify()

    def test_duplicate_keys_and_path_escape_denied(self):
        raw = json.dumps(self.value).encode()
        raw = b'{"schema":"duplicate",' + raw[1:]
        (self.root / identity.MANIFEST).write_bytes(raw)
        with self.assertRaises(ValueError):
            self.verify(pin=hashlib.sha256(raw).hexdigest())
        for path in ('../secret', '/absolute', 'mta/../escape', 'mta\\escape'):
            value = dict(self.value, files={path: 'f' * 64})
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.verify(pin=self.write(value))

    def test_undeclared_bytecode_is_not_trusted_source(self):
        path = self.root / 'mta/__pycache__/undeclared.cpython-311.pyc'
        path.parent.mkdir()
        path.write_bytes(b'not source')
        with self.assertRaises(ValueError):
            self.verify()

    def test_root_entry_and_dependency_changes_or_omissions_deny(self):
        for name in ('manage.py', 'requirements.txt'):
            path = self.root / name
            with self.subTest(name=name, action='change'):
                path.write_bytes(b'changed\n')
                with self.assertRaises(ValueError):
                    self.verify()
            with self.subTest(name=name, action='missing'):
                path.unlink()
                with self.assertRaises(ValueError):
                    self.verify()
            path.write_bytes(self.contents[name])

    def test_undeclared_root_module_or_bytecode_denies(self):
        for name in ('sitecustomize.py', 'arbitrary.py', 'arbitrary.pyc', 'arbitrary.pyo'):
            path = self.root / name
            path.write_bytes(b'undeclared')
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.verify()
            path.unlink()
        path = self.root / '__pycache__'
        path.mkdir()
        with self.assertRaises(ValueError):
            self.verify()

    def test_git_export_uses_committed_bytes_despite_dirty_working_source(self):
        from release.export import export
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=File test',
                        '-c', 'user.email=file-test@invalid', 'commit', '-qm', 'fixture'],
                       check=True, capture_output=True)
        commit = subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD'], text=True).strip()
        (self.root / 'vectorflow/settings.py').write_bytes(b'# dirty working bytes\n')
        destination = self.root.parent / (self.root.name + '-export')
        import shutil
        self.addCleanup(lambda: shutil.rmtree(destination, ignore_errors=True))
        export(self.root, commit, destination)
        pin = hashlib.sha256((destination / identity.MANIFEST).read_bytes()).hexdigest()
        admitted = identity.verify(destination, expected_commit=commit, expected_sha256=pin)
        self.assertEqual(admitted['source_commit'], commit)
        committed = subprocess.check_output(['git', '-C', str(self.root), 'show', commit + ':vectorflow/settings.py'])
        self.assertEqual((destination / 'vectorflow/settings.py').read_bytes(), committed)


if __name__ == '__main__':
    unittest.main()
