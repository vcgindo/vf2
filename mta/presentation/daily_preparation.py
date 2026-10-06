"""Finite production preparation boundary for one accepted daily run.

This module owns production source identity only.  Fixture builders keep their
retained binding and guards; callers must never use this identity to relabel a
fixture or to fill an absent source from another run.
"""
from django.conf import settings
from django.db import connection

from mta.presentation.context import PublicationUnavailable
from mta.presentation.selective import image_metadata
from mta.serialization import digest


CORE_IMAGES = (
    'reports/bpr/BPR_Table',
    'reports/bpr/vf_RationedReqReport',
    'closing/dbm/SKULocStandardAttributes',
    'closing/importer/MasterData',
    'closing/importer/SKUDescriptionTbl',
    'closing/importer/SiteDescriptionTbl',
    'closing/importer/SkuAttributeData',
    'closing/importer/LocationAttributeData',
    'closing/importer/SkuLocAttributeData',
)

BTR_HISTORY_IMAGES = (
    'closing/btr/SkuAttributeData',
    'closing/btr/LocationAttributeData',
    'closing/btr/SkuLocAttributeData',
    'closing/btr/BPPTrendPhysicalInv',
    'closing/btr/BufferTrendPhysicalInv',
    'closing/btr/BPPTrendDispatch',
    'closing/btr/BufferTrendDispatch',
    'closing/btr/BufferTrendDates',
    'closing/consumer_context/CategoryColDescription',
)

GUIDED_IMAGES = (
    'closing/btr/BTRSnapshotForUI',
    'closing/btr/ChronicUnavalabilityData',
    'closing/btr/DBMNormSuggestionsData',
    'closing/consumer_context/NMSAllItems',
)

# These sources do not currently have a qualified producer in execute_day.
MISSING_PRODUCERS = {
    'shipment_ledger': 'InTransitData',
    'bor_black': ('ReqTopOfBlack', 'CumulativeTOBlack'),
    'boroa_opening': 'BORWithOrderAllocation',
}

REQUIRED_LAYERS = (
    'dbm_sources', 'bpr', 'btr', 'planning_sources', 'planning_grids',
    'planning_charts', 'planning_custom', 'planning_git',
    'planning_expedite_grids', 'planning_expedite_custom',
    'planning_expedite_transit', 'planning_expedite_charts', 'rrr', 'history',
    'research_availability', 'guided_history', 'guided_dbm', 'guided_chronic',
    'bor', 'boroa',
)

SYNTHETIC_ROSTER = 'core-without-bor-v1'
SYNTHETIC_REQUIRED_LAYERS = tuple(
    name for name in REQUIRED_LAYERS if name not in ('bor', 'boroa'))


def roster_identity():
    value = getattr(settings, 'VF_MTA_SYNTHETIC_ROSTER', '')
    if value not in ('', SYNTHETIC_ROSTER):
        raise PublicationUnavailable('unsupported_daily_synthetic_roster:' + str(value))
    return value


def required_layers():
    return (SYNTHETIC_REQUIRED_LAYERS if roster_identity() == SYNTHETIC_ROSTER
            else tuple(REQUIRED_LAYERS))


def require_report(report):
    roster = roster_identity()
    if roster == SYNTHETIC_ROSTER and report in ('bor', 'boroa'):
        raise PublicationUnavailable(
            'synthetic_roster_report_unavailable:' + report + ':' + roster)

DBM_IMAGES = tuple('closing/dbm/' + name for name in (
    'DBMMaster', 'Suggestions', 'NormAcceptanceTbl', 'SKUDescriptionTbl',
    'SiteDescriptionTbl', 'ReasonCodes', 'SkuAttributeData',
    'SkuLocAttributeData', 'LocationAttributeData', 'LastBatchRunTbl',
    'DailyConsumption', 'SuspendHistory', 'NormChangeLogTbl',
    'SuspendStockType', 'SuspendConsumptionType', 'SuggestionsLog',
))

COMMANDS = {
    'bpr': 'prepare_bpr_fixture',
    'planning_sources': 'prepare_planning_sources',
    'planning_grids': 'prepare_planning_grids',
    'planning_charts': 'prepare_planning_charts',
    'planning_custom': 'prepare_planning_custom',
    'planning_git': 'prepare_planning_git',
    'planning_expedite_grids': 'prepare_planning_expedite_grids',
    'planning_expedite_custom': 'prepare_planning_expedite_custom',
    'planning_expedite_transit': 'prepare_planning_expedite_transit',
    'planning_expedite_charts': 'prepare_planning_expedite_charts',
    'rrr': 'prepare_rrr',
    'history': 'prepare_history_reports',
    'research_availability': 'prepare_research_availability',
    'guided_history': 'prepare_guided_history_fixture',
    'guided_dbm': 'prepare_guided_dbm_fixture',
    'guided_chronic': 'prepare_guided_chronic_fixture',
    'bor': 'prepare_bor_membership',
    'boroa': 'prepare_boroa_membership',
}

