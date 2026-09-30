"""Receipt linkage checks; no synthetic calculation or legacy parity claim."""
from contextlib import nullcontext
from datetime import date
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase
from mta.runtime.management.commands.record_parity import Command, CONTRACTS
from mta.runtime.temporal import BOUNDARIES
from parity.temporal_policy import POLICY


class ParityReceiptTest(SimpleTestCase):
    def test_exact_receipt_links_bounded_metadata_and_rejects_missing_boundary(self):
        run = SimpleNamespace(pk='run-1', output_digest='output', input_digest='input',
            business_date=date(2026,6,6), execution_revision='revision', save=Mock())
        checks = [dict(contract=name,status='PASS') for name in (*CONTRACTS,'own-action-selection','post-action-state')]
        modern = dict(artifact_sha256='artifact',action_policy=POLICY,revision='revision',
            days=[dict(day_index=0,run_id='run-1',output_digest='output',input_digest='input')])
        with TemporaryDirectory() as directory:
            root=Path(directory)
            modern_path=root/'execution.json'
            modern_path.write_text(json.dumps(modern),encoding='utf-8')
            replay=dict(modern_execution_sha256=hashlib.sha256(modern_path.read_bytes()).hexdigest(),
                input_sha256='artifact',action_policy=POLICY,status='PASS',requested_days=1,days=[dict(
                    day_index=0,date='2026-06-06',status='PASS',modern_run='run-1',
                    modern_output_digest='output',comparisons=checks)])
            replay_path=root/'replay.json'
            with patch.dict('os.environ',{'VF_EVIDENCE_ROOT':str(root/'runtime')}), \
                 patch('mta.runtime.management.commands.record_parity.transaction.atomic',return_value=nullcontext()), \
                 patch('mta.runtime.management.commands.record_parity.CalculationRun.objects') as objects, \
                 patch('mta.runtime.management.commands.record_parity.read_outputs'):
                objects.select_for_update.return_value.get.return_value=run
                replay_path.write_text(json.dumps(replay),encoding='utf-8')
                Command().handle(replay=replay_path,modern_execution=modern_path)
                self.assertEqual(run.parity_summary['boundaries'],list(BOUNDARIES))
                self.assertLess(len(json.dumps(run.parity_summary)),4096)
                self.assertFalse(run.parity_summary['legacy_flaw_is_parity'])
                checks[8]['contract']='replacement'
                replay_path.write_text(json.dumps(replay),encoding='utf-8')
                with self.assertRaisesMessage(CommandError,'Incomplete comparison roster'):
                    Command().handle(replay=replay_path,modern_execution=modern_path)
                checks[8]['contract']=CONTRACTS[8]
                replay['status']='COMPLETE_WITH_LEGACY_FLAWS'
                replay_path.write_text(json.dumps(replay),encoding='utf-8')
                with self.assertRaisesMessage(CommandError,'aggregate qualification differs'):
                    Command().handle(replay=replay_path,modern_execution=modern_path)
                replay['status']='DIVERGENCE'
                replay['days'][0]['status']='DIVERGENCE'
                replay['days'][0]['comparisons']=checks[:9]
                replay['days'][0]['comparisons'][-1]['status']='FAIL'
                replay_path.write_text(json.dumps(replay),encoding='utf-8')
                Command().handle(replay=replay_path,modern_execution=modern_path)
                self.assertEqual(run.parity_summary['status'],'DIVERGENCE')
                self.assertEqual(run.parity_summary['comparisons']['post-action-state'],'NOT_RUN')
                replay['modern_execution_sha256']='wrong'
                replay_path.write_text(json.dumps(replay),encoding='utf-8')
                with self.assertRaisesMessage(CommandError,'identity differs'):
                    Command().handle(replay=replay_path,modern_execution=modern_path)
