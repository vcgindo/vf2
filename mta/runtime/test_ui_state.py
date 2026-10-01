import json
from unittest.mock import patch
from django.test import TestCase
from mta.presentation.ui_state import dbm_columns, get_layout, save_layout
from mta.runtime.models import UserReportLayout


class UserLayoutTest(TestCase):
    def request(self, action, payload, user='preview-layout-test-A'):
        headers = {} if user is None else {'HTTP_X_VECTORFLOW_IDENTITY': json.dumps({'id': user})}
        return self.client.post('/api/mta/'+action, json.dumps(payload), content_type='application/json', **headers)

    def test_configuration_matches_visible_column_contract(self):
        rows = dbm_columns()
        self.assertEqual(len(rows), 16)
        self.assertTrue(all(row['Visible'] and 'TagID' not in row for row in rows))
        self.assertEqual({r['Col_Code'] for r in rows if r['DataType']=='Number'}, {'OldNormValue','NewNormValue'})

    def test_sequential_save_replace_get_reset_and_other_user(self):
        payload = {'reportname':'DBM','state':'{"columns":[],"charts":[],"pivot":false}'}
        self.assertEqual(self.request('GetState',payload).json()['data'],'')
        self.assertEqual(self.request('SaveState',payload).json()['data'],'1')
        self.assertEqual(self.request('GetState',payload).json()['data'],payload['state'])
        self.assertEqual(self.request('GetState',payload,user='preview-layout-test-B').json()['data'],'')
        self.assertEqual(self.request('SaveState',payload).json()['data'],'2')
        self.assertEqual(UserReportLayout.objects.count(),1)
        self.assertEqual(self.request('ResetState',payload).json()['data'],'1')
        self.assertEqual(self.request('ResetState',payload).json()['data'],'0')
        self.assertEqual(self.request('GetState',payload).json()['data'],'')

    def test_unauthorized_and_forged_body_cannot_select_another_user(self):
        save_layout('preview-layout-test-B','DBM','private-layout')
        payload={'reportname':'DBM','state':'ours','user':{'id':'preview-layout-test-B'}}
        for action in ('GetState','SaveState','ResetState'):
            self.assertEqual(self.request(action,payload,user=None).status_code,403)
        self.assertEqual(self.request('GetState',payload).json()['data'],'')
        self.assertEqual(self.request('SaveState',payload).json()['data'],'1')
        self.assertEqual(self.request('ResetState',payload).json()['data'],'1')
        self.assertEqual(get_layout('preview-layout-test-B','DBM'),'private-layout')

    def test_failed_replacement_rolls_back_delete(self):
        save_layout('preview-layout-test-A','DBM','retained')
        with patch('mta.presentation.ui_state.UserReportLayout.objects.create',side_effect=RuntimeError('injected')):
            with self.assertRaisesMessage(RuntimeError,'injected'):
                save_layout('preview-layout-test-A','DBM','replacement')
        self.assertEqual(get_layout('preview-layout-test-A','DBM'),'retained')

    def test_source_empty_scalar_is_null_not_missing_row(self):
        for value in ('',None):
            UserReportLayout.objects.all().delete()
            UserReportLayout.objects.create(username='preview-layout-test-A',reportname='DBM',state=value)
            self.assertIsNone(self.request('GetState',{'reportname':'DBM'}).json()['data'])

    def test_legacy_ambiguous_and_quoted_paths_are_not_repaired(self):
        for state in ('one','two'):
            UserReportLayout.objects.create(username='preview-layout-test-A',reportname='DBM',state=state)
        self.assertEqual(self.request('GetState',{'reportname':'DBM'}).status_code,503)
        self.assertEqual(self.request('SaveState',{'reportname':'DBM','state':"user's layout"}).status_code,503)
        self.assertEqual(UserReportLayout.objects.count(),2)
