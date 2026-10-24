"""Exact phase read references on real rollback-owned typed component rows."""
from contextlib import ExitStack
from copy import copy,deepcopy
from datetime import datetime,timezone
import os,unittest,uuid
from unittest.mock import patch
from tests.test_scoped_expedite_postgresql import ScopedExpediteTests as Fixture


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedViewTests(unittest.TestCase):
    for name in ('setUp','rollback','accept','bpr','parents','fetch','positive','start','scopes','reads',
            'prepare_dbm','finish','publication_opening'):
        locals()[name]=getattr(Fixture,name)
    row=staticmethod(Fixture.row)

    def owner(self,**options):
        from mta.runtime.production_scope import CONFIGURED_SCHEMA
        from tests.test_scope_runtime_reports import reference
        if not getattr(self,'missing_configuration',False):
            options['scope_request']=dict(schema=CONFIGURED_SCHEMA,scope='UptoBPR',command_key=getattr(self,'native_command_key','view-component'),
                compatibility_digest='a'*64,runtime_reports=reference())
            self.scope_request=options['scope_request']
        Fixture.owner(self,**options)

    def prepare(self,revision=0):
        from mta.presentation.scoped_view import prepare
        return prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=revision)

    def binding(self,view):
        from mta.presentation.scoped_view import bind
        return bind(view.reference.pk,expected_digest=view.reference.digest)

    def no_build(self):
        from mta.presentation import (scoped_report_storage,scoped_prepared,scoped_planning,scoped_git,
            scoped_expedite_storage,scoped_expedite_parent,scoped_pick_storage,scoped_transit_storage)
        from mta.runtime import scoped_pick_files
        stack=ExitStack()
        for module in (scoped_report_storage,scoped_prepared,scoped_planning,scoped_git,
                scoped_expedite_storage,scoped_expedite_parent,scoped_pick_storage,scoped_transit_storage,scoped_pick_files):
            stack.enter_context(patch.object(module,'prepare',side_effect=AssertionError('Reader built '+module.__name__)))
        stack.enter_context(patch.object(scoped_pick_files,'_files',side_effect=AssertionError('Reader scanned files')))
        return stack

    def test_complete_reference_reuses_exact_components_and_binds_without_build_or_file_scan(self):
        from mta.presentation import scoped_view,scoped_requests,planning_expedite_sql
        from mta.runtime.models import ScopeReadReference
        from mta.runtime.scope_revisions import require_current
        self.start();before=require_current(self.run);view=self.prepare()
        self.assertEqual(view.expedite.read_identity,self.reference)
        self.assertEqual(view.pick.generation.pk,self.bound.core.pick.generation.pk)
        self.assertEqual(view.bpr.sources.inherited_btr.provenance(),view.reference.metadata['bpr']['inherited_btr'])
        with self.no_build(),patch.object(scoped_requests.RequestBinding,'_records',side_effect=AssertionError('Hydrated requests')):
            rebound=self.binding(view)
        self.assertEqual(rebound.read_identity,view.read_identity)
        self.assertEqual(self.prepare().read_identity,view.read_identity)
        self.assertEqual(ScopeReadReference.objects.count(),1)
        self.assertEqual(require_current(self.run),before)
        with self.reads():
            counts=planning_expedite_sql.counts(self.run,dict(type='child'),read_binding=rebound.expedite)
        self.assertGreater(sum(counts.values()),0)
        for grain in ('excess_grid','fulfillment_grid','excess_custom','fulfillment_custom','chart_members','chart_displays'):
            self.assertEqual(rebound.planning.rows(grain),view.planning.rows(grain))
        self.assertEqual(rebound.git.rows(),view.git.rows())
        self.assertEqual(self.fetch(rebound.bpr.query('bpr_candidates')),self.fetch(view.bpr.query('bpr_candidates')))

    def test_missing_configuration_denies_before_preparation(self):
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import ScopeReadReference,ScopePlanningProjection,ScopePickFiles
        self.missing_configuration=True;self.start()
        with self.assertRaisesRegex(PublicationUnavailable,'configuration_required'):self.prepare()
        self.assertFalse(ScopeReadReference.objects.exists());self.assertFalse(ScopePlanningProjection.objects.exists())
        self.assertFalse(ScopePickFiles.objects.exists())

    def test_failed_reference_registration_rolls_back_only_new_preparation_and_retry_reuses_bpr(self):
        from mta.presentation import scoped_view
        from mta.runtime.models import ScopeReadReference,ScopeGitGeneration,ScopePlanningProjection,ScopePickFiles
        self.start();phases=list(self.run.phase_acceptances.values_list('id','digest'));core=self.bound.core.generation.pk
        with patch.object(scoped_view,'_bind',side_effect=OSError('late reference validation')),self.assertRaisesRegex(OSError,'late reference'):
            self.prepare()
        for model in (ScopeReadReference,ScopeGitGeneration,ScopePlanningProjection,ScopePickFiles):self.assertFalse(model.objects.exists())
        with patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('BPR replay')):
            view=self.prepare()
        self.assertEqual(view.expedite.core.generation.pk,core)
        self.assertEqual(list(self.run.phase_acceptances.values_list('id','digest')),phases)

    def test_sql_immutability_and_metadata_or_foreign_owner_denial(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_view
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import ScopeReadReference
        self.start();view=self.prepare();row=view.reference
        for operation in (lambda:ScopeReadReference.objects.update(digest='f'*64),lambda:ScopeReadReference.objects.all().delete(),
                lambda:connection.cursor().execute('TRUNCATE mta.fresh_mta_scopereadreference CASCADE')):
            with self.assertRaises(DatabaseError),transaction.atomic():operation()
        for changed in (dict(git_generation_id=uuid.uuid4()),dict(pick_files_id=uuid.uuid4()),
                dict(runtime_reports_digest='f'*64),dict(metadata=dict(row.metadata,runtime_reports={}))):
            bad=copy(row);bad.pk=uuid.uuid4();bad.digest=uuid.uuid4().hex*2
            for field,value in changed.items():setattr(bad,field,value)
            with self.assertRaises(DatabaseError),transaction.atomic(),scoped_view._owner(bad.pk):bad.save(force_insert=True)
        with self.assertRaises(PublicationUnavailable):scoped_view.bind(row.pk,expected_digest='f'*64)
        bad=copy(row);bad.metadata=deepcopy(row.metadata);bad.metadata['scope_request_digest']='f'*64
        from mta.serialization import digest
        bad.digest=digest(bad.metadata)
        with patch.object(ScopeReadReference.objects,'select_related') as manager:
            manager.return_value.get.return_value=bad
            with self.assertRaises(PublicationUnavailable):scoped_view.bind(row.pk,expected_digest=bad.digest)

    def test_real_append_refresh_only_rebuilds_parent_and_recovers_same_reference(self):
        from mta.presentation import scoped_view,ancillary_live,scoped_expedite_parent
        from mta.presentation.context import PublicationUnavailable
        self.start();old=self.prepare();before=old.expedite.parent.rows('base')
        value=self.row('new live prefix',datetime(2037,4,11,tzinfo=timezone.utc))
        ancillary_live.append(ancillary_live.BPR,[{k:v for k,v in value.items() if k!='RemarkDate'}],actor_id='view',timestamp=value['RemarkDate'])
        with self.assertRaises(PublicationUnavailable):self.binding(old)
        with patch.object(scoped_expedite_parent,'_receipt',side_effect=OSError('late parent failure')),self.assertRaises(OSError):
            scoped_view.refresh_parent(old.reference.pk,expected_digest=old.reference.digest)
        with ExitStack() as stack:
            from mta.presentation import scoped_report_storage,scoped_prepared,scoped_planning,scoped_git,scoped_expedite_storage,scoped_pick_storage,scoped_transit_storage
            for module in (scoped_report_storage,scoped_prepared,scoped_planning,scoped_git,scoped_expedite_storage,scoped_pick_storage,scoped_transit_storage):
                stack.enter_context(patch.object(module,'prepare',side_effect=AssertionError('Independent rebuild')))
            fresh=scoped_view.refresh_parent(old.reference.pk,expected_digest=old.reference.digest)
        self.assertNotEqual(fresh.read_identity,old.read_identity)
        for field in ('report_generation_id','git_generation_id','pick_files_id'):
            self.assertEqual(getattr(fresh.reference,field),getattr(old.reference,field))
        self.assertEqual(fresh.pick.generation.pk,old.pick.generation.pk)
        self.assertEqual(fresh.expedite.core.generation.pk,old.expedite.core.generation.pk)
        self.assertEqual(old.expedite.parent.rows('base'),before)
        self.assertTrue(any(row['remark']=='new live prefix' for row in fresh.expedite.parent.rows('base')))
        self.assertEqual(scoped_view.refresh_parent(fresh.reference.pk,expected_digest=fresh.reference.digest).read_identity,fresh.read_identity)

    def test_sleep_changes_action_reference_and_retains_inflight_rows(self):
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.runtime.scoped_actions import record
        from mta.presentation.context import PublicationUnavailable
        from tests.production_h3_fixture import SEASON,CHILD
        self.action_case=True;self.start();old=self.prepare();before=old.expedite.parent.rows('match')
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        event=record(self.run.pk,phase_id=self.receipt.pk,phase_digest=self.receipt.digest,expected_revision=0,operation='SLEEP',
            selected=[[SEASON,CHILD]],timestamp='2037-04-10T10:00:00',actor='view',idempotency_key='view-sleep')
        with self.assertRaises(PublicationUnavailable):self.binding(old)
        fresh=self.prepare(event.pk)
        self.assertEqual(fresh.reference.metadata['action_revision'],event.pk)
        self.assertNotEqual(fresh.read_identity,old.read_identity)
        self.assertEqual(old.expedite.parent.rows('match'),before)

    def test_actual_other_reference_components_cannot_cross_runs(self):
        from django.db import DatabaseError,transaction
        from mta.presentation import scoped_view
        # These two independently calculated owners share declared external
        # captures. Initialize each global fact owner once, and avoid creating
        # another source after certifying the first source's intake metadata.
        original=self.parents
        with patch.object(self,'parents',side_effect=lambda **options:original(**dict(options,counter=False,consumer_cut=False))):
            self.start()
        first=self.prepare();self.bpr(counter=False);second=self.prepare()
        for changes in (dict(git_generation_id=second.reference.git_generation_id),
                dict(expedite_parent_generation_id=second.reference.expedite_parent_generation_id),
                dict(pick_files_id=second.reference.pick_files_id)):
            row=copy(first.reference);row.pk=uuid.uuid4();row.digest=uuid.uuid4().hex*2
            for field,value in changes.items():setattr(row,field,value)
            with self.assertRaises(DatabaseError),transaction.atomic(),scoped_view._owner(row.pk):row.save(force_insert=True)

    def test_actual_same_run_full_completion_and_report_build_retain_reference(self):
        from tempfile import TemporaryDirectory
        from django.db import connection
        from django.utils import timezone as clock
        from mta.presentation import ancillary_live as live,daily_requests,operational_reports as full
        from mta.runtime.models import RunPhaseAcceptance,DailyReportGeneration
        from mta.serialization import digest
        self.full_factor=True;self.positive(duplicates=True)
        daily_requests.initialize([],provenance={'fixture':'scope-view-full-not-native'})
        self.request_snapshot=daily_requests.snapshot()
        provenance={'fixture':'scope-view-full-remarks-not-native'}
        live.initialize_owner(live.BPR,provenance_digest=digest(provenance),provenance_receipt=provenance)
        value=self.row('captured',datetime(2037,4,9,tzinfo=timezone.utc))
        live.append(live.BPR,[{k:v for k,v in value.items() if k!='RemarkDate'}],actor_id='component',timestamp=value['RemarkDate'])
        self.snapshot=live.snapshot_all(business_date='2037-04-10',bpr_remark_horizon=13)
        self.owner(claim=False,pick_root=self.enterContext(TemporaryDirectory()));self.prepare_dbm()
        self.receipt=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        view=self.prepare();before=view.expedite.parent.rows('match')
        finished=self.finish();self.assertEqual(finished.status,'SUCCEEDED')
        terminal=DailyReportGeneration.objects.create(run=finished,source_digest=finished.production_digest,recipe_digest=full.recipe_identity())
        with connection.cursor() as c:c.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(finished.pk)])
        terminal.metadata=full._build(finished);terminal.digest=digest(terminal.metadata);terminal.status='READY';terminal.sealed_at=clock.now()
        terminal.save(update_fields=['metadata','digest','status','sealed_at']);full.verify_rows(finished,full.generation(finished).metadata)
        rebound=self.binding(view)
        self.assertEqual(rebound.read_identity,view.read_identity)
        self.assertEqual(rebound.expedite.parent.rows('match'),before)

    def test_native_entry_explicit_preparation_returns_reference_and_retries_without_business_replay(self):
        from mta.runtime import production_scope
        from mta.runtime.scope_execution import _setting,_close_attempt
        self.native_command_key='owned-pick-counter';self.start()
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        report=production_scope.advance(self.run,self.scope_request,worker_reference='view-component-native-entry',prepare_reads=True)
        self.assertFalse(report['scope_ready']);self.assertFalse(report['serving_selected'])
        self.assertNotIn('phase_read_binding',report['pending'])
        self.assertIn('configured_artifact_readiness',report['pending'])
        from mta.presentation.scoped_view import bind
        bound=bind(report['phase_read_reference']['id'],expected_digest=report['phase_read_reference']['digest'])
        self.assertEqual(bound.run_id,self.run.pk)
        before=list(self.run.phase_acceptances.values_list('id','digest'))
        with patch('mta.temporal.chain.prepare_day',side_effect=AssertionError('PRE replay')), \
                patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('BPR replay')):
            repeated=production_scope.advance(self.run,self.scope_request,worker_reference='same-view-component-retry',prepare_reads=True)
        self.assertEqual(report,repeated)
        self.assertEqual(list(self.run.phase_acceptances.values_list('id','digest')),before)
        self.assertEqual(self.run.scope_attempts.count(),1)
