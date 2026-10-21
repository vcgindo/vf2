"""Fixed canonical depth and ownership proofs, no database or business run.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from datetime import date
from types import SimpleNamespace
from uuid import UUID
from unittest.mock import MagicMock, patch
import os, unittest
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','fourth-boundary-unit-only')
import django
django.setup()
from mta.serialization import digest
from mta.runtime import captured_input as ci
from mta.runtime.models import CalculationRun
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.daily_feed_models import DailyFeedAttempt


class Graph:
    def __init__(self,depth):
        self.runs=[];self.captures=[]
        self.init=UUID('00000000-0000-4000-8000-000000000100')
        for i in range(depth+1):
            run=SimpleNamespace(pk=UUID(int=i+1),kind='DAILY_CHAIN',status='FAILED',
                evidence_mode='production',business_date=date(2026,4,8),predecessor_id=None,
                execution_revision='r'+str(i),input_digest='a'*64,output_digest='',output_roster=[],production_digest='',
                checkpoints=MagicMock(),commands=MagicMock(),successors=MagicMock())
            for name in ('checkpoints','commands','successors'):getattr(run,name).exists.return_value=False
            run.identity=dict(database_name='owned_unit',database_oid=9,source_digest='b'*64,owner_kind='run',owner_id=str(run.pk))
            if not i:
                run.input_payload=dict(schema='fresh-daily-input-manifest-v3',content_digest=run.input_digest)
            else:
                parent=self.runs[-1]
                run.input_payload=dict(schema=ci.SCHEMA if i==1 else ci.SECOND,identity=run.identity,
                    origin_run_id=str(parent.pk),origin_manifest_digest=parent.input_manifest_digest,
                    content_digest=run.input_digest,images={})
                if i>1:run.input_payload.update(physical_origin_run_id=str(self.runs[0].pk),
                    physical_origin_manifest_digest=self.runs[0].input_manifest_digest)
            run.input_manifest_digest=digest(run.input_payload)
            capture=SimpleNamespace(pk=run.pk,run=run,source_id=1,status='CAPTURED',
                request_digest='c'*64,revision_digest='d'*64,origin=self.captures[-1] if i else None,
                retries=MagicMock())
            capture.retries.exclude.return_value.exists.return_value=False
            self.runs.append(run);self.captures.append(capture)
        self.runs[-1].status='RUNNING'

    def patches(self):
        from contextlib import ExitStack
        stack=ExitStack()
        def get_capture(*args,**kw):
            run=kw['run'];return self.captures[self.runs.index(run)]
        def attempts(**kw):
            return SimpleNamespace(values=lambda *args:[dict(run_id=k,initialization_id=self.init)
                for k in kw['run_id__in']])
        stack.enter_context(patch('mta.runtime.input_v3._live_identity',side_effect=lambda run,**kw:run.identity))
        manager=stack.enter_context(patch.object(MdmDailyInputCapture,'objects'))
        manager.select_related.return_value.get.side_effect=get_capture
        stack.enter_context(patch.object(DailyFeedAttempt.objects,'filter',side_effect=attempts))
        stack.enter_context(patch.object(CalculationRun.objects,'get',side_effect=lambda **kw:next(r for r in self.runs if r.pk==kw['pk'])))
        return stack


class FourthBoundaryTests(unittest.TestCase):
    def test_terminal_reader_preserves_all_ancestry_and_sixth_is_denied(self):
        for depth in (1,2,3,4,5,6):
            g=Graph(depth)
            with g.patches():
                if depth<=5:self.assertIs(ci.origin(g.runs[-1]),g.runs[0])
                else:
                    with self.assertRaisesRegex(ValueError,'fixed third-hop boundary'):ci.origin(g.runs[-1])

    def test_default_writer_stays_three_explicit_fourth_never_fifth(self):
        for depth in (1,2,3,4):
            g=Graph(depth)
            candidate=SimpleNamespace(pk=UUID(int=99),identity=dict(g.runs[-1].identity,owner_id=str(UUID(int=99))))
            with g.patches():
                if depth<=2:self.assertEqual(ci.manifest(candidate,g.runs[-1])['schema'],ci.SECOND)
                else:
                    with self.assertRaisesRegex(ValueError,'fixed third-hop boundary'):ci.manifest(candidate,g.runs[-1])
                if depth<=3:
                    self.assertEqual(ci.manifest(candidate,g.runs[-1],final_interrupted_fourth_hop=True)['physical_origin_run_id'],str(g.runs[0].pk))
                else:
                    with self.assertRaisesRegex(ValueError,'fixed third-hop boundary'):
                        ci.manifest(candidate,g.runs[-1],final_interrupted_fourth_hop=True)

    def test_foreign_cut_digest_status_sibling_and_cycle_fail_closed(self):
        for change in ('source','date','status','manifest','digest','sibling','cycle','init'):
            g=Graph(4);run=g.runs[-1];old=g.runs[-2];capture=g.captures[-1]
            if change=='source':capture.source_id=2
            if change=='date':old.business_date=date(2026,4,9)
            if change=='status':old.status='SUCCEEDED'
            if change=='manifest':run.input_manifest_digest='0'*64
            if change=='digest':old.input_digest='0'*64
            if change=='sibling':g.captures[-2].retries.exclude.return_value.exists.return_value=True
            if change=='cycle':capture.origin=capture
            with self.subTest(change=change),g.patches():
                if change=='init':
                    with patch.object(DailyFeedAttempt.objects,'filter') as manager:
                        manager.return_value.values.return_value=[dict(run_id=run.pk,initialization_id='one'),dict(run_id=old.pk,initialization_id='other')]
                        with self.assertRaises(ValueError):ci.origin(run)
                else:
                    with self.assertRaises(ValueError):ci.origin(run)

    def test_exact_interrupted_owner_and_other_depths_are_denied(self):
        from mta.runtime.captured_recovery import _second_hop_owner
        from mta.runtime.publication_models import DailyUiPublication
        for depth in (2,3,4):
            g=Graph(depth);leaf=g.runs[-1];physical=g.runs[0]
            attempt=SimpleNamespace(status='RUNNING',phase='CALCULATE',accepted_facts={},
                initialization_id=g.init,input_sha256='e'*64,batch_digest='f'*64)
            original=SimpleNamespace(attempt_id=UUID(int=500),status='FAILED',accepted_facts={'owned':True},
                initialization_id=g.init,input_sha256='e'*64,batch_digest='f'*64)
            value=dict(physical_run_id=str(physical.pk),physical_manifest_digest=physical.input_manifest_digest,
                physical_attempt_id=str(original.attempt_id),current_revision_cut=[0,0,1,1,0])
            with g.patches(),patch.object(DailyFeedAttempt.objects,'get',return_value=original), \
                    patch.object(DailyUiPublication.objects,'filter') as pubs:
                pubs.return_value.exists.return_value=False
                if depth==3:
                    self.assertIs(_second_hop_owner(leaf,attempt,value,final_interrupted_fourth_hop=True),physical)
                    for field,replacement in (('status','FAILED'),('phase','VALIDATED'),('accepted_facts',{'foreign':True})):
                        before=getattr(attempt,field);setattr(attempt,field,replacement)
                        with self.assertRaises(ValueError):_second_hop_owner(leaf,attempt,value,final_interrupted_fourth_hop=True)
                        setattr(attempt,field,before)
                    with self.assertRaises(ValueError):
                        _second_hop_owner(leaf,attempt,value,final_third_hop=True,final_interrupted_fourth_hop=True)
                else:
                    with self.assertRaises(ValueError):_second_hop_owner(leaf,attempt,value,final_interrupted_fourth_hop=True)

    def test_private_fourth_allowance_requires_its_third_prefix(self):
        g=Graph(4)
        with g.patches(),self.assertRaisesRegex(ValueError,'complete third-hop prefix'):
            ci._origin(g.runs[-1],second_allowed=True,fourth_allowed=True)
        for flag in ('yes',1,None):
            candidate=SimpleNamespace(identity={})
            with patch('mta.runtime.input_v3._live_identity',return_value={}), self.assertRaisesRegex(ValueError,'flag required'):
                ci.manifest(candidate,g.runs[-1],final_interrupted_fourth_hop=flag)

    def test_only_failed_fourth_origin_can_supply_explicit_terminal_fifth(self):
        from mta.runtime.captured_recovery import _second_hop_owner
        from mta.runtime.publication_models import DailyUiPublication
        for depth in (1,2,3,4,5,6):
            g=Graph(depth);leaf=g.runs[-1];leaf.status='FAILED';physical=g.runs[0]
            candidate=SimpleNamespace(pk=UUID(int=99),identity=dict(leaf.identity,owner_id=str(UUID(int=99))))
            attempt=SimpleNamespace(status='FAILED',phase='CALCULATE',accepted_facts={},
                initialization_id=g.init,input_sha256='e'*64,batch_digest='f'*64)
            original=SimpleNamespace(attempt_id=UUID(int=500),status='FAILED',accepted_facts={'owned':True},
                initialization_id=g.init,input_sha256='e'*64,batch_digest='f'*64)
            spec=dict(physical_run_id=str(physical.pk),physical_manifest_digest=physical.input_manifest_digest,
                physical_attempt_id=str(original.attempt_id),current_revision_cut=[0,0,1,1,0])
            with self.subTest(depth=depth),g.patches(),patch.object(DailyFeedAttempt.objects,'get',return_value=original), \
                    patch.object(DailyUiPublication.objects,'filter') as pubs:
                pubs.return_value.exists.return_value=False
                if depth!=4:
                    with self.assertRaises(ValueError):ci.manifest(candidate,leaf,final_failed_fifth_hop=True)
                    with self.assertRaises(ValueError):_second_hop_owner(leaf,attempt,spec,final_failed_fifth_hop=True)
                    continue
                self.assertEqual(ci.manifest(candidate,leaf,final_failed_fifth_hop=True)['physical_origin_run_id'],str(physical.pk))
                self.assertIs(_second_hop_owner(leaf,attempt,spec,final_failed_fifth_hop=True),physical)
                for obj,field,value in ((leaf,'status','RUNNING'),(attempt,'status','RUNNING'),
                        (attempt,'phase','VALIDATED'),(attempt,'accepted_facts',{'foreign':True})):
                    before=getattr(obj,field);setattr(obj,field,value)
                    with self.assertRaises(ValueError):_second_hop_owner(leaf,attempt,spec,final_failed_fifth_hop=True)
                    setattr(obj,field,before)
                for flag in ('yes',1,None):
                    with self.assertRaises(ValueError):ci.manifest(candidate,leaf,final_failed_fifth_hop=flag)
                with self.assertRaises(ValueError):ci.manifest(candidate,leaf,final_failed_fifth_hop=True,final_interrupted_fourth_hop=True)
                with self.assertRaises(ValueError):_second_hop_owner(leaf,attempt,spec,final_failed_fifth_hop=True,final_third_hop=True)
                for field in ('physical_run_id','physical_manifest_digest','physical_attempt_id'):
                    with self.assertRaises(ValueError):_second_hop_owner(leaf,attempt,dict(spec,**{field:'foreign'}),final_failed_fifth_hop=True)
                with self.assertRaises(ValueError):ci._origin(leaf,second_allowed=True,third_allowed=True,fifth_allowed=True)


if __name__=='__main__':unittest.main()
