import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.cohort6_bind_day import bind


class Cohort6BindDayTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.template = {
            'version': 'fresh-presentation-hierarchy-v1',
            'role': 'presentation-only-retained-hierarchy',
            'catalogue_sha256': 'c' * 64,
            'allowed_fields': {'products': ['SL1', 'SL2', 'SL3'],
                               'locations': ['LL1', 'LL2', 'LL3']},
            'catalogue_counts': {'products': 200, 'locations': 20},
            'publications': [{'run_id': 'old', 'business_date': '2026-06-17',
                              'output_digest': 'x' * 64}],
            'authorization': 'approved retained hierarchy',
        }
        self.receipt = {
            'status': 'SUCCEEDED', 'run_id': '12345678-1234-5678-9234-567812345678',
            'business_date': '2026-06-06', 'input_digest': 'i' * 64,
            'output_digest': 'o' * 64, 'validation_digest': '',
            'evidence_mode': 'production', 'seconds': 1.0,
            'publication': 'unselected; parity and preparation are separate',
        }
        self.template_path = self.root / 'template.json'
        self.receipt_path = self.root / 'run.json'
        self.template_path.write_text(json.dumps(self.template), encoding='utf-8')
        self.receipt_path.write_text(json.dumps(self.receipt), encoding='utf-8')
        self.template_sha = hashlib.sha256(
            self.template_path.read_bytes()).hexdigest()

    def test_binds_only_exact_successful_run_publication(self):
        target = self.root / 'bound.json'
        result = bind(self.template_path, self.template_sha, self.receipt_path,
                      '2026-06-06', target)
        value = json.loads(target.read_text())
        expected = {'run_id': '12345678-1234-5678-9234-567812345678',
                    'business_date': '2026-06-06',
                    'output_digest': 'o' * 64}
        self.assertEqual(value['publications'], [expected])
        self.assertEqual({k: v for k, v in value.items()
                          if k != 'publications'},
                         {k: v for k, v in self.template.items()
                          if k != 'publications'})
        self.assertEqual(result['sha256'], hashlib.sha256(target.read_bytes()).hexdigest())

    def test_changed_hash_date_receipt_or_existing_output_denies(self):
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            bind(self.template_path, '0' * 64, self.receipt_path,
                 '2026-06-06', self.root / 'one.json')
        with self.assertRaisesRegex(ValueError, 'successful'):
            bind(self.template_path, self.template_sha, self.receipt_path,
                 '2026-06-07', self.root / 'two.json')
        changed = dict(self.receipt, status='FAILED')
        self.receipt_path.write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'successful'):
            bind(self.template_path, self.template_sha, self.receipt_path,
                 '2026-06-06', self.root / 'three.json')
        self.receipt_path.write_text(json.dumps(self.receipt), encoding='utf-8')
        existing = self.root / 'existing.json'
        existing.write_text('preserve', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            bind(self.template_path, self.template_sha, self.receipt_path,
                 '2026-06-06', existing)
        self.assertEqual(existing.read_text(), 'preserve')
