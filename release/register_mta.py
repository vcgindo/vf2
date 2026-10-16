"""Register one fresh, fully migrated MTA namespace using its current source profile."""
import argparse
import json
import os
from pathlib import Path
import re
import uuid

from release.provision import plan


def render_sql(raw, values):
    # Only the committed namespace template is passed here; no operator SQL.
    from psycopg import sql
    raw = raw.replace('\\set ON_ERROR_STOP on', '')
    for key, value in values.items():
        raw = raw.replace(':"' + key + '"', sql.Identifier(value).as_string())
        raw = raw.replace(":'" + key + "'", sql.Literal(value).as_string())
    if re.search(r'(?<!:):[\"\']', raw):
        raise ValueError('Unresolved namespace template variable')
    return raw


def register(input_sha256):
    if not re.fullmatch('[0-9a-f]{64}', input_sha256):
        raise ValueError('Explicit initialization input SHA256 required')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.mta_settings')
    import django
    django.setup()
    from django.db import connection, transaction
    from mta.mdm import owned_namespace as owned
    from mta.mdm.application_registration import register_application
    from mta.mdm.initialization import current_implementation_digest
    c = plan()
    implementation = current_implementation_digest()
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database(),oid::bigint FROM pg_database WHERE datname=current_database()')
            database, oid = cursor.fetchone()
            if database != c['databases']['MTA']:
                raise ValueError('Explicit MTA installation database differs')
            cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
            if cursor.fetchone() != (True,):
                raise ValueError('Explicit trusted provisioning session required')
            cursor.execute('SELECT to_regclass(%s)', [owned.REGISTRY])
            if cursor.fetchone()[0] is not None:
                raise ValueError('Namespace already registered; replacement/repeat prohibited')
            cursor.execute('SELECT (SELECT count(*) FROM mta.fresh_mta_productioninitialization), (SELECT count(*) FROM mta.fresh_mta_mdmsource), (SELECT count(*) FROM mta.fresh_mta_calculationrun)')
            if cursor.fetchone() != (0, 0, 0):
                raise ValueError('Registration requires empty initialized/calculation ownership')
            values = dict(database_name=database, owner_role=c['roles']['MTA']['OWNER'],
                issuer_role=c['roles']['MTA']['INSTALLER'], consumer_role=c['roles']['MTA']['RUNTIME'],
                registration_id=str(uuid.uuid4()), artifact_sha256=input_sha256, adapter_sha256=implementation)
            cursor.execute(render_sql(Path(__file__).with_name('owned-namespace.sql').read_text(encoding='utf-8'), values))
            for schema in ('mta_state', 'mta_opening'):
                cursor.execute('GRANT USAGE ON SCHEMA ' + owned._quote_identifier(schema) +
                    ' TO ' + owned._quote_identifier(c['roles']['MTA']['RUNTIME']) + ',fresh_operational_acceptor')
            registration = owned._registered_identity(cursor)
            original = owned._receipt_identity(registration)
            binding = register_application(cursor, expected_database=database, expected_database_oid=oid,
                expected_registration_digest=original['registration_digest'],
                expected_original_implementation=implementation, implementation_sha256=implementation,
                production=True)
    connection.close()
    return dict(status='FRESH_CURRENT_SOURCE_CAPABILITY_REGISTERED_NO_INPUT_OR_CALCULATION',
        database=database, database_oid=oid, namespace=original['registration_id'],
        policy=binding['policy'], receipt_digest=binding['receipt_digest'], implementation_sha256=implementation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(register(args.input_sha256), sort_keys=True))


if __name__ == '__main__':
    main()
