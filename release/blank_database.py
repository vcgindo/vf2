"""Explicit blank-install database operations; never native business registration or loading.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
import os
from pathlib import Path
import sys

from release.configuration import database_options, secret
from release.provision import plan, provision


def finish():
    import psycopg
    from psycopg import sql
    from grant_service import grant
    from release.metadata_access import grant as metadata_grant
    configuration = plan()
    grant('AUTH')
    grant('MTO')
    metadata_grant()
    dbname = configuration['databases']['MTA']
    with psycopg.connect(host=os.environ.get('DB_HOST', 'postgres'),
            port=os.environ.get('DB_PORT', '5432'), dbname=dbname,
            user=os.environ.get('PG_ADMIN_USER', 'postgres'), password=secret('PG_ADMIN_PASSWORD'),
            **database_options()) as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT to_regclass('fresh_control.owned_namespace')")
            if cursor.fetchone() != (None,):
                raise ValueError('Blank installation cannot adopt a registered business namespace')
            cursor.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT LIKE 'pg_%' "
                           "AND schemaname<>'information_schema' AND tablename NOT IN ('django_migrations','django_content_type') ORDER BY 1,2")
            tables = cursor.fetchall()
            for schema, table in tables:
                cursor.execute(sql.SQL('SELECT EXISTS(SELECT 1 FROM {}.{})').format(sql.Identifier(schema), sql.Identifier(table)))
                if cursor.fetchone() != (False,):
                    raise ValueError('Blank installation has business rows: ' + schema + '.' + table)
            for kind in ('RUNTIME', 'INSTALLER'):
                for setting, value in [('idle_in_transaction_session_timeout', '300s'), ('statement_timeout', '300s'), ('lock_timeout', '5s')]:
                    cursor.execute(sql.SQL('ALTER ROLE {} IN DATABASE {} SET {} TO {}').format(
                        sql.Identifier(configuration['roles']['MTA'][kind]), sql.Identifier(dbname),
                        sql.Identifier(setting), sql.Literal(value)))
    identity = json.loads(Path('/opt/vectorflow/release.json').read_text())
    result = dict(status='BLANK_DATABASES_SCHEMA_GRANTS_VERIFIED', business_registration=False,
                  business_rows=0, checked_tables=len(tables), source_commit=identity['source_commit'])
    receipt = Path('/receipts/database.json')
    with receipt.open('x') as stream:
        json.dump(result, stream, sort_keys=True)
    return result


if __name__ == '__main__':
    operation = sys.argv[1]
    if operation == 'provision':
        result = provision(plan())
    elif operation == 'finish':
        result = finish()
    else:
        raise ValueError('Unknown blank installation operation')
    print(json.dumps(result, sort_keys=True))
