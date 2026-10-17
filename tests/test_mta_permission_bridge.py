"""MTA catalogue failure must remain distinct from valid empty definitions.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import importlib.util
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


@unittest.skipUnless(importlib.util.find_spec('rest_framework'), 'Run with existing auth dependencies')
class MtaPermissionBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.auth_settings')
        import django
        django.setup()
        from common import api_gateway_utils
        cls.gateway = api_gateway_utils

    def assemble(self, response=None, error=None):
        g = self.gateway
        with patch.dict(g.service_map, {
                'mto': dict(active=False),
                'mta': dict(active=True, base_url='http://mta:8000', application_id=1)}), \
                patch.object(g, 'local_mta_catalogue', return_value=False), \
                patch.object(g, 'get_application_details_by_id', return_value=SimpleNamespace(
                    application_id=1, application_name='MTA')), \
                patch.object(g, 'permission_request', return_value=response, side_effect=error):
            return g.ALL_PERMISSIONS.get_combined_permissions()

    def test_transport_http_and_malformed_failures_are_not_successful_omission(self):
        import requests
        from common.mta_catalogue import CatalogueUnavailable
        for error in (requests.ConnectionError('unavailable'), requests.Timeout('timeout')):
            with self.subTest(error=type(error).__name__), self.assertRaises(CatalogueUnavailable):
                self.assemble(error=error)
        for status, body in ((503, {}), (200, {}), (200, {'product': [], 'location': None})):
            response = Mock(status_code=status)
            response.json.return_value = body
            with self.subTest(status=status, body=body), self.assertRaises(CatalogueUnavailable):
                self.assemble(response=response)

    def test_valid_empty_and_populated_shapes_preserve_mta_entry(self):
        product = {'id': 7, **{'product_hierarchy_'+str(i): None for i in (1, 2, 3)}}
        location = {'id': 4, **{'location_heirarchy_'+str(i): None for i in (1, 2, 3)}}
        for products, locations in (([], []), ([product], [location])):
            response = Mock(status_code=200)
            response.json.return_value = dict(product=products, location=locations)
            self.assertEqual(self.assemble(response=response), [dict(application_id=1,
                application_name='MTA', product_permission=products, location_permission=locations)])


if __name__ == '__main__':
    unittest.main()
