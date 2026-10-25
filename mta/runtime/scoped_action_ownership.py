"""Fresh command capabilities over the existing immutable scoped read models."""
from contextlib import contextmanager, nullcontext
from importlib import import_module

from django.db import connection, transaction, DatabaseError


MIGRATION = '0226_scoped_dbm_action_dependencies'


def migration():
    return import_module('mta.runtime.migrations.' + MIGRATION)


def available(cursor):
    cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.django_migrations WHERE app='fresh_mta' AND name=%s),"
        "to_regprocedure('mta.stamp_scoped_action_transaction()')", [MIGRATION])
    applied, function = cursor.fetchone()
    if not applied and function is None:
        return False
    verify_guards(cursor)
    return True


def verify_guards(cursor=None):
    frozen = migration()
    with (connection.cursor() if cursor is None else nullcontext(cursor)) as c:
        verify_actionable(c)
        c.execute("SELECT C.relname,T.tgname,T.tgtype,P.proname,T.tgenabled,T.tgnargs,T.tgqual::text,"
            "T.tgattr::text,T.tgoldtable,T.tgnewtable,T.tgdeferrable,T.tginitdeferred,N.nspname "
            "FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid JOIN pg_proc P ON P.oid=T.tgfoid "
            "JOIN pg_namespace N ON N.oid=P.pronamespace JOIN pg_namespace CN ON CN.oid=C.relnamespace "
            "WHERE CN.nspname='mta' AND T.tgname IN ('scope_action_transaction','scope_action_cache_insert') "
            "AND NOT T.tgisinternal ORDER BY 1,2")
        specs = [(table, 'scope_action_cache_insert', 7, 'guard_scoped_action_cache') for table in frozen.GENERATIONS]
        specs.append(('fresh_mta_runcommand', 'scope_action_transaction', 7, 'stamp_scoped_action_transaction'))
        if c.fetchall() != [(*r, 'O', 0, None, '', None, None, False, False, 'mta') for r in sorted(specs)]:
            raise ValueError('Scoped action transaction/generation triggers differ')
        bodies = dict(stamp_scoped_action_transaction=(frozen.STAMP, 'trigger'),
            guard_scoped_action_cache=(frozen.CACHE, 'trigger'),
            guard_phase_rows=(frozen.PHASE_ROWS_BODY, 'trigger'),
            scope_cache_command=(frozen.LEASE, 'fresh_mta_runcommand'))
        c.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,pg_get_function_result(P.oid),"
            "P.proowner=C.relowner,(P.proname='scope_cache_command' OR NOT EXISTS(SELECT 1 FROM "
            "aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A WHERE A.grantee<>P.proowner)) "
            "FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace JOIN pg_language L ON L.oid=P.prolang "
            "CROSS JOIN pg_class C WHERE N.nspname='mta' AND C.oid='mta.fresh_mta_runcommand'::regclass "
            "AND P.proname=ANY(%s) ORDER BY 1", [list(bodies)])
        # The application profile separately validates the helper's exact ACL.
        rows = c.fetchall()
        if [r[:-1] for r in rows] != [(n,b,False,['search_path=pg_catalog, mta'],'plpgsql',result,True)
                for n,(b,result) in sorted(bodies.items())] or any(not r[-1] for r in rows):
            raise ValueError('Scoped action ownership function differs')
        c.execute("SELECT format_type(atttypid,atttypmod),attnotnull,pg_get_expr(D.adbin,D.adrelid) "
            "FROM pg_attribute A LEFT JOIN pg_attrdef D ON D.adrelid=A.attrelid AND D.adnum=A.attnum "
            "WHERE A.attrelid='mta.fresh_mta_runcommand'::regclass AND A.attname='append_transaction' AND NOT A.attisdropped")
        if c.fetchall() != [('character varying(20)', True, "''::character varying")]:
            raise ValueError('Scoped action transaction column differs')


def verified_business_rows(cursor, rows, *, name_index=1):
    if available(cursor):
        return [row for row in rows if row[name_index]!='scope_action_cache_insert']
    return rows


