"""Fast startup requires qualified protection and every dependent READY identity."""
from contextlib import ExitStack, nullcontext, contextmanager
from datetime import date
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import override_settings
from mta.presentation import accepted_publication as accepted, admission
from mta.presentation.context import PublicationUnavailable


class AcceptedPublicationTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(override_settings(VF_MTA_NATIVE_PUBLICATION=True,
            VF_MTA_DAILY_PUBLICATION=True, VF_BTR_REPORTING_GENERATION='selected'))
        self.run = SimpleNamespace(pk='run', kind='DAILY_CHAIN', status='SUCCEEDED',
                                   business_date=date(2026, 4, 8), output_digest='output')
        self.addCleanup(setattr, admission, '_admitted', admission._admitted)
        admission._admitted = None

    def dependencies(self, stack):
        names = ('mta.presentation.native_publication.require_mode',
                 'mta.presentation.report_verification.verification_scope',
                 'mta.presentation.accepted_publication._qualified_ownership',
                 'mta.presentation.daily_publication.require_ready',
                 'mta.presentation.accepted_publication._summary_ready',
                 'mta.presentation.accepted_publication._btr_ready',
                 'mta.presentation.accepted_publication._external_artifacts',
                 'mta.presentation.context.configured_run',
                 'mta.presentation.native_publication.identity',
                 'mta.presentation.native_selection.candidate',
                 'mta.presentation.native_selection.require_candidate')
        mocks = [stack.enter_context(patch(name)) for name in names]
        mocks[1].return_value = nullcontext()
        mocks[2].return_value = True
        mocks[7].return_value = self.run
        return mocks

    def test_metadata_path_skips_full_audits_only_after_all_checks(self):
        with ExitStack() as stack:
            checks = self.dependencies(stack)
            stack.enter_context(patch.object(admission, 'binding', return_value=(self.run, 'identity')))
            full = stack.enter_context(patch.object(admission, 'verify'))
            btr = stack.enter_context(patch('mta.presentation.btr_reporting.verify_generation'))
            self.assertEqual(admission.admit()['validation'], 'accepted_metadata')
            self.assertEqual(checks[3].call_count, 2)
            checks[3].assert_called_with(self.run, verify_rows=False)
            self.assertEqual(checks[4].call_count, 2)
            self.assertEqual(checks[5].call_count, 2)
            self.assertEqual(checks[10].call_count, 2)
            full.assert_not_called()
            btr.assert_not_called()

    def test_unqualified_ownership_uses_full_audit(self):
        with ExitStack() as stack:
            checks = self.dependencies(stack)
            checks[2].return_value = False
            stack.enter_context(patch.object(admission, 'binding', return_value=(self.run, 'identity')))
            full = stack.enter_context(patch.object(admission, 'verify'))
            stack.enter_context(patch('mta.presentation.btr_reporting.selected_generation', return_value='btr'))
            btr = stack.enter_context(patch('mta.presentation.btr_reporting.verify_generation'))
            self.assertEqual(admission.admit()['validation'], 'full_audit')
            full.assert_called_once_with(self.run)
            btr.assert_called_once_with('btr')
            checks[3].assert_not_called()

    def test_each_failed_check_revokes_admission_without_audit_fallback(self):
        for index in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
            with self.subTest(check=index), ExitStack() as stack:
                checks = self.dependencies(stack)
                checks[index].side_effect = ValueError('dependency invalid')
                stack.enter_context(patch.object(admission, 'binding', return_value=(self.run, 'identity')))
                full = stack.enter_context(patch.object(admission, 'verify'))
                admission._admitted = 'previous'
                with self.assertRaisesRegex(ValueError, 'dependency invalid'):
                    admission.admit()
                self.assertIsNone(admission._admitted)
                full.assert_not_called()

    def test_changed_identity_during_metadata_admission_is_rejected(self):
        with ExitStack() as stack:
            self.dependencies(stack)
            stack.enter_context(patch.object(admission, 'binding',
                side_effect=[(self.run, 'before'), (self.run, 'after')]))
            with self.assertRaisesRegex(PublicationUnavailable, 'changed_during'):
                admission.admit()
            self.assertIsNone(admission._admitted)

    def test_second_startup_pass_rechecks_metadata_and_failure_clears_scope(self):
        from mta.presentation.request_scope import once_per_metadata_operation, in_read_request
        calls = []
        @once_per_metadata_operation
        def identity():
            calls.append(1)
            return len(calls)
        observed = []
        def selection(run):
            self.assertFalse(in_read_request())
            observed.append(identity())
            self.assertEqual(identity(), observed[-1])
            if len(observed) == 2:
                raise PublicationUnavailable('second pass source changed')
        with ExitStack() as stack:
            self.dependencies(stack)
            stack.enter_context(patch.object(accepted, '_checked_selection', side_effect=selection))
            stack.enter_context(patch.object(admission, 'binding', return_value=(self.run, 'identity')))
            with self.assertRaisesRegex(PublicationUnavailable, 'second pass source changed'):
                admission.admit()
            self.assertIsNone(admission._admitted)
        self.assertEqual(observed, [1, 2])
        self.assertEqual(identity(), 3)
        self.assertEqual(identity(), 4)

    def test_lost_verification_session_cannot_publish_cached_passes(self):
        @contextmanager
        def disconnected():
            yield
            raise ValueError('verification backend changed')
        with ExitStack() as stack:
            checks = self.dependencies(stack)
            checks[1].return_value = disconnected()
            stack.enter_context(patch.object(admission, 'binding', return_value=(self.run, 'identity')))
            with self.assertRaisesRegex(ValueError, 'backend changed'):
                admission.admit()
            self.assertEqual(checks[10].call_count, 2)
            self.assertIsNone(admission._admitted)

    def test_next_startup_requalifies_instead_of_retaining_metadata(self):
        with ExitStack() as stack:
            checks = self.dependencies(stack)
            stack.enter_context(patch.object(admission, 'binding', return_value=(self.run, 'identity')))
            self.assertEqual(admission.admit()['validation'], 'accepted_metadata')
            checks[1].return_value = nullcontext()
            checks[2].side_effect = ValueError('guard changed next startup')
            with self.assertRaisesRegex(ValueError, 'guard changed next startup'):
                admission.admit()
            self.assertEqual(checks[2].call_count, 2)
            self.assertIsNone(admission._admitted)

    def test_configured_header_preserves_checks_and_http_still_validates_selection(self):
        from uuid import UUID
        from mta.presentation import context
        with override_settings(VF_MTA_PUBLISHED_RUN=str(UUID(int=1)),
                               VF_MTA_PUBLISHED_DIGEST='output'), \
                patch('mta.presentation.native_mode.require_configuration'), \
                patch('mta.presentation.native_publication.require_mode'), \
                patch('mta.presentation.daily_preparation.roster_identity'), \
                patch('mta.runtime.models.CalculationRun.objects.filter') as query, \
                patch('mta.presentation.native_selection.require_selected') as selected:
            self.run.production_manifest = {'version': 3}
            query.return_value.first.return_value = self.run
            self.assertIs(context.configured_run(), self.run)
            selected.assert_not_called()
            query.assert_called_with(pk=UUID(int=1), kind='DAILY_CHAIN', status='SUCCEEDED')
            self.assertIs(context.selected_run(), self.run)
            selected.assert_called_once_with(self.run)
            self.run.output_digest = 'changed'
            with self.assertRaisesRegex(PublicationUnavailable, 'identity_or_status'):
                context.configured_run()

    def test_checked_bundle_rejects_changed_file_or_settings_selection(self):
        from uuid import UUID
        from mta.presentation import native_selection
        from mta.serialization import digest
        bundle = {name: 'a' * 64 for name in native_selection.FIELDS}
        bundle.update(schema=native_selection.SCHEMA, business_date='2026-04-08',
                      **{name: str(UUID(int=1)) for name in ('run_id','initialization_id',
                                                          'btr_generation','summary_generation')})
        bundle['selection_digest'] = digest({k:v for k,v in bundle.items() if k!='selection_digest'})
        with override_settings(VF_MTA_SELECTION_FILE='selection', VF_MTA_SELECTION=bundle), \
                patch.object(native_selection, 'read', return_value=bundle) as read:
            native_selection.require_candidate(bundle)
            changed = dict(bundle, output_digest='b' * 64)
            changed['selection_digest'] = digest({k:v for k,v in changed.items() if k!='selection_digest'})
            read.return_value = changed
            with self.assertRaisesRegex(PublicationUnavailable, 'selection_changed'):
                native_selection.require_candidate(bundle)
            read.return_value = bundle
            with override_settings(VF_MTA_SELECTION=changed):
                with self.assertRaisesRegex(PublicationUnavailable, 'selection_changed'):
                    native_selection.require_candidate(bundle)

    def test_non_native_mode_does_not_query_ownership(self):
        with override_settings(VF_MTA_NATIVE_PUBLICATION=False), \
                patch.object(accepted, '_qualified_ownership') as qualified:
            self.assertIsNone(accepted.startup(Mock()))
            qualified.assert_not_called()

    def test_external_files_use_original_checksum_and_binding_validators(self):
        with override_settings(VF_MTA_TERMINAL_FILE='terminal', VF_MTA_TERMINAL_SHA256='sha'), \
                patch('mta.presentation.context.permission_catalogue') as catalogue, \
                patch('mta.presentation.hierarchy.selected_manifest') as hierarchy, \
                patch('mta.presentation.terminal_supplement.terminal_ancillary') as terminal:
            accepted._external_artifacts(self.run)
            catalogue.assert_called_once_with()
            hierarchy.assert_called_once_with(self.run)
            terminal.assert_called_once_with(self.run)
            catalogue.side_effect = PublicationUnavailable('catalogue checksum')
            with self.assertRaisesRegex(PublicationUnavailable, 'catalogue checksum'):
                accepted._external_artifacts(self.run)

    def test_summary_metadata_retains_complete_identity_and_guard_checks(self):
        from mta.runtime.planning_summary_models import METRICS
        identity = dict(source_digest='source', generation_digest='generation',
                        recipe_digest='recipe', business_date=self.run.business_date)
        receipt = SimpleNamespace(status='READY', metrics=list(METRICS), **identity)
        with patch('mta.presentation.planning_summary_daily.binding', return_value=(identity, None, {})), \
                patch('mta.runtime.planning_summary_models.PlanningSummaryReceipt.objects.filter') as query, \
                patch('mta.runtime.planning_summary_schema.verify_guards') as guards, \
                patch('mta.presentation.planning_summary_daily.verify') as population:
            query.return_value.first.return_value = receipt
            accepted._summary_ready(self.run)
            query.assert_called_once_with(run=self.run, **identity)
            guards.assert_called_once()
            population.assert_not_called()
            for field, wrong in [('status', 'BUILDING'), ('metrics', []),
                                 ('source_digest', 'other'), ('generation_digest', 'other'),
                                 ('recipe_digest', 'other'), ('business_date', date(2026, 4, 9))]:
                previous = getattr(receipt, field)
                setattr(receipt, field, wrong)
                with self.assertRaises(PublicationUnavailable):
                    accepted._summary_ready(self.run)
                setattr(receipt, field, previous)
            query.return_value.first.return_value = None
            with self.assertRaises(PublicationUnavailable):
                accepted._summary_ready(self.run)

    def test_btr_snapshot_always_validates_reference_without_reading_rows(self):
        generation = SimpleNamespace(version=2)
        with patch('mta.presentation.btr_reporting.selected_generation', return_value=generation), \
                patch('mta.presentation.btr_snapshot.reference_generation') as reference, \
                patch('mta.presentation.btr_reporting.verify_generation') as population:
            accepted._btr_ready(self.run)
            reference.assert_called_once_with(self.run, generation)
            population.assert_not_called()
            reference.side_effect = PublicationUnavailable('bad reference')
            with self.assertRaisesRegex(PublicationUnavailable, 'bad reference'):
                accepted._btr_ready(self.run)

    def test_ownership_requires_qualified_ancestry_or_original_guarded_certification(self):
        from mta.runtime.accepted_state_transition import PINS
        with ExitStack() as stack:
            cursor = Mock()
            context = stack.enter_context(patch.object(accepted.connection, 'cursor'))
            context.return_value.__enter__.return_value = cursor
            cursor.fetchall.return_value = [(name,) for name, _ in PINS]
            guards = stack.enter_context(patch('mta.runtime.accepted_state_ownership.verify_guards', return_value=True))
            stack.enter_context(patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.values_list'))
            stack.enter_context(patch('mta.runtime.initialization_models.ProductionInitialization.objects.values_list'))
            stack.enter_context(patch('mta.runtime.ingestion_admission._process_release',
                                      return_value={'manifest_sha256': 'current'}))
            stack.enter_context(patch('mta.runtime.ingestion_authority.read', return_value='authority'))
            cert = dict(release_digest='original', schema_digest='schema', guard_digest='guard')
            anchor = dict(target_release='original')
            effective = stack.enter_context(patch('mta.runtime.ingestion_admission.effective_schema',
                return_value=(cert, anchor, 'schema', 'guard', 'receipt')))
            extension = stack.enter_context(patch('mta.runtime.ingestion_authority.read_schema_transition',
                                                   return_value=None))
            approved = stack.enter_context(patch('mta.runtime.accepted_state_transition.approved_receipt',
                                                  return_value=False))
            self.assertTrue(accepted._qualified_ownership(self.run))
            extension.return_value = 'foreign extension'
            self.assertFalse(accepted._qualified_ownership(self.run))
            approved.return_value = True
            self.assertTrue(accepted._qualified_ownership(self.run))
            approved.assert_called_with('foreign extension')
            extension.return_value = None
            effective.return_value = (cert, anchor, 'changed schema', 'guard', 'receipt')
            self.assertFalse(accepted._qualified_ownership(self.run))
            cursor.fetchall.return_value = [(PINS[0][0],)]
            self.assertFalse(accepted._qualified_ownership(self.run))
            guards.return_value = False
            cursor.reset_mock()
            self.assertFalse(accepted._qualified_ownership(self.run))
            cursor.execute.assert_not_called()
            guards.side_effect = ValueError('tampered guard')
            with self.assertRaisesRegex(ValueError, 'tampered guard'):
                accepted._qualified_ownership(self.run)


if __name__ == '__main__':
    unittest.main()
