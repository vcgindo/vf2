import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import Client


class FoundationTest(unittest.TestCase):
    def test_health_does_not_claim_parity(self):
        response = Client().get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['parity'], 'NOT_CERTIFIED')

    def test_canonical_api_identity(self):
        manifest = json.loads(Path('baseline/manifest.json').read_text())
        self.assertEqual(len(manifest['canonical_api']), 2)
        self.assertEqual({r['sha256'] for r in manifest['canonical_api']}, {
            '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346'})
        self.assertGreater(len(manifest['engine_sources']), 100)

    def test_sizeable_inputs_not_substituted(self):
        manifest = json.loads(Path('baseline/manifest.json').read_text())
        parent = next(r for r in manifest['retained_resources']
                      if r['path'].endswith('block1-selected-consumers/input.json'))
        self.assertEqual(parent['sha256'], '8ea842061fc03687eafb30b152e3228e91632fb00914e894c1957cf049f753ec')
