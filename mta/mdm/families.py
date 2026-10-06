"""Explicit dispatch for the three delivered MDM families."""
from importlib import import_module

from mta.presentation.context import PublicationUnavailable
from mta.runtime.mdm_models import MdmFamilySource


NAMES = {1: 'sku', 2: 'location', 3: 'skuloc'}


def module(master_id, boundary='current'):
    master_id = int(master_id)
    name = NAMES[master_id]
    if boundary == 'tasks':
        name = 'tasks' if master_id == 1 else name + '_tasks'
    elif boundary == 'reads':
        name = 'task_reads' if master_id == 1 else name + '_reads'
    return import_module('mta.mdm.' + name)


def require_installed(source, master_id):
    master_id = int(master_id)
    if master_id not in NAMES:
        raise ValueError('MDM family is not delivered')
    from mta.mdm.daily_source import SCHEMA, require_binding
    if source.receipt.get('schema') == SCHEMA:
        require_binding(source,artifact_sha256=source.receipt['artifact_sha256'],
                        artifact_schema=source.receipt['artifact_schema'])
        return
    if master_id != 1:
        expected = import_module('mta.mdm.' + NAMES[master_id] + '_source').SOURCE_DIGEST
        if not MdmFamilySource.objects.filter(source=source, master_id=master_id, digest=expected).exists():
            raise PublicationUnavailable('mdm_family_not_installed')


def installed_ids(source):
    result = [1, *MdmFamilySource.objects.filter(source=source).order_by('master_id').values_list('master_id', flat=True)]
    for master_id in result:
        require_installed(source, master_id)
    return result


def draft_model(master_id):
    from mta.runtime import mdm_models
    if int(master_id) == 3:
        from mta.runtime.mdm_skuloc_models import MdmDraftSkuLoc
        return MdmDraftSkuLoc, 'DraftId'
    return (mdm_models.MdmDraftSku, 'Draftid') if int(master_id) == 1 else (mdm_models.MdmDraftLocation, 'DraftId')
