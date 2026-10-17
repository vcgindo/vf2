from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from release import preflight


class PreflightTests(unittest.TestCase):
    def config(self, directory):
        secret = Path(directory) / 'private-secret'
        secret.write_text('test-only')
        return dict(name='owned-test', secrets={'key': {'file': str(secret)}}, services={
            'frontend': dict(restart='no', image='front', ports=[dict(host_ip='127.0.0.1', published='8080')],
                environment=dict(VF_PUBLIC_URL='http://127.0.0.1:8080', VF_TLS_MODE='http'),
                build={'args': {'REACT_APP_WS_API_HOST': 'ws://127.0.0.1:8080'}}),
            'mta': dict(restart='no', image='mta', environment={'VF_DB_NAME': 'separate_mta'}),
            'mto': dict(restart='no', image='mto', environment={'DB_NAME': 'separate_mto'})})

    def inspect(self, root, config):
        with patch.object(preflight, 'exported_source', return_value='a' * 40), \
                patch.object(preflight, 'command', side_effect=[
                    json.dumps(dict(OSType='linux', Architecture='x86_64')), json.dumps(config)]), \
                patch.object(preflight.socket, 'socket'):
            return preflight.inspect(Path(root), Path(root) / 'operator.env', [])

    def test_explicit_setup_preflight_is_read_only_and_not_image_or_readiness_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.inspect(directory, self.config(directory))
            self.assertEqual(value['status'], 'PREFLIGHT_PASS_NO_RESOURCE_CHANGE')
            self.assertFalse(value['image_identity_verified'])

    def test_origin_exposure_database_and_required_file_failures_do_not_become_success(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = []
            config = self.config(directory)
            for edit in ('port', 'tls', 'public', 'websocket', 'database', 'missing-secret', 'extra-port'):
                row = deepcopy(config)
                if edit == 'port': row['services']['frontend']['ports'][0]['published'] = '9999'
                if edit == 'tls': row['services']['frontend']['environment']['VF_TLS_MODE'] = 'https'
                if edit == 'public': row['services']['frontend']['ports'][0]['host_ip'] = '0.0.0.0'
                if edit == 'websocket': row['services']['frontend']['build']['args']['REACT_APP_WS_API_HOST'] = 'ws://wrong:8080'
                if edit == 'database': row['services']['mto']['environment']['DB_NAME'] = 'separate_mta'
                if edit == 'missing-secret': row['secrets']['key']['file'] += '.missing'
                if edit == 'extra-port': row['services']['mta']['ports'] = [dict(published='8000')]
                with self.subTest(edit=edit), self.assertRaises(ValueError):
                    self.inspect(directory, row)
