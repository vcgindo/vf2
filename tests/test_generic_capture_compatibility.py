"""Original-factory source/contract identity; no arbitrary run/database pins."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from mta.runtime import generic_capture_compatibility as compatible
from mta.serialization import digest


class GenericCaptureCompatibilityTests(unittest.TestCase):
    def test_accepted_cut_fields_preserve_opaque_identity_without_inferring_factory(self):
        for scope in ('UptoBPR', 'UptoDBM'):
            value, expected = self.value(scope)
            value['compatibility_digest'] = '8'*64
            original = deepcopy(value)
            compatible.require_captured_fields(value, expected)
            self.assertEqual(value, original)
            for key in value.keys() - {'compatibility_digest'}:
                changed = deepcopy(value)
                changed[key] = 'different'
                with self.subTest(scope=scope, key=key), self.assertRaises(ValueError):
                    compatible.require_captured_fields(changed, expected)
            for identity in ('', 'not-a-digest', None):
                with self.subTest(identity=identity), self.assertRaises(ValueError):
                    compatible.require_captured_fields(dict(value, compatibility_digest=identity), expected)

    def value(self,scope):
        from mta.runtime.production_scope_policy import SCHEMA
        value=dict(schema='captured-schema',scope=scope,command_key='one-command',
            runtime_reports={'configuration_digest':'c'*64},report_hooks={'mode':'unchanged'},
            dispositions={'schema':SCHEMA},publication_recipe='p'*64)
        value['compatibility_digest']=digest(dict(request=dict(value),
            release=compatible.ORIGIN_RELEASE,phase_recipe='r'*64))
        expected=dict(value,compatibility_digest='new-release-digest')
        return value,expected

    def test_both_prefix_factories_retain_their_exact_original_digest(self):
        for scope in ('UptoBPR','UptoDBM'):
            value,expected=self.value(scope);before=deepcopy(value)
            compatible.require_factory(value,expected,'r'*64)
            self.assertEqual(value,before)
            for key in ('scope','command_key','runtime_reports','report_hooks','dispositions','publication_recipe'):
                changed=deepcopy(value);changed[key]='foreign'
                with self.subTest(scope=scope,key=key),self.assertRaises(ValueError):
                    compatible.require_factory(changed,expected,'r'*64)
            with self.assertRaises(ValueError):compatible.require_factory(value,expected,'changed-recipe')
            changed=dict(value,compatibility_digest='0'*64)
            with self.assertRaises(ValueError):compatible.require_factory(changed,expected,'r'*64)

    def test_full_and_unselected_client_policies_do_not_enter_this_profile(self):
        value,expected=self.value('Full')
        self.assertFalse(compatible.applicable(value))
        value['scope']='UptoBPR';value['dispositions']['schema']='legacy-client-policy'
        self.assertFalse(compatible.applicable(value))
        self.assertFalse(compatible.applicable(None))

    def test_exact_previous_factory_and_no_arbitrary_future_factory(self):
        value,expected=self.value('UptoBPR')
        body={key:item for key,item in value.items() if key!='compatibility_digest'}
        value['compatibility_digest']=digest(dict(request=body,release=compatible.PREVIOUS_RELEASE,phase_recipe='r'*64))
        self.assertEqual(compatible.require_factory(value,expected,'r'*64),compatible.PREVIOUS_RELEASE)
        unknown=dict(compatible.PREVIOUS_RELEASE,source_commit='0'*40)
        value['compatibility_digest']=digest(dict(request=body,release=unknown,phase_recipe='r'*64))
        with self.assertRaises(ValueError):compatible.require_factory(value,expected,'r'*64)

    def test_previous_reconstruction_preserves_all_other_native_bytes(self):
        original={'producer.py':'p'*64,'adapter.py':'old'}
        previous=dict(compatible.PREVIOUS_RELEASE,source_files_digest=digest(original))
        current={'producer.py':'p'*64,'adapter.py':'corrected'}
        with patch.object(compatible,'PREVIOUS_RELEASE',previous),patch.object(compatible,'PREVIOUS_OVERRIDES',{'adapter.py':'old'}):
            compatible.require_original_sources(current,factory_release=previous)
            for changed in ({**current,'producer.py':'wrong'},{**current,'extra.py':'x'}):
                with self.assertRaises(ValueError):compatible.require_original_sources(changed,factory_release=previous)
        with self.assertRaises(ValueError):compatible.require_original_sources(current,factory_release={'source_commit':'future'})

    def test_reconstruction_authenticates_every_unchanged_file_and_roster(self):
        original={'producer.py':'p'*64,'guard.py':'g'*64}
        release=dict(compatible.ORIGIN_RELEASE,source_files_digest=digest(original))
        current={'producer.py':'p'*64,'guard.py':'corrected-guard','new-guard.py':'n'*64}
        with patch.object(compatible,'ORIGIN_RELEASE',release), \
                patch.object(compatible,'ORIGIN_OVERRIDES',{'guard.py':'g'*64}), \
                patch.object(compatible,'ADDED_FILES',{'new-guard.py'}):
            compatible.require_original_sources(current)
            for mutation in ('producer','extra','missing','missing_guard'):
                changed=dict(current)
                if mutation=='producer':changed['producer.py']='different'
                elif mutation=='extra':changed['unreviewed.py']='a'*64
                elif mutation=='missing':changed.pop('producer.py')
                else:changed.pop('guard.py')
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                    compatible.require_original_sources(changed)

    def test_original_profile_has_no_run_id_or_database_name_roster(self):
        self.assertEqual(set(compatible.ORIGIN_RELEASE),{'schema','source_commit','manifest_sha256',
            'source_files_digest','migrations_digest','implementation_sha256'})
        self.assertTrue(all(name.startswith(('mta/','release/')) for name in compatible.ORIGIN_OVERRIDES))
        self.assertNotIn('mta/temporal/chain.py',compatible.ORIGIN_OVERRIDES)
        self.assertNotIn('mta/temporal/day_phases.py',compatible.ORIGIN_OVERRIDES)

    def test_only_the_exact_source_qualified_publication_recipe_transfers(self):
        with patch('mta.runtime.retained_registered_execution_compatibility._recipe_sources') as qualified:
            self.assertEqual(compatible.production_publication_recipe(compatible.OBSERVED_PRODUCTION_PUBLICATION_RECIPE),
                compatible.ORIGINAL_PRODUCTION_PUBLICATION_RECIPE)
            qualified.assert_called_once_with()
            with self.assertRaises(ValueError):compatible.production_publication_recipe('unknown-recipe')
        with patch('mta.runtime.retained_registered_execution_compatibility._recipe_sources',side_effect=ValueError('source changed')):
            with self.assertRaises(ValueError):compatible.production_publication_recipe(compatible.OBSERVED_PRODUCTION_PUBLICATION_RECIPE)
    def custody(self, phase_name='PRE_BPR', child_status=None):
        def mock(path, **kwargs):
            return self.enterContext(patch(path, **kwargs))

        value, expected = self.value('UptoDBM')
        owner = SimpleNamespace(pk='init', source_id=3, source=SimpleNamespace(digest='source'),
            input_sha256='opening', input_digest='opening-content', configuration_digest='configuration')
        binding = dict(id='init', source_digest='source', input_sha256='opening',
            content_digest='opening-content', configuration_digest='configuration')
        outer = dict(registration=dict(initialization_id='init', source_digest='source',
            certificate_digest='certificate'))
        input_payload = dict(content_digest='input')
        run = SimpleNamespace(pk='run', kind='DAILY_CHAIN', evidence_mode='production',
            status='RUNNING', output_digest='', input_digest='input',
            input_payload=input_payload, input_manifest_digest=digest(input_payload),
            mdm_input_capture=SimpleNamespace(source_id=3, status='CAPTURED'), scope_attempts=Mock())
        attempt = SimpleNamespace(pk='failed', run_id=run.pk, scope=value['scope'],
            command_key=value['command_key'], compatibility_digest=value['compatibility_digest'],
            input_digest=run.input_digest, input_manifest_digest=run.input_manifest_digest,
            action_revision=0, status='FAILED', attempt_no=1, created_at=1, recovery_of=None)
        phase = SimpleNamespace(pk='phase', phase=phase_name, digest='phase-digest',
            source_id=owner.source_id, input_digest=run.input_digest, attempt=attempt,
            snapshot=SimpleNamespace(run_id=run.pk, acceptance_id='phase',
                manifest={}, state_digest=digest({})))
        latest = attempt if child_status is None else SimpleNamespace(**{
            **vars(attempt), 'pk':'child', 'status':child_status, 'attempt_no':2, 'created_at':2,
            'recovery_of':attempt, 'expected_phase':phase.phase, 'expected_receipt_digest':phase.digest})
        run.scope_attempts.filter.return_value.order_by.return_value.first.return_value = latest
        run.scope_attempts.order_by.return_value.first.return_value = latest
        mock('django.db.transaction.atomic')
        mock('django.db.connection.cursor')
        mock('release.native_identity.require_current', return_value=dict(manifest_sha256='actual'))
        mock('mta.runtime.input_reader.read_input', return_value=dict(scope_request=value,
            initialization_binding=binding, report_registration_request=outer))
        mock('mta.runtime.runtime_report_registered_request.read_captured', return_value=outer)
        mock('mta.runtime.models.ProductionInitialization.objects').select_related.return_value.get.return_value = owner
        mock('mta.runtime.ingestion_admission.registration', return_value=(None,
            dict(release_identity=dict(manifest_sha256='original'))))
        mock('mta.runtime.ingestion_admission._admit',
            return_value=SimpleNamespace(certification_digest='certificate'))
        mock('mta.runtime.ingestion_upgrade._origin')
        sealed = mock('mta.runtime.models.RunPhaseAcceptance.objects')
        sealed.select_related.return_value.filter.return_value.first.return_value = phase if phase_name == 'DBM' else None
        self.read_phase = mock('mta.runtime.production_scope._phase', return_value=phase)
        self.head = mock('mta.runtime.scope_execution.head', return_value=(phase.phase, phase.digest))
        mock('mta.runtime.scope_execution.receipt_digest', return_value=phase.digest)
        mock('mta.runtime.phase_state.contract.compatible', return_value=True)
        publications = mock('mta.runtime.models.RuntimeReportPublication.objects')
        self.placements = publications.filter.return_value.values_list
        self.placements.return_value = []
        self.publication = mock('mta.runtime.runtime_report_placement_publication.read',
            return_value=SimpleNamespace(run_id=run.pk))
        self.pick = mock('mta.runtime.scoped_pick_files.read')
        return run, value, expected, phase, latest

    def test_failed_pre_bpr_qualifies_without_claiming_publication_or_pick_readiness(self):
        run, value, expected, phase, _latest = self.custody()
        self.assertEqual(compatible.validate(run, value, expected)['phase_digest'], phase.digest)
        self.read_phase.assert_called_once_with(run, 'PRE_BPR', phase.digest)
        self.publication.assert_not_called()
        self.pick.assert_not_called()
        self.head.return_value = ('START', 'start')
        with self.assertRaisesRegex(ValueError, 'sealed phase'):
            compatible.validate(run, value, expected)
        self.head.return_value = (phase.phase, phase.digest)
        run.mdm_input_capture.status = 'CONSUMED'
        with self.assertRaisesRegex(ValueError, 'unfinished prefix'):
            compatible.validate(run, value, expected)

    def test_active_recovery_authenticates_the_original_phase_and_committed_publication(self):
        run, value, expected, phase, latest = self.custody('BPR', 'ACTIVE')
        self.placements.return_value = ['PostImporter']
        self.assertEqual(compatible.validate(run, value, expected)['phase_id'], phase.pk)
        self.publication.assert_called_once_with(run.pk, placement='PostImporter', verify_bytes=True)
        self.pick.assert_not_called()
        for field, changed in (('expected_receipt_digest', 'foreign-phase'), ('input_digest', 'foreign-input'),
                ('recovery_of', None), ('attempt_no', 4)):
            original = getattr(latest, field)
            setattr(latest, field, changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                compatible.validate(run, value, expected)
            setattr(latest, field, original)
        self.placements.return_value = ['PostBPR']
        with self.assertRaisesRegex(ValueError, 'skip the accepted prefix'):
            compatible.validate(run, value, expected)
        self.placements.return_value = ['PostImporter', 'PostBPR', 'PostDBM']
        with self.assertRaisesRegex(ValueError, 'exceed'):
            compatible.validate(run, value, expected)

    def test_released_recovery_of_accepted_dbm_still_requires_publications_and_pick(self):
        run, value, expected, phase, _latest = self.custody('DBM', 'RELEASED')
        self.assertEqual(compatible.validate(run, value, expected)['phase_id'], phase.pk)
        self.placements.assert_not_called()
        self.assertEqual([call.kwargs['placement'] for call in self.publication.call_args_list],
            ['PostImporter', 'PostBPR'])
        self.pick.assert_called_once_with(phase.pk, expected_digest=phase.digest)
        self.publication.return_value = SimpleNamespace(run_id='foreign')
        with self.assertRaisesRegex(ValueError, 'original publication owner'):
            compatible.validate(run, value, expected)
