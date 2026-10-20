"""Registrar-owned release transitions; application metadata cannot activate them.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
from uuid import UUID
from mta.serialization import digest
from mta.runtime.ingestion_context import CONTRACT, sha

REGISTRAR = 'fresh_namespace_registrar'
TABLE = 'fresh_control.ingestion_release_authority'
FIELDS = frozenset(('contract', 'initialization_id', 'namespace', 'database_name', 'database_oid',
    'source_digest', 'original_registration_digest', 'original_capability_digest',
    'original_commit', 'original_release', 'target_commit', 'target_release',
    'certification_digest', 'schema_digest', 'guard_digest'))


def validate(body):
    import re
    if type(body) is not dict or set(body) != FIELDS or body['contract'] != CONTRACT:
        raise ValueError('Exact ingestion release authority contract required')
    for key in ('initialization_id', 'namespace'):
        if str(UUID(body[key])) != body[key]:
            raise ValueError('Canonical authority UUID required')
    for key in ('original_commit', 'target_commit'):
        if type(body[key]) is not str or not re.fullmatch('[0-9a-f]{40}', body[key]):
            raise ValueError('Exact original and target commits required')
    for key in FIELDS - {'contract', 'initialization_id', 'namespace', 'database_name',
                         'database_oid', 'original_commit', 'target_commit'}:
        sha(body[key])
    if (type(body['database_oid']) is not int or body['database_oid'] <= 0
            or type(body['database_name']) is not str or not 1 <= len(body['database_name']) <= 63):
        raise ValueError('Exact database identity required')
    return body


def _provisioner(cursor):
    cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
    if cursor.fetchone() != (True,):
        raise ValueError('Explicit trusted provisioning session required')
    cursor.execute('SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolinherit '
        'FROM pg_roles WHERE rolname=%s', [REGISTRAR])
    if cursor.fetchone() != (False,) * 7:
        raise ValueError('Original restricted namespace registrar required')


def bootstrap(cursor, readers):
    """Installation/upgrade primitive, never called automatically by readiness.

    Caller owns an atomic provisioning transaction. No role creation/membership,
    old namespace/capability rewrite, implicit migration or business DML.
    """
    _provisioner(cursor)
    cursor.execute("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='fresh_control'")
    row = cursor.fetchone()
    if row != (REGISTRAR,):
        raise ValueError('Existing registrar-owned namespace required')
    cursor.execute('SELECT to_regclass(%s)', [TABLE])
    if cursor.fetchone()[0] is not None:
        raise ValueError('Release authority already installed; replacement prohibited')
    from psycopg import sql
    # PostgreSQL names are identifiers, never interpolated operator SQL.
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('''CREATE TABLE fresh_control.ingestion_release_authority (
      initialization_id uuid NOT NULL, target_release varchar(64) NOT NULL,
      body jsonb NOT NULL CHECK (octet_length(body::text)<=65536),
      receipt_digest varchar(64) NOT NULL,
      PRIMARY KEY(initialization_id,target_release))''')
    cursor.execute('''CREATE FUNCTION fresh_control.ingestion_transition_immutable() RETURNS trigger
      LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
      RAISE EXCEPTION 'Ingestion release authority is append-only'; END $$''')
    cursor.execute('''CREATE TRIGGER ingestion_transition_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
      ON fresh_control.ingestion_release_authority FOR EACH STATEMENT
      EXECUTE FUNCTION fresh_control.ingestion_transition_immutable()''')
    cursor.execute('REVOKE ALL ON fresh_control.ingestion_release_authority FROM PUBLIC')
    cursor.execute('REVOKE ALL ON FUNCTION fresh_control.ingestion_transition_immutable() FROM PUBLIC')
    for role in readers:
        cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA fresh_control TO {}').format(sql.Identifier(role)))
        cursor.execute(sql.SQL('GRANT SELECT ON fresh_control.ingestion_release_authority TO {}').format(sql.Identifier(role)))
    cursor.execute('RESET ROLE')


def append(cursor, body):
    """Activate last, after exhaustive certification and exact transition review.

    This primitive grants no compatibility inference. The operator must call
    validate_activation first in the same provisioning transaction.
    """
    _provisioner(cursor)
    validate(body)
    from mta.runtime.ingestion_admission import validate_activation
    validate_activation(cursor, body)
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('INSERT INTO fresh_control.ingestion_release_authority '
        '(initialization_id,target_release,body,receipt_digest) VALUES (%s,%s,%s::jsonb,%s)',
        [body['initialization_id'], body['target_release'], json.dumps(body), digest(body)])
    cursor.execute('RESET ROLE')


def read(cursor, initialization_id, target_release):
    cursor.execute('SELECT body,receipt_digest FROM fresh_control.ingestion_release_authority '
        'WHERE initialization_id=%s AND target_release=%s', [initialization_id, target_release])
    row = cursor.fetchone()
    if row is None:
        raise ValueError('Certified release transition is absent')
    body = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    validate(body)
    if (digest(body) != row[1] or body['initialization_id'] != str(initialization_id)
            or body['target_release'] != target_release):
        raise ValueError('Certified release authority digest differs')
    return body
