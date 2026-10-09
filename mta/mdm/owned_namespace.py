"""Provisioner-owned identity guard for a fresh MDM database namespace.

The registry is deliberately outside Django migrations: the database owner being
checked must not be able to mint its own ownership assertion.  Existing 3006 and
the repository test database retain their historical installer path.
"""
from django.db import connection

from mta.serialization import digest


POLICY = 'fresh-owned-mdm-namespace-v1'
LEGACY_DATABASES = frozenset(('daily_3006', 'test_freshvcf'))
REGISTRY = 'fresh_control.owned_namespace'
REGISTRAR_ROLE = 'fresh_namespace_registrar'
ACCEPTOR_ROLE = 'fresh_operational_acceptor'
_ROLE_FIELDS = ('oid', 'name', 'can_login', 'superuser', 'create_db',
                'create_role', 'replication', 'bypass_rls')


def _reject(reason):
    raise ValueError('Fresh owned namespace ' + reason)


def _quote_identifier(value):
    """Quote a server-derived PostgreSQL identifier; never accept caller text."""
    return '"' + value.replace('"', '""') + '"'


def _role(values):
    return dict(zip(_ROLE_FIELDS, values, strict=True))


def _database_identity(cursor):
    cursor.execute("""
        SELECT d.oid::bigint,d.datname::text,
               o.oid::bigint,o.rolname,o.rolcanlogin,o.rolsuper,o.rolcreatedb,
               o.rolcreaterole,o.rolreplication,o.rolbypassrls,
               cu.oid::bigint,su.oid::bigint
          FROM pg_catalog.pg_database d
          JOIN pg_catalog.pg_roles o ON o.oid=d.datdba
          JOIN pg_catalog.pg_roles cu ON cu.rolname=current_user
          JOIN pg_catalog.pg_roles su ON su.rolname=session_user
         WHERE d.datname=current_database()
    """)
    row = cursor.fetchone()
    if row is None:
        _reject('database catalogue identity is absent')
    return dict(oid=row[0], name=row[1], owner=_role(row[2:10]),
                current_user_oid=row[10], session_user_oid=row[11])


def _registered_identity(cursor):
    cursor.execute("SELECT pg_catalog.to_regclass(%s)::text", [REGISTRY])
    row = cursor.fetchone()
    if row is None or row[0] is None:
        _reject('registration is absent')
    cursor.execute("""
        SELECT r.registration_id::text,r.policy,r.database_oid::bigint,
               r.database_name::text,r.owner_oid::bigint,r.issuer_oid::bigint,
               r.consumer_oid::bigint,r.acceptor_oid::bigint,
               r.artifact_sha256,r.adapter_sha256,
               o.rolname,o.rolcanlogin,o.rolsuper,o.rolcreatedb,o.rolcreaterole,
               o.rolreplication,o.rolbypassrls,
               i.rolname,i.rolcanlogin,i.rolsuper,i.rolcreatedb,i.rolcreaterole,
               i.rolreplication,i.rolbypassrls,
               c.rolname,c.rolcanlogin,c.rolsuper,c.rolcreatedb,c.rolcreaterole,
               c.rolreplication,c.rolbypassrls,
               a.rolname,a.rolcanlogin,a.rolsuper,a.rolcreatedb,a.rolcreaterole,
               a.rolreplication,a.rolbypassrls,
               z.oid::bigint,z.rolname,z.rolcanlogin,z.rolsuper,z.rolcreatedb,
               z.rolcreaterole,z.rolreplication,z.rolbypassrls
          FROM fresh_control.owned_namespace r
          JOIN pg_catalog.pg_roles o ON o.oid=r.owner_oid
          JOIN pg_catalog.pg_roles i ON i.oid=r.issuer_oid
          JOIN pg_catalog.pg_roles c ON c.oid=r.consumer_oid
          JOIN pg_catalog.pg_roles a ON a.oid=r.acceptor_oid
          JOIN pg_catalog.pg_class t ON t.oid='fresh_control.owned_namespace'::regclass
          JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace AND n.nspname='fresh_control'
          JOIN pg_catalog.pg_roles z ON z.oid=t.relowner AND z.oid=n.nspowner
         WHERE r.singleton IS TRUE
    """)
    rows = cursor.fetchall()
    if len(rows) != 1:
        _reject('requires exactly one registration')
    row = rows[0]
    return dict(registration_id=row[0], policy=row[1], database_oid=row[2],
                database_name=row[3], owner_oid=row[4], issuer_oid=row[5],
                consumer_oid=row[6], acceptor_oid=row[7], artifact_sha256=row[8],
                adapter_sha256=row[9], owner=_role((row[4], *row[10:17])),
                issuer=_role((row[5], *row[17:24])),
                consumer=_role((row[6], *row[24:31])),
                acceptor=_role((row[7], *row[31:38])),
                registrar=_role(row[38:46]))


