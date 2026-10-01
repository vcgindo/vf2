"""Read-only BTR CSV candidate; paired with independent deployed SQL outside it."""
import base64
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.db import connection
from django.test import Client
from mta.presentation.context import selected_run
from mta.presentation.btr_sql import read_btr
from mta.presentation.btr_export import selected_headers


def typed(value):
    kind = ('null' if value is None else 'bool' if isinstance(value, bool) else
            'decimal' if isinstance(value, Decimal) else 'int' if isinstance(value, int) else
            'float' if isinstance(value, float) else 'str')
    return dict(type=kind, value=str(value) if kind in ('decimal', 'float') else value)

cases = json.loads(Path(sys.argv[1]).read_text())['cases']
run = selected_run()
assert str(run.pk) == 'ac1612c8-0e49-4155-83c3-f59f41422293'
with connection.cursor() as cursor:
    cursor.execute('SET default_transaction_read_only=on')
    cursor.execute('SET statement_timeout=45000')
client, observations = Client(), []
with patch('mta.presentation.views.publication', side_effect=AssertionError('no whole-run read')):
    for case in cases:
        with patch('mta.presentation.ui_state.get_layout', return_value=case['layout']) as layout:
            response = client.post('/api/mta/GetExportDataAsync', case['payload'], content_type='application/json',
                                   HTTP_X_VECTORFLOW_IDENTITY='{"id":"btr-export-proof"}')
            if response.status_code != 200:
                observations.append(dict(id=case['id'], status=response.status_code, body=response.json()))
                continue
            body = b''.join(response.streaming_content)
            layout.assert_called_once_with('btr-export-proof', 'BTRon-hand' if case['payload']['name'] == 'tech' else 'BTRpipeline')
        rows, dates = read_btr(run, case['payload'], paging=None, export=True)
        observations.append(dict(id=case['id'], status=200, rows=[{k: typed(v) for k, v in row.items()} for row in rows],
                                 headers=selected_headers(case['layout'], dates),
                                 base64=base64.b64encode(body).decode(), sha256=hashlib.sha256(body).hexdigest()))
print(json.dumps(dict(run=str(run.pk), output_digest=run.output_digest, observations=observations, writes=False)))
