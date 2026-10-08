"""Create and populate only the owned Cohort3 identity schema, with real migrations."""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tools.cohort3_settings')

import django
django.setup()

from django.core import serializers
from django.core.management import call_command
from django.core.management.color import no_style
from django.db import connections, transaction
from django.db.models import Q

from api.models import (
    ApplicationMaster, Permission, Roles, User,
    User_Application_Location_Permission as LocationGrant,
    User_Application_Product_Permission as ProductGrant,
)


DATABASE = 'fresh_complete'
SCHEMA = 'cohort3_identity'
MARKER = 'cohort3_identity_owner'
VERSION = 'cohort3-identity-v1'
ACTORS = {2: 'stage2.broad@vectorflow.local', 3: 'stage2.restricted@vectorflow.local'}
PRODUCTS = {(2, 2, 71001), (3, 2, 71003)}
LOCATIONS = {(2, 2, 72001), (3, 2, 72003)}
ROLE = dict(name='Cohort3 Pick download reader 20261009',
            code='Cohort3PickDownloadReader',
            description='Isolated Cohort3 Pick download proof only',
            application_id=2, is_visible=False)
FUNCTION = dict(name='Cohort3 MTA report downloads 20261009',
                code='mta-report-urls',
                description='Isolated Cohort3 Pick download proof only',
                url='mta-report-urls')


def _validate_payload(raw_text):
    value = json.loads(raw_text)
    if not isinstance(value, list):
        raise ValueError('Private identity export is not a serialized object list')
    users = {item['pk']: item['fields'] for item in value if item.get('model') == 'api.user'}
    if ({key: fields.get('email') for key, fields in users.items()} != ACTORS or
            any(not fields.get('is_active') or fields.get('is_admin') or fields.get('is_deleted')
                for fields in users.values())):
        raise ValueError('Private export does not contain the exact current3006 actors')
    passwords = {key: fields.get('password') for key, fields in users.items()}
    if any(not isinstance(value, str) or not value for value in passwords.values()):
        raise ValueError('Private export omits an actor password hash')
    products = {(item['fields']['user_id'], item['fields']['application_id'],
                 item['fields']['productfilter_id']) for item in value
                if item.get('model') == 'api.user_application_product_permission'
                and item['fields']['application_id'] == 2}
    locations = {(item['fields']['user_id'], item['fields']['application_id'],
                  item['fields']['locationfilter_id']) for item in value
                 if item.get('model') == 'api.user_application_location_permission'
                 and item['fields']['application_id'] == 2}
    if products != PRODUCTS or locations != LOCATIONS:
        raise ValueError('Private export is stale or lacks the current3006 MTA scope rebinding')
    if any(item.get('model') == 'api.permission' and
           item.get('fields', {}).get('url') == 'mta-report-urls' for item in value):
        raise ValueError('Retained actor contract unexpectedly includes download entitlement')
    return passwords


def _guard_database():
    default = connections['default']
    identity = connections['identity']
    with default.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        default_name = cursor.fetchone()[0]
    with identity.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        identity_name = cursor.fetchone()[0]
    if (default_name, identity_name) != (DATABASE, DATABASE):
        raise ValueError('Cohort3 bootstrap requires the owned fresh_complete database')


def _ensure_schema(source_sha256):
    connection = connections['identity']
    quote = connection.ops.quote_name
    with transaction.atomic(using='identity'), connection.cursor() as cursor:
        cursor.execute('SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s)', [SCHEMA])
        exists = cursor.fetchone()[0]
        if not exists:
            cursor.execute('CREATE SCHEMA ' + quote(SCHEMA))
            cursor.execute('''CREATE TABLE cohort3_identity.cohort3_identity_owner
                (singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
                 version text NOT NULL, source_sha256 char(64) NOT NULL,
                 completed boolean NOT NULL DEFAULT false)''')
            cursor.execute('''INSERT INTO cohort3_identity.cohort3_identity_owner
                (singleton,version,source_sha256,completed) VALUES(true,%s,%s,false)''',
                [VERSION, source_sha256])
        else:
            cursor.execute('SELECT to_regclass(%s)', [SCHEMA + '.' + MARKER])
            if cursor.fetchone()[0] is None:
                raise ValueError('Existing cohort3_identity schema has no ownership marker')
            cursor.execute('SELECT version,source_sha256,completed FROM '
                           + quote(SCHEMA) + '.' + quote(MARKER) + ' WHERE singleton=true')
            row = cursor.fetchone()
            if row is None or row[:2] != (VERSION, source_sha256):
                raise ValueError('Existing Cohort3 identity ownership marker differs')
            return bool(row[2])
    return False


