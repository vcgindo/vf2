"""Immutable April BOR source receipt; live remarks are separate append-only rows."""
from mta.presentation.bor_contract import RUN_ID, NATIVE_DIGEST

SOURCE_TABLES = ('fresh_mta_borsourcerow', 'fresh_mta_borsobrow',
                 'fresh_mta_bormoqrow', 'fresh_mta_borinitialremark', 'fresh_mta_borsourcereceipt')
FORWARD = f"""
CREATE FUNCTION mta.guard_bor_source_build() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid;
BEGIN
 owner := nullif(current_setting('fresh.bor_source_build',true),'')::uuid;
 IF owner IS DISTINCT FROM '{RUN_ID}'::uuid THEN RAISE EXCEPTION 'BOR source owner required'; END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=owner AND kind='LEGACY_UI_FIXTURE'
 AND status='FIXTURE_BLOCKED' AND business_date=DATE '2026-04-07' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'BOR requires retained April fixture'; END IF;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_borsourcereceipt WHERE run_id=owner)
 THEN RAISE EXCEPTION 'BOR source already sealed'; END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION mta.guard_bor_source_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.run_id::text IS DISTINCT FROM current_setting('fresh.bor_source_build',true)
 THEN RAISE EXCEPTION 'BOR source row owner differs'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_bor_source_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.run_id::text IS DISTINCT FROM current_setting('fresh.bor_source_build',true)
 OR NEW.source_digest IS DISTINCT FROM '{NATIVE_DIGEST}'
 OR (SELECT count(*) FROM mta.fresh_mta_borsourcerow WHERE run_id=NEW.run_id)<>1196
 OR (SELECT count(*) FROM mta.fresh_mta_borsobrow WHERE run_id=NEW.run_id)<>97
 OR (SELECT count(*) FROM mta.fresh_mta_bormoqrow WHERE run_id=NEW.run_id)<>1496
 OR (SELECT count(*) FROM mta.fresh_mta_borinitialremark WHERE run_id=NEW.run_id)<>27
 THEN RAISE EXCEPTION 'BOR source receipt differs'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_bor_source_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'BOR source and history rows are immutable'; END $$;
CREATE FUNCTION mta.guard_bor_live_remark() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.run_id IS DISTINCT FROM '{RUN_ID}'::uuid
 OR NEW.actor_id IS DISTINCT FROM nullif(current_setting('fresh.bor_actor',true),'')
 OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_borsourcereceipt WHERE run_id=NEW.run_id)
 THEN RAISE EXCEPTION 'BOR authenticated write binding required'; END IF;
 RETURN NEW;
END $$;
"""
BINDINGS = []
for table in SOURCE_TABLES:
    prefix = table.removeprefix('fresh_mta_')
    BINDINGS += [(prefix+'_build', table, 6, 'guard_bor_source_build',
                  'BEFORE INSERT', 'STATEMENT'),
                 (prefix+'_row', table, 7, 'guard_bor_source_receipt' if table.endswith('receipt')
                  else 'guard_bor_source_row', 'BEFORE INSERT', 'ROW'),
                 (prefix+'_immutable', table, 58, 'deny_bor_source_mutation',
                  'BEFORE UPDATE OR DELETE OR TRUNCATE', 'STATEMENT')]
BINDINGS += [('bor_live_append', 'fresh_mta_borliveremark', 7, 'guard_bor_live_remark', 'BEFORE INSERT', 'ROW'),
             ('bor_live_immutable', 'fresh_mta_borliveremark', 58, 'deny_bor_source_mutation',
              'BEFORE UPDATE OR DELETE OR TRUNCATE', 'STATEMENT')]
for name, table, _, function, operation, level in BINDINGS:
    FORWARD += f'CREATE TRIGGER {name} {operation} ON mta.{table} FOR EACH {level} EXECUTE FUNCTION mta.{function}();\n'
REVERSE = '\n'.join(f'DROP TRIGGER {name} ON mta.{table};' for name, table, *_ in BINDINGS)
REVERSE += '\n' + '\n'.join(f'DROP FUNCTION mta.{name}();' for name in (
    'guard_bor_source_build','guard_bor_source_row','guard_bor_source_receipt',
    'deny_bor_source_mutation','guard_bor_live_remark'))


def verify_guards(connection):
    import re
    expected={name:(table,'O',bits,func,None,0,'mta') for name,table,bits,func,*_ in BINDINGS}
    bodies=dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;',FORWARD,re.S))
    with connection.cursor() as c:
        c.execute('SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,t.tgqual::text,t.tgnargs,pn.nspname '
            'FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace '
            'JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace pn ON pn.oid=p.pronamespace '
            "WHERE n.nspname='mta' AND NOT t.tgisinternal AND c.relname=ANY(%s)",[[*SOURCE_TABLES,'fresh_mta_borliveremark']])
        if sorted(c.fetchall()) != sorted((name,*row) for name,row in expected.items()):
            raise ValueError('BOR source trigger contract differs')
        c.execute("SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.lanname='plpgsql' "
            "WHERE n.nspname='mta' AND p.proname=ANY(%s) AND p.pronargs=0",[list(bodies)])
        if {name:tuple(row) for name,*row in c.fetchall()} != {n:(b,True,False) for n,b in bodies.items()}:
            raise ValueError('BOR source function contract differs')
