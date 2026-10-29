"""Generic final writers at their canonical daily positions.

The caller owns sequencing and durable publication. These adapters reuse the
qualified producers; they neither certify omitted operations nor admit a run.
"""
from copy import deepcopy
from datetime import datetime
from collections import Counter
import json
import hashlib
from pathlib import Path

from mta.application.complete_daily_inputs import supplier_dispatch
from mta.application.daily_nms_snapshot import create_snapshot
from mta.domain.complete_daily_bpr import production_order_suggestions
from mta.domain.complete_daily_completion import (
    reset_batch_flags, prune_bpr_history, mark_script_executed, validate_batch_flags,
)
from mta.domain.complete_daily_scalars import (
    ascii_equal, identifier_sort_key, datetime_to_nvarchar, parse_datetime,
)

POLICY = 'generic-finalization-v1'
ACTIVE_POLICY = 'generic-finalization-active-nms-v1'
ACTIVE_QUALIFICATION = 'active-nms-enabled-writers-complete'
FLAG_SEED_SHA256 = '1fa8858c03a4d37646b1c0e6f33b0321c5a6edaab93c5c0c168f1a5991f9931f'
_seed_bytes = (Path(__file__).resolve().parents[1] / 'config/daily_finalization_flags.json').read_bytes()
if hashlib.sha256(_seed_bytes).hexdigest() != FLAG_SEED_SHA256:
    raise ValueError('Pinned generic finalization flag seed differs')
FLAG_SEED = json.loads(_seed_bytes)['flags']
REMARK_TABLES = ('BPRReport_RemarkDetails', 'OpenExpeditRequestRemarksHistory',
                 'InTransitWhereAboutsRemarks')
EMPTY_APPROVAL_QUEUES = ('NMSSOB', 'NMSMOQWithDestination', 'NMSMOQWithoutDestination')
SUPPLIER_RAW = ('SOBDataRaw', 'MOQDataRaw1', 'MOQDataRaw2')
REQUIRED = ('ScriptExecutedFlag', 'ProdOrderSuggestions', 'SupplierDispatchReq',
            *REMARK_TABLES, *EMPTY_APPROVAL_QUEUES, *SUPPLIER_RAW)

# Each bundle is emitted only after its existing compound producer succeeds.
CALCULATION_SCRIPTS = (
    'StockCalculation.sql', 'GenerateAddionalMasterData.sql', 'CalculateRoute.sql',
    'CalculateReq.sql', 'ConsolidateReq.sql', 'CollectDataForDispatchPriority.sql',
    'UpdateDispatchPriority.sql', 'CollectDataForNormRationing.sql',
    'ExcludeReplenishment.sql', 'FillRationSteps.sql', 'GetReqData.sql',
    'GetReqDataForParent.sql', 'GetStepwiseChildReq.sql', 'RationPacksize.sql',
    'CollectDataForPSORationing.sql', 'PSORationing.sql',
    'GenerateBifurcationOfRationedReq.sql',
)


def mark(complete, *scripts):
    # One independent flag image for the compound producer, in the same script
    # order. Preserve the pure domain update's SQL NULL/collation predicate.
    from mta.domain.complete_daily_completion import _mark
    flags = deepcopy(complete['ScriptExecutedFlag'])
    for name in scripts:
        _mark(flags, name, ascii_equal)
    if scripts:
        complete['ScriptExecutedFlag'] = flags


def validate_flag_roster(flags):
    from mta.application.accepted_inputs import accepted
    if accepted():
        return
    fields = {'ScriptName', 'IsScriptExecuted', 'IsScriptCritical', 'ModuleName'}
    shape = lambda rows: Counter((r['ScriptName'], r['IsScriptCritical'], r['ModuleName'])
                                  for r in rows)
    if (any(set(row) != fields or type(row['IsScriptExecuted']) not in (bool, int)
            or row['IsScriptExecuted'] not in (False, True) for row in flags)
            or shape(flags) != shape(FLAG_SEED)):
        raise ValueError('Generic finalization flag roster differs from pinned seed')


