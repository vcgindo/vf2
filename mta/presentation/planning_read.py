"""Named operational inputs and checked persisted report projections only."""
from types import SimpleNamespace
from mta.presentation.context import selected_run, permission_catalogue, PublicationUnavailable
from mta.presentation.selective import image_rows
from mta.presentation import hierarchy
from mta.presentation.terminal_supplement import terminal_ancillary
from mta.presentation.excess_storage import read_excess
from mta.presentation.expedite_storage import read_expedite
from mta.presentation.fulfillment_storage import read_fulfillment


def terminal_git_reports(rationed, ancillary):
    # GenerateGoodsInTransitMaster.sql INSERT requires rationed.GIT>0.
    # GoodsInTransitTransporterMaster.sql INSERT INNER JOINs InTransitData and
    # requires the same positive GIT. Empty is proved here, never a fallback.
    if ancillary['InTransitData'] or any(r['GIT'] is not None and r['GIT'] > 0 for r in rationed):
        raise PublicationUnavailable('planning_nonempty_transit_projection_not_published')
    return dict(git=[], transporter=[], transit=ancillary['InTransitData'])


def planning_overview_context():
    run = selected_run()
    if run.kind == 'LEGACY_UI_FIXTURE':
        from mta.presentation.fixture import bpr_ancillary
        ancillary = bpr_ancillary(run)
    else:
        ancillary = terminal_ancillary(run)
    rationed = image_rows(run, 'reports/bpr/vf_RationedReqReport')
    reports = terminal_git_reports(rationed, ancillary)
    importer = {name: image_rows(run, 'closing/importer/' + name) for name in (
        'MasterData', 'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData',
        'SKUDescriptionTbl', 'SiteDescriptionTbl')}
    standards = image_rows(run, 'closing/dbm/SKULocStandardAttributes')
    native = dict(BPRReports=[{'vf_RationedReqReport': rationed}], ClosingState=[dict(
        importer=importer, dbm={'SKULocStandardAttributes': standards},
        orders={'SpikeOrderData': image_rows(run, 'closing/orders/SpikeOrderData')},
        btr={'ExpediteDispatches': image_rows(run, 'closing/btr/ExpediteDispatches')})])
    reports.update(excess=read_excess(run, output=native), expedite=read_expedite(run, output=native),
                   fulfillment=read_fulfillment(run, output=native)['summary'])
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    return SimpleNamespace(run=run, attributes=importer, standards=standards, reports=reports)
