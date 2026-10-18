"""Selected Pick file access checks; no database or serving process."""
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from django.test import Client, override_settings
from mta.presentation.context import PublicationUnavailable
from mta.presentation import pick_downloads


IDENTITY = {'HTTP_X_VECTORFLOW_IDENTITY': json.dumps(
    {'id': 7, 'name': 'gateway-user', 'entitlements': ['mta-report-urls']})}
ROWS = [dict(SKUCode='A', WHCode='TO', ParentWHCode='FROM', LogisticLocation='LOG')]


class PickDownloadTests(unittest.TestCase):
    def test_complete_pick_metadata_accepts_only_its_declared_typed_bindings(self):
        from mta.presentation.selective import image_metadata
        from mta.runtime.complete_daily_state import BINDINGS, TABLES
        for name in ('LogisticPickList', 'PickListDataForTruckFormation'):
            path = 'closing/complete/' + name
            key = BINDINGS[path]
            metadata = dict(image=path, table=key, count=1, digest='unused',
                            fields=[[column, column, 'str'] for column, _ in TABLES[key]])
            run = SimpleNamespace(kind='DAILY_CHAIN',
                                  production_manifest={'images': {path: metadata}})
            self.assertIs(image_metadata(run, path), metadata)
            metadata['table'] = 'importer/SkuAttributeData'
            with self.assertRaisesRegex(PublicationUnavailable, 'table_mismatch'):
                image_metadata(run, path)
            metadata['table'] = key
            metadata['fields'].append(['unexpected', 'unexpected', 'str'])
            with self.assertRaisesRegex(PublicationUnavailable, 'column_mismatch'):
                image_metadata(run, path)

    def setUp(self):
        self.run = SimpleNamespace(pk='11111111-1111-1111-1111-111111111111',
                                   kind='DAILY_CHAIN', status='SUCCEEDED')
        self.payload = {'product_permissions': [1], 'location_permissions': [2]}

    def images(self, run, path):
        if path.endswith('/LogisticPickList'):
            return ROWS
        if path.endswith('/PickListDataForTruckFormation'):
            return []
        return []

    def test_exact_four_keys_and_selected_run_bytes(self):
        expected = {
            'LogisticPickListReport', 'LogisticRemainingQtySummary',
            'LogisticRemainingQtyDetails', 'TransportReqSummaryRpt'}
        self.assertEqual(set(pick_downloads.REPORTS), expected)
        catalogue = Client().get('/api/mta/GetAllReports', **{
            'HTTP_X_VECTORFLOW_IDENTITY': '{"id":7}'}).json()['data']
        self.assertEqual(set(catalogue) & expected, expected)
        self.assertTrue(all(catalogue[key]['path'] == '' and
                            catalogue[key]['downloadName'] == pick_downloads.REPORTS[key]
                            for key in expected))
        with self.assertRaisesRegex(pick_downloads.PickDownloadDenied, 'unknown'):
            pick_downloads.open_report(self.run, self.payload, '../other-run')
        with TemporaryDirectory() as directory:
            root = Path(directory)
            download = root/str(self.run.pk)/'download'
            download.mkdir(parents=True)
            target = download/'LogisticPickListReport.csv'
            target.write_bytes(b'own-selected-run-bytes\r\n')
            with patch.object(pick_downloads, 'image_rows', side_effect=self.images), \
                    patch.object(pick_downloads, 'scope', return_value=(
                        {'A'}, {'TO', 'FROM', 'LOG'})), \
                    patch.object(pick_downloads, 'read_input',
                                 return_value={'pick_output_root': str(root)}), \
                    patch.object(pick_downloads, '_expected_bytes',
                                 return_value=b'own-selected-run-bytes\r\n'):
                stream, name = pick_downloads.open_report(
                    self.run, self.payload, 'LogisticPickListReport')
                with stream:
                    self.assertEqual(stream.read(), b'own-selected-run-bytes\r\n')
                self.assertEqual(name, target.name)

    def test_partial_scope_is_denied_without_filtering_or_opening(self):
        with patch.object(pick_downloads, 'image_rows', side_effect=self.images), \
                patch.object(pick_downloads, 'scope', return_value=(
                    {'A'}, {'TO', 'FROM'})), \
                patch.object(pick_downloads, '_owned_file',
                             side_effect=AssertionError('must not open')):
            with self.assertRaisesRegex(pick_downloads.PickDownloadDenied, 'scope'):
                pick_downloads.open_report(self.run, self.payload,
                                           'LogisticPickListReport')

    def test_scope_uses_sql_equality_for_all_identifiers_and_only_contributing_rows(self):
        formed = [dict(SKUCode='sku ', WHCode='to ', ParentWHCode='from ',
                       LogisticLocation='log ')]
        residual = [dict(SKUCode='OTHER', WHCode='DENIED', ParentWHCode='DENIED',
                         LogisticLocation='DENIED')]
        state = {'LogisticPickList': formed,
                 'PickListDataForTruckFormation': residual}
        with patch.object(pick_downloads, '_attributes', return_value={}), \
                patch.object(pick_downloads, 'scope', return_value=(
                    {'SKU'}, {'TO', 'FROM', 'LOG'})):
            self.assertTrue(pick_downloads._fully_scoped(
                self.run, self.payload, state, 'LogisticPickListReport'))
            self.assertTrue(pick_downloads._fully_scoped(
                self.run, self.payload, state, 'TransportReqSummaryRpt'))
            self.assertFalse(pick_downloads._fully_scoped(
                self.run, self.payload, state, 'LogisticRemainingQtySummary'))
            self.assertFalse(pick_downloads._fully_scoped(
                self.run, self.payload, state, 'LogisticRemainingQtyDetails'))

    def test_cross_run_missing_and_symlink_roots_are_denied(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            other = root/'22222222-2222-2222-2222-222222222222'/'download'
            other.mkdir(parents=True)
            (other/'LogisticPickListReport.csv').write_bytes(b'other-run')
            with patch.object(pick_downloads, 'image_rows', side_effect=self.images), \
                    patch.object(pick_downloads, 'scope', return_value=(
                        {'A'}, {'TO', 'FROM', 'LOG'})), \
                    patch.object(pick_downloads, 'read_input',
                                 return_value={'pick_output_root': str(root)}):
                with self.assertRaisesRegex(pick_downloads.PickDownloadDenied, 'unavailable'):
                    pick_downloads.open_report(self.run, self.payload,
                                               'LogisticPickListReport')
            with patch.object(pick_downloads, 'read_input',
                              return_value={'pick_output_root': str(root)}), \
                    patch.object(Path, 'is_symlink', return_value=True):
                with self.assertRaisesRegex(pick_downloads.PickDownloadDenied, 'path_denied'):
                    pick_downloads._owned_file(self.run, 'LogisticPickListReport.csv')

    def test_file_drift_is_denied_instead_of_rebuilt(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            download = root/str(self.run.pk)/'download'
            download.mkdir(parents=True)
            (download/'LogisticPickListReport.csv').write_bytes(b'tampered')
            with patch.object(pick_downloads, 'image_rows', side_effect=self.images), \
                    patch.object(pick_downloads, 'scope', return_value=(
                        {'A'}, {'TO', 'FROM', 'LOG'})), \
                    patch.object(pick_downloads, 'read_input',
                                 return_value={'pick_output_root': str(root)}), \
                    patch.object(pick_downloads, '_expected_bytes', return_value=b'expected'):
                with self.assertRaisesRegex(pick_downloads.PickDownloadDenied, 'file_drift'):
                    pick_downloads.open_report(self.run, self.payload,
                                               'LogisticPickListReport')

    def test_http_requires_gateway_entitlement_and_selected_accepted_run(self):
        client = Client()
        with patch('mta.presentation.views.selected_run', side_effect=AssertionError('must not select')):
            denied = client.get('/api/mta/DownloadReports/LogisticPickListReport',
                                HTTP_X_VECTORFLOW_IDENTITY='{"id":7}')
        self.assertEqual(denied.status_code, 403)
        with patch('mta.presentation.views.selected_run',
                   side_effect=PublicationUnavailable('publication_identity_or_status_mismatch')):
            failed = client.get('/api/mta/DownloadReports/LogisticPickListReport', **IDENTITY)
        self.assertEqual(failed.status_code, 503)

    def test_http_denies_removed_fixture_configuration_before_database_access(self):
        client = Client()
        with override_settings(VF_MTA_FIXTURE_FILE='forbidden-historical-mode'), \
                patch('mta.presentation.context.CalculationRun.objects.filter',
                      side_effect=AssertionError('must not read database')):
            denied = client.get('/api/mta/DownloadReports/LogisticPickListReport',
                                **IDENTITY)
        self.assertEqual(denied.status_code, 503)
        self.assertEqual(denied.json()['error'], 'removed_historical_mode:VF_MTA_FIXTURE_FILE')

    def test_non_completed_daily_run_is_denied_before_state_access(self):
        for run in (SimpleNamespace(kind='LEGACY_UI_FIXTURE', status='SUCCEEDED'),
                    SimpleNamespace(kind='DAILY_CHAIN', status='FAILED')):
            with patch.object(pick_downloads, '_complete_state',
                              side_effect=AssertionError('must not read')):
                with self.assertRaisesRegex(pick_downloads.PickDownloadDenied, 'status_denied'):
                    pick_downloads.open_report(run, self.payload,
                                               'LogisticPickListReport')

    def test_http_returns_exact_opened_bytes_and_filename(self):
        client = Client()
        with patch('mta.presentation.views.selected_run', return_value=self.run), \
                patch('mta.presentation.pick_downloads.open_report',
                      return_value=(BytesIO(b'exact-csv\r\n'), 'LogisticPickListReport.csv')) as opened:
            response = client.generic('GET', '/api/mta/DownloadReports/LogisticPickListReport',
                json.dumps(self.payload), content_type='application/json', **IDENTITY)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'exact-csv\r\n')
        self.assertIn('LogisticPickListReport.csv', response['Content-Disposition'])
        opened.assert_called_once_with(self.run, self.payload, 'LogisticPickListReport')


if __name__ == '__main__':
    unittest.main()
