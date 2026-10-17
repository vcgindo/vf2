"""Finite installation metadata access; never business initialization or admission.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import argparse
import json
import os

from release.provision import plan

# Exact read-only installation footprint. No business reader/writer grants.
TABLES = ('django_migrations', 'fresh_mta_productioninitialization',
          'fresh_mta_mdmsource', 'fresh_mta_calculationrun',
          'fresh_mta_userreportlayout')


def validate_owner(cursor, owner):
    cursor.execute("SELECT d.datname,o.rolname,o.rolcanlogin,o.rolsuper,o.rolcreatedb,"
                   "o.rolcreaterole,o.rolreplication,o.rolbypassrls "
                   "FROM pg_database d JOIN pg_roles o ON o.oid=d.datdba "
                   "WHERE d.datname=current_database()")
    row = cursor.fetchone()
    if not row or row[1:] != (owner, False, False, False, False, False, False):
        raise ValueError('Installation database ownership differs')
    cursor.execute("SELECT r.rolname FROM pg_namespace n JOIN pg_roles r "
                   "ON r.oid=n.nspowner WHERE n.nspname='mta'")
    if cursor.fetchone() != (owner,):
        raise ValueError('Installation schema ownership differs')
    cursor.execute("SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                   "JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='mta' AND r.rolname<>%s", [owner])
    if cursor.fetchall():
        raise ValueError('Installation object ownership differs')


def validate_read_profile(cursor, owner, runtime):
    validate_owner(cursor, owner)
    cursor.execute("SELECT current_user,session_user,rolcanlogin,rolsuper,rolcreatedb,"
                   "rolcreaterole,rolinherit,rolreplication,rolbypassrls "
                   "FROM pg_roles WHERE rolname=current_user")
    if cursor.fetchone() != (runtime, runtime, True, False, False, False, False, False, False):
        raise ValueError('Installation runtime role differs')
    cursor.execute("SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)")
    if cursor.fetchall():
        raise ValueError('Installation runtime must not inherit roles')
    cursor.execute("SELECT has_database_privilege(current_database(),'CREATE'),"
                   "has_database_privilege(current_database(),'TEMP')")
    if cursor.fetchone() != (False, False):
        raise ValueError('Installation runtime database privilege differs')
    cursor.execute("SELECT n.nspname,c.relname,p.privilege FROM pg_class c "
                   "JOIN pg_namespace n ON n.oid=c.relnamespace "
                   "CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),('TRIGGER')) p(privilege) "
                   "WHERE c.relkind IN ('r','p','v','m','f') "
                   "AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' "
                   "AND has_table_privilege(c.oid,p.privilege) ORDER BY 1,2,3")
    if set(cursor.fetchall()) != {('mta', name, 'SELECT') for name in TABLES}:
        raise ValueError('Installation runtime read privilege roster differs')
    cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' "
                   "AND has_schema_privilege(oid,'CREATE')")
    if cursor.fetchall():
        raise ValueError('Installation runtime schema creation is forbidden')
    cursor.execute("SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                   "WHERE c.relkind='S' AND n.nspname NOT IN ('pg_catalog','information_schema') "
                   "AND (has_sequence_privilege(c.oid,'USAGE') OR has_sequence_privilege(c.oid,'UPDATE') "
                   "OR has_sequence_privilege(c.oid,'SELECT'))")
    if cursor.fetchall():
        raise ValueError('Installation runtime sequence privileges are forbidden')
    cursor.execute("SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                   "WHERE p.prosecdef AND n.nspname NOT IN ('pg_catalog','information_schema') "
                   "AND has_schema_privilege(n.oid,'USAGE') AND has_function_privilege(p.oid,'EXECUTE')")
    if cursor.fetchall():
        raise ValueError('Installation runtime privileged function execution is forbidden')


def grant():
    """Explicit NEW unregistered target only; never amend a sealed registration."""
    import psycopg
    from psycopg import sql
    from release.configuration import database_options, secret
    c = plan()
    with psycopg.connect(host=os.environ.get('DB_HOST', 'postgres'),
            port=os.environ.get('DB_PORT', '5432'), dbname=c['databases']['MTA'],
            user=os.environ.get('PG_ADMIN_USER', 'postgres'), password=secret('PG_ADMIN_PASSWORD'),
            **database_options()) as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
            if cursor.fetchone() != (True,):
                raise ValueError('Trusted provisioning session required')
            validate_owner(cursor, c['roles']['MTA']['OWNER'])
            cursor.execute("SELECT to_regclass('fresh_control.owned_namespace')")
            if cursor.fetchone()[0] is not None:
                raise ValueError('Registered target is immutable; metadata grant refused')
            for table in TABLES[1:4]:
                cursor.execute(sql.SQL('SELECT EXISTS(SELECT 1 FROM mta.{})').format(sql.Identifier(table)))
                if cursor.fetchone() != (False,):
                    raise ValueError('Metadata installation requires untouched business state')
            role = sql.Identifier(c['roles']['MTA']['RUNTIME'])
            cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA mta TO {}').format(role))
            for table in TABLES:
                cursor.execute(sql.SQL('GRANT SELECT ON mta.{} TO {}').format(sql.Identifier(table), role))
    return dict(status='FINITE_INSTALLATION_METADATA_READ_GRANTS', tables=list(TABLES),
                database=c['databases']['MTA'], runtime=c['roles']['MTA']['RUNTIME'], business_import=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(grant() if args.apply else dict(status='INSPECT_ONLY', tables=list(TABLES)), sort_keys=True))
