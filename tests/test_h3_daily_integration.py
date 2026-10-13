"""Coupled pure H3 producers and exact carry; no execute_day or accepted run."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','h3-coupled-component-only')
import django
django.setup()

from tests.production_h3_fixture import supplied_input,supplied_day,PHASE,PHASE_IN,SEASON,CHILD,ROOT,PARENT
from tests.initialization_input_fixture import encoded
from tests.test_mdm_daily_input import snapshot as base_capture
from mta.mdm.initialization_contract import decode
from mta.mdm.daily_input import compose,nms_master_raw
from mta.mdm.supplier_capture import complete_feeds
from mta.mdm.integration_source import replace_working_inputs
from mta.domain.elephant_orders import apply_due_dates
from mta.temporal.chain import calculate_day
from mta.planning.engine import calculate_current_day
from mta.evidence import evidence_mode
from mta.serialization import digest,storage
from mta.runtime import relational_state as typed


def frame(fmt='WithDestLoc'):
    value=supplied_input(moq_format=fmt);raw,sha,args=encoded(value)
    return decode(raw,sha,**args)[1]


def captured(prior,fmt,*,parent=None,positive=True,stop=False):
    s=base_capture();master=prior['importer']
    for family,kind,name in (('sku','attributes','SkuAttributeData'),('sku','descriptions','SKUDescriptionTbl'),
            ('location','attributes','LocationAttributeData'),('location','descriptions','SiteDescriptionTbl'),
            ('skuloc','attributes','SkuLocAttributeData')):
        s['rows'][family][kind]=[dict(id=i,**row) for i,row in enumerate(master[name],1)]
    root_digest=digest(prior)
    anchor=dict(run_id=parent.pk if parent else None,output_digest=parent.output_digest if parent else '',
                root_state_digest=root_digest,generation=0)
    def seal(value):return dict(value,digest=digest(value))
    s['force']=seal(dict(source_digest='f'*64,anchor=dict(anchor,
        queue_digest=digest(prior['importer']['ForceNormChange']),log_digest=digest(prior['controls']['upload_log'])),
        rows=[dict(id=1,revision=0,SKUCode='SUPPLIED-Z9',WhCode=CHILD,NewNorm=18,Approved=True,RequestedBy='component-proof')]
             if positive else [],upload_log=[],task_revisions=[]))
    season=dict(SKUCode=SEASON,WhCode=CHILD,StartDate='2037-04-10',EndDate='2037-04-15',
        TargetNorm=24,DeltaNormPercentage=None,UpperLowerCap=None,BuildupDuration=2,ActivateDBM=False,Approved=True)
    s['season']=seal(dict(source_digest='a'*64,anchor=dict(anchor,
        queue_digest=digest(prior['control_aux']['season_requests']),current_digest=digest(prior['dbm']['Seasonality'])),
        rows=[dict(id=1,revision=0,**season)] if positive else [],
        current=[dict(id=i,revision=0,**row) for i,row in enumerate(prior['dbm']['Seasonality'],1)],task_revisions=[]))
    s['stop_pipo']=seal(dict(source_digest='b'*64,anchor=dict(anchor,queue_digest=digest(prior['control_aux']['phase_stops'])),
        rows=[dict(id=1,revision=0,SKUCode=PHASE,WhCode=CHILD)] if stop else [],task_revisions=[]))
    queues={name:prior['control_aux'][name] for name in ('phase_requests','phase_in_requests')}
    s['phase_controls']=seal(dict(source_digest='c'*64,anchor=dict(anchor,queue_digest=digest(queues)),
        phase_requests=[dict(id=1,revision=0,SKUCode=PHASE,WhCode=CHILD,PhaseInSKUCode=PHASE_IN,Approved=True)] if positive else [],
        phase_in_requests=[dict(id=1,revision=0,SKUCode=PHASE_IN,WhCode=CHILD,TargetNorm=18,Approved=True)] if positive else [],task_revisions=[]))
    sob=[dict(id=1,revision=0,SKUCode='SUPPLIED-Z9',WhCode=PARENT,SupplierCode=ROOT,
        SOB=75.0,ActionType=1,Approved=True,Reverted=False)] if positive else []
    moq=[dict(id=1,revision=0,SKUCode='SUPPLIED-Z9',SupplierCode=ROOT,MOQ=2,ActionType=1,Approved=True,Reverted=False,
        **({'WhCode':PARENT} if fmt=='WithDestLoc' else {}))] if positive else []
    s['supplier']=seal(dict(moq_format=fmt,source_digest='d'*64,
        raw={name:deepcopy(prior['complete'][name]) for name in ('SOBDataRaw','MOQDataRaw1','MOQDataRaw2')},
        queues=dict(NMSSOB=sob,NMSMOQWithDestination=moq if fmt=='WithDestLoc' else [],
                    NMSMOQWithoutDestination=moq if fmt=='WithoutDestLoc' else []),pending=[],task_revisions=[]))
    s.pop('revision_digest');s['revision_digest']=digest(s)
    return s


def coupled(profile,prior,opening,today,*,fmt='WithDestLoc',parent=None,positive=True,stop=False,observe=None):
    day=supplied_day(today)['day'];working=deepcopy(prior)
    frozen=captured(working,fmt,parent=parent,positive=positive,stop=stop)
    day.update(raw_master=compose(frozen,nms_master_raw(working),last_run_date=opening),exclusions=[],
               supplier_feeds=complete_feeds(frozen,working))
    replace_working_inputs(frozen,working,day,parent)
    def calculate(source,**owned):
        if observe is not None:observe(source,owned)
        return calculate_current_day(source,defer_pick=True,**owned),'pure-component-'+today
    with evidence_mode('production'):
        result=calculate_day(working,opening,day,profile,'pure-component-'+today,
            calculate,native_daily=True)
    return result,frozen


class CoupledDailyTests(unittest.TestCase):
    def test_actual_completion_gate_after_consumption_before_typed_publication(self):
        from contextlib import nullcontext
        from mta.runtime.services import finish_run
        from mta.application.daily_finalization import verify_successor
        f=frame();result,_=coupled(f['profile'],f['opening']['state'],'2037-04-09','2037-04-10')
        # The runtime transfers the producer's metadata into its owned lineage
        # before finish_run; retain exactly that metadata for this component gate.
        result['Lineage']=[dict(cohort1=result.pop('_Cohort1'))]
        frozen=dict(profile=f['profile']);events=[]
        class PublicationBoundary(Exception):pass
        def publish(run,capture,closing):
            events.append('current')
            self.assertTrue(capture.nms_active)
        def stop_before_storage(*args):
            events.append('typed-storage')
            verify_successor(output,f['profile'],'2037-04-10')
            raise PublicationBoundary()
        for case in ('positive','unconsumed','missing-producer'):
            events.clear();output=deepcopy(result)
            if case=='missing-producer':
                next(r for r in output['ClosingState'][0]['complete']['ScriptExecutedFlag']
                    if r['ScriptName']=='GenerateBPR.sql')['IsScriptExecuted']=False
                output['Lineage'][0]['cohort1']['flag_digest']=digest(output['ClosingState'][0]['complete']['ScriptExecutedFlag'])
            run=SimpleNamespace(pk='component',status='RUNNING',kind='DAILY_CHAIN',checkpoints=MagicMock(),
                input_payload={},input_digest=digest(frozen),business_date=date(2037,4,10))
            run.checkpoints.exists.return_value=False
            with self.subTest(case=case), \
                    patch('mta.runtime.services.transaction.atomic',return_value=nullcontext()), \
                    patch('mta.runtime.services.CalculationRun.objects') as runs, \
                    patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects') as captures, \
                    patch('mta.runtime.services.read_input',return_value=frozen), \
                    patch('mta.mdm.daily_input.finalize_consumption',side_effect=lambda *a,**k:events.append('consume')), \
                    patch('mta.mdm.daily_current.publish',side_effect=publish), \
                    patch('mta.runtime.relational_state.save_daily',side_effect=stop_before_storage):
                runs.select_for_update.return_value.get.return_value=run
                captures.filter.return_value.values_list.return_value.first.return_value=None
                captures.filter.return_value.exists.return_value=case!='unconsumed'
                captures.get.return_value=SimpleNamespace(nms_active=True)
                captures.select_related.return_value.get.return_value=SimpleNamespace(nms_active=True,
                    source=SimpleNamespace(receipt={'schema':'fresh-production-mdm-source-v1'}))
                if case=='positive':
                    with self.assertRaises(PublicationBoundary):finish_run(run,output,expected_digest=run.input_digest)
                    self.assertEqual(events,['consume','current','typed-storage'])
                else:
                    with self.assertRaisesRegex(ValueError,'not consumed' if case=='unconsumed' else 'completion failed'):
                        finish_run(run,output,expected_digest=run.input_digest)
                    self.assertEqual(events,['consume'])
                self.assertEqual(run.status,'RUNNING')

    def test_positive_supplier_modules_force_season_phase_orders_and_btr_own_carry(self):
        for fmt in ('WithDestLoc','WithoutDestLoc'):
            f=frame(fmt);prior=f['opening']['state'];before=deepcopy(prior)
            result,frozen=coupled(f['profile'],prior,'2037-04-09','2037-04-10',fmt=fmt)
            closing=storage(result['ClosingState'][0])
            from mta.runtime.production_preflight import Requirements,closing_shape
            requirements=Requirements('day');closing_shape(requirements,closing)
            self.assertEqual(requirements.issues,[])
            self.assertEqual(prior,before)
            norms={(r['SKUCode'],r['WhCode']):r['Norm'] for r in closing['dbm']['DBMMaster']}
            self.assertEqual(norms['SUPPLIED-Z9',CHILD],18)
            self.assertEqual(norms[SEASON,CHILD],24)
            self.assertTrue(closing['dbm']['PhaseOutTbl']);self.assertTrue(closing['dbm']['PhaseInTbl'])
            self.assertEqual(closing['control_aux']['phase_requests'],[])
            self.assertEqual(closing['control_aux']['season_requests'],[])
            self.assertEqual(closing['importer']['ForceNormChange'],[])
            self.assertEqual(closing['complete']['SOBDataRaw'][0]['SOB'],75.0)
            raw_name='MOQDataRaw2' if fmt=='WithDestLoc' else 'MOQDataRaw1'
            self.assertEqual(closing['complete'][raw_name][0]['MOQ'],2)
            self.assertTrue(closing['complete']['LogisticPickList'])
            self.assertTrue(closing['complete']['SupplierDispatchReq'])
            self.assertEqual([r['CustomerOrderID'] for r in closing['orders']['ElephantOrders']],['ELEPHANT-Z','ELEPHANT-A'])
            self.assertEqual([r['OrderKey'] for r in closing['orders']['SpikeOrderData']],[2,3])
            self.assertTrue(closing['orders']['SpikeOrderData'][1]['IsSpike'])
            self.assertEqual(len(closing['btr']['RationingHistory']),8)
            self.assertTrue(all(r['Dispatch'] is None for r in closing['btr']['RationingHistory']))
            self.assertEqual({r['WHCode'] for r in closing['bpr']['DailyConsumption']},
                {CHILD,'OWN-DIST','OWN-DMS','OWN-VENDOR',PARENT,ROOT})
            # Actual encoded image values (including duplicate ordinals) are the
            # second calculation's opening; no future expected outputs are seeded.
            own=deepcopy(closing);run=SimpleNamespace(pk='0188e62c-e514-4432-b43f-e1c3489c1500')
            for section,names in (('orders',('ElephantOrders','SpikeOrderData','OrderIdentity')),
                ('btr',('RationingHistory','ExpediteDispatches')),('supplier',('SOBData','MOQData')),
                ('controls',('log','phase_in','phase_out')),
                ('dbm',('PhaseOutTbl','PhaseInTbl','Seasonality'))):
                for name in names:
                    records=[];path='closing/'+section+'/'+name
                    with patch.object(typed,'bulk',side_effect=lambda sql,values:records.extend(values)):
                        meta=typed.save_image(run,path,path,closing[section][name])
                    cursor=MagicMock();cursor.fetchmany.side_effect=[[tuple(r[2:]) for r in records],[]]
                    with patch.object(typed.connection,'cursor') as context:
                        context.return_value.__enter__.return_value=cursor
                        own[section][name]=typed.load_image(run,meta)
                    self.assertEqual(own[section][name],closing[section][name])
            own['orders']=apply_due_dates(own['orders'],[dict(OrderID=oid,SKUCode='SUPPLIED-Z9',WhCode=CHILD,DueDate='2037-04-14')
                for oid in ('ELEPHANT-Z','ELEPHANT-A')])
            parent=SimpleNamespace(pk='pure-component-2037-04-10',output_digest=digest(closing))
            observed=[]
            def check_owned_guard(source,owned):
                from mta.application.r1_input import validate_r1_raw_input,prepare_owned_order_current_day
                self.assertEqual(source['schema'],'r1-current-day-input-v5')
                with self.assertRaisesRegex(ValueError,'Elephant order requires'):
                    validate_r1_raw_input(source)
                bad=deepcopy(source);bad['orders'][0]['outstanding_quantity']+=1
                with self.assertRaisesRegex(ValueError,'projection drift'):
                    prepare_owned_order_current_day(bad,owned['_owned_order_closing'])
                observed.append(True)
            second,_=coupled(f['profile'],own,'2037-04-10','2037-04-11',fmt=fmt,parent=parent,
                positive=False,stop=True,observe=check_owned_guard)
            self.assertEqual(observed,[True])
            final=storage(second['ClosingState'][0])
            requirements=Requirements('day');closing_shape(requirements,final)
            self.assertEqual(requirements.issues,[])
            self.assertEqual(final['orders']['ElephantOrders'],[])
            self.assertEqual([(r['CustomerOrderId'],r['OrderKey']) for r in final['orders']['SpikeOrderData']],
                [('ORDINARY',2),('SPIKE',3),('ELEPHANT-Z',4),('ELEPHANT-A',5)])
            self.assertEqual(final['dbm']['PhaseOutTbl'],[]);self.assertEqual(final['dbm']['PhaseInTbl'],[])
            history=final['btr']['RationingHistory']
            self.assertEqual(len(history),16)
            self.assertTrue(all(r['Dispatch']==(0 if r['WhCode']==PARENT else 1)
                for r in history if r['ReportDate']=='2037-04-10'))
            self.assertTrue(all(r['Dispatch'] is None for r in history if r['ReportDate']=='2037-04-11'))


if __name__=='__main__':unittest.main()
