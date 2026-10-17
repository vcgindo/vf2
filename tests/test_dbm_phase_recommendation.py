from tests.stage_values import capture_stages
"""Source-owned phase horizons, dispatch, typed retention and computed carry."""
from copy import deepcopy
from datetime import date,timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
from tests.test_dbm_conditional import TODAY,state,master,observation,delivery
from tests import test_dbm_auto_acceptance as auto_tests
from mta.domain import dbm_phase_recommendation as phase
from mta.temporal.chain import connected_dbm_stages,retain_dbm_stages
from mta.runtime import relational_state as typed
from mta.serialization import storage


def attributes(**keys):
    return {**keys,**{f'c{i}':'comma,value' if i==1 else None for i in range(1,16)}}


def metadata(value,skus=('S',)):
    value['SKUDescriptionTbl']=[dict(SKUCode=s,SKUDescription='SKU, '+s) for s in skus]
    value['SiteDescriptionTbl']=[dict(WHCode='W',WHDescription='Warehouse, Name')]
    value['SkuAttributeData']=[attributes(SKUCode=s) for s in skus]
    value['LocationAttributeData']=[attributes(WHCode='W')]
    value['SkuLocAttributeData']=[attributes(SKUCode=s,LocCode='W') for s in skus]


def population(horizon=90):
    value=state();value['DBMMaster']=[master(norm=9)]
    value['PhaseOutRecommendation']=[]
    value['DailyConsumption']=[observation(day=(date.fromisoformat(TODAY)-timedelta(days=i)).isoformat(),stock=6,consumption=0)
                               for i in range(horizon)]
    metadata(value)
    return value


def batch(horizons=(30,60,90),tolerance=0):
    config=delivery()['batch']
    for horizon in phase.HORIZONS:
        config[f'PhaseOutRecommendation{horizon}Days']=int(horizon in horizons)
        if horizon in horizons:config[f'PhaseOutRecommendationTolerance{horizon}Days']=tolerance
    return config


