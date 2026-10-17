"""Operator mistakes fail before resource mutation or secret disclosure.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
from pathlib import Path
import tempfile
import unittest
from release.preflight import configuration, environment, non_overlapping_subnet


class DeploymentPreflightTests(unittest.TestCase):
    def values(self):
        return dict(VF_RELEASE='pinned-tag', VF_PROJECT='owned-project',
            VF_PUBLIC_URL='http://127.0.0.1:8080', VF_PUBLIC_WS_URL='ws://127.0.0.1:8080',
            VF_CLIENT_CIPHER_KEY='public-test-only', VF_SECRETS_DIR=str(Path(tempfile.gettempdir()).resolve()))

    def test_missing_release_and_inconsistent_origins_are_actionable_errors(self):
        values = self.values()
        values['VF_RELEASE'] = ''
        with self.assertRaisesRegex(ValueError, 'VF_RELEASE'):
            configuration(values)
        values = self.values()
        values['VF_PUBLIC_WS_URL'] = 'ws://127.0.0.1:3006'
        with self.assertRaisesRegex(ValueError, 'origins'):
            configuration(values)
        values = self.values()
        values['MTA_DB_NAME'] = values['MTO_DB_NAME'] = 'same'
        with self.assertRaisesRegex(ValueError, 'database names'):
            configuration(values)

    def test_external_http_and_overlapping_subnets_never_trigger_repairs(self):
        values = self.values()
        values.update(VF_PUBLIC_URL='http://example.test:8080', VF_PUBLIC_WS_URL='ws://example.test:8080')
        with self.assertRaisesRegex(ValueError, 'TLS'):
            configuration(values)
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            non_overlapping_subnet('192.168.3.0/28', ['192.168.0.0/16'])
        self.assertEqual(non_overlapping_subnet('192.168.3.0/28', ['172.16.0.0/16']), '192.168.3.0/28')

    def test_operator_file_supports_windows_bom_quotes_but_not_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'operator.env'
            path.write_text('\ufeff# operator\nVF_RELEASE="abc"\n', encoding='utf-8')
            self.assertEqual(environment(path), {'VF_RELEASE': 'abc'})
            path.write_text('VF_RELEASE=a\nVF_RELEASE=b\n')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                environment(path)
