"""A real empty-state response is neither a fabricated report nor admission bypass."""
import json
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('VF_SECRET_KEY', 'non-serving-setup-tests')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.conf import settings
from django.test import RequestFactory, override_settings
from mta.presentation import admission, application_state, mdm_views, views
from mta.presentation.context import PublicationUnavailable


INSTALLED = dict(installed=True, initialized=False, publication_selected=False, state='installed')


class SetupApplicationTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, admission, '_setup_release', admission._setup_release)
        self.addCleanup(setattr, admission, '_admitted', admission._admitted)
        admission._setup_release = None

    def request(self, path, *, authenticated=True, body=None, method='post'):
        header = 'HTTP_' + settings.MTA_TRUSTED_GATEWAY_HEADER.upper().replace('-', '_')
        headers = {header: json.dumps({'id': 17, 'name': 'Assigned reader'})} if authenticated else {}
        return RequestFactory().generic(method.upper(), path, json.dumps(body or {}),
                                        content_type='application/json', **headers)

    def test_configuration_without_source_retains_family_operation_filtering(self):
        with patch.object(admission, 'require_application_state', return_value=INSTALLED), \
                patch.object(mdm_views, 'source', side_effect=AssertionError('fake source')):
            config = mdm_views.configuration(self.request('/api/mta/GetMasterUIConfiguration',
                                                         body={'screenType': 'modify'}))
            value = json.loads(config.content)
            self.assertEqual(config.status_code, 200)
            self.assertEqual({int(r['id']) for r in value['data']}, {1, 2, 3, 4, 5, 6, 10, 13})
            self.assertTrue(all(row['name'] and row['fields'] for row in value['data']))
            added = json.loads(mdm_views.configuration(self.request('/api/mta/GetMasterUIConfiguration',
                                                    body={'screenType': 'add'})).content)
            self.assertTrue({7, 8, 9}.issubset({int(r['id']) for r in added['data']}))
            self.assertEqual(added['setupRequirements'], [
                dict(masterId=5, setting='NMSMOQInputDataFormat', state='not_configured')])
            moq = next(r for r in added['data'] if r['id'] == '5')
            self.assertFalse(next(f for f in moq['fields'] if f['key'] == 'wc')['isAdd'])

    def test_metadata_still_requires_identity_and_operational_requests_have_no_fake_data(self):
        with patch.object(admission, 'require_application_state', return_value=INSTALLED) as state:
            denied = views.environment(self.request('/api/mta/GetEnvironmentConfiguration',
                                                    method='get', authenticated=False))
            self.assertEqual(denied.status_code, 403)
            state.assert_not_called()
            metadata = views.environment(self.request('/api/mta/GetEnvironmentConfiguration', method='get'))
            self.assertEqual(metadata.status_code, 200)
            self.assertEqual(json.loads(metadata.content)['application'], INSTALLED)
            for function, name, kwargs in ((views.bpr_data, 'GetBPRData', {}),
                    (views.last_run_date, 'GetLastRunDate', {}),
                    (views.dbm_action, 'DBMApplySelectedNorms', {'operation': 'APPLY'})):
                response = function(self.request('/api/mta/' + name,
                                    method='get' if name == 'GetLastRunDate' else 'post'), **kwargs)
                self.assertEqual(response.status_code, 409)
                body = json.loads(response.content)
                self.assertEqual(body['error'], 'application_setup_required')
                self.assertNotIn('data', body)
                self.assertNotIn('recordCount', body)

    @override_settings(VF_MTA_PERMISSIONS_FILE='', VF_MTA_PERMISSIONS_SHA256='')
    def test_no_business_population_does_not_invent_permission_ids(self):
        with patch.object(admission, 'require_application_state', return_value=INSTALLED):
            response = views.all_permissions(self.request('/api/mta/GetAllPermmision', method='get'))
        value = json.loads(response.content)
        self.assertEqual(value['product'], [])
        self.assertEqual(value['location'], [])
        self.assertEqual(value['application']['state'], 'installed')

    def test_empty_report_definitions_do_not_enable_published_unsupported_readers(self):
        for name, count in (('OrderAllocationReport', 18), ('ElephantOrderReport', 12)):
            request = self.request('/api/mta/GetUIConfig?reportName=' + name, method='get')
            with patch.object(admission, 'require_application_state', return_value=INSTALLED):
                result = views.ui_config(request)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(len(json.loads(result.content)['data']), count)
            with patch.object(admission, 'require_application_state', return_value=None):
                self.assertEqual(views.ui_config(request).status_code, 404)

    def test_setup_availability_does_not_claim_business_readiness(self):
        from vectorflow.urls import ready
        with patch('vectorflow.urls.connection.cursor') as cursor, \
                patch.object(admission, 'require_admission', side_effect=PublicationUnavailable('not selected')), \
                patch.object(admission, 'require_application_state', return_value=INSTALLED):
            cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            response = ready(RequestFactory().get('/readyz'))
        self.assertEqual(response.status_code, 503)
        value = json.loads(response.content)
        self.assertIs(value['ready'], False)
        self.assertIs(value['application']['available'], True)
        self.assertIs(value['application']['initialized'], False)

    @override_settings(VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST='',
                       VF_MTA_SELECTION_FILE='', VF_MTA_SELECTION=None,
                       VF_MTA_FIXTURE_FILE='', VF_MTA_FIXTURE_SHA256='')
    def test_partial_or_missing_after_use_selection_cannot_be_setup(self):
        for setting in ('VF_MTA_PUBLISHED_RUN', 'VF_MTA_PUBLISHED_DIGEST', 'VF_MTA_SELECTION_FILE',
                        'VF_MTA_FIXTURE_SHA256'):
            with self.subTest(setting=setting), override_settings(**{setting: 'invalid'}):
                with self.assertRaisesRegex(PublicationUnavailable, 'requires_admission'):
                    application_state.setup_state()
        with patch('mta.runtime.models.CalculationRun.objects.exists', return_value=True):
            with self.assertRaisesRegex(PublicationUnavailable, 'existing_runs_require'):
                application_state.setup_state()

    @override_settings(VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST='', VF_MTA_SELECTION_FILE='',
                       VF_MTA_SELECTION=None, VF_MTA_FIXTURE_FILE='', VF_MTA_FIXTURE_SHA256='',
                       VF_MDM_SOURCE_DIGEST='chosen-initial-source')
    def test_initialized_reader_requires_untouched_sealed_owners_not_a_selected_run(self):
        from mta.runtime.models import CalculationRun, MdmSource, ProductionInitialization
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        installed = Mock(digest='chosen-initial-source')
        with patch.object(CalculationRun.objects, 'exists', return_value=False), \
                patch.object(MdmSource.objects, 'count', return_value=1), \
                patch.object(ProductionInitialization.objects, 'count', return_value=1), \
                patch.object(MdmDailyInputCapture.objects, 'exists', return_value=False), \
                patch.object(MdmSource.objects, 'filter') as sources, \
                patch.object(ProductionInitialization.objects, 'filter') as owners, \
                patch('mta.mdm.production_families.require_binding') as binding, \
                patch.object(ProductionInitialization.objects, 'select_related'), \
                patch('mta.mdm.initialization.read_initialized_input', return_value={'opening': {'state': {}}}), \
                patch('mta.mdm.master_owners.owner_batches', return_value=[]) as batches, \
                patch('mta.mdm.initialization.verify_current_masters') as masters:
            sources.return_value.first.return_value = installed
            owners.return_value.exists.return_value = True
            self.assertIs(application_state.initialized_source(), installed)
            binding.assert_called_once_with(installed, read_only=True)
            masters.assert_called_once_with(installed, [])
            binding.reset_mock()
            with patch.object(MdmDailyInputCapture.objects, 'exists', return_value=True):
                with self.assertRaisesRegex(PublicationUnavailable, 'untouched_initialization'):
                    application_state.initialized_source()
            binding.assert_not_called()
            with override_settings(VF_MDM_SOURCE_DIGEST=''):
                with self.assertRaisesRegex(PublicationUnavailable, 'mdm_source_not_selected'):
                    application_state.initialized_source()

    def test_mdm_writes_still_require_publication_after_initialization(self):
        state = dict(INSTALLED, initialized=True, state='initialized', source_digest='source')
        with patch.object(admission, 'require_application_state', return_value=state), \
                patch.object(mdm_views, 'source', side_effect=AssertionError('write must not reach source')):
            for function, kwargs, method in ((mdm_views.submit, {'action': 'add'}, 'post'),
                    (mdm_views.approve, {}, 'post'), (mdm_views.delete_task, {}, 'delete')):
                response = function(self.request('/api/mta/write', method=method), **kwargs)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(json.loads(response.content)['detail'], 'published_operational_day_required')

    def test_initialized_draft_listing_uses_verified_read_source_without_publication(self):
        installed = Mock()
        state = dict(INSTALLED, initialized=True, state='initialized', source_digest='source')
        with patch.object(admission, 'require_application_state', return_value=state), \
                patch.object(mdm_views, 'source', return_value=installed) as selected, \
                patch('mta.runtime.mdm_models.MdmSource.objects.filter') as rows, \
                patch('mta.mdm.supplier_revisions.source_lock'), \
                patch.object(mdm_views.drafts, 'listing', return_value=[]):
            rows.return_value.values_list.return_value.first.return_value = 1
            response = mdm_views.all_drafts(self.request('/api/mta/allDrafts', method='get'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content)['data'], [])
            selected.assert_called_once_with(read_only=True)

    @override_settings(VF_MDM_SOURCE_DIGEST='chosen-initial-source')
    def test_source_initial_read_path_is_limited_to_validated_setup(self):
        from mta.mdm import source as sources
        installed = Mock(digest='chosen-initial-source', receipt={'schema': 'fresh-production-mdm-source-v1'})
        state = dict(INSTALLED, initialized=True, state='initialized', source_digest=installed.digest)
        with patch.object(sources.MdmSource.objects, 'filter') as rows, \
                patch.object(admission, 'require_application_state', return_value=state), \
                patch('mta.mdm.integration_source.require_read_binding') as selected_binding:
            rows.return_value.first.return_value = installed
            self.assertIs(sources.source(read_only=True), installed)
            selected_binding.assert_not_called()
            with patch.object(admission, 'require_application_state', return_value=None), \
                    patch('mta.mdm.native_source.require_base') as base:
                self.assertIs(sources.source(read_only=True), installed)
                self.assertEqual(base.call_count, 3)
                selected_binding.assert_called_once_with(installed, read_only=True)

    @override_settings(VF_MTA_ALLOW_UNSELECTED_STARTUP=True, VF_MTA_DAILY_PUBLICATION=True,
                       VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST='',
                       VF_MTA_SELECTION_FILE='', VF_MTA_SELECTION=None,
                       VF_MTA_FIXTURE_FILE='', VF_MTA_FIXTURE_SHA256='')
    def test_empty_wsgi_requires_source_validation_and_revokes_on_setup_drift(self):
        downstream = Mock(return_value=[b'endpoint still owns identity and prerequisites'])
        with patch('release.installed_application.verify_export', side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                admission.AdmittedApplication(downstream)
        self.assertIsNone(admission._setup_release)
        with patch('release.installed_application.verify_export', return_value='a' * 40), \
                patch.object(application_state, 'setup_state', return_value=INSTALLED):
            app = admission.AdmittedApplication(downstream)
            self.assertEqual(app({'PATH_INFO': '/api/mta/GetEnvironmentConfiguration'}, Mock()),
                             [b'endpoint still owns identity and prerequisites'])
        downstream.reset_mock()
        with patch.object(application_state, 'setup_state',
                          side_effect=PublicationUnavailable('source changed')):
            status = Mock()
            self.assertIn(b'publication_not_admitted',
                          b''.join(app({'PATH_INFO': '/api/mta/GetEnvironmentConfiguration'}, status)))
            self.assertEqual(status.call_args.args[0], '503 Service Unavailable')
        downstream.assert_not_called()
