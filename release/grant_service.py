"""Grant runtime CRUD only inside the separately owned MTO or identity schema."""
import argparse
import json
import os
from release.configuration import database_options, secret
from release.provision import plan


def grant(service):
    import psycopg
    from psycopg import sql
    c = plan()
    if service not in ('MTO', 'AUTH'):
        raise ValueError('MTA grants require its strict current-source capability registration')
    schema = 'mto' if service == 'MTO' else 'identity'
    role = c['roles'][service]
    with psycopg.connect(host=os.environ.get('DB_HOST', 'postgres'),
            port=os.environ.get('DB_PORT', '5432'), dbname=c['databases']['MTO'],
            user=os.environ.get('PG_ADMIN_USER', 'postgres'), password=secret('PG_ADMIN_PASSWORD'),
            **database_options()) as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
            if cursor.fetchone() != (True,):
                raise ValueError('Trusted provisioning session required')
            cursor.execute('SELECT r.rolname FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE n.nspname=%s', [schema])
            if cursor.fetchone() != (role['OWNER'],):
                raise ValueError('Service schema owner differs')
            cursor.execute('SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname=%s AND r.rolname<>%s', [schema, role['OWNER']])
            if cursor.fetchall():
                raise ValueError('Service object ownership differs')
            cursor.execute(sql.SQL('REVOKE ALL ON SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema)))
            cursor.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema)))
            cursor.execute(sql.SQL('REVOKE ALL ON ALL SEQUENCES IN SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema)))
            cursor.execute(sql.SQL('REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema)))
            cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role['RUNTIME'])))
            cursor.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role['RUNTIME'])))
            cursor.execute(sql.SQL('GRANT USAGE ON ALL SEQUENCES IN SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role['RUNTIME'])))
    return dict(status='SERVICE_RUNTIME_GRANTS_INSTALLED_NO_DATA_IMPORT', service=service,
        database=c['databases']['MTO'], schema=schema, runtime_role=role['RUNTIME'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service', choices=('MTO', 'AUTH'))
    print(json.dumps(grant(parser.parse_args().service), sort_keys=True))
