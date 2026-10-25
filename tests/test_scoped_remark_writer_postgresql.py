"""Rollback component proof of the actual scoped append/reference transaction."""
from contextlib import contextmanager, ExitStack, nullcontext
from copy import copy
from datetime import datetime, timezone
import json, os, unittest, uuid
from unittest.mock import patch
from tests import test_scoped_api_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class ScopedRemarkWriterTests(unittest.TestCase):
    for name in ('setUp','rollback','accept','bpr','parents','fetch','positive','start','scopes','reads',
            'prepare_dbm','finish','publication_opening','prepare','binding','no_build','owner','selected','http'):
        locals()[name] = getattr(fixtures.ScopedApiTests, name)
    row = staticmethod(fixtures.ScopedApiTests.row)

    def ready(self):
        from mta.runtime.scope_execution import _setting, _close_attempt
        self.selected()
        with _setting('fresh.scope_worker', self.attempt.worker_token):
            _close_attempt(self.attempt, self.run, 'RELEASED', {})
        from tests.production_h3_fixture import CHILD
        self.batch = dict(self.payload, data=[dict(SKUCode='SUPPLIED-Z9', WhCode=CHILD, Remark='writer batch')])
        self.actor = dict(id='component-writer', name='Fixture name')

    @contextmanager
    def clock(self):
        from mta.presentation import bpr_remarks
        class DeclaredClock(datetime):
            @classmethod
            def now(cls, tz=None): return cls(2037,4,10,12,30,45,tzinfo=tz)
        with patch.object(bpr_remarks, 'datetime', DeclaredClock): yield

    @contextmanager
    def runtime(self):
        # A rollback-only minimal registered-consumer fixture for the new SQL
        # boundary. Actual complete native registration is a separate proof.
        from django.db import connection
        from mta.runtime.scoped_remark_ownership import GRANTS, UUID_TABLES
        role = 'vftest_g2n_20261024_runtime'
        with connection.cursor() as c:
            c.execute("SELECT to_regclass('fresh_control.owned_namespace')"); self.assertEqual(c.fetchone(), (None,))
            c.execute('CREATE SCHEMA fresh_control')
            c.execute('CREATE TABLE fresh_control.owned_namespace(singleton boolean,consumer_oid oid)')
            c.execute('INSERT INTO fresh_control.owned_namespace VALUES(TRUE,(SELECT oid FROM pg_roles WHERE rolname=%s))',[role])
            c.execute('GRANT USAGE ON SCHEMA mta,mta_state,mta_opening,fresh_control TO '+role)
            c.execute('GRANT SELECT ON ALL TABLES IN SCHEMA mta,mta_state,mta_opening,fresh_control TO '+role)
            c.execute('GRANT INSERT ON mta.fresh_mta_bprliveremark TO '+role)
            c.execute('GRANT USAGE ON SEQUENCE mta.fresh_mta_bprliveremark_id_seq TO '+role)
            c.execute('GRANT UPDATE(next_ordinal) ON mta.fresh_mta_remarkowner TO '+role)
            c.execute('GRANT UPDATE(id) ON mta.fresh_mta_calculationrun TO '+role)
            c.execute('GRANT EXECUTE ON FUNCTION mta.scope_action_revision(uuid),mta.finite_capture_prefix_digest(uuid) TO '+role)
            for name, grant in GRANTS.items():
                for privilege in grant['table']:
                    columns='('+','.join(grant['columns'])+')' if privilege=='UPDATE' else ''
                    c.execute('GRANT '+privilege+columns+' ON '+name+' TO '+role)
                if name not in UUID_TABLES: c.execute('GRANT USAGE ON SEQUENCE '+name+'_id_seq TO '+role)
            c.execute('SET LOCAL ROLE '+role)
        try: yield
        finally:
            if not connection.needs_rollback:
                with connection.cursor() as c: c.execute('RESET ROLE')

    def audit_state(self):
        from mta.runtime.models import BprLiveRemark, RemarkOwner, ScopeReadReference, ScopeExpediteParentGeneration, ScopeExpediteParentBase, ScopeExpediteParentMatch
        return (RemarkOwner.objects.get(pk='BPRReport_RemarkDetails').next_ordinal,
            *[m.objects.count() for m in (BprLiveRemark, ScopeReadReference, ScopeExpediteParentGeneration,
                ScopeExpediteParentBase, ScopeExpediteParentMatch)])

    def test_runtime_batch_refreshes_only_parent_history_and_preserves_inflight(self):
        from mta.presentation import scoped_remark_writer as writer, scoped_selection, scoped_expedite_parent
        from mta.runtime.models import BprLiveRemark
        self.ready(); old=self.view; before=old.expedite.parent.rows('base')
        from mta.presentation import scoped_report_storage, scoped_prepared, scoped_planning, scoped_git, scoped_expedite_storage, scoped_pick_storage, scoped_transit_storage
        with ExitStack() as stack:
            for module in (scoped_report_storage, scoped_prepared, scoped_planning, scoped_git,
                    scoped_expedite_storage, scoped_pick_storage, scoped_transit_storage):
                stack.enter_context(patch.object(module,'prepare',side_effect=AssertionError('Independent rebuild')))
            with self.runtime(),self.clock():
                from django.test import RequestFactory
                from mta.presentation import views
                request=RequestFactory().post('/api/mta/AddRemark',data=json.dumps(self.batch),content_type='application/json',
                    HTTP_X_VECTORFLOW_IDENTITY=json.dumps(self.actor))
                response=views.bpr_remark(request)
                self.assertEqual(response.status_code,200,response.content)
                self.assertEqual(json.loads(response.content)['data'],'1')
                fresh=scoped_selection.selected()
                self.assertNotEqual(fresh.read_identity,old.read_identity)
                history=writer.history(fresh,dict(self.payload,skucode=self.batch['data'][0]['SKUCode'],whcode=self.batch['data'][0]['WhCode']))
                self.assertEqual(history[0],dict(r='writer batch',rd='2037-04-10T12:30:45',un='Fixture name'))
                query=dict(self.payload,skucode=self.batch['data'][0]['SKUCode'],whcode=self.batch['data'][0]['WhCode'])
                response=views.bpr_remark_history(RequestFactory().post('/api/mta/GetRemarkDetails',data=json.dumps(query),
                    content_type='application/json',HTTP_X_VECTORFLOW_IDENTITY=json.dumps(self.actor)))
                self.assertEqual(response.status_code,200,response.content)
                self.assertEqual(json.loads(response.content)['data'],history)
                self.assertTrue(any(r['remark']=='writer batch' for r in fresh.expedite.parent.rows('base')))
                self.assertEqual(old.expedite.parent.rows('base'),before)
                self.assertEqual(fresh.expedite.core.generation.pk,old.expedite.core.generation.pk)
                for field in ('report_generation_id','git_generation_id','pick_files_id'):
                    self.assertEqual(getattr(fresh.reference,field),getattr(old.reference,field))
                row=BprLiveRemark.objects.order_by('-ordinal').first()
                from django.db import connection
                with connection.cursor() as c:
                    c.execute('SELECT pg_current_xact_id()::text');self.assertEqual(row.append_transaction,c.fetchone()[0])
        from django.db import DatabaseError,transaction,connection
        from mta.runtime.scoped_remark_ownership import migration
        with self.assertRaisesRegex(DatabaseError,'Retained scoped remark ownership'),transaction.atomic():
            with connection.cursor() as c:c.execute(migration().REVERSE)

    def test_late_refresh_failure_rolls_back_append_all_caches_and_retry_succeeds(self):
        from mta.presentation import scoped_remark_writer as writer, scoped_expedite_parent, scoped_selection
        self.ready();before=self.audit_state()
        with self.runtime(),self.clock():
            with patch.object(scoped_expedite_parent,'_receipt',side_effect=OSError('late parent failure')):
                with self.assertRaisesRegex(OSError,'late parent'):writer.append(self.batch,self.actor)
            self.assertEqual(self.audit_state(),before)
            self.assertEqual(scoped_selection.selected().read_identity,self.view.read_identity)
            self.assertEqual(writer.append(self.batch,self.actor),'1')
            self.assertNotEqual(scoped_selection.selected().read_identity,self.view.read_identity)

    def test_permissions_and_invalid_batch_preserve_current_reference(self):
        from mta.presentation import scoped_remark_writer as writer
        self.ready();before=self.audit_state()
        with self.runtime(),self.clock():
            with self.assertRaises(writer.RemarkDenied):
                writer.append(dict(self.batch,product_permissions=[]),self.actor)
            self.assertEqual(self.audit_state(),before)
            self.assertEqual(writer.append(dict(self.batch,data=[dict(SKUCode='A',WhCode='B',Unknown='x')]),self.actor),'')
            self.assertEqual(self.audit_state(),before)

    def test_sql_no_append_marker_actor_and_stamp_ownership_denials(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_expedite_parent,ancillary_live
        from mta.runtime import scoped_remark_ownership as ownership
        from mta.runtime.models import BprLiveRemark
        self.ready()
        def candidate():
            row=copy(self.view.expedite.parent.generation);row.pk=uuid.uuid4()
            row.metadata={};row.digest='';row.sealed=False;row.sealed_at=None
            from mta.runtime.models import RemarkOwner
            row.remark_highwater=RemarkOwner.objects.get(pk=ancillary_live.BPR).next_ordinal
            return row
        def insert():
            row=candidate()
            with scoped_expedite_parent._owner(row.pk):row.save(force_insert=True)
        with self.runtime():
            for marker in (False,True):
                with self.subTest(marker=marker),self.assertRaises(DatabaseError),transaction.atomic():
                    if marker:
                        with ownership.publication(self.view.reference.pk,self.actor['id']):insert()
                    else:insert()
            # Client-provided transaction metadata cannot forge ownership.
            value=self.row('stamped',datetime(2037,4,10,tzinfo=timezone.utc))
            ancillary_live.append(ancillary_live.BPR,[dict({k:v for k,v in value.items() if k!='RemarkDate'},append_transaction='caller-forged')],
                actor_id=self.actor['id'],timestamp=value['RemarkDate'])
            row=BprLiveRemark.objects.order_by('-ordinal').first()
            self.assertNotEqual(row.append_transaction,'')
            self.assertNotEqual(row.append_transaction,'caller-forged')
            for reference,actor in ((uuid.uuid4(),self.actor['id']),(self.view.reference.pk,'foreign-actor')):
                with self.subTest(reference=reference,actor=actor),self.assertRaises(DatabaseError),transaction.atomic():
                    with ownership.publication(reference,actor):insert()
            # A real fresh batch and exact marker permit a complete refresh;
            # independent guard completeness still applies at transaction end.
            from mta.presentation import scoped_view
            with ownership.publication(self.view.reference.pk,self.actor['id']):
                fresh=scoped_view.refresh_parent(self.view.reference.pk,expected_digest=self.view.reference.digest)
            self.assertNotEqual(fresh.read_identity,self.view.read_identity)

    def test_guard_tampering_is_rejected_by_all_affected_readers(self):
        from django.db import connection,transaction
        from mta.presentation import scoped_remarks,scoped_view,scoped_expedite_parent
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.scoped_remark_ownership import verify_guards
        verify_guards()
        for sql in ('ALTER TABLE mta.fresh_mta_scopereadreference DISABLE TRIGGER scope_remark_writer_insert',
                'ALTER FUNCTION mta.stamp_scoped_remark_transaction() SECURITY DEFINER',
                'ALTER TABLE mta.fresh_mta_bprliveremark ALTER COLUMN append_transaction DROP NOT NULL'):
            with self.subTest(sql=sql),transaction.atomic():
                with connection.cursor() as c:c.execute(sql)
                for verify in (verify_guards,scoped_remarks.verify_guards,scoped_view.verify_guards,scoped_expedite_parent.verify_guards):
                    with self.assertRaises(PublicationUnavailable):verify()
                transaction.set_rollback(True)
        verify_guards()

    def test_matched_validation_reuse_preserves_complete_remark_results_and_reduces_work(self):
        from time import perf_counter,process_time
        from django.db import connection,transaction
        from mta.presentation import scoped_remark_writer as writer,scoped_selection,scoped_api
        from mta.runtime import ingestion_ownership
        self.ready();self.enterContext(self.runtime())
        initial=self.audit_state();rows=[];expected=None
        baseline_owners={field:getattr(self.view.reference,field) for field in
            ('report_generation_id','git_generation_id','pick_files_id')}
        for enabled in (False,True,True,False):
            queries=[]
            def measure(execute,sql,params,many,context):
                queries.append(sql.lstrip().split(None,1)[0])
                return execute(sql,params,many,context)
            with transaction.atomic():
                with ExitStack() as stack:
                    if not enabled:stack.enter_context(patch.object(writer,'remark_validation',nullcontext))
                    coverage=stack.enter_context(patch.object(ingestion_ownership,'_verify_guard_coverage',
                        wraps=ingestion_ownership._verify_guard_coverage))
                    stack.enter_context(self.clock());stack.enter_context(connection.execute_wrapper(measure))
                    started=perf_counter();cpu=process_time();result=writer.append(self.batch,self.actor)
                    seconds=perf_counter()-started;cpu_seconds=process_time()-cpu
                self.assertEqual(result,'1')
                fresh=scoped_selection.selected()
                semantic=dict(base=fresh.expedite.parent.rows('base'),match=fresh.expedite.parent.rows('match'),
                    remarks=fresh.bpr.remarks.rows(),bpr=scoped_api.bpr_rows(fresh,self.payload,paging=(1,1000)),
                    owners={field:getattr(fresh.reference,field) for field in baseline_owners},state=self.audit_state())
                self.assertEqual(semantic['owners'],baseline_owners)
                if expected is None:expected=semantic
                else:self.assertEqual(semantic,expected)
                row=dict(validation_reuse=enabled,seconds=round(seconds,3),cpu_seconds=round(cpu_seconds,3),
                    sql_calls=len(queries),full_guard_checks=coverage.call_count)
                rows.append(row);print(json.dumps(row),flush=True)
                transaction.set_rollback(True)
            self.assertEqual(self.audit_state(),initial)
            self.assertEqual(scoped_selection.selected().read_identity,self.view.read_identity)
        baseline=[r for r in rows if not r['validation_reuse']];bounded=[r for r in rows if r['validation_reuse']]
        self.assertLess(max(r['sql_calls'] for r in bounded),min(r['sql_calls'] for r in baseline)/2)
        self.assertLess(max(r['full_guard_checks'] for r in bounded),min(r['full_guard_checks'] for r in baseline)/2)