class PhaseProducerTests(unittest.TestCase):
    def test_positive30_60_90_full53_columns_nulls_comma_removal_and_source_immutability(self):
        for horizon in phase.HORIZONS:
            value=population();before=deepcopy(value)
            row=phase.phase_recommendation(TODAY,value,horizon,0)['PhaseOutRecommendation'][0]
            self.assertEqual(tuple(row),phase.FIELDS);self.assertEqual(len(row),53)
            self.assertEqual([row[name] for name in phase.FIELDS[:8]],['S','SKU S','W','Warehouse Name',horizon,0,9,6])
            self.assertEqual(row['SKUAtt01'],'commavalue');self.assertIsNone(row['SKULocAtt15'])
            self.assertEqual(value,before)

    def test_strict_lower_bound_future_inclusion_current_left_join_null_and_tolerance_boundary(self):
        for horizon in phase.HORIZONS:
            value=population(horizon)
            value['DailyConsumption']=[r for r in value['DailyConsumption'] if r['ReportDate']!=TODAY]
            old=(date.fromisoformat(TODAY)-timedelta(days=horizon)).isoformat()
            value['DailyConsumption'].append(observation(day=old,stock=6,consumption=99))
            self.assertEqual(phase.phase_recommendation(TODAY,value,horizon,0)['PhaseOutRecommendation'],[])
            row=phase.phase_recommendation(TODAY,value,horizon,1)['PhaseOutRecommendation'][0]
            self.assertEqual(row['StockDays'],horizon-1);self.assertIsNone(row['CurrentStock'])
            value['DailyConsumption'].append(observation(day='2037-04-11',stock=6,consumption=0))
            self.assertEqual(phase.phase_recommendation(TODAY,value,horizon,0)['PhaseOutRecommendation'][0]['StockDays'],horizon)

    def test_null_consumption_sum_and_stock_predicates_preserve_negative_sales(self):
        value=population(1)
        for sale,expected in ((None,False),(1,False),(0,True),(-1,True)):
            value['DailyConsumption'][0]['Consumption']=sale
            rows=phase.phase_recommendation(TODAY,value,30,29)['PhaseOutRecommendation']
            self.assertEqual(bool(rows),expected)
        for stock in (None,0,-1):
            value['DailyConsumption'][0]['Stock']=stock
            self.assertEqual(phase.phase_recommendation(TODAY,value,30,29)['PhaseOutRecommendation'],[])

    def test_norm_zero_null_and_phase_in_out_exclude_whole_sku_across_locations(self):
        for reason in ('zero','null','phase_in','phase_out','null_sku','null_wh','null_date'):
            value=population()
            if reason=='zero':value['DBMMaster'][0]['Norm']=0
            elif reason=='null':value['DBMMaster'][0]['Norm']=None
            elif reason in ('phase_in','phase_out'):
                value['PhaseInTbl' if reason=='phase_in' else 'PhaseOutTbl']=[dict(SKUCode='s ',WhCode='OTHER')]
            elif reason=='null_sku':value['DBMMaster'][0]['SKUCode']=None
            elif reason=='null_wh':value['DBMMaster'][0]['WhCode']=None
            else:
                for row in value['DailyConsumption']:row['ReportDate']=None
            with self.subTest(reason=reason):self.assertEqual(phase.phase_recommendation(TODAY,value,30,0)['PhaseOutRecommendation'],[])

    def test_missing_inner_metadata_join_denies_row_duplicate_dimensions_multiply(self):
        value=population()
        for table in ('SKUDescriptionTbl','SiteDescriptionTbl','SkuAttributeData','LocationAttributeData','SkuLocAttributeData'):
            current=deepcopy(value);current[table]=[]
            self.assertEqual(phase.phase_recommendation(TODAY,current,30,0)['PhaseOutRecommendation'],[])
        value['SKUDescriptionTbl']*=2;value['SkuAttributeData']*=3;value['SkuLocAttributeData']*=2
        rows=phase.phase_recommendation(TODAY,value,30,0)['PhaseOutRecommendation']
        self.assertEqual(len(rows),12);self.assertEqual(rows,[rows[0]]*12)

    def test_duplicate_master_and_current_stock_group_multiplicity_not_distinct_days(self):
        value=population(2);value['DBMMaster']*=2
        value['DailyConsumption'].append(deepcopy(value['DailyConsumption'][0]))
        value['DailyConsumption'].append(observation(stock=9,consumption=0))
        rows=phase.phase_recommendation(TODAY,value,30,22)['PhaseOutRecommendation']
        self.assertEqual([(r['CurrentStock'],r['StockDays']) for r in rows],[(6,16),(9,8)])
        self.assertEqual(len(rows),2)

    def test_encounter_order_current_norm_groups_and_conflicting_group_spelling_denial(self):
        value=population(1);value['DBMMaster']=[master(norm=9),master(norm=8)]
        rows=phase.phase_recommendation(TODAY,value,30,29)['PhaseOutRecommendation']
        self.assertEqual([r['CurrentNorm'] for r in rows],[9,8])
        value['DBMMaster']=[master(norm=9),master('s ',9)]
        with self.assertRaisesRegex(ValueError,'SOURCE_ORDER_AMBIGUITY'):phase.phase_recommendation(TODAY,value,30,29)

    def test_target_width_overflow_and_atomic_denial_do_not_truncate_inputs(self):
        value=population();value['PhaseOutRecommendation']=[dict(prior=True)]
        for table,key,column,bad in (('SKUDescriptionTbl',None,'SKUDescription','x'*126),
                                     ('SkuAttributeData',None,'c1','😀'*26),
                                     ('DailyConsumption',0,'Consumption',2**31)):
            current=deepcopy(value);current[table][key or 0][column]=bad;before=deepcopy(current)
            with self.assertRaises(ValueError):phase.phase_recommendation(TODAY,current,30,0)
            self.assertEqual(current,before)
        value['DailyConsumption'][0]['Consumption']=2**31-1
        value['DailyConsumption'][1]['Consumption']=1
        with self.assertRaises(ValueError):phase.phase_recommendation(TODAY,value,30,0)

    def test_explicit_configuration_no_tolerance_default_or_new_range_policy(self):
        phase.configuration(batch(tolerance=-1));phase.configuration(batch(tolerance=100))
        for invalid in (None,True,'5',2**31):
            config=batch();config[phase.TOLERANCES[0]]=invalid
            with self.assertRaises(ValueError):phase.configuration(config)
        config=batch();del config[phase.TOLERANCES[0]]
        with self.assertRaises(ValueError):phase.configuration(config)
        config=batch();config['PhaseOutRecommendation30Days']=2
        with self.assertRaises(ValueError):phase.configuration(config)
        phase.configuration(batch(()))

    def test_sequential_overwrites_snapshot_retention_empty_replacement_and_inactive_carry(self):
        value=population(30);value['PhaseOutRecommendation']=[dict(prior=True)]
        stages=list(phase.phase_stages(TODAY,value,batch()))
        self.assertEqual([n for n,_ in stages],['phase-recommendation-30','phase-recommendation-60','phase-recommendation-90'])
        self.assertEqual(len(stages[0][1]['PhaseOutRecommendation']),1)
        self.assertEqual(stages[1][1]['PhaseOutRecommendation'],[])
        self.assertEqual(stages[-1][1]['PhaseOutRecommendation'],[])
        self.assertEqual(list(phase.phase_stages(TODAY,value,batch(()))),[])
        self.assertEqual(value['PhaseOutRecommendation'],[dict(prior=True)])