def application_guard_body(original):
    """Extend only scoped command branches; preserve the original Full branch."""
    body = original
    anchor = " ELSIF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_runcommand' THEN\n"
    scope = """  IF NEW.phase_acceptance_id IS NOT NULL THEN
   IF (
    OLD.append_transaction IS DISTINCT FROM pg_current_xact_id()::text
    OR OLD.state_sealed OR OLD.phase_acceptance_id IS DISTINCT FROM NEW.phase_acceptance_id
    OR NEW.payload->>'actor' IS DISTINCT FROM current_setting('fresh.scope_action_actor',true)
    OR NOT mta.actionable_scope_phase(NEW.run_id,NEW.phase_acceptance_id)
    OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_scopereadreference F
     JOIN mta.fresh_mta_scopereportgeneration H ON H.id=F.report_generation_id
     WHERE F.id=nullif(current_setting('fresh.scope_action_reference',true),'')::uuid
      AND H.sealed AND H.run_id=NEW.run_id AND H.phase_id=NEW.phase_acceptance_id
      AND H.action_revision=NEW.scope_parent_revision)) THEN
   RAISE EXCEPTION 'Application scoped command requires its fresh selected transaction'; END IF;
  END IF;
"""
    assert body.count(anchor) == 1
    body = body.replace(anchor, anchor + scope)
    old = "(to_jsonb(OLD)-'state_manifest') IS DISTINCT FROM (to_jsonb(NEW)-'state_manifest')"
    new = """(to_jsonb(OLD)-CASE WHEN NEW.phase_acceptance_id IS NULL THEN ARRAY['state_manifest']
      ELSE ARRAY['state_manifest','scope_revision_after'] END) IS DISTINCT FROM
     (to_jsonb(NEW)-CASE WHEN NEW.phase_acceptance_id IS NULL THEN ARRAY['state_manifest']
      ELSE ARRAY['state_manifest','scope_revision_after'] END)"""
    assert body.count(old) == 1
    body = body.replace(old, new)
    old = "(NEW.payload->>'operation'='SLEEP' AND entry.key='NormAcceptanceTbl' AND entry.value->>'count'<>'0')"
    new = """(NEW.payload->>'operation'='SLEEP' AND entry.key='NormAcceptanceTbl' AND
       (CASE WHEN NEW.phase_acceptance_id IS NULL THEN entry.value->>'count'<>'0'
        ELSE NEW.before_digest IS DISTINCT FROM NEW.after_digest
          OR NEW.state_manifest-'NormAcceptanceTbl'<>'{}'::jsonb END))"""
    assert body.count(old) == 1
    body = body.replace(old,new)
    anchor = '  SELECT * INTO command FROM mta.fresh_mta_runcommand WHERE id=command_id AND run_id=NEW.vf_run_id;\n'
    scope = """  IF command.phase_acceptance_id IS NOT NULL THEN
   IF command.append_transaction IS DISTINCT FROM pg_current_xact_id()::text OR command.state_sealed
    OR command.state_manifest<>'{}'::jsonb
    OR command.payload->>'actor' IS DISTINCT FROM current_setting('fresh.scope_action_actor',true)
    OR (family='NormAcceptanceTbl' AND NOT (command.payload->>'operation'='APPLY'
      OR (command.payload->>'operation'='SLEEP' AND command.before_digest=command.after_digest)))
    OR (family<>'NormAcceptanceTbl' AND command.payload->>'operation'<>'SLEEP')
    OR NOT mta.actionable_scope_phase(command.run_id,command.phase_acceptance_id)
    OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_scopereadreference F
     JOIN mta.fresh_mta_scopereportgeneration H ON H.id=F.report_generation_id
     WHERE F.id=nullif(current_setting('fresh.scope_action_reference',true),'')::uuid
      AND H.sealed AND H.run_id=command.run_id AND H.phase_id=command.phase_acceptance_id
      AND H.action_revision=command.scope_parent_revision) THEN
    RAISE EXCEPTION 'Application scoped image requires its fresh selected command'; END IF;
   RETURN NEW;
  END IF;
"""
    assert body.count(anchor) == 1
    body = body.replace(anchor, anchor + scope)
    for command in ('NEW','command'):
        old = 'H.phase_id='+command+'.phase_acceptance_id'
        assert body.count(old) == 1
        body = body.replace(old,migration().dependency('H.phase_id',
            command+'.phase_acceptance_id',command+'.run_id'))
    return body


def grants():
    result = {'mta.'+name: dict(table=['INSERT', 'UPDATE'], columns=['metadata','digest','sealed','sealed_at'])
              for name in migration().GENERATIONS}
    for name in ('0198_scope_report_guards', '0200_scope_source_guards', '0202_scope_planning_guards',
                 '0207_scope_transit_guards', '0210_scope_git_guards', '0212_scope_pick_guards',
                 '0214_scope_expedite_guards', '0216_scope_expedite_parent_guards'):
        for table in import_module('mta.runtime.migrations.'+name).TABLES.values():
            result['mta.'+(table[0] if isinstance(table,tuple) else table)] = dict(table=['INSERT'], columns=[])
    result['mta.fresh_mta_runcommand'] = dict(table=['INSERT','UPDATE'], columns=['state_manifest','scope_revision_after'])
    result['mta.fresh_mta_ingestionrevisionstate'] = dict(table=['UPDATE'], columns=['initialization_id'])
    return result


