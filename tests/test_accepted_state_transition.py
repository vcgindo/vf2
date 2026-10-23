"""Exact ownership transition and maintenance-boundary contract checks."""
import hashlib
from pathlib import Path
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch
from contextlib import contextmanager, ExitStack

from tests import test_report_guard_transition as guard_tests
from mta.runtime import accepted_state_transition as ownership
from mta.presentation import report_verification as verification
from mta.serialization import digest


class AcceptedStateTransitionTests(TestCase):
    def test_exact_canonical_migration_bytes_and_declared_delta(self):
        for name, expected in ownership.PINS:
            module=import_module('mta.runtime.migrations.' + name)
            # Git/native export uses LF; Windows checkout line endings do not
            # change the Python/SQL source or its canonical release identity.
            raw=Path(module.__file__).read_text(encoding='utf-8').encode('utf-8')
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
        frozen=import_module('mta.runtime.migrations.' + ownership.PINS[0][0])
        delta=ownership.catalogue_delta()
        self.assertEqual(len(delta), len(frozen.TRIGGERS) + 2*len(frozen.FUNCTIONS) + 2)
        self.assertTrue(all(row['before'] is None for row in delta.values()))

    def fixture(self):
        f, report, extension=guard_tests.ReportGuardTransitionTests().fixture()
        extension.update(schema_digest=ownership.BEFORE_SCHEMA, guard_digest=ownership.BEFORE_GUARD)
        code=f.code('c', report, 5)
        code_link=f.links.pop(code['target_release']); f.bodies.pop(code['target_release'])
        code['target_release']=ownership.PREVIOUS_RELEASE
        code_link.update(schema_digest=ownership.BEFORE_SCHEMA, guard_digest=ownership.BEFORE_GUARD)
        f.links[code['target_release']]=code_link; f.bodies[code['target_release']]=code
        target=f.schema('d', code, 6)
        current=f.links[target['target_release']]
        current.update(before_schema_digest=ownership.BEFORE_SCHEMA, before_guard_digest=ownership.BEFORE_GUARD,
            migration_pins=ownership.migration_pins(), catalogue_delta_digest=digest(ownership.catalogue_delta()))
        return f,target,current

    def test_exact_ownership_extension_and_later_code_anchor_preserve_ancestry(self):
        f,target,extension=self.fixture()
        self.assertTrue(ownership.approved_receipt(extension))
        self.assertEqual(f.resolve(target)[1:4], (target,'s6','g6'))
        later=f.code('e',target,6)
        self.assertEqual(f.resolve(later)[1:4], (target,'s6','g6'))
        unreviewed=f.schema('f',later,7)
        with self.assertRaisesRegex(ValueError, 'four-admission boundary'):
            f.resolve(unreviewed)

    def test_partial_pins_or_changed_ownership_delta_fail_closed(self):
        f,target,extension=self.fixture()
        original=deepcopy(extension)
        for key,value in (('migration_pins',ownership.migration_pins()[:1]),
                          ('catalogue_delta_digest','0'*64), ('before_schema_digest','0'*64),
                          ('before_guard_digest','0'*64), ('previous_release','0'*64)):
            extension.update(original); extension[key]=value
            self.assertFalse(ownership.approved_receipt(extension))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,'Exact accepted-state'):
                f.resolve(target)

    def test_specification_accepts_only_the_frozen_whole_delta(self):
        spec=dict(migration_pins=ownership.migration_pins(), catalogue_delta=ownership.catalogue_delta(),
                  previous_release={'manifest_sha256':ownership.PREVIOUS_RELEASE})
        ownership.require_specification(spec)
        changed=deepcopy(spec)
        changed['catalogue_delta'].pop('column:mta.fresh_mta_runcommand.state_sealed')
        with self.assertRaisesRegex(ValueError,'exact accepted-state'):
            ownership.require_specification(changed)


