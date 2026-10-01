"""Read-only selected PostgreSQL overview + actual Django endpoint responses."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from django.test import RequestFactory
from mta.presentation.planning_read import planning_overview_context
from mta.presentation.planning_overview import counts
from mta.presentation.context import scope
from mta.presentation.views import planning_overview

cases = json.loads(Path(sys.argv[1]).read_text())['cases']
with connection.cursor() as cursor:
    cursor.execute('SET default_transaction_read_only=on')
    cursor.execute("SET statement_timeout='15s'")
with patch('mta.presentation.context.read_outputs',side_effect=AssertionError('whole-publication reconstruction')):
    context = planning_overview_context()
observations = []
for case in cases:
    payload=case['payload']
    products,locations=scope(payload,attributes=context.attributes)
    values=counts(context.attributes,context.standards,context.reports,context.run.business_date,
        products=products,locations=locations)
    request=RequestFactory().post('/api/mta/GetPlanningDataCount',json.dumps(payload),content_type='application/json',
        HTTP_X_VECTORFLOW_IDENTITY='{"id":"planning-overview-proof"}')
    with patch('mta.presentation.planning_read.planning_overview_context',return_value=context):
        reply=planning_overview(request)
    assert reply.status_code==200, (case['id'],reply.status_code,reply.content[:300])
    wire=json.loads(reply.content)
    assert wire['data']==values
    observations.append(dict(id=case['id'],data=values,wire=wire))
print(json.dumps(dict(run_id=str(context.run.pk),output_digest=context.run.output_digest,
    observations=observations,report_counts={k:len(v) for k,v in context.reports.items()})))
