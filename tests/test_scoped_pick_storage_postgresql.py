"""Phase-owned raw Pick/RRR references; owned rollback-only component proof."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_pick_queries_postgresql as fixtures
from tests import test_scoped_common_final_postgresql as final_fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedPickStorageTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr','parents','fetch','manual_members'):
        locals()[_name]=getattr(fixtures.ScopedPickQueriesTests,_name)
    for _name in ('prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(final_fixtures.ScopedCommonFinalTests,_name)

    def owner(self,**options):
        from tests import test_h3_daily_integration as supplied
        from tests.production_h3_fixture import SEASON,CHILD
        opening=supplied.frame()
        if getattr(self,'action_case',False):
            for state,name in ((opening['opening']['state']['dbm'],'Suggestions'),
                    (opening['opening']['state']['controls'],'suggestions')):
                state[name]=[dict(SKUCode=SEASON,WhCode=CHILD,Type=1,NewNorm=24)]
        with patch.object(supplied,'frame',return_value=opening):
            fixtures.ScopedPickQueriesTests.owner(self,**options)

    def prepare(self,revision=0):
        from mta.presentation.scoped_pick_storage import prepare
        return prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=revision)

    def binding(self,row,revision=0):
        from mta.presentation.scoped_pick_storage import bind
        return bind(row.pk,expected_digest=row.digest,action_revision=revision)

    def complete(self,virtual=False):
        from mta.presentation import scoped_pick_queries as queries,scoped_pick_storage as module
        from mta.runtime.models import PickProjection,RrrPreparedProjection
        from mta.runtime.scope_revisions import require_current
        from mta.serialization import storage
        self.virtual_case=virtual;self.parents(counter=True)
        self.bound=fixtures.ScopedPickQueriesTests.binding(self)
        ctx=queries.bind_sources(self.bound.sources);before=require_current(self.run)
        raw=sorted(self.fetch(ctx.raw_membership_query()),key=lambda r:r['ordinal'])
        members=sorted(self.manual_members(),key=lambda r:tuple((r[k] is not None,r[k]) for k in module.ORDER))
        expected=dict(raw=storage(raw),rrr=storage([dict(r,ordinal=i) for i,r in enumerate(members)]))
        row=self.prepare();bound=self.binding(row)
        for name in module.TABLES:
            self.assertEqual(bound.rows(name),expected[name])
            sql,params=bound.query(name)
            actual=self.fetch((sql+' ORDER BY R.ordinal',params))
            self.assertTrue(all(r.pop('run_id')==self.run.pk for r in actual))
            self.assertEqual(storage(actual),expected[name])
        sql,params=bound.pick_query()
        old_sql,old_params=ctx.pick_query()
        self.assertEqual(self.fetch((sql+' ORDER BY vf_source_ordinal',params)),
            self.fetch((old_sql+' ORDER BY vf_source_ordinal',old_params)))
        self.assertEqual(sum(r['virtual'] for r in raw),int(virtual))
        with patch.object(queries,'bind_sources',side_effect=AssertionError('band reconstruction')):
            self.assertEqual(self.prepare().pk,row.pk)
            self.assertEqual(self.binding(row).provenance()['digest'],row.digest)
        self.assertEqual(require_current(self.run),before)
        self.assertFalse(PickProjection.objects.filter(run=self.run).exists())
        self.assertFalse(RrrPreparedProjection.objects.filter(run=self.run).exists())

    def test_complete_raw_and_rrr_cells_sql_no_rebuild_and_counter_neutrality(self):self.complete()

    def test_virtual_band_and_nullable_reference_cells(self):self.complete(True)

    def test_direct_phase_owner_needs_no_other_report_or_full_receipt(self):
        from mta.presentation import scoped_sources,scoped_pick_queries
        from mta.runtime.models import ScopeReportGeneration,ScopeSourceProjection,PickProjection,RrrPreparedProjection
        self.bpr();row=self.prepare();before=self.binding(row).rows('raw')
        self.assertTrue(before)
        for model in (ScopeReportGeneration,PickProjection,RrrPreparedProjection):
            self.assertFalse(model.objects.filter(run=self.run).exists())
        self.assertFalse(ScopeSourceProjection.objects.filter(generation__run=self.run).exists())
        with patch.object(scoped_sources.BprSources,'rows',side_effect=AssertionError('source rows reconstructed')), \
                patch.object(scoped_pick_queries,'bind_sources',side_effect=AssertionError('producer replay')):
            self.assertEqual(self.prepare().pk,row.pk)
            fresh=self.binding(row)
            self.assertEqual(fresh.rows('raw'),before)
            self.assertTrue(self.fetch(fresh.pick_query()))

    def test_owned_empty_both_bags_and_pick_query(self):
        from mta.presentation.scoped_pick_storage import TABLES
        self.pick_empty_case=True;self.parents();bound=self.binding(self.prepare())
        for name in TABLES:self.assertEqual(bound.rows(name),[])
        self.assertEqual(self.fetch(bound.pick_query()),[])

    def test_sql_mutation_late_insert_and_unsealed_commit_denials(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_pick_storage as module
        from mta.runtime.models import ScopePickGeneration
        self.parents();row=self.prepare();bound=self.binding(row)
        for table,owner in [('fresh_mta_scopepickgeneration','id'),
                *[(m._meta.db_table,'generation_id') for m in module.TABLES.values()]]:
            for sql,params in [('UPDATE mta.'+table+' SET '+owner+'='+owner+' WHERE '+owner+'=%s',[row.pk]),
                    ('DELETE FROM mta.'+table+' WHERE '+owner+'=%s',[row.pk]),('TRUNCATE mta.'+table,[])]:
                with self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as c:c.execute(sql,params)
        for name,model in module.TABLES.items():
            values=dict(bound.rows(name)[0],ordinal=len(bound.rows(name)))
            with self.assertRaisesRegex(DatabaseError,'unsealed generation'),transaction.atomic():
                model.objects.create(generation=row,**values)
        candidate=ScopePickGeneration(run=row.run,phase=row.phase,action_revision=0,
            source_digest=row.source_digest,configuration_digest=row.configuration_digest,recipe_digest='f'*64)
        with self.assertRaisesRegex(DatabaseError,'Unsealed scope Pick'),transaction.atomic():
            with module._owner(candidate.pk):candidate.save(force_insert=True)
            with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
        self.assertFalse(ScopePickGeneration.objects.filter(pk=candidate.pk).exists())

    def forge(self,row,change):
        from django.db import connection
        from django.utils import timezone
        from mta.presentation import scoped_pick_storage as module
        from mta.runtime.models import ScopePickGeneration
        from mta.serialization import digest
        candidate=ScopePickGeneration(run=row.run,phase=row.phase,action_revision=0,
            source_digest=row.source_digest,configuration_digest=row.configuration_digest,recipe_digest='f'*64)
        with module._owner(candidate.pk):
            candidate.save(force_insert=True)
            for name,model in module.TABLES.items():
                fields=module.fields(name);columns=','.join(connection.ops.quote_name(f) for f in fields)
                with connection.cursor() as c:
                    c.execute('INSERT INTO mta.'+model._meta.db_table+' (generation_id,'+columns+') '
                        'SELECT %s,'+columns+' FROM mta.'+model._meta.db_table+' WHERE generation_id=%s',
                        [candidate.pk,row.pk])
            bag=deepcopy(row.metadata['pick']);change(candidate,bag)
            sources=self.binding(row).sources
            candidate.metadata=module._identity(candidate,sources,bag);candidate.digest=digest(candidate.metadata)
            candidate.sealed=True;candidate.sealed_at=timezone.now()
            candidate.save(update_fields=['metadata','digest','sealed','sealed_at'])

    def test_sql_seal_rejects_swapped_genuine_accepted_image_provenance(self):
        from django.db import transaction,DatabaseError
        self.parents();row=self.prepare()
        def swapped(candidate,bag):
            images=bag['inputs']['images']
            a='closing/importer/SkuAttributeData';b='closing/importer/LocationAttributeData'
            self.assertNotEqual(images[a],images[b]);images[a],images[b]=images[b],images[a]
        with self.assertRaisesRegex(DatabaseError,'accepted image provenance differs'),transaction.atomic():
            self.forge(row,swapped)

    def test_sql_seal_rejects_rrr_reference_to_absent_raw_band(self):
        from django.db import transaction,DatabaseError
        self.parents();row=self.prepare()
        # A newly inserted bad reference is transaction-local, under the same
        # unsealed owner; no accepted row or trigger is altered for this probe.
        from mta.presentation import scoped_pick_storage as module
        def corrupt(candidate,bag):
            model=module.TABLES['rrr'];values=dict(self.binding(row).rows('rrr')[0])
            values.update(ordinal=bag['images']['rrr']['count'],band_ordinal=999999)
            model.objects.create(generation=candidate,**values)
            bag['images']['rrr']=module._receipt(candidate.pk,'rrr')
        with self.assertRaisesRegex(DatabaseError,'raw source or RRR references differ'),transaction.atomic():
            self.forge(row,corrupt)

    def test_late_checksum_failure_rolls_back_all_bags_and_counters(self):
        from mta.presentation import scoped_pick_storage as module
        from mta.runtime.models import ScopePickGeneration
        from mta.runtime.scope_revisions import require_current
        self.parents(counter=True);before=require_current(self.run)
        with patch.object(module,'_receipt',side_effect=OSError('late Pick readback')),self.assertRaises(OSError):self.prepare()
        self.assertEqual(ScopePickGeneration.objects.count(),0)
        for model in module.TABLES.values():self.assertEqual(model.objects.count(),0)
        self.assertEqual(require_current(self.run),before)
        self.assertTrue(self.binding(self.prepare()).rows('raw'))

    def test_guard_drift_wrong_phase_digest_recipe_and_revision_deny(self):
        from django.db import connection,transaction
        from mta.presentation import scoped_pick_storage as module
        from mta.presentation.context import PublicationUnavailable
        self.parents();row=self.prepare()
        for options in (dict(expected_digest='f'*64,action_revision=0),dict(expected_digest=row.digest,action_revision=1)):
            with self.assertRaises(PublicationUnavailable):module.bind(row.pk,**options)
        with patch.object(module,'recipe_digest',return_value='f'*64),self.assertRaises(PublicationUnavailable):self.binding(row)
        with self.assertRaises(PublicationUnavailable):
            module.prepare(self.pre_receipt.pk,expected_digest=self.pre_receipt.digest,action_revision=0)
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
        with transaction.atomic():
            with connection.cursor() as c:c.execute('ALTER TABLE mta.fresh_mta_scopepickreference DISABLE TRIGGER scope_pick_view_rows_insert')
            with self.assertRaisesRegex(PublicationUnavailable,'guard_coverage'):self.binding(row)
            transaction.set_rollback(True)
        self.assertTrue(self.binding(row).rows('raw'))

    def test_actual_sleep_invalidates_fresh_binding_and_preserves_inflight(self):
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.runtime.scoped_actions import record
        from tests.production_h3_fixture import SEASON,CHILD
        from mta.presentation.context import PublicationUnavailable
        self.action_case=True;self.parents();row=self.prepare();bound=self.binding(row)
        before={name:bound.rows(name) for name in ('raw','rrr')};pick=self.fetch(bound.pick_query())
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        event=record(self.run.pk,phase_id=self.receipt.pk,phase_digest=self.receipt.digest,expected_revision=0,
            operation='SLEEP',selected=[[SEASON,CHILD]],timestamp='2037-04-10T10:00:00',
            actor='owned-pick-reference-component',idempotency_key='pick-sleep')
        self.assertTrue(event.state_sealed)
        with self.assertRaises(PublicationUnavailable):self.binding(row)
        fresh=self.prepare(event.pk);self.assertNotEqual(fresh.pk,row.pk)
        self.assertEqual({name:bound.rows(name) for name in before},before)
        self.assertEqual(self.fetch(bound.pick_query()),pick)
        self.assertEqual({name:self.binding(fresh,event.pk).rows(name) for name in before},before)

    def test_same_actual_run_full_finish_preserves_both_partial_bags(self):
        from mta.runtime.models import RunPhaseAcceptance,PickProjection,PickBand
        self.owner(claim=False);self.prepare_dbm()
        self.receipt=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        row=self.prepare();bound=self.binding(row);before={name:bound.rows(name) for name in ('raw','rrr')}
        self.assertTrue(before['raw']);self.assertTrue(before['rrr'])
        finished=self.finish();self.assertEqual((finished.pk,finished.status),(row.run_id,'SUCCEEDED'))
        self.assertTrue(PickProjection.objects.filter(run=finished).exists())
        self.assertTrue(PickBand.objects.filter(run=finished).exists())
        self.assertEqual({name:self.binding(row).rows(name) for name in before},before)

    def test_scalar_contract_matches_full_rrr_reference_fields(self):
        from mta.runtime.models import RrrPreparedMembership,ScopeRrrReference
        for field in RrrPreparedMembership._meta.local_fields:
            if field.name not in ('id','run'):
                self.assertEqual(ScopeRrrReference._meta.get_field(field.name).deconstruct()[1:],field.deconstruct()[1:])
