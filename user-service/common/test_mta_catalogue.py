import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase
from api.models import ApplicationMaster, User, User_Application_Product_Permission
from api.core import ResponseUser, ResponseProfile
from api.serializer.profile import UserProfileSerializer
from common.api_gateway_utils import ALL_PERMISSIONS
from common.mta_catalogue import CatalogueUnavailable, payload, validate_configured


class LocalCatalogueTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {
            'VF_MTA_LOCAL_PERMISSIONS': '1', 'VF_MTA_FIXTURE_FILE': '',
            'VF_MTA_FIXTURE_SHA256': '', 'VF_MTA_PUBLISHED_RUN': 'accepted',
            'VF_MTA_PUBLISHED_DIGEST': 'output',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.catalogue = dict(version='block1-permissions-v1', **{
            name: dict(records=[dict(id=7, level_1='Mixed ', level_2=None, level_3='é'),
                                dict(id=4, level_1='Mixed ', level_2=None, level_3='é')])
            for name in ('products', 'locations')})
        self.install('VF_MTA_PERMISSIONS', self.catalogue)
        self.binding = dict(version='fresh-presentation-hierarchy-v1',
            catalogue_sha256=os.environ['VF_MTA_PERMISSIONS_SHA256'],
            publications=[dict(run_id='accepted', output_digest='output')])
        self.install('VF_MTA_HIERARCHY', self.binding)
        self.service = patch('common.api_gateway_utils.service_map', {
            'mta': dict(active=True, application_id=2), 'mto': dict(active=False)})
        self.service.start()
        self.addCleanup(self.service.stop)
        ApplicationMaster.objects.create(application_id=2, application_name='MTA')

    def install(self, prefix, value):
        path = Path(self.directory.name) / (prefix + '.json')
        raw = json.dumps(value, ensure_ascii=False).encode()
        path.write_bytes(raw)
        os.environ[prefix + '_FILE'] = str(path)
        os.environ[prefix + '_SHA256'] = hashlib.sha256(raw).hexdigest()

    def test_exact_projection_and_no_mta_network(self):
        with patch('common.api_gateway_utils.requests.request', side_effect=AssertionError('network')):
            result = ALL_PERMISSIONS.get_combined_permissions(withIds=True)
        self.assertEqual(result[0]['product_permission'], [
            dict(id=i, product_hierarchy_1='Mixed ', product_hierarchy_2=None,
                 product_hierarchy_3='é') for i in (7, 4)])
        self.assertEqual(result[0]['location_permission'], [
            dict(id=i, location_heirarchy_1='Mixed ', location_heirarchy_2=None,
                 location_heirarchy_3='é') for i in (7, 4)])
        self.assertEqual(result[0]['product_permission_ids'], result[0]['product_permission'])

    def test_live_grant_addition_and_revocation(self):
        catalogue = ALL_PERMISSIONS.get_combined_permissions()
        def grants():
            return ALL_PERMISSIONS.generateProductAndLocationPermissions(81, catalogue, 'product')
        self.assertEqual(grants(), [])
        grant = User_Application_Product_Permission.objects.create(
            user_id=81, application_id=2, productfilter_id=4)
        self.assertEqual([r['id'] for r in grants()[0]['permissions']], [4])
        grant.delete()
        self.assertEqual(grants(), [])

    def test_local_assembly_failure_is_not_empty_success(self):
        ApplicationMaster.objects.all().delete()
        with self.assertRaises(CatalogueUnavailable):
            ALL_PERMISSIONS.get_combined_permissions()

    def test_login_and_profile_assembly_do_not_call_mta(self):
        user = User.objects.create(email='reader@fixture.invalid', name='Reader', tc=True)
        User_Application_Product_Permission.objects.create(
            user_id=user.pk, application_id=2, productfilter_id=4)
        with patch('common.api_gateway_utils.requests.request', side_effect=AssertionError('network')):
            login = ResponseUser(user=UserProfileSerializer(user).data, url_permission=True).response('Login successful')
            profile = ResponseProfile(user=user).response()
        self.assertEqual(login['roles']['product_permission'][0]['permissions'][0]['id'], 4)
        self.assertEqual(profile['user']['id'], user.pk)

    def test_missing_and_tampered_fail_closed_not_empty_success(self):
        path = Path(os.environ['VF_MTA_PERMISSIONS_FILE'])
        path.write_text('{}')
        with self.assertRaises(CatalogueUnavailable):
            ALL_PERMISSIONS.get_combined_permissions()
        path.unlink()
        with self.assertRaises(CatalogueUnavailable):
            validate_configured()

    def test_wrong_publication_rejected(self):
        for run in ('other', ''):
            os.environ['VF_MTA_PUBLISHED_RUN'] = run
            with self.assertRaises(CatalogueUnavailable):
                validate_configured()

    def test_fixture_same_projection_and_manifest_binding(self):
        expected = payload()
        self.catalogue.update(version='legacy-ui-fixture-permissions-v1', manifest_sha256='manifest')
        self.install('VF_MTA_PERMISSIONS', self.catalogue)
        fixture = dict(version='legacy-ui-fixture-v1', manifest_sha256='manifest',
            permissions_sha256=os.environ['VF_MTA_PERMISSIONS_SHA256'],
            run_id='fixture', consumer_publication=dict(run_id='fixture'))
        self.install('VF_MTA_FIXTURE', fixture)
        os.environ['VF_MTA_PUBLISHED_RUN'] = os.environ['VF_MTA_PUBLISHED_DIGEST'] = ''
        os.environ['VF_MTA_HIERARCHY_FILE'] = os.environ['VF_MTA_HIERARCHY_SHA256'] = ''
        self.assertEqual(payload(), expected)
        os.environ['VF_MTA_HIERARCHY_SHA256'] = 'mixed'
        with self.assertRaises(CatalogueUnavailable):
            payload()
        os.environ['VF_MTA_HIERARCHY_SHA256'] = ''
        fixture['manifest_sha256'] = 'other'
        self.install('VF_MTA_FIXTURE', fixture)
        with self.assertRaises(CatalogueUnavailable):
            payload()

    def test_wrong_version_and_duplicate_id_rejected(self):
        self.catalogue['version'] = 'legacy-ui-fixture-permissions-v1'
        self.install('VF_MTA_PERMISSIONS', self.catalogue)
        with self.assertRaises(CatalogueUnavailable):
            payload()

        self.catalogue['version'] = 'block1-permissions-v1'
        self.catalogue['products']['records'][1]['id'] = 7
        self.install('VF_MTA_PERMISSIONS', self.catalogue)
        self.binding['catalogue_sha256'] = os.environ['VF_MTA_PERMISSIONS_SHA256']
        self.install('VF_MTA_HIERARCHY', self.binding)
        with self.assertRaises(CatalogueUnavailable):
            payload()

    def test_dangling_fixture_selector_rejected(self):
        os.environ['VF_MTA_FIXTURE_SHA256'] = 'dangling'
        with self.assertRaises(CatalogueUnavailable):
            validate_configured()

    def test_nonlocal_deployment_retains_http_branch(self):
        os.environ['VF_MTA_LOCAL_PERMISSIONS'] = '0'
        with patch('common.api_gateway_utils.service_map', {
                'mta': dict(active=True, application_id=2, base_url='http://mta'),
                'mto': dict(active=False)}), patch('common.api_gateway_utils.requests.request') as request:
            request.return_value.json.return_value = payload()
            self.assertEqual(len(ALL_PERMISSIONS.get_combined_permissions()), 1)
            request.assert_called_once_with(method='GET', url='http://mta/api/mta/GetAllPermmision')
