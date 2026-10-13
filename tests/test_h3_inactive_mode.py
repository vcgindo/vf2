"""Complementary inactive-native input/finalization checks; no persisted day."""
from copy import deepcopy
import unittest
from tests.test_h3_daily_integration import frame, calculate_day, calculate_current_day, evidence_mode
from tests.production_h3_fixture import supplied_input, supplied_day
from tests.initialization_input_fixture import encoded
from tests.test_production_daily_contract import encoded_day
from mta.mdm.initialization_contract import decode as decode_initial
from mta.runtime.production_daily import decode, working_day, FEED_SCHEMA, input_table
from mta.application.daily_finalization import POLICY, ACTIVE_POLICY, verify_successor
from mta.mdm.daily_input import nms_master_raw
from mta.serialization import storage


def inactive_input():
    value=supplied_input()
    value['configuration']['complete_daily']['policy']=POLICY
    value['configuration']['force_flags']['nms_active']=False
    for bag in (value['opening']['state']['importer_settings'],value['opening']['state']['controls']['importer_settings']):
        for row in bag:
            if row['Parameter']=='NMSActive':row['Value']='0'
    value['opening']['identity']='SUPPLIED-H3-INACTIVE-NATIVE'
    value['recipe']['version']='supplied-h3-inactive-native-v1'
    return value


def inactive_frame():
    raw,sha,args=encoded(inactive_input())
    return decode_initial(raw,sha,**args)[1]


def inactive_day(today,*,root=False):
    value=supplied_day(today,root=root)
    value['schema']=FEED_SCHEMA
    # These are the same declared external master facts on each date. Only the
    # test fixture projects its initial masters into the existing raw wire shape;
    # never derive a future external input from a calculated predecessor.
    initial=inactive_frame()['opening']['state']
    value['day']['raw_master']=storage(nms_master_raw(initial))
    value['day']['supplier_feeds']={name:deepcopy(initial['complete'][name])
        for name in ('SOBDataRaw','MOQDataRaw1','MOQDataRaw2')}
    # Deliberate external facts differ from the initial master/supplier owners.
    # Their exact closing/current values prove that v2 feeds were actually used.
    for row in value['day']['raw_master']:
        if (row['SKUCode'],row['WhCode'])==('SUPPLIED-Z9','OWN-PARENT'):row['MinNorm']=4
    value['day']['supplier_feeds']['SOBDataRaw'][0]['SOB']=90.0
    return value


