"""Read-only Planning Excess route observations in an isolated worker."""
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from mta.presentation.admission import admit
from mta.presentation.context import selected_run

settings.DATABASES['default']['OPTIONS']['options'] += ' -c default_transaction_read_only=on -c statement_timeout=45000'
admission = admit()
run = selected_run()
result = dict(run=str(run.pk), output_digest=run.output_digest, admission=admission, observations=[])
client = Client()
with patch('mta.presentation.views.publication', side_effect=AssertionError('whole publication forbidden')):
    for case in json.loads(Path(sys.argv[1]).read_text())['cases']:
        start = time.monotonic()
        with CaptureQueriesContext(connection) as queries:
            response = client.post('/api/mta/' + case['route'], data=case['payload'],
                content_type='application/json', HTTP_X_VECTORFLOW_IDENTITY='{"id":"1"}')
        result['observations'].append(dict(id=case['id'], status=response.status_code, body=response.json(),
            seconds=time.monotonic()-start, query_count=len(queries)))
print(json.dumps(result))
