"""Bounded certified readiness. Full opening audit remains an installation action.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
import os
from uuid import UUID
from django.db import connection, transaction
from mta.serialization import digest
from mta.runtime.ingestion_context import CONTRACT, BASELINE_RELEASE, FAMILIES, RevisionCut, sha
from mta.runtime import ingestion_authority as authority
from mta.runtime.ingestion_ownership import require_guard_coverage
from mta.presentation.request_scope import once_per_request
from mta.presentation.identity_reuse import certified_readiness

BASELINE_MANIFEST = '2b7346f3382d78e3ea2d8c352f9854b6f59b5e13cf53d27aa9fa68216f478818'
EPOCHS = ('master_epoch', 'configuration_epoch', 'fact_epoch', 'operational_epoch', 'action_epoch')
CERT_FIELDS = ('id', 'initialization_id', 'contract', 'database_name', 'database_oid', 'namespace',
    'source_digest', 'content_digest', 'configuration_digest', 'schema_digest', 'guard_digest',
    'release_digest', 'populations', 'families', 'authority_roles')
REVISION_FIELDS = ('id', 'initialization_id', 'parent_id', 'run_id', 'master_epoch',
    'configuration_epoch', 'partitions')


def receipt(values):
    return digest({k: str(v) if isinstance(v, UUID) else v for k, v in values.items()})


def security_digest(cursor, roles):
    """Catalogue cost depends on schema size, never on business row count."""
    if type(roles) is not list or len(roles) != 3 or len(set(roles)) != 3:
        raise ValueError('Exact owner, installer and runtime roles required')
    owner, installer, runtime = roles
    cursor.execute('SELECT rolname,oid::bigint,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,'
        'rolreplication,rolbypassrls,rolinherit FROM pg_roles WHERE rolname=ANY(%s) ORDER BY rolname',
        [roles + [authority.REGISTRAR]])
    role_rows = cursor.fetchall()
    if len(role_rows) != 4 or any(any(row[3:]) for row in role_rows):
        raise ValueError('Ingestion authority role attributes differ')
    if {r[0]: r[2] for r in role_rows} != {owner: False, installer: True, runtime: True, authority.REGISTRAR: False}:
        raise ValueError('Ingestion authority login separation differs')
    cursor.execute("SELECT pg_has_role(%s,%s,'MEMBER'),pg_has_role(%s,%s,'MEMBER')",
        [runtime, owner, runtime, authority.REGISTRAR])
    if cursor.fetchone() != (False, False):
        raise ValueError('Runtime can assume ingestion authority')
    cursor.execute("SELECT pg_get_userbyid(c.relowner),pg_get_userbyid(n.nspowner) FROM pg_class c "
        "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=to_regclass(%s)", [authority.TABLE])
    if cursor.fetchone() != (authority.REGISTRAR, authority.REGISTRAR):
        raise ValueError('Release transition has no independent registrar owner')
    require_guard_coverage(cursor)
    from mta.mdm.owned_namespace import _application_catalogue
    catalogue = _application_catalogue(cursor)
    from mta.runtime.ingestion_ownership import is_revision_guard
    if not any(is_revision_guard(f) and f['owner'] == next(r[1] for r in role_rows if r[0]==owner)
               for f in catalogue['functions']):
        raise ValueError('Ingestion revision function differs from its frozen implementation')
    cursor.execute('SELECT roleid::bigint,member::bigint,grantor::bigint,admin_option FROM pg_auth_members '
        'WHERE roleid=ANY(%s::oid[]) OR member=ANY(%s::oid[]) ORDER BY 1,2,3',
        [[r[1] for r in role_rows], [r[1] for r in role_rows]])
    memberships = cursor.fetchall()
    return digest(dict(roles=role_rows, memberships=memberships, catalogue=catalogue))


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def registration(cursor):
    from mta.mdm.owned_namespace import (_registered_identity, _receipt_identity,
        CAPABILITY_FIELDS, PRODUCTION_APPLICATION_POLICY)
    original = _registered_identity(cursor)
    cursor.execute('SELECT binding FROM fresh_control.application_capability WHERE singleton IS TRUE')
    row = cursor.fetchone()
    if row is None:
        raise ValueError('Original application capability absent')
    capability = _json(row[0])
    if (type(capability) is not dict or set(capability) != CAPABILITY_FIELDS
            or capability.get('policy') != PRODUCTION_APPLICATION_POLICY
            or capability.get('receipt_digest') != digest(
                {k: v for k, v in capability.items() if k != 'receipt_digest'})):
        raise ValueError('Original capability receipt differs')
    release = capability['release_identity']
    if (type(release) is not dict or capability['original_registration'] != _receipt_identity(original)
            or not (capability['original_implementation_sha256'] == capability['implementation_sha256']
                == original['adapter_sha256'] == release.get('implementation_sha256'))):
        raise ValueError('Original capability producer/registration chain differs')
    from release.native_identity import SCHEMA
    if (set(release) != {'schema','source_commit','manifest_sha256','source_files_digest',
                         'migrations_digest','implementation_sha256'} or release['schema'] != SCHEMA):
        raise ValueError('Original native release identity shape differs')
    for key in ('manifest_sha256','source_files_digest','migrations_digest','implementation_sha256'):
        sha(release[key])
    for key in ('profile_digest','objects_digest','grants_digest','schema_digest'):
        sha(capability[key])
    return original, capability


def _certificate(initialization_id):
    from mta.runtime.ingestion_models import InitializationCertification
    value = InitializationCertification.objects.filter(initialization_id=initialization_id,
        status='CERTIFIED').values(*CERT_FIELDS, 'receipt_digest').get()
    body = {key: value[key] for key in CERT_FIELDS}
    if (value['contract'] != CONTRACT or value['families'] != list(FAMILIES)
            or value['receipt_digest'] != receipt(body)):
        raise ValueError('Initialization certification contract/receipt differs')
    for key in ('source_digest', 'content_digest', 'configuration_digest', 'schema_digest',
                'guard_digest', 'release_digest', 'receipt_digest'):
        sha(value[key])
    if (type(value['populations']) is not dict
            or set(value['populations']) != {'opening_manifest','integration'}):
        raise ValueError('Certified population roots are absent')
    for root in value['populations'].values():
        sha(root)
    return value


def _origin_transition(body,cert):
    """Fresh certified origins may advance only from that same original release.

    The surrounding validator still authenticates registration/certificate joins,
    the original activated row, audit receipt and live catalogue. An older
    installation certified under a different producer keeps its pinned bridge.
    """
    if body['original_commit']!=body['target_commit']:
        if ((body['original_commit'],body['original_release'])!=(BASELINE_RELEASE,BASELINE_MANIFEST)
                and body['original_release']!=cert['release_digest']):
            raise ValueError('Unreviewed original release transition')
    elif body['original_release']!=body['target_release']:
        raise ValueError('Same-commit manifest substitution prohibited')


def _activation_metadata(cursor, body):
    """Authenticate immutable certificate/registrar joins, not a live catalogue.

    Historical activations describe their original catalogue. A separately
    authenticated schema transition may replace the *live* catalogue comparison,
    never the original certificate or its chain of custody.
    """
    authority.validate(body)
    cert = _certificate(body['initialization_id'])
    from release.native_schema import schema_digest
    cursor.execute('SELECT current_database(),oid::bigint FROM pg_database WHERE datname=current_database()')
    if cursor.fetchone() != (body['database_name'], body['database_oid']):
        raise ValueError('Foreign database authority')
    original, capability = registration(cursor)
    original_release = capability['release_identity']
    if (body['original_commit'] != original_release['source_commit']
            or body['original_release'] != original_release['manifest_sha256']
            or body['namespace'] != original['registration_id']
            or body['original_registration_digest'] != digest(original)
            or body['original_capability_digest'] != capability['receipt_digest']):
        raise ValueError('Original namespace/capability identity differs')
    _origin_transition(body,cert)
    expected = dict(contract=cert['contract'], database_name=cert['database_name'],
        database_oid=cert['database_oid'], namespace=str(cert['namespace']),
        source_digest=cert['source_digest'], certification_digest=cert['receipt_digest'],
        schema_digest=cert['schema_digest'], guard_digest=cert['guard_digest'])
    if any(body[k] != v for k, v in expected.items()):
        raise ValueError('Release transition/certification join differs')
    if body['target_release'] != cert['release_digest']:
        # A later compatible code release may borrow the same immutable data
        # certificate. Its original activation must still exist and validate;
        # only an independently reviewed registrar append admits the new code.
        certified_origin = authority.read(cursor, body['initialization_id'], cert['release_digest'])
        if (certified_origin['target_release'] != cert['release_digest']
                or any(certified_origin[k] != body[k]
                       for k in authority.FIELDS - {'target_commit', 'target_release'})):
            raise ValueError('Compatible release changed original certified ownership')
        _activation_metadata(cursor, certified_origin)
    from mta.runtime.ingestion_models import IngestionReleaseCompatibility
    audit = IngestionReleaseCompatibility.objects.get(initialization_id=body['initialization_id'],
        target_release=body['target_release'])
    values = dict(original_release=body['original_release'], target_release=body['target_release'],
        original_commit=body['original_commit'], target_commit=body['target_commit'],
        contract=CONTRACT, original_registration_digest=body['original_registration_digest'],
        schema_digest=body['schema_digest'], certification_digest=body['certification_digest'])
    if any(getattr(audit, k) != v for k, v in values.items()) or audit.receipt_digest != digest(values):
        raise ValueError('Release compatibility audit differs')
    return cert


def effective_schema(cursor, body):
    """Authenticate direct code inheritance without extending the real DDL bound."""
    cert = _activation_metadata(cursor, body)
    expected_schema, expected_guard = cert['schema_digest'], cert['guard_digest']
    chain=[]; current=body; seen=set(); real_count=0; guard_transition=False; ownership_transition=False; anchor=None
    link=authority.read_schema_transition(cursor,current)
    # Original schema admission plus the three reviewed finite extensions.
    # Historical catalogues authenticate metadata; only the last is compared live.
    while True:
        if current['target_release'] in seen:
            raise ValueError('Schema transition contains a cycle')
        seen.add(current['target_release'])
        extension=link
        if extension is None:
            break
        if extension['contract']==authority.CODE_SCHEMA_CONTRACT:
            parent=authority.read(cursor,current['initialization_id'],extension['anchor_release'])
            if (_activation_metadata(cursor,parent)!=cert or digest(parent)!=extension['anchor_authority_digest']
                    or extension['target_commit']!=current['target_commit']
                    or extension['certification_digest']!=cert['receipt_digest']
                    or any(parent[k]!=current[k] for k in authority.FIELDS-{'target_commit','target_release'})):
                raise ValueError('Code-only schema anchor ownership differs')
            parent_link=authority.read_schema_transition(cursor,parent)
            if parent_link and parent_link['contract']==authority.CODE_SCHEMA_CONTRACT:
                raise ValueError('Code-only schema anchor cannot be another code-only release')
            if (extension['anchor_schema_receipt_digest']!=(digest(parent_link) if parent_link else cert['receipt_digest'])
                    or (parent_link is None and parent['target_release']!=cert['release_digest'])):
                raise ValueError('Code-only schema anchor receipt differs')
            chain.append(extension);current=parent;link=parent_link
            continue
        from mta.runtime.report_guard_transition import MIGRATION_NAME,approved_receipt
        from mta.runtime import accepted_state_transition as ownership
        if any(pin[0] in {name for name,_ in ownership.PINS} for pin in extension.get('migration_pins',[])):
            if ownership_transition or guard_transition or not ownership.approved_receipt(extension):
                raise ValueError('Exact accepted-state schema transition required after report guards')
            ownership_transition=True
        elif any(pin[0]==MIGRATION_NAME for pin in extension.get('migration_pins',[])):
            if guard_transition or not approved_receipt(extension):
                raise ValueError('Exact released report guard schema transition required')
            guard_transition=True
        else:
            if real_count==4:
                raise ValueError('Schema transition exceeds the reviewed four-admission boundary')
            real_count+=1
        if anchor is None:
            anchor=current;anchor_receipt=digest(extension)
        parent=authority.read(cursor,current['initialization_id'],extension['previous_release'])
        if (_activation_metadata(cursor,parent)!=cert
                or digest(parent)!=extension['previous_authority_digest']
                or extension['certification_digest']!=cert['receipt_digest']
                or any(parent[k]!=current[k] for k in authority.FIELDS-{'target_commit','target_release'})
                or extension['target_commit']!=current['target_commit']):
            raise ValueError('Schema transition changed original certified ownership')
        chain.append(extension);current=parent
        link=authority.read_schema_transition(cursor,current)
    if guard_transition and real_count!=4:
        raise ValueError('Report guard transition requires the original four schema admissions')
    if ownership_transition and not guard_transition:
        raise ValueError('Accepted-state transition requires the released report guard ancestry')
    for extension in reversed(chain):
        if extension['contract']==authority.CODE_SCHEMA_CONTRACT:
            if extension['schema_digest']!=expected_schema or extension['guard_digest']!=expected_guard:
                raise ValueError('Code-only inherited catalogue differs from its schema anchor')
            continue
        if (extension['before_schema_digest']!=expected_schema
                or extension['before_guard_digest']!=expected_guard):
            raise ValueError('Schema transition predecessor catalogue differs')
        expected_schema,expected_guard=extension['schema_digest'],extension['guard_digest']
    if anchor is None:
        # append() validates the original certified activation before inserting
        # its first row. That already-authenticated body is its own schema
        # anchor; requiring the not-yet-inserted row makes bootstrap circular.
        # Later releases still require the persisted certified origin, and
        # _admit() always reads its requested activation from authority first.
        anchor=(body if body['target_release']==cert['release_digest'] else
                authority.read(cursor,body['initialization_id'],cert['release_digest']))
        anchor_receipt=cert['receipt_digest']
    return cert,anchor,expected_schema,expected_guard,anchor_receipt


def validate_activation(cursor, body):
    """Validate immutable ownership and the exact effective live catalogue."""
    cert,anchor,expected_schema,expected_guard,_=effective_schema(cursor,body)
    from release.native_schema import schema_digest
    if (schema_digest(cursor) != expected_schema
            or security_digest(cursor, cert['authority_roles']) != expected_guard):
        raise ValueError('Current schema, grants, roles or guards differ')
    return cert


@lru_cache(maxsize=4)
def _process_release(commit, manifest):
    from release.native_identity import require_current
    actual = require_current()
    if (actual['source_commit'], actual['manifest_sha256']) != (commit, manifest):
        raise ValueError('Independent process release pins differ')
    return actual


@dataclass(frozen=True)
class CertifiedReadiness:
    initialization_id: str
    source_digest: str
    certification_digest: str
    master_revision_id: str
    configuration_digest: str
    revisions: RevisionCut


def _admit(cursor, initialization_id, release, *, pending=False):
    body = authority.read(cursor, initialization_id, release['manifest_sha256'])
    if body['target_commit'] != release['source_commit']:
        raise ValueError('Release authority targets another commit')
    cert = validate_activation(cursor, body)
    from mta.runtime.initialization_models import ProductionInitialization
    from mta.runtime.ingestion_models import IngestionRevisionState, MasterInputRevision
    owner = ProductionInitialization.objects.values('source__digest', 'input_digest', 'configuration_digest',
        'input_manifest_digest').get(pk=initialization_id)
    if (owner['source__digest'] != cert['source_digest'] or owner['input_digest'] != cert['content_digest']
            or owner['configuration_digest'] != cert['configuration_digest']
            or cert['populations'].get('opening_manifest') != owner['input_manifest_digest']):
        raise ValueError('Certified opening metadata differs')
    state = IngestionRevisionState.objects.values(*EPOCHS).get(initialization_id=initialization_id)
    revisions = MasterInputRevision.objects.filter(initialization_id=initialization_id, status='ACCEPTED')
    if pending:
        revision = revisions.filter(master_epoch__lte=state['master_epoch'],
            configuration_epoch__lte=state['configuration_epoch']).order_by('-master_epoch','-configuration_epoch').values(
                *REVISION_FIELDS,'receipt_digest').first()
        if revision is None:
            raise ValueError('No accepted base master revision for preparation')
    else:
        revision = revisions.filter(master_epoch=state['master_epoch'],
            configuration_epoch=state['configuration_epoch']).values(*REVISION_FIELDS,'receipt_digest').get()
    if revision['receipt_digest'] != receipt({k: revision[k] for k in REVISION_FIELDS}):
        raise ValueError('Accepted master revision receipt differs')
    if type(revision['partitions']) is dict and set(revision['partitions']) == {'opening_master_root'}:
        sha(revision['partitions']['opening_master_root'])
    else:
        from mta.runtime.master_revisions import validate
        validate(revision['partitions'],initialization_id)
        from mta.runtime.master_revisions import PHASE_CONTRACT
        if (revision['partitions'].get('contract')==PHASE_CONTRACT
                and revision['partitions']['revision_cut'][:2]!=[revision['master_epoch'],revision['configuration_epoch']]):
            raise ValueError('Accepted phase master revision counters differ')
    # Source/integration identity is bounded: exactly the sealed thirteen-family roster.
    from mta.runtime.mdm_models import MdmSource, MdmFamilySource
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    source = MdmSource.objects.get(digest=cert['source_digest'])
    seal = MdmSourceIntegration.objects.get(source=source)
    families = {'1': digest(source.receipt['families']['1'])}
    families.update({str(k): v for k, v in MdmFamilySource.objects.filter(source=source).values_list('master_id','digest')})
    if (digest(source.receipt) != source.digest or digest(seal.receipt) != seal.digest
            or families != seal.receipt.get('families')
            or set(families) != {str(i) for i in FAMILIES}
            or cert['populations'].get('integration') != seal.digest):
        raise ValueError('Certified source/family integration differs')
    return CertifiedReadiness(str(initialization_id), cert['source_digest'], cert['receipt_digest'],
        str(revision['id']), cert['configuration_digest'], RevisionCut(*(state[k] for k in EPOCHS)))


@once_per_request
@certified_readiness
def readiness(initialization_id):
    """Validate certified metadata in its own consistent read-only snapshot.

    Successful serving reads reuse metadata only while the database/session is
    unchanged. Offline admission and writes always perform this complete check.
    No public arbitrary release override, TTL, data-hash skip, opening scan or
    accepted-day inference. Caller must not hold an unrelated writer transaction.
    """
    if connection.in_atomic_block:
        raise ValueError('Certified readiness owns its read-only snapshot')
    release = _process_release(os.environ.get('VF_NATIVE_RELEASE_COMMIT'), os.environ.get('VF_NATIVE_RELEASE_SHA256'))
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        return _admit(cursor, initialization_id, release)


def preparation_readiness(initialization_id):
    """A current cut plus its accepted base; this does not admit stale serving."""
    if connection.in_atomic_block:
        raise ValueError('Preparation readiness owns its read-only snapshot')
    release = _process_release(os.environ.get('VF_NATIVE_RELEASE_COMMIT'),os.environ.get('VF_NATIVE_RELEASE_SHA256'))
    with transaction.atomic(),connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        return _admit(cursor,initialization_id,release,pending=True)


def preparation_source(source_digest):
    from mta.runtime.ingestion_models import InitializationCertification
    cert=InitializationCertification.objects.filter(source_digest=source_digest).values('initialization_id').first()
    if cert is None:
        certified_source(source_digest)  # Missing activated authority is still an error.
        return None
    return preparation_readiness(cert['initialization_id'])


def certified_source(source_digest):
    """Opt-in is persisted authority, not an environment bypass or hash fallback.

    Old installations with no certification retain their exact full-check path.
    An incomplete or invalidated certificate is an error, never an old-path retry.
    """
    from mta.runtime.ingestion_models import InitializationCertification
    from mta.runtime.mdm_models import MdmSource
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('mta.fresh_mta_initializationcertification')")
        if cursor.fetchone()[0] is None:
            return None
    cert = InitializationCertification.objects.filter(source_digest=source_digest).values('initialization_id').first()
    if cert is None:
        # Missing certificate after activation must not silently fall back.
        with connection.cursor() as cursor:
            cursor.execute('SELECT to_regclass(%s)', [authority.TABLE])
            if cursor.fetchone()[0] is not None:
                cursor.execute('SELECT 1 FROM fresh_control.ingestion_release_authority '
                    "WHERE body->>'source_digest'=%s LIMIT 1", [source_digest])
                if cursor.fetchone() is not None:
                    raise ValueError('Activated ingestion certification is missing')
        return None
    state = readiness(cert['initialization_id'])
    if state.source_digest != source_digest:
        raise ValueError('Selected source differs from certified source')
    return MdmSource.objects.get(digest=source_digest)
