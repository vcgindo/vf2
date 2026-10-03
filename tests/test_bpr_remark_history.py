"""Read-only terminal history envelope and admission guards."""
import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-test-only-not-a-serving-secret')
import django
django.setup()
from django.test import Client
from mta.presentation.context import PublicationUnavailable


class BprRemarkHistoryTests(unittest.TestCase):
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
