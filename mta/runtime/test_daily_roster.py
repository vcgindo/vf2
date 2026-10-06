"""Focused identity and denial proofs for the finite synthetic daily roster."""
import json
from unittest.mock import patch

from django.test import Client, SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from mta.presentation import daily_preparation, daily_publication
from mta.presentation.context import PublicationUnavailable
from mta.presentation.daily_sources import recipe_digest as source_recipe
from mta.runtime.models import CalculationRun, DailySourceReceipt, DailyUiPublication
from mta.serialization import digest


SYNTHETIC = 'core-without-bor-v1'
IDENTITY = {'HTTP_X_VECTORFLOW_IDENTITY': '{"id":"synthetic-roster-test"}'}


class DailyRosterContractTests(SimpleTestCase):
    def test_default_is_the_unchanged_twenty_layer_roster(self):
        with override_settings(VF_MTA_SYNTHETIC_ROSTER=''):
            self.assertEqual(daily_preparation.required_layers(), daily_preparation.REQUIRED_LAYERS)
            self.assertEqual(len(daily_preparation.required_layers()), 20)

    def test_versioned_roster_has_only_the_two_authorized_exclusions(self):
        with override_settings(VF_MTA_SYNTHETIC_ROSTER=SYNTHETIC):
            layers = daily_preparation.required_layers()
            self.assertEqual(len(layers), 18)
            self.assertEqual(set(daily_preparation.REQUIRED_LAYERS) - set(layers), {'bor', 'boroa'})
            for name in ('bor', 'boroa'):
                with self.assertRaisesRegex(PublicationUnavailable,
                        'daily_layer_excluded_by_synthetic_roster:' + name):
                    daily_preparation.prepare_layer(object(), name)

    def test_unknown_roster_and_excluded_http_families_fail_explicitly(self):
        with override_settings(VF_MTA_SYNTHETIC_ROSTER='unknown-roster'):
            with self.assertRaisesRegex(PublicationUnavailable,
                                        'unsupported_daily_synthetic_roster'):
                daily_preparation.required_layers()
        client = Client()
        cases = (
            ('get', '/api/mta/BORUIConfig', None, 'bor'),
            ('get', '/api/mta/GetUIConfig?reportName=BuyerOrderReport', None, 'bor'),
            ('get', '/api/mta/GetUIConfig?reportName=BOR_OA', None, 'boroa'),
            ('post', '/api/mta/BORData', {}, 'bor'),
            ('post', '/api/mta/BORDataCount', {}, 'bor'),
            ('get', '/api/mta/BORAnalytics', None, 'bor'),
            ('post', '/api/mta/AddBORRemark', {}, 'bor'),
            ('post', '/api/mta/GetBORRemarkDetails', {}, 'bor'),
            ('post', '/api/mta/GetBOROrderAllocationReportData', {}, 'boroa'),
            ('post', '/api/mta/GetBOROrderAllocationReportDataCount', {}, 'boroa'),
            ('post', '/api/mta/AddBOROARemark', {}, 'boroa'),
            ('post', '/api/mta/GetBOROARemarkDetails', {}, 'boroa'),
            ('post', '/api/mta/GetExportDataAsync', {'reportName': 'BOR'}, 'bor'),
            ('post', '/api/mta/GetExportDataAsync', {'reportName': 'BOROA'}, 'boroa'),
        )
        with override_settings(VF_MTA_SYNTHETIC_ROSTER=SYNTHETIC):
            for method, path, payload, family in cases:
                call = getattr(client, method)
                response = (call(path, **IDENTITY) if payload is None else
                            call(path, json.dumps(payload), content_type='application/json', **IDENTITY))
                self.assertEqual(response.status_code, 503, path)
                self.assertEqual(response.json()['error'],
                    'synthetic_roster_report_unavailable:' + family + ':' + SYNTHETIC)

    def test_configuration_and_recipe_bind_the_roster(self):
        with override_settings(VF_MTA_SYNTHETIC_ROSTER=''):
            full = (daily_publication.configuration_identity(), daily_publication.recipe_identity())
        with override_settings(VF_MTA_SYNTHETIC_ROSTER=SYNTHETIC):
            reduced = (daily_publication.configuration_identity(), daily_publication.recipe_identity())
        self.assertNotEqual(full[0], reduced[0])
        self.assertNotEqual(full[1], reduced[1])


@override_settings(VF_MTA_DAILY_PUBLICATION=True, VF_MTA_PUBLISHED_RUN='',
                   VF_MTA_PUBLISHED_DIGEST='', VF_MTA_SYNTHETIC_ROSTER='')
class DailyRosterPublicationTests(TransactionTestCase):
    def setUp(self):
        self.run = CalculationRun.objects.create(
            kind='DAILY_CHAIN', status='RUNNING', business_date='2026-10-06',
            input_digest='i' * 64, output_digest='o' * 64, production_digest='p' * 64,
            execution_revision=self._testMethodName, input_payload={},
            production_manifest={'images': {}})
        DailySourceReceipt.objects.create(
            run=self.run, input_digest=self.run.input_digest,
            recipe_digest=source_recipe(), images={}, images_digest=digest({}))
        self.run.status = 'SUCCEEDED'
        self.run.save(update_fields=['status'])

    def test_ready_seal_rejects_roster_identity_drift(self):
        layers = {name: {'status': 'READY', 'receipt': {}}
                  for name in daily_preparation.required_layers()}
        publication = DailyUiPublication(
            run=self.run, status='READY', output_digest=self.run.output_digest,
            source_digest=daily_publication.source_identity(self.run),
            configuration_digest=daily_publication.configuration_identity(),
            recipe_digest=daily_publication.recipe_identity(), layers=layers,
            sealed_at=timezone.now())
        publication.seal_digest = daily_publication.seal_identity(publication)
        publication.save(force_insert=True)
        daily_publication.require_ready(self.run)
        with override_settings(VF_MTA_SYNTHETIC_ROSTER=SYNTHETIC):
            with self.assertRaisesRegex(PublicationUnavailable,
                                        'daily_ui_publication_seal_mismatch'):
                daily_publication.require_ready(self.run)

    @override_settings(VF_MTA_SYNTHETIC_ROSTER=SYNTHETIC)
    def test_failure_of_an_included_layer_keeps_reduced_roster_incomplete(self):
        def build(run, name):
            if name == 'dbm_sources':
                raise ValueError('included source unavailable')
            return {'source_digest': 's', 'recipe_digest': 'r',
                    'rows_digest': name, 'row_count': 0}
        with patch('mta.presentation.daily_preparation.prepare_layer', side_effect=build), \
                patch('mta.presentation.daily_preparation.verify_layer'):
            publication = daily_publication.prepare(
                self.run.pk, expected_output_digest=self.run.output_digest)
        self.assertEqual(publication.status, 'INCOMPLETE')
        self.assertEqual(set(publication.layers), set(daily_preparation.SYNTHETIC_REQUIRED_LAYERS))
        self.assertEqual(publication.layers['dbm_sources']['status'], 'FAILED')
        self.assertNotIn('bor', publication.layers)
        self.assertNotIn('boroa', publication.layers)

    def _fixture_teardown(self):
        pass
