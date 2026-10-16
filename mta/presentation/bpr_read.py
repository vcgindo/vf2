"""BPR's exact persisted consumer dependencies with explicit ancillary inputs."""
from types import SimpleNamespace
from django.conf import settings
from mta.presentation.context import selected_run, permission_catalogue, PublicationUnavailable
from mta.presentation.selective import image_rows
from mta.presentation import hierarchy
from mta.presentation.terminal_supplement import terminal_ancillary


def bpr_context():
    run = selected_run()
    fixture=getattr(run,'kind',None)=='LEGACY_UI_FIXTURE'
    daily = (getattr(run, 'kind', None) == 'DAILY_CHAIN' and
             getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False))
    if fixture:
        from mta.presentation.fixture import bpr_ancillary,bpr_image_rows
        ancillary=bpr_ancillary(run)
        reader=bpr_image_rows
    elif daily:
        from mta.presentation.daily_preparation import ancillary_rows
        ancillary = ancillary_rows(run)
        from mta.presentation.logistics_live import serving_transit_rows
        ancillary['InTransitData'] = serving_transit_rows(run,ancillary['InTransitData'])
        reader=image_rows
    else:
        ancillary = terminal_ancillary(run)
        reader=image_rows
    importer = {name: reader(run, 'closing/importer/' + name) for name in (
        'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    reports = {name: reader(run, 'reports/bpr/' + name) for name in ('BPR_Table', 'vf_RationedReqReport')}
    output = dict(BPRReports=[reports], ClosingState=[dict(importer=importer,
        dbm={'SKULocStandardAttributes': reader(run, 'closing/dbm/SKULocStandardAttributes')})],
        BTRFinal=[{'BufferTrendPhysicalInv': reader(run, 'closing/btr/BufferTrendPhysicalInv')}])
    if not fixture and not daily and any(row['GIT'] != 0 for row in reports['BPR_Table']):
        raise PublicationUnavailable('terminal_empty_transit_conflicts_with_published_git')
    return SimpleNamespace(run=run, output=output, ancillary=ancillary)