def _member_oids(cursor, member_oid):
    cursor.execute("""
        SELECT role.oid::bigint
          FROM pg_catalog.pg_roles role
         WHERE role.oid<>%s AND role.rolname<>'pg_database_owner' AND NOT role.rolsuper
           AND pg_catalog.pg_has_role(%s,role.oid,'MEMBER')
         ORDER BY role.oid
    """, [member_oid, member_oid])
    return [row[0] for row in cursor.fetchall()]


def _owner_member_oids(cursor, owner_oid):
    cursor.execute("""
        SELECT member.oid::bigint
          FROM pg_catalog.pg_roles member
         WHERE member.oid<>%s AND NOT member.rolsuper
           AND pg_catalog.pg_has_role(member.oid,%s,'MEMBER')
         ORDER BY member.oid
    """, [owner_oid, owner_oid])
    return [row[0] for row in cursor.fetchall()]


def _acl_violations(cursor, database, registration):
    """Count grants outside the exact owner, consumer and operational acceptor."""
    cursor.execute("""
        WITH database_bad AS (
          SELECT 1
            FROM pg_catalog.pg_database d
            CROSS JOIN LATERAL pg_catalog.aclexplode(
              COALESCE(d.datacl,pg_catalog.acldefault('d',d.datdba))) a
           WHERE d.oid=%s AND (
             a.grantee=0 OR
             a.grantee NOT IN (d.datdba,%s,%s) OR
             (a.grantee IN (%s,%s) AND a.privilege_type<>'CONNECT'))
        ), schema_bad AS (
          SELECT 1
            FROM pg_catalog.pg_namespace n
            CROSS JOIN LATERAL pg_catalog.aclexplode(
              COALESCE(n.nspacl,pg_catalog.acldefault('n',n.nspowner))) a
           WHERE n.nspname IN ('public','mta','fresh_control') AND (
             a.grantee=0 OR
             a.grantee NOT IN (n.nspowner,%s,%s,%s) OR
             (a.grantee=%s AND a.privilege_type<>'USAGE') OR
             (a.grantee IN (%s,%s) AND a.grantee<>n.nspowner AND a.privilege_type<>'USAGE'))
        ), relation_bad AS (
          SELECT 1
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN LATERAL pg_catalog.aclexplode(COALESCE(c.relacl,
              pg_catalog.acldefault((CASE WHEN c.relkind='S' THEN 'S' ELSE 'r' END)::"char",c.relowner))) a
           WHERE n.nspname IN ('mta','fresh_control')
             AND c.relkind IN ('r','p','v','m','f','S') AND (
               a.grantee=0 OR
               a.grantee NOT IN (c.relowner,%s,%s,%s) OR
               (a.grantee=%s AND a.privilege_type<>'SELECT') OR
               (a.grantee=%s AND a.grantee<>c.relowner AND a.privilege_type<>'SELECT') OR
               (a.grantee=%s AND NOT (
                 (a.privilege_type='SELECT' AND ((n.nspname='mta' AND c.relkind<>'S') OR
                   (n.nspname='fresh_control' AND c.relname='owned_namespace'))) OR
                 (n.nspname='mta' AND c.relname IN (
                   'fresh_mta_calculationrun','fresh_mta_dailyuipublication',
                   'fresh_mta_operationalattempt') AND a.privilege_type='UPDATE') OR
                 (n.nspname='mta' AND c.relname IN (
                   'fresh_mta_operationalacceptance','fresh_mta_dailyuiactivation')
                   AND a.privilege_type='INSERT'))))
        )
        SELECT (SELECT count(*) FROM database_bad)+
               (SELECT count(*) FROM schema_bad)+
               (SELECT count(*) FROM relation_bad),
               pg_catalog.has_database_privilege(%s,%s,'CONNECT'),
               pg_catalog.has_database_privilege(%s,%s,'CONNECT')
    """, [database['oid'], registration['issuer_oid'], registration['consumer_oid'],
          registration['issuer_oid'], registration['consumer_oid'],
          registration['owner_oid'], registration['consumer_oid'],
          registration['acceptor_oid'], registration['consumer_oid'],
          registration['owner_oid'], registration['acceptor_oid'],
          registration['owner_oid'], registration['consumer_oid'],
          registration['acceptor_oid'], registration['consumer_oid'],
          registration['owner_oid'], registration['acceptor_oid'],
          registration['issuer_oid'], database['oid'],
          registration['consumer_oid'], database['oid']])
    row = cursor.fetchone()
    return dict(count=row[0], issuer_connect=row[1], consumer_connect=row[2])


def _catalogue_evidence(cursor, database, registration):
    return dict(owner_members=_owner_member_oids(cursor, registration['owner_oid']),
                acceptor_members=_owner_member_oids(cursor, registration['acceptor_oid']),
                registrar_members=_owner_member_oids(cursor, registration['registrar']['oid']),
                owner_roles=_member_oids(cursor, registration['owner_oid']),
                issuer_roles=_member_oids(cursor, registration['issuer_oid']),
                consumer_roles=_member_oids(cursor, registration['consumer_oid']),
                acceptor_roles=_member_oids(cursor, registration['acceptor_oid']),
                registrar_roles=_member_oids(cursor, registration['registrar']['oid']),
                acl=_acl_violations(cursor, database, registration))


