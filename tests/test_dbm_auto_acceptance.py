"""Automatic queue timing and own next-date control/suspension ownership."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tests.test_dbm_conditional import (
    TODAY, state, master, observation, delivery)
from tests import test_dbm_conditional as conditional_tests
from mta.domain.dbm_auto_acceptance import automatic_acceptance
from mta.domain.control_carry import TABLES, control_stages
from mta.domain.dbm_suspensions import apply_accepted_norm_stock, apply_accepted_norm_consumption
from mta.temporal.chain import carry_dbm_controls, connected_dbm_stages, native_rows
from mta.runtime import relational_state as typed
from mta.serialization import storage

TOMORROW = '2037-04-11'
RUN = SimpleNamespace(pk='94de4a53-e2d6-4bc7-81ae-47c12a1437cf')
FLAGS = dict(from_ui=True, ignore_master_norm=False, nms_active=False)


def suggestion(kind=1, sku='S', norm=6, wh='W'):
    return dict(SKUCode=sku, WhCode=wh, Type=kind, NewNorm=norm)


def reconstructed(value, names):
    result = deepcopy(value)
    for name in names:
        path = 'closing/dbm/'+name
        records = []
        with patch.object(typed, 'bulk', side_effect=lambda query, rows: records.extend(rows)):
            meta = typed.save_image(RUN, path, None, storage(value[name]), table='DBM/'+name)
        cursor = MagicMock()
        cursor.fetchmany.side_effect = [[tuple(row[2:]) for row in records], []]
        with patch.object(typed.connection, 'cursor') as context:
            context.return_value.__enter__.return_value = cursor
            result[name] = typed.load_image(RUN, meta)
        if result[name] != storage(value[name]):
            raise AssertionError('Typed reconstruction differs: '+name)
        if cursor.execute.call_args.args[1] != [RUN.pk, path]:
            raise AssertionError('Readback owner differs')
    return result


def controls(closing):
    value = {name: [] for name in TABLES}
    value.update(last_batch=[dict(LastRunDate=TODAY+'T00:00:00')], IntermediateTables={},
        importer_master=[dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], Norm=r['Norm'], MinNorm=r['MinNorm'])
                         for r in closing['DBMMaster']])
    # Deliberately stale controls must lose to this run's DBM owner.
    value['acceptance'] = [dict(SKUCode='STALE', WhCode='W', OldNorm=1, NewNorm=99, AcceptanceDate=TODAY)]
    return carry_dbm_controls(value, closing)


def next_controls(closing, accepted=()):
    return list(control_stages(TOMORROW, TODAY, controls(closing), FLAGS, list(accepted), []))


def suspension_input(closing, control):
    value = deepcopy(closing)
    value.update(DBMMaster=deepcopy(control['dbm_master']), NormAcceptanceTbl=deepcopy(control['acceptance']),
        NormChangeLogTbl=native_rows(control['log'], ('SKUCode','WHCode','OldNorm','NewNorm','NormChangeDate','NormChangeReason')),
        LastBatchRunTbl=[dict(LastRunDate=TOMORROW+'T00:00:00')],
        DailyConsumption=[observation(sku=r['SKUCode'], day=TOMORROW, stock=0, consumption=0) for r in closing['DBMMaster']])
    return value


class AutomaticQueueTests(unittest.TestCase):
    def test_exact_type_exclusions_null_predicate_and_queue_replacement(self):
        value = state()
        value['Suggestions'] = [suggestion(kind) for kind in (*range(14), None)]
        value['NormAcceptanceTbl'] = [dict(stale=True)]
        before = deepcopy(value)
        result = automatic_acceptance(TODAY, value)
        self.assertEqual(result['NormAcceptanceTbl'], [dict(SKUCode='S',WhCode='W',AcceptanceDate=TODAY,OldNorm=0,NewNorm=6)]*8)
        self.assertEqual({k:v for k,v in result.items() if k!='NormAcceptanceTbl'},
                         {k:v for k,v in before.items() if k!='NormAcceptanceTbl'})
        self.assertEqual(value, before)

    def test_join_multiplicity_order_spelling_and_null_nonmatches(self):
        value = state(); value['DBMMaster'] = [master(norm=2), master('s ',3), master('X',4), master(sku=None)]
        value['Suggestions'] = [suggestion(sku='s '),suggestion(sku='X',norm=4),suggestion(sku='S',norm=2),
                                suggestion(sku=None),suggestion(wh=None),suggestion(sku='absent')]
        rows = automatic_acceptance(TODAY,value)['NormAcceptanceTbl']
        self.assertEqual([(r['SKUCode'],r['OldNorm'],r['NewNorm']) for r in rows],
                         [('s ',2,6),('s ',3,6),('X',4,4),('S',2,2),('S',3,2)])

    def test_target_constraint_failure_denies_entire_queue_without_mutating_opening(self):
        for field,bad in (('NewNorm',None),('OldNorm',None),('NewNorm',2**31),
                          ('OldNorm',True),('SKUCode','x'*51),('WhCode','x'*51)):
            value=state();value['DBMMaster'].append(master('BAD',2))
            value['Suggestions']=[suggestion(),suggestion(sku='BAD')]
            if field=='OldNorm':value['DBMMaster'][1]['Norm']=bad
            else:
                value['Suggestions'][1][field]=bad
                if field in ('SKUCode','WhCode'):value['DBMMaster'][1][field]=bad
            value['NormAcceptanceTbl']=[dict(SKUCode='PRIOR',WhCode='W',OldNorm=1,NewNorm=2,AcceptanceDate=TODAY)]
            before=deepcopy(value)
            with self.assertRaises(ValueError):automatic_acceptance(TODAY,value)
            self.assertEqual(value,before)

    def test_empty_computed_queue_clears_stale_operator_acceptance(self):
        value = state();value['Suggestions']=[suggestion(7)]
        value['NormAcceptanceTbl']=[dict(SKUCode='S',WhCode='W',OldNorm=0,NewNorm=8,AcceptanceDate=TODAY)]
        self.assertEqual(automatic_acceptance(TODAY,value)['NormAcceptanceTbl'],[])

    def test_date_guard_no_implicit_top_one_or_midnight_conversion(self):
        value=state()
        self.assertEqual(automatic_acceptance(date.fromisoformat(TODAY),value),automatic_acceptance(TODAY,value))
        for rows in ([],value['LastBatchRunTbl']*2,[dict(LastRunDate=TODAY+'T01:00:00')]):
            value['LastBatchRunTbl']=rows
            with self.assertRaises(ValueError):automatic_acceptance(TODAY,value)


class AutomaticCarryTests(unittest.TestCase):
    def setup_flow(self):
        value,facts=conditional_tests.ConnectedConditionalTests().setup_flow()
        for row in value['DailyConsumption']:
            if row['SKUCode']=='TWO':row['Stock']=2
        facts['daily_raw']=[observation(sku='TWO',stock=0,consumption=0)]
        config=delivery();config['batch']['AutoDBMActive']=1
        value['ReasonCodes']=[dict(Id=1,Reason='Increase'),dict(Id=7,Reason='Order')]
        return value,facts,config

    def test_actual_daily_dispatch_same_day_norms_history_and_queue(self):
        value,facts,config=self.setup_flow();before=deepcopy(value)
        stages=list(connected_dbm_stages(TODAY,value,facts,config));names=[n for n,_ in stages]
        self.assertEqual(names[names.index('norm1-advisory'):names.index('norm-change-export')+1],
                         ['norm1-advisory','auto-acceptance','norm-change-export'])
        auto=dict(stages)['auto-acceptance'];final=stages[-1][1]
        expected=[dict(SKUCode='TWO',WhCode='W',OldNorm=2,NewNorm=3,AcceptanceDate=TODAY)]
        self.assertEqual(auto['NormAcceptanceTbl'],expected)
        self.assertEqual(final['NormAcceptanceTbl'],expected)
        self.assertEqual(final['DBMMaster'],before['DBMMaster'])
        self.assertEqual(final['NormChangeLogTbl'],[])
        self.assertEqual([(r['SKUCode'],r['Type']) for r in final['Suggestions']], [('TWO',1),('ZERO',7),('ONE',10)])
        self.assertEqual(value,before)

    def test_own_typed_closing_next_controls_logs_trigger_importer_and_stock_queue(self):
        value,facts,config=self.setup_flow()
        closing=list(connected_dbm_stages(TODAY,value,facts,config))[-1][1]
        own=reconstructed(closing,('NormAcceptanceTbl','DBMMaster','Suggestions','SuggestionsLog','NormChangeLogTbl','SuspendHistory'))
        stages=next_controls(own);current=stages[-1][1]
        self.assertEqual([(r['SKUCode'],r['Norm']) for r in current['dbm_master']], [('ZERO',0),('ONE',1),('TWO',3)])
        self.assertEqual([r['Norm'] for r in current['importer_master']],[0,1,3])
        log=dict(SKUCode='TWO',WhCode='W',OldNorm=2,NewNorm=3,NormChangeDate=TOMORROW,NormChangeReason=1)
        self.assertEqual(current['log'],[log]);self.assertEqual(current['triggers'],[])
        self.assertEqual(stages[2][1]['triggers'],[dict(SKUCode='TWO',WhCode='W',NewNorm=3,Reason=1)])
        self.assertEqual(current['acceptance'],own['NormAcceptanceTbl']);self.assertEqual(current['accepted'],[])
        next_state=suspension_input(own,current)
        stock=apply_accepted_norm_stock(TOMORROW,next_state)
        self.assertEqual(stock['NormAcceptanceTbl'],[])
        self.assertEqual(stock['SuspendAcceptedNormsStockType'],[dict(SKUCode='TWO',WhCode='W',DeltaNorm=1,
            WaitStartDate=TOMORROW,WaitTillDate='2037-04-14',WaitForReceipts=False,HasStockComeOutOfRed=False,
            IsRedEnabled=False,IsGreenEnabled=False)])
        rebuilt=reconstructed(stock,('NormAcceptanceTbl','DBMMaster','NormChangeLogTbl','SuspendAcceptedNormsStockType'))
        self.assertEqual(rebuilt['DBMMaster'][2]['Norm'],3)
        # Actual next-date DBM dispatcher consumes the same queue before rules.
        next_state['DailyConsumption']=own['DailyConsumption']
        successor=dict(connected_dbm_stages(TOMORROW,next_state,{**facts,'daily_raw':[observation(sku='TWO',day=TOMORROW,stock=0,consumption=0)],'order_raw':[]},config))
        self.assertEqual(successor['suspension7']['NormAcceptanceTbl'],[])
        self.assertEqual(successor['suspension7']['SuspendAcceptedNormsStockType'],stock['SuspendAcceptedNormsStockType'])

    def test_stock_cooling_uses_own_wait_start_and_receipt_delta(self):
        value=state();value['DBMMaster'][0]['Norm']=2;value['Suggestions']=[suggestion(norm=6)]
        value['ReasonCodes']=[dict(Id=1,Reason='Increase')]
        closing=automatic_acceptance(TODAY,value)
        stock=apply_accepted_norm_stock(TOMORROW,suspension_input(closing,next_controls(closing)[-1][1]))
        stock['LastBatchRunTbl']=[dict(LastRunDate='2037-04-14T00:00:00')]
        stock['DailyConsumption']=[observation(day='2037-04-14',stock=4)]
        stock['DailyConsumption'][0]['Receipts']=4
        released=apply_accepted_norm_stock('2037-04-14',stock)['SuspendAcceptedNormsStockType'][0]
        self.assertTrue(released['WaitForReceipts']);self.assertTrue(released['HasStockComeOutOfRed'])
        self.assertTrue(released['IsRedEnabled']);self.assertTrue(released['IsGreenEnabled'])
        stock['DailyConsumption'][0]['Receipts']=3
        self.assertFalse(apply_accepted_norm_stock('2037-04-14',stock)['SuspendAcceptedNormsStockType'][0]['IsRedEnabled'])

    def test_type6_next_date_history_consumption_resume_and_downward_stock(self):
        value=state();value['DBMMaster'][0]['Norm']=9;value['Suggestions']=[suggestion(6,norm=6)]
        value['ReasonCodes']=[dict(Id=6,Reason='Decrease')]
        closing=automatic_acceptance(TODAY,value);control=next_controls(closing)[-1][1]
        current=suspension_input(closing,control)
        current['SuspendConsumptionType']=[dict(SKUCode='S',WhCode='W',RedEnabled=True,GreenEnabled=True,
                                               RedResumeDate='2001-01-01',GreenResumeDate='2001-01-01')]
        stock=apply_accepted_norm_stock(TOMORROW,current)
        self.assertIsNone(stock['SuspendAcceptedNormsStockType'][0]['DeltaNorm'])
        self.assertIsNone(stock['SuspendAcceptedNormsStockType'][0]['WaitTillDate'])
        consumed=apply_accepted_norm_consumption(TOMORROW,stock)
        self.assertEqual(consumed['SuspendAcceptedNormsConsumptionType'],[dict(SKUCode='S',WhCode='W',IsRedEnabled=False,IsGreenEnabled=True)])
        self.assertEqual(consumed['SuspendConsumptionType'][0]['RedResumeDate'],TOMORROW)
        self.assertEqual(consumed['SuspendConsumptionType'][0]['GreenResumeDate'],TOMORROW)
        reconstructed(consumed,('NormAcceptanceTbl','NormChangeLogTbl','SuspendConsumptionType','SuspendAcceptedNormsConsumptionType'))

    def test_auto_plus_operator_approval_rejects_both_duplicate_pair_rows(self):
        value=state();value['Suggestions']=[suggestion()];value['ReasonCodes']=[dict(Id=1,Reason='Increase')]
        closing=automatic_acceptance(TODAY,value)
        current=next_controls(closing,[dict(SKUCode='S',WhCode='W')])[-1][1]
        self.assertEqual(current['acceptance'],[]);self.assertEqual(current['log'],[])
        self.assertEqual(current['dbm_master'][0]['Norm'],0)

    def test_actual_delivery_control_dispatch_and_typed_trigger_checkpoint(self):
        from mta.application.timeline_controls import timeline_control_stages, EXTRA_TABLES, REQUEST_TABLES
        value,facts,config=self.setup_flow()
        closing=list(connected_dbm_stages(TODAY,value,facts,config))[-1][1]
        own=reconstructed(closing,('NormAcceptanceTbl','Suggestions','DBMMaster'))
        day=dict(control_requests={name:[] for name in REQUEST_TABLES},accepted_feed=[],new_force_requests=[])
        profile=dict(from_ui=True,start_percent=50,history_horizon=370,force_flags=FLAGS)
        stages=list(timeline_control_stages(TOMORROW,TODAY,controls(own),
            {name:[] for name in EXTRA_TABLES},day,profile,[],[]))
        final=stages[-1][1]
        self.assertEqual(final['dbm_master'][2]['Norm'],3)
        self.assertEqual(final['importer_master'][2]['Norm'],3)
        self.assertEqual(final['acceptance'],closing['NormAcceptanceTbl'])
        trigger=next(s['triggers'] for _,s,_ in stages if s['triggers'])
        records=[];path='closing/controls/triggers'
        with patch.object(typed,'bulk',side_effect=lambda query,rows:records.extend(rows)):
            meta=typed.save_image(RUN,path,None,storage(trigger),table='DBM/NormChangeTriggerTbl')
        cursor=MagicMock();cursor.fetchmany.side_effect=[[tuple(r[2:]) for r in records],[]]
        with patch.object(typed.connection,'cursor') as context:
            context.return_value.__enter__.return_value=cursor
            loaded=typed.load_image(RUN,meta)
        self.assertEqual(loaded,trigger)
        self.assertEqual(cursor.execute.call_args.args[1],[RUN.pk,path])

    def test_missing_reason_changes_dbm_without_invented_log_or_importer_trigger(self):
        value=state();value['Suggestions']=[suggestion()]
        current=next_controls(automatic_acceptance(TODAY,value))[-1][1]
        self.assertEqual(current['dbm_master'][0]['Norm'],6)
        self.assertEqual(current['importer_master'][0]['Norm'],0)
        self.assertEqual(current['log'],[]);self.assertEqual(current['triggers'],[])

    def test_stale_suggestion_and_phase_out_acceptances_are_rejected_next_date(self):
        for reason in ('missing','phase'):
            value=state();value['Suggestions']=[suggestion()]
            own=automatic_acceptance(TODAY,value)
            if reason=='missing':own['Suggestions']=[]
            else:own['PhaseOutTbl']=[dict(SKUCode='S',WhCode='W')]
            current=next_controls(own)[-1][1]
            self.assertEqual(current['acceptance'],[]);self.assertEqual(current['dbm_master'][0]['Norm'],0)

    def test_inactive_has_exact_prior_stages_and_preserves_existing_queue(self):
        from mta.domain import dbm_selected_chain as chain
        value,facts,config=self.setup_flow();config['batch']['AutoDBMActive']=0
        with patch.object(chain,'automatic_acceptance',side_effect=AssertionError('inactive producer called')):
            stages=list(connected_dbm_stages(TODAY,value,facts,config))
        self.assertNotIn('auto-acceptance',[n for n,_ in stages])
        advisory=dict(stages)['norm1-advisory']
        advisory['NormAcceptanceTbl']=[dict(SKUCode='PRIOR',WhCode='W',OldNorm=1,NewNorm=2,AcceptanceDate=TODAY)]
        with patch.object(chain,'automatic_acceptance',side_effect=AssertionError('inactive producer called')):
            with patch.object(chain,'norm1_advisory',return_value=advisory):
                inactive=list(connected_dbm_stages(TODAY,value,facts,config))[-1][1]
        self.assertEqual(inactive['NormAcceptanceTbl'],advisory['NormAcceptanceTbl'])
        enabled=deepcopy(config);enabled['batch']['AutoDBMActive']=1
        actual=list(connected_dbm_stages(TODAY,value,facts,enabled))
        for (name,before),(other,after) in zip(stages,[(n,s) for n,s in actual if n!='auto-acceptance']):
            self.assertEqual(name,other)
            self.assertEqual({k:v for k,v in before.items() if k!='NormAcceptanceTbl'},
                             {k:v for k,v in after.items() if k!='NormAcceptanceTbl'})

    def test_native_enabled_initialization_and_preflight_keep_other_capability_gates(self):
        from tests.production_daily_fixture import initialized_input
        from tests.initialization_input_fixture import encoded
        from mta.mdm.initialization_contract import decode
        from mta.runtime import production_preflight as pf
        value=initialized_input();value['configuration']['delivery']['batch']['AutoDBMActive']=1
        raw,sha,args=encoded(value)
        self.assertEqual(decode(raw,sha,**args)[1]['profile']['delivery']['batch']['AutoDBMActive'],1)
        report=pf.initialization(raw,sha,**args)
        self.assertFalse(any(q['code']=='AUTO_DBM_UNQUALIFIED' for q in report['issues']))
        self.assertFalse(report['production_ready'])
        for invalid in (2,-1,True,'1',None):
            changed=deepcopy(value);changed['configuration']['delivery']['batch']['AutoDBMActive']=invalid
            raw,sha,args=encoded(changed)
            with self.assertRaises(ValueError):decode(raw,sha,**args)
        value['configuration']['delivery']['batch']['PhaseOutRecommendation30Days']=1
        raw,sha,args=encoded(value);report=pf.initialization(raw,sha,**args)
        self.assertTrue(any(q['owner']=='Phase recommendation configuration' for q in report['issues']))


if __name__ == '__main__':
    unittest.main()