class MaintenanceVerificationBoundaryTests(TestCase):
    def test_public_scope_does_not_accept_an_existing_writer_transaction(self):
        run=SimpleNamespace(kind='DAILY_CHAIN')
        with patch.object(verification,'connection',SimpleNamespace(in_atomic_block=True)), \
             patch('mta.presentation.native_publication.enabled',return_value=True):
            with self.assertRaisesRegex(ValueError,'precede layer transactions'), verification.verification_scope(run):
                self.fail('ordinary transaction bypass')

    def test_private_scope_requires_outer_transaction_and_exact_current_release(self):
        with patch.object(verification,'connection',SimpleNamespace(in_atomic_block=False)):
            with self.assertRaisesRegex(ValueError,'exclusive outer transaction'), \
                 verification._schema_transition_scope(None,None,{},None):
                self.fail('maintenance transaction absent')
        with patch.object(verification,'connection',SimpleNamespace(in_atomic_block=True)), \
             patch('release.native_identity.require_current',return_value={'actual':'release'}):
            with self.assertRaisesRegex(ValueError,'target release differs'), \
                 verification._schema_transition_scope(None,None,{'other':'release'},None):
                self.fail('arbitrary release accepted')

    def test_public_catalogue_stamp_keeps_read_committed_requirement(self):
        cursor=MagicMock()
        cursor.fetchone.return_value=('db','oid','session','role','repeatable read','origin',
                                     'mta,public','on','UTC','ISO, YMD','UTF8')
        cursor.fetchall.return_value=[]
        connection=MagicMock()
        connection.cursor.return_value.__enter__.return_value=cursor
        with patch.object(verification,'connection',connection):
            with self.assertRaisesRegex(ValueError,'READ COMMITTED'):
                verification.guard_stamp()
            self.assertEqual(len(verification._guard_stamp('repeatable read')),64)


class PublicationQualificationTests(TestCase):
    """Dispatch/failure coverage; does not certify stubbed business populations."""

    def fixture(self, stack):
        from release import advance_ingestion
        stack.enter_context(patch('mta.presentation.native_publication.require_mode'))
        owner=SimpleNamespace(pk='owner',source_id='source')
        publications=[SimpleNamespace(run=SimpleNamespace(pk=str(i),output_digest='out'+str(i)),
            layers={'btr':{'receipt':{'generation':'generation'+str(i)}}},
            seal_digest='seal'+str(i)) for i in range(2)]
        runs=stack.enter_context(patch('mta.runtime.models.CalculationRun.objects.filter'))
        runs.return_value.values.return_value=['owned-run-query']
        query=stack.enter_context(patch('mta.runtime.models.DailyUiPublication.objects.select_related'))
        query.return_value.filter.return_value.order_by.return_value=publications
        generations=stack.enter_context(patch('mta.runtime.models.BtrReportingGeneration.objects.get'))
        source=stack.enter_context(patch('mta.presentation.btr_reporting.source_identity',return_value={'source':1}))
        generations.side_effect=[SimpleNamespace(version=3,source_digest=digest(source.return_value)) for _ in publications]
        verify=stack.enter_context(patch('mta.presentation.admission.verify'))
        btr=stack.enter_context(patch('mta.presentation.btr_reporting.verify_generation'))
        entered=[]
        @contextmanager
        def scope(run, actual_owner, target, check):
            self.assertIs(actual_owner,owner)
            self.assertEqual(target,{'target':1})
            entered.append(('enter',run.pk))
            try:
                yield
            finally:
                entered.append(('exit',run.pk))
        stack.enter_context(patch.object(verification,'_schema_transition_scope',side_effect=scope))
        return advance_ingestion,owner,publications,query,generations,verify,btr,entered

    def test_every_owned_ready_publication_receives_complete_and_btr_audit(self):
        with ExitStack() as stack:
            module,owner,pubs,query,generations,verify,btr,entered=self.fixture(stack)
            result=module._qualify_owned_publications(owner,{'target':1},lambda:None)
            query.return_value.filter.assert_called_once_with(status='READY',run_id__in=['owned-run-query'])
            self.assertEqual([call.args[0] for call in verify.call_args_list],[p.run for p in pubs])
            self.assertEqual(btr.call_count,2)
            self.assertEqual([r['run_id'] for r in result],['0','1'])
            self.assertEqual(entered,[('enter','0'),('exit','0'),('enter','1'),('exit','1')])
            for call,pub in zip(generations.call_args_list,pubs):
                self.assertEqual(call.kwargs,dict(pk=pub.layers['btr']['receipt']['generation'],
                                                 run=pub.run,status='READY'))

    def test_failed_audit_or_btr_source_never_returns_qualification(self):
        for failure in ('business','btr-source','btr-rows'):
            with self.subTest(failure=failure), ExitStack() as stack:
                module,owner,pubs,query,generations,verify,btr,entered=self.fixture(stack)
                if failure=='business':
                    verify.side_effect=ValueError('business audit failed')
                elif failure=='btr-source':
                    generations.side_effect=None
                    generations.return_value=SimpleNamespace(version=3,source_digest='changed')
                else:
                    btr.side_effect=ValueError('BTR row audit failed')
                with self.assertRaises(ValueError):
                    module._qualify_owned_publications(owner,{'target':1},lambda:None)
                self.assertEqual(entered,[('enter','0'),('exit','0')])
                self.assertEqual(verify.call_count,1)
                if failure!='btr-rows':
                    btr.assert_not_called()

    def test_missing_native_mode_fails_before_publication_query(self):
        from release.advance_ingestion import _qualify_owned_publications
        with patch('mta.presentation.native_publication.require_mode',
                   side_effect=ValueError('native mode required')), \
             patch('mta.runtime.models.CalculationRun.objects.filter') as query:
            with self.assertRaisesRegex(ValueError,'native mode required'):
                _qualify_owned_publications(None,{},lambda:None)
            query.assert_not_called()


