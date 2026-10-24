"""Frozen request ownership on actual accepted BPR; all cases roll back."""
from copy import copy
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_pick_files_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedRequestTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr'):
        locals()[_name]=getattr(fixtures.ScopedPickFileTests,_name)

    def owner(self,**options):
        from tests import test_h3_daily_integration as supplied
        from tests.production_h3_fixture import SEASON,CHILD
        opening=supplied.frame()
        if getattr(self,'action_case',False):
            for state,name in ((opening['opening']['state']['dbm'],'Suggestions'),
                    (opening['opening']['state']['controls'],'suggestions')):
                state[name]=[dict(SKUCode=SEASON,WhCode=CHILD,Type=1,NewNorm=24)]
        with patch.object(supplied,'frame',return_value=opening):
            fixtures.ScopedPickFileTests.owner(self,request_inputs=self.request_snapshot,**options)

    def parents(self,rows=None,*,counter=False):
        from mta.presentation import daily_requests,scoped_sources
        self.request_snapshot=None
        if rows is not None:
            daily_requests.initialize(rows,provenance=getattr(self,'request_provenance',
                dict(fixture='declared-scoped-request-component-input-not-native')))
            self.request_snapshot=daily_requests.snapshot()
        self.bpr(counter=counter)
        self.sources=scoped_sources.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)

    def binding(self,sources=None):
        from mta.presentation.scoped_requests import bind
        return bind(self.sources if sources is None else sources)

    def row(self,**values):
        from tests.production_h3_fixture import CHILD,PARENT
        from mta.presentation.daily_requests import FIELDS
        row=dict.fromkeys(FIELDS)
        row.update(SKUCode='SUPPLIED-Z9',WhCode=CHILD,ParentWhCode=PARENT)
        row.update(values)
        return row

    def test_complete_capture_fields_order_duplicates_nulls_full_equivalence_and_no_hydration_in_bind(self):
        from mta.presentation import scoped_requests as module,daily_requests
        from mta.runtime.scope_revisions import require_current
        rows=[self.row(Request='Need / more',UserId='Operator Ω',RequestDate='2037-04-09T08:00:00'),
            self.row(Request=None),self.row(Request='Need / more',UserId='Operator Ω',RequestDate='2037-04-09T08:00:00')]
        self.parents(rows,counter=True);before=require_current(self.run)
        with patch.object(module.RequestBinding,'_records',side_effect=AssertionError('capture hydration during bind')):
            bound=self.binding()
        self.assertEqual(bound.rows(),rows);bound.verify_rows()
        self.assertEqual(bound.rows(),daily_requests.rows(self.run))
        self.assertEqual(bound.provenance()['revision'],self.request_snapshot['revision'])
        self.assertEqual(bound.provenance()['input_physical_owner_id'],str(self.run.pk))
        from django.db import connection
        query,params=bound.query()
        with connection.cursor() as c:
            c.execute(query+' ORDER BY ordinal',params);fields=[col[0] for col in c.description]
            records=[dict(zip(fields,r)) for r in c.fetchall()]
        self.assertEqual([r.pop('vf_ordinal') for r in records],list(range(len(rows))))
        for row in records:
            for field in module.DATES:
                if row[field] is not None:
                    self.assertIsNone(row[field].tzinfo);row[field]=row[field].isoformat()
        self.assertEqual(records,rows);self.assertEqual(require_current(self.run),before)

    def test_missing_request_source_is_unavailable_and_explicit_empty_is_owned(self):
        from mta.presentation.context import PublicationUnavailable
        self.parents()
        with self.assertRaises(PublicationUnavailable):self.binding()
        # The second owned run explicitly captures the zero-row source. No old
        # run or retained empty export is reinterpreted as that source owner.
        self.parents([]);bound=self.binding()
        self.assertEqual(bound.rows(),[]);bound.verify_rows()
        self.assertEqual(bound.provenance()['row_count'],0)

    def test_later_current_request_revision_does_not_change_frozen_rows_or_identity(self):
        from django.db import connection
        from mta.presentation import daily_requests
        from mta.runtime.models import DailyOpenRequest,DailyRequestOwner
        rows=[self.row(Request='captured',RequestDate='2037-04-09T08:00:00')]
        self.parents(rows);bound=self.binding();before=bound.provenance()
        with connection.cursor() as c:c.execute("SELECT set_config('fresh.daily_request_owner',%s,true)",[daily_requests.OWNER])
        DailyOpenRequest.objects.update(Request='later workflow value')
        DailyRequestOwner.objects.filter(pk=daily_requests.OWNER).update(revision=1)
        self.assertNotEqual(daily_requests.snapshot()['rows'],rows)
        self.assertEqual(self.binding().provenance(),before)
        self.assertEqual(bound.rows(),rows);self.assertEqual(self.binding().rows(),rows)

    def test_running_surplus_insert_cannot_extend_frozen_prefix_but_full_verification_denies(self):
        from django.db import transaction,DatabaseError
        from mta.presentation import daily_requests
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import DailyCapturedRequest,DailyRequestCapture
        row=self.row(Request='original');self.parents([row]);bound=self.binding();before=bound.provenance()
        DailyCapturedRequest.objects.create(capture_id=self.run.pk,ordinal=1,**daily_requests._typed(self.row(Request='surplus')))
        self.assertEqual(bound.rows(),[row]);self.assertEqual(self.binding().rows(),[row])
        self.assertEqual(self.binding().provenance(),before)
        with self.assertRaises(PublicationUnavailable):bound.verify_rows()
        with self.assertRaises(ValueError):daily_requests.rows(self.run)
        for model,changes in ((DailyCapturedRequest,dict(Request='changed')),(DailyRequestCapture,dict(row_count=2))):
            with self.assertRaises(DatabaseError),transaction.atomic():model.objects.update(**changes)

    def test_native_wall_datetimes_are_independent_of_session_timezone(self):
        from django.db import connection
        row=self.row(RequestDate='2037-04-09T08:00:00',ActionDate='2037-04-09T09:00:00',ETA='2037-04-12T10:00:00')
        self.parents([row]);before=self.binding().provenance()
        for zone in ('Pacific/Auckland','Asia/Kolkata'):
            with connection.cursor() as c:c.execute('SET LOCAL TIME ZONE %s',[zone])
            bound=self.binding();self.assertEqual(bound.provenance(),before)
            self.assertEqual(bound.rows(),[row]);bound.verify_rows()

    def test_original_latest_parent_scope_null_date_future_and_tie_semantics(self):
        from tests.production_h3_fixture import CHILD,PARENT
        from mta.presentation.expedite_child_sources import projections
        rows=[self.row(Request='undated'),self.row(Request='old',RequestDate='2037-01-01T00:00:00'),
            self.row(Request='future-closed',RequestDate='2038-01-01T00:00:00',Action='Closed'),
            self.row(Request='other-parent',ParentWhCode='OTHER',RequestDate='2039-01-01T00:00:00')]
        self.parents(rows);lookup=projections(self.binding().rows(),[])
        self.assertEqual(lookup('supplied-z9 ',CHILD.lower(),PARENT.lower())['remark'],'future-closed')
        self.assertEqual(lookup('SUPPLIED-Z9',CHILD,'OTHER')['remark'],'other-parent')
        self.assertIsNone(lookup(None,CHILD,PARENT)['remark'])
        tied=[self.row(Request='one'),self.row(Request='two')]
        # Isolate source-shape projection semantics; no captured state is edited.
        with self.assertRaisesRegex(ValueError,'ambiguous_latest_request'):projections(tied,[])

    def test_capture_identity_guard_and_datetime_type_drift_deny(self):
        import uuid
        from django.db import connection,transaction
        from mta.presentation import scoped_requests as module
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import DailyRequestCapture
        self.parents([])
        with self.assertRaises(PublicationUnavailable):module.bind(None)
        wrong=copy(self.run);wrong.pk=uuid.uuid4()
        with self.assertRaises(PublicationUnavailable):module.bind(replace(self.sources,run=wrong))
        capture=DailyRequestCapture.objects.get(run=self.run)
        for field,value in (('revision',capture.revision+1),('row_count',1),('provenance_digest','f'*64),('rows_digest','f'*64)):
            bad=copy(capture);setattr(bad,field,value)
            with patch.object(module.models.DailyRequestCapture.objects,'get',return_value=bad),self.assertRaises(PublicationUnavailable):self.binding()
        with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
        for sql in ('ALTER TABLE mta.fresh_mta_dailycapturedrequest DISABLE TRIGGER daily_capture_immutable',
                'ALTER FUNCTION mta.guard_daily_request_capture() SECURITY DEFINER',
                'ALTER TABLE mta.fresh_mta_dailycapturedrequest ALTER COLUMN "RequestDate" TYPE timestamp without time zone'):
            with transaction.atomic():
                with connection.cursor() as c:c.execute(sql)
                with self.assertRaises(PublicationUnavailable):self.binding()
                transaction.set_rollback(True)
        self.assertEqual(self.binding().rows(),[])

    def test_actual_sleep_advances_fresh_source_identity_and_retains_inflight_requests(self):
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.runtime.scoped_actions import record
        from mta.presentation import scoped_sources
        from mta.presentation.context import PublicationUnavailable
        from tests.production_h3_fixture import SEASON,CHILD
        self.action_case=True;rows=[self.row(Request='captured')];self.parents(rows)
        bound=self.binding();before=bound.provenance()
        with _setting('fresh.scope_worker',self.attempt.worker_token):_close_attempt(self.attempt,self.run,'RELEASED',{})
        event=record(self.run.pk,phase_id=self.receipt.pk,phase_digest=self.receipt.digest,expected_revision=0,
            operation='SLEEP',selected=[[SEASON,CHILD]],timestamp='2037-04-10T10:00:00',actor='owned-request-component',idempotency_key='request-sleep')
        with self.assertRaises(PublicationUnavailable):
            scoped_sources.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        sources=scoped_sources.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=event.pk)
        fresh=self.binding(sources)
        self.assertEqual(fresh.provenance()['action_revision'],event.pk)
        self.assertNotEqual(fresh.provenance(),before)
        self.assertEqual(bound.provenance(),before);self.assertEqual(bound.rows(),rows);self.assertEqual(fresh.rows(),rows)

    def test_foreign_production_initialization_and_captured_mdm_source_are_denied(self):
        from mta.presentation import scoped_requests as module
        from mta.presentation.context import PublicationUnavailable
        self.request_provenance=dict(schema='fresh-production-consumer-opening-v1',
            initialization_id='ffffffff-ffff-ffff-ffff-ffffffffffff',source_digest='f'*64)
        self.parents([])
        with self.assertRaises(PublicationUnavailable):self.binding()
        # Isolate the source predicate after a matching initialization resolver;
        # the MDM source remains the actual accepted component run's source.
        with patch.object(module.input_v3,'_run_initialization_id',return_value=self.request_provenance['initialization_id']), \
                self.assertRaises(PublicationUnavailable):self.binding()

    def test_actual_captured_latest_tie_disagreement_is_not_repaired(self):
        from mta.presentation.expedite_child_sources import projections
        rows=[self.row(Request='one'),self.row(Request='two')]
        self.parents(rows);bound=self.binding()
        self.assertEqual(bound.rows(),rows);bound.verify_rows()
        with self.assertRaisesRegex(ValueError,'child_expedite_ambiguous_latest_request'):
            projections(bound.rows(),[])
