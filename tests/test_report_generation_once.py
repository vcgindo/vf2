"""Report builders create row identities once and reuse immutable receipts."""
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from datetime import date
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.test import override_settings
from mta.presentation import daily_native_prepared as native
from mta.presentation import daily_publication as publication
from mta.presentation import operational_reports as reports
from mta.serialization import digest


class ReportGenerationOnceTests(unittest.TestCase):
    def patch(self, stack, target, **kwargs):
        return stack.enter_context(patch(target, **kwargs))

    def test_derived_build_writes_exact_computed_bags_without_readback(self):
        run = SimpleNamespace(business_date=date(2026, 10, 21),
            pick_projection=SimpleNamespace(calculation_digest='pick'),
            production_manifest={'report_sources': {'routes': 'route-receipt'}})
        derived = {'Derived': [{'SKUCode': 'SKU', 'Amount': None},
                               {'SKUCode': 'SKU', 'Amount': 7}]}
        exported = {'Table': [{'Value': None}, {'Value': 3}, {'Value': 3}]}
        output = {'ClosingState': [{'consumer_context': {}, 'importer': {},
            'dbm': {}, 'btr': {'old': []}}],
            'BPRReports': [{'vf_RationedReqReport': []}],
            'Reports': [{'stage': 'export', 'deferred': 'recipe', 'sources': {}}]}
        images, exports = {}, {}

        def save_image(_run, path, image, rows):
            images[path] = deepcopy(rows)
            return {'image': image, 'count': len(rows), 'digest': digest(rows)}

        def save_export(_run, path, rows):
            exports[path] = deepcopy(rows)
            return {'image': path, 'count': len(rows), 'digest': digest(rows)}

        with ExitStack() as stack:
            self.patch(stack, 'mta.presentation.operational_reports.read_daily', return_value=output)
            self.patch(stack, 'mta.runtime.input_reader.read_input', return_value={
                'profile': {'delivery': {'btr_settings': {}}}})
            self.patch(stack, 'mta.runtime.report_sources.read_routes', return_value=[])
            self.patch(stack, 'mta.domain.btr_finalization.reporting_btr', return_value=derived)
            self.patch(stack, 'mta.domain.btr_finalization.DERIVED_TABLES', new={'Derived'})
            self.patch(stack, 'mta.domain.deferred_dbm_exports.render', return_value=exported)
            self.patch(stack, 'mta.presentation.pick_storage.read_pick_bands', return_value=[])
            for target in ('excess_storage.write_excess', 'fulfillment_storage.write_fulfillment',
                           'expedite_storage.write_expedite', 'pick_post_storage.write_pick_post'):
                self.patch(stack, 'mta.presentation.' + target)
            self.patch(stack, 'mta.presentation.operational_reports.consumer_metadata', return_value={'consumer': []})
            self.patch(stack, 'mta.presentation.operational_reports.save_image', side_effect=save_image)
            self.patch(stack, 'mta.presentation.operational_reports.save_export', side_effect=save_export)
            forbidden = [self.patch(stack, target, side_effect=AssertionError('full reread'))
                for target in ('mta.presentation.operational_reports.load_image',
                    'mta.presentation.operational_reports.load_export',
                    'mta.presentation.operational_reports.verify_rows',
                    'mta.application.native_output_contracts.validate_rows')]
            metadata = reports._build(run)
        self.assertEqual(images, {'closing/btr/Derived': derived['Derived']})
        self.assertEqual(exports, {'reports/export/Table': exported['Table']})
        self.assertEqual(metadata['images']['closing/btr/Derived']['digest'], digest(derived['Derived']))
        self.assertEqual(metadata['exports']['export']['Table']['digest'], digest(exported['Table']))
        for validator in forbidden:
            validator.assert_not_called()

    @override_settings(VF_MTA_PUBLISHED_RUN='')
    def test_ready_derived_generation_is_reused_without_build_or_row_scan(self):
        run = SimpleNamespace(pk=uuid.uuid4(), production_manifest={'version': 3},
            production_digest='production', output_digest='output')
        row = SimpleNamespace(status='READY', source_digest='production', recipe_digest='recipe')
        with ExitStack() as stack:
            self.patch(stack, 'mta.presentation.operational_reports.transaction.get_autocommit', return_value=True)
            self.patch(stack, 'mta.presentation.operational_reports.CalculationRun.objects.get', return_value=run)
            self.patch(stack, 'mta.presentation.operational_reports.DailyReportGeneration.objects.get_or_create', return_value=(row, False))
            self.patch(stack, 'mta.presentation.operational_reports.recipe_identity', return_value='recipe')
            self.patch(stack, 'mta.presentation.operational_reports.generation', return_value=row)
            self.patch(stack, 'mta.runtime.receipt_integrity.verify_root')
            cursor = MagicMock()
            cursor.__enter__.return_value.fetchone.return_value = (True,)
            self.patch(stack, 'mta.presentation.operational_reports.connection.cursor', return_value=cursor)
            build = self.patch(stack, 'mta.presentation.operational_reports._build')
            verify = self.patch(stack, 'mta.presentation.operational_reports.verify_rows')
            for _ in range(2):
                self.assertIs(reports.prepare(run.pk, expected_output_digest='output'), row)
        build.assert_not_called()
        verify.assert_not_called()

    def test_explicit_derived_diagnostic_keeps_full_image_export_and_consumer_checks(self):
        run = object()
        image, export = {'image': 'image', 'count': 2}, {'image': 'export', 'count': 1}
        metadata = {'images': {'path': image}, 'exports': {'report': {'table': export}},
                    'consumers': {'consumer': []}}
        with patch.object(reports, 'iter_image', return_value=iter([{}, {}])) as images, \
                patch.object(reports, 'iter_export', return_value=iter([{}])) as exports, \
                patch.object(reports, 'consumer_metadata', return_value={'consumer': []}) as consumers:
            reports.verify_rows(run, metadata)
            images.assert_called_once_with(run, image)
            exports.assert_called_once_with(run, export)
            consumers.return_value = {'changed': []}
            with self.assertRaisesRegex(ValueError, 'consumer receipt drift'):
                reports.verify_rows(run, metadata)

    def native_context(self, stack, receipt):
        self.patch(stack, 'mta.presentation.daily_native_prepared.connection.vendor', new='postgresql')
        self.patch(stack, 'mta.presentation.daily_native_prepared.transaction.atomic', side_effect=nullcontext)
        self.patch(stack, 'mta.presentation.daily_native_prepared._binding', return_value='source')
        self.patch(stack, 'mta.presentation.daily_native_prepared._lock')
        self.patch(stack, 'mta.presentation.daily_native_prepared.production_recipe_digest', return_value='recipe')
        self.patch(stack, 'mta.presentation.daily_preparation.assert_unchanged')
        row_model, receipt_model = MagicMock(), MagicMock()
        row_model.objects.filter.return_value.exists.return_value = False
        receipt_model.objects.filter.return_value.first.side_effect = [None, receipt]
        receipt_model.objects.create.return_value = receipt
        return row_model, receipt_model

    def test_native_build_creates_identity_once_and_repeat_writes_zero_rows(self):
        receipt = SimpleNamespace(source_digest='source', schema_digest='schema',
            row_count=3, rows_digest='typed-row-digest')
        with ExitStack() as stack:
            row_model, receipt_model = self.native_context(stack, receipt)
            cursor = MagicMock()
            cursor.__enter__.return_value.rowcount = 3
            self.patch(stack, 'mta.presentation.daily_native_prepared.connection.cursor', return_value=cursor)
            stream = self.patch(stack, 'mta.presentation.daily_native_prepared._stream_receipt',
                return_value=(3, 'typed-row-digest'))
            query = MagicMock(return_value=('INSERT exact rows', ['run']))
            args = dict(layer='bpr', row_model=row_model, receipt_model=receipt_model,
                fields=('ordinal',), insert_query=query, schema='schema', guard=MagicMock(), verify_only=False)
            first = native._single_prepare(SimpleNamespace(pk='run'), **args)
            second = native._single_prepare(SimpleNamespace(pk='run'), **args)
        self.assertTrue(first.pop('created'))
        self.assertFalse(second.pop('created'))
        self.assertEqual(first, second)
        query.assert_called_once()
        cursor.__enter__.return_value.execute.assert_called_once_with('INSERT exact rows', ['run'])
        stream.assert_called_once()
        receipt_model.objects.create.assert_called_once_with(run=unittest.mock.ANY,
            source_digest='source', schema_digest='schema', rows_digest='typed-row-digest', row_count=3)

    def test_explicit_native_diagnostic_still_rejects_row_digest_drift(self):
        receipt = SimpleNamespace(source_digest='source', schema_digest='schema', row_count=3, rows_digest='original')
        with ExitStack() as stack:
            row_model, receipt_model = self.native_context(stack, receipt)
            receipt_model.objects.filter.return_value.first.side_effect = None
            receipt_model.objects.filter.return_value.first.return_value = receipt
            self.patch(stack, 'mta.presentation.daily_native_prepared._stream_receipt', return_value=(3, 'changed'))
            with self.assertRaisesRegex(Exception, 'complete_row_receipt_changed'):
                native._single_prepare(SimpleNamespace(pk='run'), layer='bpr', row_model=row_model,
                    receipt_model=receipt_model, fields=('ordinal',), insert_query=MagicMock(),
                    schema='schema', guard=MagicMock(), verify_only=True)

    def test_history_creates_one_identity_per_family_and_reuses_without_scans(self):
        run = SimpleNamespace(pk='run')
        receipts = {}

        def create(**values):
            receipt = SimpleNamespace(**values)
            receipts[receipt.family] = receipt
            return receipt

        with ExitStack() as stack:
            self.native_context(stack, None)
            identity = self.patch(stack, 'mta.presentation.native_excess_history.identity', return_value={'lineage': []})
            self.patch(stack, 'mta.presentation.native_excess_history.source_digest', return_value='history-source')
            self.patch(stack, 'mta.runtime.guided_history_schema.verify_guards')
            self.patch(stack, 'mta.presentation.daily_native_prepared.history_schema_digest', return_value='history-schema')
            self.patch(stack, 'mta.presentation.daily_native_prepared.native_excess_schema_digest', return_value='excess-schema')
            for model in ('GuidedAvailabilityHistoryRow', 'GuidedAvailabilitySnapshotReference', 'GuidedExcessHistoryRow'):
                self.patch(stack, 'mta.presentation.daily_native_prepared.' + model + '.objects.filter').return_value.exists.return_value = False
            self.patch(stack, 'mta.presentation.daily_native_prepared.GuidedHistoryPreparedProjection.objects.filter',
                side_effect=lambda **_kwargs: list(receipts.values()))
            receipt_create = self.patch(stack, 'mta.presentation.daily_native_prepared.GuidedHistoryPreparedProjection.objects.create', side_effect=create)
            self.patch(stack, 'mta.presentation.daily_native_prepared.connection.cursor', return_value=MagicMock())
            availability = self.patch(stack, 'mta.presentation.daily_native_prepared._history_availability')
            excess = self.patch(stack, 'mta.presentation.daily_native_prepared._history_excess')
            scan = self.patch(stack, 'mta.presentation.daily_native_prepared._history_receipt',
                side_effect=[(3, 2, 'availability-rows'), (4, 0, 'excess-rows')])
            first = native._prepare_guided_history(run, verify_only=False)
            second = native._prepare_guided_history(run, verify_only=False)
            self.assertTrue(first.pop('created'))
            self.assertFalse(second.pop('created'))
            self.assertEqual(first, second)
            self.assertEqual(first['families'], {
                'availability': {'row_count': 3, 'reference_count': 2, 'rows_digest': 'availability-rows'},
                'excess': {'row_count': 4, 'reference_count': 0, 'rows_digest': 'excess-rows'}})
            self.assertEqual(scan.call_count, 2)
            self.assertEqual(receipt_create.call_count, 2)
            availability.assert_called_once()
            excess.assert_called_once()
            # Explicit diagnostics retain their complete row scan and drift check.
            scan.side_effect = [(3, 2, 'changed-availability')]
            with self.assertRaisesRegex(Exception, 'existing_receipt_changed:availability'):
                native._prepare_guided_history(run, verify_only=True)
            self.assertEqual(identity.call_args_list, [
                unittest.mock.call(run, verify_rows=False),
                unittest.mock.call(run, verify_rows=False),
                unittest.mock.call(run, verify_rows=True)])

    @override_settings(VF_MTA_PUBLISHED_RUN='')
    def test_ui_prepare_builds_once_reuses_layer_and_ready_without_row_verification(self):
        run = SimpleNamespace(pk=uuid.uuid4(), kind='DAILY_CHAIN', status='SUCCEEDED', output_digest='output')
        row = MagicMock(status='INCOMPLETE', layers={}, output_digest='output',
            source_digest='source', configuration_digest='configuration', recipe_digest='recipe')
        attempt = MagicMock()
        with ExitStack() as stack:
            self.patch(stack, 'mta.presentation.daily_publication.transaction.get_autocommit', return_value=True)
            self.patch(stack, 'mta.presentation.daily_publication.transaction.atomic', side_effect=nullcontext)
            self.patch(stack, 'mta.presentation.daily_publication.CalculationRun.objects.get', return_value=run)
            self.patch(stack, 'mta.presentation.daily_publication.DailyUiPublication.objects.get_or_create', return_value=(row, False))
            create = self.patch(stack, 'mta.presentation.daily_publication.DailyUiPublicationAttempt.objects.create', return_value=attempt)
            for function, value in (('source_identity', 'source'), ('configuration_identity', 'configuration'),
                                    ('recipe_identity', 'recipe'), ('seal_identity', 'seal')):
                self.patch(stack, 'mta.presentation.daily_publication.' + function, return_value=value)
            self.patch(stack, 'mta.presentation.daily_preparation.required_layers', return_value=('bpr',))
            build = self.patch(stack, 'mta.presentation.daily_preparation.prepare_layer', return_value={'rows_digest': 'rows', 'row_count': 3})
            verify = self.patch(stack, 'mta.presentation.daily_preparation.verify_layer', side_effect=AssertionError('full reread'))
            ready = self.patch(stack, 'mta.presentation.daily_publication.require_ready')
            cursor = MagicMock()
            cursor.__enter__.return_value.fetchone.return_value = (True,)
            self.patch(stack, 'django.db.connection.cursor', return_value=cursor)
            publication.prepare(run.pk, expected_output_digest='output')
            self.assertEqual(row.layers, {'bpr': {'status': 'READY', 'receipt': {'rows_digest': 'rows', 'row_count': 3}}})
            self.assertEqual(row.status, 'READY')
            # An interrupted publication reuses its already sealed layer.
            row.status = 'INCOMPLETE'
            publication.prepare(run.pk, expected_output_digest='output')
            publication.prepare(run.pk, expected_output_digest='output')
            build.assert_called_once_with(run, 'bpr')
            self.assertEqual(create.call_count, 2)
            # A real builder failure still leaves an incomplete publication and
            # a FAILED diagnostic; no operational run state is written here.
            row.status, row.layers = 'INCOMPLETE', {}
            build.side_effect = ValueError('report build failed')
            publication.prepare(run.pk, expected_output_digest='output')
            self.assertEqual(row.status, 'INCOMPLETE')
            self.assertEqual(attempt.status, 'FAILED')
            self.assertEqual(row.layers['bpr']['status'], 'FAILED')
            self.assertEqual(row.layers['bpr']['error'], 'report build failed')
            self.assertEqual(run.status, 'SUCCEEDED')
        verify.assert_not_called()
        ready.assert_called_once_with(run)
        self.assertEqual(create.call_count, 3)