class VerifiedOwnerLifetimeTests(TestCase):
    def fixture(self, stack):
        from mta.runtime import ingestion_models, mdm_daily_models
        owner=SimpleNamespace(pk='owner',source_id='source',refresh_from_db=Mock(),
                              source=SimpleNamespace(refresh_from_db=Mock()))
        admitted=SimpleNamespace(certification_digest='certificate',master_revision_id='revision',
                                 revisions=SimpleNamespace(as_tuple=lambda:(2,3,4,5,6)))
        handle=stack.enter_context(patch('mta.mdm.production_families.certified_state_handle'))
        seal=stack.enter_context(patch('mta.runtime.opening_scope.sealed_identity',return_value=('seal',)))
        certificate=stack.enter_context(patch.object(ingestion_models.InitializationCertification.objects,'values_list'))
        certificate.return_value.get.return_value=('cert-id','CERTIFIED')
        certificate.return_value.filter.return_value.first.return_value=('cert-id','CERTIFIED')
        revision=stack.enter_context(patch.object(ingestion_models.MasterInputRevision.objects,'values_list'))
        revision.return_value.get.return_value=('revision-id','ACCEPTED')
        revision.return_value.filter.return_value.first.return_value=('revision-id','ACCEPTED')
        state=stack.enter_context(patch.object(ingestion_models.IngestionRevisionState.objects,'values_list'))
        state.return_value.get.return_value=(2,3)
        capture=stack.enter_context(patch.object(mdm_daily_models.MdmDailyInputCapture.objects,'get',
                                                return_value=SimpleNamespace(source_id='source')))
        check=Mock();stamp=Mock(return_value='stamp')
        return owner,admitted,handle,seal,certificate,revision,state,capture,check,stamp

    def test_operation_scope_rejects_each_changed_authority_and_clears_audits(self):
        for changed in ('seal','stamp','certificate','revision','epochs','capture','session','audit'):
            with self.subTest(changed=changed), ExitStack() as stack:
                owner,admitted,handle,seal,cert,rev,state,capture,check,stamp=self.fixture(stack)
                with self.assertRaises(ValueError), verification._verified_owner(
                        object(),owner,admitted,check,'stamp',stamp):
                    verification._current.get()['audits']['completed']=True
                    if changed=='seal':seal.return_value=('new-seal',)
                    elif changed=='stamp':stamp.return_value='new-stamp'
                    elif changed=='certificate':cert.return_value.filter.return_value.first.return_value=None
                    elif changed=='revision':rev.return_value.filter.return_value.first.return_value=None
                    elif changed=='epochs':state.return_value.get.return_value=(3,3)
                    elif changed=='capture':capture.return_value.source_id='foreign-source'
                    elif changed=='session':check.side_effect=ValueError('lost session')
                    else:raise ValueError('audit failed')
                self.assertIsNone(verification._current.get())
                handle.assert_called_once_with(owner,admitted)

    def test_success_does_not_leak_audit_markers_to_the_next_operation(self):
        with ExitStack() as stack:
            owner,admitted,handle,seal,cert,rev,state,capture,check,stamp=self.fixture(stack)
            for _ in range(2):
                with verification._verified_owner(object(),owner,admitted,check,'stamp',stamp):
                    self.assertEqual(verification._current.get()['audits'],{})
                    verification._current.get()['audits']['completed']=True
                self.assertIsNone(verification._current.get())