def _plain_role(role, *, login):
    return (role['can_login'] is login and not role['superuser'] and
            not role['create_db'] and not role['create_role'] and
            not role['replication'] and not role['bypass_rls'])


def _receipt_identity(registration):
    value = dict(policy=registration['policy'],
        registration_id=registration['registration_id'],
        database_oid=registration['database_oid'],database_name=registration['database_name'],
        owner_oid=registration['owner_oid'],owner_role=registration['owner']['name'],
        issuer_oid=registration['issuer_oid'],issuer_role=registration['issuer']['name'],
        consumer_oid=registration['consumer_oid'],consumer_role=registration['consumer']['name'],
        acceptor_oid=registration['acceptor_oid'],acceptor_role=registration['acceptor']['name'],
        registrar_oid=registration['registrar']['oid'],registrar_role=registration['registrar']['name'],
        artifact_sha256=registration['artifact_sha256'],
        adapter_sha256=registration['adapter_sha256'])
    return {**value, 'registration_digest': digest(value)}


def _validate(database, registration, evidence, *, artifact_sha256=None,
              adapter_sha256=None, installer=False):
    if (registration['policy'] != POLICY
            or registration['database_oid'] != database['oid']
            or registration['database_name'] != database['name']
            or registration['owner_oid'] != database['owner']['oid']
            or registration['owner'] != database['owner']
            or not _plain_role(registration['owner'], login=False)
            or not _plain_role(registration['issuer'], login=True)
            or not _plain_role(registration['consumer'], login=True)
            or registration['acceptor']['name'] != ACCEPTOR_ROLE
            or not _plain_role(registration['acceptor'], login=False)
            or registration['registrar']['name'] != REGISTRAR_ROLE
            or not _plain_role(registration['registrar'], login=False)
            or len({registration['owner_oid'],registration['issuer_oid'],
                    registration['consumer_oid'],registration['acceptor_oid'],
                    registration['registrar']['oid']}) != 5):
        _reject('database or role catalogue identity differs')
    if (artifact_sha256 is not None and registration['artifact_sha256'] != artifact_sha256
            or adapter_sha256 is not None and registration['adapter_sha256'] != adapter_sha256):
        _reject('artifact or adapter identity differs')
    if (evidence['owner_members'] != [registration['issuer_oid']]
            or evidence['acceptor_members'] != [registration['issuer_oid']]
            or evidence['registrar_members']
            or evidence['owner_roles']
            or evidence['issuer_roles'] != sorted((registration['owner_oid'],
                                                   registration['acceptor_oid']))
            or evidence['consumer_roles']
            or evidence['acceptor_roles']
            or evidence['registrar_roles']
            or evidence['acl']['count'] != 0
            or evidence['acl']['issuer_connect'] is not True
            or evidence['acl']['consumer_connect'] is not True):
        _reject('membership or grant catalogue differs')
    if installer and (database['current_user_oid'] != registration['owner_oid']
                      or database['session_user_oid'] != registration['issuer_oid']):
        _reject('requires the registered issuer session and database owner role')
    return _receipt_identity(registration)


def authorize_install(artifact_sha256, adapter_sha256):
    """Authorize a one-time install and return receipt metadata for new namespaces."""
    if not connection.in_atomic_block:
        _reject('install guard requires one transaction')
    with connection.cursor() as cursor:
        database = _database_identity(cursor)
        if database['name'] in LEGACY_DATABASES:
            return dict(database_name=database['name'], registration=None)
        if not _plain_role(database['owner'], login=False):
            _reject('database owner is not the dedicated unprivileged NOLOGIN role')
        # The owner comes only from pg_database. SET LOCAL is transaction-scoped;
        # caller-controlled role names are never interpolated.
        cursor.execute('SET LOCAL ROLE ' + _quote_identifier(database['owner']['name']))
        database = _database_identity(cursor)
        registration = _registered_identity(cursor)
        evidence = _catalogue_evidence(cursor, database, registration)
        identity = _validate(database, registration, evidence,
            artifact_sha256=artifact_sha256, adapter_sha256=adapter_sha256,
            installer=True)
        return dict(database_name=database['name'], registration=identity)


def verify_binding(receipt):
    """Recheck a registered namespace without requiring the reader to own it."""
    if not isinstance(receipt, dict) or not isinstance(receipt.get('owned_namespace'), dict):
        _reject('receipt binding is absent')
    expected = receipt['owned_namespace']
    with connection.cursor() as cursor:
        database = _database_identity(cursor)
        registration = _registered_identity(cursor)
        evidence = _catalogue_evidence(cursor, database, registration)
        actual = _validate(database, registration, evidence,
            artifact_sha256=expected.get('artifact_sha256'),
            adapter_sha256=expected.get('adapter_sha256'))
    if actual != expected:
        _reject('receipt registration differs')
    return receipt
