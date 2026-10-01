"""Read-only affected-contract comparison using the retained 44-case receipts.

Run in an owned bounded worker with repository/evidence mounts read-only.
No legacy replay, state write, fixture generation or replacement baseline.
"""
import gzip
import hashlib
import json
import os
import time
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from mta.presentation.context import selected_run

parent = Path('/evidence/f3-rrr-filters-modern-001')
assert hashlib.sha256((parent/'receipt.json').read_bytes()).hexdigest() == 'f96cc963afce16ce3342ab49b7448ecea047159e71efe745bf81b568049c0dff'
cases = json.loads((parent/'cases.json').read_text())['cases']
if os.environ.get('RRR_SELECTIVE_PLAN')=='1': cases=cases[:1]
if os.environ.get('RRR_SELECTIVE_INTEGRITY')=='1': cases=[]
client = Client()
results = []
run = selected_run()
assert str(run.pk)=='ac1612c8-0e49-4155-83c3-f59f41422293'
with connection.cursor() as cursor:
    cursor.execute("SET statement_timeout='10s'")
with patch('mta.runtime.services.read_outputs',side_effect=AssertionError('whole output read forbidden')), \
     patch('mta.runtime.relational_state.read_daily',side_effect=AssertionError('whole daily read forbidden')), \
     patch('mta.presentation.context.read_outputs',side_effect=AssertionError('whole context read forbidden')):
    for index, case in enumerate(cases):
        for route in ('RRRData','RRRDataCount'):
            started=time.monotonic()
            with CaptureQueriesContext(connection) as queries:
                response=client.post('/api/mta/'+route,json.dumps(case['payload']),content_type='application/json',
                    HTTP_X_VECTORFLOW_IDENTITY='{"id":"selective-evidence","name":"private-contract-probe"}')
            retained=json.loads(gzip.decompress((parent/f'response-{index:02}-{route}.json.gz').read_bytes()))
            # The old response archive stores status + envelope; inspect explicitly.
            expected=retained['response']
            actual=response.json()
            # JSON equality must distinguish true/1 and integer/float wire types.
            if json.dumps(actual,sort_keys=True,separators=(',',':')) != json.dumps(expected,sort_keys=True,separators=(',',':')):
                differences=[]
                if isinstance(actual.get('data'),list) and isinstance(expected.get('data'),list):
                    for a,b in zip(actual['data'],expected['data']):
                        differences.extend((k,a.get(k),b.get(k)) for k in set(a)|set(b) if a.get(k)!=b.get(k))
                raise AssertionError((case['id'],route,response.status_code,'response mismatch',differences[:4]))
            assert response.status_code==retained['status']
            assert all(not q['sql'].lstrip().upper().startswith(('INSERT','UPDATE','DELETE','CREATE','DROP','ALTER')) for q in queries)
            results.append(dict(case=case['id'],route=route,status=response.status_code,
                seconds=round(time.monotonic()-started,4),queries=len(queries),
                body_sha256=hashlib.sha256(response.content).hexdigest()))
            if os.environ.get('RRR_SELECTIVE_PLAN')=='1':
                with connection.cursor() as cursor:
                    cursor.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+queries[-1]['sql'])
                    results[-1]['query_plan']=cursor.fetchone()[0]
    for route in ('GetLastRunDate','LocationType'):
        started=time.monotonic()
        with CaptureQueriesContext(connection) as queries:
            response=client.get('/api/mta/'+route,HTTP_X_VECTORFLOW_IDENTITY='{"id":"selective-evidence"}')
        assert response.status_code==200
        results.append(dict(route=route,status=200,seconds=round(time.monotonic()-started,4),queries=len(queries)))
integrity=None
if os.environ.get('RRR_SELECTIVE_INTEGRITY')=='1':
    from mta.runtime.services import read_outputs
    from mta.serialization import digest
    started=time.monotonic()
    output=read_outputs(run)
    assert digest(output)==run.production_digest
    integrity=dict(status='FULL_INPUT_ROSTER_OPERATIONAL_CHECKSUM_PASS',
        seconds=round(time.monotonic()-started,3),images=len(run.production_manifest['images']),
        qualification='Explicit integrity verification only, not an ordinary request.')
print(json.dumps(dict(status='SELECTIVE_AFFECTED_CONTRACTS_PASS_NOT_BROWSER_ACCEPTANCE',run=str(run.pk),integrity=integrity,
    date=str(run.business_date),output_digest=run.output_digest,production_digest=run.production_digest,
    parent_receipt_sha256='f96cc963afce16ce3342ab49b7448ecea047159e71efe745bf81b568049c0dff',
    whole_run_reconstruction_forbidden=True,persistent_writes=False,observations=results)))
