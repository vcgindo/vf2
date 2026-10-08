"""MDM runner wiring only: no engine execution, SQL replay or admission claim."""
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
from mta.runtime.models import MdmSource


class MdmRunnerTests(unittest.TestCase):
    def test_requires_exact_source_binding_and_explicit_horizon(self):
        command = runner.Command()
        with self.assertRaisesRegex(CommandError, 'supplied together'):
            command.handle(mdm_source='source')
        with self.assertRaisesRegex(CommandError, 'explicit bound source'):
            command.handle(mdm_retry='failed-run')
        source = SimpleNamespace(pk='owned', digest='d'*64)
        with patch.object(MdmSource.objects, 'get', return_value=source), \
                self.assertRaisesRegex(CommandError, 'explicit BPR remark horizon'):
            command.handle(mdm_source='owned', mdm_source_digest='d'*64)

    def test_binds_both_smoke_days_to_owned_source_and_own_predecessor(self):
        artifact = Path('D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/ten-pair-input-v1.json')
        checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
        source = SimpleNamespace(pk='owned-mdm-test', digest='d'*64)
        calls = []
        def execute(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(pk='run-'+str(len(calls)),
                predecessor_id=None if len(calls)==1 else 'run-1',
                input_digest='input', output_digest='output', validation_digest='validation')
        output = {'ClosingState': [{}], 'DBMFinal': [{'Suggestions': []}]}
        with TemporaryDirectory() as directory, \
                patch.object(MdmSource.objects, 'get', return_value=source), \
                patch('mta.mdm.daily_source.require_binding') as binding, \
                patch.object(runner, 'execute_day', side_effect=execute), \
                patch.object(runner, 'export_run', side_effect=lambda run,path:path/'manifest.json'), \
                patch.object(runner, 'read_outputs', return_value=output), \
                patch.object(runner, 'command_state', return_value=({}, [])), \
                patch.object(runner, 'OutputArchive') as archive:
            archive.return_value.iter_rows.return_value=[]
            target=Path(directory)/'trial'
            runner.Command(stdout=io.StringIO()).handle(input=artifact, sha256=checksum,
                revision='mdm-runner-unit', evidence=target, through=1, exceptions=None,
                automatic_actions=False, mdm_source=source.pk, mdm_source_digest=source.digest,
                bpr_remark_horizon=90,
                shipment_input=artifact.with_name('ten-pair-shipment-input-v1.json'),
                shipment_sha256='dee26721ff67a7e09cb70dde849a43976a0132ea71a3a3402705a55b393664ae')
            receipt=json.loads((target/'execution.json').read_text())
            binding.assert_called_once_with(source, artifact_sha256=checksum,
                artifact_schema=json.loads(artifact.read_text()).get('schema'))
        self.assertEqual(len(calls), 2)
        self.assertEqual([len(call['day']['shipment_input']['rows']) for call in calls],[15,14])
        self.assertTrue(all(call['mdm_source'] is source for call in calls))
        self.assertIsNone(calls[0]['predecessor'])
        self.assertEqual(calls[1]['predecessor'].pk, 'run-1')
        self.assertIsNone(calls[1]['opening'])
        self.assertTrue(all(call['pick_output_root'] is None and call['pick_config_sha256'] is None
                            and 'complete_pick' not in call['profile'] for call in calls))
        self.assertTrue(calls[0]['profile']['daily_publication'])
        self.assertEqual(calls[0]['profile']['daily_publication_config']['bpr_remark_horizon'], 90)
        self.assertEqual(receipt['mdm_source']['digest'], source.digest)
        self.assertTrue(all(day['status']=='COMPUTED_NOT_YET_PARITY' for day in receipt['days']))

    def test_frozen_retry_routes_first_day_without_recapturing_source(self):
        artifact = Path('D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/ten-pair-input-v1.json')
        source = SimpleNamespace(pk='owned-mdm-test', digest='d'*64)
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        with TemporaryDirectory() as directory, \
                patch.object(MdmSource.objects, 'get', return_value=source), \
                patch.object(MdmDailyInputCapture.objects, 'filter') as captures, \
                patch('mta.mdm.daily_source.require_binding'), \
                patch.object(runner, 'execute_day', side_effect=RuntimeError('stop after routing')) as execute:
            captures.return_value.exists.return_value = True
            target = Path(directory)/'retry'
            with self.assertRaisesRegex(RuntimeError, 'stop after routing'):
                runner.Command(stdout=io.StringIO()).handle(input=artifact,
                    sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    revision='frozen-retry-unit', evidence=target, through=0, exceptions=None,
                    automatic_actions=False, mdm_source=source.pk, mdm_source_digest=source.digest,
                    bpr_remark_horizon=90, mdm_retry='failed-root')
            self.assertEqual(execute.call_args.kwargs['mdm_retry'], 'failed-root')
            self.assertNotIn('mdm_source', execute.call_args.kwargs)
            self.assertEqual(json.loads((target/'execution.json').read_text())['days'][0]['retry_of'], 'failed-root')
