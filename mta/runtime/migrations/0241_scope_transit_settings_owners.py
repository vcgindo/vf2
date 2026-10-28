"""Extend the transit seal to exact native opening owners.

The legacy profile path retains its existing predicate. New paths must match
the complete stored image and the run's own initialization or predecessor.
Only this function changes; historical migrations and triggers stay intact.
"""
from importlib import import_module
from django.db import migrations

prior = import_module('mta.runtime.migrations.0207_scope_transit_guards')
MARKER = """  OR bag->'settings_owner'->>'path' IS DISTINCT FROM
     'input/profile/delivery/btr_history/importer_vf_settings'"""
OWNERS = r"""  OR (
   bag->'settings_owner'->>'path'='input/profile/delivery/btr_history/importer_vf_settings'
   OR (
    bag->'settings_owner'->>'path'='input/opening/state/dbm/VFSettings'
    AND (SELECT count(*) FROM jsonb_object_keys(bag->'settings_owner'))=5
    AND (bag->'settings_owner') ?& ARRAY['path','owner_kind','owner_id','input_manifest_digest','image']
    AND bag->'settings_owner'->>'owner_kind'='productioninitialization'
    AND R.predecessor_id IS NULL
    AND EXISTS(SELECT 1 FROM mta.fresh_mta_productioninitialization I
     WHERE I.id::text=bag->'settings_owner'->>'owner_id'
      AND I.source_id=P.source_id AND I.opening_date+1=R.business_date
      AND I.input_manifest_digest=bag->'settings_owner'->>'input_manifest_digest'
      AND I.input_payload->'images'->'input/opening/state/dbm/VFSettings/values'
       =bag->'settings_owner'->'image')
   ) OR (
    bag->'settings_owner'->>'path'='closing/dbm/VFSettings'
    AND (SELECT count(*) FROM jsonb_object_keys(bag->'settings_owner'))=6
    AND (bag->'settings_owner') ?& ARRAY['path','owner_kind','owner_id','input_manifest_digest','output_digest','image']
    AND bag->'settings_owner'->>'owner_kind'='calculationrun'
    AND EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun A
     JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=A.id
     WHERE A.id=R.predecessor_id AND A.id::text=bag->'settings_owner'->>'owner_id'
      AND A.kind='DAILY_CHAIN' AND A.status='SUCCEEDED'
      AND A.business_date+1=R.business_date AND C.source_id=P.source_id AND C.status='CONSUMED'
      AND A.input_manifest_digest=bag->'settings_owner'->>'input_manifest_digest'
      AND A.output_digest=bag->'settings_owner'->>'output_digest'
      AND A.production_manifest->'images'->'closing/dbm/VFSettings'
       =bag->'settings_owner'->'image')
   )
  ) IS NOT TRUE"""
assert prior.SQL.count(MARKER) == 1
SQL = prior.SQL.replace(MARKER, OWNERS, 1)
NAME = 'guard_scope_transit_generation'


def body(sql):
    return sql.split('CREATE FUNCTION mta.' + NAME + '()', 1)[1].split(
        'AS $guard$', 1)[1].split('$guard$;', 1)[0]


def replace(editor, before, after):
    with editor.connection.cursor() as cursor:
        cursor.execute("SELECT prosrc FROM pg_proc WHERE oid="
                       "'mta.guard_scope_transit_generation()'::regprocedure")
        if cursor.fetchall() != [(body(before),)]:
            raise ValueError('Existing transit generation guard differs; no replacement')
        function = after.split('CREATE FUNCTION mta.' + NAME + '()', 1)[1].split('$guard$;', 1)[0]
        cursor.execute('CREATE OR REPLACE FUNCTION mta.' + NAME + '()' + function + '$guard$;')


def install(apps, editor):
    replace(editor, prior.SQL, SQL)


def reverse(apps, editor):
    with editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM mta.fresh_mta_scopetransitgeneration WHERE "
            "metadata#>>'{transit,settings_owner,path}' IN "
            "('input/opening/state/dbm/VFSettings','closing/dbm/VFSettings') LIMIT 1")
        if cursor.fetchone():
            raise ValueError('Accepted native transit owners require a compatible forward release')
    replace(editor, SQL, prior.SQL)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0240_framework_metadata_writer_guards')]
    operations = [migrations.RunPython(install, reverse)]
