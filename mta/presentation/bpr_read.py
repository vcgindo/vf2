"""BPR's exact persisted consumer dependencies with explicit ancillary inputs."""
from types import SimpleNamespace
from mta.presentation.context import selected_run, permission_catalogue, PublicationUnavailable
from mta.presentation.selective import image_rows
from mta.presentation import hierarchy
from mta.presentation.terminal_supplement import terminal_ancillary


def bpr_context():
    run = selected_run()
    ancillary = terminal_ancillary(run)
    importer = {name: image_rows(run, 'closing/importer/' + name) for name in (
        'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    reports = {name: image_rows(run, 'reports/bpr/' + name) for name in ('BPR_Table', 'vf_RationedReqReport')}
    output = dict(BPRReports=[reports], ClosingState=[dict(importer=importer,
        dbm={'SKULocStandardAttributes': image_rows(run, 'closing/dbm/SKULocStandardAttributes')})],
        BTRFinal=[{'BufferTrendPhysicalInv': image_rows(run, 'closing/btr/BufferTrendPhysicalInv')}])
    if any(row['GIT'] != 0 for row in reports['BPR_Table']):
        raise PublicationUnavailable('terminal_empty_transit_conflicts_with_published_git')
    return SimpleNamespace(run=run, output=output, ancillary=ancillary)
