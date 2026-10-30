"""Actual scoped Expedition providers and original human-visible read contracts."""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timezone
import json,os,unittest
from unittest.mock import patch
from tests import test_scoped_expedite_parent_postgresql as parent_fixture
from tests import test_scoped_transit_postgresql as transit_fixture


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedExpediteTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr','parents','fetch'):
        locals()[_name]=getattr(parent_fixture.ScopedExpediteParentTests,_name)
    row=staticmethod(parent_fixture.ScopedExpediteParentTests.row)
    positive=transit_fixture.ScopedTransitTests.positive
    for _name in ('prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(parent_fixture.ScopedExpediteParentTests,_name)

    def owner(self,**options):
        from tests import production_h3_fixture as h3,test_h3_daily_integration as supplied
        original=h3.supplied_day;frame=supplied.frame()
        if getattr(self,'full_factor',False):
            frame['opening']['state']['dbm']['VFSettings'].append(dict(Parameter='SuperDelayFactor',Value='2',
                Description='Declared matching Full component setting'))
        if getattr(self,'action_case',False):
            for state,name in ((frame['opening']['state']['dbm'],'Suggestions'),(frame['opening']['state']['controls'],'suggestions')):
                state[name]=[dict(SKUCode=h3.SEASON,WhCode=h3.CHILD,Type=1,NewNorm=24)]
        def day(*args,**kwargs):
            value=original(*args,**kwargs)
            for r in value['day']['raw_daily']:
                if r['SKUCode']!='SUPPLIED-Z9':continue
                if r['WhCode']==h3.CHILD:r.update(Stock=1000 if getattr(self,'zero_facts_case',False) else 0,GIT=0,Consumption=0,Receipts=0)
                if getattr(self,'availability_case',False) and r['WhCode']==h3.PARENT:r.update(Stock=0,Consumption=40,Receipts=0)
            return value
        with patch.object(h3,'supplied_day',side_effect=day),patch.object(supplied,'frame',return_value=frame):
            transit_fixture.ScopedTransitTests.owner(self,remark_inputs=self.snapshot,request_inputs=self.request_snapshot,**options)

    def start(self,*,empty=False,missing=False,requests=None):
        from mta.presentation import daily_requests,scoped_expedite
        self.positive(duplicates=True)
        if empty:
            self.transit_sources['shipments']['rows']=[];self.transit_sources['transporters']['rows']=[]
        self.request_snapshot=None
        if not missing:
            daily_requests.initialize([] if requests is None else requests,provenance={'fixture':'scoped-composite-requests-not-native'})
            self.request_snapshot=daily_requests.snapshot()
        stamp=datetime(2037,4,9,tzinfo=timezone.utc)
        self.parents(rows=[] if empty else [self.row(None,stamp),self.row('same',stamp),self.row('same',stamp)],counter=True,consumer_cut=True)
        if missing:return
        self.reference=scoped_expedite.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.bound=scoped_expedite.bind(self.reference)

    def scopes(self,*,empty=False):
        from mta.presentation.permissions import PermissionCodes
        from tests.production_h3_fixture import CHILD,PARENT
        return PermissionCodes({} if empty else {'SUPPLIED-Z9':2}),PermissionCodes({} if empty else {CHILD:3,PARENT:3})

    def reads(self,*,empty=False):
        from mta.presentation import planning_expedite_sql as normal,planning_expedite_custom_sql as custom,planning_expedite_chart_sql as charts
        stack=ExitStack();codes=self.scopes(empty=empty)
        for module in (normal,custom,charts):
            stack.enter_context(patch.object(module,'scope',return_value=codes))
            stack.enter_context(patch.object(module,'_projected_attributes',side_effect=AssertionError('Full attributes')))
            if hasattr(module,'image_query'):stack.enter_context(patch.object(module,'image_query',side_effect=AssertionError('Full image')))
        return stack

    def context(self):
        from mta.presentation import rrr,pick_post
        s=self.bound.sources
        names=('SkuAttributeData','LocationAttributeData','SkuLocAttributeData','SKUDescriptionTbl','SiteDescriptionTbl','MasterData')
        importer={n:s.rows('closing/importer/'+n) for n in names}
        standards=s.rows('closing/dbm/SKULocStandardAttributes')
        raw=rrr.pick_rows(s.rows('reports/bpr/vf_RationedReqReport'),s.rows('sources/calculation/PickBands'))
        post=pick_post.produce(raw)
        pick=[dict(r,**post[i]) for i,r in enumerate(raw)]
        return dict(importer=importer,standards=standards,raw=raw,pick=pick,
            masters=s.rows('closing/bpr/BPRMaster'),
            facts=self.bound.core.prepared.reports.rows('ExpediteDispatches'),nms=s.rows('closing/consumer_context/NMSAllItems'),
            bpr=s.rows('reports/bpr/BPR_Table'),remarks=self.bound.parent.remarks.rows())

    @staticmethod
    def unordered_transit(data):
        data=deepcopy(data)
        for key in ('expediteDispatchestransit','createAvailabilityAtParenttransit'):
            data[key].sort(key=lambda row:json.dumps(row,sort_keys=True))
        return data

    def complete(self,*,availability=False,empty=False):
        from django.test import override_settings
        from mta.presentation import expedite_read as public,planning_expedite_sql as normal,planning_expedite_chart_sql as charts
        from mta.presentation import expedite_parent,expedite_child,expedite_custom,expedite_views,expedite_charts,expedite_child_sources
        from mta.runtime.scope_revisions import require_current
        from mta.serialization import storage
        self.availability_case=availability;self.start(empty=empty)
        c=self.context();products,locations=self.scopes();before=require_current(self.run)
        payload=dict(type='parent',paginationParameter=dict(pageNumber=1,recordsPerPage=2))
        with override_settings(VF_MTA_LOGISTICS_CURRENT=False),self.reads():
            actual=public.parent_grid(payload,read_binding=self.bound)
            self.assertTrue(actual['data']['createAvailabilityAtParent' if availability else 'expediteDispatches'])
            expected=expedite_parent.parent_rows(c['facts'],c['importer'],c['standards'],c['masters'],
                nms=c['nms'],products=products,locations=locations,paging=(1,2),remarks=c['remarks'],pick=c['raw'])
            self.assertEqual(self.unordered_transit(actual['data']),self.unordered_transit(expected))
            self.assertEqual(actual['uiConfig'],[dict(header=h,colCode=k,colPosition=p) for h,k,p in public.PARENT_COLUMNS])
            child=public.child_grid(dict(payload,type='child'),read_binding=self.bound)
            expected_child=expedite_child.child_rows(c['facts'],c['importer'],c['standards'],products=products,locations=locations,
                paging=(1,2),business_date=self.bound.sources.run.business_date,requests=[],transit=[])
            nested=expedite_child_sources.projections(*self.bound.child_sources)
            for bag in expected_child.values():
                for r in bag:
                    fact=next(a for a in c['facts'] if a['SKUCode']==r['sc'] and a['WhCode']==r['wc'])
                    r.update(nested(r['sc'],r['wc'],fact['ParentWhCode']))
            self.assertEqual(storage(child['data']),storage(expected_child))
            custom=public.custom_grid(payload,read_binding=self.bound)
            expected_custom=expedite_custom.custom_rows(c['facts'],nms=c['nms'],products=products,locations=locations,paging=(1,2),
                bpr_rows=c['bpr'],site_descriptions=c['importer']['SiteDescriptionTbl'],visible_dynamic_attributes=[],stable_producer_order=True)
            from decimal import Decimal
            expected_custom=[{k:float(v) if isinstance(v,Decimal) else v for k,v in r.items()} for r in expected_custom]
            self.assertEqual(storage(custom['data']),storage(expected_custom))
            # This is a pure reference operand, never a persisted Full result.
            output={'ClosingState':[dict(importer=c['importer'],dbm=dict(SKULocStandardAttributes=c['standards']),bpr=dict(BPRMaster=c['masters']))]}
            for kind in ('parent','child'):
                self.assertEqual(normal.counts(self.run,dict(payload,type=kind),read_binding=self.bound),
                    expedite_views.counts(output,c['facts'],kind,products=products,locations=locations))
                actual_tables=charts.queries(self.run,payload,kind,read_binding=self.bound)
                expected_tables=expedite_charts.queries(output,c['facts'],c['pick'],kind,products=products,locations=locations)
                self.assertEqual(storage(actual_tables),storage(expected_tables))
                self.assertEqual(expedite_charts.response(actual_tables,kind,receiving_own_label=True),
                    expedite_charts.response(expected_tables,kind,receiving_own_label=True))
        self.assertEqual(require_current(self.run),before)

    def test_complete_dispatch_parent_child_custom_counts_and_charts(self):self.complete()
    def test_complete_availability_parent_child_counts_and_charts(self):self.complete(availability=True)
    def test_owned_empty_remarks_requests_and_shipments(self):self.complete(empty=True)

    def test_produced_zero_expedite_facts_settle_without_missing_source_fallback(self):
        from mta.presentation import expedite_read as public,planning_expedite_sql as normal,planning_expedite_chart_sql as charts
        self.zero_facts_case=True;self.start(empty=True)
        self.assertEqual(self.bound.core.prepared.reports.rows('ExpediteDispatches'),[])
        with self.reads():
            payload=dict(type='parent',paginationParameter=dict(pageNumber=1,recordsPerPage=2))
            parent=public.parent_grid(payload,read_binding=self.bound)['data']
            self.assertEqual((parent['expediteDispatches'],parent['createAvailabilityAtParent']),([],[]))
            self.assertTrue(parent['expediteDispatchestransit'])  # Canonical NMS LEFT population.
            self.assertEqual(public.child_grid(payload,read_binding=self.bound)['data'],dict(expediteDispatches=[],createAvailabilityAtParent=[]))
            self.assertEqual(public.custom_grid(payload,read_binding=self.bound)['data'],[])
            self.assertEqual(normal.counts(self.run,payload,read_binding=self.bound),dict(expediteDispatches=0,createAvailabilityAtParent=0))
            for kind in ('parent','child'):
                tables=charts.queries(self.run,payload,kind,read_binding=self.bound)
                for key in tables:
                    if key!='pre_post':self.assertEqual(tables[key],[])

    def test_missing_request_capture_denies_before_new_core_parent_or_transit(self):
        from mta.presentation import scoped_expedite as module
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import ScopeExpediteGeneration,ScopeExpediteParentGeneration,ScopeTransitGeneration
        self.start(missing=True)
        with self.assertRaises(PublicationUnavailable):module.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        for model in (ScopeExpediteGeneration,ScopeExpediteParentGeneration,ScopeTransitGeneration):self.assertEqual(model.objects.count(),0)

    def test_metadata_only_admission_and_all_reads_do_not_prepare(self):
        from mta.presentation import scoped_expedite as module,scoped_expedite_storage as core,scoped_expedite_parent as parent,scoped_requests
        from mta.presentation import expedite_read as public,planning_expedite_sql as normal,planning_expedite_chart_sql as charts
        self.start()
        with patch.object(scoped_requests.RequestBinding,'_records',side_effect=AssertionError('requests hydrated in bind')), \
                patch.object(core,'bind',wraps=core.bind) as core_admission:
            bound=module.bind(self.reference)
            core_admission.assert_called_once()
        with patch.object(core,'prepare',side_effect=AssertionError('core rebuilt')),patch.object(parent,'prepare',side_effect=AssertionError('parent rebuilt')),self.reads():
            payload=dict(type='parent',paginationParameter=dict(pageNumber=1,recordsPerPage=1))
            public.parent_grid(payload,read_binding=bound);public.child_grid(payload,read_binding=bound)
            public.custom_grid(payload,read_binding=bound);normal.counts(self.run,payload,read_binding=bound)
            charts.queries(self.run,payload,'parent',read_binding=bound)

    def test_reference_and_cross_owner_contract_denials(self):
        from mta.presentation import scoped_expedite as module
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import CalculationRun
        self.start()
        for key,value in [('core_digest','e'*64),('parent_digest','e'*64),('transit_digest','e'*64),('phase_digest','e'*64),
                ('snapshot_digest','e'*64),('source_digest','e'*64),('action_revision',True),('core_generation_id','invalid')]:
            changed=dict(self.reference,**{key:value})
            with self.subTest(key=key),self.assertRaises(PublicationUnavailable):module.bind(changed)
        changed=dict(self.reference,unknown='extra')
        with self.assertRaises(PublicationUnavailable):module.bind(changed)
        foreign=CalculationRun.objects.exclude(pk=self.run.pk).first();self.assertIsNotNone(foreign)
        with self.assertRaises(PublicationUnavailable):module.require_binding(foreign,self.bound)
        wrong=deepcopy(self.bound.transit.generation);wrong.phase_id=foreign.pk
        with self.assertRaises(PublicationUnavailable):module.require_binding(self.run,replace(self.bound,transit=replace(self.bound.transit,generation=wrong)))

    def test_retained_complete_reference_reuses_rows_and_refreshes_owned_prefix(self):
        from django.db import connection
        from mta.presentation import scoped_expedite as module,scoped_expedite_parent as parent,ancillary_live as live
        from mta.presentation import legacy_scope_read_compatibility as profile
        from mta.presentation.context import PublicationUnavailable
        with patch.object(parent,'recipe_digest',return_value=parent.RETAINED_RECIPE):self.start()
        old=deepcopy(self.reference);self.assertEqual(old['recipe_digest'],module.RETAINED_RECIPE)
        before={name:self.bound.parent.rows(name) for name in ('base','match')}
        # Persist the complete public composite locator; all referenced immutable
        # core/parent/transit rows are real guarded PostgreSQL generations.
        with connection.cursor() as c:
            c.execute('CREATE TEMP TABLE retained_transit_reference (reference jsonb) ON COMMIT DROP')
            c.execute('INSERT INTO retained_transit_reference VALUES (%s::jsonb)',[json.dumps(old)])
            c.execute('SELECT reference FROM retained_transit_reference');stored=c.fetchone()[0]
        if isinstance(stored,str):stored=json.loads(stored)
        with patch.object(parent,'_inserts',side_effect=AssertionError('retained parent rebuilt')):
            self.assertEqual(module.bind(stored).read_identity,old)
            self.assertEqual(module.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0),old)
        with patch.dict(profile.ADAPTED_DEPENDENCIES,{'mta.presentation.planning_expedite_transit':'f'*64}):
            with self.assertRaises(PublicationUnavailable):module.bind(stored)
        stamp=datetime(2037,4,11,tzinfo=timezone.utc);value=self.row('new prefix',stamp)
        live.append(live.BPR,[{k:v for k,v in value.items() if k!='RemarkDate'}],actor_id='retained-reference',timestamp=stamp)
        with self.assertRaises(PublicationUnavailable):module.bind(stored)
        fresh=module.refresh_parent(stored)
        self.assertEqual(fresh['core_generation_id'],old['core_generation_id'])
        self.assertNotEqual(fresh['parent_generation_id'],old['parent_generation_id'])
        self.assertEqual(fresh['recipe_digest'],module.recipe_digest())
        rebound=module.bind(fresh)
        self.assertTrue(any(r['remark']=='new prefix' for r in rebound.parent.rows('base')))
        self.assertEqual({name:self.bound.parent.rows(name) for name in before},before)
        with self.assertRaises(PublicationUnavailable):module.bind(dict(fresh,recipe_digest=module.RETAINED_RECIPE))
        with connection.cursor() as c:
            c.execute('SELECT reference FROM retained_transit_reference');same=c.fetchone()[0]
        self.assertEqual(json.loads(same) if isinstance(same,str) else same,old)

    def request_row(self,**values):
        from mta.presentation.daily_requests import FIELDS
        from tests.production_h3_fixture import CHILD,PARENT
        row=dict.fromkeys(FIELDS);row.update(SKUCode='SUPPLIED-Z9',WhCode=CHILD,ParentWhCode=PARENT,**values)
        return row

    def test_populated_frozen_latest_request_and_duplicate_shipment_json(self):
        from mta.presentation import expedite_read as public
        requests=[self.request_row(Request='old',RequestDate=None),
            self.request_row(Request='latest / future',RequestDate='2037-04-12T10:00:00',Action='Closed',UserId='Operator Ω'),
            self.request_row(Request='earlier',RequestDate='2037-04-11T10:00:00')]
        self.start(requests=requests)
        with self.reads():result=public.child_grid(dict(paginationParameter=dict(pageNumber=1,recordsPerPage=20)),read_binding=self.bound)
        rows=[r for group in result['data'].values() for r in group if r['sc']=='SUPPLIED-Z9']
        self.assertTrue(rows);self.assertTrue(all(r['remark']=='latest / future' for r in rows))
        from mta.presentation.expedite_child_sources import TRANSIT_ALIASES
        from mta.serialization import storage
        transit=[{k:r[v] for k,v in TRANSIT_ALIASES.items()} for r in self.bound.transit.rows('InTransitData')
            if r['SKUCode']=='SUPPLIED-Z9' and r['WhCode']==rows[0]['wc']]
        self.assertEqual(len(transit),2)
        for r in rows:self.assertEqual(json.loads(r['intransit']),storage(transit))

    def test_latest_request_tie_denial(self):
        from mta.presentation import expedite_read as public
        self.start(requests=[self.request_row(Request='one'),self.request_row(Request='two')])
        with self.reads(),self.assertRaisesRegex(ValueError,'ambiguous_latest_request'):
            public.child_grid({},read_binding=self.bound)

    def test_filtered_parent_transit_uses_complete_scope_before_paging(self):
        from mta.presentation import expedite_read as public,expedite_parent
        self.start();c=self.context();products,locations=self.scopes()
        with self.reads():
            first=public.parent_grid(dict(paginationParameter=dict(pageNumber=1,recordsPerPage=1)),read_binding=self.bound)
            second=public.parent_grid(dict(paginationParameter=dict(pageNumber=2,recordsPerPage=1)),read_binding=self.bound)
            for key in ('expediteDispatchestransit','createAvailabilityAtParenttransit'):
                self.assertEqual(first['data'][key],second['data'][key])
            self.assertEqual(first['data']['expediteDispatches'][0]['rn'],'1')
            self.assertEqual(second['data']['expediteDispatches'][0]['rn'],'2')
            payload=dict(paginationParameter=dict(pageNumber=1,recordsPerPage=2),
                filters={'productFilter':{'filters':[dict(attributeName='sku',value='unknown')]}})
            actual=public.parent_grid(payload,read_binding=self.bound)
            expected=expedite_parent.parent_rows(c['facts'],c['importer'],c['standards'],c['masters'],nms=c['nms'],products=products,
                locations=locations,paging=(1,2),remarks=c['remarks'],pick=c['raw'],matches=expedite_parent.parent_filter(payload,c['importer']))
            self.assertEqual(self.unordered_transit(actual['data']),self.unordered_transit(expected))

    def test_dynamic_config_and_unbound_live_annotation_owner_deny(self):
        from django.test import override_settings
        from mta.presentation import expedite_read as public
        from mta.presentation.context import PublicationUnavailable
        self.start()
        with patch('mta.presentation.legacy_ui.BPR_UI_CONFIG',[dict(Visible=True,Col_Code='SkuAttr1')]):
            with self.assertRaisesRegex(PublicationUnavailable,'dynamic_attributes'):public.child_grid({},read_binding=self.bound)
            with self.assertRaisesRegex(PublicationUnavailable,'dynamic_attributes'):public.custom_grid({},read_binding=self.bound)
        # A predicate-isolation denial test, not a qualified phase workflow owner.
        with override_settings(VF_MTA_LOGISTICS_CURRENT=True),patch('mta.runtime.models.TransitLiveGeneration.objects.filter') as manager:
            manager.return_value.exists.return_value=True
            with self.reads(),self.assertRaisesRegex(PublicationUnavailable,'live_transit_binding_required'):
                public.child_grid({},read_binding=self.bound)

    def test_real_append_refresh_recovery_uses_same_core_transit_and_requests(self):
        from mta.presentation import scoped_expedite as module,ancillary_live as live,scoped_expedite_storage as core,scoped_expedite_parent as parent
        from mta.presentation.context import PublicationUnavailable
        self.start();old=self.bound;old_data=old.parent.rows('base')
        value=self.row('later',datetime(2037,4,11,tzinfo=timezone.utc))
        live.append(live.BPR,[{k:v for k,v in value.items() if k!='RemarkDate'}],actor_id='composite',timestamp=value['RemarkDate'])
        with self.assertRaises(PublicationUnavailable):module.bind(self.reference)
        # An appended business remark is retained if derived refresh fails.
        with patch.object(parent,'_receipt',side_effect=OSError('late parent refresh')),self.assertRaises(OSError):module.refresh_parent(self.reference)
        with patch.object(core,'prepare',side_effect=AssertionError('core rebuilt')):
            fresh=module.refresh_parent(self.reference)
        bound=module.bind(fresh);self.assertNotEqual(fresh['parent_generation_id'],self.reference['parent_generation_id'])
        for field in ('core_generation_id','core_digest','transit_generation_id','transit_digest','requests'):self.assertEqual(fresh[field],self.reference[field])
        self.assertEqual(old.parent.rows('base'),old_data);self.assertTrue(any(r['remark']=='later' for r in bound.parent.rows('base')))
        self.assertEqual(module.refresh_parent(fresh),fresh)

    def test_empty_permissions_and_original_unpaged_norm_dynamic_denials(self):
        from mta.presentation import expedite_read as public,planning_expedite_sql as normal,planning_expedite_chart_sql as charts
        from mta.presentation.context import PublicationUnavailable
        self.start()
        with self.reads(empty=True):
            payload=dict(type='child',paginationParameter=dict(pageNumber=1,recordsPerPage=2))
            self.assertEqual(public.child_grid(payload,read_binding=self.bound)['data'],dict(expediteDispatches=[],createAvailabilityAtParent=[]))
            self.assertEqual(public.custom_grid(payload,read_binding=self.bound)['data'],[])
            self.assertEqual(normal.counts(self.run,payload,read_binding=self.bound),dict(expediteDispatches=0,createAvailabilityAtParent=0))
            self.assertEqual(charts.queries(self.run,payload,'child',read_binding=self.bound)['critical'],[])
        with self.assertRaisesRegex(PublicationUnavailable,'UNPAGED-SQL156'):public.parent_grid({},read_binding=self.bound)
        payload=dict(filters={'availabilityFilter':{'filters':[dict(attributeName='norm',operator='>',value='0')]}})
        with self.assertRaisesRegex(PublicationUnavailable,'norm_filter'):public.child_grid(payload,read_binding=self.bound)

    def test_real_sleep_requires_new_composite_but_retains_inflight_reads(self):
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.runtime.scoped_actions import record
        from mta.presentation import scoped_expedite as module
        from mta.presentation.context import PublicationUnavailable
        from tests.production_h3_fixture import SEASON,CHILD
        self.action_case=True;self.start();old=self.bound;before=old.parent.rows('match')
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        event=record(self.run.pk,phase_id=self.receipt.pk,phase_digest=self.receipt.digest,expected_revision=0,operation='SLEEP',
            selected=[[SEASON,CHILD]],timestamp='2037-04-10T10:00:00',actor='composite',idempotency_key='composite-sleep')
        with self.assertRaises(PublicationUnavailable):module.bind(self.reference)
        with self.assertRaises(PublicationUnavailable):module.refresh_parent(self.reference)
        fresh=module.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=event.pk)
        self.assertNotEqual(fresh['core_generation_id'],self.reference['core_generation_id'])
        self.assertEqual(old.parent.rows('match'),before);self.assertEqual(module.bind(fresh).parent.rows('match'),before)

    def test_same_actual_full_completion_and_report_build_keep_phase_read_reference(self):
        from django.db import connection
        from django.utils import timezone as django_time
        from mta.presentation import scoped_expedite as module,ancillary_live as live,daily_requests,operational_reports as full
        from mta.presentation import expedite_read as public,planning_expedite_chart_sql as charts
        from mta.runtime.models import RunPhaseAcceptance,DailyReportGeneration,ExpediteProjection
        from mta.serialization import digest
        self.full_factor=True;self.positive(duplicates=True)
        daily_requests.initialize([],provenance={'fixture':'scoped-composite-full-not-native'})
        self.request_snapshot=daily_requests.snapshot()
        provenance={'fixture':'scoped-composite-full-remarks-not-native'}
        live.initialize_owner(live.BPR,provenance_digest=digest(provenance),provenance_receipt=provenance)
        value=self.row('captured',datetime(2037,4,9,tzinfo=timezone.utc))
        live.append(live.BPR,[{k:v for k,v in value.items() if k!='RemarkDate'}],actor_id='component',timestamp=value['RemarkDate'])
        self.snapshot=live.snapshot_all(business_date='2037-04-10',bpr_remark_horizon=13)
        self.owner(claim=False);self.prepare_dbm();self.receipt=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        self.reference=module.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.bound=module.bind(self.reference);payload=dict(paginationParameter=dict(pageNumber=1,recordsPerPage=2))
        with self.reads():
            before=(public.parent_grid(payload,read_binding=self.bound),public.child_grid(payload,read_binding=self.bound),
                public.custom_grid(payload,read_binding=self.bound),charts.queries(self.run,payload,'parent',read_binding=self.bound))
        finished=self.finish();self.assertEqual((finished.pk,finished.status),(self.run.pk,'SUCCEEDED'))
        terminal=DailyReportGeneration.objects.create(run=finished,source_digest=finished.production_digest,recipe_digest=full.recipe_identity())
        with connection.cursor() as c:c.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(finished.pk)])
        terminal.metadata=full._build(finished);terminal.digest=digest(terminal.metadata);terminal.status='READY';terminal.sealed_at=django_time.now()
        terminal.save(update_fields=['metadata','digest','status','sealed_at']);full.verify_rows(finished,full.generation(finished).metadata)
        self.assertTrue(ExpediteProjection.objects.filter(run=finished).exists())
        rebound=module.bind(self.reference);self.assertEqual(rebound.read_identity,self.reference)
        with self.reads():
            after=(public.parent_grid(payload,read_binding=rebound),public.child_grid(payload,read_binding=rebound),
                public.custom_grid(payload,read_binding=rebound),charts.queries(finished,payload,'parent',read_binding=rebound))
        self.assertEqual(after,before)
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
