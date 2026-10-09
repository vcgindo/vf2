"""Explicit dispatch for installed MDM families."""
from importlib import import_module

from mta.presentation.context import PublicationUnavailable
from mta.runtime.mdm_models import MdmFamilySource


NAMES = {1: 'sku', 2: 'location', 3: 'skuloc', 4: 'sob', 5: 'moq', 6: 'stop_pipo',
         7: 'add_po', 8: 'add_pipo', 9: 'add_target_norm',
         10: 'season', 11: 'season_absolute', 12: 'season_percentage', 13: 'force'}


def module(master_id, boundary='current'):
    master_id = int(master_id)
    name = NAMES[master_id]
    if master_id in (7, 8, 9) and boundary in ('tasks', 'reads'):
        return import_module('mta.mdm.phase_controls_' + boundary)
    if master_id == 6 and boundary in ('tasks', 'reads'):
        return import_module('mta.mdm.stop_pipo_' + boundary)
    if master_id in (10, 11, 12) and boundary in ('tasks', 'reads'):
        return import_module('mta.mdm.season_' + boundary)
    if master_id in (4, 5) and boundary in ('tasks', 'reads'):
        return import_module('mta.mdm.supplier_' + boundary)
    if boundary == 'tasks':
        name = 'tasks' if master_id == 1 else name + '_tasks'
    elif boundary == 'reads':
        name = 'task_reads' if master_id == 1 else name + '_reads'
    return import_module('mta.mdm.' + name)


def require_installed(source, master_id):
    master_id = int(master_id)
    if master_id not in NAMES:
        raise ValueError('MDM family is not delivered')
    if master_id in (7, 8, 9):
        from mta.mdm.phase_controls_source import require_installed as require_phase
        require_phase(source)
    if master_id == 6:
        from mta.mdm.stop_pipo_source import require_installed as require_stop
        require_stop(source)
    if master_id in (10, 11, 12):
        from mta.mdm.season_source import require_installed as require_season
        require_season(source)
    if master_id == 13:
        from mta.mdm.force_source import require_installed as require_force
        require_force(source)
    if master_id in (4, 5):
        from mta.mdm.supplier_source import require_installed as require_supplier
        require_supplier(source, master_id)
    from mta.mdm.daily_source import SCHEMA, FORCE_SCHEMA, SEASON_SCHEMA, require_binding
    if source.receipt.get('schema') in (SCHEMA, FORCE_SCHEMA, SEASON_SCHEMA):
        require_binding(source,artifact_sha256=source.receipt['artifact_sha256'],
                        artifact_schema=source.receipt['artifact_schema'])
        return
    if master_id not in (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
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
    if int(master_id) in (7, 8, 9):
        from mta.runtime.mdm_phase_controls_models import MdmDraftAddPipo
        return MdmDraftAddPipo, 'DraftId'
    if int(master_id) == 6:
        from mta.runtime.mdm_stop_pipo_models import MdmDraftStopPipo
        return MdmDraftStopPipo, 'DraftId'
    if int(master_id) in (10, 11, 12):
        from mta.runtime.mdm_season_models import MdmDraftSeason
        return MdmDraftSeason, 'DraftId'
    if int(master_id) == 13:
        from mta.runtime.mdm_force_models import MdmDraftForce
        return MdmDraftForce, 'DraftId'
    if int(master_id) in (4, 5):
        from mta.runtime.mdm_supplier_models import MdmDraftSob, MdmDraftMoq
        return (MdmDraftSob if int(master_id) == 4 else MdmDraftMoq), 'DraftId'
    if int(master_id) == 3:
        from mta.runtime.mdm_skuloc_models import MdmDraftSkuLoc
        return MdmDraftSkuLoc, 'DraftId'
    return (mdm_models.MdmDraftSku, 'Draftid') if int(master_id) == 1 else (mdm_models.MdmDraftLocation, 'DraftId')
