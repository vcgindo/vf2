"""Private HTTP readback on native production rows; no state/action writes."""
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from django.test import Client

with connection.cursor() as cursor:
    cursor.execute('SET default_transaction_read_only=on')
client = Client()
observed = []
for case in json.loads(Path(sys.argv[1]).read_text())['cases']:
    result = dict(id=case['id'])
    for route in ('GetBPRDataCount', 'GetBPRData'):
        response = client.post('/api/mta/'+route,json.dumps(case['payload']),content_type='application/json',
            HTTP_X_VECTORFLOW_IDENTITY='{"id":"bpr-wire-proof"}')
        assert response.status_code == 200, (route,response.status_code,response.content[:250])
        result[route] = response.json()
    observed.append(result)
print(json.dumps(observed))