class InactiveNativeContract(unittest.TestCase):
    def test_preflight_binds_mode_policy_and_explicit_feeds(self):
        from mta.runtime.production_preflight import Requirements,state_requirements,daily
        import tempfile
        f=inactive_frame()
        c=Requirements('day');state_requirements(c,f['opening']['state'],f['profile'],'/opening/state',initial=True)
        self.assertEqual(c.issues,[])
        bad=deepcopy(f['profile']);bad['complete_daily']['policy']=ACTIVE_POLICY
        c=Requirements('day');state_requirements(c,f['opening']['state'],bad,'/opening/state',initial=True)
        self.assertTrue(any('/NMSActive' in q['path'] for q in c.issues))
        with tempfile.TemporaryDirectory() as output:
            raw,sha=encoded_day(inactive_day('2037-04-10',root=True))
            from mta.serialization import digest
            report=daily(raw,sha,frame=f,initialization_id='00000000-0000-4000-8000-000000000001',
                source_digest='a'*64,configuration_digest=digest(f['profile']),
                pick_output_root=output,execution_revision='inactive-component')
            self.assertFalse([q for q in report['issues'] if 'day' in q['stages']],report)

    def test_current_publication_denies_capture_policy_mismatch_before_writes(self):
        from types import SimpleNamespace
        from unittest.mock import patch,MagicMock
        from mta.mdm.daily_current import publish
        run=SimpleNamespace(pk='run',kind='DAILY_CHAIN',status='RUNNING')
        for active,policy in ((True,POLICY),(False,ACTIVE_POLICY),(False,'unknown')):
            capture=SimpleNamespace(run_id='run',source_id=1,status='CONSUMED',nms_active=active)
            conn=MagicMock(in_atomic_block=True)
            with patch('mta.mdm.daily_current.connection',conn), \
                    patch('mta.runtime.mdm_models.MdmSource.objects') as sources, \
                    patch('mta.mdm.native_source.require_native'), \
                    patch('mta.mdm.production_families.require_binding'), \
                    patch('mta.runtime.validation_storage.read_input',return_value={'profile':{'complete_daily':{'policy':policy}}}):
                with self.assertRaisesRegex(ValueError,'mode-bound'):publish(run,capture,{})
                conn.cursor.assert_not_called()

    def test_explicit_external_feeds_and_typed_paths(self):
        value=inactive_day('2037-04-10',root=True);raw,sha=encoded_day(value)
        opening=inactive_frame()['opening']['state']
        self.assertNotEqual(next(r['MinNorm'] for r in opening['importer']['MasterData']
            if (r['SKUCode'],r['WhCode'])==('SUPPLIED-Z9','OWN-PARENT')),4)
        self.assertEqual(opening['complete']['SOBDataRaw'][0]['SOB'],100.0)
        actual=working_day(decode(raw,sha),inactive_frame()['profile'])
        self.assertEqual(actual['raw_master'],value['day']['raw_master'])
        for name,rows in actual['supplier_feeds'].items():
            key=input_table(list(rows[0]) if rows else [],'input/day/supplier_feeds/'+name+'/values',rows)
            self.assertTrue(key.endswith('Temp'+name))
        with self.assertRaisesRegex(ValueError,'captured owners'):
            working_day(value,{'complete_daily':{'policy':ACTIVE_POLICY}})
        empty=deepcopy(value);empty['day']['raw_master']=[]
        empty['day']['supplier_feeds']={name:[] for name in empty['day']['supplier_feeds']}
        with self.assertRaisesRegex(ValueError,'requires v1'):
            working_day(empty,{'complete_daily':{'policy':ACTIVE_POLICY}})
        with self.assertRaisesRegex(ValueError,'explicit v2'):
            working_day(supplied_day('2037-04-10',root=True),inactive_frame()['profile'])
        del value['day']['supplier_feeds']['MOQDataRaw1']
        with self.assertRaisesRegex(ValueError,'raw feed roster'):decode(*encoded_day(value))

    def test_coupled_inactive_days_keep_skipped_flags_and_own_calculated_state(self):
        f=inactive_frame();prior=f['opening']['state'];opening='2037-04-09'
        for today in ('2037-04-10','2037-04-11'):
            day=working_day(decode(*encoded_day(inactive_day(today,root=today.endswith('10')))),f['profile'])
            with evidence_mode('production'):
                result=calculate_day(deepcopy(prior),opening,day,f['profile'],'component-inactive-'+today,
                    lambda source,**owned:(calculate_current_day(source,defer_pick=True,**owned),'component-inactive-'+today),
                    native_daily=True)
            result['Lineage']=[dict(cohort1=result.pop('_Cohort1'))]
            verify_successor(result,f['profile'],today)
            prior=result['ClosingState'][0]
            values={r['Parameter']:r['Value'] for r in prior['importer_settings']}
            self.assertEqual((values['NMSActive'],values['IsBatchFileExecuted'],values['IsBPRBatchFileExecuted']),('0','0','1'))
            skipped={r['ScriptName'] for r in prior['complete']['ScriptExecutedFlag']
                     if r['IsScriptCritical']==1 and r['IsScriptExecuted']==0}
            self.assertEqual(skipped,{'NMSImportData.sql','NMSClearInputTables.sql'})
            self.assertTrue(prior['importer']['MasterData'])
            self.assertEqual(next(r['MinNorm'] for r in prior['importer']['MasterData']
                if (r['SKUCode'],r['WhCode'])==('SUPPLIED-Z9','OWN-PARENT')),4)
            self.assertEqual(prior['complete']['SOBDataRaw'][0]['SOB'],90.0)
            opening=today
