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


def _validate_identity(database, registration, evidence, *, artifact_sha256=None,
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
            or evidence['acl']['issuer_connect'] is not True
            or evidence['acl']['consumer_connect'] is not True):
        _reject('membership or grant catalogue differs')
    if installer and (database['current_user_oid'] != registration['owner_oid']
                      or database['session_user_oid'] != registration['issuer_oid']):
        _reject('requires the registered issuer session and database owner role')
    return _receipt_identity(registration)



def _validate(database, registration, evidence, *, artifact_sha256=None,
              adapter_sha256=None, installer=False):
    identity = _validate_identity(database, registration, evidence,
        artifact_sha256=artifact_sha256, adapter_sha256=adapter_sha256, installer=installer)
    if evidence['acl']['count'] != 0:
        _reject('membership or grant catalogue differs')
    return identity


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
        if adapter_sha256 == registration['adapter_sha256']:
            identity = _validate(database, registration, evidence,
                artifact_sha256=artifact_sha256, adapter_sha256=adapter_sha256,
                installer=True)
        else:
            identity = _validate_application(cursor, database, registration, evidence,
                artifact_sha256=artifact_sha256, implementation_sha256=adapter_sha256,
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
        if expected.get('policy') == APPLICATION_POLICY:
            actual = _validate_application(cursor, database, registration, evidence,
                artifact_sha256=expected.get('artifact_sha256'),
                implementation_sha256=expected.get('implementation_sha256'))
        else:
            actual = _validate(database, registration, evidence,
                artifact_sha256=expected.get('artifact_sha256'),
                adapter_sha256=expected.get('adapter_sha256'))
    if actual != expected:
        _reject('receipt registration differs')
    return receipt


# Explicit UI capability profile. This is source-controlled, never an environment allowlist.
APPLICATION_POLICY = "fresh-owned-ui-workflows-v1"
APPLICATION_REGISTRY = "fresh_control.application_capability"
APPLICATION_GRANTS = {'mta.fresh_mta_bprliveremark': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_calculationrun': {'columns': ['id'], 'table': ['UPDATE']},
 'mta.fresh_mta_mdmdraft': {'columns': ['LastModifiedDateTime', 'Masters', 'SearchKeys'],
                            'table': ['INSERT', 'UPDATE', 'DELETE']},
 'mta.fresh_mta_mdmdraftmaster': {'columns': [], 'table': ['INSERT', 'DELETE']},
 'mta.fresh_mta_mdmdraftsku': {'columns': [], 'table': ['INSERT', 'DELETE']},
 'mta.fresh_mta_mdmforcehistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'NewNorm', 'Status'],
                                   'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmforceowner': {'columns': ['generation'], 'table': ['UPDATE']},
 'mta.fresh_mta_mdmforcequeue': {'columns': ['NewNorm', 'revision'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmforcerequested': {'columns': ['Approved', 'RequestedBy', 'Reverted'],
                                     'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmforcetaskrevision': {'columns': ['revision'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmforceuploadlog': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmlocationapproved': {'columns': ['LL1',
                                                   'LL2',
                                                   'LL3',
                                                   'LL4',
                                                   'LL5',
                                                   'LocationType',
                                                   'LogisticsLocation',
                                                   'WHDescription',
                                                   'c1',
                                                   'c10',
                                                   'c11',
                                                   'c12',
                                                   'c13',
                                                   'c14',
                                                   'c15',
                                                   'c2',
                                                   'c3',
                                                   'c4',
                                                   'c5',
                                                   'c6',
                                                   'c7',
                                                   'c8',
                                                   'c9'],
                                       'table': ['INSERT', 'UPDATE', 'DELETE']},
 'mta.fresh_mta_mdmlocationattributes': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmlocationdescription': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmlocationhistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'Status'],
                                      'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmlocationrequested': {'columns': ['Approved', 'Reverted'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmlocationuploadlog': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmmoqhistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'Status'],
                                 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmmoqrequested': {'columns': ['Approved', 'Reverted'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmmoquploadlog': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmmoqwithdestinationapproved': {'columns': ['MOQ', 'revision'],
                                                 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmphasecontrolsowner': {'columns': ['generation'], 'table': ['UPDATE']},
 'mta.fresh_mta_mdmphasecontrolstaskrevision': {'columns': ['revision'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmphaseinnormhistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'Status'],
                                         'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmphaseinnormqueue': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmphaseinnormrequested': {'columns': ['Approved', 'Reverted'],
                                           'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmphaseouthistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'Status'],
                                      'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmphaseoutqueue': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmphaseoutrequested': {'columns': ['Approved', 'Reverted'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmseasoncurrent': {'columns': ['Status', 'Comment', 'revision'], 'table': ['UPDATE']},
 'mta.fresh_mta_mdmseasonhistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'Status'],
                                    'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmseasonowner': {'columns': ['generation'], 'table': ['UPDATE']},
 'mta.fresh_mta_mdmseasonqueue': {'columns': ['BuildupDuration',
                                              'DeltaNormPercentage',
                                              'EndDate',
                                              'StartDate',
                                              'TargetNorm',
                                              'UpperLowerCap',
                                              'revision'],
                                  'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmseasonrequested': {'columns': ['ActivateDBM', 'Approved', 'Reverted'],
                                      'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmseasonstatushistory': {'columns': ['ApproverBy', 'ApproverId', 'Comments', 'Status'],
                                          'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmseasonstatusrequested': {'columns': ['Approved', 'Reverted'],
                                            'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmseasontaskrevision': {'columns': ['revision'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskuapproved': {'columns': ['ElephantOrderCapping',
                                              'SKUDescription',
                                              'SL1',
                                              'SL2',
                                              'SL3',
                                              'SL4',
                                              'SL5',
                                              'Volume',
                                              'Weight',
                                              'c1',
                                              'c10',
                                              'c11',
                                              'c12',
                                              'c13',
                                              'c14',
                                              'c15',
                                              'c2',
                                              'c3',
                                              'c4',
                                              'c5',
                                              'c6',
                                              'c7',
                                              'c8',
                                              'c9'],
                                  'table': ['INSERT', 'UPDATE', 'DELETE']},
 'mta.fresh_mta_mdmskuattributes': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmskudescription': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmskuhistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'Status'],
                                 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskulocaddapproved': {'columns': ['DBMActive',
                                                    'FGRMFlag',
                                                    'GCP',
                                                    'MinNorm',
                                                    'MinOrderCount',
                                                    'Norm',
                                                    'NormPercentReservation',
                                                    'OCP',
                                                    'PSOThreshold',
                                                    'PackSize',
                                                    'ParentWhCode',
                                                    'RCP',
                                                    'RLT',
                                                    'SKULocAtt01',
                                                    'SKULocAtt02',
                                                    'SKULocAtt03',
                                                    'SKULocAtt04',
                                                    'SKULocAtt05',
                                                    'SKULocAtt06',
                                                    'SKULocAtt07',
                                                    'SKULocAtt08',
                                                    'SKULocAtt09',
                                                    'SKULocAtt10',
                                                    'SKULocAtt11',
                                                    'SKULocAtt12',
                                                    'SKULocAtt13',
                                                    'SKULocAtt14',
                                                    'SKULocAtt15',
                                                    'SpikeThreshold',
                                                    'StockPercentForRat'],
                                        'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskulocaddrequested': {'columns': ['Approved'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskulochistory': {'columns': ['ApprovedBy', 'Comments', 'Status'],
                                    'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskulocmodifyapproved': {'columns': ['DBMActive',
                                                       'FGRMFlag',
                                                       'GCP',
                                                       'MinNorm',
                                                       'MinOrderCount',
                                                       'NormPercentReservation',
                                                       'OCP',
                                                       'PSOThreshold',
                                                       'PackSize',
                                                       'ParentWhCode',
                                                       'RCP',
                                                       'RLT',
                                                       'SKULocAtt01',
                                                       'SKULocAtt02',
                                                       'SKULocAtt03',
                                                       'SKULocAtt04',
                                                       'SKULocAtt05',
                                                       'SKULocAtt06',
                                                       'SKULocAtt07',
                                                       'SKULocAtt08',
                                                       'SKULocAtt09',
                                                       'SKULocAtt10',
                                                       'SKULocAtt11',
                                                       'SKULocAtt12',
                                                       'SKULocAtt13',
                                                       'SKULocAtt14',
                                                       'SKULocAtt15',
                                                       'SpikeThreshold',
                                                       'StockPercentForRat'],
                                           'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskulocmodifyrequested': {'columns': ['Approved'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskulocremoveapproved': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmskulocremoverequested': {'columns': ['Approved'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskurequested': {'columns': ['Approved', 'Reverted'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmskuuploadlog': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmsobapproved': {'columns': ['SOB', 'revision'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmsobhistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'Status'],
                                 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmsobrequested': {'columns': ['Approved', 'Reverted'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmsobuploadlog': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmsource': {'columns': ['id'], 'table': ['UPDATE']},
 'mta.fresh_mta_mdmstoppipohistory': {'columns': ['ApprovedBy', 'ApproverId', 'Comments', 'Status'],
                                      'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmstoppipoowner': {'columns': ['generation'], 'table': ['UPDATE']},
 'mta.fresh_mta_mdmstoppipoqueue': {'columns': [], 'table': ['INSERT']},
 'mta.fresh_mta_mdmstoppiporequested': {'columns': ['Approved', 'Reverted'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmstoppipotaskrevision': {'columns': ['revision'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmsubtask': {'columns': ['ApprovedOrRejectedDate', 'DBUpdatedDate', 'TaskStatus'],
                              'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmsuppliertaskrevision': {'columns': ['revision'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_mdmtask': {'columns': ['TaskStatus'], 'table': ['INSERT', 'UPDATE']},
 'mta.fresh_mta_remarkowner': {'columns': ['next_ordinal'], 'table': ['UPDATE']},
 'mta.fresh_mta_runcommand': {'columns': ['state_manifest'], 'table': ['INSERT', 'UPDATE']},
 'mta_state.dbm_normacceptancetbl': {'columns': [], 'table': ['INSERT']},
 'mta_state.dbm_normsinsleepmodetbl': {'columns': [], 'table': ['INSERT']},
 'mta_state.dbm_suggestions': {'columns': [], 'table': ['INSERT']}}

CAPABILITY_GUARD_BODY = "BEGIN RAISE EXCEPTION 'Application capability is immutable'; END"
CAPABILITY_FIELDS = frozenset(('policy', 'original_registration', 'original_implementation_sha256',
    'implementation_sha256', 'profile_digest', 'objects_digest', 'grants_digest', 'receipt_digest'))


def _application_profile_digest():
    return digest({'grants':APPLICATION_GRANTS,'functions':sorted(APPLICATION_FUNCTIONS),
        'write_guard':APPLICATION_WRITE_GUARD_BODY,'write_targets':APPLICATION_WRITE_GUARDS})


def _application_catalogue(cursor):
    """One explicit namespace catalogue, including column and default privileges."""
    cursor.execute("""
        SELECT n.nspname,c.relname,c.oid::bigint,c.relkind,c.relowner::bigint,
               pn.nspname,pc.relname,pa.attname
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_depend dep ON c.relkind='S' AND dep.classid='pg_class'::regclass
          AND dep.objid=c.oid AND dep.refclassid='pg_class'::regclass AND dep.deptype IN ('a','i')
        LEFT JOIN pg_class pc ON pc.oid=dep.refobjid
        LEFT JOIN pg_namespace pn ON pn.oid=pc.relnamespace
        LEFT JOIN pg_attribute pa ON pa.attrelid=pc.oid AND pa.attnum=dep.refobjsubid
        WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
          AND c.relkind IN ('r','p','v','m','f','S') ORDER BY n.nspname,c.relname
    """)
    objects = [dict(name=n+'.'+name,oid=oid,kind=kind,owner=owner,
        sequence_for=(pn+'.'+parent+'.'+column if pn and parent and column else None))
        for n,name,oid,kind,owner,pn,parent,column in cursor.fetchall()]
    cursor.execute("""
        WITH acl AS (
          SELECT 'database' scope,d.datname::text name,d.oid::bigint oid,d.datdba::bigint owner,
            NULL::text col,a.* FROM pg_database d CROSS JOIN LATERAL aclexplode(
              coalesce(d.datacl,acldefault('d',d.datdba))) a WHERE d.datname=current_database()
          UNION ALL
          SELECT 'schema',n.nspname,n.oid::bigint,n.nspowner::bigint,NULL,a.*
            FROM pg_namespace n CROSS JOIN LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
          UNION ALL
          SELECT CASE WHEN c.relkind='S' THEN 'sequence' ELSE 'table' END,n.nspname||'.'||c.relname,
            c.oid::bigint,c.relowner::bigint,NULL,a.*
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault(
              (CASE WHEN c.relkind='S' THEN 'S' ELSE 'r' END)::"char",c.relowner))) a
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
              AND c.relkind IN ('r','p','v','m','f','S')
          UNION ALL
          SELECT 'column',n.nspname||'.'||c.relname,c.oid::bigint,c.relowner::bigint,att.attname,a.*
            FROM pg_attribute att JOIN pg_class c ON c.oid=att.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN LATERAL aclexplode(att.attacl) a
            WHERE att.attnum>0 AND NOT att.attisdropped
              AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
          UNION ALL
          SELECT 'function',n.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
            p.oid::bigint,p.proowner::bigint,NULL,a.* FROM pg_proc p
            JOIN pg_namespace n ON n.oid=p.pronamespace
            CROSS JOIN LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
          UNION ALL
          SELECT 'default',coalesce(n.nspname,'*')||':'||d.defaclobjtype::text,d.oid::bigint,
            d.defaclrole::bigint,NULL,a.* FROM pg_default_acl d
            LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace
            CROSS JOIN LATERAL aclexplode(d.defaclacl) a
        ) SELECT scope,name,oid,owner,col,grantor::bigint,grantee::bigint,privilege_type,is_grantable
          FROM acl ORDER BY scope,name,col NULLS FIRST,grantor,grantee,privilege_type,is_grantable
    """)
    grants = [dict(zip(('scope','name','oid','owner','column','grantor','grantee','privilege','grantable'), row))
              for row in cursor.fetchall()]
    cursor.execute("""
        SELECT n.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
          p.oid::bigint,p.proowner::bigint,p.prosecdef,p.prosrc,p.proconfig,p.prolang::bigint,
          p.prorettype::regtype::text
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema' ORDER BY 1
    """)
    functions = [dict(zip(('name','oid','owner','security_definer','body','configuration','language','returns'),r))
                 for r in cursor.fetchall()]
    return dict(objects=objects,grants=grants,functions=functions)


def _check_application_grants(catalogue, registration):
    """Admit only this fixed application profile; the signed row cannot expand it."""
    owner, consumer, acceptor, issuer = (registration[k+'_oid'] for k in ('owner','consumer','acceptor','issuer'))
    registrar = registration['registrar']['oid']
    objects = {o['name']:o for o in catalogue['objects']}
    if len(objects) != len(catalogue['objects']):
        _reject('application object identity is ambiguous')
    for name, obj in objects.items():
        expected_owner = registrar if name.startswith('fresh_control.') else owner
        if obj['owner'] != expected_owner or not name.startswith(('mta.','mta_state.','mta_opening.','fresh_control.')):
            _reject('application object owner or namespace differs')
    expected = {('table',name,None,'SELECT') for name,o in objects.items() if o['kind']!='S'}
    for name, permissions in APPLICATION_GRANTS.items():
        if name not in objects or objects[name]['kind'] not in ('r','p'):
            _reject('application write object is absent')
        for permission in permissions['table']:
            if permission == 'UPDATE' and permissions['columns']:
                expected.update(('column',name,col,'UPDATE') for col in permissions['columns'])
            else:
                expected.add(('table',name,None,permission))
        if 'INSERT' in permissions['table']:
            sequences = [o for o in objects.values() if o['kind']=='S' and o['sequence_for']==name+'.id']
            if len(sequences)!=(1 if name.startswith('mta.') else 0):
                _reject('application sequence owner is ambiguous')
            expected.update(('sequence',o['name'],None,'USAGE') for o in sequences)
    functions = {f['name']:f for f in catalogue['functions']}
    if len(functions)!=len(catalogue['functions']):
        _reject('application function identity is ambiguous')
    for name,func in functions.items():
        expected_owner = registrar if name.startswith('fresh_control.') else owner
        if func['security_definer'] or func['owner']!=expected_owner or not name.startswith(('mta.','fresh_control.')):
            _reject('application function authority differs')
    if not APPLICATION_FUNCTIONS <= functions.keys():
        _reject('application helper function is absent')
    expected.update(('function',name,None,'EXECUTE') for name in APPLICATION_FUNCTIONS)
    actual = set()
    for acl in catalogue['grants']:
        scope,name,priv,grantee = (acl[k] for k in ('scope','name','privilege','grantee'))
        if scope == 'default':
            _reject('application default privileges are not permitted')
        if grantee == 0:
            _reject('application PUBLIC privileges are not permitted')
        if scope=='schema' and (name not in ('public','mta','mta_state','mta_opening','fresh_control') or
                (name!='public' and acl['owner']!=(registrar if name=='fresh_control' else owner)) or
                (name=='public' and acl['owner'] in (consumer,issuer,acceptor))):
            _reject('application schema authority differs')
        if grantee == acl['owner']:
            continue
        if acl['grantable']:
            _reject('application delegated grant option is not permitted')
        if scope=='database':
            allowed = grantee in (issuer,consumer) and priv=='CONNECT'
        elif scope=='schema':
            allowed = (name in ('public','mta','mta_state','mta_opening','fresh_control')
                and grantee in (owner,consumer,acceptor) and priv=='USAGE')
        elif grantee==consumer:
            actual.add((scope,name,acl['column'],priv))
            allowed = (scope,name,acl['column'],priv) in expected
        elif grantee==owner:
            allowed = scope=='table' and name.startswith('fresh_control.') and priv=='SELECT'
        elif grantee==acceptor:
            allowed = (scope=='table' and (
                (priv=='SELECT' and (name.startswith('mta.') or name in (REGISTRY,APPLICATION_REGISTRY))) or
                (priv=='UPDATE' and name in ('mta.fresh_mta_calculationrun','mta.fresh_mta_dailyuipublication','mta.fresh_mta_operationalattempt')) or
                (priv=='INSERT' and name in ('mta.fresh_mta_operationalacceptance','mta.fresh_mta_dailyuiactivation'))))
        else:
            allowed = False
        if not allowed:
            _reject('application grant outside the explicit profile')
    if actual != expected:
        _reject('application grant profile is incomplete')
    return dict(objects_digest=digest({'relations':catalogue['objects'],'functions':catalogue['functions']}),
                grants_digest=digest(catalogue['grants']))


def _read_application_capability(cursor, registration):
    cursor.execute("SELECT pg_catalog.to_regclass(%s)::oid", [APPLICATION_REGISTRY])
    row = cursor.fetchone()
    if not row or row[0] is None:
        _reject('explicit application capability is absent')
    oid = row[0]
    cursor.execute("""
        SELECT c.relowner::bigint,n.nspowner::bigint,c.relrowsecurity,c.relforcerowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=%s
    """, [oid])
    registrar = registration['registrar']['oid']
    if cursor.fetchone() != (registrar,registrar,False,False):
        _reject('application capability is not registrar-owned')
    cursor.execute("""
        SELECT t.tgname,t.tgtype,t.tgenabled,p.proowner::bigint,p.prosecdef,p.prosrc
        FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
        WHERE t.tgrelid=%s AND NOT t.tgisinternal ORDER BY t.tgname
    """, [oid])
    expected = [('application_capability_immutable',27,'O',registrar,False,CAPABILITY_GUARD_BODY),
                ('application_capability_truncate',34,'O',registrar,False,CAPABILITY_GUARD_BODY)]
    if cursor.fetchall() != expected:
        _reject('application capability mutation guards differ')
    cursor.execute('SELECT singleton,binding::text FROM '+APPLICATION_REGISTRY)
    rows = cursor.fetchall()
    if len(rows)!=1 or rows[0][0] is not True:
        _reject('exactly one application capability is required')
    import json
    try:
        value = json.loads(rows[0][1])
    except (ValueError,TypeError) as exc:
        raise ValueError('Fresh owned namespace application capability is invalid') from exc
    if not isinstance(value,dict):
        _reject('application capability is invalid')
    return value


def _validate_application_binding(binding, original, implementation_sha256, catalog_digests):
    if (set(binding)!=CAPABILITY_FIELDS or binding['policy']!=APPLICATION_POLICY or
            binding['original_registration']!=original or
            binding['original_implementation_sha256']!=original['adapter_sha256'] or
            binding['implementation_sha256']!=implementation_sha256 or
            implementation_sha256==original['adapter_sha256'] or
            binding['profile_digest']!=_application_profile_digest() or
            any(binding[k]!=v for k,v in catalog_digests.items()) or
            binding['receipt_digest']!=digest({k:v for k,v in binding.items() if k!='receipt_digest'})):
        _reject('application capability identity or grants differ')
    return {**binding, 'artifact_sha256':original['artifact_sha256']}


def _validate_application(cursor, database, registration, evidence, *,
                          artifact_sha256, implementation_sha256, installer=False):
    original = _validate_identity(database,registration,evidence,
        artifact_sha256=artifact_sha256,adapter_sha256=registration['adapter_sha256'],installer=installer)
    binding = _read_application_capability(cursor,registration)
    _check_application_write_guards(cursor,registration)
    catalogue = _application_catalogue(cursor)
    digests = _check_application_grants(catalogue,registration)
    return _validate_application_binding(binding,original,implementation_sha256,digests)

# Consumer row-lock permission must not become a calculation writer. Typed command
# INSERTs belong only to the newly recorded action; existing closing images stay immutable.
APPLICATION_WRITE_GUARD_BODY = """DECLARE role_name text; command_id bigint; command record; family text; entry record; physical_name text; actual_count bigint;
BEGIN
 SELECT binding->'original_registration'->>'consumer_role' INTO role_name
 FROM fresh_control.application_capability WHERE singleton IS TRUE;
 IF role_name IS NULL THEN RAISE EXCEPTION 'Application capability is absent'; END IF;
 IF current_user<>role_name THEN RETURN NEW; END IF;
 IF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME IN ('fresh_mta_calculationrun','fresh_mta_mdmsource') THEN
  RAISE EXCEPTION 'Application calculation permission is row-lock only';
 ELSIF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME='fresh_mta_runcommand' THEN
  IF OLD.state_manifest<>'{}'::jsonb OR NEW.state_manifest='{}'::jsonb
    OR (to_jsonb(OLD)-'state_manifest') IS DISTINCT FROM (to_jsonb(NEW)-'state_manifest')
   THEN RAISE EXCEPTION 'Application command fields are immutable'; END IF;
  IF jsonb_typeof(NEW.state_manifest)<>'object' THEN
   RAISE EXCEPTION 'Application command manifest must be an object'; END IF;
  FOR entry IN SELECT key,value FROM jsonb_each(NEW.state_manifest) LOOP
   IF entry.key NOT IN ('NormAcceptanceTbl','NormsInSleepModeTbl','Suggestions')
     OR (NEW.payload->>'operation'='APPLY' AND entry.key<>'NormAcceptanceTbl')
     OR (NEW.payload->>'operation'='SLEEP' AND entry.key='NormAcceptanceTbl' AND entry.value->>'count'<>'0')
     OR NEW.payload->>'operation' NOT IN ('APPLY','SLEEP')
     OR entry.value->>'image' IS DISTINCT FROM ('action/'||NEW.id::text||'/'||entry.key)
     OR entry.value->>'table' IS DISTINCT FROM ('DBM/'||entry.key)
     OR COALESCE(entry.value->>'digest','')!~'^[0-9a-f]{64}$'
     OR COALESCE(entry.value->>'count','')!~'^[0-9]+$'
     OR jsonb_typeof(entry.value->'fields') IS DISTINCT FROM 'array'
    THEN RAISE EXCEPTION 'Application command manifest ownership differs'; END IF;
   physical_name=CASE entry.key WHEN 'NormAcceptanceTbl' THEN 'dbm_normacceptancetbl'
    WHEN 'NormsInSleepModeTbl' THEN 'dbm_normsinsleepmodetbl' WHEN 'Suggestions' THEN 'dbm_suggestions' END;
   EXECUTE format('SELECT count(*) FROM mta_state.%I WHERE vf_run_id=$1 AND vf_image=$2',physical_name)
    INTO actual_count USING NEW.run_id,entry.value->>'image';
   IF actual_count<>(entry.value->>'count')::bigint THEN
    RAISE EXCEPTION 'Application command manifest row count differs'; END IF;
  END LOOP;
  RETURN NEW;
 ELSIF TG_TABLE_SCHEMA='mta' AND TG_TABLE_NAME IN
   ('fresh_mta_mdmforceowner','fresh_mta_mdmseasonowner','fresh_mta_mdmstoppipoowner','fresh_mta_mdmphasecontrolsowner') THEN
  IF pg_trigger_depth()<>2 OR NEW.generation<>OLD.generation+1
    OR (to_jsonb(OLD)-'generation') IS DISTINCT FROM (to_jsonb(NEW)-'generation')
   THEN RAISE EXCEPTION 'Application generation may advance only inside its workflow trigger'; END IF;
  RETURN NEW;
 ELSIF TG_TABLE_SCHEMA='mta_state' THEN
  family=CASE TG_TABLE_NAME WHEN 'dbm_normacceptancetbl' THEN 'NormAcceptanceTbl'
   WHEN 'dbm_normsinsleepmodetbl' THEN 'NormsInSleepModeTbl'
   WHEN 'dbm_suggestions' THEN 'Suggestions' END;
  IF family IS NULL OR NEW.vf_image!~('^action/[0-9]+/'||family||'$')
   THEN RAISE EXCEPTION 'Application write requires a typed command image'; END IF;
  command_id=split_part(NEW.vf_image,'/',2)::bigint;
  SELECT * INTO command FROM mta.fresh_mta_runcommand WHERE id=command_id AND run_id=NEW.vf_run_id;
  IF NOT FOUND OR command.state_manifest<>'{}'::jsonb
    OR (family='NormAcceptanceTbl' AND command.payload->>'operation'<>'APPLY')
    OR (family<>'NormAcceptanceTbl' AND command.payload->>'operation'<>'SLEEP')
    OR NOT EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun WHERE id=NEW.vf_run_id AND status='SUCCEEDED')
    OR EXISTS(SELECT 1 FROM mta.fresh_mta_calculationrun WHERE predecessor_id=NEW.vf_run_id AND status IN ('RUNNING','SUCCEEDED'))
   THEN RAISE EXCEPTION 'Application command image ownership differs'; END IF;
  RETURN NEW;
 END IF;
 RAISE EXCEPTION 'Unexpected application write guard target';
END"""
APPLICATION_WRITE_GUARDS = {
    'mta.fresh_mta_calculationrun': 19,
    'mta.fresh_mta_mdmsource': 19,
    'mta.fresh_mta_mdmforceowner': 19,
    'mta.fresh_mta_mdmseasonowner': 19,
    'mta.fresh_mta_mdmstoppipoowner': 19,
    'mta.fresh_mta_mdmphasecontrolsowner': 19,
    'mta.fresh_mta_runcommand': 19,
    'mta_state.dbm_normacceptancetbl': 7,
    'mta_state.dbm_normsinsleepmodetbl': 7,
    'mta_state.dbm_suggestions': 7,
}


def _check_application_write_guards(cursor, registration):
    cursor.execute("""
        SELECT n.nspname||'.'||c.relname,t.tgtype,t.tgenabled,p.proowner::bigint,p.prosecdef,p.prosrc
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid
        WHERE t.tgname='application_write_boundary' ORDER BY 1
    """)
    expected = [(name,kind,'O',registration['registrar']['oid'],False,APPLICATION_WRITE_GUARD_BODY)
                for name,kind in sorted(APPLICATION_WRITE_GUARDS.items())]
    if cursor.fetchall()!=expected:
        _reject('application write boundary guards differ')


# Existing invoker helpers called by the fixed workflow/guard SQL. No PUBLIC
# EXECUTE or security-definer capability is admitted by the writable profile.
APPLICATION_FUNCTIONS = frozenset((
    'mta.active_mdm_current_source(owner bigint)',
    'mta.daily_prepared_owner(owner uuid)',
    'mta.force_consumption_owned(owner bigint)',
    'mta.location_transition_record(owner bigint)',
    'mta.lock_native_location_add(owner bigint)',
    'mta.lock_native_sku_add(owner bigint)',
    'mta.native_audit_policy_matches(payload jsonb, horizon integer, timezone text, client_folder text)',
    'mta.native_audit_source_delete_allowed(source_table text, old_row jsonb)',
    'mta.native_audit_source_table(audit_table text)',
    'mta.native_audit_table_complete(capture uuid, audit_table text, source_table text, force_log boolean)',
    'mta.native_initialization_pending(identity uuid)',
    'mta.native_location_add_row(target text, candidate jsonb)',
    'mta.native_mdm_family_bootstrap(owner bigint)',
    'mta.native_sku_add_row(target text, candidate jsonb)',
    'mta.season_accepted_closing_owned(owner bigint)',
    'mta.supplier_accepted_closing_owned(owner bigint)',
    'mta.supplier_decision_owned(owner bigint)',
    'mta.target_mdm_install_owned(owner bigint)',
    'mta.typed_input_node(root jsonb, path text[])',
    'mta.valid_closing_projection(p fresh_mta_mdmclosingprojectionreceipt)',
))
