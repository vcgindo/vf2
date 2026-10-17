"""Source binding and atomic selection tests; full READY remains a separate gate."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from uuid import uuid4
from django.test import override_settings
from mta.presentation import native_publication as native, native_selection as selection, daily_publication as daily
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


class SelectionTests(unittest.TestCase):
    def test_invalid_types_and_duplicate_json_fields_fail_closed(self):
        import json
        value = self.bundle()
        for field in selection.FIELDS:
            with self.subTest(field=field), self.assertRaises(ValueError):
                selection.validate(value | {field: None})
        with TemporaryDirectory() as directory:
            path = Path(directory)/'selection.json'
            path.write_text(json.dumps(value)[:-1]+', "run_id": "duplicate"}')
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                selection.read(path)

    @override_settings(VF_MTA_SELECTION_FILE='', VF_MTA_SELECTION=None)
    def test_individual_environment_values_cannot_bypass_atomic_selection(self):
        with self.assertRaisesRegex(PublicationUnavailable, 'atomic_selection_required'):
            selection.require_selected(NS(pk=uuid4()))

    def test_loaded_selection_cannot_change_or_disappear(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'selection.json'
            first, second = self.bundle(), self.bundle()
            selection.write(path, first)
            with override_settings(VF_MTA_SELECTION_FILE=str(path), VF_MTA_SELECTION=first), \
                    patch.object(native, 'identity'), patch.object(daily, 'require_ready'), \
                    patch('mta.presentation.planning_summary_daily.require_ready'), \
                    patch.object(selection, 'candidate', return_value=first):
                selection.require_selected(NS())
                selection.write(path, second)
                with self.assertRaisesRegex(PublicationUnavailable, 'changed_restart_required'):
                    selection.require_selected(NS())
                path.unlink()
                with self.assertRaisesRegex(PublicationUnavailable, 'selection_unavailable'):
                    selection.require_selected(NS())

    def bundle(self):
        run = NS(pk=uuid4(), output_digest='a'*64, business_date=date(2037,4,10))
        publication = NS(seal_digest='b'*64, configuration_digest='c'*64,
            layers={'btr':{'receipt':{'generation':str(uuid4())}}})
        summary = NS(pk=uuid4(), rows_digest='d'*64)
        return selection.candidate(run, publication, summary, {'initialization':{'id':str(uuid4())}})

    def test_atomic_success_and_replace_failure_preserve_previous(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'selection.json'
            first, second = self.bundle(), self.bundle()
            selection.write(path, first)
            before = path.read_bytes()
            with patch.object(selection.os, 'replace', side_effect=OSError('interrupted')):
                with self.assertRaisesRegex(OSError, 'interrupted'):
                    selection.write(path, second)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])
            selection.write(path, second)
            self.assertEqual(selection.read(path), second)

    def test_partial_and_changed_bundle_never_replace(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'selection.json'
            value = self.bundle(); selection.write(path, value)
            before = path.read_bytes()
            for changed in ({'run_id':str(uuid4())}, {'summary_digest':''}):
                with self.assertRaises(ValueError):
                    selection.write(path, value | changed)
                self.assertEqual(path.read_bytes(), before)


class NativeBindingTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(override_settings(VF_MTA_SYNTHETIC_ROSTER=''))
        self.profile = {'configured':'native'}
        self.owner = NS(pk=uuid4(), source=NS(digest='source'), input_sha256='input',
            input_digest='content', configuration_digest=digest(self.profile), opening_date=date(2037,4,9))
        self.binding = dict(id=str(self.owner.pk),source_digest='source',input_sha256='input',
            content_digest='content',configuration_digest=self.owner.configuration_digest)
        self.run = NS(pk=uuid4(),kind='DAILY_CHAIN',status='SUCCEEDED',input_digest='input',
            output_digest='output',production_digest='production',predecessor_id=None,business_date=date(2037,4,10))
        self.capture = NS(status='CONSUMED',source=NS(receipt={'schema':'fresh-production-mdm-source-v1'}))
        self.input = dict(initialization_binding=self.binding,profile=self.profile,lineage={})
        patches = [patch('mta.runtime.input_reader.read_input',return_value=self.input),
            patch('mta.runtime.initialization_models.ProductionInitialization.objects.select_related'),
            patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.select_related'),
            patch('mta.presentation.daily_sources.receipt',return_value=NS(images_digest='images',recipe_digest='recipe'))]
        self.mocks = [self.enterContext(p) for p in patches]
        self.mocks[1].return_value.filter.return_value.first.return_value = self.owner
        self.mocks[2].return_value.filter.return_value.first.return_value = self.capture

    def test_native_binding_independent_of_parity(self):
        self.assertEqual(native.identity(self.run)['initialization'], self.binding)

    def test_full_readback_uses_daily_family_initialization_verifier(self):
        self.mocks[3].return_value.images = {}
        with patch('mta.mdm.production_families.require_initialization') as check, \
                patch('mta.runtime.services.read_outputs') as outputs:
            native.identity(self.run, verify_rows=True)
        check.assert_called_once_with(self.owner.source)
        outputs.assert_called_once_with(self.run)

    def test_wrong_initialization_and_nonconsecutive_date_deny(self):
        self.input['initialization_binding'] = self.binding | {'id':str(uuid4())}
        with self.assertRaisesRegex(PublicationUnavailable, 'binding_changed'):
            native.identity(self.run)
        self.input['initialization_binding'] = self.binding
        self.run.business_date=date(2037,4,11)
        with self.assertRaisesRegex(PublicationUnavailable, 'opening_date_changed'):
            native.identity(self.run)

    def test_successor_requires_own_parent_digest_and_initialization(self):
        parent=NS(pk=uuid4(),kind='DAILY_CHAIN',status='SUCCEEDED',business_date=date(2037,4,9),output_digest='parent')
        self.run.predecessor=parent;self.run.predecessor_id=parent.pk
        self.input['lineage']={'run_id':str(parent.pk),'output_digest':'wrong'}
        with self.assertRaisesRegex(PublicationUnavailable,'predecessor_changed'):
            native.identity(self.run)
        self.input['lineage']['output_digest']='parent'
        self.assertEqual(native.identity(self.run)['predecessor_id'],str(parent.pk))

    @override_settings(VF_MTA_DAILY_PUBLICATION=True)
    def test_completed_native_day_does_not_admit_partial_roster(self):
        with patch.object(daily,'require_ready',side_effect=PublicationUnavailable('daily_ui_publication_not_ready')):
            with self.assertRaisesRegex(PublicationUnavailable,'not_ready'):
                native.require_publication(self.run)

    @override_settings(VF_MTA_SYNTHETIC_ROSTER='core-without-bor-v1')
    def test_native_cannot_exclude_required_layers(self):
        with self.assertRaisesRegex(PublicationUnavailable,'full_report_roster_required'):
            native.identity(self.run)


class NativeAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(override_settings(VF_MTA_NATIVE_PUBLICATION=True, VF_MTA_DAILY_PUBLICATION=True,
            VF_MTA_FIXTURE_FILE='', VF_MTA_FIXTURE_SHA256='', VF_MTA_SYNTHETIC_ROSTER='',
            VF_MTA_OPERATIONAL_POLICY='', VF_MTA_OPERATIONAL_RECEIPT='', VF_MTA_CONSUMPTION_POLICY=''))

    def test_native_mode_cannot_mix_fixture_or_synthetic_admission(self):
        native.require_mode()
        for field in ('VF_MTA_FIXTURE_FILE', 'VF_MTA_FIXTURE_SHA256',
                      'VF_MTA_OPERATIONAL_POLICY', 'VF_MTA_OPERATIONAL_RECEIPT',
                      'VF_MTA_CONSUMPTION_POLICY', 'VF_MTA_SYNTHETIC_ROSTER'):
            with self.subTest(field=field), override_settings(**{field:'conflicting'}):
                with self.assertRaisesRegex(PublicationUnavailable, 'mode_conflict'):
                    native.require_mode()

    def test_selected_native_run_needs_full_publication_summary_and_atomic_bundle(self):
        from mta.presentation import context
        run = NS(pk=uuid4(), production_manifest={'native':True}, output_digest='a'*64,
                 parity_summary={}, business_date=date(2037,4,10))
        native_identity = {'initialization': {'id': str(uuid4())}}
        ready = NS(seal_digest='b'*64, configuration_digest='c'*64,
                   layers={'btr': {'receipt': {'generation': str(uuid4())}}})
        summary_receipt = NS(pk=uuid4(), rows_digest='d'*64)
        bundle = selection.candidate(run, ready, summary_receipt, native_identity)
        with TemporaryDirectory() as directory:
            path = Path(directory)/'selection.json'
            selection.write(path, bundle)
            with override_settings(VF_MTA_PUBLISHED_RUN=str(run.pk),
                    VF_MTA_PUBLISHED_DIGEST=run.output_digest,
                    VF_MTA_SELECTION_FILE=str(path), VF_MTA_SELECTION=bundle), \
                    patch.object(context.CalculationRun.objects, 'filter') as runs, \
                    patch.object(native, 'identity', return_value=native_identity) as identity, \
                    patch.object(daily, 'require_ready', return_value=ready) as publication, \
                    patch('mta.presentation.planning_summary_daily.require_ready',
                          return_value=summary_receipt) as summary, \
                    patch.object(selection, 'require_selected', wraps=selection.require_selected) as selected:
                runs.return_value.first.return_value = run
                self.assertIs(context.selected_run(), run)
                identity.assert_called_once_with(run)
                publication.assert_called_once_with(run)
                summary.assert_called_once_with(run)
                selected.assert_called_once_with(run)
                for gate in (identity, publication, summary, selected):
                    gate.side_effect = PublicationUnavailable('incomplete_or_mixed')
                    with self.assertRaisesRegex(PublicationUnavailable, 'incomplete_or_mixed'):
                        context.selected_run()
                    gate.side_effect = None
                path.unlink()
                with self.assertRaisesRegex(PublicationUnavailable, 'selection_unavailable'):
                    context.selected_run()

    @override_settings(VF_MTA_NATIVE_PUBLICATION=False)
    def test_native_mode_does_not_weaken_existing_parity_gate(self):
        from mta.presentation import context
        run = NS(pk=uuid4(), production_manifest={'native':True}, output_digest='a'*64,
                 parity_summary={})
        with override_settings(VF_MTA_PUBLISHED_RUN=str(run.pk), VF_MTA_PUBLISHED_DIGEST=run.output_digest), \
                patch.object(context.CalculationRun.objects, 'filter') as runs:
            runs.return_value.first.return_value = run
            with self.assertRaisesRegex(PublicationUnavailable, 'acceptance_required'):
                context.selected_run()

    def test_failed_native_selection_command_preserves_old_file(self):
        from mta.runtime.management.commands.check_daily_selection import Command
        import io
        run = NS(kind='DAILY_CHAIN', status='SUCCEEDED', output_digest='a'*64, parity_summary={})
        with TemporaryDirectory() as directory:
            path = Path(directory)/'selection.json'
            path.write_bytes(b'previous complete selection')
            output = io.StringIO()
            with patch('mta.runtime.management.commands.check_daily_selection.CalculationRun.objects.get', return_value=run), \
                    patch('mta.presentation.admission.verify', side_effect=PublicationUnavailable('native_rows_changed')):
                with self.assertRaisesRegex(PublicationUnavailable, 'native_rows_changed'):
                    Command(stdout=output).handle(run_id='candidate', output_digest=run.output_digest,
                                                 selection_file=str(path))
            self.assertEqual(path.read_bytes(), b'previous complete selection')
            self.assertEqual(output.getvalue(), '')


class SummaryRowsTests(unittest.TestCase):
    def test_checksum_detects_same_count_value_changes_and_non_dense_ordinals(self):
        from mta.presentation import planning_summary_daily as summary
        rows = [('git_child', 'sku', None, 'raw', 2), ('git_parent', 'sku', 'loc', 'raw', 1)]
        receipt = NS(row_count=2, rows_digest=digest(rows))
        with patch.object(summary.PlanningSummaryContribution.objects, 'filter') as query:
            iterator = query.return_value.order_by.return_value.values_list.return_value.iterator
            iterator.return_value = iter([(i,*row) for i,row in enumerate(rows)])
            summary.verify_contribution_rows(receipt)
            iterator.return_value = iter([(0,*rows[0][:-1],3),(1,*rows[1])])
            with self.assertRaisesRegex(PublicationUnavailable, 'rows_changed'):
                summary.verify_contribution_rows(receipt)
            iterator.return_value = iter([(0,*rows[0]),(3,*rows[1])])
            with self.assertRaisesRegex(PublicationUnavailable, 'ordinals_changed'):
                summary.verify_contribution_rows(receipt)


if __name__ == '__main__':
    unittest.main()
