"""Frozen fixture identity must fail closed before any database mutation."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.stage2_vm_contract import atomic, roster, sealed


class Stage2ManifestTests(unittest.TestCase):
    def manifest(self):
        return {'identity': 'fixture', 'sources': [{'source': 'Demo_BPR_1', 'tables': [
            {'schema_name': 'dbo', 'table_name': 'BPR_Table', 'file': 'rows.gz'}]}]}

    def test_seal_detects_even_whitespace_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            atomic(data / 'dataset-manifest.json', self.manifest())
            digest = hashlib.sha256((data / 'dataset-manifest.json').read_bytes()).hexdigest()
            value=self.manifest();value['sources'][0]['tables'][0]['count']=1
            atomic(data / 'dataset-manifest.json', value)
            digest=hashlib.sha256((data / 'dataset-manifest.json').read_bytes()).hexdigest()
            atomic(data / 'manifest-seal.json', {'identity': 'fixture', 'manifest_sha256': digest,'tables':1,'rows':1})
            self.assertEqual(sealed(data)[1], digest)
            with (data / 'dataset-manifest.json').open('a') as stream:
                stream.write('\n')
            with self.assertRaisesRegex(ValueError, 'seal changed'):
                sealed(data)

    def test_schema_collision_is_rejected(self):
        value = self.manifest()
        value['sources'][0]['tables'][0]['schema_name'] = 'other'
        with self.assertRaisesRegex(ValueError, 'unique dbo'):
            roster(value)

    def test_casefold_duplicate_is_rejected(self):
        value = self.manifest()
        value['sources'][0]['tables'].append({'schema_name': 'dbo', 'table_name': 'bpr_table', 'file': 'other.gz'})
        with self.assertRaisesRegex(ValueError, 'unique dbo'):
            roster(value)

    def test_atomic_receipt_replaces_complete_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            atomic(path, {'status': 'IN_PROGRESS'})
            atomic(path, {'status': 'VERIFIED', 'tables': [1, 2]})
            self.assertEqual(json.loads(path.read_text()), {'status': 'VERIFIED', 'tables': [1, 2]})
            self.assertFalse(path.with_suffix('.json.tmp').exists())
