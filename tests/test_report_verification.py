"""Negative identity/lifetime checks; PostgreSQL proof qualifies persisted rows."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from contextlib import ExitStack
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import uuid4

from mta.presentation import report_verification as verification
from mta.runtime.input_v3 import V3
from mta.serialization import digest


class ProfileReferenceTests(TestCase):
    def fixture(self):
        from mta.runtime.input_storage import SCHEMA
        owner = NS(pk=uuid4(), input_digest='a'*64,
            input_payload={'schema': SCHEMA, 'content_digest': 'a'*64,
                           'tree': {'object': [['profile', {'scalar': 'profile'}]]}})
        owner.input_manifest_digest = digest(owner.input_payload)
        reference = dict(kind='INITIALIZATION', path='input/profile', owner_id=str(owner.pk),
            content_digest=owner.input_digest, manifest_digest=owner.input_manifest_digest)
        manifest = dict(schema=V3, content_digest='b'*64,
            owner_references={'input/profile': reference},
            tree={'object': [['profile', {'owner_reference': 'input/profile'}]]})
        run = NS(input_payload=manifest, input_digest='b'*64,
                 input_manifest_digest=digest(manifest))
        return run, owner, reference

    def test_exact_one_hop_reference_uses_no_population_reader(self):
        run, owner, _ = self.fixture()
        with patch('mta.runtime.input_reader.read_input', side_effect=AssertionError('hydration')):
            self.assertTrue(verification.profile_reference(run, owner))

    def test_foreign_owner_and_stale_manifest_content_and_target_fail(self):
        for field in ('owner_id', 'manifest_digest', 'content_digest', 'path', 'kind'):
            run, owner, reference = self.fixture()
            reference[field] = str(uuid4()) if field == 'owner_id' else 'c'*64
            run.input_manifest_digest = digest(run.input_payload)
            with self.subTest(field=field), self.assertRaises(ValueError):
                verification.profile_reference(run, owner)
        run, owner, _ = self.fixture()
        owner.input_payload['changed'] = True
        with self.assertRaises(ValueError):
            verification.profile_reference(run, owner)
        run, owner, _ = self.fixture()
        run.input_payload['tree']['object'][0][1]['owner_reference'] = 'input/opening'
        run.input_manifest_digest = digest(run.input_payload)
        with self.assertRaises(ValueError):
            verification.profile_reference(run, owner)

    def test_physical_profile_keeps_legacy_full_comparison(self):
        run, owner, _ = self.fixture()
        run.input_payload['owner_references'] = {}
        self.assertFalse(verification.profile_reference(run, owner))


class AuditLifetimeTests(TestCase):
    def run_node(self):
        return NS(pk=uuid4(), status='SUCCEEDED', input_digest='input',
            input_manifest_digest='manifest', output_digest='output', production_digest='production',
            input_payload={}, production_manifest={}, refresh_from_db=Mock())

    def test_success_only_reuse_exact_run_generation_and_operation(self):
        run = self.run_node()
        audit, check = Mock(), Mock()
        token = verification._current.set(dict(check=check, audits={}))
        try:
            verification.immutable_audit(run, 'rows', audit)
            verification.immutable_audit(run, 'rows', audit)
            self.assertEqual(audit.call_count, 1)
            run.production_manifest['changed'] = True
            verification.immutable_audit(run, 'rows', audit)
            self.assertEqual(audit.call_count, 2)
            check.side_effect = ValueError('guard generation changed')
            with self.assertRaisesRegex(ValueError, 'guard generation'):
                verification.immutable_audit(run, 'rows', audit)
        finally:
            verification._current.reset(token)
        verification.immutable_audit(run, 'rows', audit)
        self.assertEqual(audit.call_count, 3)

    def test_failure_is_never_reused(self):
        run = self.run_node()
        audit = Mock(side_effect=ValueError('same-count digest drift'))
        token = verification._current.set(dict(check=Mock(), audits={}))
        try:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'digest drift'):
                    verification.immutable_audit(run, 'rows', audit)
            self.assertEqual(audit.call_count, 2)
        finally:
            verification._current.reset(token)


class VerificationBoundaryTests(TestCase):
    def test_complete_operational_audit_does_not_require_derived_readiness(self):
        profile = {'native': 'configured'}
        source = NS()
        run = NS(production_manifest={'version': 3})
        receipt = NS(images={'sources/production/BOR_OrderAllocationHistory': {'table': 'bpr_history/BOR_OrderAllocationHistory'},
                             'sources/ordinary': {'table': 'ordinary'}},
                     images_digest='source-images', recipe_digest='source-recipe')
        with ExitStack() as stack:
            capture = stack.enter_context(patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.select_related'))
            capture.return_value.get.return_value = NS(source=source)
            owner = stack.enter_context(patch('mta.runtime.initialization_models.ProductionInitialization.objects.get'))
            owner.return_value = NS(configuration_digest=digest(profile))
            opening = stack.enter_context(patch('mta.mdm.production_families.require_initialization'))
            stack.enter_context(patch('mta.runtime.input_reader.read_input', return_value={'profile': profile}))
            root = stack.enter_context(patch('mta.runtime.receipt_integrity.verify_root'))
            inputs = stack.enter_context(patch.object(verification, '_audit_input'))
            outputs = stack.enter_context(patch('mta.runtime.receipt_integrity.audit_output'))
            stack.enter_context(patch('mta.runtime.services.read_outputs', side_effect=AssertionError('discarded graph')))
            stack.enter_context(patch('mta.presentation.operational_reports.generation', side_effect=AssertionError('derived readiness')))
            private_rows = stack.enter_context(patch('mta.presentation.daily_sources.image_rows', return_value=[]))
            ordinary_rows = stack.enter_context(patch('mta.runtime.relational_state.iter_image', return_value=iter(())))
            verification.audit_native_rows(run, receipt)
        private_rows.assert_called_once_with(run, 'sources/production/BOR_OrderAllocationHistory')
        ordinary_rows.assert_called_once_with(run, {'table': 'ordinary'})
        opening.assert_called_once_with(source)
        root.assert_called_once_with(run)
        inputs.assert_called_once_with(run)
        outputs.assert_called_once_with(run)

    def test_graph_cannot_use_a_caller_flag_to_skip_guarded_verification(self):
        for include_reports in (False, True):
            with self.subTest(include_reports=include_reports), self.assertRaisesRegex(ValueError, 'guarded verification scope'):
                verification.consumer_outputs(NS(), include_reports=include_reports)

