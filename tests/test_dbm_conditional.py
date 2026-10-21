"""Enabled conditional rules: values, joins, ownership, dispatch and typed carry."""
from copy import deepcopy
from datetime import date, timedelta
from types import SimpleNamespace
import os
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'conditional-unit-only')
import django
django.setup()
from mta.domain import dbm_conditional as rules
from mta.domain.dbm_selected_chain import selected_stages
from mta.temporal.chain import connected_dbm_stages
from mta.runtime import relational_state as typed
from mta.serialization import storage

TODAY = '2037-04-10'


def master(sku='S', norm=0, wh='W', **values):
    return dict(SKUCode=sku, WhCode=wh, Norm=norm, MinNorm=0, RLT=3, RCP=3, GCP=3,
        OCP=4, MinOrderCount=1, ParentWhCode=None, SKUIntroDate='2001-01-01', **values)


def observation(sku='S', wh='W', day=TODAY, stock=1, consumption=3):
    return dict(SKUCode=sku, WhCode=wh, Stock=stock, Consumption=consumption,
                GIT=0, Receipts=0, BlueZone=0, ReportDate=day)


def member(sku='S', wh='W', **values):
    row = dict(SKUCode=sku, WhCode=wh, RedEnabled=True, GreenEnabled=True,
        RedResumeDate='2001-01-01', GreenResumeDate='2001-01-01', SuggestionStartDate=None)
    row.update(values)
    return row


def settings(one='2', two='1', percent='50'):
    return [dict(Parameter=name, Value=value, Description='Operator threshold') for name, value in zip(rules.THRESHOLDS, (one, two, percent))]


def state():
    value = {path.rsplit('/', 1)[-1]: [] for path in typed.CATALOG['bindings'] if path.startswith('closing/dbm/')}
    value.update(LastBatchRunTbl=[dict(LastRunDate=TODAY+'T00:00:00')],
        DBMMaster=[master()], DailyConsumption=[observation(day='2037-04-08'), observation()],
        SuspendOrderType=[member()], IntermediateTables=[],
        DBMSettingsTbl=[dict(Parameter='NormZeroOneRuleActive', Value='1'),
            dict(Parameter='SpikeRuleHorizon', Value='7'), dict(Parameter='SpikeRuleParCount', Value='3')],
        FirstReplenishmentPercentageTbl=[dict(ReplenishmentPercentage=50)],
        ReportHeader=[], ReportRows=[])
    return value


def order(sku='S', wh='W', day=TODAY):
    return dict(OrderID='O1', SKUCode=sku, WhCode=wh, OrderQuantity=100, OrderDate=day, ImportDate=day)


def delivery():
    batch = dict(AutoDBMActive=0, PhaseOutRecommendation30Days=0, PhaseOutRecommendation60Days=0,
        PhaseOutRecommendation90Days=0, DBMNormChangeReportHorizon=1, NormChangeLogHorizon=7,
        GatherSuspensionHistory=1, ActivateNormChangeLogReport=1, DailyConsumptionHorizonDBM=370,
        ActivateNorm0Report30Days=0, ActivateNorm0Report60Days=0, ActivateNorm0Report90Days=0,
        ActivateNorm1Report30Days=0, ActivateNorm2Report30Days=0,
        Norm1Increase_MultipleRLT=1, Norm2Decrease_MultipleRLT=1)
    return dict(batch=batch, conditional_dbm=dict(importer_vf_settings=settings()))


