"""One reviewed baseline-to-ingestion transition; immutable origins stay intact.

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
    # Do not change ordinary fresh-release checks or infer authority from a hash.
    from mta.mdm.initialization import current_implementation_digest
    if source.implementation_digest==current_implementation_digest():
        return None
    from mta.runtime.ingestion_admission import _process_release,_admit,registration
    import os
    release=_process_release(os.environ.get('VF_NATIVE_RELEASE_COMMIT'),os.environ.get('VF_NATIVE_RELEASE_SHA256'))
    from mta.runtime.initialization_models import ProductionInitialization
    owner=ProductionInitialization.objects.get(source=source)
    with connection.cursor() as cursor:
        _admit(cursor,owner.pk,release,pending=True)
        original,capability=registration(cursor);baseline(capability)
    return dict(source_digest=source.digest,capability=capability,original=original)


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
    if _origin(source) is None:
        return None
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
