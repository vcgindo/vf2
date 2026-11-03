"""Parent ingredients use immutable core occurrences and fixed real remark cuts."""
import os
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from tests import test_scoped_expedite_pick_queries_postgresql as fixture
from tests import test_scoped_expedite_queries_postgresql as ordinary_fixture
from tests import test_scoped_common_final_postgresql as full_fixture


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedExpediteParentTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr','parents','fetch','rows','match','facts','grid'):
        locals()[_name]=getattr(fixture.ScopedExpeditePickQueriesTests,_name)
    row=staticmethod(fixture.ScopedExpeditePickQueriesTests.row)
    for _name in ('prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(full_fixture.ScopedCommonFinalTests,_name)

    def owner(self,**options):
        from tests import test_h3_daily_integration as supplied
        from tests.production_h3_fixture import SEASON,CHILD
        frame=supplied.frame()
        if getattr(self,'action_case',False):
            for state,name in ((frame['opening']['state']['dbm'],'Suggestions'),(frame['opening']['state']['controls'],'suggestions')):
                state[name]=[dict(SKUCode=SEASON,WhCode=CHILD,Type=1,NewNorm=24)]
        with patch.object(supplied,'frame',return_value=frame):fixture.ScopedExpeditePickQueriesTests.owner(self,**options)

    def dependencies(self,revision=0):
        from mta.presentation import scoped_report_storage as facts,scoped_prepared,scoped_pick_storage,scoped_expedite_storage as core
        self.report=facts.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=revision)
        self.projection=scoped_prepared.prepare(self.report.pk,expected_report_digest=self.report.digest,action_revision=revision)
        self.pick=scoped_pick_storage.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=revision)
        self.core_row=core.prepare(self.report.pk,expected_report_digest=self.report.digest,expected_source_digest=self.projection.digest,
            pick_generation_id=self.pick.pk,expected_pick_digest=self.pick.digest,action_revision=revision)
        self.core=core.bind(self.core_row.pk,expected_digest=self.core_row.digest,action_revision=revision)

    def prepare(self,revision=0):
        from mta.presentation.scoped_expedite_parent import prepare
        return prepare(self.core_row.pk,expected_core_digest=self.core_row.digest,action_revision=revision)

    def binding(self,row,revision=0):
        from mta.presentation.scoped_expedite_parent import bind
        return bind(row.pk,expected_digest=row.digest,action_revision=revision)

    def expected(self):
        from mta.presentation import scoped_remarks,rrr
        from mta.serialization import storage
        prepared=self.core.prepared;self.bound=prepared
        remarks=scoped_remarks.bind(prepared.sources,configuration_digest=self.core_row.configuration_digest)
        history=self.fetch(remarks.query());history.sort(key=lambda r:r['vf_ordinal'])
        base=[]
        for i,n in enumerate(prepared.sources.rows('closing/consumer_context/NMSAllItems')):
            rows=[r for r in history if ordinary_fixture.same(n['SKUCode'],r['SKUCode']) and ordinary_fixture.same(n['WhCode'],r['WhCode'])]
            for r in rows or [None]:
                base.append(dict(ordinal=len(base),nms_ordinal=i,remark_ordinal=None if r is None else r['vf_ordinal'],
                    sku_code=n['SKUCode'],location_code=n['WhCode'],sku_key=ordinary_fixture.k(n['SKUCode']),
                    location_key=ordinary_fixture.k(n['WhCode']),rlt=n['RLT'],remark=None if r is None else r['Remark'],
                    remark_key=None if r is None else ordinary_fixture.k(r['Remark'])))
        raw=rrr.pick_rows(prepared.sources.rows('reports/bpr/vf_RationedReqReport'),prepared.sources.rows('sources/calculation/PickBands'))
        from mta.presentation.scoped_expedite_pick_queries import GRID_ORDER
        grids=[]
        for branch in ('dispatch','availability'):
            rows=sorted(self.grid('parent',branch),key=lambda r:tuple((r[f] is not None,r[f]) for f in GRID_ORDER))
            grids.extend(dict(branch=branch,ordinal=i,fact_ordinal=r['fact_ordinal']) for i,r in enumerate(rows))
        facts=dict(self.facts());history={r['vf_ordinal']:r for r in history};matches=[]
        for b in base:
            r=history.get(b['remark_ordinal'])
            if r is None:continue
            for g in grids:
                a=facts[g['fact_ordinal']]
                if not(ordinary_fixture.same(a['SKUCode'],r['SKUCode']) and ordinary_fixture.same(a['WhCode'],r['WhCode'])):continue
                picked=[(i,p) for i,p in enumerate(raw) if ordinary_fixture.same(p['SKUCode'],a['SKUCode']) and ordinary_fixture.same(p['WhCode'],a['WhCode'])]
                for i,p in picked or [(None,{})]:
                    matches.append(dict(base_ordinal=b['ordinal'],branch=g['branch'],grid_ordinal=g['ordinal'],
                        pick_ordinal=i,parent_stock=p.get('ParentStockForRationing')))
        matches.sort(key=lambda r:tuple((r[f] is not None,r[f]) for f in ('base_ordinal','branch','grid_ordinal','pick_ordinal')))
        return storage(dict(base=base,match=[dict(r,ordinal=i) for i,r in enumerate(matches)]))

    def start(self,boundary=None,*,empty=False):
        self.external_boundary=boundary
        stamp=datetime(2037,4,9,tzinfo=timezone.utc)
        self.parents(rows=[] if empty else [self.row(None,stamp),self.row('same',stamp),self.row('same',stamp)],counter=True,consumer_cut=True)
        self.dependencies()

    def complete(self,boundary=None,*,empty=False):
        from mta.presentation import scoped_expedite_parent as module,scoped_expedite_queries as ordinary
        from mta.runtime.scope_revisions import require_current
        from mta.serialization import storage
        self.start(boundary,empty=empty);before=require_current(self.run);expected=self.expected()
        with patch.object(ordinary,'grid_occurrences',side_effect=AssertionError('core grid rebuild')):
            row=self.prepare()
        bound=self.binding(row)
        for name in module.TABLES:
            self.assertEqual(bound.rows(name),expected[name])
            sql,params=bound.query(name);rows=self.fetch((sql+' ORDER BY R.ordinal',params))
            self.assertTrue(all(r.pop('run_id')==self.run.pk for r in rows));self.assertEqual(storage(rows),expected[name])
        with patch.object(module,'_inserts',side_effect=AssertionError('parent rebuild')), \
                patch.object(module,'_match_query',side_effect=AssertionError('match rebuild')):
            self.assertEqual(self.prepare().pk,row.pk);self.assertEqual(self.binding(row).read_identity,bound.read_identity)
        self.assertEqual(require_current(self.run),before)
        if boundary in ('dispatch','availability') and not empty:self.assertTrue(expected['match'])
        if empty:
            self.assertTrue(expected['base']);self.assertFalse(expected['match'])
            self.assertTrue(all(r['remark_ordinal'] is None for r in expected['base']))

    def test_complete_default_duplicate_and_null_captured_remarks(self):self.complete()
    def test_complete_dispatch_matches_without_core_rebuild(self):self.complete('dispatch')
    def test_complete_availability_matches_without_core_rebuild(self):self.complete('availability')
    def test_explicit_empty_remarks_preserve_nms_left_rows(self):self.complete('dispatch',empty=True)

    def test_retained_parent_recipe_is_readable_and_reused_without_rebuild(self):
        from mta.presentation import scoped_expedite_parent as module
        self.start('dispatch')
        with patch.object(module,'recipe_digest',return_value=module.RETAINED_RECIPE):row=self.prepare()
        before=self.binding(row).read_identity
        self.assertNotEqual(row.recipe_digest,module.recipe_digest())
        with patch.object(module,'_inserts',side_effect=AssertionError('accepted parent rebuild')):
            self.assertEqual(self.prepare().pk,row.pk)
        self.assertEqual(self.binding(row).read_identity,before)
        self.assertEqual({name:self.binding(row).rows(name) for name in module.TABLES},self.expected())

    def test_temp_preparer_recipe_is_readable_and_reused_without_rebuild(self):
        from mta.presentation import scoped_expedite_parent as module
        self.start('dispatch')
        with patch.object(module,'recipe_digest',return_value=module.TEMP_RECIPE):row=self.prepare()
        before=self.binding(row).read_identity
        with patch.object(module,'_inserts',side_effect=AssertionError('accepted parent rebuild')):
            self.assertEqual(self.prepare().pk,row.pk)
        self.assertEqual(self.binding(row).read_identity,before)
        self.assertEqual({name:self.binding(row).rows(name) for name in module.TABLES},self.expected())

    def test_match_statement_failure_rolls_back_temporary_operands_and_parent(self):
        from contextlib import contextmanager
        from django.db import connection,DatabaseError
        from mta.presentation import scoped_expedite_parent as module
        self.start('dispatch');original=module._prepared_match;before=self.core.read_identity
        @contextmanager
        def failed(*args):
            with original(*args) as (query,params):
                yield query.replace('P.parent_stock FROM','(1/0)::numeric AS parent_stock FROM'),params
        with patch.object(module,'_prepared_match',failed),self.assertRaises(DatabaseError):self.prepare()
        for model in module.TABLES.values():self.assertEqual(model.objects.count(),0)
        self.assertEqual(module.models.ScopeExpediteParentGeneration.objects.count(),0)
        with connection.cursor() as c:
            c.execute("SELECT count(*) FROM pg_class WHERE relnamespace=pg_my_temp_schema() AND relname LIKE 'vf_transit_%%'")
            self.assertEqual(c.fetchone()[0],0)
        self.assertEqual(self.core.read_identity,before)
        self.assertTrue(self.binding(self.prepare()).rows('match'))

    def test_missing_capture_denies_but_retains_independent_core(self):
        from mta.presentation.context import PublicationUnavailable
        self.parents(missing=True);self.dependencies();before=self.core.read_identity
        with self.assertRaises(PublicationUnavailable):self.prepare()
        self.assertEqual(self.core.read_identity,before);self.assertTrue(self.core.rows('chart'))

    def test_live_append_gapped_cutoff_and_future_prefix_reuses_exact_core(self):
        from mta.presentation import ancillary_live as live,scoped_expedite_parent as module,scoped_expedite_queries as ordinary
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.scope_revisions import require_current
        self.start('dispatch');row=self.prepare();bound=self.binding(row);before={n:bound.rows(n) for n in module.TABLES}
        core_before={n:self.core.rows(n) for n in ('grid','custom','chart','prepost')};core_identity=self.core.read_identity
        cutoff=bound.remarks.cutoff;future=datetime(2037,4,11,tzinfo=timezone.utc)
        for text,stamp in (('excluded-at-cutoff',cutoff),('visible-future',future)):
            value=self.row(text,stamp)
            live.append(live.BPR,[{k:v for k,v in value.items() if k!='RemarkDate'}],actor_id='parent-prefix',timestamp=stamp)
        after_append=require_current(self.run)
        self.assertEqual({n:bound.rows(n) for n in module.TABLES},before)
        with self.assertRaises(PublicationUnavailable):self.binding(row)
        with patch.object(ordinary,'grid_occurrences',side_effect=AssertionError('core rebuild')):
            fresh=self.prepare()
        current=self.binding(fresh);self.assertNotEqual(row.pk,fresh.pk)
        self.assertEqual(fresh.core_generation_id,row.core_generation_id);self.assertEqual(current.core.read_identity,core_identity)
        self.assertEqual({n:current.core.rows(n) for n in core_before},core_before)
        self.assertEqual({n:current.rows(n) for n in module.TABLES},self.expected())
        self.assertTrue(any(r['remark']=='visible-future' for r in current.rows('base')))
        self.assertFalse(any(r['remark']=='excluded-at-cutoff' for r in current.rows('base')))
        ordinals=[r['remark_ordinal'] for r in current.rows('base') if r['remark_ordinal'] is not None]
        self.assertIn(bound.remarks.row_count+1,ordinals);self.assertNotIn(bound.remarks.row_count,ordinals)
        self.assertEqual(require_current(self.run),after_append)

    def test_late_failure_rolls_back_only_parent_and_input_counters(self):
        from mta.presentation import scoped_expedite_parent as module
        from mta.runtime.scope_revisions import require_current
        self.start('dispatch');before=require_current(self.run);identity=self.core.read_identity
        with patch.object(module,'_receipt',side_effect=OSError('late parent checksum')),self.assertRaises(OSError):self.prepare()
        self.assertEqual(module.models.ScopeExpediteParentGeneration.objects.count(),0)
        for model in module.TABLES.values():self.assertEqual(model.objects.count(),0)
        self.assertEqual(require_current(self.run),before);self.assertEqual(self.core.read_identity,identity)
        self.assertTrue(self.binding(self.prepare()).rows('match'))

    def candidate(self,row):
        from mta.runtime.models import ScopeExpediteParentGeneration
        return ScopeExpediteParentGeneration(**{f.attname:getattr(row,f.attname) for f in ScopeExpediteParentGeneration._meta.local_fields
            if f.name not in ('id','metadata','digest','sealed','sealed_at','created_at','recipe_digest')},recipe_digest='f'*64)

    def forge(self,row,change):
        from mta.presentation import scoped_expedite_parent as module
        from mta.serialization import digest
        from django.utils import timezone as django_time
        candidate=self.candidate(row);bound=self.binding(row)
        with module._owner(candidate.pk):
            candidate.save(force_insert=True)
            for name,model in module.TABLES.items():
                rows=[change(name,dict(r)) for r in bound.rows(name)]
                model.objects.bulk_create([model(generation=candidate,**r) for r in rows])
            images={name:module._receipt(candidate.pk,name) for name in module.TABLES}
            candidate.metadata=module._identity(candidate,bound.core,bound.remarks,images);change('metadata',candidate.metadata)
            candidate.digest=digest(candidate.metadata);candidate.sealed=True;candidate.sealed_at=django_time.now()
            candidate.save(update_fields=['metadata','digest','sealed','sealed_at'])

    def test_sql_immutability_late_insert_unsealed_and_wrong_core_denials(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_expedite_parent as module
        self.start('dispatch');row=self.prepare();bound=self.binding(row)
        for table,key in [('fresh_mta_scopeexpediteparentgeneration','id'),*[(m._meta.db_table,'generation_id') for m in module.TABLES.values()]]:
            for sql,params in [('UPDATE mta.'+table+' SET '+key+'='+key+' WHERE '+key+'=%s',[row.pk]),
                    ('DELETE FROM mta.'+table+' WHERE '+key+'=%s',[row.pk]),('TRUNCATE mta.'+table,[])]:
                with self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as c:c.execute(sql,params)
        values=dict(bound.rows('base')[0]);values['ordinal']=len(bound.rows('base'))
        with self.assertRaisesRegex(DatabaseError,'unsealed generation'),transaction.atomic():module.TABLES['base'].objects.create(generation=row,**values)
        candidate=self.candidate(row)
        with self.assertRaisesRegex(DatabaseError,'Unsealed scope Expedite parent'),transaction.atomic():
            with module._owner(candidate.pk):candidate.save(force_insert=True)
            with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
        for field,value in (('core_generation_digest','e'*64),('remark_highwater',row.remark_highwater+1),
                ('remark_watermark',row.remark_watermark+1),('remark_rows_digest','e'*64)):
            candidate=self.candidate(row);setattr(candidate,field,value)
            with self.assertRaisesRegex(DatabaseError,'exact core and captured remark prefix'),transaction.atomic():
                with module._owner(candidate.pk):candidate.save(force_insert=True)

    def test_sql_seal_denies_nms_remark_base_grid_pick_and_provenance_mismatches(self):
        from django.db import transaction,DatabaseError
        self.start('dispatch');row=self.prepare()
        for name,field,value in [('base','nms_ordinal',999999),('base','remark_ordinal',999999),
                ('match','base_ordinal',999999),('match','grid_ordinal',999999),('match','pick_ordinal',999999),('match','branch','unknown')]:
            def change(bag,record):
                if bag==name:record[field]=value
                return record
            with self.subTest(field=field),self.assertRaisesRegex(DatabaseError,'source references differ'),transaction.atomic():self.forge(row,change)
        def wrong(bag,record):
            if bag=='metadata':record['occurrences']['remarks']['live_highwater']+=1
            return record
        with self.assertRaisesRegex(DatabaseError,'remark provenance differs'),transaction.atomic():self.forge(row,wrong)

    def test_guard_digest_recipe_and_wrong_run_denials(self):
        from django.db import connection,transaction
        from mta.runtime.models import CalculationRun
        from mta.presentation import scoped_expedite_parent as module
        from mta.presentation.context import PublicationUnavailable
        self.start('dispatch');row=self.prepare();old=self.binding(row);before=old.rows('match')
        with self.assertRaises(PublicationUnavailable):module.bind(row.pk,expected_digest='f'*64,action_revision=0)
        with patch.object(module,'recipe_digest',return_value='f'*64),self.assertRaises(PublicationUnavailable):self.binding(row)
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE');c.execute('SET CONSTRAINTS ALL DEFERRED')
        with transaction.atomic():
            with connection.cursor() as c:c.execute('ALTER TABLE mta.fresh_mta_scopeexpediteparentbase DISABLE TRIGGER scope_expedite_parent_rows_insert')
            with self.assertRaisesRegex(PublicationUnavailable,'guard_coverage'):self.binding(row)
            transaction.set_rollback(True)
        # The owned baseline already retains foreign runs. Do not mutate a new
        # MDM source after this test has certified its intake owner.
        foreign=CalculationRun.objects.exclude(pk=self.run.pk).first()
        self.assertIsNotNone(foreign)
        with self.assertRaises(PublicationUnavailable):module.require_binding(foreign,old)
        self.assertEqual(old.rows('match'),before)

    def test_actual_sleep_invalidates_fresh_parent_and_preserves_inflight(self):
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.runtime.scoped_actions import record
        from mta.presentation.context import PublicationUnavailable
        from tests.production_h3_fixture import SEASON,CHILD
        self.action_case=True;self.start('dispatch');row=self.prepare();bound=self.binding(row)
        before={n:bound.rows(n) for n in ('base','match')}
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        event=record(self.run.pk,phase_id=self.receipt.pk,phase_digest=self.receipt.digest,expected_revision=0,
            operation='SLEEP',selected=[[SEASON,CHILD]],timestamp='2037-04-10T10:00:00',actor='owned-parent',idempotency_key='parent-sleep')
        with self.assertRaises(PublicationUnavailable):self.binding(row)
        self.dependencies(event.pk);fresh=self.prepare(event.pk)
        self.assertNotEqual(fresh.pk,row.pk);self.assertNotEqual(fresh.core_generation_id,row.core_generation_id)
        self.assertEqual({n:bound.rows(n) for n in before},before)
        self.assertEqual({n:self.binding(fresh,event.pk).rows(n) for n in before},before)

    def test_same_actual_full_and_report_build_preserve_parent_bags(self):
        from django.db import connection
        from django.utils import timezone as django_time
        from mta.runtime.models import RunPhaseAcceptance,DailyReportGeneration,ExpediteProjection
        from mta.presentation import operational_reports as full
        from mta.presentation import ancillary_live as live
        from mta.serialization import digest
        self.external_boundary='dispatch'
        provenance={'fixture':'parent-full-component'}
        live.initialize_owner(live.BPR,provenance_digest=digest(provenance),provenance_receipt=provenance)
        value=self.row('captured',datetime(2037,4,9,tzinfo=timezone.utc))
        live.append(live.BPR,[{k:v for k,v in value.items() if k!='RemarkDate'}],actor_id='component',timestamp=value['RemarkDate'])
        self.snapshot=live.snapshot_all(business_date='2037-04-10',bpr_remark_horizon=13)
        self.owner(claim=False);self.prepare_dbm()
        self.receipt=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR');self.dependencies()
        row=self.prepare();bound=self.binding(row);before={n:bound.rows(n) for n in ('base','match')}
        self.assertTrue(before['match']);finished=self.finish();self.assertEqual((finished.pk,finished.status),(row.run_id,'SUCCEEDED'))
        terminal=DailyReportGeneration.objects.create(run=finished,source_digest=finished.production_digest,recipe_digest=full.recipe_identity())
        with connection.cursor() as c:c.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(finished.pk)])
        terminal.metadata=full._build(finished);terminal.digest=digest(terminal.metadata);terminal.status='READY';terminal.sealed_at=django_time.now()
        terminal.save(update_fields=['metadata','digest','status','sealed_at']);full.verify_rows(finished,full.generation(finished).metadata)
        self.assertTrue(ExpediteProjection.objects.filter(run=finished).exists())
        self.assertEqual({n:self.binding(row).rows(n) for n in before},before)
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')

    def test_full_scalar_contracts_match(self):
        from mta.runtime import models
        for scoped,full in ((models.ScopeExpediteParentBase,models.PlanningExpediteTransitBase),
                (models.ScopeExpediteParentMatch,models.PlanningExpediteTransitMatch)):
            for field in full._meta.local_fields:
                if field.name not in ('id','run'):self.assertEqual(scoped._meta.get_field(field.name).deconstruct()[1:],field.deconstruct()[1:])
