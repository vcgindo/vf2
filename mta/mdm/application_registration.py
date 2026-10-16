"""Trusted one-time additive registration of the fixed native UI capability.

Call inside a provisioner-owned PostgreSQL transaction. The caller must explicitly
choose commit or rollback; this helper never connects, commits, reads credentials,
changes role memberships, or replaces the original namespace registration.
"""
from mta.mdm import owned_namespace as owned
from mta.serialization import digest


def _identifier(value):
    return '"'+value.replace('"','""')+'"'


def _relation(name):
    return '.'.join(_identifier(part) for part in name.split('.'))


def register_application(cursor, *, expected_database, expected_database_oid,
                         expected_registration_digest, expected_original_implementation,
                         implementation_sha256, production=False):
    database=owned._database_identity(cursor)
    registration=owned._registered_identity(cursor)
    evidence=owned._catalogue_evidence(cursor,database,registration)
    original=owned._validate_identity(database,registration,evidence)
    if (database['name']!=expected_database or database['oid']!=expected_database_oid or
            original['registration_digest']!=expected_registration_digest or
            registration['adapter_sha256']!=expected_original_implementation or
            len(implementation_sha256)!=64 or
            (implementation_sha256==expected_original_implementation) is not production):
        raise ValueError('Application registration explicit identity differs')
    cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
    if cursor.fetchone()!=(True,):
        raise ValueError('Trusted provisioner session required')
    cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
    cursor.execute('LOCK TABLE mta.fresh_mta_productioninitialization, mta.fresh_mta_mdmsource, '
                   'mta.fresh_mta_calculationrun IN ACCESS EXCLUSIVE MODE')
    cursor.execute('SELECT (SELECT count(*) FROM mta.fresh_mta_productioninitialization), '
                   '(SELECT count(*) FROM mta.fresh_mta_mdmsource), '
                   '(SELECT count(*) FROM mta.fresh_mta_calculationrun)')
    if cursor.fetchone()!=(0,0,0):
        raise ValueError('Additive application registration requires the original empty namespace')
    cursor.execute('SELECT to_regclass(%s)',[owned.APPLICATION_REGISTRY])
    if cursor.fetchone()!=(None,):
        raise ValueError('Application capability already exists; replacement prohibited')
    cursor.execute('CREATE TABLE fresh_control.application_capability '
                   '(singleton boolean PRIMARY KEY DEFAULT TRUE CHECK(singleton IS TRUE), binding jsonb NOT NULL)')
    cursor.execute('ALTER TABLE fresh_control.application_capability OWNER TO fresh_namespace_registrar')
    cursor.execute('REVOKE ALL ON fresh_control.application_capability FROM PUBLIC')
    roles=(registration['owner']['name'],registration['consumer']['name'],registration['acceptor']['name'])
    cursor.execute('GRANT SELECT ON fresh_control.application_capability TO '+','.join(map(_identifier,roles)))
    # No consumer UPDATE/DELETE/DDL on this additive authority row.
    for function,body in (('deny_application_capability_change',owned.CAPABILITY_GUARD_BODY),
                          ('guard_application_write',owned.APPLICATION_WRITE_GUARD_BODY)):
        assert '$capability$' not in body
        cursor.execute('CREATE FUNCTION fresh_control.'+function+'() RETURNS trigger LANGUAGE plpgsql AS $capability$'+body+'$capability$')
        cursor.execute('ALTER FUNCTION fresh_control.'+function+'() OWNER TO fresh_namespace_registrar')
        cursor.execute('REVOKE ALL ON FUNCTION fresh_control.'+function+'() FROM PUBLIC')
    cursor.execute('CREATE TRIGGER application_capability_immutable BEFORE UPDATE OR DELETE '
                   'ON fresh_control.application_capability FOR EACH ROW EXECUTE FUNCTION '
                   'fresh_control.deny_application_capability_change()')
    cursor.execute('CREATE TRIGGER application_capability_truncate BEFORE TRUNCATE '
                   'ON fresh_control.application_capability FOR EACH STATEMENT EXECUTE FUNCTION '
                   'fresh_control.deny_application_capability_change()')
    for name,kind in owned.APPLICATION_WRITE_GUARDS.items():
        event='INSERT' if kind==7 else 'UPDATE'
        cursor.execute('CREATE TRIGGER application_write_boundary BEFORE '+event+' ON '+_relation(name)+
                       ' FOR EACH ROW EXECUTE FUNCTION fresh_control.guard_application_write()')
    catalogue=owned._application_catalogue(cursor)
    consumer=_identifier(registration['consumer']['name'])
    for obj in catalogue['objects']:
        name=_relation(obj['name'])
        if obj['kind']=='S':
            cursor.execute('REVOKE ALL ON SEQUENCE '+name+' FROM '+consumer)
        else:
            cursor.execute('REVOKE INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER ON '+name+' FROM '+consumer)
            cursor.execute('GRANT SELECT ON '+name+' TO '+consumer)
    # Remove the old explicit column grants as well as relation ACLs.
    for acl in catalogue['grants']:
        if acl['scope']=='column' and acl['grantee']==registration['consumer_oid']:
            cursor.execute('REVOKE '+acl['privilege']+' ('+_identifier(acl['column'])+') ON '+
                           _relation(acl['name'])+' FROM '+consumer)
    permissions = dict(owned.APPLICATION_GRANTS)
    if production:
        permissions.update(owned.LOGISTICS_APPLICATION_GRANTS)
        permissions.update(owned.PRODUCTION_UI_GRANTS)
    for name,grant in permissions.items():
        for permission in grant['table']:
            columns=' ('+','.join(map(_identifier,grant['columns']))+')' if permission=='UPDATE' else ''
            cursor.execute('GRANT '+permission+columns+' ON '+_relation(name)+' TO '+consumer)
        if 'INSERT' in grant['table'] and name.startswith('mta.'):
            sequences=[o for o in catalogue['objects'] if o['kind']=='S' and o['sequence_for']==name+'.id']
            if len(sequences)!=1:raise ValueError('Explicit application sequence dependency differs')
            cursor.execute('GRANT USAGE ON SEQUENCE '+_relation(sequences[0]['name'])+' TO '+consumer)
    for function in catalogue['functions']:
        # Identity arguments come from pg_proc, never user input. Use regprocedure
        # server formatting for quoted names and types.
        cursor.execute('SELECT %s::oid::regprocedure::text',[function['oid']])
        identity=cursor.fetchone()[0]
        cursor.execute('REVOKE ALL ON FUNCTION '+identity+' FROM PUBLIC,'+consumer)
        if function['name'] in owned.APPLICATION_FUNCTIONS:
            cursor.execute('GRANT EXECUTE ON FUNCTION '+identity+' TO '+consumer)
    catalogue=owned._application_catalogue(cursor)
    digests=owned._check_application_grants(catalogue,registration,logistics=production,production=production)
    if production:
        owned._check_logistics_schema(cursor,catalogue,registration)
    binding=dict(policy=owned.PRODUCTION_APPLICATION_POLICY if production else owned.APPLICATION_POLICY,
        original_registration=original,
        original_implementation_sha256=expected_original_implementation,
        implementation_sha256=implementation_sha256,profile_digest=owned._production_application_profile_digest() if production else owned._application_profile_digest(),**digests)
    binding['receipt_digest']=digest(binding)
    import json
    cursor.execute('SET LOCAL ROLE fresh_namespace_registrar')
    cursor.execute('INSERT INTO fresh_control.application_capability(singleton,binding) VALUES(TRUE,%s::jsonb)',
                   [json.dumps(binding,sort_keys=True)])
    cursor.execute('RESET ROLE')
    owned._check_application_write_guards(cursor,registration)
    actual=owned._validate_application(cursor,database,registration,evidence,
        artifact_sha256=registration['artifact_sha256'],implementation_sha256=implementation_sha256)
    if actual!={**binding,'artifact_sha256':registration['artifact_sha256']}:
        raise ValueError('Application capability final readback differs')
    if owned._registered_identity(cursor)!=registration:
        raise ValueError('Original namespace was modified')
    return actual
