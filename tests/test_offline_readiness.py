import hashlib
from copy import deepcopy
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.runtime import offline_transition as transition
from parity.accepted_prefix import CONTRACTS, verify_prefix
from tools import offline_temporal_validation as runner


class ReadinessGuards(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def write(self,name,value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value));return dict(path=str(path),sha256=runner.sha(path))
    def fixture(self):
        day=dict(day_index=0,date='2026-06-06',run_id='run0',output_digest='output0',
            post_action_state_digest='actions0',execution_revision='revision0')
        execution=dict(revision='revision0',artifact_sha256='input',action_policy='policy',days=[day])
        modern={**execution,'days':[day,{**day,'day_index':1,'date':'2026-06-07'}]}
        capture={'closing_digest':'closing0','post_action_state_digest':'legacy-actions0'};cp=self.write('legacy0/receipt.json',capture)
        entry=dict(day_index=0,date=day['date'],status='PASS',modern_run='run0',
            modern_output_digest='output0',post_action_state_digest='legacy-actions0',
            capture_receipt=cp,closing_digest='closing0',comparisons=[dict(contract=c,status='PASS')
                for c in (*CONTRACTS,'own-action-selection','post-action-state')])
        ex=self.write('modern0/execution.json',execution)
        replay=self.write('compare0/replay.json',dict(status='PASS',input_sha256='input',
            action_policy='policy',modern_execution_sha256=ex['sha256'],requested_days=1,days=[entry]))
        rrr=self.write('compare0/rrr-source.json',dict(status='PASS',run_id='run0',output_digest='output0'))
        accepted=self.write('compare0/accepted.json',dict(status='PASS',modern=str(Path(ex['path']).parent),
            legacy=str(Path(cp['path']).parent),replay_sha256=replay['sha256'],rrr_sha256=rrr['sha256']))
        descriptor=dict(day_index=0,accepted=accepted,replay=replay,rrr=rrr,execution=ex)
        lineage=[(Path(cp['path']),capture),(self.root/'legacy1/receipt.json',{})]
        return descriptor,modern,lineage,entry
    def test_exact_prefix_reused_without_opening_populations(self):
        d,m,l,e=self.fixture();self.assertEqual(verify_prefix([d],m,l),[e])
    def test_readiness_hold_prevents_engines_and_publication(self):
        with patch.object(transition,'transition',return_value={'business_calculation_release':False}), \
                patch.object(runner,'initialize') as initialize:
            with self.assertRaisesRegex(ValueError,'human release'):
                runner.execute(SimpleNamespace())
            initialize.assert_not_called()
            with self.assertRaisesRegex(ValueError,'human release'):
                runner.publish(SimpleNamespace(restore=False))
            runner.require_release(SimpleNamespace(release_calculations=True),'calculations')
    def test_pinned_modern_receipts_reject_changed_source(self):
        ex=self.write('modern/execution.json',{'days':[{'day_index':0}]})
        source=self.write('modern/source.json',{'files':{}})
        with patch.object(transition,'transition',return_value={'modern_retained':[dict(execution=ex,sources=source)]}):
            self.assertEqual(runner.retained_modern(self.root,0),self.root/'modern')
            Path(source['path']).write_text('{}')
            with self.assertRaisesRegex(ValueError,'identity changed'):runner.retained_modern(self.root,0)
        sibling=self.write('modern/sibling.json',{'days':[{'day_index':0}]})
        with patch.object(transition,'transition',return_value={'modern_retained':[dict(execution=sibling,sources=source)]}):
            with self.assertRaisesRegex(ValueError,'paths differ'):runner.retained_modern(self.root,0)
    def test_new_acceptance_requires_transition_binding(self):
        d,_,_,_=self.fixture()
        path=Path(d['accepted']['path']).parent
        with patch.object(transition,'transition',return_value={'accepted_prefix':[]}), \
                patch.dict(os.environ,{transition.SHA_ENV:'trusted'}), \
                patch.object(runner,'latest',return_value=path):
            with self.assertRaisesRegex(ValueError,'matching readiness'):runner.prefix_receipts(self.root,1)
    def test_readiness_worker_cannot_change_image_or_resources(self):
        original={'services':{'mta':{'image':'old','mem_limit':'4g','cpus':2}}}
        self.write('worker-compose.json',original)
        worker=self.write('candidate.json',{'services':{'mta':{'image':'wrong','mem_limit':'4g','cpus':2}}})
        package=dict(execution_id='x',sources={},image='old',databases={},input={'sha256':'input'})
        old=self.write('package.json',package)
        value=dict(execution_id='x',package_sha256=old['sha256'],before_sources={},before_image='old',
            databases={},input_sha256='input',worker_compose=worker,after_image='new',modern_retained=[])
        with patch.object(transition,'transition',return_value=value):
            with self.assertRaisesRegex(ValueError,'isolation and resources'):runner.readiness_package(self.root,package)
    def test_comparison_only_cannot_advance_past_anchor(self):
        from contextlib import nullcontext
        self.write('package.json',{})
        with patch.object(transition,'transition',return_value={'accepted_prefix':[{},{}]}), \
                patch.object(runner,'owned',return_value=self.root), \
                patch.object(runner,'execution_lock',return_value=nullcontext()), \
                patch.object(runner,'require_package_sources'), \
                patch.object(runner,'summary',return_value={'accepted_dates':[1,2,3]}), \
                patch.object(runner,'bounded_legacy_command') as compare:
            with self.assertRaisesRegex(ValueError,'anchored next'):runner.compare_next(SimpleNamespace(execution_id='x'))
            compare.assert_not_called()
    def test_tamper_gap_and_prefix_drift_denied(self):
        d,m,l,e=self.fixture()
        with self.assertRaisesRegex(ValueError,'next unaccepted'):verify_prefix([],m,l)
        with self.assertRaisesRegex(ValueError,'gap'):verify_prefix([{**d,'day_index':1}],m,l)
        m['days'][0]['post_action_state_digest']='changed'
        with self.assertRaisesRegex(ValueError,'counterpart'):verify_prefix([d],m,l)
        m['days'][0]['post_action_state_digest']='actions0'
        Path(d['replay']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'digest'):verify_prefix([d],m,l)
    def test_rehashed_missing_contract_still_denied(self):
        d,m,l,e=self.fixture();p=Path(d['replay']['path']);v=json.loads(p.read_text())
        v['days'][0]['comparisons'].pop();p.write_text(json.dumps(v));d['replay']['sha256']=runner.sha(p)
        ap=Path(d['accepted']['path']);a=json.loads(ap.read_text());a['replay_sha256']=d['replay']['sha256']
        ap.write_text(json.dumps(a));d['accepted']['sha256']=runner.sha(ap)
        with self.assertRaisesRegex(ValueError,'contracts'):verify_prefix([d],m,l)
    def test_transition_hash_scope_and_modern_source_drift_denied(self):
        v=dict(schema='fresh-offline-readiness-v1',approval=transition.APPROVAL,
            execution_id='temporal-full-001',input_sha256=transition.INPUT,
            business_calculation_release=False,publication_release=False,
            modern_before=[{'old':'pin'}],modern_after={'new':'pin'})
        anchor=self.write('transition.json',v)
        with patch.dict(os.environ,{transition.PATH_ENV:anchor['path'],transition.SHA_ENV:anchor['sha256']}):
            self.assertTrue(transition.modern_sources({'old':'pin'},{'new':'pin'}))
            with self.assertRaisesRegex(ValueError,'source transition'):transition.modern_sources({'old':'changed'},{'new':'pin'})
            Path(anchor['path']).write_text('{}')
            with self.assertRaisesRegex(ValueError,'hash'):transition.transition()
    def test_comparison_first_failure_stops_before_next_day(self):
        modern=self.root/'modern';legacy=self.root/'legacy'
        runner.save(self.root/'protected-before.json',{})
        def latest(_,pattern,*args,**kwargs):return modern if pattern.startswith('modern') else None
        with patch.object(runner,'latest',side_effect=latest),patch.object(runner,'retained_legacy',return_value=legacy), \
                patch.object(runner,'modern_day',return_value=modern) as calculate, \
                patch.object(runner,'bounded_legacy_command',side_effect=runner.ComparisonFailure('first mismatch')), \
                patch.object(runner,'worker') as worker:
            with self.assertRaises(runner.ComparisonFailure):
                runner.execute_locked(SimpleNamespace(mode='combined',execution_id='test'),self.root,
                    dict(input={'execution_through':2},scenario='full',execution_id='test'))
            self.assertEqual(calculate.call_count,1);worker.assert_not_called()
    def test_next_day_comparator_never_loads_prefix_population(self):
        from tests.test_offline_temporal import OfflineTemporalTest,load_gzip,dump_gzip
        from parity import offline_temporal as offline
        from mta.serialization import digest
        fixture=OfflineTemporalTest();fixture.setUp()
        try:
            first=fixture.root/'legacy0';second=fixture.root/'legacy1'
            fixture.capture(0,first)
            captured=fixture.capture(1,second,first/'receipt.json',offline._sha(first/'receipt.json'))
            legacy=load_gzip(captured['capture_path']);modern=fixture.root/'modern';modern.mkdir()
            output={'independent':'modern'};dump_gzip(modern/'day-001.json.gz',output)
            dump_gzip(modern/'actions-001.json.gz',{'state':legacy['post_command_state']})
            execution=dict(artifact_sha256=fixture.artifact_sha,action_policy=captured['action_policy'],
                days=[{},dict(day_index=1,date='2026-06-07',status='COMPUTED_NOT_YET_PARITY',
                    run_id='second',output_digest=digest(output),post_action_state_digest=digest(legacy['post_command_state']),commands=[])])
            (modern/'execution.json').write_text(json.dumps(execution))
            def bounded_load(path):
                if Path(path).is_relative_to(first):raise AssertionError('Loaded accepted population')
                return load_gzip(path)
            authority=SimpleNamespace(source_files=fixture.authority.source_files,load_gzip=bounded_load,
                compare_day=lambda *args:[dict(contract=c,status='PASS') for c in CONTRACTS],
                independent_contracts_pass=lambda rows:all(r['status']=='PASS' for r in rows))
            with patch.object(offline,'_registered_artifact'),patch.object(offline,'_authority',return_value=authority), \
                    patch('parity.legacy_isolation.MAPPING',fixture.namespace), \
                    patch('parity.temporal.legacy_states',return_value={}), \
                    patch('parity.accepted_prefix.verify_prefix',return_value=[dict(day_index=0,status='PASS')]):
                result=offline.compare_retained(fixture.artifact,fixture.artifact_sha,modern,
                    second/'receipt.json',fixture.root/'comparison',accepted_prefix=[{}])
            self.assertEqual(result['status'],'PASS');self.assertEqual(len(result['days'][1]['comparisons']),31)
        finally:fixture.tearDown()
    def test_only_known_preparation_dependency_gets_one_retry(self):
        ready={'status':'READY','receipt':{'digest':'same'}}
        before=dict(status='INCOMPLETE',layers={'rrr':ready,'bpr':ready,'planning_expedite_transit':
            dict(status='FAILED',error_type='DoesNotExist',error='RrrPreparedProjection matching query does not exist.')})
        after=dict(status='READY',layers={**before['layers'],'planning_expedite_transit':ready})
        with patch.object(runner,'worker',side_effect=[RuntimeError('failed'),None]) as worker, \
                patch.object(runner,'last_json',side_effect=[before,after]):
            self.assertEqual(runner.prepare_terminal(self.root,[]),after);self.assertEqual(worker.call_count,2)
        before['layers']['planning_expedite_transit']['error']='different failure'
        with patch.object(runner,'worker',side_effect=RuntimeError('failed')) as worker, \
                patch.object(runner,'last_json',return_value=before):
            with self.assertRaises(RuntimeError):runner.prepare_terminal(self.root,[])
            self.assertEqual(worker.call_count,1)


