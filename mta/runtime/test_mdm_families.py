"""Changed shared routes and owned drafts for the two new MDM families."""
import json
from importlib import import_module
from unittest.mock import patch

from django.test import TestCase
from mta.mdm import drafts, families
from mta.presentation.context import PublicationUnavailable
from mta.runtime.mdm_models import MdmSource, MdmFamilySource, MdmDraftMaster


class FamilyIntegrationTests(TestCase):
    def setUp(self):
        self.source = MdmSource.objects.create(digest='f' * 64, dll_digest='d' * 64,
                                               database_name='owned-test', receipt={})
        self.actor = {'id': 3, 'name': 'Requester'}
        self.other = {'id': 2, 'name': 'Other actor'}
        for master_id in (2, 3):
            digest = import_module('mta.mdm.' + families.NAMES[master_id] + '_source').SOURCE_DIGEST
            MdmFamilySource.objects.create(source=self.source, master_id=master_id,
                                           digest=digest, receipt={})

    def test_family_drafts_reopen_modify_append_and_ownership(self):
        for master_id, row in ((2, {'wc': "L'1", 'wd': 'Location', 'LL1': None}),
                               (3, {'sc': 'SKU1', 'wc': 'L1', 'mn': 'not a number'})):
            with self.subTest(master=master_id):
                payload = {'draftId': '', 'actionType': 2, 'instanceName': 'Family draft',
                    'searchKey': '', 'draftData': [{'masterId': master_id, 'gridState': '{}',
                        'status': 'Invalid', 'dataMaster': [row]}]}
                identifier = drafts.write(self.source, payload, self.actor)['data']
                actual = drafts.details(self.source, identifier, self.actor,
                                        {'pageNumber': 1, 'recordsPerPage': 100})
                self.assertEqual(actual[0]['MasterId'], master_id)
                self.assertEqual(actual[0]['DataMaster'][0]['wc'], 'L"1' if master_id == 2 else 'L1')
                if master_id == 3:
                    self.assertEqual(actual[0]['DataMaster'][0]['mn'], 'not a number')
                for operation in (lambda: drafts.count(self.source, identifier, self.other),
                                  lambda: drafts.details(self.source, identifier, self.other,
                                      {'pageNumber': 1, 'recordsPerPage': 100})):
                    with self.assertRaises(drafts.DraftDenied):
                        operation()
                payload['draftId'] = identifier
                with self.assertRaises(drafts.DraftDenied):
                    drafts.write(self.source, payload, self.other)
                drafts.write(self.source, payload, self.actor)
                self.assertEqual(json.loads(drafts.count(self.source, identifier, self.actor)),
                                 [{'masterid': master_id, 'recordCount': 2}])
                drafts.write(self.source, payload, self.actor, modify=True)
                self.assertEqual(json.loads(drafts.count(self.source, identifier, self.actor))[0]['recordCount'], 1)
                drafts.delete(self.source, identifier, self.actor)
                self.assertFalse(MdmDraftMaster.objects.filter(source=self.source, DraftId=identifier).exists())

    def test_uninstalled_family_is_not_implicitly_empty(self):
        MdmFamilySource.objects.filter(source=self.source, master_id=3).delete()
        with self.assertRaises(PublicationUnavailable):
            families.require_installed(self.source, 3)
        self.assertEqual(families.installed_ids(self.source), [1, 2])

    def test_native_direct_body_and_family_configuration_dispatch(self):
        payload = {'draftId': '', 'actionType': 2, 'instanceName': 'Location', 'searchKey': '',
            'draftData': [{'masterId': 2, 'gridState': '{}', 'status': 'Valid',
                           'dataMaster': [{'wc': 'L1', 'wd': 'Location'}]}]}
        identifier = drafts.write(self.source, payload, self.actor)['data']
        with patch('mta.presentation.mdm_views.source', return_value=self.source), \
                patch('mta.presentation.fixture.enabled', return_value=False):
            config = self.client.post('/api/mta/GetMasterUIConfiguration',
                {'screenType': 'modify'}, content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY=json.dumps(self.actor))
            response = self.client.post('/api/mta/draft/' + identifier,
                {'pageNumber': 1, 'recordsPerPage': 100}, content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY=json.dumps(self.actor))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'][0]['MasterId'], 2)
        self.assertEqual(config.status_code, 200)
        self.assertEqual([row['id'] for row in config.json()['data']], ['1', '2', '3'])
