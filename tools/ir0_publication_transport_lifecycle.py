"""Run only in the uniquely owned empty IR0 transport PG database.

Uses real Django WSGI lifecycle, signals, transactions and concurrent PostgreSQL.
The small identity fixture isolates transport; this is not publication acceptance.
Connection inputs are ordinary PG* environment variables; credentials never print.
"""
import json
import os
from io import BytesIO
from unittest.mock import patch
from wsgiref.util import setup_testing_defaults

if os.environ.get('PGDATABASE') != 'vftest_fresh_ir0_transport_20261103':
    raise SystemExit('Exact uniquely owned IR0 transport database required')

from django.conf import settings
settings.configure(SECRET_KEY='isolated-ir0-transport-fixture', DEBUG=False,
    ALLOWED_HOSTS=['testserver', 'localhost'], ROOT_URLCONF=__name__,
    INSTALLED_APPS=['mta.runtime'],
    MIDDLEWARE=['django.middleware.security.SecurityMiddleware',
                'mta.presentation.publication_binding.PublicationBindingMiddleware'],
    DATABASES={'default': {'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['PGDATABASE'], 'HOST': os.environ['PGHOST'],
        'PORT': os.environ.get('PGPORT', '5432'), 'USER': os.environ['PGUSER'],
        'PASSWORD': os.environ['PGPASSWORD'], 'CONN_MAX_AGE': 60}},
    VF_MTA_NATIVE_PUBLICATION=True, VF_MTA_PHASE_SELECTION_FILE='',
    MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity', USE_TZ=True)
import django
django.setup()
import psycopg
from django.core.handlers.wsgi import WSGIHandler
from django.core.signals import request_started, request_finished
from django.db import connection
from django.http import JsonResponse, StreamingHttpResponse
from django.urls import path
from mta.presentation import admission, publication_binding as binding
from mta.presentation.request_scope import in_read_request
from mta.serialization import digest


def generation():
    with connection.cursor() as cursor:
        cursor.execute('SELECT generation FROM public.ir0_transport_sample WHERE id=1')
        return cursor.fetchone()[0]


def update(value):
    with psycopg.connect(host=os.environ['PGHOST'], port=os.environ.get('PGPORT', '5432'),
            dbname=os.environ['PGDATABASE'], user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD']) as separate:
        separate.execute('UPDATE public.ir0_transport_sample SET generation=%s WHERE id=1', (value,))


def report(request):
    assert connection.in_atomic_block and in_read_request()
    with connection.cursor() as cursor:
        cursor.execute('SHOW transaction_isolation')
        assert cursor.fetchone()[0] == 'repeatable read'
        cursor.execute('SHOW transaction_read_only')
        assert cursor.fetchone()[0] == 'on'
    return JsonResponse({'generation': generation()})


def export(request):
    def chunks():
        assert connection.in_atomic_block and in_read_request()
        yield str(generation()).encode() + b'\n'
        update(3)
        assert connection.in_atomic_block and in_read_request()
        yield str(generation()).encode() + b'\n'
    return StreamingHttpResponse(chunks(), content_type='text/csv')


urlpatterns = [path('api/mta/PublicationBinding', binding.bootstrap_view),
    path('api/mta/RRRDataCount', report), path('api/mta/RRRData', report),
    path('api/mta/GetExportDataAsync', export)]

signals = []
def observe_started(sender, **kwargs):
    assert not connection.in_atomic_block
    signals.append('started')

def observe_finished(sender, **kwargs):
    assert not connection.in_atomic_block
    assert not in_read_request()
    signals.append('finished')


def invoke(application, route, token=None, authenticated=True, disconnect=False):
    environ = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=route, REQUEST_METHOD='GET', SERVER_NAME='testserver',
        HTTP_HOST='testserver', **{'wsgi.input': BytesIO()})
    if authenticated:
        environ['HTTP_X_VECTORFLOW_IDENTITY'] = '{"id":7}'
        environ['HTTP_X_VECTORFLOW_REPORT_SCOPE'] = 'c' * 64
    if token is not None:
        environ[binding.ENVIRON_HEADER] = token
    captured = {}
    def start(status, headers, exc_info=None):
        captured.update(status=int(status.split()[0]), headers=dict(headers))
    response = application(environ, start)
    try:
        captured['body'] = b'' if disconnect else b''.join(response)
    finally:
        response.close()
    assert not connection.in_atomic_block and not in_read_request()
    return captured


def main():
    # Refuse a reused witness database; preserve any existing table for diagnosis.
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.ir0_transport_sample')")
        if cursor.fetchone()[0] is not None:
            raise SystemExit('Witness table already exists; preserve it, do not reset')
        cursor.execute('CREATE TABLE public.ir0_transport_sample (id integer PRIMARY KEY, generation integer NOT NULL)')
        cursor.execute('INSERT INTO public.ir0_transport_sample VALUES (1,1)')
    request_started.connect(observe_started, weak=False)
    request_finished.connect(observe_finished, weak=False)
    application = admission.AdmittedApplication.__new__(admission.AdmittedApplication)
    application.application = WSGIHandler()
    with patch.object(admission, 'require_admission', return_value='fixture-admission'), \
            patch('mta.presentation.installation_metadata.publication_configured', return_value=True), \
            patch.object(binding, 'identity', side_effect=lambda admitted: digest(dict(generation=generation()))):
        assert invoke(application, binding.BOOTSTRAP, authenticated=False)['status'] == 403
        first = invoke(application, binding.BOOTSTRAP)
        assert first['status'] == 200, first
        a = json.loads(first['body'])['binding']
        assert invoke(application, '/api/mta/RRRDataCount', a)['status'] == 200
        update(2)
        assert invoke(application, '/api/mta/RRRData', a)['status'] == 409
        b = json.loads(invoke(application, binding.BOOTSTRAP)['body'])['binding']
        assert a != b
        streamed = invoke(application, '/api/mta/GetExportDataAsync', b)
        assert streamed['status'] == 200 and streamed['body'] == b'2\n2\n', streamed
        assert invoke(application, '/api/mta/RRRData', b)['status'] == 409
        c = json.loads(invoke(application, binding.BOOTSTRAP)['body'])['binding']
        assert invoke(application, '/api/mta/GetExportDataAsync', c, disconnect=True)['status'] == 200
    assert signals.count('started') == signals.count('finished')
    print(json.dumps(dict(result='PASS', database=os.environ['PGDATABASE'],
        real_wsgi=True, real_pg=True, signal_pairs=signals.count('started'),
        bootstrap_auth=True, count_cutover_data_denied=True,
        lazy_export_snapshot='2/2 despite concurrent generation 3',
        disconnect_cleanup=True, identity='fixture only; native identity acceptance excluded')))


if __name__ == '__main__':
    main()
