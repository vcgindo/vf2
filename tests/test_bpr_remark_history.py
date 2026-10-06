"""Read-only terminal history envelope and admission guards."""
import inspect
import json
import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-test-only-not-a-serving-secret')
import django
django.setup()
from django.test import Client, override_settings
from mta.presentation.context import PublicationUnavailable


class BprRemarkHistoryTests(unittest.TestCase):
    def test_fixture_remarks_select_native_pair_date_order_and_scope(self):
        from mta.presentation.views import bpr_remark_history
        rows = [dict(SKUCode='A', WhCode='X', Remark='first', Username=None,
                     RemarkDate=datetime(2026, 5, 4, 12, 44, 24)),
                dict(SKUCode='A', WhCode='X', Remark='second', Username='fixture',
                     RemarkDate=datetime(2026, 5, 7, 16, 19, 57)),
                dict(SKUCode='B', WhCode='X', Remark='outside', Username=None, RemarkDate=None)]
        payload = dict(skucode='a ', whcode='x')
        with patch('mta.presentation.views.selected_run', return_value=SimpleNamespace(kind='LEGACY_UI_FIXTURE')), \
             patch('mta.presentation.fixture.bpr_ancillary', return_value={'BPRReport_RemarkDetails': rows}), \
             patch('mta.presentation.selective.image_rows', return_value=[]), \
             patch('mta.presentation.views.scope', return_value=({'A'}, {'X'})) as scope:
            response = inspect.unwrap(bpr_remark_history)(None, payload)
            self.assertEqual(json.loads(response.content)['data'], [
                dict(r='second', rd='2026-05-07T16:19:57', un='fixture'),
                dict(r='first', rd='2026-05-04T12:44:24')])
            scope.return_value = ({'B'}, {'X'})
            self.assertEqual(json.loads(inspect.unwrap(bpr_remark_history)(None, payload).content)['data'], [])

    def test_empty_history_and_guards(self):
        client = Client()
        payload = dict(skucode='337', whcode='AG515802', forwardUsers=True)
        def read(identity=True):
            return client.post('/api/mta/GetRemarkDetails', data=payload,
                content_type='application/json', **({'HTTP_X_VECTORFLOW_IDENTITY': '{"id":"1"}'} if identity else {}))
        self.assertEqual(read(False).status_code, 403)
        with patch('mta.presentation.views.selected_run', return_value=object()), \
                patch('mta.presentation.terminal_supplement.terminal_ancillary') as ancillary:
            ancillary.return_value = {'BPRReport_RemarkDetails': []}
            response = read()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content)['data'], [])
            ancillary.return_value = {'BPRReport_RemarkDetails': [{'Remark': 'unsupported'}]}
            self.assertEqual(read().status_code, 503)
            ancillary.side_effect = PublicationUnavailable('terminal_ancillary_supplement_scope_mismatch')
            self.assertEqual(read().status_code, 503)

    @override_settings(VF_MTA_DAILY_PUBLICATION=True)
    def test_daily_history_formats_captured_timestamp_as_native_naive_wall_time(self):
        from mta.presentation.views import bpr_remark_history
        rows = [dict(SKUCode='A', WhCode='X', Remark='daily', Username='user',
                     RemarkDate='2026-10-06T08:09:10.123000+00:00')]
        with patch('mta.presentation.views.selected_run',
                   return_value=SimpleNamespace(kind='DAILY_CHAIN')), \
                patch('mta.presentation.ancillary_live.image_rows', return_value=rows), \
                patch('mta.presentation.selective.image_rows', return_value=[]), \
                patch('mta.presentation.views.scope', return_value=({'A'}, {'X'})):
            response = inspect.unwrap(bpr_remark_history)(None, dict(skucode='a', whcode='x'))
        self.assertEqual(json.loads(response.content)['data'], [
            dict(r='daily', rd='2026-10-06T08:09:10.123', un='user')])
