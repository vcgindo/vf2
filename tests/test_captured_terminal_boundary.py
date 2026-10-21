"""The single terminal reference retains the unchanged old finite reader.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import copy
from uuid import UUID
from unittest.mock import patch,MagicMock
import unittest
from tests.test_captured_finite_boundary import FiniteGraph
from mta.runtime import captured_input as ci
from mta.serialization import digest


class TerminalBoundaryTests(unittest.TestCase):
    def graph(self):
        graph=FiniteGraph(child=True)
        stack=graph.patches()
        leaf=graph.seal_child()
        candidate=copy(leaf);candidate.pk=UUID(int=99)
        candidate.identity=dict(leaf.identity,owner_id=str(candidate.pk))
        candidate.execution_revision='native-terminal-'+'f'*40
        cap=copy(graph.captures[-1]);cap.pk=cap.run_id=candidate.pk;cap.run=candidate
        cap.origin=graph.captures[-1];cap.origin_id=leaf.pk;cap.retries=MagicMock()
        cap.retries.exclude.return_value.exists.return_value=False
        attempt=copy(graph.attempts[-1]);attempt.id=999;attempt.attempt_id=UUID(int=999)
        attempt.run_id=candidate.pk;attempt.recovery_origin_id=graph.attempts[-1].id
        graph.runs.append(candidate);graph.captures.append(cap);graph.attempts.append(attempt)
        def pin(leaf):
            return digest([dict(run=ci._metadata(r),capture=ci._metadata(c),attempt=ci._metadata(a))
                for r,c,a in reversed(list(zip(graph.runs[:-1],graph.captures[:-1],graph.attempts[:-1])))])
        stack.enter_context(patch.object(ci,'_terminal_prefix_digest',side_effect=pin))
        _,_,prefix=ci.terminal_prefix(leaf)
        candidate.input_payload=ci.terminal_manifest(candidate,leaf,expected_prefix_digest=prefix,packaged_source='f'*40)
        candidate.input_manifest_digest=digest(candidate.input_payload)
        return graph,leaf,candidate,stack

    def test_exact_eight_readable_no_further_continuation(self):
        graph,leaf,run,stack=self.graph()
        with stack:
            self.assertIs(ci.origin(run),graph.runs[0])
            self.assertEqual(len(ci.terminal_prefix(leaf)[1]),8)
            self.assertEqual(run.input_payload['images'],{})
            with self.assertRaises(ValueError):ci.terminal_prefix(run)
            with self.assertRaises(ValueError):ci.finite_prefix(leaf)
            with self.assertRaises(ValueError):ci.manifest(run,run)

    def test_changed_prefix_source_attempt_schema_and_sibling_rejected(self):
        for change in ('prefix','source','attempt','schema','sibling','parentstatus','parentorigin'):
            graph,leaf,run,stack=self.graph()
            with self.subTest(change=change),stack:
                if change=='prefix':graph.attempts[2].phase='foreign'
                if change=='source':graph.captures[-1].source_id=99
                if change=='attempt':graph.attempts[-1].recovery_origin_id=9999
                if change=='schema':run.input_payload['schema']=ci.FINITE
                if change=='sibling':graph.captures[-2].retries.exclude.return_value.exists.return_value=True
                if change=='parentstatus':leaf.status='FAILED'
                if change=='parentorigin':graph.attempts[-2].recovery_origin_id=None
                with self.assertRaises(ValueError):ci.origin(run)

    def test_operational_resolution_includes_only_authenticated_eight(self):
        from mta.runtime.daily_feed import _finite_resolved_ancestors
        from mta.runtime.models import CalculationRun
        graph,leaf,run,stack=self.graph()
        with stack,patch.object(CalculationRun.objects,'filter') as manager:
            run.mdm_input_capture=graph.captures[-1]
            manager.return_value.iterator.return_value=iter([run])
            self.assertEqual(_finite_resolved_ancestors('owned'),[str(r.pk) for r in reversed(graph.runs[:-1])])


class TerminalNativeAuditTests(unittest.TestCase):
    def test_running_audit_origin_requires_authenticated_terminal_and_same_scope(self):
        from types import SimpleNamespace
        from mta.mdm import native_audit as audit
        from mta.runtime.initialization_models import ProductionInitialization
        profile={'fixture':'frozen-audit-policy'}
        policy={'timezone':audit.settings.VF_MTA_ACTION_TIME_ZONE}
        run=SimpleNamespace(pk=UUID(int=99),kind='DAILY_CHAIN',status='RUNNING',
            predecessor_id=None,business_date='2037-04-10',
            input_payload={'schema':ci.TERMINAL,'origin_run_id':str(UUID(int=98))})
        source=SimpleNamespace(receipt={'schema':'fresh-production-mdm-source-v1'})
        daily=SimpleNamespace(run_id=run.pk,source=source,source_id=1,origin_id=UUID(int=98))
        original=SimpleNamespace(run=SimpleNamespace(status='RUNNING'),run_id=daily.origin_id,
            source_id=1,predecessor_id=None,business_date=run.business_date)
        with patch.object(audit,'validate_policy',return_value=policy), \
                patch.object(ProductionInitialization.objects,'get',return_value=SimpleNamespace(configuration_digest=digest(profile))), \
                patch.object(audit.NativeUploadAudit.objects,'select_related') as manager, \
                patch.object(audit,'verify',side_effect=lambda value,**kw:value), \
                patch.object(audit,'_policy',return_value=policy), \
                patch.object(ci,'origin') as resolve, \
                patch.object(audit,'images',side_effect=RuntimeError('reached frozen source')):
            manager.return_value.get.return_value=original
            with self.assertRaisesRegex(RuntimeError,'reached frozen source'):
                audit.bind(run,daily,profile)
            resolve.assert_called_once_with(run)
            original.source_id=2
            with self.assertRaisesRegex(ValueError,'not the frozen failed request'):
                audit.bind(run,daily,profile)
            original.source_id=1
            resolve.side_effect=ValueError('tampered terminal prefix')
            with self.assertRaisesRegex(ValueError,'tampered terminal prefix'):
                audit.bind(run,daily,profile)


if __name__=='__main__':unittest.main()
