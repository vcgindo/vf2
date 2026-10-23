"""Exact recognition of the additive accepted-state guards, never a bypass.

The frozen migration owns SQL/participants. Existing source, opening, layer and
application guards remain independently required. No row checks are removed here.
"""
from importlib import import_module


NAMES = frozenset(('accepted_rows_insert', 'accepted_rows_update', 'accepted_rows_delete',
    'accepted_no_truncate', 'terminal_run_immutable', 'zz_accepted_command_seal',
    'accepted_command_complete'))


def verify_guards(cursor, *, required=True):
    frozen = import_module('mta.runtime.migrations.0169_accepted_state_ownership')
    cursor.execute("SELECT n.nspname,c.relname,t.tgname,t.tgenabled,t.tgtype,t.tgnargs,"
        "encode(t.tgargs,'escape'),t.tgqual::text,t.tgattr::text,t.tgoldtable,t.tgnewtable,"
        "t.tgdeferrable,t.tginitdeferred,(t.tgconstraint<>0),pn.nspname,p.proname "
        "FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid "
        "JOIN pg_namespace pn ON pn.oid=p.pronamespace "
        "WHERE t.tgname=ANY(%s) OR (pn.nspname='mta' AND p.proname=ANY(%s)) ORDER BY 1,2,3",
        [list(NAMES), list(frozen.FUNCTIONS)])
    actual = cursor.fetchall()
    cursor.execute("SELECT n.nspname,p.proname,p.pronargs,p.prosrc,p.prosecdef,p.proconfig,"
        "p.prorettype='trigger'::regtype,p.proowner=R.relowner,L.lanname,p.provolatile,"
        "p.proisstrict,p.proleakproof,p.proparallel,p.prokind,p.proretset,"
        "NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) A "
        "WHERE A.grantee<>p.proowner) "
        "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "JOIN pg_language L ON L.oid=p.prolang CROSS JOIN pg_class R "
        "WHERE R.oid=to_regclass('mta.fresh_mta_calculationrun') "
        "AND n.nspname='mta' AND p.proname=ANY(%s) ORDER BY p.proname",
        [list(frozen.FUNCTIONS)])
    functions = cursor.fetchall()
    cursor.execute("SELECT format_type(a.atttypid,a.atttypmod),a.attnotnull,a.atthasdef,"
        "a.attidentity,a.attgenerated,pg_get_expr(D.adbin,D.adrelid) FROM pg_attribute a "
        "LEFT JOIN pg_attrdef D ON D.adrelid=a.attrelid AND D.adnum=a.attnum "
        "WHERE a.attrelid=to_regclass('mta.fresh_mta_runcommand') "
        "AND a.attname='state_sealed' AND NOT a.attisdropped")
    column = cursor.fetchall()
    if not actual and not functions and not column and not required:
        return False
    expected_functions = [('mta', name, 0, body, False, ['search_path=pg_catalog, mta'],
        True, True, 'plpgsql', 'v', False, False, 'u', 'f', False, True)
        for name, body in sorted(frozen.FUNCTIONS.items())]
    if functions != expected_functions:
        raise ValueError('Accepted state function/seal contract differs')
    specs = {
        'accepted_rows_insert': (4, 1, None, 'new_rows', False, 'guard_accepted_rows'),
        'accepted_rows_update': (16, 1, 'old_rows', 'new_rows', False, 'guard_accepted_rows'),
        'accepted_rows_delete': (8, 1, 'old_rows', None, False, 'guard_accepted_rows'),
        'accepted_no_truncate': (34, 0, None, None, False, 'deny_accepted_truncate'),
        'terminal_run_immutable': (27, 0, None, None, False, 'guard_terminal_run'),
        'zz_accepted_command_seal': (31, 0, None, None, False, 'guard_command_seal'),
        'accepted_command_complete': (5, 0, None, None, True, 'require_command_complete'),
    }
    expected = []
    for schema, table, name in sorted(frozen.TRIGGERS):
        kind, nargs, old, new, deferred, function = specs[name]
        argument = ('vf_run_id' if schema == 'mta_state' else 'run_id') + '\\000' if nargs else ''
        expected.append((schema, table, name, 'O', kind, nargs, argument, None, '', old, new,
                         deferred, deferred, deferred, 'mta', function))
    if actual != expected:
        raise ValueError('Accepted state trigger coverage/ownership differs')
    cursor.execute("SELECT name FROM mta.django_migrations WHERE app='fresh_mta' "
                   "AND name IN ('0169_accepted_state_ownership','0170_command_writer_compatibility') ORDER BY name")
    history = cursor.fetchall()
    if history not in ([('0169_accepted_state_ownership',)],
                       [('0169_accepted_state_ownership',), ('0170_command_writer_compatibility',)]):
        raise ValueError('Accepted state migration registration differs')
    compatibility = len(history) == 2
    if column != [('boolean', True, compatibility, '', '', 'false' if compatibility else None)]:
        raise ValueError('Accepted state seal/default contract differs')
    return True


def business_trigger_rows(cursor, rows):
    if any(row[0] in NAMES for row in rows):
        verify_guards(cursor)
        return [row for row in rows if row[0] not in NAMES]
    return rows
