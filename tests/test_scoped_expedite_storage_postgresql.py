"""Four core Expedite bags under real accepted phase/source/Pick owners."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_expedite_queries_postgresql as fixtures
from tests import test_scoped_pick_storage_postgresql as pick_fixture
from tests import test_scoped_common_final_postgresql as full_fixture


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedExpediteStorageTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr','fetch','rows','match','facts','grid','custom','members'):
        locals()[_name]=getattr(fixtures.ScopedExpediteQueriesTests,_name)
    owner=pick_fixture.ScopedPickStorageTests.owner
    for _name in ('prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(full_fixture.ScopedCommonFinalTests,_name)

    def dependencies(self,revision=0):
        from mta.presentation import scoped_report_storage as facts,scoped_prepared,scoped_pick_storage
        self.report=facts.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=revision)
        self.source=scoped_prepared.prepare(self.report.pk,expected_report_digest=self.report.digest,action_revision=revision)
        self.pick=scoped_pick_storage.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=revision)
        self.bound=scoped_prepared.bind(self.report.pk,expected_digest=self.source.digest,
            expected_report_digest=self.report.digest,action_revision=revision,include_nms=True)

    def parents(self,**options):
        self.bpr(**options);self.dependencies()

    def prepare(self,revision=0):
        from mta.presentation.scoped_expedite_storage import prepare
        return prepare(self.report.pk,expected_report_digest=self.report.digest,expected_source_digest=self.source.digest,
            pick_generation_id=self.pick.pk,expected_pick_digest=self.pick.digest,action_revision=revision)

    def binding(self,row,revision=0):
        from mta.presentation.scoped_expedite_storage import bind
        return bind(row.pk,expected_digest=row.digest,action_revision=revision)

    def expected(self):
        from mta.presentation import scoped_expedite_storage as module,rrr
        expected={name:[] for name in module.TABLES}
        for direction in ('parent','child'):
            for branch in ('dispatch','availability'):
                rows=sorted(self.grid(direction,branch),key=lambda r:tuple((r[f] is not None,r[f]) for f in module.ORDERS['grid']))
                expected['grid'] += [dict(r,direction=direction,branch=branch,ordinal=i) for i,r in enumerate(rows)]
        rows=sorted(self.custom(),key=lambda r:tuple((r[f] is not None,r[f]) for f in module.ORDERS['custom']))
        expected['custom']=[dict(r,ordinal=i) for i,r in enumerate(rows)]
        for direction,family in module.GRAINS:
            rows=sorted(self.members(direction,family),key=lambda r:tuple((r[f] is not None,r[f]) for f in module.ORDERS['chart']))
            expected['chart'] += [dict(r,direction=direction,family=family,ordinal=i) for i,r in enumerate(rows)]
        raw=rrr.pick_rows(self.bound.sources.rows('reports/bpr/vf_RationedReqReport'),self.bound.sources.rows('sources/calculation/PickBands'))
        for s,source in enumerate(raw):
            n=sum(fixtures.same(row['ParentWhCode'],source['WhCode']) for row in raw)
            for t,target in enumerate(raw):
                if (n and fixtures.same(source['SKUCode'],target['SKUCode']) and fixtures.same(source['WhCode'],target['WhCode'])
                        and target['WhCode'] is not None and target['ParentWhCode'] is not None
                        and not fixtures.same(target['WhCode'],target['ParentWhCode'])):
                    expected['prepost'].append(dict(scope_ordinal=s,fact_ordinal=t,multiplicity=n,ordinal=len(expected['prepost'])))
        for name,rows in expected.items():rows.sort(key=lambda r:tuple(r[f] for f in (*module.GROUPS[name],'ordinal')))
        return expected

    def complete(self,boundary=None,*,empty=False,virtual=False):
        from mta.presentation import scoped_expedite_storage as module,scoped_expedite_queries as queries,scoped_pick_storage
        from mta.serialization import storage
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.models import PlanningExpediteGridProjection,PlanningExpediteChartProjection
        self.external_boundary=boundary;self.pick_empty_case=empty;self.virtual_case=virtual
        self.parents(counter=True);before=require_current(self.run);expected=self.expected()
        row=self.prepare();bound=self.binding(row)
        for name in module.TABLES:
            self.assertEqual(bound.rows(name),storage(expected[name]))
            sql,params=bound.query(name)
            actual=self.fetch((sql+' ORDER BY '+','.join('R.'+f for f in (*module.GROUPS[name],'ordinal')),params))
            self.assertTrue(all(r.pop('run_id')==self.run.pk for r in actual))
            self.assertEqual(storage(actual),storage(expected[name]))
        with patch.object(queries,'grid_occurrences',side_effect=AssertionError('grid rebuild')), \
                patch.object(scoped_pick_storage.PickBinding,'pick_query',side_effect=AssertionError('Pick rebuild')):
            self.assertEqual(self.prepare().pk,row.pk)
            self.assertEqual(self.binding(row).read_identity,bound.read_identity)
        self.assertEqual(require_current(self.run),before)
        self.assertFalse(PlanningExpediteGridProjection.objects.filter(run=self.run).exists())
        self.assertFalse(PlanningExpediteChartProjection.objects.filter(run=self.run).exists())
        if boundary=='dispatch':self.assertTrue(expected['grid']);self.assertTrue(expected['custom'])
        if boundary=='availability':self.assertTrue(expected['grid'])
        if empty:self.assertTrue(all(not rows for rows in expected.values()))

    def test_complete_default_receiving_and_virtual_pick_reference(self):self.complete(virtual=True)

    def test_complete_positive_dispatch_grids_custom_and_charts(self):self.complete('dispatch')

    def test_complete_positive_availability_and_nil_stock_charts(self):self.complete('availability')

    def test_owned_empty_four_bags(self):self.complete(empty=True)

    def test_late_readback_failure_rolls_back_only_core_bags_and_counters(self):
        from mta.presentation import scoped_expedite_storage as module
        from mta.runtime.models import ScopeExpediteGeneration
        from mta.runtime.scope_revisions import require_current
        self.external_boundary='dispatch';self.parents(counter=True);before=require_current(self.run)
        with patch.object(module,'_receipt',side_effect=OSError('late Expedite checksum')),self.assertRaises(OSError):self.prepare()
        self.assertEqual(ScopeExpediteGeneration.objects.count(),0)
        for model in module.TABLES.values():self.assertEqual(model.objects.count(),0)
        self.assertEqual(require_current(self.run),before)
        self.assertTrue(self.binding(self.prepare()).rows('grid'))

    def candidate(self,row):
        from mta.runtime.models import ScopeExpediteGeneration
        return ScopeExpediteGeneration(**{f.attname:getattr(row,f.attname) for f in ScopeExpediteGeneration._meta.local_fields
            if f.name not in ('id','metadata','digest','sealed','sealed_at','created_at','recipe_digest')},recipe_digest='f'*64)

    def forge(self,row,*,change=None,extra=None):
        from mta.presentation import scoped_expedite_storage as module
        from mta.serialization import digest
        from django.utils import timezone
        candidate=self.candidate(row);bound=self.binding(row)
        with module._owner(candidate.pk):
            candidate.save(force_insert=True)
            for name,model in module.TABLES.items():
                rows=bound.rows(name)
                if change:rows=[change(name,dict(r)) for r in rows]
                model.objects.bulk_create([model(generation=candidate,**r) for r in rows])
            if extra:extra(candidate)
            images={name:module._receipt(candidate.pk,name) for name in module.TABLES}
            candidate.metadata=module._identity(candidate,bound.prepared,bound.pick,images)
            if change:change('metadata',candidate.metadata)
            candidate.digest=digest(candidate.metadata);candidate.sealed=True;candidate.sealed_at=timezone.now()
            candidate.save(update_fields=['metadata','digest','sealed','sealed_at'])

    def test_sql_owner_mutation_late_insert_and_unsealed_commit_denials(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_expedite_storage as module
        self.external_boundary='dispatch';self.parents();row=self.prepare();bound=self.binding(row)
        for table,key in [('fresh_mta_scopeexpeditegeneration','id'),*[(m._meta.db_table,'generation_id') for m in module.TABLES.values()]]:
            for sql,params in [('UPDATE mta.'+table+' SET '+key+'='+key+' WHERE '+key+'=%s',[row.pk]),
                    ('DELETE FROM mta.'+table+' WHERE '+key+'=%s',[row.pk]),('TRUNCATE mta.'+table,[])]:
                with self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as c:c.execute(sql,params)
        values=dict(bound.rows('grid')[0]);values['ordinal']+=1
        with self.assertRaisesRegex(DatabaseError,'unsealed generation'),transaction.atomic():
            module.TABLES['grid'].objects.create(generation=row,**values)
        candidate=self.candidate(row)
        with self.assertRaisesRegex(DatabaseError,'Unsealed scope Expedite'),transaction.atomic():
            with module._owner(candidate.pk):candidate.save(force_insert=True)
            with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
        for field in ('report_generation_digest','source_projection_digest','pick_generation_digest'):
            candidate=self.candidate(row);setattr(candidate,field,'e'*64)
            with self.assertRaisesRegex(DatabaseError,'exact sealed report/source/Pick'),transaction.atomic():
                with module._owner(candidate.pk):candidate.save(force_insert=True)

    def test_sql_seal_rejects_wrong_nms_grain_fact_and_raw_pick_references(self):
        from django.db import transaction,DatabaseError
        from mta.presentation import scoped_expedite_storage as module
        self.external_boundary='dispatch';self.parents();row=self.prepare()
        def nms(name,value):
            if name=='metadata':value['occurrences']['nms']=self.bound.sources.provenance('closing/importer/SkuAttributeData')
            return value
        with self.assertRaisesRegex(DatabaseError,'NMS image provenance differs'),transaction.atomic():self.forge(row,change=nms)
        def grain(name,value):
            if name=='grid' and value['direction']=='parent':value['direction']='unknown'
            return value
        with self.assertRaisesRegex(DatabaseError,'Unknown scoped Expedite'),transaction.atomic():self.forge(row,change=grain)
        def fact(name,value):
            if name=='grid':value['fact_ordinal']=999999
            return value
        with self.assertRaisesRegex(DatabaseError,'source references differ'),transaction.atomic():self.forge(row,change=fact)
        def extra(candidate):
            module.TABLES['prepost'].objects.create(generation=candidate,ordinal=0,scope_ordinal=999999,fact_ordinal=999999,multiplicity=1)
        with self.assertRaisesRegex(DatabaseError,'source references differ'),transaction.atomic():self.forge(row,extra=extra)

    def test_guard_wrong_digest_recipe_run_and_missing_dependency_deny(self):
        from django.db import connection,transaction
        from mta.presentation import scoped_expedite_storage as module
        from mta.presentation.context import PublicationUnavailable
        self.parents();row=self.prepare();old=self.binding(row)
        with self.assertRaises(PublicationUnavailable):module.bind(row.pk,expected_digest='f'*64,action_revision=0)
        with patch.object(module,'recipe_digest',return_value='f'*64),self.assertRaises(PublicationUnavailable):self.binding(row)
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE');c.execute('SET CONSTRAINTS ALL DEFERRED')
        with transaction.atomic():
            with connection.cursor() as c:c.execute('ALTER TABLE mta.fresh_mta_scopeexpeditegrid DISABLE TRIGGER scope_expedite_rows_insert')
            with self.assertRaisesRegex(PublicationUnavailable,'guard_coverage'):self.binding(row)
            transaction.set_rollback(True)
        old_pick=self.pick;before=old.rows('chart');self.parents()
        with self.assertRaises(PublicationUnavailable):module.require_binding(self.run,old)
        with self.assertRaises(PublicationUnavailable):
            module.prepare(self.report.pk,expected_report_digest=self.report.digest,expected_source_digest=self.source.digest,
                pick_generation_id=old_pick.pk,expected_pick_digest=old_pick.digest,action_revision=0)
        self.assertEqual(old.rows('chart'),before)

    def test_actual_sleep_invalidates_fresh_core_but_keeps_inflight(self):
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.runtime.scoped_actions import record
        from mta.presentation import scoped_expedite_storage as module
        from mta.presentation.context import PublicationUnavailable
        from tests.production_h3_fixture import SEASON,CHILD
        self.action_case=True;self.external_boundary='dispatch';self.parents();row=self.prepare();bound=self.binding(row)
        before={name:bound.rows(name) for name in module.TABLES}
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        event=record(self.run.pk,phase_id=self.receipt.pk,phase_digest=self.receipt.digest,expected_revision=0,
            operation='SLEEP',selected=[[SEASON,CHILD]],timestamp='2037-04-10T10:00:00',actor='owned-expedite-core',idempotency_key='expedite-core-sleep')
        with self.assertRaises(PublicationUnavailable):self.binding(row)
        self.dependencies(event.pk);fresh=self.prepare(event.pk)
        self.assertNotEqual(fresh.pk,row.pk)
        self.assertEqual({name:bound.rows(name) for name in module.TABLES},before)
        self.assertEqual({name:self.binding(fresh,event.pk).rows(name) for name in module.TABLES},before)

    def test_same_actual_run_full_finish_preserves_core_bags(self):
        from django.db import connection
        from django.utils import timezone
        from mta.runtime.models import RunPhaseAcceptance,ExpediteProjection,PickProjection,DailyReportGeneration
        from mta.presentation import scoped_expedite_storage as module
        from mta.presentation import operational_reports as full
        from mta.serialization import digest
        self.external_boundary='dispatch';self.owner(claim=False);self.prepare_dbm()
        self.receipt=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR');self.dependencies()
        row=self.prepare();bound=self.binding(row);before={name:bound.rows(name) for name in module.TABLES}
        self.assertTrue(before['grid']);finished=self.finish()
        self.assertEqual((finished.pk,finished.status),(row.run_id,'SUCCEEDED'))
        # Full prepare owns autocommit. Use its unchanged builder/sealer inside
        # this rollback-only component, as in the existing report proofs.
        terminal=DailyReportGeneration.objects.create(run=finished,
            source_digest=finished.production_digest,recipe_digest=full.recipe_identity())
        with connection.cursor() as c:c.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(finished.pk)])
        terminal.metadata=full._build(finished);terminal.digest=digest(terminal.metadata)
        terminal.status='READY';terminal.sealed_at=timezone.now()
        terminal.save(update_fields=['metadata','digest','status','sealed_at'])
        full.verify_rows(finished,full.generation(finished).metadata)
        self.assertTrue(ExpediteProjection.objects.filter(run=finished).exists());self.assertTrue(PickProjection.objects.filter(run=finished).exists())
        self.assertEqual({name:self.binding(row).rows(name) for name in module.TABLES},before)
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')

    def test_full_scalar_contracts_match_for_all_four_bags(self):
        from mta.runtime import models
        pairs=((models.ScopeExpediteGrid,models.PlanningExpediteGridOccurrence),
            (models.ScopeExpediteCustom,models.PlanningExpediteCustomOccurrence),
            (models.ScopeExpediteChartMember,models.PlanningExpediteChartMember),
            (models.ScopeExpeditePrepostMember,models.PlanningExpeditePrepostMember))
        for scoped,full in pairs:
            for field in full._meta.local_fields:
                if field.name not in ('id','run'):
                    self.assertEqual(scoped._meta.get_field(field.name).deconstruct()[1:],field.deconstruct()[1:])
