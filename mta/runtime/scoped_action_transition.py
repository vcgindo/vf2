"""One pinned recovered-stage guard upgrade over the existing registrar."""
from importlib import import_module
from mta.serialization import digest

MIGRATION_NAME = '0222_recovered_scope_actions'
MIGRATION_SHA256 = '860c149aa326b24eb8e7a8763c697456d06a80fb6ef170c0157b71b42e8a33b7'
PREVIOUS_COMMIT = '6066b298203078ab9f12597f0c20f3d67b6ff38f'
PREVIOUS_RELEASE = '14e08da6ff3d774df0f51898e0b24701a834964de44fa07a002aa032294154fc'
BEFORE_SCHEMA = '4484ec0facc53d9e20c64c9dcf72b3098498c174f3c4499c6719c7bb328b7ed1'
BEFORE_GUARD = '93d6e8ecaf0d8397290b5b294a70f338c9baefecc891301b8794e74bbf50e31b'
# This finite transition belongs to the exact registered UI221 database. Role
# names remain those of its original certificate; no production-role aliasing.
OWNER = 'vftest_g2n_20261024_owner'
RUNTIME = 'vftest_g2n_20261024_runtime'


def migration_pins():
    return [[MIGRATION_NAME, MIGRATION_SHA256]]


def catalogue_delta(*, bootstrap=False):
    frozen = import_module('mta.runtime.migrations.'+MIGRATION_NAME)
    name = 'mta.actionable_scope_phase(target uuid, accepted uuid)'
    before = dict(name=name, owner=OWNER, security_definer=False,
        body=frozen.OLD, configuration=['search_path=pg_catalog, mta'], language='sql', returns='boolean')
    result = {'functions:'+name: dict(before=before, after=dict(before, body=frozen.BODY))}
    if not bootstrap:
        return result
    # A fresh221 registration has no schema compatibility relation yet. These
    # are exactly bootstrap_schema_transition's registrar-owned additions.
    table = 'fresh_control.ingestion_schema_compatibility'
    registrar = 'fresh_namespace_registrar'
    def added(key, value):
        result[key] = dict(before=None, after=value)
    added('objects:'+table, dict(name=table, kind='r', owner=registrar, sequence_for=None))
    for privilege in ('INSERT', 'SELECT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'):
        added('grants:'+table+':None:'+registrar+':'+registrar+':'+privilege,
            dict(scope='table', name=table, owner=registrar, column=None, grantor=registrar,
                grantee=registrar, privilege=privilege, grantable=False))
    for reader in (OWNER, RUNTIME):
        added('grants:'+table+':None:'+registrar+':'+reader+':SELECT',
            dict(scope='table', name=table, owner=registrar, column=None, grantor=registrar,
                grantee=reader, privilege='SELECT', grantable=False))
    for index, (column, sqltype) in enumerate((('initialization_id', 'uuid'),
            ('target_release', 'character varying(64)'), ('body', 'jsonb'),
            ('receipt_digest', 'character varying(64)')), 1):
        added('column:'+table+'.'+column, [index, sqltype, True, '', '', None])
    added('constraint:'+table+'.ingestion_schema_compatibility_body_check',
        ['c', True, 'CHECK ((octet_length((body)::text) <= 65536))'])
    added('constraint:'+table+'.ingestion_schema_compatibility_pkey',
        ['p', True, 'PRIMARY KEY (initialization_id, target_release)'])
    added('index:fresh_control.ingestion_schema_compatibility_pkey',
        ['CREATE UNIQUE INDEX ingestion_schema_compatibility_pkey ON '+table+
         ' USING btree (initialization_id, target_release)'])
    # The complete catalogue includes pg_attribute rows for the new index too.
    for index, (column, sqltype) in enumerate((('initialization_id', 'uuid'),
            ('target_release', 'character varying(64)')), 1):
        added('column:'+table+'_pkey.'+column, [index, sqltype, False, '', '', None])
    added('trigger:'+table+'.ingestion_schema_transition_immutable',
        ['O', 'CREATE TRIGGER ingestion_schema_transition_immutable BEFORE DELETE OR UPDATE OR TRUNCATE ON '+
         table+' FOR EACH STATEMENT EXECUTE FUNCTION fresh_control.ingestion_transition_immutable()'])
    return result


def approved_receipt(extension):
    return (extension.get('migration_pins') == migration_pins()
        and extension.get('catalogue_delta_digest') in
            {digest(catalogue_delta(bootstrap=value)) for value in (False, True)}
        and extension.get('previous_release') == PREVIOUS_RELEASE
        and extension.get('before_schema_digest') == BEFORE_SCHEMA
        and extension.get('before_guard_digest') == BEFORE_GUARD)


def require_specification(spec):
    previous = spec['previous_release']
    if (spec['migration_pins'] != migration_pins()
            or spec['catalogue_delta'] not in [catalogue_delta(bootstrap=v) for v in (False, True)]
            or previous['manifest_sha256'] != PREVIOUS_RELEASE
            or previous['source_commit'] != PREVIOUS_COMMIT):
        raise ValueError('Only the exact released recovered-action transition is supported')
