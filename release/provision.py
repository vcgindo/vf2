"""Provision a NEW two-database deployment. Never reuse or reset existing targets."""
import argparse
import json
import os
import re

from release.configuration import database_options, secret


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', value):
        raise ValueError('Database and role names must be lowercase PostgreSQL identifiers')
    return value


def plan():
    databases = {key: identifier(os.environ.get(key + '_DB_NAME', 'vectorflow_' + key.lower()))
                 for key in ('MTA', 'MTO')}
    roles = {service: {kind: identifier(os.environ.get(service + '_' + kind + '_ROLE',
                'vectorflow_' + service.lower() + '_' + kind.lower()))
                for kind in ('OWNER', 'INSTALLER', 'RUNTIME')}
             for service in ('MTA', 'MTO', 'AUTH')}
    names = [name for role in roles.values() for name in role.values()]
    if (len(set(databases.values())) != 2 or len(set(names)) != 9
            or set(names) & {'fresh_namespace_registrar', 'fresh_operational_acceptor'}):
        raise ValueError('Separate database and service role identities are required')
    return dict(databases=databases, roles=roles,
                authorities=['fresh_namespace_registrar', 'fresh_operational_acceptor'])


def provision(configuration):
    import psycopg
    from psycopg import sql
    c = configuration
    connection = dict(host=os.environ.get('DB_HOST', 'postgres'),
        port=os.environ.get('DB_PORT', '5432'), dbname=os.environ.get('PG_ADMIN_DATABASE', 'postgres'),
        user=os.environ.get('PG_ADMIN_USER', 'postgres'), password=secret('PG_ADMIN_PASSWORD'),
        **database_options())
    names = [name for role in c['roles'].values() for name in role.values()] + c['authorities']
    passwords = {(service, kind): secret(service + '_' + kind + '_PASSWORD')
                 for service in c['roles'] for kind in ('INSTALLER', 'RUNTIME')}
    with psycopg.connect(**connection, autocommit=True) as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
            if cursor.fetchone() != (True,):
                raise ValueError('Explicit trusted provisioning session required')
            cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)', [list(c['databases'].values())])
            if cursor.fetchall():
                raise ValueError('A deployment database already exists; reuse/reset is prohibited')
            cursor.execute('SELECT rolname FROM pg_roles WHERE rolname=ANY(%s)', [names])
            if cursor.fetchall():
                raise ValueError('A deployment role already exists; role replacement is prohibited')
            with db.transaction():
                for role in [*[v['OWNER'] for v in c['roles'].values()], *c['authorities']]:
                    cursor.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(role)))
                for service, roles in c['roles'].items():
                    for kind in ('INSTALLER', 'RUNTIME'):
                        cursor.execute(sql.SQL('CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(roles[kind]), sql.Literal(passwords[service, kind])))
                    cursor.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(roles['OWNER']), sql.Identifier(roles['INSTALLER'])))
                cursor.execute(sql.SQL('GRANT fresh_operational_acceptor TO {}').format(sql.Identifier(c['roles']['MTA']['INSTALLER'])))
            for service in ('MTA', 'MTO'):
                cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(c['databases'][service]), sql.Identifier(c['roles'][service]['OWNER'])))
    for service in ('MTA', 'MTO'):
        with psycopg.connect(**{**connection, 'dbname': c['databases'][service]}) as db:
            with db.cursor() as cursor:
                cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(c['databases'][service])))
                services = ('MTA',) if service == 'MTA' else ('MTO', 'AUTH')
                for name in services:
                    for kind in ('INSTALLER', 'RUNTIME'):
                        cursor.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(c['databases'][service]), sql.Identifier(c['roles'][name][kind])))
                cursor.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
                # Native migrations0006/0118 create their own state/opening
                # schemas under the selected MTA owner. Do not pre-create them.
                schemas = [('mta', 'MTA')] if service == 'MTA' else [('mto', 'MTO'), ('identity', 'AUTH')]
                for schema, owner in schemas:
                    cursor.execute(sql.SQL('CREATE SCHEMA {} AUTHORIZATION {}').format(sql.Identifier(schema), sql.Identifier(c['roles'][owner]['OWNER'])))
                    cursor.execute(sql.SQL('REVOKE ALL ON SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema)))
    return dict(status='NEW_DATABASES_AND_ROLES_PROVISIONED_NO_MIGRATION_OR_INPUT_IMPORT', **c)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Explicit one-time creation; existing targets always fail')
    args = parser.parse_args()
    configuration = plan()
    print(json.dumps(provision(configuration) if args.apply else dict(status='PLAN_ONLY_NO_MUTATION', **configuration), sort_keys=True))


if __name__ == '__main__':
    main()
