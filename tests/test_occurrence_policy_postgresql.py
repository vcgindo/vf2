"""Owned rollback-only integrated policy, typed reader and Full/split proofs.

Supplied component identities/configuration are explicit rule-boundary fixtures,
not a native registration or legacy parity claim. Native capture is separately
qualified through the normal small CSV lifecycle before the production retry.
"""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from tests.test_prepared_effects_postgresql import PreparedEffectsPostgresTests
from tests.test_scoped_common_final_postgresql import ScopedCommonFinalTests

DB='vftest_fresh_occurrence_policy_20261030'
COMMENT='owned occurrence policy component proof 20261030; synthetic only'
NORMS={'OWN-DIST':0,'OWN-VENDOR':1,'OWN-DMS':2}


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class OccurrencePolicyPostgresTests(unittest.TestCase):
    for _name in ('rollback','accept'):
        locals()[_name]=getattr(PreparedEffectsPostgresTests,_name)
    for _name in ('prepare_dbm','finish','publication_opening','compare_full_scope'):
        locals()[_name]=getattr(ScopedCommonFinalTests,_name)
    from tests.test_scoped_actions_postgresql import ScopedActionTests as _Actions
    for _name in ('pause_bpr','state','action','resume_dbm'):
        locals()[_name]=getattr(_Actions,_name)

    def setUp(self):
        from django.db import connection,transaction
        self.assertEqual(connection.settings_dict['NAME'],DB)
        with connection.cursor() as cursor:
            cursor.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(cursor.fetchone()[0],COMMENT)
        self.atomic=transaction.atomic();self.atomic.__enter__();self.addCleanup(self.rollback)
        from mta.runtime import phase_state
        encode=phase_state.encode
        def strict_component(phase,*args,**kwargs):
            # This supplied source has no certified native initialization.
            # Retain every strict source audit instead of claiming the private
            # certified-input shortcut solely because the phase is native-shaped.
            phase.context.accepted_inputs=None
            return encode(phase,*args,**kwargs)
        self.enterContext(patch.object(phase_state,'encode',side_effect=strict_component))

    def owner(self,**kwargs):
        from tests import test_h3_daily_integration as supplied
        from tests import production_h3_fixture as fixture
        from mta.temporal import chain
        from mta.runtime.models import CalculationRun
        from mta.runtime.occurrence_text_policy import admit,context,KEY
        from mta.serialization import digest
        old_frame,old_day,old_prepare=supplied.frame,fixture.supplied_day,chain.prepare_day
        def frame():
            result=old_frame();prior=result['opening']['state']
            for rows in (prior['dbm']['DBMMaster'],prior['controls']['dbm_master'],prior['importer']['MasterData']):
                for row in rows:
                    if row['SKUCode']=='SUPPLIED-Z9' and row['WhCode'] in NORMS:
                        row.update(Norm=NORMS[row['WhCode']],MinNorm=0)
            result['profile']['delivery']['batch']['AutoDBMActive']=0
            return result
        def day(today):
            result=old_day(today)
            for row in result['day']['raw_daily']:
                if row['SKUCode']=='SUPPLIED-Z9' and row['WhCode'] in NORMS:row['Consumption']=1
            return result
        def prepare(prior,opening_date,day,profile,identity,calculate,*args,**options):
            run=CalculationRun.objects.get(pk=identity)
            run.production_manifest={KEY:admit(run,digest(profile))}
            run.save(update_fields=['production_manifest'])
            return old_prepare(prior,opening_date,day,profile,identity,calculate,context(run),**options)
        with patch.object(supplied,'frame',side_effect=frame),patch.object(fixture,'supplied_day',side_effect=day), \
                patch.object(chain,'prepare_day',side_effect=prepare):
            PreparedEffectsPostgresTests.owner(self,**kwargs)

    def ordinary_full(self):
        from mta.temporal.chain import produce_bpr,produce_dbm,produce_btr
        from mta.application.native_output_contracts import native_assignments
        from mta.runtime.input_reader import read_input
        from mta.runtime.services import finish_run
        from mta.application.occurrence_text_policy import KEY,summaries
        with native_assignments(True):output=produce_btr(produce_dbm(produce_bpr(deepcopy(self.prepared))))
        output.pop('_CompletedBoundaries')
        lineage=read_input(self.run,components=('lineage',))['lineage']
        lineage['cohort1']=output.pop('_Cohort1')
        lineage[KEY]=self.prepared.context.report_exceptions[KEY]
        lineage['occurrence_text_availability']=summaries(output['Reports'],lineage[KEY])
        sources=output.pop('_PickSourceDigests',None)
        if sources is not None:lineage['pick_source_digests']=sources
        output['Lineage']=[lineage]
        return finish_run(self.run,output,expected_digest=self.run.input_digest,
            publication_opening=self.publication_opening())

    def assert_reports(self,run,days):
        from mta.runtime.relational_state import read_daily
        from mta.runtime.receipt_integrity import verify
        from mta.application import occurrence_text_policy as policy
        from mta.domain.deferred_dbm_exports import render
        # Component publication has not run the separate derived-generation
        # preparation. Verify the complete operational receipt, then read its
        # actual typed reports and exercise the unchanged deferred formatter.
        verify(run)
        output=read_daily(run)
        lineage=output['Lineage'][0];binding=lineage[policy.KEY]
        policy.verify_owner(binding,run,binding['owner']['configuration_digest'])
        self.assertEqual(binding['owner']['predecessor_id'],str(run.predecessor_id) if run.predecessor_id else None)
        for stage,norm in policy.STAGES.items():
            report=next(row for row in output['Reports'] if row['stage']==stage)
            tables=report['tables']
            if 'deferred' in report:tables.update(render(run.business_date,report['deferred'],report['sources']))
            rows=[r for r in tables['Norm0Norm1Norm2Report'] if r['SKUCode']=='SUPPLIED-Z9' and NORMS.get(r['WHCode'])==norm]
            self.assertEqual(len(rows),1,(stage,rows))
            self.assertEqual((rows[0]['Count'],rows[0]['TotalSale']),(days,days))
            if days==1:self.assertIsInstance(rows[0]['Occurances'],str)
            else:self.assertIsNone(rows[0]['Occurances'])
            policy.verify_export(tables,binding,norm=norm)
            self.assertEqual(lineage['occurrence_text_availability'][stage]['affected_groups'],int(days>1))
        return output

    def test_first_and_own_successor_full_equal_both_split_paths(self):
        from mta.runtime.models import CalculationRun,RunPhaseAcceptance
        from mta.serialization import storage
        parent=self.compare_full_scope('PostBPR')
        before=storage(CalculationRun.objects.filter(pk=parent.pk).values().get())
        self.assert_reports(parent,1)
        successor=self.compare_full_scope('PostDBM',predecessor=parent)
        self.assert_reports(successor,2)
        self.assertEqual(storage(CalculationRun.objects.filter(pk=parent.pk).values().get()),before)
        self.assertEqual(successor.predecessor_id,parent.pk)
        self.assertEqual(RunPhaseAcceptance.objects.filter(run=successor,state_sealed=True).count(),4)

    def test_positive_apply_sleep_keep_policy_phase_and_action_ownership(self):
        from django.db import transaction
        from mta.runtime.scoped_actions import restore
        from mta.application.occurrence_text_policy import KEY
        for operation in ('APPLY','SLEEP'):
            with self.subTest(operation=operation),transaction.atomic():
                self.pause_bpr()
                original=self.bpr.snapshot.state_digest
                binding=self.prepared.context.report_exceptions[KEY]
                event=self.action(operation)
                receipt=self.resume_dbm()
                phase,_=restore(self.run,receipt)
                self.assertEqual(phase.context.action_revision,event.pk)
                self.assertEqual(phase.context.report_exceptions[KEY],binding)
                self.bpr.snapshot.refresh_from_db()
                self.assertEqual(self.bpr.snapshot.state_digest,original)
                result=self.finish()
                self.assert_reports(result,1)
                self.assertEqual(result.production_manifest['lineage'][0]['scope_actions'][0]['id'],event.pk)
                transaction.set_rollback(True)

    def test_actual_persisted_reader_all_report_contract_cases_and_threshold(self):
        from django.db import transaction
        from mta.runtime.models import CalculationRun
        from mta.runtime.relational_state import save_image,load_image
        from mta.row_sequences import RecordRows
        from tests import test_occurrence_text_policy as cases
        from mta.serialization import storage
        import uuid
        run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2026-10-17',
            execution_revision='occurrence-reader-'+uuid.uuid4().hex,input_digest='a'*64,input_payload={})
        original=cases.source
        calculate=cases.data_stage
        def persisted(today,state,*args,**kwargs):
            value=dict(state)
            for table in ('DBMMaster','DailyConsumption'):
                image=save_image(run,'policy-proof/'+uuid.uuid4().hex+'/'+table,'closing/dbm/'+table,value[table])
                actual=load_image(run,image)
                self.assertEqual(storage(actual),storage(value[table]))
                value[table]=actual
            result=calculate(today,value,*args,**kwargs)
            self.assertEqual(storage(load_image(run,image)),storage(state['DailyConsumption']))
            return storage(result)
        methods=[name for name in dir(cases.OccurrenceTextPolicyTests) if name.startswith('test_')
            and name not in ('test_deferred_and_eager_have_identical_cells_and_typed_nulls',
                             'test_all_null_total_and_overflow_remain_denied')]
        with patch.object(cases,'data_stage',side_effect=persisted):
            for name in methods:
                case=cases.OccurrenceTextPolicyTests(name)
                getattr(case,name)()
        for norm in (0,1,2):
            for observations in ([('2026-10-17',None)],[('2026-10-17',2147483647),('2026-10-16',1)]):
                with self.assertRaises(ValueError):
                    persisted('2026-10-17',original(norm,observations),norm,30,occurrence_policy=cases.admitted(norm))
            from decimal import InvalidOperation
            with self.assertRaises(InvalidOperation):
                persisted('2026-10-17',original(norm,[('2026-10-17',True)]),norm,30,occurrence_policy=cases.admitted(norm))
        rows=original(0,[('2026-10-16',1)]*10000+[('2026-10-17',1)])['DailyConsumption']
        image=save_image(run,'policy-proof/threshold','closing/dbm/DailyConsumption',rows)
        actual=load_image(run,image)
        self.assertIsInstance(actual,RecordRows)
        value=original(0,[]);value['DailyConsumption']=actual
        from mta.domain.dbm_norm012 import data_stage
        result=data_stage('2026-10-17',value,0,30,occurrence_policy=cases.admitted())
        row=result['Norm0Norm1Norm2Report'][0]
        self.assertEqual((row['Count'],row['TotalSale'],row['Occurances']),(10001,10001,None))
        self.assertEqual(storage(load_image(run,image)),rows)
