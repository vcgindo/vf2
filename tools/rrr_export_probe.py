"""Read-only candidate export receipt; run in the owned bounded worker."""
import base64
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from mta.presentation.context import selected_run
from mta.presentation.rrr_sql import read_rrr
from mta.presentation.rrr_export import FIELDS,selected_headers


def typed(value):
    kind = ('null' if value is None else 'bool' if isinstance(value,bool) else
            'decimal' if isinstance(value,Decimal) else 'int' if isinstance(value,int) else
            'float' if isinstance(value,float) else 'str')
    return dict(type=kind,value=str(value) if kind in ('decimal','float') else value)


roster=json.loads(Path(sys.argv[1]).read_text())['cases']
run=selected_run()
assert str(run.pk)=='ac1612c8-0e49-4155-83c3-f59f41422293'
client=Client()
observations=[]
with connection.cursor() as cursor: cursor.execute("SET statement_timeout='10s'")
with patch('mta.presentation.context.read_outputs',side_effect=AssertionError('whole-run reconstruction forbidden')):
    for case in roster:
        with patch('mta.presentation.ui_state.get_layout',return_value=case['layout']) as layout, CaptureQueriesContext(connection) as queries:
            response=client.post('/api/mta/GetExportDataAsync',json.dumps(case['payload']),content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY='{"id":"rrr-export-proof"}')
            assert response.status_code==200,(case['id'],response.content)
            body=b''.join(response.streaming_content)
            layout.assert_called_once_with('rrr-export-proof','RRR')
        assert all(not q['sql'].lstrip().upper().startswith(('INSERT','UPDATE','DELETE','CREATE','DROP','ALTER')) for q in queries)
        rows=read_rrr(run,case['payload'],paging=None)
        headers=selected_headers(case['layout'],FIELDS)
        observations.append(dict(id=case['id'],rows=[{k:typed(v) for k,v in row.items()} for row in rows],
            headers=headers,base64=base64.b64encode(body).decode(),sha256=hashlib.sha256(body).hexdigest(),
            status=response.status_code,content_type=response['Content-Type'],disposition=response['Content-Disposition']))
assert client.post('/api/mta/GetExportDataAsync','{}',content_type='application/json').status_code==403
print(json.dumps(dict(status='EXPORT_READBACK_REQUIRES_ORACLE_COMPARISON',run=str(run.pk),date=str(run.business_date),
    output_digest=run.output_digest,production_digest=run.production_digest,persistent_writes=False,
    layout_qualification='Request-level layout variants supplied to reader; no saved-user state changed. Real layout lookup checked at gateway separately.',
    observations=observations)))
