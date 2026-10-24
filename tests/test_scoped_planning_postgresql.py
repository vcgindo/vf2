"""Real typed phase occurrences/consumers; every fixture rolls back."""
from itertools import product
from types import SimpleNamespace
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_pick_files_postgresql as fixtures
from tests.test_scoped_prepared_postgresql import native_key


def k(value):return None if value is None else native_key(value)[0]

def same(a,b):return a is not None and b is not None and k(a)==k(b)


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedPlanningTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr'):
        locals()[_name]=getattr(fixtures.ScopedPickFileTests,_name)

    def parents(self,*,positive=False,counter=False,duplicates=False):
        from tests.production_h3_fixture import supplied_day,PARENT
        from mta.presentation import scoped_report_storage as facts,scoped_prepared
        def day(*args,**kwargs):
            value=supplied_day(*args,**kwargs)
            if positive:
                for row in value['day']['raw_daily']:
                    if row['WhCode']==PARENT:row.update(Stock=1000,Receipts=960)
            if duplicates:
                order=next(r for r in value['day']['order_feed'] if r['OrderID']=='SPIKE')
                value['day']['order_feed'].append(dict(order,OrderID='SPIKE-SECOND'))
            return value
        with patch('tests.production_h3_fixture.supplied_day',side_effect=day):
            self.bpr(counter=counter)
        self.report=facts.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.source=scoped_prepared.prepare(self.report.pk,expected_report_digest=self.report.digest,action_revision=0)

    def prepare(self):
        from mta.presentation.scoped_planning import prepare
        return prepare(self.report.pk,expected_source_digest=self.source.digest,expected_report_digest=self.report.digest,action_revision=0)

    def binding(self,row):
        from mta.presentation.scoped_planning import bind
        return bind(row.pk,expected_digest=row.digest,expected_source_digest=self.source.digest,expected_report_digest=self.report.digest,action_revision=0)

    def manual(self,bound,name):
        sources=bound.prepared.sources
        image=lambda table:list(enumerate(sources.rows('closing/importer/'+table)))
        if name.startswith('chart_'):
            result=[]
            for family,factname in (('excess','ExcessInventoryDetails'),('fulfillment_summary','OrderFulfillmentSummary'),('fulfillment_detail','OrderFulfillmentDetails')):
                facts=bound.prepared.reports.rows(factname)
                for direction in ('location','sku'):
                    location=direction=='location';code='WhCode' if location else 'SKUCode'
                    dim='WHCode' if location else 'SKUCode';description='WHDescription' if location else 'SKUDescription'
                    descriptions=image('SiteDescriptionTbl' if location else 'SKUDescriptionTbl')
                    attributes=image('LocationAttributeData' if location else 'SkuAttributeData')
                    members=[];groups={}
                    for i,a in enumerate(facts):
                        for j,d in descriptions:
                            if not same(a[code],d[dim]):continue
                            band=a.get('Coverage' if family=='fulfillment_summary' else 'OrderStatus') if family!='excess' else None
                            group=(k(a[code]),k(d[description]),k(band))
                            group_ordinal=groups.setdefault(group,len(members))
                            members.append(dict(family=family,direction=direction,ordinal=len(members),group_ordinal=group_ordinal,
                                fact_ordinal=i,description_ordinal=j,code=a[code],description=d[description],band=band))
                    if name=='chart_members':result.extend(members);continue
                    displays=[]
                    for group_ordinal in sorted(set(m['group_ordinal'] for m in members)):
                        first=members[group_ordinal]
                        for j,a in attributes:
                            if not same(first['code'],a[dim]):continue
                            displays.append(dict(family=family,direction=direction,ordinal=len(displays),group_ordinal=group_ordinal,
                                attribute_ordinal=j,**{'h'+str(n):a[('LL' if location else 'SL')+str(n)] for n in range(1,6)}))
                    result.extend(displays)
            return sorted(result,key=lambda r:(r['family'],r['direction'],r['ordinal']))
        family,grain=name.split('_');facts=bound.prepared.reports.rows('ExcessInventoryDetails' if family=='excess' else 'OrderFulfillmentSummary')
        result=[]
        for i,a in enumerate(facts):
            if grain=='grid':
                matching=[]
                for table,code,value in (('SKUDescriptionTbl','SKUCode',a['SKUCode']),('SiteDescriptionTbl','WHCode',a['WhCode']),
                        ('SkuAttributeData','SKUCode',a['SKUCode']),('LocationAttributeData','WHCode',a['WhCode'])):
                    matching.append([(j,row) for j,row in image(table) if same(value,row[code])])
                matching.append([(j,row) for j,row in image('SkuLocAttributeData')
                    if same(a['SKUCode'],row['SKUCode']) and same(a['WhCode'],row['LocCode'])])
                parents=[(j,row) for j,row in image('SiteDescriptionTbl') if same(a['ParentWhCode'],row['WHCode'])] or [(None,None)]
                if family!='excess':parents=[(None,None)]
                for (sdj,sd),(ldj,ld),(saj,sa),(laj,la),(pj,p),(pdj,pd) in product(*matching,parents):
                    row=dict(fact_ordinal=i,sku_description_ordinal=sdj,location_description_ordinal=ldj,sku_ordinal=saj,
                        location_ordinal=laj,pair_ordinal=pj,sku_key=k(a['SKUCode']),location_key=k(a['WhCode']),parent_key=k(a['ParentWhCode']),
                        sku_description=sd['SKUDescription'],location_description=ld['WHDescription'])
                    row.update({prefix.lower()+str(n):attr[prefix+str(n)] for prefix,attr in (('SL',sa),('LL',la)) for n in range(1,6)})
                    if family=='excess':row.update(parent_description_ordinal=pdj,parent_description=None if pd is None else pd['WHDescription'])
                    result.append(row)
            else:
                nms=[(j,row) for j,row in enumerate(sources.rows('closing/consumer_context/NMSAllItems'))
                    if same(a['SKUCode'],row['SKUCode']) and same(a['WhCode'],row['WhCode'])]
                if family=='fulfillment' and not nms:nms=[(None,None)]
                for j,n in nms:
                    parents=[(t,row) for t,row in image('SiteDescriptionTbl') if n is not None and same(n['ParentWhCode'],row['WHCode'])]
                    if family=='fulfillment' and not parents:parents=[(None,None)]
                    standards=[(t,row) for t,row in enumerate(sources.rows('closing/dbm/SKULocStandardAttributes'))
                        if same(a['SKUCode'],row['SKUCode']) and same(a['WhCode'],row['WhCode'])] if family=='excess' else [(None,None)]
                    for (t,pd),(q,s) in product(parents,standards):
                        row=dict(fact_ordinal=i,nms_ordinal=j,parent_description_ordinal=t,sku_key=None if n is None else k(n['SKUCode']),
                            location_key=None if n is None else k(n['WhCode']),parent_description=None if pd is None else pd['WHDescription'])
                        if family=='excess':row['standard_ordinal']=q
                        result.append(row)
        order=(['fact_ordinal','sku_description_ordinal','location_description_ordinal']+(['parent_description_ordinal'] if family=='excess' else [])+
            ['sku_ordinal','location_ordinal','pair_ordinal']) if grain=='grid' else ['fact_ordinal','nms_ordinal','parent_description_ordinal']+(['standard_ordinal'] if family=='excess' else [])
        result.sort(key=lambda r:tuple(-1 if r[field] is None else r[field] for field in order))
        return [dict(ordinal=i,**r) for i,r in enumerate(result)]

    def test_independent_complete_bags_nulls_duplicates_and_parameterized_queries(self):
        from django.db import connection
        from mta.presentation.scoped_planning import TABLES
        from mta.serialization import storage
        self.parents(positive=True,duplicates=True);row=self.prepare();bound=self.binding(row)
        self.assertTrue(all(row.metadata['images'][name]['count'] for name in TABLES))
        self.assertTrue(any(r['band'] is None for r in bound.rows('chart_members')))
        self.assertTrue(any(r['Customer'] is None for r in bound.prepared.reports.rows('OrderFulfillmentDetails')))
        orders=bound.prepared.sources.rows('closing/orders/SpikeOrderData')
        self.assertIn('SPIKE-SECOND',{r['CustomerOrderId'] for r in orders})
        details=bound.prepared.reports.rows('OrderFulfillmentDetails')
        indices={i for i,r in enumerate(details) if r['OrderNo'] in ('SPIKE','SPIKE-SECOND')}
        self.assertEqual(len(indices),2)
        members=[r for r in bound.rows('chart_members') if r['family']=='fulfillment_detail'
                 and r['direction']=='location' and r['fact_ordinal'] in indices]
        self.assertEqual(len(members),2)
        self.assertEqual(len({r['group_ordinal'] for r in members}),1)
        for name in TABLES:
            with self.subTest(name=name):
                expected=self.manual(bound,name);self.assertEqual(bound.rows(name),expected)
                query,params=bound.query(name)
                order='R.family,R.direction,R.ordinal' if name.startswith('chart_') else 'R.ordinal'
                with connection.cursor() as cursor:
                    cursor.execute(query+' ORDER BY '+order,params)
                    names=[c[0] for c in cursor.description]
                    actual=[dict(zip(names,r)) for r in cursor.fetchall()]
                for r in actual:self.assertEqual(r.pop('run_id'),self.run.pk)
                self.assertEqual(storage(actual),expected)

    def test_query_text_and_parameters_match_unchanged_full_producers(self):
        from mta.presentation import scoped_planning_queries as new,planning_grid_preparation as grid,planning_custom_preparation as custom,planning_chart_preparation as chart
        from mta.runtime.relational_state import quote
        from mta.runtime.models import ExcessInventoryRow,FulfillmentSummaryRow,FulfillmentDetailRow
        self.parents()
        run=self.run
        models={'ExcessInventoryDetails':ExcessInventoryRow,'OrderFulfillmentSummary':FulfillmentSummaryRow,'OrderFulfillmentDetails':FulfillmentDetailRow}
        def image(run,path):return ('SELECT * FROM immutable_source WHERE image=%s',[path])
        fake=SimpleNamespace(fact_query=lambda name:('SELECT * FROM mta.'+quote(models[name]._meta.db_table)+' WHERE run_id=%s',[run.pk]),image_query=lambda path:image(run,path))
        for old in (grid,custom,chart):
            with patch.object(old,'image_query',side_effect=image),patch('mta.presentation.daily_preparation.source_digest',return_value='qualified-comparison'):
                if old==chart:
                    for family in chart.FAMILIES:
                        for direction in ('sku','location'):
                            self.assertEqual(new.chart_ingredients(run,family,direction,fake),chart.production_chart_ingredients(run,family,direction))
                else:
                    for family in ('excess','fulfillment'):
                        self.assertEqual(getattr(new,'grid_occurrences' if old==grid else 'custom_occurrences')(run,family,fake),
                            getattr(old,'production_grid_occurrences' if old==grid else 'production_custom_occurrences')(run,family))

    def test_failure_repeat_counter_neutrality_and_owned_empty(self):
        from mta.presentation import scoped_planning as module
        from mta.runtime.models import ScopePlanningProjection
        from mta.runtime.scope_revisions import require_current
        self.parents(counter=True);before=require_current(self.run)
        original=module._inserts
        def fail(*args):
            for name,query,params in original(*args):
                if name=='chart_displays':raise OSError('late occurrence failure')
                yield name,query,params
        with patch.object(module,'_inserts',side_effect=fail),self.assertRaisesRegex(OSError,'late occurrence failure'):self.prepare()
        self.assertFalse(ScopePlanningProjection.objects.filter(generation=self.report).exists())
        self.assertTrue(all(model.objects.count()==0 for model in module.TABLES.values()))
        self.assertEqual(require_current(self.run),before)
        self.report.refresh_from_db();self.source.refresh_from_db();self.assertTrue(self.report.sealed and self.source.sealed)
        row=self.prepare();bound=self.binding(row)
        self.assertEqual(bound.rows('excess_grid'),[]);self.assertEqual(bound.rows('excess_custom'),[])
        self.assertEqual(require_current(self.run),before)
        with patch.object(module,'_inserts',side_effect=AssertionError('occurrence replay')):self.assertEqual(self.prepare().digest,row.digest)
        self.assertEqual(require_current(self.run),before)

    def test_identity_guards_unsealed_commit_and_wrong_run(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_planning as module,planning_grids,planning_custom,planning_charts
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import ScopePlanningProjection
        import uuid
        self.parents()
        with self.assertRaises(DatabaseError),transaction.atomic():
            with module._owner(self.report.pk):ScopePlanningProjection.objects.create(generation=self.report,
                report_generation_digest=self.report.digest,source_projection_digest=self.source.digest,recipe_digest=module.recipe_digest())
            with connection.cursor() as c:c.execute('SET CONSTRAINTS scope_planning_complete IMMEDIATE')
        row=self.prepare();bound=self.binding(row)
        # Scalar fields are cloned from the Full models. A later imported
        # model change must alter admission identity even if this module's
        # cloning loop itself has not changed; in-flight ownership stays fixed.
        from mta.runtime.models import ScopePlanningChartMember
        with patch.object(ScopePlanningChartMember._meta.get_field('code'),'null',False):
            with self.assertRaises(PublicationUnavailable):self.binding(row)
            self.assertEqual(bound.rows('chart_members'),self.manual(bound,'chart_members'))
        options=dict(expected_source_digest=self.source.digest,expected_report_digest=self.report.digest,action_revision=0)
        for key,value in (('expected_source_digest','f'*64),('expected_report_digest','f'*64),('action_revision',1)):
            with self.subTest(key=key),self.assertRaises(PublicationUnavailable):module.prepare(row.pk,**dict(options,**{key:value}))
        with self.assertRaises(PublicationUnavailable):module.bind(row.pk,expected_digest='f'*64,**options)
        other=SimpleNamespace(pk=uuid.uuid4())
        for reader in (planning_grids.admitted_grids,planning_custom.admitted_custom,planning_charts.admitted_charts):
            with self.assertRaises(PublicationUnavailable):reader(other,read_binding=bound)
            with self.assertRaises(PublicationUnavailable):reader(self.run)
        for table in ['fresh_mta_scopeplanningprojection',*(m._meta.db_table for m in module.TABLES.values())]:
            for query in ('UPDATE mta.'+table+' SET generation_id=generation_id WHERE generation_id=%s',
                    'DELETE FROM mta.'+table+' WHERE generation_id=%s','TRUNCATE mta.'+table):
                with self.subTest(query=query),self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as c:c.execute(query,[] if query.startswith('TRUNCATE') else [row.pk])
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
        with transaction.atomic():
            with connection.cursor() as c:c.execute('ALTER TABLE mta.fresh_mta_scopeplanningchartmember DISABLE TRIGGER scope_planning_rows_insert')
            with self.assertRaises(PublicationUnavailable):self.binding(row)
            transaction.set_rollback(True)
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
        self.assertTrue(self.binding(row).projection.sealed)

    def test_actual_consumers_have_no_terminal_fact_source_or_admission_fallback(self):
        from mta.presentation import planning_grid_sql as grid,planning_custom_sql as custom,planning_chart_sql as chart
        from mta.presentation import excess_views,fulfillment_views,fulfillment_charts,excess_read,fulfillment_read
        from mta.presentation.excess_grid import excess_grid_rows
        from mta.presentation.fulfillment_grid import fulfillment_grid_rows
        from mta.presentation.permissions import PermissionCodes
        from django.db import connection
        self.parents(positive=True);bound=self.binding(self.prepare())
        attrs=bound.attributes()
        products=PermissionCodes({r['SKUCode']:2 for r in attrs['SkuAttributeData']})
        locations=PermissionCodes({r['WHCode']:3 for r in attrs['LocationAttributeData']})
        importer={name:bound.prepared.sources.rows('closing/importer/'+name) for name in
                  ('SkuAttributeData','LocationAttributeData','SKUDescriptionTbl','SiteDescriptionTbl','SkuLocAttributeData')}
        output=dict(ClosingState=[dict(importer=importer)])
        excess=bound.prepared.reports.rows('ExcessInventoryDetails')
        fulfillment=dict(summary=bound.prepared.reports.rows('OrderFulfillmentSummary'),
                         details=bound.prepared.reports.rows('OrderFulfillmentDetails'))
        guards=[]
        for module in (grid,custom,chart):
            guards.extend([patch.object(module,'scope',return_value=(products,locations)),
                           patch.object(module,'_projected_attributes',side_effect=AssertionError('terminal attributes'))])
        guards.extend([patch.object(grid,'image_query',side_effect=AssertionError('terminal grid image')),
                       patch.object(custom,'image_query',side_effect=AssertionError('terminal custom image'))])
        for guard in guards:guard.start();self.addCleanup(guard.stop)
        terminal_names=('fresh_mta_excessinventoryrow','fresh_mta_fulfillmentsummaryrow','fresh_mta_fulfillmentdetailrow')
        def no_terminal(execute,sql,params,many,context):
            self.assertFalse(any(name in sql for name in terminal_names),sql)
            return execute(sql,params,many,context)
        with connection.execute_wrapper(no_terminal):
            for family in ('excess','fulfillment'):
                rows=grid.read_grid(self.run,{},family=family,paging=None,read_binding=bound)
                self.assertTrue(rows)
                expected=(excess_grid_rows(excess_views.joined_rows(output,excess,self.run.business_date,predicate=lambda *_:6))
                    if family=='excess' else fulfillment_grid_rows(fulfillment_views.joined_rows(output,fulfillment['summary'],predicate=lambda *_:6),
                                                                  fulfillment_views.detail_aliases(fulfillment['details'])))
                self.assertEqual(rows,expected)
                self.assertEqual(grid.read_grid(self.run,{},family=family,paging=(1,2),read_binding=bound),rows[:2])
                self.assertEqual(grid.read_grid(self.run,{},family=family,paging=None,count=True,read_binding=bound),
                    6*len(bound.rows(family+'_grid')))
                self.assertEqual(grid.read_grid(self.run,{},family=family,paging=(1000,2),read_binding=bound),[])
                value=custom.custom_grid(self.run,{},None,family=family,read_binding=bound)
                self.assertTrue(value['data'])
                context=SimpleNamespace(output=output,business_date=self.run.business_date,
                    rows=excess if family=='excess' else fulfillment,
                    nms=bound.prepared.sources.rows('closing/consumer_context/NMSAllItems'),
                    standards=bound.prepared.sources.rows('closing/dbm/SKULocStandardAttributes'))
                selector=excess_read if family=='excess' else fulfillment_read
                with patch.object(selector,'scope',return_value=(products,locations)):
                    self.assertEqual(value,selector.custom_grid(context,{},None))
                self.assertEqual(custom.custom_grid(self.run,{},(1,2),family=family,read_binding=bound)['data'],value['data'][:2])
                chart_output=chart.chart_queries(self.run,{},family,read_binding=bound)
                self.assertTrue(all(chart_output.values()))
                original=dict(ClosingState=[dict(importer=importer)])
                expected=(excess_views.chart_queries(original,excess,self.run.business_date,products=products,locations=locations)
                    if family=='excess' else fulfillment_charts.chart_queries(original,fulfillment,products=products,locations=locations))
                self.assertEqual(chart_output,expected)
            summaries=bound.prepared.reports.rows('OrderFulfillmentSummary')
            details=grid.selected_details(self.run,summaries,read_binding=bound)
            pairs={native_key(r['SKUCode'],r['WhCode']) for r in summaries}
            self.assertEqual(details,[r for r in bound.prepared.reports.rows('OrderFulfillmentDetails')
                                     if native_key(r['SKUCode'],r['WhCode']) in pairs])

    def test_nms_owner_opt_in_is_independent_and_missing_stays_unavailable(self):
        from django.db import connection
        from mta.presentation import scoped_sources,scoped_prepared
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import ScopePlanningProjection
        from mta.runtime.relational_state import load_image
        from mta.runtime import phase_state
        from mta.serialization import storage
        self.parents()
        options=dict(expected_digest=self.receipt.digest,action_revision=0)
        ordinary=scoped_sources.bind(self.receipt.pk,**options)
        extra=scoped_sources.bind(self.receipt.pk,include_nms=True,**options)
        path='closing/consumer_context/NMSAllItems'
        self.assertEqual(extra.source_digest,ordinary.source_digest)
        with self.assertRaises(PublicationUnavailable):ordinary.rows(path)
        actual=extra.metadata(path)
        self.assertEqual(extra.rows(path),load_image(self.run,actual,table_registry=phase_state.REGISTRY))
        with connection.cursor() as c:
            c.execute(*extra.query(path));names=[f[0] for f in c.description]
            rows=[dict(zip(names,r)) for r in c.fetchall()]
        rows.sort(key=lambda r:r['vf_ordinal'])
        for i,r in enumerate(rows):self.assertEqual(r.pop('vf_ordinal'),i)
        self.assertEqual(storage(rows),extra.rows(path))
        # Simulate only absent metadata for this optional image. The actual
        # sealed component owner/rows remain intact, and independent default
        # fact/source admission is exercised in the same context.
        original=scoped_sources._image
        def missing(manifest,node):return None if node==('state','nms','NMSAllItems') else original(manifest,node)
        with patch.object(scoped_sources,'_image',side_effect=missing):
            with self.assertRaisesRegex(PublicationUnavailable,'source_unavailable'):self.prepare()
            independent=scoped_prepared.bind(self.report.pk,expected_digest=self.source.digest,
                expected_report_digest=self.report.digest,action_revision=0)
            self.assertEqual(independent.sources.source_digest,ordinary.source_digest)
        self.assertFalse(ScopePlanningProjection.objects.filter(generation=self.report).exists())
        bound=self.binding(self.prepare())
        self.assertEqual(bound.projection.metadata['nms_source'],extra.provenance(path))


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedPlanningFullCoexistenceTests(unittest.TestCase):
    from tests import test_scoped_common_final_postgresql as _fixtures
    for _name in ('setUp','rollback','owner','accept','prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(_fixtures.ScopedCommonFinalTests,_name)

    def test_same_run_actual_full_report_build_retains_all_partial_bags(self):
        from django.db import connection
        from django.utils import timezone
        from mta.presentation import scoped_report_storage as facts,scoped_prepared as sources,scoped_planning as module,operational_reports as full
        from mta.runtime.models import RunPhaseAcceptance,DailyReportGeneration
        from mta.serialization import digest
        self.owner(claim=False);self.prepare_dbm()
        phase=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        reports=facts.prepare(phase.pk,expected_digest=phase.digest,action_revision=0)
        source=sources.prepare(reports.pk,expected_report_digest=reports.digest,action_revision=0)
        options=dict(expected_source_digest=source.digest,expected_report_digest=reports.digest,action_revision=0)
        projection=module.prepare(reports.pk,**options)
        bound=module.bind(reports.pk,expected_digest=projection.digest,**options)
        before={name:bound.rows(name) for name in module.TABLES};identity=bound.read_identity
        result=self.finish();self.assertEqual((result.pk,result.status),(reports.run_id,'SUCCEEDED'))
        terminal=DailyReportGeneration.objects.create(run=result,source_digest=result.production_digest,recipe_digest=full.recipe_identity())
        with connection.cursor() as c:c.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(result.pk)])
        terminal.metadata=full._build(result);terminal.digest=digest(terminal.metadata);terminal.status='READY';terminal.sealed_at=timezone.now()
        terminal.save(update_fields=['metadata','digest','status','sealed_at'])
        full.verify_rows(result,full.generation(result).metadata)
        rebound=module.bind(reports.pk,expected_digest=projection.digest,**options)
        self.assertEqual({name:rebound.rows(name) for name in module.TABLES},before)
        self.assertEqual(bound.read_identity,identity);self.assertEqual(rebound.read_identity,identity)
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')


if __name__=='__main__':unittest.main()
