"""Run in an owned, port-free worker with PostgreSQL default_transaction_read_only.

Faults affect only values returned into this process, never database rows.
No engine, projection writer, action, layout or acceptance mutation is called.
"""
import json
import os
import resource
import statistics
import time
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from mta.presentation import admission
from mta.runtime import relational_state, services
from mta.runtime.models import PickProjection

# Django supplies libpq options explicitly for the schema search path, so add
# read-only there as well; PGOPTIONS alone is overridden by those options.
settings.DATABASES['default']['OPTIONS']['options'] += ' -c default_transaction_read_only=on'
with connection.cursor() as cursor:
    cursor.execute('SHOW default_transaction_read_only')
    assert cursor.fetchone()[0] == 'on'

results = []
def rejected(name, manager, expected):
    started = time.monotonic()
    with manager:
        try:
            admission.admit()
        except Exception as exc:
            assert expected in str(exc), (name, type(exc).__name__, str(exc))
            assert admission._admitted is None
            results.append(dict(case=name, rejected=True, error=str(exc),
                                seconds=round(time.monotonic()-started, 4)))
        else:
            raise AssertionError(name + ' was incorrectly admitted')

rejected('missing identity', override_settings(VF_MTA_PUBLISHED_RUN=''), 'explicit_publication')
rejected('wrong output digest', override_settings(VF_MTA_PUBLISHED_DIGEST='0'*64), 'identity_or_status')
original_input = services.read_input
def wrong_input(run):
    value = original_input(run)
    return {**value, 'isolated_integrity_fault': True}
rejected('input identity corruption', patch.object(services, 'read_input', wrong_input), 'Immutable input drift')

original_daily = relational_state.read_daily
def wrong_daily(run):
    output = original_daily(run)
    output['DBMFinal'][0]['isolated_integrity_fault'] = True
    return output
rejected('native output corruption', patch.object(relational_state, 'read_daily', wrong_daily),
         'Operational output checksum drift')

original_get = PickProjection.objects.get
def wrong_projection(*args, **kwargs):
    value = original_get(*args, **kwargs)
    value.rows_digest = '0'*64
    return value
rejected('projection integrity corruption', patch.object(PickProjection.objects, 'get', wrong_projection),
         'Pick projection typed values/multiplicity drift')
rejected('hierarchy identity corruption', override_settings(VF_MTA_HIERARCHY_SHA256='0'*64),
         'hierarchy_supplement_hash_mismatch')

started = time.monotonic()
identity = admission.admit()
startup_seconds = time.monotonic()-started
samples = []
with patch.object(services, 'read_outputs', side_effect=AssertionError('request attempted full read')):
    with CaptureQueriesContext(connection) as queries:
        for _ in range(30):
            started = time.monotonic()
            assert admission.require_admission() == identity['admission_digest']
            samples.append(time.monotonic()-started)
    sql = [q['sql'] for q in queries.captured_queries]
    assert not any('mta_state.' in q or 'fresh_mta_pickband' in q for q in sql)
    with override_settings(VF_MTA_TERMINAL_SHA256='0'*64):
        try: admission.require_admission()
        except admission.PublicationUnavailable as exc:
            assert 'restart_required' in str(exc)
        else: raise AssertionError('Changed configuration kept admission')
    assert admission._admitted is None
    try: admission.require_admission()
    except admission.PublicationUnavailable: pass
    else: raise AssertionError('Restoring configuration silently readmitted publication')

print(json.dumps(dict(status='PASS', identity=identity, rejection_cases=results,
    startup_seconds=round(startup_seconds, 4), guard_samples_seconds=samples,
    guard_median_seconds=statistics.median(samples), guard_max_seconds=max(samples),
    guard_queries_per_request=len(sql)/len(samples), guard_sql=sorted(set(sql)),
    process_peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
    read_only_database=True, no_engine_or_state_writes=True, config_drift_revokes_until_restart=True)))
