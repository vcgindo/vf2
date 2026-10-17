"""Metadata availability must not admit operational rows or weakened identities.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'installation-contract-unit-only')
import django
django.setup()
from django.test import SimpleTestCase, override_settings
from mta.presentation import admission, installation_metadata as metadata
from mta.presentation.context import PublicationUnavailable
from mta.mdm import integration_source


@override_settings(VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST='',
    VF_MTA_SELECTION_FILE='', VF_MTA_SELECTION=None,
    VF_MTA_FIXTURE_FILE='', VF_MTA_FIXTURE_SHA256='')
class InstallationMetadataTests(SimpleTestCase):
    def test_only_existing_metadata_methods_and_queries_are_classified(self):
        self.assertTrue(metadata.metadata_request(dict(PATH_INFO='/api/mta/GetMasterUIConfiguration', REQUEST_METHOD='POST')))
        self.assertTrue(metadata.metadata_request(dict(PATH_INFO='/api/mta/GetUIConfig', QUERY_STRING='reportName=AdminBPR')))
        for path, method, query in (
                ('GetBPRData', 'POST', ''), ('AddMasterData', 'POST', ''),
                ('SaveState', 'POST', ''), ('GetState', 'GET', ''),
                ('GetUIConfig', 'GET', 'reportName=BOR_OA'),
                ('GetUIConfig', 'GET', 'reportName=BuyerOrderReport'),
                ('GetUIConfig', 'GET', 'reportName=AdminBPR&reportName=BOR_OA')):
            self.assertFalse(metadata.metadata_request(dict(PATH_INFO='/api/mta/'+path,
                REQUEST_METHOD=method, QUERY_STRING=query)))

    def dispatch(self, path, method='GET', query=''):
        app = admission.AdmittedApplication.__new__(admission.AdmittedApplication)
        app.application = Mock(return_value=[b'original endpoint'])
        start = Mock()
        body = b''.join(app._dispatch(dict(PATH_INFO='/api/mta/'+path,
            REQUEST_METHOD=method, QUERY_STRING=query), start))
        return app, start, body

    def test_metadata_uses_install_authority_but_operational_requests_stay_closed(self):
        with patch.object(metadata, 'require_installation', return_value=None) as check, \
                patch.object(admission, 'require_admission', side_effect=PublicationUnavailable('no publication')):
            app, _, body = self.dispatch('GetEnvironmentConfiguration')
            self.assertEqual(body, b'original endpoint')
            check.assert_called_once()
            app.application.assert_called_once()
            app, start, body = self.dispatch('GetBPRData', 'POST')
            self.assertEqual(json.loads(body), {'error': 'publication_not_admitted'})
            app.application.assert_not_called()
            self.assertTrue(start.call_args.args[0].startswith('503'))

    def test_corrupt_installation_cannot_reach_original_metadata_handler(self):
        with patch.object(metadata, 'require_installation', side_effect=PublicationUnavailable('bad role')):
            app, _, _ = self.dispatch('GetEnvironmentConfiguration')
            app.application.assert_not_called()

    def test_initialized_master_route_requires_validated_source_and_never_admits_write(self):
        with patch.object(metadata, 'require_installation', return_value=None):
            app, _, _ = self.dispatch('GetMasterData', 'POST')
            app.application.assert_not_called()
        with patch.object(metadata, 'require_installation', return_value=object()) as verify, \
                patch.object(admission, 'require_admission', side_effect=PublicationUnavailable('no publication')):
            app, _, body = self.dispatch('GetMasterData', 'POST')
            self.assertEqual(body, b'original endpoint')
            verify.assert_called_once()
            app, _, _ = self.dispatch('ModifyMasterData', 'POST')
            app.application.assert_not_called()

    def test_every_partial_or_configured_publication_uses_existing_admission(self):
        for name, value in (
                ('VF_MTA_PUBLISHED_RUN', 'missing'), ('VF_MTA_PUBLISHED_DIGEST', 'f'*64),
                ('VF_MTA_SELECTION_FILE', '/not-present'), ('VF_MTA_SELECTION', {}),
                ('VF_MTA_FIXTURE_SHA256', 'f'*64)):
            # A configured selection object is normally nonempty; even an empty
            # one must never authorize metadata as an unselected installation.
            with self.subTest(name=name), override_settings(**{name: value}), \
                    patch.object(metadata, 'require_installation') as check, \
                    patch.object(admission, 'require_admission', side_effect=PublicationUnavailable('bad selection')):
                app, _, _ = self.dispatch('GetEnvironmentConfiguration')
                app.application.assert_not_called()
                check.assert_not_called()

    def test_existing_family_fields_and_operation_eligibility_are_reused(self):
        with patch.object(metadata, 'require_installation', return_value=None):
            rows = metadata.configuration('modify')
        self.assertEqual({r['name'] for r in rows}, {
            'SKU', 'Location', 'SKULocation', 'SOB', 'MOQ', 'StopPIPO',
            'SeasonalityStatus', 'ForceNormChange'})
        sku = next(r for r in rows if r['id'] == '1')
        self.assertTrue(sku['fields'])
        self.assertTrue(all(set(f) == {'displayName', 'key', 'col_Position', 'visible',
            'isAdd', 'isEdit', 'isDelete', 'isDownload', 'isApplicable', 'dataType'} for f in sku['fields']))

    def test_initialized_reader_checks_seal_and_zero_day_without_selecting_fake_run(self):
        source = SimpleNamespace(receipt={'schema': 'fresh-production-mdm-source-v1'})
        with patch('mta.mdm.production_families.require_binding', return_value='verified-seal') as verify, \
                patch('mta.runtime.models.CalculationRun.objects.exists', return_value=False), \
                patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.filter') as captures, \
                patch('mta.presentation.context.selected_run', side_effect=AssertionError('fake run')):
            captures.return_value.exists.return_value = False
            self.assertEqual(integration_source.require_read_binding(source, read_only=True), 'verified-seal')
            verify.assert_called_once_with(source, read_only=True)
            captures.return_value.exists.return_value = True
            with self.assertRaisesRegex(ValueError, 'untouched'):
                integration_source.require_read_binding(source, read_only=True)

    def test_initialized_reader_retains_configured_publication_checks(self):
        source = SimpleNamespace(receipt={'schema': 'fresh-production-mdm-source-v1'})
        with override_settings(VF_MTA_SELECTION_FILE='/configured/missing'), \
                patch('mta.mdm.production_families.require_binding', return_value='verified-seal'), \
                patch('mta.presentation.context.selected_run', side_effect=PublicationUnavailable('invalid selection')):
            with self.assertRaisesRegex(PublicationUnavailable, 'invalid selection'):
                integration_source.require_read_binding(source, read_only=True)


@unittest.skipUnless(importlib.util.find_spec('rest_framework'), 'Auth dependencies are verified inside the existing auth container')
class RemotePermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1]/'user-service/common/mta_catalogue.py'
        spec = importlib.util.spec_from_file_location('installation_test_catalogue', path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_empty_is_valid_only_after_successful_shaped_response(self):
        response = Mock(status_code=200)
        response.json.return_value = dict(product=[], location=[])
        self.assertEqual(self.module.remote_payload(response), dict(product=[], location=[]))
        for status, body in [(503, {'error': 'publication_not_admitted'}),
                (200, {}), (200, {'product': [], 'location': None}),
                (200, {'product': [{'id': 1}], 'location': []})]:
            with self.subTest(status=status, body=body):
                response.status_code, response.json.return_value = status, body
                with self.assertRaises(self.module.CatalogueUnavailable):
                    self.module.remote_payload(response)
