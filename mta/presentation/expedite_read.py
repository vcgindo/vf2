"""Selective, checksum-verified persisted inputs for Expedite consumers."""
from types import SimpleNamespace

from mta.presentation import hierarchy
from mta.presentation.context import selected_run, permission_catalogue, PublicationUnavailable
from mta.presentation.expedite_storage import read_expedite
from mta.presentation.selective import image_rows
from mta.presentation.terminal_supplement import terminal_ancillary
from mta.runtime.models import ExpediteProjection


def expedite_context():
    run = selected_run()
    importer = {name: image_rows(run, 'closing/importer/'+name) for name in (
        'MasterData', 'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData',
        'SKUDescriptionTbl', 'SiteDescriptionTbl')}
    standards = image_rows(run, 'closing/dbm/SKULocStandardAttributes')
    native = dict(BPRReports=[{'vf_RationedReqReport': image_rows(run, 'reports/bpr/vf_RationedReqReport')}],
                  ClosingState=[dict(importer=importer, dbm={'SKULocStandardAttributes': standards},
                                     btr={'ExpediteDispatches': image_rows(run, 'closing/btr/ExpediteDispatches')})])
    try:
        rows = read_expedite(run, output=native)
    except ExpediteProjection.DoesNotExist as exc:
        raise PublicationUnavailable('selected_run_expedite_projection_not_published') from exc
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    ancillary = terminal_ancillary(run)
    return SimpleNamespace(run=run, rows=rows, importer=importer, standards=standards,
                           masters=image_rows(run, 'closing/bpr/BPRMaster'),
                           nms=image_rows(run, 'closing/consumer_context/NMSAllItems'),
                           remarks=ancillary['BPRReport_RemarkDetails'])
