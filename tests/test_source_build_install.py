"""Exact source-build outputs must install without the old runtime archive.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from release.build_release import installation_files


class SourceBuildInstallationTests(unittest.TestCase):
    def test_runtime_and_installer_pins_and_native_identity_use_this_build(self):
        source=Path(__file__).resolve().parents[1]
        app_images={name:{'id':'sha256:'+str(index)*64}
            for index,name in enumerate(('mta','auth','mto','frontend'),1)}
        proof={'images':app_images,'source_commit':'c'*40,'native_sha256':'a'*64,
            'source_sha256':'b'*64,'restriction':__doc__.splitlines()[2],
            'public_origin':'http://127.0.0.1:8080','websocket_origin':'ws://127.0.0.1:8080'}
        def inspect(arguments, **kwargs):
            name='5' if 'postgres:' in arguments[-1] else '6'
            return subprocess.CompletedProcess(arguments,0,json.dumps([
                {'Id':'sha256:'+name*64,'Architecture':'amd64','Os':'linux'}]))
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            with patch('release.build_release.subprocess.run',side_effect=inspect):
                installation_files(source,output,proof,'p'*32)
            services=json.loads((output/'source-build-images.yaml').read_text())['services']
            for alias,component in (('mta','mta'),('provision','mta'),('mta-install','mta'),
                    ('auth-install','auth'),('mto-install','mto'),('frontend','frontend')):
                self.assertEqual(services[alias]['image'],app_images[component]['id'])
                self.assertEqual(services[alias]['pull_policy'],'never')
            release=json.loads((output/'installation-release.json').read_text())
            self.assertNotIn('runtime_archive',release)
            self.assertEqual(release['component_sources']['mta'],proof['source_commit'])
            self.assertEqual(release['native_manifest_sha256'],proof['native_sha256'])
            env=dict(line.split('=',1) for line in (output/'operator.env.template').read_text().splitlines()
                if line and not line.startswith('#'))
            self.assertEqual(env['VF_NATIVE_RELEASE_COMMIT'],proof['source_commit'])
            self.assertEqual(env['VF_NATIVE_RELEASE_SHA256'],proof['native_sha256'])
            self.assertEqual(env['VF_SOURCE_MANIFEST_SHA256'],proof['source_sha256'])
            self.assertEqual(env['MTA_SELECTION_FILE'],'')
            self.assertEqual(env['VF_CLIENT_CIPHER_KEY'],'p'*32)


if __name__=='__main__':
    unittest.main()
