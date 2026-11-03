"""Schema compatibility is independent of the currently executing application commit.

Original activation/certificate rows remain immutable producer evidence. Existing
certified schema is usable by another authenticated image with the same migration
roster. A real schema migration may append one registrar-owned schema receipt,
keyed by that migration roster, rather than a permission for every code release.
"""
import json
import re
from pathlib import Path

from mta.serialization import digest

CONTRACT = 'vectorflow-migrated-schema-v1'
FIELDS = frozenset(('contract', 'initialization_id', 'target_release', 'target_commit',
    'certification_digest', 'original_registration_digest', 'migrations',
    'applied_migrations', 'schema_digest', 'guard_digest'))


class SchemaUpgradeRequired(ValueError):
    """No schema receipt exists; distinct from corrupted ownership/receipt data."""


def native_migrations():
    """Only after complete image-owned source authentication succeeds."""
    from release.native_identity import require_current, MANIFEST
    release = require_current()
    path = Path(__file__).resolve().parents[2] / MANIFEST
    files = json.loads(path.read_bytes())['migrations']
    if digest(files) != release['migrations_digest']:
        raise ValueError('Authenticated migration roster differs')
    return files


def validate_migration_history(cursor, files, expected_digest):
    expected={Path(name).stem for name in files if Path(name).stem!='__init__'}
    applied = applied_migrations(cursor)
    actual={name for app,name in applied if app=='fresh_mta'}
    installed={name:pin for name,pin in files.items()
        if Path(name).stem=='__init__' or Path(name).stem in actual}
    if not actual <= expected or digest(installed) != expected_digest:
        raise ValueError('Applied migration history is incomplete or contains unknown migrations')
    return applied


def applied_migrations(cursor):
    cursor.execute('SELECT app,name FROM mta.django_migrations ORDER BY app,name')
    return [list(row) for row in cursor.fetchall()]


def original_activation(cursor, initialization_id):
    from mta.runtime import ingestion_authority as authority
    from mta.runtime.ingestion_admission import _certificate, _activation_metadata, registration
    cert = _certificate(initialization_id)
    body = authority.read(cursor, initialization_id, cert['release_digest'])
    original, capability = registration(cursor)
    _activation_metadata(cursor, body, certificate=cert, registered=(original, capability))
    return cert, original, capability, body


def _record(cursor, initialization_id, migration_digest):
    from mta.runtime import ingestion_authority as authority
    cursor.execute('SELECT to_regclass(%s)', [authority.SCHEMA_TABLE])
    if cursor.fetchone()[0] is None:
        return None
    authority._schema_contract(cursor)
    cursor.execute('SELECT body,receipt_digest FROM '+authority.SCHEMA_TABLE+
        ' WHERE initialization_id=%s AND target_release=%s', [initialization_id, migration_digest])
    row = cursor.fetchone()
    if row is None:
        return None
    body = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    if (type(body) is not dict or set(body) != FIELDS or body.get('contract') != CONTRACT
            or body['initialization_id'] != str(initialization_id)
            or body['target_release'] != migration_digest
            or not isinstance(body['target_commit'],str)
            or re.fullmatch('[0-9a-f]{40}',body['target_commit']) is None
            or digest(body['migrations']) != migration_digest or digest(body) != row[1]):
        raise ValueError('Schema migration receipt identity differs')
    return body


def validate(cursor, initialization_id, release):
    """Validate actual ownership/schema; never append code-release authority."""
    from mta.runtime.ingestion_admission import validate_activation, security_digest
    from release.native_schema import schema_digest
    cert, original, capability, body = original_activation(cursor, initialization_id)
    applied = validate_migration_history(cursor,native_migrations(),release['migrations_digest'])
    if release['migrations_digest'] == capability['release_identity']['migrations_digest']:
        # A compatible reader of the original schema keeps the same original
        # activation and all live schema/security checks, without a current-
        # application-manifest lookup or an inferred activation.
        return validate_activation(cursor, body)
    record = _record(cursor, initialization_id, release['migrations_digest'])
    if record is None:
        raise SchemaUpgradeRequired('Installed schema requires the explicit upgrade command')
    if (record['certification_digest'] != cert['receipt_digest']
            or record['original_registration_digest'] != digest(original)
            or record['applied_migrations'] != applied
            or record['schema_digest'] != schema_digest(cursor)
            or record['guard_digest'] != security_digest(cursor, cert['authority_roles'])):
        raise ValueError('Migrated schema, ownership or guard contract differs')
    return cert


def append(cursor, initialization_id, release):
    """Privileged schema-change checkpoint, not routine code admission.

    Caller owns the same transaction as forward migrations and has verified the
    old schema before them. Original registration/certification is not rewritten.
    """
    from mta.runtime import ingestion_authority as authority
    from mta.runtime.ingestion_admission import security_digest
    from release.native_schema import schema_digest
    authority._provisioner(cursor)
    cert, original, _capability, _body = original_activation(cursor, initialization_id)
    cursor.execute('SELECT to_regclass(%s)', [authority.SCHEMA_TABLE])
    if cursor.fetchone()[0] is None:
        authority.bootstrap_schema_transition(cursor,
            [original['owner']['name'], original['consumer']['name']])
    authority._schema_contract(cursor)
    migrations = native_migrations()
    if _record(cursor, initialization_id, digest(migrations)) is not None:
        return validate(cursor, initialization_id, release)
    body = dict(contract=CONTRACT, initialization_id=str(initialization_id),
        target_release=digest(migrations), target_commit=release['source_commit'],
        certification_digest=cert['receipt_digest'], original_registration_digest=digest(original),
        migrations=migrations, applied_migrations=applied_migrations(cursor),
        schema_digest=schema_digest(cursor), guard_digest=security_digest(cursor, cert['authority_roles']))
    # The existing protected table is reused. For this new schema-only contract,
    # target_release is the migration roster digest; source commit is provenance
    # of the DDL producer, never a requirement on later compatible reader code.
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('INSERT INTO '+authority.SCHEMA_TABLE+
        '(initialization_id,target_release,body,receipt_digest) VALUES(%s,%s,%s::jsonb,%s)',
        [initialization_id,body['target_release'],json.dumps(body),digest(body)])
    cursor.execute('RESET ROLE')
    return validate(cursor, initialization_id, release)
