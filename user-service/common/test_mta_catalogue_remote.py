import unittest
from unittest.mock import Mock, patch

from requests import Timeout
from common.mta_catalogue import CatalogueUnavailable, remote_payload


class RemoteCatalogueTests(unittest.TestCase):
    def test_empty_population_is_valid_but_failure_is_not(self):
        empty = {'product': [], 'location': []}
        with patch('common.startup_probe.permission_request',
                   return_value=Mock(status_code=200, json=Mock(return_value=empty))) as request:
            self.assertEqual(remote_payload('http://mta/catalogue'), empty)
        request.assert_called_once_with('permission_mta', method='GET',
                                       url='http://mta/catalogue', timeout=(3.05, 15))
        for status in (401, 403, 404, 500, 503):
            response = Mock(status_code=status, json=Mock(return_value=empty))
            with self.subTest(status=status), patch(
                    'common.startup_probe.permission_request', return_value=response):
                with self.assertRaises(CatalogueUnavailable):
                    remote_payload('http://mta/catalogue')
                response.json.assert_not_called()

    def test_transport_invalid_json_and_invalid_shapes_fail_closed(self):
        with patch('common.startup_probe.permission_request', side_effect=Timeout):
            with self.assertRaises(CatalogueUnavailable):
                remote_payload('http://mta/catalogue')
        for value in (None, [], {}, {'error': 'not_ready'},
                      {'product': None, 'location': []}):
            with self.subTest(value=value), patch('common.startup_probe.permission_request',
                    return_value=Mock(status_code=200, json=Mock(return_value=value))):
                with self.assertRaises(CatalogueUnavailable):
                    remote_payload('http://mta/catalogue')
        with patch('common.startup_probe.permission_request',
                   return_value=Mock(status_code=200, json=Mock(side_effect=ValueError))):
            with self.assertRaises(CatalogueUnavailable):
                remote_payload('http://mta/catalogue')

    def test_successful_catalogue_is_preserved_without_scope_invention(self):
        value = {'product': [{'id': 4, 'product_hierarchy_1': None}] * 2,
                 'location': [{'id': 8, 'location_heirarchy_1': 'Mixed '}]}
        with patch('common.startup_probe.permission_request',
                   return_value=Mock(status_code=200, json=Mock(return_value=value))):
            self.assertIs(remote_payload('http://mta/catalogue'), value)