def validate_completion(complete, settings, today, *, kind):
    result = validate_batch_flags(complete['ScriptExecutedFlag'], settings,
        datetime.fromisoformat(today), kind=kind, equal=ascii_equal,
        parse_datetime=parse_datetime)
    parameter = 'IsBPRBatchFileExecuted' if kind == 'BPR' else 'IsBatchFileExecuted'
    values = [row['Value'] for row in result['ImporterSettingsTbl']
              if ascii_equal(row['Parameter'], parameter)]
    if not values or any(value != '1' for value in values):
        missing = [row['ScriptName'] for row in result['ScriptExecutedFlag']
                   if row['IsScriptCritical'] == 1 and row['IsScriptExecuted'] == 0
                   and (kind == 'ALL' or ascii_equal(row['ModuleName'], 'BPR'))]
        raise ValueError('Generic completion failed: ' + kind + ': ' + repr(missing))
    complete['ScriptExecutedFlag'] = result['ScriptExecutedFlag']
    return result['ImporterSettingsTbl']


def nms_active(settings):
    return any(ascii_equal(row['Parameter'], 'NMSActive') and row['Value'] is not None
               and ascii_equal(str(row['Value']), '1') for row in settings)


def require_inactive_qualification(settings):
    from mta.application.accepted_inputs import accepted
    if accepted():
        return
    values = [row['Value'] for row in settings if ascii_equal(row['Parameter'], 'NMSActive')]
    if not values or any(type(value) is not str or value != '0' for value in values):
        raise ValueError('Cohort1 qualification requires explicit NMSActive=0')
    for parameter in ('IsBatchFileExecuted', 'IsBPRBatchFileExecuted', 'BatchFileExecutionDate'):
        values = [row['Value'] for row in settings if ascii_equal(row['Parameter'], parameter)]
        if not values or any(type(value) is not str for value in values):
            raise ValueError('Explicit completion setting required: ' + parameter)


def finish(complete, settings, today, *, policy=POLICY):
    """Qualified Cohort1 gate; canonical ALL remains unchanged and distinct.

    Only the two source-skipped inactive-NMS critical rows may remain false.
    This is not a publication receipt or a whole-batch success override.
    """
    if policy == ACTIVE_POLICY:
        require_active_settings(settings)
        validate_flag_roster(complete['ScriptExecutedFlag'])
        result = validate_completion(complete, settings, today, kind='ALL')
        for parameter in ('IsBPRBatchFileExecuted', 'IsBatchFileExecuted'):
            values = [r['Value'] for r in result if ascii_equal(r['Parameter'], parameter)]
            if len(values) != 1 or values != ['1']:
                raise ValueError('Active NMS requires canonical completion: ' + parameter)
        stamps = [r['Value'] for r in result if ascii_equal(r['Parameter'], 'BatchFileExecutionDate')]
        if len(stamps) != 1 or parse_datetime(stamps[0]) != datetime.fromisoformat(today):
            raise ValueError('Active NMS completion date differs')
        return result
    if policy != POLICY:
        raise ValueError('Unknown generic finalization policy')
    require_inactive_qualification(settings)
    if any(row['Value'] != '1' for row in settings
           if ascii_equal(row['Parameter'], 'IsBPRBatchFileExecuted')):
        raise ValueError('Cohort1 requires completed BPR validation')
    validate_flag_roster(complete['ScriptExecutedFlag'])
    result = validate_batch_flags(complete['ScriptExecutedFlag'], settings,
        datetime.fromisoformat(today), kind='ALL', equal=ascii_equal,
        parse_datetime=parse_datetime)
    allowed = set() if nms_active(settings) else {'NMSImportData.sql', 'NMSClearInputTables.sql'}
    if any(row['IsScriptExecuted'] != 0 for row in result['ScriptExecutedFlag']
           if row['ScriptName'] in allowed):
        raise ValueError('Inactive NMS skipped flags must remain false')
    absent = [row['ScriptName'] for row in result['ScriptExecutedFlag']
              if row['IsScriptCritical'] == 1 and row['IsScriptExecuted'] == 0
              and row['ScriptName'] not in allowed]
    stamps = [row['Value'] for row in settings
              if ascii_equal(row['Parameter'], 'BatchFileExecutionDate')]
    if absent or not stamps or any(parse_datetime(value) != datetime.fromisoformat(today)
                                  for value in stamps):
        raise ValueError('Cohort1 enabled-writer completion failed: ' + repr(absent))
    values = [row['Value'] for row in result['ImporterSettingsTbl']
              if ascii_equal(row['Parameter'], 'IsBatchFileExecuted')]
    if not values or any(value != '0' for value in values):
        raise ValueError('Cohort1 qualification must preserve native whole-batch flag zero')
    complete['ScriptExecutedFlag'] = result['ScriptExecutedFlag']
    return result['ImporterSettingsTbl']


