import os
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import Client

from mta.presentation.descriptions import description_rows, selected_descriptions
from mta.presentation.permissions import PermissionCodes


class DescriptionLookupTests(unittest.TestCase):
    def test_endpoint_identity_and_empty_id_source_failure(self):
        client = Client()
        for route in ('SKUDesc', 'WHDesc'):
            self.assertEqual(client.get('/api/mta/' + route).status_code, 403)
            response = client.get('/api/mta/' + route, HTTP_X_VECTORFLOW_IDENTITY='{"id":"1"}')
            self.assertEqual(response.status_code, 500)
            self.assertIsNone(response.json()['data'])

    def test_join_bag_nulls_case_and_padding(self):
        rows = [dict(SKUCode='a ', SKUDescription='first '),
                dict(SKUCode='A', SKUDescription=None),
                dict(SKUCode=None, SKUDescription='must not match'),
                dict(SKUCode='b', SKUDescription='denied')]
        codes = PermissionCodes({'A': 2, 'a ': 1})
        self.assertEqual(description_rows(rows, codes, 'sku'),
            [dict(sc='a ', sd='first ')] * 3 + [dict(sc='A')] * 3)
        self.assertIsNone(description_rows(rows, PermissionCodes({}), 'sku'))

    def test_location_aliases_preserve_description_duplicates(self):
        rows = [dict(WHCode='L', WHDescription='one'), dict(WHCode='L', WHDescription='two')]
        self.assertEqual(description_rows(rows, {'L'}, 'location'),
                         [dict(wc='L', wd='one'), dict(wc='L', wd='two')])

    def test_selective_reads_use_btr_owner_and_native_null_scope(self):
        paths = []
        attributes = {'SkuAttributeData': [{'native': 'sku'}],
                      'LocationAttributeData': [{'native': 'location'}]}
        def read(run, path):
            paths.append(path)
            return attributes.get(path.rsplit('/', 1)[1], [dict(SKUCode='S', SKUDescription='kept')])
        with patch('mta.presentation.descriptions.selected_run', return_value=object()), \
             patch('mta.presentation.descriptions.image_rows', side_effect=read), \
             patch('mta.presentation.descriptions.hierarchy.selected_manifest', return_value=None), \
             patch('mta.presentation.descriptions.scope', return_value=(set(), set())) as scoped:
            self.assertIsNone(selected_descriptions({'product_permissions': []}, 'sku'))
            self.assertEqual(scoped.call_args.kwargs['attributes'], attributes)
        self.assertEqual(paths, ['closing/btr/SkuAttributeData', 'closing/btr/LocationAttributeData',
                                 'closing/btr/SKUDescriptionTbl'])


if __name__ == '__main__':
    unittest.main()