ANCILLARY_IMAGES = {
    'BPRReport_RemarkDetails': 'sources/bpr/BPRReport_RemarkDetails',
    'InTransitData': 'sources/bpr/InTransitData',
}

BOR_IMAGES = {
    'SupplierDispatchReq': 'sources/bor/SupplierDispatchReq',
    'SOBData': 'sources/bor/SOBData',
    'MOQData': 'sources/bor/MOQData',
    'BORReport_RemarkDetails': 'sources/bor/BORReport_RemarkDetails',
}

BOROA_IMAGES = {
    'BORWithOrderAllocation': 'sources/boroa/BORWithOrderAllocation',
    'BOROARequirement': 'sources/boroa/BOROARequirement',
    'BORReport_OARemarkDetails': 'sources/boroa/BORReport_OARemarkDetails',
    'ColorSequence': 'metadata/bpr/ColorSequence',
}

def production_branch(run):
    """Allow daily readers only for enabled serving or an explicit offline build."""
    if getattr(run, 'kind', None) != 'DAILY_CHAIN':
        return False
    if getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False):
        return True
    if connection.vendor != 'postgresql' or not connection.in_atomic_block:
        return False
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.daily_publication_build',true)")
        owner = cursor.fetchone()[0]
    return owner == str(run.pk)


def source_digest(run):
    """Identity shared by production builders and their sealed receipts."""
    if (getattr(run, 'kind', None) != 'DAILY_CHAIN' or
            getattr(run, 'status', None) != 'SUCCEEDED' or
            not getattr(run, 'input_digest', None) or
            not getattr(run, 'output_digest', None) or
            not getattr(run, 'production_digest', None)):
        raise PublicationUnavailable('daily_preparation_source_run_not_accepted')
    return digest(dict(version=1, run=str(run.pk), date=str(run.business_date),
                       input=run.input_digest, output=run.output_digest,
                       production=run.production_digest))


def command_binding(run_id=None):
    """Resolve an explicit daily build or retain the command's fixture binding."""
    if run_id is None:
        from mta.presentation.fixture import binding
        return binding()
    from mta.runtime.models import CalculationRun
    run = CalculationRun.objects.get(pk=run_id)
    return run, source_digest(run)


def assert_unchanged(run, expected):
    if getattr(run, 'kind', None) == 'DAILY_CHAIN':
        if source_digest(run) != expected:
            raise PublicationUnavailable('daily_preparation_source_changed')
        return
    from mta.presentation.fixture import binding
    selected, source = binding()
    if selected.pk != run.pk or source != expected:
        raise PublicationUnavailable('fixture_preparation_source_changed')


def recipe_for(run, module):
    function = (getattr(module, 'production_recipe_digest', None)
                if getattr(run, 'kind', None) == 'DAILY_CHAIN' else None)
    return function() if function else module.recipe_digest()


def required_images(run, paths):
    """Bind a recipe to complete named images; the first absence fails closed."""
    source = source_digest(run)
    metadata = {path: image_metadata(run, path) for path in paths}
    return source, metadata


def ancillary_rows(run):
    """Read explicitly captured day facts; absence is different from an empty bag."""
    from mta.presentation.selective import image_rows
    source_digest(run)
    return {name: image_rows(run, path) for name, path in ANCILLARY_IMAGES.items()}


def ancillary_row(run, name):
    from mta.presentation.selective import image_rows
    source_digest(run)
    return image_rows(run, ANCILLARY_IMAGES[name])


def available_source_roster(run):
    """Return the finite already-produced source roster for readiness sealing."""
    paths = (*CORE_IMAGES, *BTR_HISTORY_IMAGES, *GUIDED_IMAGES)
    source, metadata = required_images(run, paths)
    return dict(source_digest=source, images=metadata,
                missing_producers=dict(MISSING_PRODUCERS))


