"""Attribute one full BTR request without changing its query or response contract."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
    import django
    django.setup()
    from django.db import connection
    from django.test import Client
    from mta.presentation import admission, fixture, btr_sql, views
    admission.admit()
    actor = next(a for a in fixture.policy()['actors'] if 'broad' in a['email'])
    client = Client()
    observations = []
    payload = dict(name='both', filters={'horizonFilter': {'filters': []}},
                   paginationParameter=dict(pageNumber=1, recordsPerPage=5000),
                   product_permissions=actor['products'], location_permissions=actor['locations'])
    target = Path(sys.argv[1])
    if target.exists():
        raise ValueError('Preserve existing attribution evidence')
    for route in ('GetBTRDataCount', 'GetBTRData'):
        queries = []
        phases = {}
        def timed(name, function):
            def invoke(*args, **kwargs):
                started = time.monotonic()
                try:
                    return function(*args, **kwargs)
                finally:
                    phases[name] = phases.get(name, 0) + time.monotonic() - started
            return invoke
        def measured(execute, sql, params, many, context):
            started = time.monotonic()
            try:
                return execute(sql, params, many, context)
            finally:
                queries.append(dict(seconds=time.monotonic()-started, sql=sql))
        started = time.monotonic()
        with connection.execute_wrapper(measured), \
             patch.object(btr_sql, 'read_btr', timed('reader_seconds', btr_sql.read_btr)), \
             patch.object(views, 'envelope', timed('envelope_serialization_seconds', views.envelope)):
            response = client.post('/api/mta/' + route, payload, content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY=json.dumps(dict(id=actor['id'], email=actor['email'])))
        seconds = time.monotonic()-started
        assert response.status_code == 200, (route, response.status_code)
        decoded = json.loads(response.content)
        assert decoded['status'] == 200
        if route.endswith('Count'):
            assert decoded['data'] == dict(TechCount='97299', EcoCount='97299')
        else:
            assert all(len(decoded['data'][branch]) == 5000 for branch in ('tech', 'eco'))
        observations.append(dict(route=route, total_seconds=seconds, sql_execute_seconds=sum(q['seconds'] for q in queries),
            query_count=len(queries), bytes=len(response.content), sha256=hashlib.sha256(response.content).hexdigest(),
            queries=queries, phases=phases))
    target.write_text(json.dumps(dict(observations=observations,
        limitation='SQL execute time excludes fetch/serialization; in-process request excludes gateway/network/browser'), indent=2))


if __name__ == '__main__':
    main()
