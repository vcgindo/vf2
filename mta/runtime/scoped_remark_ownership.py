"""Exact statement ownership for application-owned remark cache publication."""
from contextlib import contextmanager, nullcontext
from importlib import import_module
from django.db import connection, transaction, DatabaseError
from mta.presentation.context import PublicationUnavailable


def migration():
    return import_module('mta.runtime.migrations.0220_scoped_remark_cache_writer')


def available(cursor):
    from mta.presentation.schema_reuse import action_guard
    if action_guard('remark',cursor):
        return True
    cursor.execute("SELECT to_regprocedure('mta.guard_scoped_remark_cache_writer()'),"
        "to_regprocedure('mta.stamp_scoped_remark_transaction()')")
    row = cursor.fetchone()
    if row == (None, None): return False
    verify_guards(cursor)
    return True


def verified_business_rows(cursor, rows, *, name_index=0):
    # Old guards still verify their complete original set. Only these separately
    # verified additive triggers may be removed from that comparison.
    if available(cursor):
        return [row for row in rows if row[name_index] not in
            ('scope_remark_transaction', 'scope_remark_writer_insert', 'scope_remark_writer_update')]
    return rows


GRANTS = {
    'mta.fresh_mta_scopeexpediteparentgeneration': dict(table=['INSERT', 'UPDATE'],
        columns=['metadata', 'digest', 'sealed', 'sealed_at']),
    'mta.fresh_mta_scopeexpediteparentbase': dict(table=['INSERT'], columns=[]),
    'mta.fresh_mta_scopeexpediteparentmatch': dict(table=['INSERT'], columns=[]),
    'mta.fresh_mta_scopereadreference': dict(table=['INSERT'], columns=[]),
}
UUID_TABLES = frozenset(('mta.fresh_mta_scopeexpediteparentgeneration', 'mta.fresh_mta_scopereadreference'))


def application_grants(catalogue):
    names = {f['name']: f for f in catalogue['functions']}
    expected = dict(guard_scoped_remark_cache_writer=migration().GUARD,
        stamp_scoped_remark_transaction=migration().STAMP)
    if 'mta.stamp_scoped_action_transaction()' in names:
        from mta.runtime.scoped_action_ownership import migration as action_migration
        expected['guard_scoped_remark_cache_writer'] = action_migration(catalogue=catalogue).REMARK_GUARD
    present = {n for n in expected if 'mta.' + n + '()' in names}
    if not present: return {}
    if present != set(expected): raise ValueError('Incomplete scoped remark ownership capability')
    for name, body in expected.items():
        f = names['mta.' + name + '()']
        if (f['body'] != body or f['security_definer'] or f['returns'] != 'trigger'
                or f['configuration'] != ['search_path=pg_catalog, mta']):
            raise ValueError('Scoped remark ownership capability differs')
    return GRANTS


def verify_guards(cursor=None):
    from mta.presentation.schema_reuse import action_guard
    if action_guard('remark',cursor):
        return
    return _verify_guards(cursor)


def _verify_guards(cursor=None):
    expected = []
    frozen = migration()
    for table in frozen.TARGETS:
        for operation, kind in (('insert', 4), ('update', 16)):
            if operation == 'update' and table != frozen.TARGETS[0]: continue
            expected.append((table, 'scope_remark_writer_' + operation, kind,
                'guard_scoped_remark_cache_writer', None, 'new_rows'))
    expected.append(('fresh_mta_bprliveremark', 'scope_remark_transaction', 7,
        'stamp_scoped_remark_transaction', None, None))
    with (connection.cursor() if cursor is None else nullcontext(cursor)) as c:
        c.execute("SELECT C.relname,T.tgname,T.tgtype,P.proname,T.tgoldtable,T.tgnewtable,T.tgenabled,"
            "T.tgnargs,T.tgqual::text,T.tgattr::text,T.tgdeferrable,T.tginitdeferred,N.nspname "
            "FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid JOIN pg_namespace CN ON CN.oid=C.relnamespace "
            "JOIN pg_proc P ON P.oid=T.tgfoid JOIN pg_namespace N ON N.oid=P.pronamespace "
            "WHERE CN.nspname='mta' AND (T.tgname='scope_remark_transaction' OR T.tgname LIKE 'scope_remark_writer_%%') "
            "AND NOT T.tgisinternal ORDER BY 1,2")
        if c.fetchall() != [(*r, 'O', 0, None, '', False, False, 'mta') for r in sorted(expected)]:
            raise PublicationUnavailable('scoped_remark_writer_trigger_contract_differs')
        bodies = dict(guard_scoped_remark_cache_writer=frozen.GUARD, stamp_scoped_remark_transaction=frozen.STAMP)
        from mta.runtime import scoped_action_ownership
        if scoped_action_ownership.available(c):
            bodies['guard_scoped_remark_cache_writer'] = scoped_action_ownership.migration(c).REMARK_GUARD
        c.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,P.proowner=C.relowner,"
            "P.prorettype='trigger'::regtype,P.pronargs=0,NOT EXISTS(SELECT 1 FROM "
            "aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A WHERE A.grantee<>P.proowner) "
            "FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace JOIN pg_language L ON L.oid=P.prolang "
            "CROSS JOIN pg_class C WHERE C.oid='mta.fresh_mta_scopereadreference'::regclass "
            "AND N.nspname='mta' AND P.proname=ANY(%s) ORDER BY 1", [list(bodies)])
        if c.fetchall() != [(n,b,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True,True)
                for n,b in sorted(bodies.items())]:
            raise PublicationUnavailable('scoped_remark_writer_function_contract_differs')
        c.execute("SELECT format_type(atttypid,atttypmod),attnotnull FROM pg_attribute "
            "WHERE attrelid='mta.fresh_mta_bprliveremark'::regclass AND attname='append_transaction' AND NOT attisdropped")
        if c.fetchall() != [('character varying(20)', True)]:
            raise PublicationUnavailable('scoped_remark_transaction_column_differs')


@contextmanager
def publication(reference_id, actor_id):
    if not connection.in_atomic_block: raise ValueError('Scoped remark publication requires its transaction')
    with connection.cursor() as c:
        c.execute("SELECT current_setting('fresh.scope_remark_reference',true),current_setting('fresh.daily_remark_actor',true)")
        previous = tuple(value or '' for value in c.fetchone())
        c.execute("SELECT set_config('fresh.scope_remark_reference',%s,true),set_config('fresh.daily_remark_actor',%s,true)",
            [str(reference_id), str(actor_id)])
    try: yield
    except DatabaseError:
        transaction.set_rollback(True)
        raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as c:
                c.execute("SELECT set_config('fresh.scope_remark_reference',%s,true),set_config('fresh.daily_remark_actor',%s,true)", previous)