class ConnectedPhaseTests(unittest.TestCase):
    def test_typed_wrong_owner_report_and_closing_bindings_deny_before_write(self):
        from mta.runtime.dbm_phase_storage import OPENING,TABLE
        rows=phase.phase_recommendation(TODAY,population(),30,0)['PhaseOutRecommendation']
        for image,binding in ((OPENING,None),('closing/dbm/PhaseOutRecommendation',None),
                ('reports/phase-recommendation-30/PhaseOutRecommendation','reports/phase-recommendation-60/PhaseOutRecommendation')):
            with patch.object(typed,'bulk') as write:
                with self.assertRaises(ValueError):typed.save_image(auto_tests.RUN,image,binding,rows,table=TABLE)
                write.assert_not_called()

    def setup_flow(self):
        value,facts,config=auto_tests.AutomaticCarryTests().setup_flow()
        value['DBMMaster'].append(master('DORMANT',9));value['PhaseOutRecommendation']=[]
        value['DailyConsumption'].extend([dict(row,SKUCode='DORMANT') for row in population()['DailyConsumption']])
        facts['daily_raw'].append(observation(sku='DORMANT',stock=6,consumption=0))
        metadata(value,('ZERO','ONE','TWO','DORMANT'))
        config['batch']=batch();config['batch']['AutoDBMActive']=1
        return value,facts,config

    def test_all_enabled_actual_position_auto_queue_and_closing_without_phase_workflow_mutation(self):
        value,facts,config=self.setup_flow();before=deepcopy(value)
        stages=capture_stages(connected_dbm_stages(TODAY,value,facts,config));names=[name for name,_ in stages]
        self.assertEqual(names[names.index('norm1-advisory'):names.index('auto-acceptance')+1],
                         ['norm1-advisory','phase-recommendation-30','phase-recommendation-60','phase-recommendation-90','auto-acceptance'])
        for horizon in phase.HORIZONS:
            self.assertEqual(dict(stages)[f'phase-recommendation-{horizon}']['PhaseOutRecommendation'][0]['StockDays'],horizon)
        final=stages[-1][1]
        self.assertEqual(final['PhaseOutRecommendation'][0]['StockDays'],90)
        self.assertTrue(any(r['SKUCode']=='TWO' for r in final['NormAcceptanceTbl']))
        for name in ('PhaseInTbl','PhaseOutTbl','DBMMaster'):
            self.assertEqual(final[name],before[name])
        self.assertEqual(value,before)

    def test_retained_per_horizon_images_and_own_reconstructed_next_date_inactive_carry(self):
        value,facts,config=self.setup_flow()
        retained=retain_dbm_stages(connected_dbm_stages(TODAY,value,facts,config),[])
        self.assertEqual([name for name,_ in retained if name.startswith('phase-')],list(typed.PHASE_STAGES))
        reconstructed=deepcopy(retained[-1][1])
        for name,current in [*(r for r in retained if r[0].startswith('phase-')),('closing',retained[-1][1])]:
            path='closing/dbm/PhaseOutRecommendation' if name=='closing' else 'reports/'+name+'/PhaseOutRecommendation'
            records=[]
            with patch.object(typed,'bulk',side_effect=lambda query,rows:records.extend(rows)):
                meta=typed.save_image(auto_tests.RUN,path,path,storage(current['PhaseOutRecommendation']))
            cursor=MagicMock();cursor.fetchmany.side_effect=[[tuple(r[2:]) for r in records],[]]
            with patch.object(typed.connection,'cursor') as context:
                context.return_value.__enter__.return_value=cursor
                rows=typed.load_image(auto_tests.RUN,meta)
            self.assertEqual(rows,storage(current['PhaseOutRecommendation']))
            if name=='closing':reconstructed['PhaseOutRecommendation']=rows
        config['batch']=batch(());reconstructed['LastBatchRunTbl']=[dict(LastRunDate=auto_tests.TOMORROW+'T00:00:00')]
        final=list(connected_dbm_stages(auto_tests.TOMORROW,reconstructed,{**facts,'daily_raw':[],'order_raw':[]},config))[-1][1]
        self.assertEqual(final['PhaseOutRecommendation'],reconstructed['PhaseOutRecommendation'])

    def test_inactive_real_dispatch_unchanged_and_single_horizon_uses_only_explicit_tolerance(self):
        value,facts,config=self.setup_flow();config['batch']=batch(())
        with patch.object(phase,'phase_recommendation',side_effect=AssertionError('inactive called')):
            inactive=capture_stages(connected_dbm_stages(TODAY,value,facts,config))
        self.assertFalse(any(name.startswith('phase-recommendation-') for name,_ in inactive))
        for horizon in phase.HORIZONS:
            config['batch']=batch((horizon,));stages=capture_stages(connected_dbm_stages(TODAY,value,facts,config))
            self.assertEqual([name for name,_ in stages if name.startswith('phase-')],[f'phase-recommendation-{horizon}'])
            for (name,expected),(actual,current) in zip(inactive,[(n,s) for n,s in stages if not n.startswith('phase-')]):
                self.assertEqual(name,actual)
                self.assertEqual({k:v for k,v in expected.items() if k!='PhaseOutRecommendation'},
                                 {k:v for k,v in current.items() if k!='PhaseOutRecommendation'})

    def test_initialized_empty_derived_population_no_answer_seed_and_enabled_tolerances(self):
        from tests.production_daily_fixture import initialized_input
        from tests.initialization_input_fixture import encoded
        from mta.mdm.initialization_contract import decode
        value=initialized_input();value['configuration']['delivery']['batch'].update(batch())
        raw,sha,args=encoded(value);decoded=decode(raw,sha,**args)[1]
        self.assertEqual(decoded['opening']['state']['dbm']['PhaseOutRecommendation'],[])
        from mta.runtime import production_preflight as preflight
        report=preflight.initialization(raw,sha,**args)
        self.assertFalse(any(q['code']=='PHASE_RECOMMENDATION_UNQUALIFIED' for q in report['issues']))
        self.assertFalse(report['production_ready'])
        for invalid in ('missing',True,'5',None):
            changed=deepcopy(value)
            if invalid=='missing':del changed['configuration']['delivery']['batch'][phase.TOLERANCES[1]]
            else:changed['configuration']['delivery']['batch'][phase.TOLERANCES[1]]=invalid
            bad_raw,bad_sha,bad_args=encoded(changed)
            self.assertFalse(preflight.initialization(bad_raw,bad_sha,**bad_args)['stage_eligibility']['day'])
        value['opening']['state']['dbm']['PhaseOutRecommendation']=phase.phase_recommendation(TODAY,population(),30,0)['PhaseOutRecommendation']
        raw,sha,args=encoded(value)
        with self.assertRaisesRegex(ValueError,'cannot seed phase'):decode(raw,sha,**args)


if __name__=='__main__':unittest.main()
