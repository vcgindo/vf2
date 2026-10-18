"""Security/configuration invariants for the simple blank-install interface.

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
from unittest.mock import patch

from release.compose_secrets import ROUTES, ensure
from release.compose_build import require_clean
from release.image_entrypoint import configure


class GitCheckoutTests(unittest.TestCase):
    def test_checkout_eol_conversion_is_allowed_but_real_edits_and_spaces_are_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.run(['git','-C',str(root),*args], check=True, capture_output=True)
            git('init')
            git('config','core.autocrlf','false')
            (root/'.gitattributes').write_text('example.txt -text\n')
            path = root/'example.txt'
            path.write_bytes(b'value=1\r\nnext=2\n')
            git('add','.')
            git('-c','user.name=Unit','-c','user.email=unit@example.invalid','commit','-m','Unit input')
            path.write_bytes(b'value=1\nnext=2\n')
            require_clean(root)
            for changed in (b'value=2\nnext=2\n', b'value=1 \nnext=2\n'):
                path.write_bytes(changed)
                with self.assertRaises(subprocess.CalledProcessError):
                    require_clean(root)


class ImageIdentityTests(unittest.TestCase):
    def test_baked_pins_replace_only_auto_values_and_reject_mismatch_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.json'
            identity = dict(source_commit='a'*40, native_sha256='b'*64, source_sha256='c'*64)
            path.write_text(json.dumps(identity))
            env = {'VF_NATIVE_RELEASE_COMMIT': 'image'}
            configure(path, env)
            self.assertEqual(env, {'VF_NATIVE_RELEASE_COMMIT': 'a'*40,
                'VF_NATIVE_RELEASE_SHA256': 'b'*64, 'VF_SOURCE_MANIFEST_SHA256': 'c'*64})
            env = {'VF_NATIVE_RELEASE_COMMIT': 'image', 'VF_NATIVE_RELEASE_SHA256': 'd'*64}
            before = dict(env)
            with self.assertRaisesRegex(ValueError, 'differs'):
                configure(path, env)
            self.assertEqual(env, before)
            identity['source_commit'] = 'not-a-commit'
            path.write_text(json.dumps(identity))
            with self.assertRaisesRegex(ValueError, 'Invalid'):
                configure(path, {})


class RoutedSecretTests(unittest.TestCase):
    def test_secret_routing_reuse_and_corruption_fail_without_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('private', *ROUTES):
                (root / name).mkdir()
            def generate(destination):
                destination.mkdir()
                for name in set().union(*ROUTES.values()):
                    (destination / name).write_text('new-owned-unit-secret:' + name)
            with patch('release.compose_secrets.prepare', side_effect=generate) as create:
                self.assertEqual(ensure(root)['status'], 'NEW_PRIVATE_SECRETS_ROUTED')
                before = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob('*') if p.is_file()}
                self.assertEqual(ensure(root)['status'], 'EXISTING_SECRETS_VERIFIED_UNCHANGED')
                self.assertEqual(create.call_count, 1)
                self.assertEqual(before, {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob('*') if p.is_file()})
                for name, files in ROUTES.items():
                    self.assertEqual({p.name for p in (root / name).iterdir()}, set(files))
                self.assertNotIn('mta_installer_password', ROUTES['mta-runtime'])
                self.assertNotIn('postgres_admin_password', set().union(*(v for k,v in ROUTES.items() if k.endswith('-runtime'))))
                victim = root / 'mta-runtime/mta_runtime_password'
                victim.chmod(0o600)
                victim.write_text('corrupted')
                with self.assertRaisesRegex(ValueError, 'differs'):
                    ensure(root)
                self.assertEqual(create.call_count, 1)

    def test_partial_secrets_are_not_automatically_repaired(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('private', *ROUTES):
                (root / name).mkdir()
            (root / 'postgres/postgres_admin_password').write_text('retained')
            with patch('release.compose_secrets.prepare') as create:
                with self.assertRaisesRegex(ValueError, 'Partial'):
                    ensure(root)
                create.assert_not_called()
            self.assertEqual((root / 'postgres/postgres_admin_password').read_text(), 'retained')


@unittest.skipUnless(shutil.which('docker'), 'Docker CLI needed for Compose configuration checks')
class ComposeConfigurationTests(unittest.TestCase):
    def config(self, install=False):
        root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        for line in (root / '.env.example').read_text().splitlines():
            if line and not line.startswith('#') and '=' in line:
                env.pop(line.split('=',1)[0], None)
        env['VF_HTTP_PORT'] = '8097'
        command = ['docker','compose','--env-file','.env.example']
        if install:
            command += ['--profile','install']
        result = subprocess.run(command + ['config','--format','json'], cwd=root, env=env,
            capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_default_startup_has_only_six_runtime_services_and_matching_env_origins(self):
        c = self.config()
        self.assertEqual(set(c['services']), {'postgres','redis','mta','auth','mto','frontend'})
        front = c['services']['frontend']
        self.assertEqual(front['ports'][0]['published'], '8097')
        self.assertEqual(front['build']['args']['REACT_APP_WS_API_HOST'], 'ws://127.0.0.1:8097')
        self.assertEqual(c['services']['auth']['environment']['VF_PUBLIC_URL'], 'http://127.0.0.1:8097')
        self.assertFalse(c.get('secrets'))
        for service in ('postgres','mta','auth','mto'):
            self.assertNotIn('VF_ADMIN_PASSWORD', c['services'][service].get('environment',{}))
            role = 'postgres' if service=='postgres' else service+'_runtime'
            mounted = [v for v in c['services'][service]['volumes'] if v['target']=='/run/secrets']
            self.assertEqual(len(mounted), 1)
            self.assertEqual(mounted[0]['source'], role+'_secrets')
            self.assertTrue(mounted[0]['read_only'])

    def test_installation_orders_secrets_provision_migrations_and_metadata(self):
        c = self.config(install=True)['services']
        sequence = ['secret-init','provision','mta-install','auth-install','mto-install','database-finish','install']
        for previous, current in zip(sequence, sequence[1:]):
            self.assertEqual(c[current]['depends_on'][previous]['condition'], 'service_completed_successfully')
        self.assertEqual(c['secret-init']['network_mode'], 'none')
        for name in sequence:
            self.assertEqual(c[name]['profiles'], ['install'])
        self.assertEqual(c['install']['entrypoint'], ['python','-m','release.compose_install'])
        self.assertEqual(c['mta-install']['environment']['DB_SESSION_ROLE'], 'vectorflow_mta_owner')
        self.assertNotIn('VF_ADMIN_PASSWORD', c['auth']['build'].get('args',{}))


if __name__ == '__main__':
    unittest.main()