class ConditionalRuleTests(unittest.TestCase):
    def test_rule7_node_ratio_order_count_hierarchy_and_own_summary(self):
        value = state(); value['OrderData'] = [order(), order()]
        before = deepcopy(value)
        result = rules.order_norm_zero_increase(TODAY, value)
        self.assertEqual(result['Suggestions'], [dict(SKUCode='S', WhCode='W', Type=7, NewNorm=3)])
        self.assertEqual(result['OrderRuleSummary'], [dict(SKUCode='S', WhCode='W', NodeOrderCount=2,
            CummOrderCount=2, NodeConsumption=6, OCPStartDate='2037-04-06',
            ConsumptionStartDate='2037-04-08', StartingStock=1)])
        self.assertEqual(result['DBMMaster'], value['DBMMaster'])
        self.assertEqual(result['NormAcceptanceTbl'], [])
        self.assertEqual(value, before)

    def test_rule7_children_roll_up_counts_but_not_consumption_or_node_denominator(self):
        value = state(); value['DBMMaster'][0]['ParentWhCode'] = 'P'
        value['DBMMaster'].append(master(wh='P'))
        value['DBMMaster'][1]['MinOrderCount'] = 2
        value['DailyConsumption'].append(observation(wh='P', consumption=99))
        value['SuspendOrderType'].append(member(wh='P'))
        value['OrderData'] = [order(), order()]
        result = rules.order_norm_zero_increase(TODAY, value)
        self.assertEqual([(r['WhCode'],r['NodeOrderCount'],r['CummOrderCount'],r['NodeConsumption'])
                         for r in result['OrderRuleSummary']], [('W',2,2,6),('P',0,2,99)])
        self.assertEqual([r['WhCode'] for r in result['Suggestions']], ['W'])

    def test_rule7_duplicate_master_member_fact_multiplicity_is_not_deduplicated(self):
        value = state(); value['DailyConsumption'] = [observation()]
        value['DBMMaster'] *= 2; value['SuspendOrderType'] *= 2; value['OrderData'] = [order()]
        result = rules.order_norm_zero_increase(TODAY, value)
        self.assertEqual(len(result['Suggestions']), 2)
        self.assertTrue(all(r['NewNorm'] == 2 for r in result['Suggestions']))
        self.assertEqual([(r['NodeOrderCount'],r['NodeConsumption']) for r in result['OrderRuleSummary']], [(4,6),(4,6)])

    def test_rule7_missing_null_disabled_minimum_and_prior_winner_cases(self):
        for change in ('orders', 'resume', 'consumption', 'stock', 'ocp', 'disabled', 'minimum', 'winner'):
            value = state(); value['OrderData'] = [order()]
            if change == 'orders': value['OrderData'] = []
            if change == 'resume': value['SuspendOrderType'][0]['RedResumeDate'] = None
            if change == 'consumption':
                for row in value['DailyConsumption']: row['Consumption'] = None
            if change == 'stock':
                for row in value['DailyConsumption']: row['Stock'] = None
            if change == 'ocp': value['DBMMaster'][0]['OCP'] = None
            if change == 'disabled': value['SuspendOrderType'][0]['RedEnabled'] = False
            if change == 'minimum': value['DBMMaster'][0]['MinOrderCount'] = 2
            if change == 'winner': value['Suggestions'] = [dict(SKUCode='S', WhCode='W', Type=1, NewNorm=8)]
            with self.subTest(change=change):
                result = rules.order_norm_zero_increase(TODAY, value)
                self.assertFalse(any(r['Type']==7 for r in result['Suggestions']))

    def test_rule7_future_rows_inclusive_resume_cutoff_and_conflicting_starting_stock(self):
        value = state(); value['DailyConsumption'] = [observation(day='2037-04-06'), observation(day='2037-04-11')]
        value['SuspendOrderType'][0]['RedResumeDate'] = '2037-04-06'; value['OrderData'] = [order(day='2037-04-06')]
        result = rules.order_norm_zero_increase(TODAY, value)
        self.assertEqual(result['OrderRuleSummary'][0]['NodeConsumption'],6)
        self.assertEqual(result['OrderRuleSummary'][0]['NodeOrderCount'],1)
        value['DailyConsumption'].append(observation(day='2037-04-06', stock=2))
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            rules.order_norm_zero_increase(TODAY, value)

    def test_rule7_cycle_returns_partial_rollup_without_inventing_a_break(self):
        value = state(); value['DBMMaster'][0]['ParentWhCode'] = 'W'; value['OrderData'] = [order()]
        result = rules.order_norm_zero_increase(TODAY, value)
        self.assertEqual(result['Suggestions'], [])
        scratch = {r['table']:r['rows'] for r in result['IntermediateTables']}
        self.assertEqual(scratch['dbo.ParentHeirarchy'], [dict(SKUCode='S',WhCode='W',ParentWhCode='W')])
        self.assertEqual(scratch['dbo.LeafNode'], [])
        self.assertEqual(result['OrderRuleSummary'][0]['NodeConsumption'],6)

    def test_rule7_counter_boundary_and_signed_recommendation_are_preserved(self):
        for depth in (99,100):
            value=state();value['DBMMaster']=[];value['DailyConsumption']=[]
            value['SuspendOrderType']=[];value['OrderData']=[]
            for i in range(depth):
                wh='W'+str(i);m=master(wh=wh);m['ParentWhCode']='W'+str(i+1) if i+1<depth else None
                value['DBMMaster'].append(m);value['DailyConsumption'].append(observation(wh=wh))
                value['SuspendOrderType'].append(member(wh=wh));value['OrderData'].append(order(wh=wh))
            result=rules.order_norm_zero_increase(TODAY,value)
            self.assertEqual(len(result['Suggestions']),99 if depth==99 else 0)
            self.assertEqual(result['OrderRuleSummary'][-1]['CummOrderCount'],depth)
        value=state();value['DailyConsumption']=[observation(stock=-3,consumption=-1)];value['OrderData']=[order()]
        self.assertEqual(rules.order_norm_zero_increase(TODAY,value)['Suggestions'],[dict(SKUCode='S',WhCode='W',Type=7,NewNorm=-1)])

    def test_rule10_counts_sales_not_quantity_and_uses_importer_settings(self):
        value = state(); value['DBMMaster'][0]['Norm'] = 1
        value['VFSettings'] = settings(one='999')
        value['DailyConsumption'] = [observation(consumption=999), observation(consumption=1)]
        result = rules.norm_one_consumption_increase(TODAY, value, multiple_rlt=1, importer_vf_settings=settings())
        self.assertEqual(result['Suggestions'], [dict(SKUCode='S',WhCode='W',Type=10,NewNorm=2)])
        self.assertEqual(result['DBMMaster'], value['DBMMaster'])
        value['DailyConsumption'] = [observation(consumption=999)]
        self.assertEqual(rules.norm_one_consumption_increase(TODAY,value,multiple_rlt=1,importer_vf_settings=settings())['Suggestions'],[])

    def test_rule10_duplicate_join_counts_group_once_and_null_lower_bounds_exclude(self):
        value = state(); value['DBMMaster'][0]['Norm']=1
        value['DBMMaster'] *= 2; value['SuspendOrderType'] *= 2; value['DailyConsumption']=[observation(day='2037-04-07')]
        result = rules.norm_one_consumption_increase(TODAY,value,multiple_rlt=1,importer_vf_settings=settings(one='4'))
        self.assertEqual(len(result['Suggestions']),1)
        value['SuspendOrderType'][0]['RedResumeDate']=None
        result = rules.norm_one_consumption_increase(TODAY,value,multiple_rlt=1,importer_vf_settings=settings(one='1'))
        self.assertEqual(result['Suggestions'],[])

    def test_rule10_zero_negative_period_future_rows_and_disabled_prior_filter(self):
        value=state();value['DBMMaster'][0]['Norm']=1
        value['DailyConsumption']=[observation(day='2037-04-13')]
        self.assertEqual(len(rules.norm_one_consumption_increase(TODAY,value,multiple_rlt=-1,importer_vf_settings=settings(one='1'))['Suggestions']),1)
        for change in ('disabled','prior','rlt'):
            current=deepcopy(value)
            if change=='disabled': current['SuspendOrderType'][0]['RedEnabled']=False
            if change=='prior': current['Suggestions']=[dict(SKUCode='S',WhCode='W',Type=7,NewNorm=9)]
            if change=='rlt': current['DBMMaster'][0]['RLT']=None
            result=rules.norm_one_consumption_increase(TODAY,current,multiple_rlt=0,importer_vf_settings=settings(one='1'))
            self.assertFalse(any(r['Type']==10 for r in result['Suggestions']))

    def test_rule11_coverage_sale_threshold_stockout_and_null_stock_semantics(self):
        value=state();value['DBMMaster'][0]['Norm']=2
        value['DailyConsumption']=[observation(consumption=None,stock=None),observation(day='2037-04-07',consumption=0)]
        call=lambda s:rules.norm_two_consumption_decrease(TODAY,s,multiple_rlt=1,importer_vf_settings=settings())
        self.assertEqual(call(value)['Suggestions'],[dict(SKUCode='S',WhCode='W',Type=11,NewNorm=1)])
        for change in ('coverage','sale','stockout','disabled','resume'):
            current=deepcopy(value)
            if change=='coverage':current['DailyConsumption']=current['DailyConsumption'][:1]
            if change=='sale':current['DailyConsumption'][0]['Consumption']=1
            if change=='stockout':current['DailyConsumption'][0]['Stock']=0
            if change=='disabled':current['SuspendOrderType'][0]['GreenEnabled']=False
            if change=='resume':current['SuspendOrderType'][0]['GreenResumeDate']=None
            with self.subTest(change=change):self.assertEqual(call(current)['Suggestions'],[])

    def test_rule11_removes_same_norm_prior_suggestion_but_protects_other_winner(self):
        value=state();value['DBMMaster'][0]['Norm']=2
        value['DailyConsumption']=[observation(consumption=0)]*2
        value['Suggestions']=[dict(SKUCode='S',WhCode='W',Type=1,NewNorm=2),dict(SKUCode='other',WhCode='W',Type=11,NewNorm=1)]
        result=rules.norm_two_consumption_decrease(TODAY,value,multiple_rlt=1,importer_vf_settings=settings())
        self.assertEqual(result['Suggestions'],[dict(SKUCode='S',WhCode='W',Type=11,NewNorm=1)])
        value['Suggestions'][0]['NewNorm']=4
        self.assertEqual(rules.norm_two_consumption_decrease(TODAY,value,multiple_rlt=1,importer_vf_settings=settings())['Suggestions'],value['Suggestions'][:1])

    def test_rule11_duplicate_master_period_maximum_and_duplicate_points(self):
        value=state();value['DBMMaster'][0]['Norm']=2
        other=deepcopy(value['DBMMaster'][0]);other['RLT']=6;value['DBMMaster'].append(other)
        value['DailyConsumption']=[observation(day='2037-04-0'+str(d),consumption=0) for d in (7,8,9)]+[observation(consumption=0)]
        self.assertEqual(len(rules.norm_two_consumption_decrease(TODAY,value,multiple_rlt=1,importer_vf_settings=settings(percent='100'))['Suggestions']),1)
        value['DBMMaster']=value['DBMMaster'][1:]
        self.assertEqual(rules.norm_two_consumption_decrease(TODAY,value,multiple_rlt=1,importer_vf_settings=settings(percent='100'))['Suggestions'],[])

    def test_activation_count_settings_null_empty_duplicate_and_overflow(self):
        self.assertFalse(rules.enabled([]))
        self.assertTrue(rules.enabled([dict(Parameter='normzerooneruleactive ',Value='1 ')]))
        self.assertFalse(rules.enabled([dict(Parameter='NormZeroOneRuleActive',Value='1')]*2))
        self.assertIsNone(rules.scalar_setting([],rules.THRESHOLDS[0]))
        self.assertIsNone(rules.scalar_setting(settings(one=None),rules.THRESHOLDS[0]))
        self.assertEqual(rules.scalar_setting(settings(one=''),rules.THRESHOLDS[0]),0)
        self.assertEqual(str(rules.scalar_setting(settings(percent='50.1235'),rules.THRESHOLDS[2],percentage=True)),'50.124')
        for rows in (settings()*2,settings(one='bad'),settings(one=str(2**31))):
            with self.assertRaises(ValueError):rules.configuration(delivery()['batch'],rows)
        value=state();value['DBMMaster'][0]['Norm']=1
        for multiple in (True,2**31,2**31-1):
            with self.assertRaises(ValueError):rules.norm_one_consumption_increase(TODAY,value,multiple_rlt=multiple,importer_vf_settings=settings())

    def test_active_missing_config_fails_before_connected_ingestion(self):
        from mta.domain import dbm_selected_chain as chain
        with patch.object(chain,'connected_stages') as connected:
            with self.assertRaisesRegex(ValueError,'multipliers required'):
                list(selected_stages(TODAY,state(),{},{}))
            connected.assert_not_called()


