"""BTR history source mapping, exact dispatch, typed carry and denials."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date,timedelta
import json,os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','btr-history-unit-only')
import django
django.setup()
from mta.domain import btr_rationing_history as history, btr_finalization as btr
from mta.temporal.chain import connected_btr_stages
from mta.runtime import relational_state as typed, btr_history_storage as schema
from mta.serialization import storage
from mta.application.r1_rationed_report import rationed_report
from mta.application.complete_daily_inputs import supplier_dispatch
from mta.domain.complete_daily_scalars import ascii_equal
from mta.planning.engine import calculate_current_day

TODAY='2026-01-15';YESTERDAY='2026-01-14';TOMORROW='2026-01-16'


def report(**overrides):
    value={c['name']:('0.00' if c['type']=='decimal' else False if c['type']=='bit' else
        0 if c['type']=='int' else None) for c in history.COLUMNS if c['name'] in history.SOURCE_FIELDS}
    value.update(SKUCode='S',WhCode='W',ParentWhCode='P',SKUName='source sku',WhName='source W',
        Norm=10,Stock=20,GIT=13,DispatchPen='125.00',DispatchColor='Black',RationedReq=6)
    value.update(overrides)
    return value


def closing(day=YESTERDAY,**overrides):
    value={n:day if n=='ReportDate' else history.INSERT_LITERALS[n] if n in history.INSERT_LITERALS
        else None if n in history.OMITTED else report()[n] for n in history.FIELDS}
    value.update({'GIT':10,**overrides})
    return value


def daily(day=TODAY,**overrides):
    return dict(SKUCode='S',WHCode='W',ReportDate=day,Receipts=4,Consumption=3,**overrides)


def vf(value='1'):
    return dict(Parameter='CaptureDispatchExecutionEfficiency',Value=value,Description='explicit owner')


def delivery(enabled=True,horizon=30,owner=None):
    settings=dict(CaptureDispatchExecutionEfficiency=int(enabled),GenerateColorAgeingReport=0,
        BRAgeColorTolerance=1,CARNoColorToleranceDuration=2,NormSuggestion_Upward='3',NormSuggestion_Downward='4')
    if enabled:settings['RationingHistoryHorizonBTR']=horizon
    value=dict(btr_settings=settings)
    if owner is not None or enabled:value['btr_history']=dict(importer_vf_settings=[vf()] if owner is None else owner)
    return value


def dispatch(value,report_rows,daily_rows,supplier_rows,config=None,today=TODAY,facts=None):
    config=delivery() if config is None else config
    source={n:[] for n in btr.FACT_TABLES}
    source.update(vf_RationedReqReport=report_rows,DailyConsumption=[dict(SKUCode='S',WhCode='W',Receipts=999)],
                  **({} if facts is None else facts))
    prior={n:[] for n in btr.PRIOR_TABLES};prior['RationingHistory']=value
    # Isolate only the existing downstream trend computations. Actual daily
    # BTR dispatch and history producer execute, with no full business-day claim.
    with ExitStack() as stack:
        for name in ('_import_bpr','_generate_trends','_colour_age','_norm_suggestions','_categories'):
            stack.enter_context(patch.object(btr,name,side_effect=lambda *a:a[1]))
        for name in ('_update_br_age','_availability','_snapshot','_count_graph','_chronic'):
            stack.enter_context(patch.object(btr,name,side_effect=lambda *a:a[0]))
        return list(connected_btr_stages(today,prior,source,config,bpr_daily=daily_rows,
                    supplier_dispatch_req=supplier_rows))


class HistoryTests(unittest.TestCase):
    def test_enabled_actual_dispatch_first_before_import_and_complete_fields(self):
        prior=[closing()];before=deepcopy(prior)
        stages=dispatch(prior,[report()],[daily()],[dict(SKUCode='S',WHCode='W',DispatchReq=7),
                    dict(SKUCode='s ',WHCode='w ',DispatchReq=5)])
        self.assertEqual(stages[0][0],history.STAGE)
        self.assertEqual(stages[1][0],'1. Import BPR.sql')
        rows=stages[-1][1]['RationingHistory']
        self.assertEqual(rows[0]['Dispatch'],7)
        self.assertEqual(tuple(rows[1]),history.FIELDS);self.assertEqual(len(rows[1]),69)
        self.assertEqual((rows[1]['Receipts'],rows[1]['Consumption'],rows[1]['SupplierDispatchReq']),(4,3,12))
        self.assertEqual((rows[1]['Dispatch'],rows[1]['WhType'],rows[1]['ParentWhType']),(None,None,None))
        self.assertEqual((rows[1]['DispatchPen'],rows[1]['DispatchColor']),('125.00','Black'))
        self.assertEqual(prior,before)

    def test_literal_cutoff_today_replacement_future_and_null_date_retention(self):
        cutoff=(date.fromisoformat(TODAY)-timedelta(days=30)).isoformat()
        prior=[closing(cutoff),closing('2025-12-17'),closing(TODAY),closing('2026-01-20'),closing(None)]
        rows=history.collect(TODAY,prior,[report()],[],[],30)
        self.assertEqual([r['ReportDate'] for r in rows],['2025-12-17','2026-01-20',None,TODAY])
        for horizon in (0,-1):
            rows=history.collect(TODAY,prior,[report()],[],[],horizon)
            self.assertEqual([r['ReportDate'] for r in rows],['2026-01-20',None,TODAY])
        for horizon in (-(2**31),2**31-1):
            with self.assertRaises(ValueError):history.collect(TODAY,prior,[],[],[],horizon)

    def test_exact_previous_calendar_date_no_latest_fallback_and_global_negative_clamp(self):
        prior=[closing('2026-01-13'),closing(GIT=100),closing(None,Dispatch=-9)]
        rows=history.collect(TODAY,prior,[report()],[],[],30)
        self.assertIsNone(rows[0]['Dispatch']);self.assertEqual(rows[1]['Dispatch'],0)
        self.assertEqual(rows[2]['Dispatch'],0);self.assertIsNone(rows[3]['Dispatch'])

    def test_empty_report_does_not_invent_dispatch_or_matching_daily_or_supplier(self):
        prior=[closing()]
        self.assertEqual(history.collect(TODAY,prior,[],[daily()],[dict(SKUCode='S',WHCode='W',DispatchReq=5)],30),prior)
        rows=history.collect(TODAY,prior,[report(WhCode='OTHER')],[daily()],[],30)
        self.assertEqual((rows[-1]['Receipts'],rows[-1]['Consumption'],rows[-1]['SupplierDispatchReq']),(0,0,0))
        self.assertIsNone(rows[0]['Dispatch'])

    def test_duplicate_bags_and_equal_updates_remain_distinct_occurrences(self):
        rows=history.collect(TODAY,[closing(),closing()],[report(),report()],
            [daily(),dict(daily(),SKUCode='s ',WHCode='w ')],[],30)
        self.assertEqual(len(rows),4)
        self.assertEqual([r['Dispatch'] for r in rows],[7,7,None,None])
        # An unrelated SKU must not introduce an UPDATE-source conflict.
        rows=history.collect(TODAY,[closing()],[report(GIT=13),report(SKUCode='OTHER',GIT=14)],
            [daily(),dict(daily(),SKUCode='OTHER',Receipts=3)],[],30)
        self.assertEqual(rows[0]['Dispatch'],7)
        rows=history.collect(TODAY,[closing()],[report()],
            [daily(),dict(daily(),SKUCode='OTHER',Receipts=3),dict(daily(),SKUCode='OTHER',Receipts=99)],[],30)
        self.assertEqual(rows[0]['Dispatch'],7)

    def test_conflicting_updates_deny_the_whole_producer_without_mutating_inputs(self):
        for reports,days in (([report()],[daily(),dict(daily(),Receipts=99)]),
                             ([report(),report(GIT=14)],[daily()])):
            prior=[closing()];before=deepcopy((prior,reports,days))
            with self.assertRaisesRegex(ValueError,'SOURCE_ORDER_AMBIGUITY'):
                history.collect(TODAY,prior,reports,days,[],30)
            self.assertEqual((prior,reports,days),before)

    def test_supplier_null_sum_multiplicity_and_zero_denominator_fields_are_unchanged(self):
        row=report(Req=0,RationedReq=0,Norm=0)
        for suppliers,expected in (([],0),([None],None),([None,7,7],14)):
            source=[dict(SKUCode='S',WHCode='W',DispatchReq=v) for v in suppliers]
            current=history.collect(TODAY,[],[row],[],source,30)[0]
            self.assertEqual(current['SupplierDispatchReq'],expected)
            self.assertEqual((current['Req'],current['RationedReq'],current['Norm']),(0,0,0))
            self.assertEqual(current['DispatchPen'],'125.00')

    def test_arithmetic_target_and_aggregate_overflow_deny_atomically(self):
        scenarios=[([closing(GIT=-1)],[report(GIT=2**31-1)],[],[]),
            ([closing(GIT=0)],[report(GIT=2**31-1)],[dict(daily(),Receipts=1)],[]),
            ([],[report()],[],[dict(SKUCode='S',WHCode='W',DispatchReq=v) for v in (2**31-1,1)]),
            ([],[report(ParentWhCode=None)],[],[]),( [],[report(SKUName='x'*126)],[],[]),
            ([],[report(DispatchPen='100000000.00')],[],[])]
        for previous,reports,days,suppliers in scenarios:
            before=deepcopy((previous,reports,days,suppliers))
            with self.assertRaises(ValueError):history.collect(TODAY,previous,reports,days,suppliers,30)
            self.assertEqual((previous,reports,days,suppliers),before)
        for values in ((2**31-1,-1,1),(2**31-1,1,-1)):
            suppliers=[dict(SKUCode='S',WHCode='W',DispatchReq=v) for v in values]
            with self.assertRaisesRegex(ValueError,'SUM accumulation overflow'):
                history.collect(TODAY,[],[report()],[],suppliers,30)

    def test_activation_exact_count_owned_projection_missing_owner_and_inactive_regression(self):
        self.assertTrue(history.configuration(delivery()['btr_settings'],[vf()]))
        self.assertFalse(history.configuration(delivery(False)['btr_settings'],[vf(),vf()]))
        self.assertFalse(history.configuration(delivery(False)['btr_settings'],[]))
        for owner in (None,[],[vf(),vf()]):
            with self.assertRaises(ValueError):history.configuration(delivery()['btr_settings'],owner)
        for missing in ('daily','supplier'):
            with self.assertRaisesRegex(ValueError,'owner populations'):
                dispatch([],[report()],None if missing=='daily' else [],None if missing=='supplier' else [])
        prior=[closing(Dispatch=9)]
        stages=dispatch(prior,[report()],None,None,delivery(False))
        self.assertEqual(stages[0][0],'1. Import BPR.sql')
        self.assertEqual(stages[-1][1]['RationingHistory'],prior)

    def test_current_date_owner_is_not_an_implicit_or_latest_default(self):
        facts={n:[] for n in btr.FACT_TABLES};facts['vf_RationedReqReport']=[report()]
        prior={n:[] for n in btr.PRIOR_TABLES};prior['RationingHistory']=[]
        for value in (None,[],[dict(LastRunDate=YESTERDAY+'T00:00:00')],
                      [dict(LastRunDate=TODAY+'T00:00:00')]*2):
            facts['LastBatchRunTbl']=value
            with self.assertRaisesRegex(ValueError,'singleton current date'):
                list(btr.btr_stages(TODAY,prior,facts,delivery()['btr_settings'],importer_vf_settings=[vf()]))


class ConnectedStorageTests(unittest.TestCase):
    def test_actual_calculation_rationed_and_supplier_producers_feed_dispatch_history(self):
        raw=json.loads((Path(__file__).resolve().parents[1]/'mta/fixtures/r1_season_current_day.json').read_text())
        # Explicit finite shortage boundary: retain catalogue/rules, admit the
        # two supplying roots and give GP one stock unit for actual allocation.
        raw['replenishment_exclusions']=[]
        for row in raw['foundation']['inventory_positions']:
            row['stock_quantity']=1 if row['location_code']=='R1-GP' else 0
        for row in raw['stock_openings']:
            row['stock']=1 if row['location_code']=='R1-GP' else 0
        calculated=calculate_current_day(raw,defer_pick=True)
        reports=rationed_report(raw,calculated,[dict(sku_code='R1SKU',description='Source item')],
            [dict(location_code=r['location_code'],description=r['location_code']) for r in raw['foundation']['locations']])
        masters=[dict(SKUCode=r['sku_code'],WHCode=r['location_code'],ParentWhCode=r['parent_location_code'])
                 for r in calculated['r1_bpr_master']]
        attrs=[dict(SKUCode=r['SKUCode'],LocCode=r['WHCode'],**{f'c{i}':None for i in range(1,16)}) for r in masters]
        supplier,_=supplier_dispatch(sourcing=raw['sourcing'],bor=calculated['r1_bor'],bpr_master=masters,
                                     sku_loc_attributes=attrs,equal=ascii_equal)
        days=[dict(SKUCode=r['SKUCode'],WHCode=r['WhCode'],ReportDate=TODAY,Receipts=2,Consumption=3) for r in reports]
        current=dispatch([],reports,days,supplier)[-1][1]['RationingHistory']
        self.assertTrue(any(r['RationedReq']>0 for r in current))
        self.assertEqual([r['RationedReq'] for r in current],[r['RationedReq'] for r in reports])
        for row in current:
            expected=sum(r['DispatchReq'] for r in supplier if (r['SKUCode'],r['WHCode'])==(row['SKUCode'],row['WhCode']))
            self.assertEqual(row['SupplierDispatchReq'],expected)
        self.assertTrue(supplier)

    def test_complete_typed_closing_readback_then_own_next_date_dispatch(self):
        rows=history.collect(TODAY,[closing()],[report()], [daily()],[],30)
        run=SimpleNamespace(pk='241f8877-d38b-47bc-8850-e0319b294aa8');path='closing/btr/RationingHistory';records=[]
        with patch.object(typed,'bulk',side_effect=lambda query,values:records.extend(values)):
            meta=typed.save_image(run,path,path,storage(rows))
        cursor=MagicMock();cursor.fetchmany.side_effect=[[tuple(r[2:]) for r in records],[]]
        with patch.object(typed.connection,'cursor') as context:
            context.return_value.__enter__.return_value=cursor
            own=typed.load_image(run,meta)
        self.assertEqual(own,storage(rows));self.assertEqual(cursor.execute.call_args.args[1],[run.pk,path])
        next_rows=history.collect(TOMORROW,own,[report(GIT=20)],[dict(daily(TOMORROW),Receipts=2)],[],30)
        self.assertEqual([r['Dispatch'] for r in next_rows],[7,9,None])

    def test_input_namespace_closing_binding_and_initial_answer_denial(self):
        from mta.runtime.input_storage import choose_table
        from mta.runtime.production_daily import input_table
        rows=[closing()]
        self.assertEqual(choose_table(history.FIELDS,schema.FROZEN,rows),schema.TABLE)
        self.assertEqual(input_table((),schema.FROZEN,[]),schema.TABLE)
        from mta.runtime.input_storage import save_input
        for population in ([],rows):
            run=SimpleNamespace(pk='71f27608-f8b3-4c60-af39-6228d5c79182',input_digest='component-only')
            source=dict(opening=dict(state=dict(btr=dict(RationingHistory=population))))
            source['profile']=dict(delivery=dict(site_code='component-only'))
            with patch.object(typed,'bulk'):
                manifest=save_input(run,source,table_selector=input_table)
            self.assertIn(schema.FROZEN,manifest['images'])
            self.assertNotIn(schema.OPENING,manifest['images'])
            self.assertEqual(manifest['images'][schema.FROZEN]['table'],schema.TABLE)
        schema.validate_write(schema.FROZEN,None,rows)
        for image,binding in ((schema.OPENING,None),('closing/dbm/RationingHistory',None),
                               ('closing/btr/RationingHistory','closing/dbm/RationingHistory')):
            with self.assertRaises(ValueError):schema.validate_write(image,binding,rows)
        from tests.production_daily_fixture import initialized_input
        from tests.initialization_input_fixture import encoded
        from mta.mdm.initialization_contract import decode
        value=initialized_input();raw,sha,args=encoded(value)
        frame=decode(raw,sha,**args)[1]
        self.assertEqual(frame['opening']['state']['btr']['RationingHistory'],[])
        value['opening']['state']['btr']['RationingHistory']=rows
        raw,sha,args=encoded(value)
        with self.assertRaisesRegex(ValueError,'seed calculated rationing history'):decode(raw,sha,**args)

    def test_enabled_native_preflight_requires_explicit_owner_horizon_and_keeps_readiness_false(self):
        from tests.production_daily_fixture import initialized_input
        from tests.initialization_input_fixture import encoded
        from mta.runtime.production_preflight import initialization
        value=initialized_input();value['configuration']['delivery'].update(delivery())
        raw,sha,args=encoded(value);report=initialization(raw,sha,**args)
        self.assertTrue(report['stage_eligibility']['installation'],report['issues'])
        self.assertFalse(report['production_ready'])
        self.assertFalse(any(r['code']=='BTR_HISTORY_MODE_UNQUALIFIED' for r in report['issues']))
        for name in ('RationingHistoryHorizonBTR','owner'):
            broken=deepcopy(value)
            if name=='owner':del broken['configuration']['delivery']['btr_history']
            else:del broken['configuration']['delivery']['btr_settings'][name]
            raw,sha,args=encoded(broken);report=initialization(raw,sha,**args)
            self.assertFalse(report['stage_eligibility']['installation'])


if __name__=='__main__':unittest.main()
