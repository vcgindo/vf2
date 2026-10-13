"""Native source and family admission; no external qualification authority."""
from mta.mdm.initialization_contract import SOURCE_SCHEMA
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


def require_native(source):
    if not isinstance(source.receipt,dict) or source.receipt.get('schema')!=SOURCE_SCHEMA or source.dll_digest!='':
        raise PublicationUnavailable('native_mdm_initialization_required')
    from mta.mdm.production_families import require_initialization
    return require_initialization(source)


def require_base(source,master_id):
    require_native(source)
    if master_id not in (1,2,3):raise ValueError('Native base family1–3 required')
    if master_id==1:return source
    from mta.runtime.mdm_models import MdmFamilySource
    expected=source.receipt['families'][str(master_id)]
    row=MdmFamilySource.objects.get(source=source,master_id=master_id)
    if row.receipt!=expected or row.digest!=digest(expected):
        raise PublicationUnavailable('native_mdm_base_family_identity_changed')
    return row


def require_owner(source,owner,family):
    if not isinstance(source.receipt,dict) or source.receipt.get('schema')!=SOURCE_SCHEMA or source.dll_digest!='':
        raise PublicationUnavailable('native_mdm_initialization_required')
    from mta.mdm.production_families import require_owner as verify
    return verify(source,owner,family)
