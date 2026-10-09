"""One bounded repair of Cohort6's unsealed, access-bound preparation metadata."""
import argparse
import hashlib
import json
from pathlib import Path

RUN = '71a5addc-dcb7-49ca-811d-6cd93886d4e5'
DATABASE = 'fresh_cohort6_20261009_001'
PRIOR = '5966067dbbc4037f58f722b4c16f98ad02ead9c0bc59ebeced82026aea1b3eee'
NATIVE = '5cc3659af6b12b183000844f73088ef3798dd75a3a379ed30b52677a20ad8f34'
OUTPUT = '7075127ea7fc6fa3d3d05f00bcb6e771eb1bf6401a811cbf2c97158e5976235b'
SOURCE = 'c121b63cb503afa7e4ecef7bd1dcbd408689a437e5016c035c5bd3b67ea4a6a2'
RECIPE = '3695c411a7f6252ae064e97940f35b2c2d2e14006c42c9fbfb26522bcbb0c149'


def guard_definition(cursor):
    cursor.execute("""SELECT p.prosrc,pg_get_functiondef(p.oid),p.prosecdef,
        p.proconfig,p.proowner,l.lanname FROM pg_proc p
        JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang
        WHERE n.nspname='mta' AND p.proname='guard_daily_ui_publication' AND p.pronargs=0""")
    rows=cursor.fetchall()
    if len(rows)!=1:raise ValueError('Exact publication guard required')
    return rows[0]


def exception_body(original, layers):
    # All literals derive from the pinned target and its hash-verified snapshot.
    literal=lambda v:"'"+str(v).replace("'","''")+"'"
    condition=f"""
 IF TG_OP='UPDATE' AND TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_dailyuipublication'
 AND current_database()={literal(DATABASE)}
 AND session_user='fresh_cohort6_issuer_001' AND current_user='fresh_cohort6_owner_001'
 AND current_setting('fresh.cohort6_native_rebind',true)={literal(RUN)}
 AND OLD.run_id={literal(RUN)}::uuid AND OLD.status='INCOMPLETE'
 AND OLD.seal_digest='' AND OLD.sealed_at IS NULL
 AND OLD.output_digest={literal(OUTPUT)} AND OLD.source_digest={literal(SOURCE)}
 AND OLD.recipe_digest={literal(RECIPE)} AND OLD.configuration_digest={literal(PRIOR)}
 AND NEW.configuration_digest={literal(NATIVE)}
 AND (to_jsonb(NEW)-'configuration_digest')=(to_jsonb(OLD)-'configuration_digest')
 AND OLD.layers={literal(json.dumps(layers))}::jsonb
 AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_dailyuiactivation WHERE publication_id=OLD.run_id)
 AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_operationalacceptance WHERE run_id=OLD.run_id)
 THEN RETURN NEW; END IF;
"""
    return original.replace('BEGIN','BEGIN'+condition,1)


def serialized(value):
    return json.loads(json.dumps(value, default=str))


