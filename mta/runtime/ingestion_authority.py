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


# This relation is registrar metadata, not a replacement data certificate.
# Its DDL is installed only by the explicit maintenance transition, atomically
# with the reviewed migrations and final release append.
SCHEMA_TABLE = 'fresh_control.ingestion_schema_compatibility'
SCHEMA_CONTRACT = 'vectorflow-ingestion-schema-transition-v1'
SCHEMA_FIELDS = frozenset(('contract','initialization_id','target_release','target_commit',
    'previous_release','previous_authority_digest','certification_digest',
    'before_schema_digest','before_guard_digest','schema_digest','guard_digest',
    'migration_pins','catalogue_delta_digest','preservation_digest'))
CODE_SCHEMA_CONTRACT='fresh-code-schema-inheritance-v1'
CODE_SCHEMA_FIELDS=frozenset(('contract','initialization_id','target_release','target_commit',
    'anchor_release','anchor_authority_digest','anchor_schema_receipt_digest',
    'certification_digest','schema_digest','guard_digest','migration_pins','catalogue_delta_digest'))


def _schema_contract(cursor):
    """Check registrar ownership, exact columns, append guard and finite ACLs."""
    cursor.execute("SELECT pg_get_userbyid(c.relowner),pg_get_userbyid(n.nspowner) "
        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=to_regclass(%s)", [SCHEMA_TABLE])
    if cursor.fetchone() != (REGISTRAR,REGISTRAR):
        raise ValueError('Schema compatibility requires independent registrar ownership')
    cursor.execute("SELECT column_name,data_type,is_nullable FROM information_schema.columns "
        "WHERE table_schema='fresh_control' AND table_name='ingestion_schema_compatibility' ORDER BY ordinal_position")
    if cursor.fetchall() != [('initialization_id','uuid','NO'),('target_release','character varying','NO'),
                            ('body','jsonb','NO'),('receipt_digest','character varying','NO')]:
        raise ValueError('Schema compatibility relation shape differs')
    cursor.execute("SELECT t.tgenabled,t.tgtype,t.tgnargs,t.tgqual::text,p.prosrc,p.prosecdef,"
        "p.proconfig,pg_get_userbyid(p.proowner),pn.nspname,p.proname "
        "FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace pn ON pn.oid=p.pronamespace "
        "WHERE t.tgrelid=to_regclass(%s) AND NOT t.tgisinternal", [SCHEMA_TABLE])
    rows=cursor.fetchall()
    if (len(rows)!=1 or rows[0][:4] != ('O',58,0,None)
            or rows[0][4].strip() != "BEGIN\n      RAISE EXCEPTION 'Ingestion release authority is append-only'; END"
            or rows[0][5:] != (False,['search_path=pg_catalog'],REGISTRAR,'fresh_control','ingestion_transition_immutable')):
        raise ValueError('Schema compatibility append-only guard differs')
    cursor.execute("SELECT a.grantee::bigint,a.privilege_type,a.is_grantable,pg_get_userbyid(a.grantee) "
        "FROM pg_class c CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a "
        "WHERE c.oid=to_regclass(%s)", [SCHEMA_TABLE])
    for grantee,privilege,grantable,name in cursor.fetchall():
        if grantee==0 or grantable or (name != REGISTRAR and privilege != 'SELECT'):
            raise ValueError('Schema compatibility writer privilege differs')


def bootstrap_schema_transition(cursor, readers):
    _provisioner(cursor)
    cursor.execute('SELECT to_regclass(%s)',[SCHEMA_TABLE])
    if cursor.fetchone()[0] is not None:
        raise ValueError('Schema compatibility already installed; replacement prohibited')
    from psycopg import sql
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('''CREATE TABLE fresh_control.ingestion_schema_compatibility (
      initialization_id uuid NOT NULL,target_release varchar(64) NOT NULL,
      body jsonb NOT NULL CHECK(octet_length(body::text)<=65536),
      receipt_digest varchar(64) NOT NULL,
      PRIMARY KEY(initialization_id,target_release))''')
    cursor.execute('CREATE TRIGGER ingestion_schema_transition_immutable BEFORE UPDATE OR DELETE OR TRUNCATE '
        'ON fresh_control.ingestion_schema_compatibility FOR EACH STATEMENT '
        'EXECUTE FUNCTION fresh_control.ingestion_transition_immutable()')
    cursor.execute('REVOKE ALL ON fresh_control.ingestion_schema_compatibility FROM PUBLIC')
    for role in readers:
        cursor.execute(sql.SQL('GRANT SELECT ON fresh_control.ingestion_schema_compatibility TO {}').format(sql.Identifier(role)))
    cursor.execute('RESET ROLE')
    _schema_contract(cursor)


def validate_schema_transition(body):
    if type(body) is not dict or set(body)!=SCHEMA_FIELDS or body['contract']!=SCHEMA_CONTRACT:
        raise ValueError('Exact schema transition receipt required')
    if str(UUID(body['initialization_id']))!=body['initialization_id']:
        raise ValueError('Canonical schema transition initialization required')
    import re
    if type(body['target_commit']) is not str or not re.fullmatch('[0-9a-f]{40}',body['target_commit']):
        raise ValueError('Exact schema transition source commit required')
    for key in SCHEMA_FIELDS - {'contract','initialization_id','target_commit','migration_pins'}:
        sha(body[key])
    pins=body['migration_pins']
    if type(pins) is not list or not pins or any(type(p) is not list or len(p)!=2 for p in pins):
        raise ValueError('Ordered migration byte pins required')
    if len({p[0] for p in pins})!=len(pins):
        raise ValueError('Duplicate migration pin')
    for name,pin in pins:
        if type(name) is not str or not (re.fullmatch(r'01[0-9]{2}_[a-z0-9_]+',name)
                or name in ('0222_recovered_scope_actions', '0223_bpr_history_completion',
                    '0224_uptodbm_bpr_read_configuration','0225_scope_read_configuration_alias',
                    '0226_scoped_dbm_action_dependencies','0227_scope_read_action_reference',
                    '0228_scope_read_action_ownership','0229_runtime_report_publication',
                    '0230_runtime_report_publication_guards','0231_runtime_report_placement_guards',
                    '0232_runtime_report_consumer_read','0233_report_definition_registration',
                    '0234_report_definition_guards','0235_registered_scope_read_attachment',
                    '0236_intake_diagnostic_custody','0237_intake_diagnostic_guards')):
            raise ValueError('Invalid schema transition migration name')
        sha(pin)
    return body


def append_schema_transition(cursor, body):
    _provisioner(cursor);_schema_contract(cursor);validate_schema_transition(body)
    # Canonical live schema/security checks also happen before the final release
    # append. This insertion alone never activates runtime admission.
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('INSERT INTO fresh_control.ingestion_schema_compatibility '
        '(initialization_id,target_release,body,receipt_digest) VALUES(%s,%s,%s::jsonb,%s)',
        [body['initialization_id'],body['target_release'],json.dumps(body),digest(body)])
    cursor.execute('RESET ROLE')


def read_schema_transition(cursor, activation):
    cursor.execute('SELECT to_regclass(%s)',[SCHEMA_TABLE])
    if cursor.fetchone()[0] is None:return None
    _schema_contract(cursor)
    cursor.execute('SELECT body,receipt_digest FROM fresh_control.ingestion_schema_compatibility '
        'WHERE initialization_id=%s AND target_release=%s',
        [activation['initialization_id'],activation['target_release']])
    row=cursor.fetchone()
    if row is None:return None
    body=json.loads(row[0]) if isinstance(row[0],str) else row[0]
    if body.get('contract')==CODE_SCHEMA_CONTRACT:
        validate_code_schema(body)
    else:
        validate_schema_transition(body)
    if (digest(body)!=row[1] or body['initialization_id']!=activation['initialization_id']
            or body['target_release']!=activation['target_release']):
        raise ValueError('Schema transition row identity differs')
    return body


def validate_code_schema(body):
    import re
    if type(body) is not dict or set(body)!=CODE_SCHEMA_FIELDS or body['contract']!=CODE_SCHEMA_CONTRACT:
        raise ValueError('Exact code-only schema inheritance required')
    if str(UUID(body['initialization_id']))!=body['initialization_id']:
        raise ValueError('Canonical code-only initialization required')
    if type(body['target_commit']) is not str or not re.fullmatch('[0-9a-f]{40}',body['target_commit']):
        raise ValueError('Exact code-only source commit required')
    for key in CODE_SCHEMA_FIELDS-{'contract','initialization_id','target_commit','migration_pins'}:
        sha(body[key])
    if (body['target_release']==body['anchor_release'] or body['migration_pins']!=[]
            or body['catalogue_delta_digest']!=digest({})):
        raise ValueError('Code-only inheritance cannot change schema or reference itself')
    return body


def inherit_code_schema(cursor,activation,predecessor):
    """Provisioner-only direct link to authenticated effective schema, no DDL."""
    _provisioner(cursor);validate(activation)
    from mta.runtime.ingestion_admission import effective_schema
    cert,anchor,schema,guard,anchor_receipt=effective_schema(cursor,predecessor)
    if any(activation[k]!=predecessor[k] for k in FIELDS-{'target_commit','target_release'}):
        raise ValueError('Code-only promotion changed original ownership')
    # effective_schema authenticates the chain; the predecessor must also
    # still match the actual live catalogue/security, never caller digests.
    from mta.runtime.ingestion_admission import validate_activation
    validate_activation(cursor,predecessor)
    cursor.execute('SELECT to_regclass(%s)',[SCHEMA_TABLE])
    if cursor.fetchone()[0] is None:
        # Original installations without extensions need no extra catalogue
        # receipt and retain their existing certificate-only admission path.
        return None
    _schema_contract(cursor)
    body=validate_code_schema(dict(contract=CODE_SCHEMA_CONTRACT,
        initialization_id=activation['initialization_id'],target_release=activation['target_release'],
        target_commit=activation['target_commit'],anchor_release=anchor['target_release'],
        anchor_authority_digest=digest(anchor),anchor_schema_receipt_digest=anchor_receipt,
        certification_digest=cert['receipt_digest'],schema_digest=schema,guard_digest=guard,
        migration_pins=[],catalogue_delta_digest=digest({})))
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('INSERT INTO fresh_control.ingestion_schema_compatibility '
        '(initialization_id,target_release,body,receipt_digest) VALUES(%s,%s,%s::jsonb,%s)',
        [body['initialization_id'],body['target_release'],json.dumps(body),digest(body)])
    cursor.execute('RESET ROLE')
    return body
