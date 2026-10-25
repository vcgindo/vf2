"""Actual existing BPR read dependencies under the new captured scope request."""
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_view_postgresql as fixtures
from tests.test_scope_runtime_reports import reference
from tests.test_production_upto_dbm import dispositions


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedUptoDbmViewTests(unittest.TestCase):
    for name in ('setUp','rollback','accept','bpr','parents','fetch','positive','start','scopes','reads',
                 'prepare_dbm','finish','publication_opening','prepare','binding','no_build'):
        locals()[name] = getattr(fixtures.ScopedViewTests,name)
    row = staticmethod(fixtures.ScopedViewTests.row)

    def bpr(self, **options):
        from mta.runtime import scope_execution
        claim = scope_execution._claim
        def dbm_scope(*args, **kwargs):
            return claim(*args,**dict(kwargs,scope='UptoDBM',command_key='dbm-read-components'))
        # Only the declared component scope differs; real SQL claims and all
        # calculation/acceptance functions remain in use.
        with patch.object(scope_execution,'_claim',side_effect=dbm_scope):
            return fixtures.ScopedViewTests.bpr(self,**options)

    def owner(self, **options):
        from mta.runtime.production_upto_dbm import SCHEMA
        self.scope_request = dict(schema=SCHEMA,scope='UptoDBM',command_key='dbm-read-components',
            compatibility_digest='a'*64,runtime_reports=reference(),dispositions=dispositions())
        options['scope_request'] = self.scope_request
        fixtures.Fixture.owner(self,**options)

    def test_bpr_dependencies_keep_exact_owner_and_frozen_request_under_new_scope(self):
        from mta.serialization import digest
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.models import ScopeReadReference
        self.start()
        before = require_current(self.run)
        phases = list(self.run.phase_acceptances.values_list('id','digest'))
        view = self.prepare()
        self.assertEqual(view.reference.metadata['scope_request_digest'],digest(self.scope_request))
        self.assertEqual(view.bpr.sources.acceptance_id,self.receipt.pk)
        self.assertEqual(view.bpr.sources.acceptance_digest,self.receipt.digest)
        with self.no_build(): self.assertEqual(self.binding(view).read_identity,view.read_identity)
        self.assertEqual(self.prepare().read_identity,view.read_identity)
        self.assertEqual(require_current(self.run),before)
        self.assertEqual(list(self.run.phase_acceptances.values_list('id','digest')),phases)
        self.assertEqual(ScopeReadReference.objects.count(),1)

    def test_dbm_composition_reuses_bpr_dependencies_and_denies_unreleased_or_wrong_phase(self):
        from mta.presentation import scoped_dbm_view
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.scoped_actions import calculate_dbm
        from mta.runtime.scope_execution import _setting,_close_attempt
        self.start()
        bpr_view = self.prepare()
        with self.assertRaises(PublicationUnavailable):
            scoped_dbm_view.compose(bpr_view,self.receipt.pk,expected_digest=self.receipt.digest)
        dbm = calculate_dbm(self.attempt.pk,self.attempt.worker_token,compatibility_digest='a'*64)
        with self.assertRaisesRegex(PublicationUnavailable,'released_scope'):
            scoped_dbm_view.compose(bpr_view,dbm.pk,expected_digest=dbm.digest)
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'RELEASED',{})
        with self.no_build():
            view = scoped_dbm_view.compose(bpr_view,dbm.pk,expected_digest=dbm.digest)
        self.assertEqual(view.reference.pk,bpr_view.reference.pk)
        self.assertEqual(view.bpr.sources.acceptance_id,self.receipt.pk)
        self.assertEqual(view.dbm_phase.pk,dbm.pk)
        self.assertEqual(view.dbm_context.phase_id,dbm.pk)
        self.assertEqual(view.read_identity['dbm_phase_digest'],dbm.digest)
        self.assertEqual(scoped_dbm_view.prepare(dbm.pk,expected_digest=dbm.digest,
            action_revision=0).read_identity,view.read_identity)
