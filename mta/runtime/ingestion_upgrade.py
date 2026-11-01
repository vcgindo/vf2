"""Explicitly admitted source origins; immutable producer seals stay intact.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from mta.serialization import digest
from mta.runtime.ingestion_context import BASELINE_RELEASE
from mta.runtime.ingestion_admission import BASELINE_MANIFEST

BASELINE_IDENTITY=dict(schema='vectorflow-native-release-source-v1',
    source_commit=BASELINE_RELEASE,manifest_sha256=BASELINE_MANIFEST,
    migrations_digest='85586e2de8f8903a46e36ba5a780bdfd0878119e6624e4f3de878ca6c43603ea',
    source_files_digest='2b1da9eaeb3d56c3e2269c45b632eeab71981c98e500ea096cfaaf374d6e8889',
    implementation_sha256='7da39f8552197ebbd7ca68148a03e4ed3423600d3fc8c425fcaa0c292472dbe4')
BASELINE_PROFILE='57d8ce8f55b455b9bedd1152a41aeda843f35757479092e25b2bb3e179a32f56'
BASELINE_EXECUTION=dict(adapter_digest='056666ac3ae6c30cb9a519d2d6bf25ddefb7eb0163bd85b5028d2f468c03ba1d',
    source_manifest_digest='ba6a954d008134fc300e5e1b641cbf0ffe25a224140b5932f0a95cc0034650c5',
    closing_projection_version='native-closing-locations-v2')
_audit=ContextVar('ingestion_upgrade_origin',default=None)


def baseline(capability):
    if capability['release_identity'] != BASELINE_IDENTITY or capability['profile_digest'] != BASELINE_PROFILE:
        raise ValueError('Only the reviewed 687adcf native origin may upgrade')
    if capability['implementation_sha256'] != BASELINE_IDENTITY['implementation_sha256']:
        raise ValueError('Baseline producer differs')
    return capability


def audited_capability(capability):
    scoped=_audit.get()
    return scoped is not None and scoped['capability']==baseline(capability)


def original_catalogue(cursor):
    """Authenticate exact OLD catalogue before any migration or grant."""
    from mta.mdm import owned_namespace as owned
    from mta.runtime.ingestion_admission import registration
    from release.native_schema import schema_digest
    original,capability=registration(cursor);baseline(capability)
    actual=owned._registered_identity(cursor)
    database=owned._database_identity(cursor)
    owned._validate_identity(database,actual,owned._catalogue_evidence(cursor,database,actual),
        artifact_sha256=actual['artifact_sha256'],adapter_sha256=BASELINE_IDENTITY['implementation_sha256'])
    if owned._read_application_capability(cursor,actual)!=capability:
        raise ValueError('Baseline capability or guards differ')
    owned._check_application_write_guards(cursor,actual)
    catalogue=owned._application_catalogue(cursor)
    expected=owned._check_application_grants(catalogue,actual,logistics=True,production=True)
    owned._check_logistics_schema(cursor,catalogue,actual)
    expected['schema_digest']=schema_digest(cursor)
    if any(capability[k]!=v for k,v in expected.items()):
        raise ValueError('Baseline catalogue/schema/grants differ before upgrade')
    return original,capability


def _origin(source):
    from django.db import connection
    scoped=_audit.get()
    if scoped is not None:
        if scoped['source_digest']!=source.digest or digest(source.receipt)!=source.digest:
            raise ValueError('Upgrade audit source differs')
        return scoped
    # Same implementation bytes are not the same source artifact. In particular
    # a presentation-only patch still needs original-owner validation, without a
    # current-commit database permission. Never infer authority from a hash.
    from mta.mdm.initialization import current_implementation_digest
    from mta.runtime.ingestion_admission import _process_release,_admit,registration
    import os
    release=_process_release(os.environ.get('VF_NATIVE_RELEASE_COMMIT'),os.environ.get('VF_NATIVE_RELEASE_SHA256'))
    if (source.implementation_digest==current_implementation_digest()
            and source.receipt.get('owned_namespace',{}).get('release_identity')==release):
        return None
    from mta.runtime.initialization_models import ProductionInitialization
    owner=ProductionInitialization.objects.get(source=source)
    with connection.cursor() as cursor:
        _admit(cursor,owner.pk,release,pending=True)
        original,capability=registration(cursor)
        if capability['release_identity']!=BASELINE_IDENTITY:
            return _certified_origin(cursor,source,owner,release,original,capability)
        baseline(capability)
    return dict(source_digest=source.digest,capability=capability,original=original)


def _certified_origin(cursor,source,owner,release,original,capability):
    """Preserve the actual producer after schema-based reader admission.

    No producer is inferred from a matching hash or a caller's metadata. The
    original immutable registration/certificate/integration and live target
    schema admission have already joined in _origin. There is no permission
    row for the currently executing application commit. Historical baseline
    auditing stays pinned above for the old format that actually needs it.
    """
    from mta.runtime.ingestion_admission import _certificate
    cert=_certificate(owner.pk)
    from mta.runtime.ingestion_context import sha
    sha(cert['receipt_digest']);sha(cert['populations']['integration'])
    origin=capability['release_identity']
    if (digest(source.receipt)!=source.digest or cert['source_digest']!=source.digest
            or str(cert['initialization_id'])!=str(owner.pk)
            or str(cert['namespace'])!=original['registration_id']
            or cert['database_name']!=original['database_name']
            or cert['database_oid']!=original['database_oid']
            or cert['release_digest']!=origin['manifest_sha256']
            or source.implementation_digest!=capability['implementation_sha256']
            or original['adapter_sha256']!=capability['implementation_sha256']
            or origin['implementation_sha256']!=capability['implementation_sha256']
            or source.receipt.get('owned_namespace')!={**capability,'artifact_sha256':original['artifact_sha256']}):
        raise ValueError('Certified fresh origin differs from its original producer')
    return dict(source_digest=source.digest,capability=capability,original=original,
                integration_digest=cert['populations']['integration'])


def implementation_for(source):
    origin=_origin(source)
    if origin is None:
        from mta.mdm.initialization import implementation_digest
        return implementation_digest()
    return origin['capability']['implementation_sha256']


def binding_for(receipt):
    from mta.runtime.mdm_models import MdmSource
    source=MdmSource.objects.get(digest=digest(receipt))
    if source.receipt!=receipt:
        raise ValueError('Original source receipt differs')
    origin=_origin(source)
    if origin is None:
        return False
    expected={**origin['capability'],'artifact_sha256':origin['original']['artifact_sha256']}
    if receipt.get('owned_namespace')!=expected:
        raise ValueError('Original sealed namespace receipt differs')
    return True


def execution_for(source,seal):
    origin=_origin(source)
    if origin is None:
        return None
    if 'integration_digest' in origin:
        from mta.runtime.ingestion_context import sha
        from mta.mdm.location_projection import VERSION
        if (seal.source_id!=source.pk or digest(seal.receipt)!=seal.digest
                or seal.digest!=origin['integration_digest']):
            raise ValueError('Certified original integration producer differs')
        values={key:seal.receipt.get(key) for key in ('adapter_digest','source_manifest_digest','closing_projection_version')}
        sha(values['adapter_digest']);sha(values['source_manifest_digest'])
        if values['closing_projection_version']!=VERSION:
            raise ValueError('Certified origin requires its corrected closing projection')
        return values
    if digest(seal.receipt)!=seal.digest or any(seal.receipt.get(k)!=v for k,v in BASELINE_EXECUTION.items()):
        raise ValueError('Original integration producer differs')
    return dict(BASELINE_EXECUTION)


@contextmanager
def auditing(owner,original,capability):
    """Private maintenance-only scope; entered after exact baseline admission."""
    baseline(capability)
    token=_audit.set(dict(source_digest=owner.source.digest,original=original,capability=capability))
    try:
        yield
    finally:
        _audit.reset(token)
