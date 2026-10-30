"""Shared diagnostic contract with independently derived numeric expectations."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from uuid import uuid4

from mta.application import occurrence_text_policy as policy
from mta.domain.dbm_norm012 import data_stage, norm012_stages, AmbiguousReport
from mta.domain.dbm_selected_chain import selected_norm012_stages
from mta.domain.deferred_dbm_exports import render
from mta.serialization import digest, storage
from mta.temporal.chain import retain_dbm_stages, dbm_report_images
from tests.test_native_report_disposition import state, batch


def admitted(norm=0):
    run=SimpleNamespace(pk=uuid4(),business_date=date(2026,10,17),input_digest='a'*64,
        predecessor_id=None,execution_revision='occurrence-contract-test')
    return policy.binding(policy.owner_for(run,digest(batch()),'b'*40))


def source(norm=0, observations=None):
    value=state()
    value['DBMMaster'][0]['Norm']=norm
    if observations is not None:
        value['DailyConsumption']=[dict(SKUCode=value['DBMMaster'][0]['SKUCode'],
            WhCode=value['DBMMaster'][0]['WhCode'],ReportDate=day,Consumption=q)
            for day,q in observations]
    return value


class OccurrenceTextPolicyTests(unittest.TestCase):
    def test_all_three_norms_keep_complete_numeric_rows_null_details_and_visible_exports(self):
        for norm in (0,1,2):
            src=source(norm,[('2026-10-16',1),('2026-10-17',2),('2026-10-17',0),
                ('2026-10-17',-2),('2026-10-17',None)])
            src['SKUDescriptionTbl']*=2
            before=deepcopy(src);binding=admitted(norm)
            steps=dict(norm012_stages('2026-10-17',src,norm,30,occurrence_policy=binding))
            rows=steps['data']['Norm0Norm1Norm2Report']
            expected=dict(SKUCode=src['DBMMaster'][0]['SKUCode'],WHCode=src['DBMMaster'][0]['WhCode'],
                Count=4,TotalSale=2,Occurances=None,SKUName=src['SKUDescriptionTbl'][0]['SKUDescription'])
            self.assertEqual(rows,[expected,expected]) # two description joins; each aggregate sees both occurrences
            self.assertTrue(all(r['Occurances'] is None and r['NumOfDaysSold']==4 and r['TotalSale']==2
                for r in steps['detail']['Norm0_1_2ReportDetails']))
            self.assertEqual(len(steps['export']['ReportRows']),2)
            self.assertTrue(all(r['values'][8]=='"'+policy.DISPLAY+'"' for r in steps['export']['ReportRows']))
            policy.verify_export(steps['export'],binding,norm=norm)
            self.assertEqual(src,before)

    def test_empty_single_identical_duplicate_and_nonpositive_text_preserved(self):
        cases=[([],None),([('2026-10-17',1)],'[17/10/26 - 1]'),
            ([('2026-10-17',1)]*2,'[17/10/26 - 1], [17/10/26 - 1]'),
            ([('2026-10-17',0),('2026-10-17',-2)],'')]
        for norm in (0,1,2):
            for observations,text in cases:
                src=source(norm,observations)
                ordinary=data_stage('2026-10-17',src,norm,30)
                actual=data_stage('2026-10-17',src,norm,30,occurrence_policy=admitted(norm))
                self.assertEqual(actual,ordinary)
                if text is not None:self.assertEqual(actual['Norm0Norm1Norm2Report'][0]['Occurances'],text)

    def test_distinct_quantity_same_date_and_distinct_date_need_admission(self):
        for observations in ([('2026-10-17',1),('2026-10-17',2)],
                             [('2026-10-16',1),('2026-10-17',1)]):
            with self.assertRaises(AmbiguousReport):data_stage('2026-10-17',source(0,observations),0,30)
            actual=data_stage('2026-10-17',source(0,observations),0,30,occurrence_policy=admitted())
            self.assertIsNone(actual['Norm0Norm1Norm2Report'][0]['Occurances'])
            self.assertEqual(actual['Norm0Norm1Norm2Report'][0]['TotalSale'],sum(q for _,q in observations))

    def test_null_keys_dates_and_exclusive_horizon_are_unchanged(self):
        src=source(0,[('2026-09-17',99),('2026-09-18',2),(None,100)])
        src['DailyConsumption'] += [dict(src['DailyConsumption'][1],SKUCode=None,Consumption=100)]
        result=data_stage('2026-10-17',src,0,30,occurrence_policy=admitted())
        self.assertEqual(result['Norm0Norm1Norm2Report'][0]['Count'],1)
        self.assertEqual(result['Norm0Norm1Norm2Report'][0]['TotalSale'],2)
        self.assertEqual(result['Norm0Norm1Norm2Report'][0]['Occurances'],'[18/09/26 - 2]')

    def test_all_null_total_and_overflow_remain_denied(self):
        for norm in (0,1,2):
            for observations in ([('2026-10-17',None)], [('2026-10-17',2147483647),('2026-10-16',1)],
                                 [('2026-10-17',True)]):
                with self.assertRaises(ValueError):
                    data_stage('2026-10-17',source(norm,observations),norm,30,occurrence_policy=admitted(norm))

    def test_policy_does_not_extend_sixty_ninety_or_other_family_or_allow_tampering(self):
        for norm,horizon in ((0,60),(0,90),(1,60),(3,30)):
            with self.assertRaises(ValueError):
                data_stage('2026-10-17',source(),norm,horizon,occurrence_policy=admitted())
        for key in ('policy','owner','binding_digest'):
            bad=admitted();bad[key]={} if key!='binding_digest' else '0'*64
            with self.assertRaises((ValueError,KeyError,TypeError)):
                data_stage('2026-10-17',source(),0,30,occurrence_policy=bad)
        with self.assertRaises(ValueError):
            data_stage('2026-10-17',source(),0,30,exclude_all_occurrence_order=True,occurrence_policy=admitted())

    def test_deferred_and_eager_have_identical_cells_and_typed_nulls(self):
        config=batch((30,));config.update(ActivateNorm1Report30Days=1,ActivateNorm2Report30Days=1)
        for norm in (0,1,2):
            src=source(norm);binding=admitted()
            def reports(deferred):
                stages=retain_dbm_stages(selected_norm012_stages('2026-10-17',src,config,
                    {policy.KEY:binding},_defer_exports=deferred),[])
                return dbm_report_images([(name,value) for name,value in stages if name.endswith('-export')])
            eager=reports(False);deferred=reports(True)
            for row in deferred:
                if 'deferred' in row:
                    row['tables'].update(render('2026-10-17',row.pop('deferred'),row.pop('sources')))
            self.assertEqual(storage(deferred),storage(eager))
            summaries=policy.summaries(eager,binding)
            self.assertEqual(summaries[f'norm{norm}-export']['affected_groups'],1)
            self.assertEqual(sum(r['affected_groups'] for r in summaries.values()),1)

    def test_capture_context_and_phase_cannot_drop_or_change_policy(self):
        from mta.runtime.occurrence_text_policy import context,verify_phase,verify_output
        binding=admitted();owner=binding['owner']
        run=SimpleNamespace(pk=owner['run_id'],business_date=date.fromisoformat(owner['business_date']),
            input_digest=owner['input_digest'],predecessor_id=None,execution_revision=owner['execution_revision'],
            production_manifest={policy.KEY:binding})
        self.assertEqual(context(run),{policy.KEY:binding})
        phase=SimpleNamespace(context=SimpleNamespace(report_exceptions={}))
        with self.assertRaises(ValueError):verify_phase(run,phase)
        with self.assertRaises(ValueError):verify_output(run,[{}],owner['configuration_digest'],binding)
        phase.context.report_exceptions=context(run);verify_phase(run,phase)
        wrong=deepcopy(run);wrong.input_digest='0'*64
        with self.assertRaises(ValueError):context(wrong)

    def test_commit_requires_exact_affected_metadata_and_no_orphan_summary(self):
        from mta.runtime.occurrence_text_policy import verify_output
        binding=admitted();owner=binding['owner']
        run=SimpleNamespace(pk=owner['run_id'],business_date=date.fromisoformat(owner['business_date']),
            input_digest=owner['input_digest'],predecessor_id=None,execution_revision=owner['execution_revision'])
        for metadata in ({},{'norm0-export':{}}):
            with self.assertRaises(ValueError):
                verify_output(run,[{policy.KEY:binding,'occurrence_text_availability':metadata}],
                    owner['configuration_digest'],binding,[dict(stage='norm0-export',tables={'Norm0Norm1Norm2Report':[]})])
        verify_output(run,[{policy.KEY:binding,'occurrence_text_availability':{}}],
            owner['configuration_digest'],binding,[])
        with self.assertRaises(ValueError):verify_output(run,[{'occurrence_text_availability':{}}],owner['configuration_digest'],None,[])

    def test_legacy_native_capture_keeps_strict_path_and_new_capture_uses_admission(self):
        from unittest.mock import patch
        from mta.runtime import temporal
        class CalculationReached(RuntimeError):pass
        run=SimpleNamespace(pk=uuid4(),input_digest='a'*64,production_manifest={})
        raw=dict(profile=batch(),day={'business_date':'2026-10-17'})
        for expected in ({}, {policy.KEY:admitted()}):
            run.production_manifest=dict(expected)
            with patch.object(temporal,'calculate_day',side_effect=CalculationReached) as calculate, \
                    patch.object(temporal,'fail_run'), \
                    patch('mta.runtime.occurrence_text_policy.context',return_value=expected) as context:
                with self.assertRaises(CalculationReached):
                    temporal._calculate_and_finish_captured_day(run,raw,None,'2026-10-16',{},None,
                        False,None,{},None,True)
                self.assertEqual(calculate.call_args.args[6],expected)
                self.assertEqual(context.call_count,int(bool(expected)))


if __name__=='__main__':unittest.main()
