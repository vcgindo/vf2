"""Intermediate owner-chain checks; no PostgreSQL or browser qualification."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import patch
from django import conf

from tests import test_runtime_report_registered_request as request_tests
from mta.serialization import digest


@unittest.skipUnless(conf.settings.configured, 'Offline Django settings required; no database used')
class RegisteredReportViewTests(unittest.TestCase):
    def setUp(self):
        global view
        from mta.presentation import registered_report_view as view
        self.release = patch('release.native_identity.require_current', return_value={'local-test':'release-a'})
        self.release.start(); self.addCleanup(self.release.stop)
        self.make_case('UptoBPR')

    def make_case(self, scope):
        self.request = request_tests.RegisteredRequestTests().request(scope)
        self.inner = self.request['scope_request']; self.outer = self.request['report_registration_request']
        self.run = Obj(pk='owned-run', input_digest='a'*64, input_manifest_digest='b'*64)
        self.pre = Obj(pk='pre', run_id=self.run.pk, phase='PRE_BPR', digest='c'*64, state_sealed=True)
        self.bpr = Obj(pk='bpr', run_id=self.run.pk, phase='BPR', digest='d'*64, state_sealed=True,
                       snapshot=Obj(parent=Obj(acceptance=self.pre)))
        self.dbm = Obj(pk='dbm', run_id=self.run.pk, run=self.run, phase='DBM', digest='e'*64,
            state_sealed=True, snapshot=Obj(parent=Obj(acceptance_id='bpr')),
            metadata={'effects':{'parent_acceptance_digest':self.bpr.digest}})
        self.rows = {}
        for placement, phase, parent in (('PostImporter',self.pre,None),('PostBPR',self.bpr,'PostImporter'),
                                         ('PostDBM',self.dbm,'PostBPR')):
            self.rows[placement] = Obj(pk=placement, digest=digest(placement), run_id=self.run.pk,
                phase_id=phase.pk, owner_kind='SCOPED_PHASE', catalogue_parent_id=parent,
                configuration_digest=self.inner['runtime_reports']['configuration_digest'],
                scope_request_digest=digest(self.inner), input_digest=self.run.input_digest,
                input_manifest_digest=self.run.input_manifest_digest,
                metadata={'authority':{'owner':{'phase_digest':phase.digest}}})

    @contextmanager
    def data(self):
        from mta.runtime.models import RunPhaseAcceptance
        with patch('mta.runtime.runtime_report_registered_request.read_captured', return_value=self.outer), \
                patch('mta.runtime.input_reader.read_input', return_value={'scope_request':self.inner}), \
                patch('mta.runtime.scope_runtime_reports.require_test_database'), \
                patch.object(RunPhaseAcceptance.objects, 'select_related') as phases, \
                patch('mta.runtime.runtime_report_placement_publication.read',
                    side_effect=lambda _run, *, placement, verify_bytes:self.rows[placement]):
            phases.return_value.get.return_value=self.bpr
            yield

    def test_configuration_attaches_actual_registration_and_two_placement_receipts(self):
        with self.data(): config, request_digest = view.configuration(self.run)
        self.assertEqual(set(config), view.FIELDS)
        self.assertEqual(request_digest, digest(self.inner))
        self.assertEqual(config['registration_request'], self.outer)
        self.assertEqual(config['reference'], self.inner['runtime_reports'])
        self.assertEqual(config['post_importer'], {'id':'PostImporter','digest':digest('PostImporter')})
        self.assertEqual(config['post_bpr'], {'id':'PostBPR','digest':digest('PostBPR')})

    def test_wrong_run_phase_parent_configuration_and_input_are_refused(self):
        from mta.presentation.context import PublicationUnavailable
        for attribute, changed in (('run_id','foreign'),('phase_id','foreign'),
                ('catalogue_parent_id','foreign'),('configuration_digest','f'*64),
                ('scope_request_digest','f'*64),('input_digest','f'*64),('input_manifest_digest','f'*64)):
            self.make_case('UptoBPR'); setattr(self.rows['PostBPR'],attribute,changed)
            with self.subTest(attribute=attribute), self.data(), self.assertRaises(PublicationUnavailable):
                view.configuration(self.run)
        self.make_case('UptoBPR'); self.pre.phase='BPR'
        with self.data(), self.assertRaises(PublicationUnavailable): view.configuration(self.run)

    def test_missing_attachment_cannot_make_an_old_request_registered(self):
        from mta.presentation.context import PublicationUnavailable
        with self.data(), patch('mta.runtime.runtime_report_registered_request.read_captured',return_value=None), \
                self.assertRaises(PublicationUnavailable):
            view.configuration(self.run)

    def test_dbm_keeps_its_own_phase_and_bpr_parent(self):
        self.make_case('UptoDBM')
        with self.data():
            config,_=view.configuration(self.run)
            binding=Obj(run_id=self.run.pk,reference=Obj(metadata={'runtime_reports':config}),
                bpr=Obj(sources=Obj(acceptance_id=self.bpr.pk,acceptance_digest=self.bpr.digest)))
            self.assertIs(view.require_dbm(binding,self.dbm),self.rows['PostDBM'])
            from mta.presentation.context import PublicationUnavailable
            self.dbm.snapshot.parent.acceptance_id='foreign'
            with self.assertRaises(PublicationUnavailable): view.require_dbm(binding,self.dbm)
            self.dbm.snapshot.parent.acceptance_id=self.bpr.pk
            self.rows['PostDBM'].catalogue_parent_id='foreign'
            with self.assertRaises(PublicationUnavailable): view.require_dbm(binding,self.dbm)
            self.rows['PostDBM'].catalogue_parent_id='PostBPR'
            binding.reference.metadata['runtime_reports']=deepcopy(config)
            binding.reference.metadata['runtime_reports']['post_bpr']['digest']='f'*64
            with self.assertRaises(PublicationUnavailable): view.require_dbm(binding,self.dbm)


if __name__ == '__main__': unittest.main()