class DbmReadinessChain(unittest.TestCase):
    setUp = ReadinessGuards.setUp
    tearDown = ReadinessGuards.tearDown
    write = ReadinessGuards.write
    def chain(self):
        worker = self.write('readiness-v1/worker.json',
            {'services':{'mta':{'image':'old','mem_limit':'4g','cpus':2}}})
        pins = {p:b for p,(b,_) in runner.DBM_SOURCE_TRANSITION.items()}
        pins['tools/offline_temporal_validation.py'] = 'old-runner'
        parent = dict(schema='fresh-offline-readiness-v1', version=5,
            approval=transition.APPROVAL, execution_id='temporal-full-001',
            input_sha256=transition.INPUT, business_calculation_release=False,
            publication_release=False, after_image='old', worker_compose=worker,
            after_sources=pins, modern_after=dict(pins), legacy_after=dict(pins),
            modern_before=[{'retained':'exact'}], accepted_prefix=[{'retained':'anchor'}],
            package_sha256='original', protected_baseline={'unchanged':True})
        anchor = self.write('readiness-v1/transition-a005.json',parent)
        candidate = self.write('readiness-dbm-v1/worker-compose.json',
            {'services':{'mta':{'image':runner.DBM_READINESS_IMAGE,'mem_limit':'4g','cpus':2}}})
        child = deepcopy(parent)
        for field in ('after_sources','modern_after','legacy_after'):
            child[field].update({p:a for p,(_,a) in runner.DBM_SOURCE_TRANSITION.items()})
        path='tools/offline_temporal_validation.py'; after=runner.sha(runner.ROOT/path)
        child['after_sources'][path]=after
        child.update(version=6, prior_transition_sha256=anchor['sha256'],
            after_image=runner.DBM_READINESS_IMAGE, worker_compose=candidate,
            readiness_extension=dict(schema='fresh-offline-readiness-chain-v1',
                approval='01a117d2-e638-7761-9382-cd0cecfe79b1',parent=anchor,
                candidate_commit='d004dc10426d486cd130d00d747124db03107e26',
                candidate_image=runner.DBM_READINESS_IMAGE,
                source_changes={p:dict(before=b,after=a) for p,(b,a) in runner.DBM_SOURCE_TRANSITION.items()},
                runner_changes={path:dict(before='old-runner',after=after)}))
        return anchor,child

    def test_fixed_runtime_accepts_exact_host_authorized_chain(self):
        parent,child=self.chain();bound=self.write('child.json',child)
        with patch.object(runner,'owned',return_value=self.root), \
                patch.object(runner,'DBM_READINESS_PARENT',parent['sha256']), \
                patch.dict(os.environ,{transition.PATH_ENV:bound['path'],transition.SHA_ENV:bound['sha256']}):
            self.assertEqual(transition.transition(),child)
            runner.validate_readiness_extension(child)

    def test_rehashed_scope_expansion_and_worker_change_denied(self):
        parent,child=self.chain()
        mutations=[lambda c:c.pop('readiness_extension'),
            lambda c:c['readiness_extension'].update(approval='wrong'),
            lambda c:c['readiness_extension']['parent'].update(sha256='wrong'),
            lambda c:c['readiness_extension'].update(candidate_commit='wrong'),
            lambda c:c.update(after_image='wrong'),
            lambda c:c.update(business_calculation_release=True),
            lambda c:c.update(publication_release=True),
            lambda c:c.update(accepted_prefix=[]),
            lambda c:c.update(package_sha256='changed'),
            lambda c:c.update(protected_baseline={}),
            lambda c:c.update(modern_before=[]),
            lambda c:c['after_sources'].update(extra='fourth-source'),
            lambda c:c['modern_after'].update(extra='fourth-source'),
            lambda c:c['legacy_after'].update(extra='fourth-source'),
            lambda c:c['after_sources'].update({'tools/offline_temporal_validation.py':'wrong'})]
        with patch.object(runner,'owned',return_value=self.root), \
                patch.object(runner,'DBM_READINESS_PARENT',parent['sha256']):
            for index,mutate in enumerate(mutations):
                bad=deepcopy(child);mutate(bad)
                with self.subTest(case=index),self.assertRaisesRegex(ValueError,'exact approved'):
                    runner.validate_readiness_extension(bad)
            self.write('readiness-dbm-v1/worker-compose.json',
                {'services':{'mta':{'image':runner.DBM_READINESS_IMAGE,'mem_limit':'8g','cpus':2}}})
            with self.assertRaisesRegex(ValueError,'only image'):
                runner.validate_readiness_extension(child)

    def test_cli_and_inherited_environment_validate_before_dispatch(self):
        parent,child=self.chain();child['readiness_extension']['approval']='wrong'
        bound=self.write('child.json',child)
        for cli in (False,True):
            args=['runner','summary','--execution-id','temporal-full-001']
            if cli:args+=['--transition-file',bound['path'],'--transition-sha256',bound['sha256']]
            with patch.object(runner,'owned',return_value=self.root), \
                    patch.object(runner,'DBM_READINESS_PARENT',parent['sha256']), \
                    patch.dict(os.environ,{transition.PATH_ENV:bound['path'],transition.SHA_ENV:bound['sha256']}), \
                    patch('sys.argv',args),patch('sys.stdout',io.StringIO()), \
                    patch.object(runner,'summary') as summary:
                with self.assertRaisesRegex(ValueError,'exact approved'):runner.main()
                summary.assert_not_called()


if __name__=='__main__':unittest.main()
