"""Focused PostgreSQL connector proofs, not a new calculation/day acceptance."""
from datetime import date, datetime, timezone
from unittest.mock import patch
from django.db import connection, transaction, DatabaseError
from django.test import TestCase, override_settings
from mta.presentation import logistics_read as reader, logistics_live as live
from mta.presentation import daily_requests, daily_transit
from mta.presentation import logistics_commands as commands
from mta.presentation.permissions import PermissionCodes
from mta.runtime.models import (CalculationRun, DailyTransitRow, TransitAnnotation,
    TransitRemarkHistory, ExpediteRemarkHistory)
from mta.runtime.relational_state import quote
from mta.serialization import digest
import json


@override_settings(VF_MTA_LOGISTICS_CURRENT=True)
class LogisticsReadTests(TestCase):
    def setUp(self):
        self.run = CalculationRun.objects.create(kind='DAILY_CHAIN',status='RUNNING',
            business_date='2026-10-18',input_digest=digest('logistics-component'),
            execution_revision='logistics-component-only',input_payload={})
        self.source = [dict.fromkeys(daily_transit.processor.TRANSIT_FIELDS) for _ in range(2)]
        for i,r in enumerate(self.source):
            r.update(SKUCode=str(337+i),WhCode='DP010290',ParentWhCode='DC010001',
                OrderNo='GAP-ORDER',InTransitQty=i+2,GateOutDate='2026-10-17',
                ETA=None,CurrentLocationCode='DC010001')
        self.importer = dict(SkuAttributeData=[dict(SKUCode=r['SKUCode'],SL1='B1Product',SL2='Selected',SL3='Leaf') for r in self.source],
            LocationAttributeData=[dict(WHCode='DP010290',LL1='Location',LL2='Selected',LL3='Leaf',LocationType='DP')])
        self.contacts = [dict(SKUCode=r['SKUCode'],WhCode=r['WhCode'],ParentWhCode=r['ParentWhCode'],
            OrderNo=r['OrderNo'],Ageing=1,PhysicalInventoryColor='Red',TransporterName='Registered carrier',
            TransporterContact=None) for r in self.source for _ in range(2)]
        self.images = {
            daily_transit.PATH:self.source,
            daily_transit.TRANSPORTER_PATH:self.contacts,
            'closing/importer/SkuAttributeData':self.importer['SkuAttributeData'],
            'closing/importer/LocationAttributeData':self.importer['LocationAttributeData'],
            'closing/importer/SkuLocAttributeData':[dict(SKUCode=r['SKUCode'],LocCode=r['WhCode'],c1=None) for r in self.source],
            'closing/importer/SKUDescriptionTbl':[dict(SKUCode=r['SKUCode'],SKUDescription='Registered '+r['SKUCode']) for r in self.source],
            'closing/btr/ExpediteDispatches':[dict(SKUCode='337',WhCode='DP010290',RationedQty=4,
                PipelineInventoryColor='Red',BRAge=3,PotentialLossPerDay=12) for _ in range(2)],
        }
        self.products = PermissionCodes({'337':1,'338':1})
        self.locations = PermissionCodes({'DP010290':1})
        self.patches = [
            patch.object(reader,'_projected_attributes',return_value=(self.importer,None)),
            patch.object(reader,'scope',side_effect=lambda *a,**k:(self.products,self.locations)),
            patch.object(reader,'image_query',side_effect=self.query),
            patch.object(reader,'_dispatch_relation',side_effect=lambda r:self.query(r,'closing/btr/ExpediteDispatches')),
            patch('mta.presentation.selective.image_rows',side_effect=lambda r,p:self.images[p]),
            patch('mta.presentation.selective.image_metadata',side_effect=lambda r,p:dict(digest=digest(self.images[p]))),
        ]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        for i,row in enumerate(self.source):
            DailyTransitRow.objects.create(run=self.run,ordinal=i,**{
                k:date.fromisoformat(v) if k in daily_transit.DATES and v is not None else v for k,v in row.items()})
        live.initialize(self.run,provenance={'component_fixture':'retained-catalogue-logistics'})

    def query(self,run,path):
        rows = self.images[path]
        fields = list(rows[0])
        casts = {name:('bigint' if name in ('InTransitQty','Ageing','RationedQty','BRAge','PotentialLossPerDay')
                     else 'date' if name in daily_transit.DATES else 'text') for name in fields}
        values = [v for i,r in enumerate(rows) for v in (i,*[r[f] for f in fields])]
        placeholders = ','.join(['(%s::bigint,'+','.join('%s::'+casts[f] for f in fields)+')']*len(rows))
        return ('SELECT * FROM (VALUES '+placeholders+') R(vf_ordinal,'+','.join(map(quote,fields))+')',values)

    def test_implicated_parent_reader_is_opt_in_and_preserves_unpaged_restriction(self):
        from mta.presentation import expedite_read, planning_expedite_sql
        from mta.presentation.context import PublicationUnavailable
        with patch.object(expedite_read,'selected_run',return_value=self.run), \
                patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch.object(planning_expedite_sql,'parent_grid',return_value={'target':'typed'}) as prepared:
            self.assertEqual(expedite_read.parent_grid({'paginationParameter':{
                'pageNumber':1,'recordsPerPage':10}}),{'target':'typed'})
            with patch.object(expedite_read,'expedite_context',return_value=object()):
                with self.assertRaisesRegex(PublicationUnavailable,'UNPAGED-SQL156'):
                    expedite_read.parent_grid({})
            with override_settings(VF_MTA_LOGISTICS_CURRENT=False), \
                    patch.object(expedite_read,'expedite_context',side_effect=RuntimeError('original path')):
                with self.assertRaisesRegex(RuntimeError,'original path'):
                    expedite_read.parent_grid({'paginationParameter':{'pageNumber':1,'recordsPerPage':10}})
            self.assertEqual(prepared.call_count,1)

    def test_transit_count_join_multiplicity_nested_outer_correlations_and_nulls(self):
        rows = reader.transit_grid(self.run,{})
        self.assertEqual(len(rows),4)
        self.assertEqual(reader.transit_grid(self.run,{},count=True),4)
        self.assertEqual([r['RN'] for r in rows],[1,2,3,4])
        self.assertEqual({r['Qty'] for r in rows},{10})
        for r in rows:
            self.assertNotIn('ETA',r)
            self.assertEqual(len(r['skuDetails']),2)
            self.assertEqual([x['InTransitQty'] for x in r['skuDetails']],[2,3])
            self.assertEqual({x['SKUDescription'] for x in r['skuDetails']},{r['SKUDescription']})
            self.assertEqual({x['PhysicalInventoryColor'] for x in r['skuDetails']},{'Red'})
        contacts = reader.contacts(self.run,{'orderNo':'GAP-ORDER'})
        self.assertEqual(len(contacts),4)
        self.assertNotIn('TransporterContact',contacts[0])

    def test_grid_filter_paging_permission_weights_and_denied_nested_order(self):
        payload=dict(filters=dict(productFilter=dict(filters=[dict(attributeName='sku',operator='equalto',value='337')])))
        self.assertEqual(reader.transit_grid(self.run,payload,count=True),2)
        self.assertEqual(len(reader.transit_grid(self.run,dict(payload,paginationParameter=dict(pageNumber=1,recordsPerPage=1)))),1)
        self.products = PermissionCodes({'337':2,'338':1})
        self.assertEqual(reader.transit_grid(self.run,{},count=True),6)
        self.products = PermissionCodes({'337':1})
        with self.assertRaises(reader.TargetDenied):reader.transit_grid(self.run,{})
        with self.assertRaises(reader.TargetDenied):reader.transit_history(self.run,{'orderNo':'GAP-ORDER'})

    def test_current_request_duplicate_pair_join_and_frozen_capture(self):
        row = dict.fromkeys(daily_requests.FIELDS)
        row.update(SKUCode='337',WhCode='DP010290',ParentWhCode='DC010001',Request='Need stock',UserId='Registered actor')
        daily_requests.initialize([row,dict(row,ParentWhCode=None)],provenance={'component_fixture':'duplicate requests'})
        daily_requests.bind(self.run,daily_requests.snapshot())
        result=reader.open_requests(self.run,{})
        self.assertEqual(len(result['data']),4)
        self.assertEqual(len(result['uiConfig']),9)
        self.assertEqual({r['qty'] for r in result['data']},{4})
        self.assertEqual(sum('pwc' not in r for r in result['data']),2)
        self.assertEqual(daily_requests.rows(self.run),[row,dict(row,ParentWhCode=None)])

    def test_history_native_actor_types_order_null_projection_and_guards(self):
        owner=live.history_owner()
        generation=live.generation(self.run)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.logistics_command',%s,true)",[live.OWNER])
        stamp=datetime(2026,10,16,9,tzinfo=timezone.utc)
        TransitRemarkHistory.objects.create(owner=owner,ordinal=0,generation=generation,
            OrderNo='GAP-ORDER',Remarks='Location update',UserId=1,RemarksDate=stamp)
        ExpediteRemarkHistory.objects.create(owner=owner,ordinal=1,SKUCode='337',WHCode='DP010290',
            Remark='Expedite',UserId='Registered actor',RemarkDate=stamp)
        result=reader.transit_history(self.run,{'orderNo':'GAP-ORDER'})
        self.assertEqual(result,[dict(Remarks='Location update',RemarksDate='2026-10-16T09:00:00',UserName=1)])
        result=reader.expedite_history(self.run,{'skucode':'337','whcode':'DP010290'})
        self.assertEqual(result,[dict(RN='1',r='Expedite',rd='2026-10-16T09:00:00',UserId='Registered actor',eta='')])
        with self.assertRaises(DatabaseError),transaction.atomic():
            ExpediteRemarkHistory.objects.update(UserId='Replacement')
        with self.assertRaises(DatabaseError),transaction.atomic():
            DailyTransitRow.objects.filter(run=self.run).update(Remark='Changed frozen input')
        with self.assertRaises(DatabaseError),transaction.atomic():
            TransitRemarkHistory.objects.all().delete()
        self.assertEqual(live.retain_history(business_date=date(2026,10,17),horizon=1),(0,0))
        self.assertEqual(live.retain_history(business_date=date(2026,10,18),horizon=1),(1,1))

    def test_overlay_nullable_fields_generation_binding_and_no_carry_to_next_source(self):
        value=live.generation(self.run)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.logistics_command',%s,true)",[live.OWNER])
        TransitAnnotation.objects.create(generation=value,source_ordinal=0,
            CurrentLocationCode=None,ETA=None,Remark='Edited once')
        self.assertIsNone(live.transit_rows(self.run)[0]['CurrentLocationCode'])
        self.assertEqual(live.transit_rows(self.run)[0]['Remark'],'Edited once')
        self.assertIsNone(live.transit_rows(self.run,include_live=False)[0]['Remark'])
        self.images[daily_transit.PATH][0]['Remark']='Source drift'
        with self.assertRaisesRegex(ValueError,'generation_missing_or_changed'):
            live.transit_rows(self.run)

    def test_six_route_envelopes_two_exact_config_aliases_and_gateway_method_gates(self):
        from django.test import RequestFactory
        from django.conf import settings
        from django.urls import resolve
        daily_requests.initialize([],provenance={'component_fixture':'HTTP empty request owner'})
        routes = [('GetInTransitWhereAboutsData',{}),('GetInTransitWhereAboutsDataCount',{}),
            ('GetTransporterDetails',{'orderNo':'GAP-ORDER'}),
            ('GetRemarkDetailsForInTransit',{'orderNo':'GAP-ORDER'}),
            ('GetOpenExpediteRequest',{}),
            ('GetRemarkDetailsForExpedite',{'skucode':'337','whcode':'DP010290'})]
        factory = RequestFactory()
        with patch('mta.presentation.logistics_views.selected_run',return_value=self.run):
            for name,body in routes:
                path='/api/mta/'+name
                callback=resolve(path).func
                request=factory.post(path,json.dumps(body),content_type='application/json')
                self.assertEqual(callback(request).status_code,403)
                request=factory.post(path,json.dumps(body),content_type='application/json',
                    headers={settings.MTA_TRUSTED_GATEWAY_HEADER:json.dumps({'id':1,'name':'Registered actor'})})
                response=callback(request)
                self.assertEqual(response.status_code,200,response.content)
                self.assertEqual(json.loads(response.content)['status'],200)
                self.assertEqual(callback(factory.get(path)).status_code,405)
        callback=resolve('/api/mta/GetUIConfig').func
        for report,n in [('InTransitWhereAbouts',9),('OpenExpeditingRequests',10)]:
            request=factory.get('/api/mta/GetUIConfig',{'reportName':report},
                headers={settings.MTA_TRUSTED_GATEWAY_HEADER:json.dumps({'id':1})})
            columns=json.loads(callback(request).content)['data']
            self.assertEqual(len(columns),n)
            self.assertEqual({r['ReportName'] for r in columns},{report})
            self.assertEqual({r['DataType'] for r in columns},{'String'})

    def transit_command_row(self,**changes):
        row = dict(OrderNo='GAP-ORDER',SKUCode='337',WhCode='DP010290',ParentWHCode='DC010001',
                   Remarks="Driver's update",CurrentLocation='DC010002',ETA='2026/10/20')
        row.update(changes)
        return row

    def test_transit_batch_broad_order_current_history_actor_date_and_frozen_source(self):
        first=self.transit_command_row(); second=dict(first,SKUCode='338',Remarks='Second input',ETA='')
        frozen=list(DailyTransitRow.objects.filter(run=self.run).order_by('ordinal').values())
        stamp=datetime(2026,10,16,11,12,13,tzinfo=timezone.utc)
        with patch.object(commands,'_now',return_value=stamp):
            commands.submit_transit(self.run,dict(data=[first,second],user={'id':999}),{'id':1,'name':'Registered actor'})
        rows=live.transit_rows(self.run)
        self.assertEqual({r['Remark'] for r in rows},{'Second input'})
        self.assertEqual({r['ETA'] for r in rows},{'1900-01-01'})
        history=list(TransitRemarkHistory.objects.order_by('ordinal').values())
        self.assertEqual([r['SKUCode'] for r in history],['337','338'])
        self.assertEqual([r['Remarks'] for r in history],["Driver's update",'Second input'])
        self.assertEqual({r['UserId'] for r in history},{1})
        self.assertEqual({r['RemarksDate'] for r in history},{stamp})
        self.assertEqual(list(DailyTransitRow.objects.filter(run=self.run).order_by('ordinal').values()),frozen)
        self.assertEqual(live.generation(self.run).revision,1)
        self.assertEqual(live.history_owner().next_ordinal,2)

    def test_transit_denied_sibling_and_late_storage_error_roll_back_every_effect(self):
        payload=dict(data=[self.transit_command_row()])
        self.products=PermissionCodes({'337':1})
        with self.assertRaises(reader.TargetDenied):
            commands.submit_transit(self.run,payload,{'id':1,'name':'Registered actor'})
        self.assertFalse(TransitRemarkHistory.objects.exists())
        self.products=PermissionCodes({'337':1,'338':1})
        create=TransitRemarkHistory.objects.create
        def fail_second(**kwargs):
            if kwargs['ordinal']==1:raise DatabaseError('injected later history failure')
            return create(**kwargs)
        with patch.object(TransitRemarkHistory.objects,'create',side_effect=fail_second):
            with self.assertRaises(DatabaseError):
                commands.submit_transit(self.run,dict(data=payload['data']*2),{'id':1})
        self.assertFalse(TransitRemarkHistory.objects.exists())
        self.assertFalse(TransitAnnotation.objects.exists())
        self.assertEqual(live.history_owner().revision,0)
        self.assertEqual(live.generation(self.run).revision,0)

    def test_expedite_new_update_action_duplicate_targets_history_and_next_capture(self):
        from mta.runtime.models import DailyOpenRequest
        row=dict.fromkeys(daily_requests.FIELDS)
        row.update(SKUCode='337',WhCode='DP010290',ParentWhCode='DC010001',
            Request='Initial',UserId='Earlier actor',ETA='2026-10-19T07:08:09')
        daily_requests.initialize([row,dict(row,ParentWhCode=None)],provenance={'component_fixture':'requests'})
        frozen=daily_requests.snapshot();daily_requests.bind(self.run,frozen)
        actor={'id':1,'name':'Registered actor'}
        commands.submit_request(self.run,dict(skuCode='337',whCode='DP010290',parentWhCode='Other',
            request="Buyer's request",eta='ignored on existing pair'),actor)
        current=list(DailyOpenRequest.objects.order_by('ordinal'))
        self.assertEqual([r.ParentWhCode for r in current],['DC010001',None])
        self.assertEqual({r.Request for r in current},{"Buyer's request"})
        self.assertEqual({r.ETA.isoformat() for r in current},{'2026-10-19T07:08:09+00:00'})
        commands.submit_request(self.run,dict(skuCode='338',whCode='DP010290',parentWhCode='DC010001',
            request='New request',eta=''),actor)
        new=DailyOpenRequest.objects.get(ordinal=2)
        self.assertIsNone(new.ETA);self.assertIsNone(new.Action)
        self.assertEqual(new.UserId,'Registered actor')
        count=commands.add_expedite_remark(self.run,dict(data=[dict(SKUCode='337',WHCode='DP010290',
            Remark='Contacted',ETA='2026-10-20T11:23:45')]),actor)
        self.assertEqual(count,'3')
        current=list(DailyOpenRequest.objects.filter(SKUCode='337'))
        self.assertEqual({r.ETA.isoformat() for r in current},{'2026-10-20T00:00:00+00:00'})
        self.assertEqual({r.Action for r in current},{'Contacted'})
        history=list(ExpediteRemarkHistory.objects.order_by('ordinal'))
        self.assertEqual([r.Remark for r in history],["Buyer's request",'New request','Contacted'])
        self.assertEqual([r.ETA.isoformat() if r.ETA else None for r in history],[None,None,'2026-10-20T11:23:45+00:00'])
        self.assertEqual({r.UserId for r in history},{'Registered actor'})
        self.assertEqual(daily_requests.rows(self.run),[row,dict(row,ParentWhCode=None)])
        future=daily_requests.snapshot()
        self.assertEqual(future['revision'],3)
        self.assertEqual(len(future['rows']),3)
        self.assertEqual(future['rows'][0]['Action'],'Contacted')

    def test_expedite_denied_batch_invalid_eta_and_storage_failure_are_atomic(self):
        from mta.runtime.models import DailyOpenRequest
        daily_requests.initialize([],provenance={'component_fixture':'empty requests'})
        actor={'id':1,'name':'Registered actor'}
        with patch.object(ExpediteRemarkHistory.objects,'create',side_effect=DatabaseError('history unavailable')):
            with self.assertRaises(DatabaseError):
                commands.submit_request(self.run,dict(skuCode='337',whCode='DP010290',parentWhCode='DC010001',
                    request='New',eta=None),actor)
        self.assertFalse(DailyOpenRequest.objects.exists())
        good=dict(SKUCode='337',WHCode='DP010290',Remark='Contacted',ETA='2026-10-20')
        with self.assertRaises(reader.TargetDenied):
            commands.add_expedite_remark(self.run,dict(data=[good,dict(good,SKUCode='Denied')]),actor)
        with self.assertRaises(ValueError):
            commands.add_expedite_remark(self.run,dict(data=[dict(good,ETA='')]),actor)
        self.assertFalse(ExpediteRemarkHistory.objects.exists())
        self.assertEqual(daily_requests.snapshot()['revision'],0)
        self.assertEqual(live.history_owner().next_ordinal,0)

    def test_command_http_truthful_failure_actor_body_rejection_and_database_binding(self):
        from django.test import RequestFactory
        from django.conf import settings
        from django.urls import resolve
        daily_requests.initialize([],provenance={'component_fixture':'HTTP commands'})
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()');database=cursor.fetchone()[0]
        factory=RequestFactory()
        headers={settings.MTA_TRUSTED_GATEWAY_HEADER:json.dumps({'id':1,'name':'Trusted actor'})}
        def post(name,body):
            path='/api/mta/'+name
            return resolve(path).func(factory.post(path,json.dumps(body),content_type='application/json',headers=headers))
        body=dict(skuCode='337',whCode='DP010290',parentWhCode='DC010001',request='Verified',eta=None,
                  user=dict(id=999,name='Forged actor'))
        with patch('mta.presentation.logistics_views.selected_run',return_value=self.run):
            self.assertEqual(post('SubmitOpenExpediteRequest',body).status_code,403)
            with override_settings(VF_MTA_LOGISTICS_COMMAND_DATABASE='wrong-database'):
                self.assertEqual(post('SubmitOpenExpediteRequest',body).status_code,403)
            with override_settings(VF_MTA_LOGISTICS_COMMAND_DATABASE=database):
                self.assertEqual(post('SubmitOpenExpediteRequest',body).status_code,200)
                self.assertEqual(ExpediteRemarkHistory.objects.get().UserId,'Trusted actor')
                self.assertEqual(post('SubmitRemarksForInTransit',dict(data=[self.transit_command_row()])).status_code,200)
                self.assertEqual(TransitRemarkHistory.objects.get().UserId,1)
                with patch.object(ExpediteRemarkHistory.objects,'create',side_effect=DatabaseError('history unavailable')):
                    response=post('AddRemarkForExpedite',dict(data=[dict(SKUCode='337',WHCode='DP010290',
                        Remark='Must fail',ETA='2026-10-20')]))
                self.assertEqual(response.status_code,500)
                self.assertEqual(json.loads(response.content)['status'],500)
                from mta.runtime.models import DailyOpenRequest
                self.assertIsNone(DailyOpenRequest.objects.get().Action)

    def test_serving_overlay_never_changes_publication_source_and_refresh_is_separate(self):
        value=live.generation(self.run)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.logistics_command',%s,true)",[live.OWNER])
        TransitAnnotation.objects.create(generation=value,source_ordinal=0,
            CurrentLocationCode='DC010002',ETA=date(2026,10,20),Remark='Current only')
        with override_settings(VF_MTA_DAILY_PUBLICATION=True):
            self.assertEqual(live.serving_transit_rows(self.run,self.source)[0]['Remark'],'Current only')
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.daily_publication_build',%s,true)",[str(self.run.pk)])
            self.assertIsNone(live.serving_transit_rows(self.run,self.source)[0]['Remark'])
        successor=CalculationRun.objects.create(kind='DAILY_CHAIN',status='RUNNING',
            business_date='2026-10-19',input_digest=digest('component-refresh-only'),
            execution_revision='component-refresh-only',input_payload={})
        # No day is executed. This is solely the generation/reader component.
        live.initialize(successor,provenance={'component_fixture':'retained-catalogue-logistics'})
        self.assertIsNone(live.transit_rows(successor)[0]['Remark'])
        self.assertEqual(live.generation(successor).revision,0)
        self.assertEqual(TransitAnnotation.objects.filter(generation=value).count(),1)