def verify_finalization_identity(output, profile, today):
    """Bind uncommitted completion metadata to its actual captured profile."""
    from mta.serialization import digest
    state = output['ClosingState'][0]
    policy = configuration(profile)['policy']
    expected = dict(policy=policy, business_date=today,
        configuration_digest=digest(profile),
        qualification=qualification(policy),
        flag_digest=digest(state['complete']['ScriptExecutedFlag']))
    if (output.get('Lineage') or [{}])[0].get('cohort1') != expected:
        raise ValueError('Cohort1 predecessor gate identity differs')


def verify_successor(output, profile, today):
    """Require the committed Cohort1 gate as well as typed output integrity."""
    verify_finalization_identity(output,profile,today)
    state=output['ClosingState'][0]
    policy=configuration(profile)['policy']
    if finish(deepcopy(state['complete']), state['importer_settings'], today, policy=policy) != state['importer_settings']:
        raise ValueError('Cohort1 predecessor completion state differs')


def configuration(profile):
    value = profile.get('complete_daily')
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != {
            'policy', 'consumption_days', 'remark_days'} or value['policy'] not in (POLICY, ACTIVE_POLICY)):
        raise ValueError('Explicit supported generic finalization configuration required')
    for name in ('consumption_days', 'remark_days'):
        if type(value[name]) is not int or not -2147483648 <= value[name] <= 2147483647:
            raise ValueError('Typed SQL int finalization horizon required')
    return value