def _command_result(run, name, *, verify_only):
    import io
    import json
    from django.core.management import call_command
    output = io.StringIO()
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.daily_publication_build',%s,true)", [str(run.pk)])
    call_command(COMMANDS[name], run_id=str(run.pk), verify_only=verify_only,
                 stdout=output, verbosity=0)
    lines = [line for line in output.getvalue().splitlines() if line.strip()]
    if not lines:
        raise PublicationUnavailable(name + '_preparation_returned_no_receipt')
    raw = json.loads(lines[-1])
    def values(node, suffixes):
        found = []
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, int) and key in ('rows','references') + suffixes:
                    found.append(value)
                elif isinstance(value, str) and key in suffixes:
                    found.append(value)
                else:
                    found.extend(values(value, suffixes))
        elif isinstance(node, list):
            for value in node: found.extend(values(value, suffixes))
        return found
    counts = values(raw, ('row_count','research_master_count','research_history_count',
                          'availability_count','graph_count','member_count','display_count',
                          'excess_count','fulfillment_count','base_count','match_count'))
    digests = values(raw, ('rows_digest','research_master_digest','research_history_digest',
                           'availability_digest','graph_digest','member_digest','display_digest',
                           'excess_digest','fulfillment_digest','base_digest','match_digest','digest'))
    return dict(source_digest=raw.get('source_digest', source_digest(run)),
                recipe_digest=raw.get('recipe_digest', raw.get('schema_digest',
                    digest(dict(version=1, command=COMMANDS[name])))),
                rows_digest=raw.get('rows_digest', digest(digests)),
                row_count=raw.get('row_count', sum(counts)), details=raw)


def _dbm_result(run):
    source, metadata = required_images(run, DBM_IMAGES)
    return dict(source_digest=source, recipe_digest=digest(DBM_IMAGES),
                rows_digest=digest(metadata),
                row_count=sum(item['count'] for item in metadata.values()))


def _btr_result(run, *, verify_only):
    from mta.presentation.btr_reporting import build_run, source_identity, verify_generation
    from mta.serialization import digest as value_digest
    if verify_only:
        from mta.runtime.models import BtrReportingGeneration
        identity = value_digest(source_identity(run))
        generation = BtrReportingGeneration.objects.get(
            run=run, version=1, source_digest=identity, status='READY')
        verify_generation(generation)
    else:
        generation = build_run(run)
    return dict(source_digest=generation.source_digest,
                recipe_digest=value_digest(dict(version=generation.version)),
                rows_digest=generation.rows_digest, row_count=generation.row_count,
                generation=str(generation.pk))


def _require_ancillary(run, layer):
    if layer == 'bpr':
        ancillary_rows(run)
    elif layer == 'planning_git':
        ancillary_row(run, 'InTransitData')
        from mta.presentation.daily_git_preparation import validate_ready
        validate_ready(run)
    elif layer == 'planning_expedite_transit':
        ancillary_row(run, 'BPRReport_RemarkDetails')
    elif layer == 'planning_expedite_grids':
        from mta.presentation.selective import image_rows
        requests = image_rows(run, 'sources/planning/OpenExpediteRequests')
        transit = ancillary_row(run, 'InTransitData')
        from mta.presentation.expedite_child_sources import projections
        # Both sources are independently owned and typed. Reject native TOP(1)
        # ambiguity before sealing, rather than inventing a request winner.
        projections(requests, transit)


def prepare_layer(run, name):
    """Build one explicit finite layer; callers own retry/readiness state."""
    if name not in REQUIRED_LAYERS:
        raise ValueError('Unknown daily preparation layer: ' + str(name))
    if name not in required_layers():
        raise PublicationUnavailable('daily_layer_excluded_by_synthetic_roster:' + name)
    source_digest(run)
    if name == 'dbm_sources':
        return _dbm_result(run)
    if name == 'btr':
        return _btr_result(run, verify_only=False)
    _require_ancillary(run, name)
    if name == 'bor':
        raise PublicationUnavailable('bor_daily_black_fields_missing:ReqTopOfBlack,CumulativeTOBlack')
    if name == 'boroa':
        raise PublicationUnavailable('boroa_daily_opening_source_missing:BORWithOrderAllocation')
    return _command_result(run, name, verify_only=False)


def verify_layer(run, name, receipt):
    """Verify an unchanged successful layer without rebuilding it."""
    if name not in REQUIRED_LAYERS:
        raise ValueError('Unknown daily preparation layer: ' + str(name))
    if name not in required_layers():
        raise PublicationUnavailable('daily_layer_excluded_by_synthetic_roster:' + name)
    if not isinstance(receipt, dict):
        raise PublicationUnavailable(name + '_daily_receipt_source_changed')
    source = source_digest(run)
    if name in ('bor','boroa'):
        # These cannot have a valid daily receipt until their named producers
        # replace the explicit preparation blockers above.
        return prepare_layer(run, name)
    if name != 'btr' and receipt.get('source_digest') != source:
        raise PublicationUnavailable(name + '_daily_receipt_source_changed')
    if name == 'dbm_sources':
        current = _dbm_result(run)
    elif name == 'btr':
        current = _btr_result(run, verify_only=True)
    else:
        _require_ancillary(run, name)
        current = _command_result(run, name, verify_only=True)
    for field in ('source_digest', 'recipe_digest', 'rows_digest', 'row_count'):
        if field in receipt and current.get(field) != receipt[field]:
            raise PublicationUnavailable(name + '_daily_receipt_changed:' + field)
    return current