def validate(current, expected, *, configuration, native, identities, activated, accepted):
    if (current != expected or str(current['run_id']) != RUN
            or current['status'] != 'INCOMPLETE' or current['seal_digest']
            or current['sealed_at'] is not None or activated or accepted
            or current['configuration_digest'] != PRIOR or configuration != PRIOR or native != NATIVE
            or any(current[key] != value for key, value in identities.items())):
        raise ValueError('Exact unsealed Cohort6 access-to-native transition required')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--evidence',required=True)
    parser.add_argument('--rollback-proof',action='store_true')
    args=parser.parse_args()
    raw=Path(args.snapshot).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=args.sha256:
        raise ValueError('Original publication snapshot differs')
    expected=json.loads(raw)
    import django
    django.setup()
    from django.db import connection,transaction,DatabaseError
    from mta.runtime.models import CalculationRun,DailyUiPublication,DailyUiActivation,OperationalAcceptance
    from mta.presentation.daily_publication import configuration_identity,source_identity,recipe_identity
    from mta.presentation.daily_activation import EMPTY_ACCESS
    if connection.settings_dict['NAME']!=DATABASE:
        raise ValueError('Only the owned Cohort6 database is permitted')
    run=CalculationRun.objects.get(pk=RUN)
    lock=int.from_bytes(run.pk.bytes[:8],'big',signed=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(%s)',[lock])
        if not cursor.fetchone()[0]:raise ValueError('Publication is busy')
    try:
        with transaction.atomic():
            from mta.runtime.publication_schema import FORWARD
            from psycopg import sql
            with connection.cursor() as cursor:
                cursor.execute('LOCK TABLE mta.fresh_mta_dailyuipublication IN ACCESS EXCLUSIVE MODE')
                original=guard_definition(cursor)
                expected_body=FORWARD.split('CREATE FUNCTION mta.guard_daily_ui_publication()',1)[1].split('AS $$',1)[1].split('$$;',1)[0]
                if original[0]!=expected_body or original[2] or original[3] or original[5]!='plpgsql':
                    raise ValueError('Installed guard differs from retained definition')
                cursor.execute('SELECT current_database(),session_user,current_user')
                if cursor.fetchone()!=(DATABASE,'fresh_cohort6_issuer_001','fresh_cohort6_owner_001'):
                    raise ValueError('Dedicated owned issuer required')
            publication=DailyUiPublication.objects.select_for_update().get(run=run)
            before=serialized(DailyUiPublication.objects.filter(run=run).values().get())
            attempts=serialized(list(publication.attempts.order_by('id').values()))
            if attempts!=expected['attempts'] or any(a['status']!='FAILED' for a in attempts):
                raise ValueError('Retained failed preparation attempt differs')
            validate(before,expected['publication'],configuration=configuration_identity(),
                native=configuration_identity(access=EMPTY_ACCESS),
                identities=dict(output_digest=run.output_digest,source_digest=source_identity(run),recipe_digest=recipe_identity()),
                activated=DailyUiActivation.objects.filter(publication=publication).exists(),
                accepted=OperationalAcceptance.objects.filter(run=run).exists())
            # Save the complete former metadata before changing its one draft field.
            with Path(args.evidence).open('xb') as stream:stream.write(raw)
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL('CREATE OR REPLACE FUNCTION mta.guard_daily_ui_publication() RETURNS trigger LANGUAGE plpgsql AS {}').format(sql.Literal(exception_body(original[0],before['layers']))))
                cursor.execute("SELECT set_config('fresh.cohort6_native_rebind',%s,true)",[RUN])
            denied=[]
            if args.rollback_proof:
                for name,changes in [('other_config',dict(configuration_digest='0'*64)),
                    ('ready',dict(configuration_digest=NATIVE,status='READY')),
                    ('seal',dict(configuration_digest=NATIVE,seal_digest='x')),
                    ('receipt',dict(configuration_digest=NATIVE,layers={})),
                    ('source',dict(configuration_digest=NATIVE,source_digest='x')),
                    ('recipe',dict(configuration_digest=NATIVE,recipe_digest='x')),
                    ('other_run',dict(configuration_digest=NATIVE,run_id='00000000-0000-0000-0000-000000000001'))]:
                    try:
                        with transaction.atomic():DailyUiPublication.objects.filter(run=run).update(**changes)
                    except DatabaseError as exc:
                        if 'Daily UI publication identity or ready seal is immutable' not in str(exc):raise
                        denied.append(name)
                    else:raise ValueError('Forbidden transition was admitted: '+name)
            publication.configuration_digest=NATIVE
            publication.save(update_fields=['configuration_digest'])
            after=serialized(DailyUiPublication.objects.filter(run=run).values().get())
            assert after=={**before,'configuration_digest':NATIVE}
            assert serialized(list(publication.attempts.order_by('id').values()))==attempts
            with connection.cursor() as cursor:
                cursor.execute(original[1])
                if guard_definition(cursor)!=original:raise ValueError('Original guard restoration differs')
            if args.rollback_proof:transaction.set_rollback(True)
        with connection.cursor() as cursor:
            if guard_definition(cursor)!=original:raise ValueError('Post-transaction guard differs')
        if args.rollback_proof:
            assert serialized(DailyUiPublication.objects.filter(run=run).values().get())==before
        print(json.dumps(dict(status='ROLLBACK_GUARD_PROOF_PASS' if args.rollback_proof else 'UNSEALED_CONFIGURATION_CORRECTED',run=RUN,
            prior=PRIOR,native=NATIVE,snapshot_sha256=args.sha256,other_fields_unchanged=True,
            original_guard_restored=True,denied=denied)))
    finally:
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock(%s)',[lock])


if __name__=='__main__':main()
