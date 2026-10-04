"""Bounded PostgreSQL readback/immutability proof for prepared Planning normal-grid occurrences."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.core.management import call_command
from django.db import connection, transaction, DatabaseError
from mta.presentation import fixture
from mta.presentation.planning_custom_preparation import custom_occurrences
from mta.presentation.planning_custom import admitted_custom
from mta.runtime.management.commands.prepare_planning_custom import MODELS, fields_for
from mta.runtime.planning_custom_schema import verify_guards
from mta.runtime.models import PlanningCustomProjection
from mta.runtime.relational_state import quote


def verify():
    run, before = fixture.binding()
    verify_guards(connection)
    admitted = admitted_custom(run)
    result = {}
    with connection.cursor() as cursor:
        for name, model in MODELS:
            query, params = custom_occurrences(run, name)
            columns = ','.join(map(quote, [f for f in fields_for(model) if f != "ordinal"]))
            stored = 'SELECT ' + columns + ' FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s'
            derived = 'SELECT ' + columns + ' FROM (' + query + ') source'
            cursor.execute('SELECT count(*) FROM ((' + stored + ') EXCEPT ALL (' + derived + ')) missing',
                           [run.pk, *params])
            missing = cursor.fetchone()[0]
            cursor.execute('SELECT count(*) FROM ((' + derived + ') EXCEPT ALL (' + stored + ')) extra',
                           [*params, run.pk])
            extra = cursor.fetchone()[0]
            assert (missing, extra) == (0, 0), (name, missing, extra)
            relation, relation_params = admitted[name]
            cursor.execute('SELECT count(*) FROM (' + relation + ') admitted', relation_params)
            count = cursor.fetchone()[0]
            assert count == getattr(PlanningCustomProjection.objects.get(run=run),
                                    name.split('_')[0] + '_count')
            result[name] = dict(missing=missing, extra=extra, admitted_count=count)
    # Rollback even if a guard is broken: these tests can never persist a mutation.
    guarded = []
    for model in [item[1] for item in MODELS] + [PlanningCustomProjection]:
        table = 'mta.' + quote(model._meta.db_table)
        columns = ','.join(quote(field.column) for field in model._meta.local_fields
                           if field.name != 'id')
        for build_enabled, expected in ((False, 'Planning custom preparation required'),
                                        (True, 'Planning custom receipt already sealed')):
            denied = False
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT set_config('fresh.planning_custom_build',%s,true)",
                                       [str(run.pk) if build_enabled else ''])
                        cursor.execute('INSERT INTO ' + table + ' (' + columns + ') SELECT '
                                       + columns + ' FROM ' + table + ' WHERE run_id=%s LIMIT 1', [run.pk])
                    transaction.set_rollback(True)
            except DatabaseError as exc:
                denied = expected in str(exc)
            assert denied, 'Missing insert guard: ' + model.__name__
            guarded.append(model.__name__ + ':INSERT:' + str(build_enabled))
        for sql in ('UPDATE ' + table + ' SET run_id=run_id WHERE run_id=%s',
                    'DELETE FROM ' + table + ' WHERE run_id=%s',
                    'TRUNCATE ' + table):
            denied = False
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(sql, [] if sql.startswith('TRUNCATE') else [run.pk])
                    transaction.set_rollback(True)
            except DatabaseError as exc:
                denied = 'Planning custom rows and receipts are immutable' in str(exc)
            assert denied, 'Missing immutable guard: ' + sql
            guarded.append(model.__name__ + ':' + sql.split()[0])
    call_command('prepare_planning_custom', verify_only=True)
    assert fixture.binding()[1] == before
    print(json.dumps(dict(status='PASS', values=result, guarded=guarded,
                          source_digest=before), sort_keys=True))


if __name__ == '__main__':
    verify()
