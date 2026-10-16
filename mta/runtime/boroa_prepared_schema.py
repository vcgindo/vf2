"""BOROA stable join occurrence guards; no live permissions or remarks are sealed."""
from mta.presentation.boroa_contract import RUN_ID
FORWARD=f"""
CREATE FUNCTION mta.guard_boroa_prepared_build() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid;
BEGIN
 owner:=nullif(current_setting('fresh.boroa_prepared_build',true),'')::uuid;
 IF owner IS DISTINCT FROM '{RUN_ID}'::uuid THEN RAISE EXCEPTION 'BOROA preparation owner required'; END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=owner FOR UPDATE;
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_boroasourcereceipt WHERE run_id=owner)
 THEN RAISE EXCEPTION 'BOROA source receipt required'; END IF;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_boroapreparedreceipt WHERE run_id=owner)
 THEN RAISE EXCEPTION 'BOROA preparation already sealed'; END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION mta.guard_boroa_prepared_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.run_id::text IS DISTINCT FROM current_setting('fresh.boroa_prepared_build',true)
 THEN RAISE EXCEPTION 'BOROA preparation row owner differs'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.guard_boroa_prepared_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.run_id::text IS DISTINCT FROM current_setting('fresh.boroa_prepared_build',true)
 OR NEW.row_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_boroapreparedrow WHERE run_id=NEW.run_id)
 THEN RAISE EXCEPTION 'BOROA prepared receipt differs'; END IF;
 RETURN NEW;
END $$;
"""
BINDINGS=[]
for table in ('fresh_mta_boroapreparedrow','fresh_mta_boroapreparedreceipt'):
    prefix=table.removeprefix('fresh_mta_')
    BINDINGS += [(prefix+'_build',table,6,'guard_boroa_prepared_build','BEFORE INSERT','STATEMENT'),
        (prefix+'_row',table,7,'guard_boroa_prepared_receipt' if table.endswith('receipt') else 'guard_boroa_prepared_row','BEFORE INSERT','ROW'),
        (prefix+'_immutable',table,58,'deny_boroa_source_mutation','BEFORE UPDATE OR DELETE OR TRUNCATE','STATEMENT')]
for name,table,_,function,operation,level in BINDINGS:
    FORWARD+=f'CREATE TRIGGER {name} {operation} ON mta.{table} FOR EACH {level} EXECUTE FUNCTION mta.{function}();\n'
REVERSE='\n'.join(f'DROP TRIGGER {name} ON mta.{table};' for name,table,*_ in BINDINGS)
REVERSE+='\n'+'\n'.join(f'DROP FUNCTION mta.{name}();' for name in (
    'guard_boroa_prepared_build','guard_boroa_prepared_row','guard_boroa_prepared_receipt'))


PRODUCTION_BODIES={
'guard_boroa_prepared_build':f"""
DECLARE owner uuid;
BEGIN
 owner:=nullif(current_setting('fresh.boroa_prepared_build',true),'')::uuid;
 IF NOT mta.daily_prepared_owner(owner) AND owner IS DISTINCT FROM '{RUN_ID}'::uuid
 THEN RAISE EXCEPTION 'BOROA preparation owner required'; END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun WHERE id=owner FOR UPDATE;
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_boroasourcereceipt WHERE run_id=owner)
 THEN RAISE EXCEPTION 'BOROA source receipt required'; END IF;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_boroapreparedreceipt WHERE run_id=owner)
 THEN RAISE EXCEPTION 'BOROA preparation already sealed'; END IF;
 RETURN NULL;
END """,
'guard_boroa_prepared_row':"""
BEGIN
 IF NEW.run_id::text IS DISTINCT FROM current_setting('fresh.boroa_prepared_build',true)
 THEN RAISE EXCEPTION 'BOROA preparation row owner differs'; END IF;
 RETURN NEW;
END """,
'guard_boroa_prepared_receipt':"""
BEGIN
 IF NEW.run_id::text IS DISTINCT FROM current_setting('fresh.boroa_prepared_build',true)
 OR NEW.row_count IS DISTINCT FROM (SELECT count(*) FROM mta.fresh_mta_boroapreparedrow WHERE run_id=NEW.run_id)
 THEN RAISE EXCEPTION 'BOROA prepared receipt differs'; END IF;
 RETURN NEW;
END """}

def production_definitions():
    return '\n'.join('CREATE OR REPLACE FUNCTION mta.'+name+
        '() RETURNS trigger LANGUAGE plpgsql AS $$'+body+'$$;' for name,body in PRODUCTION_BODIES.items())

def installed_bodies(connection,bodies):
    with connection.cursor() as c:
        c.execute("SELECT EXISTS(SELECT 1 FROM django_migrations WHERE app='fresh_mta' AND name='0139_native_bor_preparation')")
        if not c.fetchone()[0]: return bodies
    return {name:PRODUCTION_BODIES.get(name,body) for name,body in bodies.items()}


def verify_guards(connection):
    import re
    from mta.runtime.boroa_source_schema import verify_guards as source_guards
    source_guards(connection)
    expected={name:(table,'O',bits,func,None,0,'mta') for name,table,bits,func,*_ in BINDINGS}
    bodies=installed_bodies(connection,dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;',FORWARD,re.S)))
    with connection.cursor() as c:
        c.execute('SELECT t.tgname,c.relname,t.tgenabled,t.tgtype,p.proname,t.tgqual::text,t.tgnargs,pn.nspname '
            'FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace '
            'JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace pn ON pn.oid=p.pronamespace '
            "WHERE n.nspname='mta' AND NOT t.tgisinternal AND c.relname=ANY(%s)",[sorted({row[1] for row in BINDINGS})])
        if sorted(c.fetchall())!=sorted((name,*row) for name,row in expected.items()): raise ValueError('BOROA prepared trigger drift')
        c.execute("SELECT p.proname,p.prosrc,p.prolang=l.oid,p.prosecdef FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.lanname='plpgsql' "
            "WHERE n.nspname='mta' AND p.proname=ANY(%s) AND p.pronargs=0",[list(bodies)])
        if {name:tuple(row) for name,*row in c.fetchall()}!={n:(b,True,False) for n,b in bodies.items()}:
            raise ValueError('BOROA prepared function drift')
