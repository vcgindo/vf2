"""DB-blocked native publication/recovery contracts; no real day calculation."""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from datetime import date
import inspect
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('VF_SECRET_KEY','native-publication-contract-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.runtime import services, temporal
from mta.serialization import digest


class NativePublicationContractTests(unittest.TestCase):
    def setUp(self):
        guard=patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection',
                    side_effect=AssertionError('No Step3 database authority'))
        guard.start()
        self.addCleanup(guard.stop)

    def fixture(self):
        events=[]
        run=SimpleNamespace(pk='owned',kind='DAILY_CHAIN',status='RUNNING',
            input_payload={'schema':'fresh-daily-input-manifest-v2'},input_digest='a'*64,
            evidence_mode='production',production_manifest={},business_date=date(2037,4,10),
            checkpoints=MagicMock(),validation_digest='preserved-history-marker')
        run.checkpoints.exists.return_value=False
        run.save=MagicMock(side_effect=lambda **kw:events.append('run-save'))
        output=dict(Lineage=[{}],ClosingState=[{'complete':{}}],
            CalculationOutputs=[dict(capability='r1_ration_bifurcation',rows=[])])
        return run,output,events

    @contextmanager
    def publication(self,run,events,fail=False):
        # Resolve decorated modules before substituting the transaction context.
        from mta.mdm import daily_input, native_audit
        @contextmanager
        def atomic():
            events.append('atomic-enter')
            try:
                yield
            except Exception:
                events.append('atomic-rollback')
                raise
            else:events.append('atomic-commit')
        with ExitStack() as stack:
            stack.enter_context(patch.object(services.transaction,'atomic',side_effect=atomic))
            runs=stack.enter_context(patch.object(services.CalculationRun,'objects'))
            runs.select_for_update.return_value.get.return_value=run
            captures=stack.enter_context(patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects'))
            captures.filter.return_value.values_list.return_value.first.return_value=None
            stack.enter_context(patch.object(services,'read_input',return_value={'profile':{}}))
            stack.enter_context(patch('mta.runtime.receipt_integrity.audit_input',side_effect=lambda r:events.append('input-audit')))
            stack.enter_context(patch('mta.runtime.relational_state.save_daily',side_effect=lambda *a:events.append('typed-state') or {}))
            def audit_output(r):
                events.append('output-audit')
                if fail:raise ValueError('injected typed audit failure')
            stack.enter_context(patch('mta.runtime.receipt_integrity.audit_output',side_effect=audit_output))
            for module,function,label in (
                ('pick_storage','write_pick_bands','pick'),('excess_storage','write_excess','excess'),
                ('fulfillment_storage','write_fulfillment','fulfillment'),('expedite_storage','write_expedite','expedite'),
                ('pick_post_storage','write_pick_post','post-pick')):
                stack.enter_context(patch('mta.presentation.'+module+'.'+function,
                    side_effect=lambda *a,label=label,**kw:events.append(label)))
            stack.enter_context(patch('mta.mdm.daily_input.finalize_consumption',
                side_effect=lambda *a,**kw:events.append('consume')))
            stack.enter_context(patch('mta.mdm.native_audit.finalize',side_effect=lambda *a:events.append('native-audit')))
            stack.enter_context(patch('mta.runtime.receipt_integrity.source_receipts',return_value={}))
            stack.enter_context(patch('mta.runtime.receipt_integrity.output_root',return_value='root'))
            stack.enter_context(patch.object(services.Checkpoint.objects,'create',side_effect=AssertionError('trace checkpoint write')))
            yield

    def test_native_atomic_publication_keeps_audit_consumption_and_consumer_order_without_trace(self):
        run,output,events=self.fixture()
        with self.publication(run,events):
            self.assertIs(services.finish_run(run,output,expected_digest=run.input_digest),run)
        self.assertEqual(events,['atomic-enter','input-audit','typed-state','output-audit',
            'pick','excess','fulfillment','expedite','post-pick','consume','native-audit','run-save','atomic-commit'])
        self.assertEqual(run.status,'SUCCEEDED')
        self.assertEqual(run.validation_digest,'preserved-history-marker')
        self.assertNotIn('validation_digest',run.save.call_args.kwargs['update_fields'])
        self.assertEqual(run.output_roster,['BPRReports','BTRFinal','ClosingState','DBMFinal','Lineage','PublicationContext','Reports'])

    def test_failed_typed_audit_does_not_publish_status_consume_or_save(self):
        run,output,events=self.fixture()
        with self.publication(run,events,fail=True),self.assertRaisesRegex(ValueError,'injected typed audit failure'):
            services.finish_run(run,output,expected_digest=run.input_digest)
        self.assertEqual(events,['atomic-enter','input-audit','typed-state','output-audit','atomic-rollback'])
        self.assertEqual(run.status,'RUNNING')
        run.save.assert_not_called()

    def test_historical_or_untyped_daily_run_is_rejected_before_typed_writes(self):
        for change in ('mode','input'):
            run,output,events=self.fixture()
            if change=='mode':run.evidence_mode='validation'
            else:run.input_payload={}
            with self.publication(run,events),self.assertRaisesRegex(ValueError,'typed production input'):
                services.finish_run(run,output,expected_digest=run.input_digest)
            self.assertEqual(events,['atomic-enter','atomic-rollback'])
            run.save.assert_not_called()

    def test_native_entry_has_no_mode_or_trace_writer_hook(self):
        self.assertNotIn('evidence_mode',inspect.signature(temporal.execute_day).parameters)
        self.assertNotIn('checkpoint_writer',inspect.signature(temporal.execute_day).parameters)
        self.assertNotIn('checkpoint_writer',inspect.signature(services.finish_run).parameters)
        with self.assertRaises(TypeError):temporal.execute_day(evidence_mode='validation')
        with self.assertRaises(TypeError):services.finish_run(None,{},expected_digest='x',checkpoint_writer=lambda *a:None)

    def test_bpr_constructor_consumer_exhausts_live_stages_before_late_update(self):
        from mta.domain import bpr_construction as bpr
        events=[]
        state={'BPRDailyConsumption':[{'Stock':None}], 'LastBatchRunTbl':[{'LastRunDate':'2037-04-10'}]}
        working={'BPR_Table':[]}
        def stages(*a):
            for label in ('CollectDataForBPR.sql','PhysicalInventoryColour','GenerateBPR.sql'):
                events.append(label)
                working['BPR_Table'].append({'stage':label})
                yield label,working
        def late(source):
            events.append('late')
            self.assertEqual(source['BPR_Table'],[{'stage':n} for n in events[:-1]])
            self.assertIs(source['BPRDailyConsumption'],state['BPRDailyConsumption'])
            return deepcopy(source)
        with patch.object(bpr,'construct_stages',side_effect=stages),patch.object(bpr,'update_bpr',side_effect=late):
            constructed,result=bpr.constructor_then_late('2037-04-10',state,[])
        self.assertEqual(events,['CollectDataForBPR.sql','PhysicalInventoryColour','GenerateBPR.sql','late'])
        working['BPR_Table'].clear()
        self.assertEqual(len(result['BPR_Table']),3)
        self.assertIs(constructed,working)


if __name__=='__main__':unittest.main()
