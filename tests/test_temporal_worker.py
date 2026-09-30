"""Validation-orchestration guards only; no replacement parity fixture."""
from copy import deepcopy
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from parity.temporal_policy import POLICY, commands_for_day
from tools.temporal_worker import sequence, verify_sources, sha, select_day_inputs, predecessor_process


class TemporalWorkerTests(unittest.TestCase):
    def example(self):
        case = {'days': [{'business_date':'2026-06-%02d' % d} for d in (6,7,8)]}
        record = dict(artifact_sha256='pinned', action_policy=POLICY, requested_days=3, artifact_days=3,
            days=[dict(day_index=0,date='2026-06-06',status='COMPUTED_NOT_YET_PARITY',input_sha256='pinned')])
        return record, case

    def test_only_next_day_can_follow_unchanged_prefix(self):
        record, case = self.example()
        before = deepcopy(record)
        self.assertEqual(sequence(record,case,'pinned'),1)
        self.assertEqual(record,before)

    def test_rejects_input_policy_horizon_or_prefix_substitution(self):
        for key,value in (('artifact_sha256','other'),('action_policy','other'),('requested_days',2)):
            record,case=self.example(); record[key]=value
            with self.assertRaises(ValueError):sequence(record,case,'pinned')
        for key,value in (('day_index',1),('date','2026-06-07'),('status','RUNNING'),('input_sha256','other')):
            record,case=self.example(); record['days'][0][key]=value
            with self.assertRaises(ValueError):sequence(record,case,'pinned')

    def test_engine_and_orchestration_source_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'engine.py').write_text('unchanged')
            source=dict(files={'engine.py':sha(root/'engine.py')})
            (root/'source.json').write_text(json.dumps(source))
            with patch('tools.temporal_worker.ROOT',root):
                self.assertEqual(verify_sources(root),source)
                source['one_day_worker']=dict(path='tools/temporal_worker.py',sha256='substituted')
                (root/'source.json').write_text(json.dumps(source))
                with self.assertRaises(ValueError):verify_sources(root)
                source.pop('one_day_worker')
                (root/'source.json').write_text(json.dumps(source))
                (root/'engine.py').write_text('changed')
                with self.assertRaises(ValueError):verify_sources(root)

    def test_retained_worker_requires_exact_archived_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'worker-source.py').write_text('retained worker')
            pinned=sha(root/'worker-source.py')
            source=dict(files={},one_day_worker=dict(path='tools/temporal_worker.py',sha256=pinned))
            (root/'source.json').write_text(json.dumps(source))
            with patch('tools.temporal_worker.RETAINED_WORKER',pinned):
                self.assertEqual(verify_sources(root),source)
                (root/'worker-source.py').write_text('changed worker')
                with self.assertRaises(ValueError):verify_sources(root)

    def test_unused_artifact_release_preserves_day_profile_and_policy(self):
        _,case=self.example()
        for day in case['days']:day['external_facts']=[{'quantity':7}]
        case.update(profile={'unchanged':True}, static_day={'settings':[1,2]}, opening={'unused':[3]},
            commands=[dict(after_day=0,operation='SLEEP',selected=[['337','AG515802']],
                           timestamp='2026-06-06T12:00:00+05:30')])
        before=deepcopy(case)
        own=[dict(SKUCode='337',WhCode='AG515802'),dict(SKUCode='6404',WhCode='PPI000604')]
        for index in range(3):
            profile,day,policy=select_day_inputs(case,index)
            self.assertIs(profile,case['profile'])
            self.assertEqual(day,{**case['days'][index],**case['static_day']})
            self.assertEqual(commands_for_day(policy,index,own),commands_for_day(case,index,own))
            self.assertNotIn('opening',policy)
            self.assertEqual(set(policy['days'][index]),{'business_date'})
        self.assertEqual(case,before)

    def test_predecessor_verification_is_awaited_and_failure_stops_parent(self):
        with patch('tools.temporal_worker.subprocess.run') as run:
            run.return_value.stdout = '{"status":"VERIFIED","predecessor_id":"retained"}'
            self.assertEqual(predecessor_process(Path('/evidence/previous'))['status'],'VERIFIED')
            args, kwargs = run.call_args
            self.assertEqual(args[0][-3:],['verify-predecessor','--previous',str(Path('/evidence/previous'))])
            self.assertTrue(kwargs['check'])
            run.side_effect = subprocess.CalledProcessError(1,args[0],stderr='integrity mismatch')
            with self.assertRaises(subprocess.CalledProcessError):
                predecessor_process(Path('/evidence/previous'))

    def test_day12_transition_is_exact_and_does_not_rewrite_prior_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            engine = root/'mta/temporal/chain.py'
            engine.parent.mkdir(parents=True)
            engine.write_text('old calculator')
            source = {'files': {'mta/temporal/chain.py': sha(engine)}}
            source_path = root/'source.json'
            source_path.write_text(json.dumps(source))
            original_source = source_path.read_bytes()
            execution = dict(artifact_sha256='same-artifact', days=[{'run_id':'same-parent'}]*11)
            (root/'execution.json').write_text(json.dumps(execution))
            before = sha(engine)
            engine.write_text('reviewed memory boundary')
            transition = root/'baseline/f2-day12-memory-transition.json'
            transition.parent.mkdir()
            approval = dict(schema='f2-day12-memory-transition-v1',day_index=11,
                artifact_sha256='same-artifact',predecessor_id='same-parent',
                accepted_modern_execution_sha256=sha(root/'execution.json'),
                files={'mta/temporal/chain.py':dict(before=before,after=sha(engine))})
            transition.write_text(json.dumps(approval))
            with patch('tools.temporal_worker.ROOT',root), patch('tools.temporal_worker.TRANSITION_SHA',sha(transition)):
                with self.assertRaises(ValueError): verify_sources(root)
                result = verify_sources(root,transition)
                self.assertEqual(result['files']['mta/temporal/chain.py'],sha(engine))
                self.assertEqual(result['runtime_transition']['day_index'],11)
                self.assertEqual(source_path.read_bytes(),original_source)
                engine.write_text('unapproved further change')
                with self.assertRaises(ValueError): verify_sources(root,transition)
                engine.write_text('reviewed memory boundary')
                transition.write_text(json.dumps({**approval,'predecessor_id':'substituted'}))
                with self.assertRaisesRegex(ValueError,'manifest changed'): verify_sources(root,transition)
                transition.write_text(json.dumps(approval))
                execution['days'][-1]={'run_id':'different-parent'}
                (root/'execution.json').write_text(json.dumps(execution))
                with self.assertRaises(ValueError): verify_sources(root,transition)


if __name__=='__main__':unittest.main()
