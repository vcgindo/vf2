"""Freeze owned fixture data after full load proof; preferences stay writable."""
import os
from tools.stage2_vm_load import DATA,DB,IDENTITY
from tools.stage2_vm_contract import atomic,sealed


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()
    from django.db import connection,transaction
    from mta.runtime.models import UserReportLayout
    from mta.serialization import digest
    from mta.presentation.fixture import freeze_state
    manifest,manifest_sha=sealed(DATA)
    if connection.settings_dict['NAME']!=DB:raise ValueError('Wrong fixture database')
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute('SELECT metadata FROM stage2_owner.consumer_publication WHERE identity=%s',[IDENTITY])
            if not cur.fetchone():raise ValueError('Final consumer publication required')
            cur.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND (n.nspname LIKE 'stage_demo_%' OR n.nspname IN ('mta','mta_state','stage2_owner')) ORDER BY 1,2")
            tables=[(s,t) for s,t in cur.fetchall() if t!=UserReportLayout._meta.db_table]
            cur.execute("CREATE OR REPLACE FUNCTION stage2_owner.deny_fixture_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable Stage2 legacy fixture'; END $$")
            for schema,table in tables:
                cur.execute('SELECT 1 FROM pg_trigger WHERE tgrelid=%s::regclass AND tgname=%s',[connection.ops.quote_name(schema)+'.'+connection.ops.quote_name(table),'stage2_immutable'])
                if not cur.fetchone():
                    cur.execute('CREATE TRIGGER stage2_immutable BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON '+connection.ops.quote_name(schema)+'.'+connection.ops.quote_name(table)+' FOR EACH STATEMENT EXECUTE FUNCTION stage2_owner.deny_fixture_mutation()')
    state=freeze_state()
    atomic(DATA/'freeze-receipt.json',dict(identity=IDENTITY,manifest_sha256=manifest_sha,state=state,digest=digest(state)))
    print('Frozen fixture relations',len(state['triggers']))


if __name__=='__main__':main()