def application_grants(catalogue):
    functions = {f['name']: f for f in catalogue['functions']}
    names = ('mta.stamp_scoped_action_transaction()', 'mta.guard_scoped_action_cache()',
             'mta.scope_cache_command(reference uuid, actor text)')
    if not any(n in functions for n in names):
        return {}
    expected = ((migration().STAMP,'trigger'), (migration().CACHE,'trigger'), (migration().LEASE,'fresh_mta_runcommand'))
    for name,(body,result) in zip(names,expected):
        f=functions.get(name)
        if (f is None or f['body']!=body or f['returns']!=result or f['security_definer']
                or f['configuration']!=['search_path=pg_catalog, mta']):
            raise ValueError('Scoped action application capability differs')
    return grants()


def verify_actionable(cursor):
    """Only the original or explicitly migrated222 helper may own actions."""
    cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.django_migrations WHERE app='fresh_mta' AND name=%s)",
        ['0222_recovered_scope_actions'])
    upgraded=cursor.fetchone()[0]
    frozen=import_module('mta.runtime.migrations.0222_recovered_scope_actions')
    cursor.execute("SELECT P.prosrc,P.prosecdef,P.proconfig,L.lanname,P.provolatile,"
        "P.prorettype='boolean'::regtype,P.proowner=C.relowner FROM pg_proc P "
        "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
        "WHERE P.oid=to_regprocedure('mta.actionable_scope_phase(uuid,uuid)') "
        "AND C.oid='mta.fresh_mta_runscopeattempt'::regclass")
    if cursor.fetchall()!=[(frozen.BODY if upgraded else frozen.OLD,False,
            ['search_path=pg_catalog, mta'],'sql','s',True,True)]:
        raise ValueError('Scoped actionable recovery helper differs')


def application_functions(catalogue):
    if not application_grants(catalogue):
        return set()
    # Exact current invoker bodies only; none can become a definer capability.
    definitions = {}
    for name,args,module,attribute in (
        ('scope_head','target uuid','0188_day_final_ownership','_head'),
        ('scope_native_cut','target uuid','0204_scoped_bpr_consumer_ownership','NEW_NATIVE'),
        ('scope_expected_cut','target uuid','0191_scoped_action_ownership','_expected')):
        raw=getattr(import_module('mta.runtime.migrations.'+module),attribute)
        definitions['mta.'+name+'('+args+')']=raw.split('AS $body$',1)[1]
    for name,args,module in (
        ('valid_scope_cut','value jsonb','0182_scoped_revision_ownership'),
        ('scope_cut_next','value jsonb','0182_scoped_revision_ownership'),
        ('actionable_scope_phase','target uuid, accepted uuid','0191_scoped_action_ownership'),
        ('pending_scope_action','target uuid, image text, physical text','0191_scoped_action_ownership')):
        raw=import_module('mta.runtime.migrations.'+module).SQL
        definitions['mta.'+name+'('+args+')']=raw.split('FUNCTION mta.'+name+'('+args+')',1)[1].split('AS $body$',1)[1].split('$body$;',1)[0]
    actionable='mta.actionable_scope_phase(target uuid, accepted uuid)'
    frozen=import_module('mta.runtime.migrations.0222_recovered_scope_actions')
    functions={f['name']:f for f in catalogue['functions']}
    # Application catalogue verification has no database cursor. Accept only
    # these two finite bodies; runtime admission checks the actual migration.
    if functions.get(actionable,{}).get('body')==frozen.BODY:
        definitions[actionable]=frozen.BODY
    raw=import_module('mta.runtime.migrations.0188_day_final_ownership').SQL
    definitions['mta.pending_day_final(target uuid)']=raw.split('FUNCTION mta.pending_day_final(target uuid)',1)[1].split('AS $body$',1)[1].split('$body$;',1)[0]
    definitions['mta.scope_bpr_consumer_cut(target uuid, observed jsonb)']=import_module(
        'mta.runtime.migrations.0205_scoped_bpr_consumer_recovery').NEW
    definitions['mta.scope_cache_command(reference uuid, actor text)']=migration().LEASE
    functions={f['name']:f for f in catalogue['functions']}
    for name,body in definitions.items():
        f=functions.get(name)
        if (f is None or f['body']!=body or f['security_definer']
                or f['configuration'] not in (['search_path=pg_catalog, mta'],['search_path=pg_catalog'])):
            raise ValueError('Scoped action invoker helper differs: '+name)
    return set(definitions)


@contextmanager
def publication(reference_id, actor):
    if not connection.in_atomic_block:
        raise ValueError('Scoped action publication requires its transaction')
    with connection.cursor() as c:
        c.execute("SELECT current_setting('fresh.scope_action_reference',true),current_setting('fresh.scope_action_actor',true)")
        previous=tuple(value or '' for value in c.fetchone())
        c.execute("SELECT set_config('fresh.scope_action_reference',%s,true),set_config('fresh.scope_action_actor',%s,true)",
                  [str(reference_id),str(actor)])
    try:
        yield
    except DatabaseError:
        transaction.set_rollback(True)
        raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as c:
                c.execute("SELECT set_config('fresh.scope_action_reference',%s,true),set_config('fresh.scope_action_actor',%s,true)",previous)
