"""Successor orchestration guards; no calculation or database execution."""
from datetime import date
import gzip
import hashlib
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
from mta.runtime.management.commands.run_temporal import Command
from mta.runtime.management.commands.record_parity import CONTRACTS
from mta.runtime.temporal import BOUNDARIES, KIND
from mta.runtime.temporal_continuation import (RUNNER_PATHS, composed_prefix,
    copy_prefix_evidence, mapping_digest, validate_accepted_prefix,
    validate_source_transition, successor_index)
from mta.serialization import digest
from parity.temporal_policy import POLICY


class Manager:
    def __init__(self, rows): self.rows=rows
    def order_by(self, *args): return self.rows


class Successors:
    def filter(self, **kwargs): return self
    def exists(self): return False


class TemporalContinuationTests(unittest.TestCase):
    def test_identical_complete_sources_need_no_transition(self):
        current={'mta/application/a.py':'same',
                 **{path:'same-runner' for path in RUNNER_PATHS}}
        result=validate_source_transition({'files':dict(current)},current)
        self.assertEqual(result['schema'],'fresh-modern-successor-source-identity-v1')
        self.assertEqual(result['before_digest'],mapping_digest(current))
        self.assertEqual(result['before_digest'],result['after_digest'])
        self.assertEqual(result['changes'],[])
        for changed in ({**current,'mta/application/a.py':'changed'},
                        {**current,'mta/application/new.py':'added'},
                        {k:v for k,v in current.items() if k!='mta/application/a.py'}):
            with self.assertRaisesRegex(ValueError,'Unreviewed engine/application'):
                validate_source_transition({'files':current},changed)

    def test_continuation_rejects_frozen_root_retry_before_any_io(self):
        with self.assertRaisesRegex(CommandError,'cannot reuse a failed root'):
            Command().handle(continue_from=Path('accepted'),mdm_retry='failed')

    def test_source_transition_is_exact_and_semantic_drift_fails(self):
        old={'files': {'mta/application/a.py':'same', 'mta/presentation/views.py':'old',
            **{path:'old-runner' for path in RUNNER_PATHS}}}
        current={'mta/application/a.py':'same', 'mta/presentation/views.py':'new',
            **{path:'new-runner' for path in RUNNER_PATHS}}
        reviewed=[dict(path='mta/presentation/views.py',before='old',after='new')]
        with patch('mta.runtime.temporal_continuation.REVIEWED_NON_EXECUTION_TRANSITION',
                   mapping_digest(reviewed)):
            result=validate_source_transition(old,current)
            self.assertEqual(result['reviewed_non_execution_digest'],mapping_digest(reviewed))
            changed={**current,'mta/application/a.py':'changed'}
            with self.assertRaisesRegex(ValueError,'Unreviewed engine/application'):
                validate_source_transition(old,changed)

    def test_composed_prefix_preserves_effective_revision(self):
        execution={'revision':'day-one-revision','days':[{'day_index':0}]}
        composed=composed_prefix(execution)
        self.assertEqual(composed[0]['execution_revision'],'day-one-revision')
        self.assertNotIn('execution_revision',execution['days'][0])

    def test_only_immediate_successor_is_permitted(self):
        execution={'days':[{'day_index':0}]};case={'days':[{},{}]}
        self.assertEqual(successor_index(execution,1,case),1)
        for through in (0,2):
            with self.assertRaisesRegex(ValueError,'exactly one immediate successor'):
                successor_index(execution,through,case)

    def test_prefix_manifest_and_actions_are_byte_identical_at_same_paths(self):
        with TemporaryDirectory() as directory:
            parent=Path(directory); previous=parent/'previous'; target=parent/'next'
            (previous/'day-000').mkdir(parents=True); target.mkdir()
            manifest=b'{"manifest":"unchanged"}\n'; action=b'action-gzip-bytes'
            (previous/'day-000/manifest.json').write_bytes(manifest)
            (previous/'actions-000.json.gz').write_bytes(action)
            copied=copy_prefix_evidence(previous,target,
                {'days':[{'day_index':0,'output_archive':'day-000/manifest.json'}]})
            self.assertEqual((target/'day-000/manifest.json').read_bytes(),manifest)
            self.assertEqual((target/'actions-000.json.gz').read_bytes(),action)
            self.assertEqual(copied[0]['output_archive'],'day-000/manifest.json')

    def test_complete_accepted_prefix_is_validated_without_mutation(self):
        checks=[dict(contract=name,status='PASS')
                for name in (*CONTRACTS,'own-action-selection','post-action-state')]
        statuses={row['contract']:row['status'] for row in checks}
        output={'ClosingState':[{}],'DBMFinal':[{'Suggestions':[]}]}
        state={'Suggestions':[]}; events=[dict(id=1,digest='d',before='b',after='a')]
        command=dict(after_day=0,cohort='automatic-own-suggestions',operation='APPLY',
                     selected=[],timestamp='2026-06-06T12:00:00+05:30')
        event=SimpleNamespace(pk=1,payload=dict(operation='APPLY',selected=[],
            timestamp='2026-06-06T12:00:00+05:30',actor='retained-synthetic-trial'),
            digest='d',before_digest='b',after_digest='a')
        run=SimpleNamespace(pk='run-1',status='SUCCEEDED',kind=KIND,
            business_date=date(2026,6,6),predecessor_id=None,input_digest='input',
            output_digest='output',execution_revision='revision',commands=Manager([event]),
            successors=Successors())
        day=dict(day_index=0,date='2026-06-06',status='COMPUTED_NOT_YET_PARITY',
            input_sha256='artifact',run_id='run-1',predecessor_id=None,input_digest='input',
            output_digest='output',closing_digest=digest(output['ClosingState']),
            output_archive='day-000/manifest.json',post_action_state_digest=digest(state),
            boundaries=list(BOUNDARIES),suggestions=0,
            commands=[dict(id=1,command=command,digest='d',before='b',after='a')])
        execution=dict(artifact_sha256='artifact',artifact_days=2,requested_days=1,
            revision='revision',action_policy=POLICY,days=[day])
        case={'days':[{'business_date':'2026-06-06'},{'business_date':'2026-06-07'}]}
        with TemporaryDirectory() as directory:
            root=Path(directory); previous=root/'modern'; (previous/'day-000').mkdir(parents=True)
            (previous/'day-000/manifest.json').write_text('{}')
            execution_path=previous/'execution.json';execution_path.write_text(json.dumps(execution))
            replay=dict(modern_execution_sha256=hashlib.sha256(execution_path.read_bytes()).hexdigest(),
                input_sha256='artifact',action_policy=POLICY,status='PASS',days=[dict(
                    day_index=0,date='2026-06-06',status='PASS',modern_run='run-1',
                    modern_output_digest='output',comparisons=checks)])
            replay_path=root/'replay.json';replay_path.write_text(json.dumps(replay))
            run.parity_summary=dict(receipt='replay.json',sha256=hashlib.sha256(replay_path.read_bytes()).hexdigest(),
                day_index=0,artifact_sha256='artifact',status='PASS',boundaries=list(BOUNDARIES),
                comparisons=statuses,legacy_flaw_is_parity=False)
            with gzip.open(previous/'actions-000.json.gz','wt',encoding='utf-8') as stream:
                json.dump({'state':state,'events':events},stream)
            with patch.dict(os.environ,{'VF_EVIDENCE_ROOT':str(root/'runtime')}), \
                    patch('mta.runtime.models.CalculationRun.objects.get',return_value=run), \
                    patch('mta.runtime.services.read_outputs',return_value=output), \
                    patch('mta.runtime.temporal.command_state',return_value=(state,events)), \
                    patch('parity.output_archive.OutputArchive') as archive:
                self.assertIs(validate_accepted_prefix(previous,execution,case),run)
                archive.return_value.verify.assert_called_once_with('output')
            run.output_digest='changed'
            with patch.dict(os.environ,{'VF_EVIDENCE_ROOT':str(root/'runtime')}), \
                    patch('mta.runtime.models.CalculationRun.objects.get',return_value=run):
                with self.assertRaisesRegex(ValueError,'run identity'):
                    validate_accepted_prefix(previous,execution,case)


if __name__=='__main__':unittest.main()
