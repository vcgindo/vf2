"""Finite stopped-prefix reader proofs; no database or calculation execution."""
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID
import unittest

from tests.test_captured_fourth_boundary import Graph
from mta.runtime import captured_input as ci
from mta.runtime.daily_feed_models import DailyFeedAttempt
from mta.runtime.models import CalculationRun
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.serialization import digest


class FiniteGraph(Graph):
    def __init__(self, depth=6, *, child=False):
        super().__init__(depth+int(child))
        self.leaf=self.runs[-2] if child else self.runs[-1]
        self.leaf.status='RUNNING'
        self.attempts=[]
        for index,(run,capture) in enumerate(zip(self.runs,self.captures)):
            capture.run_id=run.pk
            capture.origin_id=capture.origin.pk if capture.origin else None
            self.attempts.append(SimpleNamespace(id=index+100,attempt_id=UUID(int=index+100),
                status='RUNNING' if run is self.leaf or index==len(self.runs)-1 and child else 'FAILED',
                phase='CALCULATE',accepted_facts={'physical':True} if index==0 else {},
                initialization_id=self.init,run_id=run.pk,recovery_origin_id=None))
        if child:self.attempts[-1].recovery_origin_id=self.attempts[-2].id

    def patches(self):
        stack=super().patches()
        stack.enter_context(patch.object(DailyFeedAttempt.objects,'get',
            side_effect=lambda **kw:self.attempts[self.runs.index(kw['run'])]))
        def values(**kw):
            rows=[dict(run_id=a.run_id,initialization_id=a.initialization_id,
                       recovery_origin_id=a.recovery_origin_id)
                  for a in self.attempts if a.run_id in kw['run_id__in']]
            return SimpleNamespace(values=lambda *args:rows)
        stack.enter_context(patch.object(DailyFeedAttempt.objects,'filter',side_effect=values))
        def metadata(obj):
            if obj in self.runs:
                return dict(id=str(obj.pk),status=obj.status,input_payload=obj.input_payload,
                            input_manifest_digest=obj.input_manifest_digest)
            if obj in self.captures:
                return dict(run_id=str(obj.pk),status=obj.status,
                            origin_id=str(obj.origin_id) if obj.origin_id else None)
            return dict(id=obj.id,attempt_id=str(obj.attempt_id),status=obj.status,
                        phase=obj.phase,accepted_facts=obj.accepted_facts)
        stack.enter_context(patch.object(ci,'_metadata',side_effect=metadata))
        def prefix_digest(leaf):
            stop=self.runs.index(leaf)
            return digest([dict(run=metadata(self.runs[index]),capture=metadata(self.captures[index]),
                                attempt=metadata(self.attempts[index]))
                           for index in range(stop,-1,-1)])
        stack.enter_context(patch.object(ci,'_finite_prefix_digest',side_effect=prefix_digest))
        return stack

    def seal_child(self):
        candidate=self.runs[-1]
        candidate.execution_revision='native-finite-'+'e'*40
        _,_,prefix=ci.finite_prefix(self.leaf)
        candidate.input_payload=ci.finite_manifest(candidate,self.leaf,
            expected_prefix_digest=prefix,packaged_source='e'*40)
        candidate.input_manifest_digest=digest(candidate.input_payload)
        return candidate


