import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.serialization import digest
from parity import offline_temporal as offline


def dump_gzip(path, value):
    with gzip.open(path, 'xt', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, separators=(',', ':'))


def load_gzip(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


class OfflineTemporalTest(unittest.TestCase):
    namespace = {'VFTEST_DBM': 'VFTEST_Fresh_Owned_DBM'}

    def test_day_three_repair_transition_rejects_unrelated_changes(self):
        old={'parity/adapters/legacy/temporal_day.py':'old',
             'parity/offline_temporal.py':'old','canonical.sql':'fixed'}
        new={**old,'parity/adapters/legacy/temporal_day.py':'new','parity/offline_temporal.py':'new'}
        sha='ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56'
        path=self.root/'transition.json'
        def check(after):
            value=dict(schema='fresh-legacy-day3-conversion-repair-v1',input_sha256=sha,
                       day_index=2,before=old,after=after)
            path.write_text(json.dumps(value))
            return offline._repair_transition(path,offline._sha(path),after,sha)
        self.assertEqual(check(new)['before'],old)
        with self.assertRaisesRegex(ValueError,'exceeds approved'):
            check({**new,'canonical.sql':'changed'})
        with self.assertRaisesRegex(ValueError,'identity differs'):
            offline._repair_transition(path,'0'*64,new,sha)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifact = self.root / 'artifact.json'
        self.case = {
            'opening': {'dbm': {'Suggestions': []}}, 'opening_date': '2026-06-05',
            'days': [{'business_date': '2026-06-06'}, {'business_date': '2026-06-07'}],
            'static_day': {}, 'commands': [],
            'profile': {'synthetic_action_policy':
                        'own-recommendations-apply-eligible-retained-sleep-v1'},
        }
        self.artifact.write_text(json.dumps({'case': self.case}), encoding='utf-8')
        self.artifact_sha = offline._sha(self.artifact)
        self.authority = SimpleNamespace(
            source_files=lambda: {'parity/source.py': 'source-sha'},
            dump_gzip=dump_gzip, load_gzip=load_gzip,
        )

    def tearDown(self):
        self.temp.cleanup()

    def result(self, prior):
        return {
            'closing': {'dbm': {'Suggestions': []}, 'prior': prior},
            'post_commands': [], 'post_command_state': {'Suggestions': []},
            'scripts': [{'path': 'canonical.sql', 'sha256': 'sql-sha'}],
            'command_inputs': [], 'post_command_receipts': [],
        }

    def capture(self, index, destination, previous=None, previous_sha=None):
        with patch.object(offline, '_registered_artifact'), \
             patch.object(offline, '_authority', return_value=self.authority), \
             patch.object(offline, '_bound_namespace', return_value=self.namespace), \
             patch.object(offline, '_execute_legacy_day',
                          side_effect=lambda prior, *args, **kwargs: self.result(prior)):
            return offline.capture_legacy_day(
                artifact=self.artifact, expected_sha=self.artifact_sha,
                destination=destination, day_index=index, namespace=self.namespace,
                predecessor_receipt=previous,
                predecessor_receipt_sha256=previous_sha,
            )

    def test_legacy_capture_is_independent_of_modern_output(self):
        target = self.root / 'legacy-0'
        receipt = self.capture(0, target)
        self.assertEqual(receipt['status'], 'CAPTURED')
        self.assertEqual(receipt['action_policy'], self.case['profile']['synthetic_action_policy'])
        self.assertIsNone(receipt['predecessor'])
        self.assertEqual(load_gzip(receipt['capture_path'])['post_commands'], [])
        self.assertNotIn('modern', json.dumps(receipt).lower())

    def test_capture_destination_is_immutable_and_failed_attempt_is_retained(self):
        target = self.root / 'attempt'
        target.mkdir()
        with self.assertRaisesRegex(ValueError, 'Preserve prior attempt'):
            self.capture(0, target)
        failed = self.root / 'failed'
        with patch.object(offline, '_registered_artifact'), \
             patch.object(offline, '_bound_namespace', side_effect=ValueError('wrong namespace')):
            with self.assertRaisesRegex(ValueError, 'wrong namespace'):
                offline.capture_legacy_day(
                    artifact=self.artifact, expected_sha=self.artifact_sha,
                    destination=failed, day_index=0, namespace=self.namespace)
        receipt = json.loads((failed / 'receipt.json').read_text())
        self.assertEqual(receipt['status'], 'FAILED')
        self.assertEqual(receipt['error_type'], 'ValueError')

    def test_next_day_requires_verified_contiguous_own_closing(self):
        first = self.root / 'legacy-0'
        self.capture(0, first)
        receipt_path = first / 'receipt.json'
        second = self.root / 'legacy-1'
        with self.assertRaisesRegex(ValueError, 'receipt digest differs'):
            self.capture(1, second, receipt_path, '0' * 64)
        self.assertEqual(json.loads((second / 'receipt.json').read_text())['status'], 'FAILED')

    def test_compare_retained_emits_record_parity_compatible_31_contracts(self):
        capture_dir = self.root / 'legacy-0'
        captured = self.capture(0, capture_dir)
        legacy = load_gzip(captured['capture_path'])
        modern_value = {'retained': 'modern'}
        modern = self.root / 'modern'
        modern.mkdir()
        dump_gzip(modern / 'day-000.json.gz', modern_value)
        dump_gzip(modern / 'actions-000.json.gz', {'state': legacy['post_command_state']})
        execution = {
            'artifact_sha256': self.artifact_sha,
            'action_policy': captured['action_policy'], 'revision': 'attempt-1',
            'report_exceptions': {},
            'days': [{
                'day_index': 0, 'date': '2026-06-06',
                'status': 'COMPUTED_NOT_YET_PARITY', 'run_id': 'run-1',
                'output_digest': digest(modern_value),
                'post_action_state_digest': digest(legacy['post_command_state']),
                'commands': [], 'input_digest': 'input',
            }],
        }
        (modern / 'execution.json').write_text(json.dumps(execution), encoding='utf-8')
        checks = [{'contract': 'contract-%02d' % index, 'status': 'PASS', 'differences': []}
                  for index in range(29)]
        authority = SimpleNamespace(
            source_files=self.authority.source_files, load_gzip=load_gzip,
            compare_day=lambda *args: list(checks),
            independent_contracts_pass=lambda rows: all(row['status'] == 'PASS' for row in rows),
        )
        destination = self.root / 'comparison'
        with patch.object(offline, '_registered_artifact'), \
             patch.object(offline, '_authority', return_value=authority), \
             patch('parity.temporal.legacy_states', return_value={'opening': []}):
            record = offline.compare_retained(
                self.artifact, self.artifact_sha, modern,
                capture_dir / 'receipt.json', destination)
        self.assertEqual(record['status'], 'PASS')
        self.assertEqual(len(record['days'][0]['comparisons']), 31)
        self.assertEqual([row['contract'] for row in record['days'][0]['comparisons'][-2:]],
                         ['own-action-selection', 'post-action-state'])
        persisted = json.loads((destination / 'replay.json').read_text())
        self.assertEqual(persisted['modern_execution_sha256'], offline._sha(modern / 'execution.json'))

    def test_compare_stops_at_first_divergence_and_preserves_receipt(self):
        capture_dir = self.root / 'legacy-0'
        captured = self.capture(0, capture_dir)
        modern = self.root / 'modern'
        modern.mkdir()
        value = {'retained': 'modern'}
        dump_gzip(modern / 'day-000.json.gz', value)
        (modern / 'execution.json').write_text(json.dumps({
            'artifact_sha256': self.artifact_sha,
            'action_policy': captured['action_policy'], 'report_exceptions': {},
            'days': [{'day_index': 0, 'date': '2026-06-06',
                      'status': 'COMPUTED_NOT_YET_PARITY', 'run_id': 'run-1',
                      'output_digest': digest(value), 'commands': []}],
        }), encoding='utf-8')
        authority = SimpleNamespace(
            source_files=self.authority.source_files, load_gzip=load_gzip,
            compare_day=lambda *args: [{'contract': 'first', 'status': 'FAIL',
                                        'differences': [{'path': '/first'}]}],
            independent_contracts_pass=lambda rows: all(row['status'] == 'PASS' for row in rows),
        )
        destination = self.root / 'divergence'
        with patch.object(offline, '_registered_artifact'), \
             patch.object(offline, '_authority', return_value=authority), \
             patch('parity.temporal.legacy_states', return_value={'opening': []}):
            record = offline.compare_retained(
                self.artifact, self.artifact_sha, modern,
                capture_dir / 'receipt.json', destination)
        self.assertEqual(record['status'], 'DIVERGENCE')
        self.assertEqual(len(record['days'][0]['comparisons']), 1)
        self.assertTrue((destination / 'replay.json').exists())


if __name__ == '__main__':
    unittest.main()