def validate_supplement(content, profile, opening=None):
    """Pin the supplement at execute_day, including direct service callers."""
    from mta.serialization import digest
    if (not isinstance(content, bytes) or hashlib.sha256(content).hexdigest() !=
            profile.get('complete_daily_config_sha256')):
        raise ValueError('Pinned finalization supplement bytes required')
    value = json.loads(content)
    if (set(value) != {'schema', 'artifact_sha256', 'configuration', 'opening_complete'}
            or value['schema'] != 'generic-finalization-input-v1'
            or value['configuration'] != configuration(profile)
            or value['artifact_sha256'] != profile.get('complete_daily_artifact_sha256')
            or not isinstance(value['artifact_sha256'], str)
            or len(value['artifact_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in value['artifact_sha256'])):
        raise ValueError('Finalization supplement identity differs')
    if opening is not None and opening['state'].get('complete') != value['opening_complete']:
        raise ValueError('Finalization opening differs from pinned supplement')
    return dict(sha256=hashlib.sha256(content).hexdigest(),
                artifact_sha256=value['artifact_sha256'],
                opening_digest=digest(value['opening_complete']))


def preserve_settings(original, produced):
    """Apply the existing narrow settings writer without dropping other rows."""
    result = deepcopy(original)
    for row in result:
        values = [other['Value'] for other in produced
                  if ascii_equal(other['Parameter'], row['Parameter'])]
        if values:
            if any(value != values[0] for value in values):
                raise ValueError('Ambiguous produced importer setting')
            row['Value'] = values[0]
    return result


def qualification(policy):
    if policy not in (POLICY, ACTIVE_POLICY):
        raise ValueError('Unknown generic finalization policy')
    return ACTIVE_QUALIFICATION if policy == ACTIVE_POLICY else 'inactive-nms-critical-flags-remain-false'


def require_active_settings(settings):
    from mta.application.accepted_inputs import accepted
    if accepted():
        return
    values = [row['Value'] for row in settings if ascii_equal(row['Parameter'], 'NMSActive')]
    if values != ['1']:
        raise ValueError('Active finalization requires one explicit NMSActive=1')
    for parameter in ('IsBatchFileExecuted', 'IsBPRBatchFileExecuted', 'BatchFileExecutionDate'):
        values = [row['Value'] for row in settings if ascii_equal(row['Parameter'], parameter)]
        if len(values) != 1 or type(values[0]) is not str:
            raise ValueError('Explicit completion setting required: ' + parameter)


def begin(prior, today, *, policy=POLICY):
    """Reset owned flag/settings rows; missing populations are never made empty."""
    if 'complete' not in prior or any(name not in prior['complete'] for name in REQUIRED):
        raise ValueError('Explicit generic finalization opening populations required')
    if policy == ACTIVE_POLICY:
        require_active_settings(prior['importer_settings'])
    elif policy == POLICY:
        require_inactive_qualification(prior['importer_settings'])
    else:
        raise ValueError('Unknown generic finalization policy')
    if any(prior['complete'][name] != [] for name in EMPTY_APPROVAL_QUEUES):
        raise ValueError('Populated SOB/MOQ approval workflows are outside the qualified domain')
    validate_flag_roster(prior['complete']['ScriptExecutedFlag'])
    result = deepcopy(prior)
    reset = reset_batch_flags(result['complete']['ScriptExecutedFlag'],
        result['importer_settings'], datetime.fromisoformat(today),
        equal=ascii_equal, format_datetime=datetime_to_nvarchar)
    result['complete']['ScriptExecutedFlag'] = reset['ScriptExecutedFlag']
    result['importer_settings'] = reset['ImporterSettingsTbl']
    return result


def fresh_feeds(prior, day, *, policy=POLICY):
    """Clear working raw populations and load explicit non-NMS facts.

    Immutable inputs and predecessor rows are never the working tables. Active
    NMS needs its different persisted-input/queue path, not this raw-feed route.
    """
    if nms_active(prior['importer_settings']) and policy != ACTIVE_POLICY:
        raise ValueError('Active NMS complete finalization intake is not yet qualified')
    feeds = ('raw_master', 'raw_non_nms', 'raw_no_norm', 'raw_daily',
             'accepted_feed', 'order_feed', 'supplier_feeds')
    working = deepcopy({name: value for name, value in day.items() if name not in feeds})
    for name in ('raw_master', 'raw_non_nms', 'raw_no_norm', 'raw_daily',
                 'accepted_feed', 'order_feed'):
        from mta.application.persistent_master import NmsMasterRows
        if name == 'raw_master' and isinstance(day[name],NmsMasterRows):
            working[name]=day[name]
            continue
        working[name] = deepcopy(day[name])
    working['supplier_feeds'] = {}
    for name in SUPPLIER_RAW:
        working['supplier_feeds'][name] = deepcopy(day['supplier_feeds'][name])
    mark(prior['complete'], 'ClearMasterInputTables.sql', 'ClearNonMasterInputTables.sql')
    return working


def nms_snapshot(importer, controls, prior, exclusions):
    """NormChangesRun: after ClearPhaseInPhaseOutData, before BPR/DBM."""
    return create_snapshot(nms_active=nms_active(controls['importer_settings']),
        master_data=importer['MasterData'], dbm_master=controls['dbm_master'],
        skuloc_attributes=importer['SkuLocAttributeData'],
        sku_descriptions=importer['SKUDescriptionTbl'],
        site_descriptions=importer['SiteDescriptionTbl'], exclusions=exclusions,
        sku_attributes=importer['SkuAttributeData'],
        location_attributes=importer['LocationAttributeData'],
        nms_all_items=prior['consumer_context']['NMSAllItems'])


def production_and_retention(*, complete, source, calculated, bpr_master,
                             importer, plants, report, late, today, config, _owned=False):
    """RunCoreBPR: production suggestions, then ClearHistoryData_BPR."""
    complete = dict(complete) if _owned else deepcopy(complete)
    supplier, _ = supplier_dispatch(sourcing=source['sourcing'],
        bor=calculated['r1_bor'], bpr_master=bpr_master,
        sku_loc_attributes=importer['SkuLocAttributeData'], equal=ascii_equal)
    suggestions = production_order_suggestions(supplier_dispatch_req=supplier,
        plants=plants, rationed_req_report=report,
        daily_consumption=late['BPRDailyConsumption'],
        last_batch_run=[{'LastRunDate': today}],
        prod_order_suggestions=complete['ProdOrderSuggestions'],
        intermediate_tables={name: [] for name in (
            'TempProductionOrderReq', 'TempConsolidatedProdOrderReq', 'PlantStock')},
        equal=ascii_equal, sort_key=identifier_sort_key)
    retained = prune_bpr_history({
        'DailyConsumption': late['BPRDailyConsumption'],
        **{name: complete[name] for name in REMARK_TABLES}},
        [{'LastRunDate': today}], consumption_days=config['consumption_days'],
        remark_days=config['remark_days'])
    complete.update(SupplierDispatchReq=supplier,
                    ProdOrderSuggestions=suggestions['ProdOrderSuggestions'])
    complete.update({name: retained[name] for name in REMARK_TABLES})
    return complete, retained['DailyConsumption']