class FiniteBoundaryTests(unittest.TestCase):
    def test_exact_six_prefix_and_physical_reference_without_payload_copy(self):
        graph=FiniteGraph(child=True)
        with graph.patches():
            run=graph.seal_child()
            self.assertIs(ci.origin(run),graph.runs[0])
            self.assertEqual(run.input_payload['images'],{})
            self.assertEqual(len(ci.finite_prefix(graph.leaf)[1]),7)
            self.assertEqual(graph.leaf.status,'RUNNING')
            self.assertEqual(graph.attempts[-2].status,'RUNNING')
            with self.assertRaisesRegex(ValueError,'another continuation'):
                ci._origin(run,second_allowed=True,third_allowed=True,fourth_allowed=True,
                           fifth_allowed=True,sixth_allowed=True)

    def test_other_depths_leaf_status_and_cycle_rejected(self):
        for depth in (1,2,3,4,5,7):
            graph=FiniteGraph(depth)
            with self.subTest(depth=depth),graph.patches(),self.assertRaises(ValueError):
                ci.finite_prefix(graph.leaf)
        graph=FiniteGraph()
        with graph.patches():
            for status in ('FAILED','SUCCEEDED'):
                graph.leaf.status=status
                with self.assertRaises(ValueError):ci.finite_prefix(graph.leaf)
            graph.leaf.status='RUNNING'
            graph.captures[-1].origin=graph.captures[-1]
            with self.assertRaises(ValueError):ci.finite_prefix(graph.leaf)

    def test_manifest_pins_original_metadata_physical_and_canonical_child(self):
        for change in ('prefix','physical','manifest','attempt','revision','sibling','initialization','child'):
            graph=FiniteGraph(child=True)
            with self.subTest(change=change),graph.patches():
                run=graph.seal_child()
                if change=='prefix':graph.attempts[2].phase='foreign'
                if change=='physical':run.input_payload['physical_origin_run_id']=str(UUID(int=999))
                if change=='manifest':run.input_manifest_digest='0'*64
                if change=='attempt':run.input_payload['origin_attempt_id']=str(UUID(int=999))
                if change=='revision':run.execution_revision='foreign'
                if change=='sibling':graph.captures[-2].retries.exclude.return_value.exists.return_value=True
                if change=='initialization':graph.attempts[-1].initialization_id=UUID(int=999)
                if change=='child':graph.attempts[-1].recovery_origin_id=999
                if change in ('physical','attempt'):run.input_manifest_digest=digest(run.input_payload)
                with self.assertRaises(ValueError):ci.origin(run)

    def test_metadata_includes_every_concrete_field_and_lossless_uuid(self):
        run=CalculationRun(id=UUID(int=42),failure={'original':'preserve'})
        values=ci._metadata(run)
        self.assertEqual(set(values),{field.attname for field in run._meta.concrete_fields})
        self.assertEqual(values['id'],str(run.pk))
        self.assertEqual(values['failure'],{'original':'preserve'})
        digest(values)

    def test_operational_commit_resolves_only_proven_chain_without_publication(self):
        from mta.runtime.daily_feed import _finite_resolved_ancestors
        graph=FiniteGraph(child=True)
        with graph.patches(),patch.object(CalculationRun.objects,'filter') as manager:
            run=graph.seal_child()
            run.mdm_input_capture=graph.captures[-1]
            manager.return_value.iterator.return_value=iter([run])
            self.assertEqual(_finite_resolved_ancestors('owned'),[str(r.pk) for r in reversed(graph.runs[:-1])])
            self.assertIn('COMMITTED',manager.call_args.kwargs['csv_attempt__status__in'])
            self.assertEqual(manager.call_args.kwargs['production_manifest__version'],3)
            graph.attempts[1].status='RUNNING'
            manager.return_value.iterator.return_value=iter([run])
            with self.assertRaises(ValueError):_finite_resolved_ancestors('owned')

    def test_report_generation_and_route_source_are_not_empty_output_exceptions(self):
        from mta.runtime import captured_recovery as recovery
        from mta.runtime import models
        from mta.runtime.offline_rrr_models import OfflineRrrColourSource
        from mta.runtime.report_generation_models import DailyReportGeneration,DailyReportOrderRouteSource
        guarded=(models.PickProjection,models.ExcessProjection,models.FulfillmentProjection,
                 models.ExpediteProjection,models.PickPostProjection,models.DailySourceReceipt,
                 OfflineRrrColourSource,DailyReportGeneration,DailyReportOrderRouteSource)
        for populated in (None,DailyReportGeneration,DailyReportOrderRouteSource):
            with self.subTest(populated=populated),ExitStack() as stack:
                cursor=stack.enter_context(patch.object(recovery.connection,'cursor'))
                cursor.return_value.__enter__.return_value.fetchone.return_value=None
                for model in guarded:
                    manager=stack.enter_context(patch.object(model.objects,'filter'))
                    manager.return_value.exists.return_value=model is populated
                if populated is None:recovery._empty_terminal_outputs(SimpleNamespace(pk=UUID(int=1)))
                else:
                    with self.assertRaisesRegex(ValueError,'report generation rows'):
                        recovery._empty_terminal_outputs(SimpleNamespace(pk=UUID(int=1)))


if __name__=='__main__':unittest.main()