class ConnectedConditionalTests(unittest.TestCase):
    def test_native_initialization_contract_and_preflight_preserve_owned_settings(self):
        from tests.production_daily_fixture import initialized_input
        from tests.initialization_input_fixture import encoded
        from mta.mdm.initialization_contract import decode
        from mta.mdm.initialization_rows import select
        from mta.runtime import production_preflight as pf
        value=initialized_input()
        value['opening']['state']['dbm']['DBMSettingsTbl'].append(dict(Parameter='NormZeroOneRuleActive',Value='1'))
        value['configuration']['delivery']['batch'].update(Norm1Increase_MultipleRLT=4,Norm2Decrease_MultipleRLT=4)
        value['configuration']['delivery']['conditional_dbm']=delivery()['conditional_dbm']
        raw,sha,args=encoded(value)
        frame=decode(raw,sha,**args)[1]
        rows=frame['profile']['delivery']['conditional_dbm']['importer_vf_settings']
        self.assertEqual(rows,settings())
        self.assertEqual(select(tuple(rows[0]),'input/profile/delivery/conditional_dbm/importer_vf_settings/values',rows),'Importer/VFSettings')
        report=pf.initialization(raw,sha,**args)
        self.assertFalse(any(q['code']=='CONDITIONAL_DBM_RULES_UNQUALIFIED' for q in report['issues']))
        self.assertFalse(any(q['code']=='CONTRACT_INVALID' and 'conditional_dbm' in q['path'] for q in report['issues']))
        self.assertFalse(report['production_ready'])
        before=deepcopy(rows)
        for changed in (dict(rows[0],Value=None),dict(rows[0],Parameter='x'*51),dict(rows[0],Description='😀'*101)):
            with self.assertRaises(ValueError):
                select(tuple(changed),'input/profile/delivery/conditional_dbm/importer_vf_settings/values',[changed])
        self.assertEqual(rows,before)
        # No multiplier defaults and no NULL/duplicate scalar replacement.
        for changed in ('missing','wrong_type','duplicate'):
            current=deepcopy(value)
            if changed=='missing':del current['configuration']['delivery']['batch']['Norm1Increase_MultipleRLT']
            if changed=='wrong_type':current['configuration']['delivery']['batch']['Norm1Increase_MultipleRLT']='4'
            if changed=='duplicate':current['configuration']['delivery']['conditional_dbm']['importer_vf_settings']*=2
            encoded_raw,encoded_sha,encoded_args=encoded(current)
            report=pf.initialization(encoded_raw,encoded_sha,**encoded_args)
            self.assertFalse(report['stage_eligibility']['day'])
            self.assertTrue(any('conditional_dbm' in q['path'] or 'Norm1Increase_MultipleRLT' in q['path'] for q in report['issues']))

    def setup_flow(self):
        value=state()
        value['DBMMaster']=[master('ZERO',0),master('ONE',1),master('TWO',2)]
        value['DailyConsumption']=[observation(sku=sku,day=day,stock=1 if sku=='ZERO' else None,
            consumption=3 if sku=='ZERO' else 1 if sku=='ONE' else 0)
            for sku in ('ZERO','ONE','TWO') for day in ('2037-04-07','2037-04-08','2037-04-09')]
        value['SuspendOrderType']=[]
        value['VFSettings']=settings(one='999',two='999',percent='999')
        facts=dict(daily_raw=[],bpr_daily=[],order_raw=[order(sku='ZERO')],exclusions=[],
                   distributor_transactions=[],vendor_transactions=[])
        return value,facts

    def test_real_daily_dbm_dispatch_order_outputs_history_and_own_typed_next_state(self):
        value,facts=self.setup_flow();before=deepcopy(value)
        stages=list(connected_dbm_stages(TODAY,value,facts,delivery()))
        names=[n for n,_ in stages]
        self.assertEqual(names[names.index('rule6'):names.index('discard')+1],['rule6','rule7','rule10','rule11','discard'])
        final=stages[-1][1]
        self.assertEqual([(r['SKUCode'],r['Type'],r['NewNorm']) for r in final['Suggestions']], [('ZERO',7,9),('ONE',10,2),('TWO',11,1)])
        self.assertEqual([(r['SKUCode'],r['Type'],r['OldNorm'],r['NewNorm'],r['SuggestionDate']) for r in final['SuggestionsLog']],
                         [('ZERO',7,0,9,TODAY),('ONE',10,1,2,TODAY),('TWO',11,2,1,TODAY)])
        self.assertEqual(final['DBMMaster'],before['DBMMaster'])
        self.assertEqual(final['NormAcceptanceTbl'],[])
        self.assertEqual(final['OrderDataSummary'][0]['NodeConsumption'],9)
        self.assertTrue(final['SuspendHistory'])
        self.assertEqual(value,before)
        # Exercise the real relational codecs, without database execution/acceptance.
        reconstructed=deepcopy(final)
        for name in ('DBMMaster','DailyConsumption','OrderData','OrderRuleSummary','OrderDataSummary','Suggestions','SuggestionsLog','SuspendOrderType','SuspendHistory'):
            path='closing/dbm/'+name;records=[]
            with patch.object(typed,'bulk',side_effect=lambda query, rows:records.extend(rows)):
                meta=typed.save_image(SimpleNamespace(pk='2b2f8d37-0a14-4624-985b-88c8d2662f6a'),path,None,storage(final[name]),table='DBM/'+name)
            cursor=MagicMock();cursor.fetchmany.side_effect=[[tuple(r[2:]) for r in records],[]]
            with patch.object(typed.connection,'chunked_cursor') as context:
                context.return_value.__enter__.return_value=cursor
                reconstructed[name]=typed.load_image(SimpleNamespace(pk='2b2f8d37-0a14-4624-985b-88c8d2662f6a'),meta)
            self.assertEqual(reconstructed[name],storage(final[name]))
            self.assertEqual(cursor.execute.call_args.args[1],['2b2f8d37-0a14-4624-985b-88c8d2662f6a',path])
        tomorrow='2037-04-11';reconstructed['LastBatchRunTbl']=[dict(LastRunDate=tomorrow+'T00:00:00')]
        successor=list(connected_dbm_stages(tomorrow,reconstructed,
            {**facts,'order_raw':[order(sku='ZERO',day=tomorrow)]},delivery()))[-1][1]
        self.assertEqual(successor['DBMMaster'],final['DBMMaster'])
        self.assertEqual([r['ImportDate'] for r in successor['OrderDataSummary']],[TODAY,tomorrow])
        self.assertEqual(successor['OrderRuleSummary'][0]['NodeOrderCount'],2)
        self.assertEqual(successor['Suggestions'][0]['NewNorm'],5)

    def test_inactive_and_duplicate_activation_keep_rules_one_six_exact(self):
        value,facts=self.setup_flow()
        for active in ('0','duplicate'):
            current=deepcopy(value)
            current['DBMSettingsTbl'][0]['Value']='0' if active=='0' else '1'
            if active=='duplicate':current['DBMSettingsTbl'].append(deepcopy(current['DBMSettingsTbl'][0]))
            stages=list(connected_dbm_stages(TODAY,current,facts,delivery()))
            self.assertFalse(any(n in ('rule7','rule10','rule11') for n,_ in stages))
            from mta.domain.dbm_connected import connected_stages
            expected=list(connected_stages(TODAY,current,facts))
            self.assertEqual(stages[:len(expected)],expected)

    def test_overlapping_prior_rules_then_conditional_then_delisting(self):
        value,facts=self.setup_flow()
        for row in value['DailyConsumption']:
            if row['SKUCode']=='TWO':row['Stock']=2
        stages=dict(connected_dbm_stages(TODAY,value,facts,delivery()))
        # Rule5 proposes unchanged Norm2; rule11 removes it before generating Norm1.
        self.assertTrue(any(r['SKUCode']=='TWO' and r['Type']==5 and r['NewNorm']==2 for r in stages['rule6']['Suggestions']))
        self.assertTrue(any(r['SKUCode']=='TWO' and r['Type']==11 and r['NewNorm']==1 for r in stages['rule11']['Suggestions']))
        facts['daily_raw']=[observation(sku='TWO',stock=0,consumption=0)]
        winner=dict(connected_dbm_stages(TODAY,value,facts,delivery()))
        self.assertTrue(any(r['SKUCode']=='TWO' and r['Type']==1 and r['NewNorm']==3 for r in winner['rule11']['Suggestions']))

    def test_delisting_runs_after_conditional_prior_winners(self):
        value,facts=self.setup_flow()
        value['DBMMaster'].append(master('DELIST',3))
        value['DailyConsumption'].append(observation(sku='DELIST',stock=None,consumption=0))
        value['DBMSettingsTbl'].append(dict(Parameter='DelistingofNormRuleActive',Value='1'))
        value['VFSettings'].append(dict(Parameter='DBMDelistingDataPointPercent',Value='0'))
        value['SKUDescriptionTbl']=[dict(SKUCode=sku,SKUDescription=sku) for sku in ('ZERO','ONE','TWO','DELIST')]
        value['SiteDescriptionTbl']=[dict(WHCode='W',WHDescription='Warehouse')]
        value['SKULocStandardAttributes']=[dict(SKUCode=sku,WhCode='W',ExtendedOCP=None) for sku in ('ZERO','ONE','TWO','DELIST')]
        stages=list(connected_dbm_stages(TODAY,value,facts,delivery()))
        names=[name for name,_ in stages]
        self.assertEqual(names[names.index('rule6'):names.index('discard')+1],['rule6','rule7','rule10','rule11','rule12','discard'])
        suggestions=dict(stages)['rule12']['Suggestions']
        self.assertEqual([(r['SKUCode'],r['Type']) for r in suggestions],[('ZERO',7),('ONE',10),('TWO',11),('DELIST',12)])