def _migrate_identity():
    # These are the repository's actual migration modules. The router denies
    # api/auth/contenttypes on default and every non-identity app on identity.
    call_command('migrate', 'contenttypes', database='identity', interactive=False, verbosity=1)
    call_command('migrate', 'auth', database='identity', interactive=False, verbosity=1)
    call_command('migrate', 'api', database='identity', interactive=False, verbosity=1)


def _contracts():
    actors = {(row['id'], row['email'], row['is_active'], row['is_admin']) for row in
              User.all_objects.using('identity').filter(id__in=ACTORS).values(
                  'id', 'email', 'is_active', 'is_admin')}
    products = set(ProductGrant.objects.using('identity').filter(application_id=2).values_list(
        'user_id', 'application_id', 'productfilter_id'))
    locations = set(LocationGrant.objects.using('identity').filter(application_id=2).values_list(
        'user_id', 'application_id', 'locationfilter_id'))
    return actors, products, locations


def _verify_source_contract(passwords):
    actors, products, locations = _contracts()
    expected_actors = {(key, email, True, False) for key, email in ACTORS.items()}
    if actors != expected_actors or products != PRODUCTS or locations != LOCATIONS:
        raise ValueError('Imported identity actor or current3006 scope contract differs')
    if User.all_objects.using('identity').count() != 2:
        raise ValueError('Cohort3 identity schema contains an unapproved actor')
    if dict(User.all_objects.using('identity').values_list('pk', 'password')) != passwords:
        raise ValueError('Imported actor password hashes differ from the retained contract')
    if not ApplicationMaster.objects.using('identity').filter(application_id=2).exists():
        raise ValueError('MTA application2 identity is absent')


def _install_contract(raw_text):
    if User.all_objects.using('identity').exists():
        return
    objects = list(serializers.deserialize('json', raw_text))
    with transaction.atomic(using='identity'):
        for item in objects:
            item.save(using='identity')
        models = list({type(item.object) for item in objects})
        with connections['identity'].cursor() as cursor:
            for statement in connections['identity'].ops.sequence_reset_sql(no_style(), models):
                cursor.execute(statement)


def _install_download_entitlement():
    with transaction.atomic(using='identity'):
        role, created = Roles.objects.using('identity').get_or_create(
            name=ROLE['name'], defaults={key: value for key, value in ROLE.items() if key != 'name'})
        if not created and any(getattr(role, key) != value for key, value in ROLE.items()):
            raise ValueError('Existing Cohort3-only role differs')
        conflicts = Permission.objects.using('identity').filter(
            Q(name=FUNCTION['name']) | Q(url=FUNCTION['url']))
        permission = conflicts.first()
        if permission is None:
            permission = Permission.objects.using('identity').create(**FUNCTION)
        elif conflicts.count() != 1 or any(getattr(permission, key) != value
                                            for key, value in FUNCTION.items()):
            raise ValueError('Existing Cohort3 download permission differs')
        role.user_id.set([User.all_objects.using('identity').get(pk=2)])
        permission.role_id.set([role])
        if role.user_id.filter(pk=3).exists():
            raise ValueError('Restricted actor received the Cohort3 download role')


def _verify_final(passwords):
    _verify_source_contract(passwords)
    role = Roles.objects.using('identity').get(name=ROLE['name'])
    permission = Permission.objects.using('identity').get(url='mta-report-urls')
    if (set(role.user_id.values_list('pk', flat=True)) != {2} or
            set(permission.role_id.values_list('pk', flat=True)) != {role.pk}):
        raise ValueError('Cohort3 download entitlement assignment differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity-json', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    if len(args.source_sha256) != 64:
        raise ValueError('Exact source SHA256 is required')
    raw = args.identity_json.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.source_sha256:
        raise ValueError('Private identity export SHA256 differs')
    raw_text = raw.decode('utf-8')
    passwords = _validate_payload(raw_text)
    _guard_database()
    completed = _ensure_schema(args.source_sha256)
    _migrate_identity()
    if not completed:
        _install_contract(raw_text)
        _verify_source_contract(passwords)
        _install_download_entitlement()
        _verify_final(passwords)
        with transaction.atomic(using='identity'), connections['identity'].cursor() as cursor:
            cursor.execute('''UPDATE cohort3_identity.cohort3_identity_owner
                SET completed=true WHERE singleton=true AND version=%s AND source_sha256=%s''',
                [VERSION, args.source_sha256])
            if cursor.rowcount != 1:
                raise ValueError('Cohort3 identity completion marker update failed')
    _verify_final(passwords)
    print(json.dumps({'status': 'COHORT3_IDENTITY_READY', 'database': DATABASE,
                      'schema': SCHEMA, 'source_sha256': args.source_sha256,
                      'actors': sorted(ACTORS), 'broad_download_entitled': 2,
                      'restricted_download_denied': 3}))


if __name__ == '__main__':
    main()
