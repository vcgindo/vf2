"""Complete Pick command forwarding only; no engine or database execution."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from django.core.management.base import CommandError
from mta.runtime.management.commands import run_temporal as runner


ARTIFACT = Path('D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/ten-pair-input-v1.json')


class CompletePickRunnerTests(unittest.TestCase):
    def config(self, artifact):
        locations = sorted({row['from_location'] for row in
                            artifact['case']['profile']['calculation']['logistics']['items']})
        return dict(vehicles=[dict(vehicle_id=7, name='OWNED-PICK-TRUCK',
                    weight_capacity=1000, volume_capacity=1000)],
                    location_vehicles=[dict(location_code=location, vehicle_id=7)
                                       for location in locations])

    def options(self, root, config_path, config_sha):
        raw = ARTIFACT.read_bytes()
        return dict(input=ARTIFACT, sha256=hashlib.sha256(raw).hexdigest(),
            revision='pick-runner-unit', evidence=root/'evidence', through=0,
            exceptions=None, automatic_actions=False, mdm_source=None,
            mdm_source_digest=None, mdm_retry=None, bpr_remark_horizon=None,
            shipment_input=None, shipment_sha256=None, continue_from=None,
            computation_only=False, bounded_one_day=False, verify_prefix_only=False,
            complete_pick_policy='canonical-tied-order-v1', pick_output_root=root,
            pick_config=config_path, pick_config_sha256=config_sha)

    def test_forwards_digest_bound_configuration_and_owned_root(self):
        artifact = json.loads(ARTIFACT.read_text())
        original = deepcopy(artifact['case']['profile'])
        config = self.config(artifact)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root/'pick.json'
            config_path.write_text(json.dumps(config), encoding='utf-8')
            options = self.options(root, config_path, hashlib.sha256(config_path.read_bytes()).hexdigest())
            calls = []
            def execute(**kwargs):
                calls.append(kwargs)
                return SimpleNamespace(pk='pick-run', predecessor_id=None, input_digest='input',
                    output_digest='output', validation_digest='validation')
            output = {'ClosingState': [{}], 'DBMFinal': [{'Suggestions': []}]}
            with patch.object(runner, 'execute_day', side_effect=execute), \
                    patch.object(runner, 'export_run', side_effect=lambda run, path: path/'manifest.json'), \
                    patch.object(runner, 'read_outputs', return_value=output), \
                    patch.object(runner, 'command_state', return_value=({}, [])), \
                    patch.object(runner, 'OutputArchive') as archive:
                archive.return_value.iter_rows.return_value = []
                runner.Command(stdout=io.StringIO()).handle(**options)
            self.assertEqual(len(calls), 1)
            call = calls[0]
            self.assertEqual(call['pick_output_root'], root.resolve())
            self.assertEqual(call['pick_config_sha256'], options['pick_config_sha256'])
            self.assertEqual(call['profile']['complete_pick'],
                             {'policy': 'canonical-tied-order-v1'})
            logistics = call['profile']['calculation']['logistics']
            self.assertEqual(logistics['vehicles'], config['vehicles'])
            self.assertEqual(logistics['location_vehicles'], config['location_vehicles'])
            self.assertNotIn('vehicle', logistics)
            self.assertEqual(logistics['items'], original['calculation']['logistics']['items'])
            receipt = json.loads((root/'evidence'/'execution.json').read_text())
            self.assertEqual(receipt['artifact_sha256'], options['sha256'])
            self.assertEqual(receipt['complete_pick'], dict(
                policy='canonical-tied-order-v1', output_root=str(root.resolve()),
                config_sha256=options['pick_config_sha256']))

    def test_complete_pick_options_are_all_or_none_and_digest_bound(self):
        artifact = json.loads(ARTIFACT.read_text())
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root/'pick.json'
            config_path.write_text(json.dumps(self.config(artifact)), encoding='utf-8')
            options = self.options(root, config_path, '0'*64)
            with self.assertRaisesRegex(CommandError, 'digest differs'):
                runner.Command(stdout=io.StringIO()).handle(**options)
            options['pick_config_sha256'] = None
            with self.assertRaisesRegex(CommandError, 'supplied together'):
                runner.Command(stdout=io.StringIO()).handle(**options)


if __name__ == '__main__':
    unittest.main()
