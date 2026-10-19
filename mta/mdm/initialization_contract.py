"""Operator-owned master/opening input; no fixture or calculation authority."""
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
import math
import re
from pathlib import Path

from mta.serialization import digest, storage
from mta.row_sequences import is_record_rows
from mta.application.streamed_input import StreamedInput
from mta.mdm.master_owners import owner_batches
from mta.application.r1_importer_master import PRIOR_TABLES
from mta.application.daily_finalization import configuration, validate_flag_roster, REQUIRED
from mta.application.r1_daily_input import PRIOR_TABLES as BPR_TABLES, _typed_rows as daily_rows, FLAGS
from mta.domain.control_carry import TABLES as CONTROL_TABLES

CONTRACT = json.loads((Path(__file__).resolve().parents[1]/'config/initialization_storage_v1.json').read_text())

SCHEMA = 'fresh-production-initialization-input-v1'
SOURCE_SCHEMA = 'fresh-production-mdm-source-v1'
RECIPE = 'native-base-owner-projection-v1'
MASTER_TABLES = {
    'importer': ('SkuAttributeData', 'SKUDescriptionTbl', 'LocationAttributeData',
                 'SiteDescriptionTbl', 'SkuLocAttributeData', 'MasterData'),
    'btr': ('SkuAttributeData', 'SKUDescriptionTbl'),
    'dbm': ('SkuAttributeData', 'SKUDescriptionTbl'),
}
STATE_SECTIONS = frozenset(('importer', 'importer_settings', 'bpr', 'supplier',
    'orders', 'controls', 'dbm', 'btr', 'control_aux', 'consumer_context',
    'publication_context', 'complete'))

# Supplied initial carry/history is distinct from fresh recommendations, rule
# scratch tables and consumer reports. Every other DBM/BTR population is empty.
DBM_CARRY = frozenset(('DBMMaster', 'DBMSettingsTbl', 'DailyConsumption',
    'FirstReplenishmentPercentageTbl', 'LastBatchRunTbl', 'LocationAttributeData',
    'NormAcceptanceTbl', 'NormChangeLogTbl', 'NormsInSleepModeTbl', 'OrderData',
    'OrderDataSummary', 'PhaseInTbl', 'PhaseOutTbl', 'ReasonCodes', 'SKUDescriptionTbl',
    'SKULocStandardAttributes', 'Seasonality', 'SiteDescriptionTbl', 'SkuAttributeData',
    'SkuLocAttributeData', 'SuggestionsLog', 'SuspendHistory', 'SuspendConsumptionType',
    'SuspendStockType', 'SuspendOrderType', 'SuspendSpikeTbl', 'SuspendSupplyIssueTbl',
    'VFSettings', 'ui_ReportConfigurations'))
BTR_BASE = frozenset(('LastBatchRunTbl', 'LocationAttributeData', 'SKUDescriptionTbl',
    'SKULocStandardAttributes', 'SiteDescriptionTbl', 'SkuAttributeData', 'SkuLocAttributeData'))
BTR_CARRY = BTR_BASE | {'BPR', 'RationingHistory'}
COMPLETE_OUTPUTS = frozenset(('FGTrendData', 'DataSanitizationResult', 'ProdOrderSuggestions',
    'RuntimeReports', 'SupplierDispatchReq', 'LogisticPickList', 'PickListDataForTruckFormation'))
HISTORY_DATES = frozenset(('ReportDate', 'AcceptanceDate', 'NormChangeDate',
    'SuggestionDate', 'ImportDate', 'Event_Date', 'RejectionDate', 'ActionTimeStamp',
    'Log_Date', 'LastProcessedDate', 'LastProcessedOn', 'CreationDate', 'LastRunDate'))


def scalar_configuration(profile):
    """Deny undeclared configuration objects before typed storage selection."""
    from mta.mdm.initialization_rows import scalar
    from mta.mdm.native_audit_policy import validate_policy
    def fields(value, kinds, label, *, required=False):
        if not isinstance(value, dict) or set(value) - set(kinds) or required and set(value) != set(kinds):
            raise ValueError('Initialization configuration fields differ: '+label)
        for name, kind in kinds.items():
            if name in value:
                if value[name] is None:
                    raise ValueError('NULL configuration: '+label+'/'+name)
                scalar(value[name], kind, label+'/'+name)
    calc = profile['calculation']
    if set(calc) != {'skus', 'locations', 'stock_openings', 'policies', 'logistics',
                    'stock_configuration', 'allocation', 'replenishment_exclusions'}:
        raise ValueError('Undeclared calculation configuration')
    fields(calc['stock_configuration'], {'reservation_type': 'int',
        'reservation_for_rationing_only': 'bit'}, 'stock_configuration', required=True)
    if calc['stock_configuration']['reservation_type'] not in (0, 1, 2) or type(calc['stock_configuration']['reservation_for_rationing_only']) is not bool:
        raise ValueError('Stock configuration option/type differs')
    fields(calc['allocation'], {'advance_stock_threshold_percent': 'numeric'}, 'allocation', required=True)
    if not 0 <= float(calc['allocation']['advance_stock_threshold_percent']) <= 100:
        raise ValueError('Allocation threshold outside supported range')
    logistics = calc['logistics']
    if set(logistics) - {'items', 'vehicles', 'location_vehicles'}:
        raise ValueError('Undeclared logistics configuration')
    if not {'items', 'vehicles', 'location_vehicles'} <= set(logistics):
        raise ValueError('Explicit logistics populations required')
    fields(profile['force_flags'], {'from_ui': 'bit', 'ignore_master_norm': 'bit',
        'nms_active': 'bit'}, 'force_flags', required=True)
    if any(type(value) is not bool for value in profile['force_flags'].values()):
        raise ValueError('Force flags must be explicit booleans')
    delivery = profile['delivery']
    if set(delivery) - {'site_code', 'batch', 'controls', 'btr_settings', 'conditional_dbm', 'btr_history'} or not {'site_code', 'batch', 'controls', 'btr_settings'} <= set(delivery):
        raise ValueError('Delivery configuration fields differ')
    batch = {name: 'int' for name in ('AutoDBMActive', 'DBMNormChangeReportHorizon',
        'NormChangeLogHorizon', 'GatherSuspensionHistory', 'ActivateNormChangeLogReport',
        'DailyConsumptionHorizonDBM', 'PhaseOutRecommendation30Days',
        'PhaseOutRecommendation60Days', 'PhaseOutRecommendation90Days',
        'ActivateNorm0Report30Days', 'ActivateNorm0Report60Days', 'ActivateNorm0Report90Days',
        'ActivateNorm1Report30Days', 'ActivateNorm2Report30Days')}
    from mta.domain.dbm_conditional import MULTIPLIERS
    from mta.domain.dbm_phase_recommendation import TOLERANCES, configuration as phase_configuration
    if not set(batch) <= set(delivery['batch']):
        raise ValueError('Required delivery batch fields differ')
    fields(delivery['batch'], {**batch, **dict.fromkeys((*MULTIPLIERS, *TOLERANCES), 'int')}, 'delivery/batch')
    if 'conditional_dbm' in delivery and (not isinstance(delivery['conditional_dbm'], dict)
            or set(delivery['conditional_dbm']) != {'importer_vf_settings'}
            or not isinstance(delivery['conditional_dbm']['importer_vf_settings'], list)):
        raise ValueError('Explicit conditional Importer settings object required')
    if delivery['batch']['AutoDBMActive'] not in (0, 1):
        raise ValueError('Explicit automatic acceptance flag 0/1 required')
    phase_configuration(delivery['batch'])
    fields(delivery['controls'], {'from_ui': 'bit', 'start_percent': 'numeric',
        'history_horizon': 'int'}, 'delivery/controls', required=True)
    btr_kinds={'CaptureDispatchExecutionEfficiency': 'int',
        'GenerateColorAgeingReport': 'int', 'BRAgeColorTolerance': 'int',
        'CARNoColorToleranceDuration': 'int', 'NormSuggestion_Upward': 'nvarchar',
        'NormSuggestion_Downward': 'nvarchar'}
    if not set(btr_kinds)<=set(delivery['btr_settings']):
        raise ValueError('Required BTR settings differ')
    fields(delivery['btr_settings'],{**btr_kinds,'RationingHistoryHorizonBTR':'int'},'delivery/btr_settings')
    owner=delivery.get('btr_history')
    if owner is not None and (not isinstance(owner,dict) or set(owner)!={'importer_vf_settings'}):
        raise ValueError('Explicit BTR Importer settings owner required')
    from mta.domain.btr_finalization import _selected_settings
    _selected_settings(delivery['btr_settings'],None if owner is None else owner['importer_vf_settings'])
    fields(profile['daily_publication_config'], {'bpr_remark_horizon': 'int'},
        'daily_publication_config', required=True)
    if profile['daily_publication_config']['bpr_remark_horizon'] < 0:
        raise ValueError('Negative remark horizon')
    validate_policy(profile)
    policies = {'operational_sources': 'cohort2-operational-sources-v1',
        'operational_force_sources': 'cohort2-pre-clear-force-v1',
        'operational_input_sources': 'cohort2-input-tables-v1'}
    for name, policy in policies.items():
        if name in profile and profile[name] != policy:
            raise ValueError('Unsupported initialization policy: '+name)
    if 'synthetic_action_policy' in profile:
        from mta.temporal.action_policy import POLICIES
        if profile['synthetic_action_policy'] not in POLICIES:
            raise ValueError('Unsupported explicit action policy')
    for name in ('settings', 'vf_settings'):
        allowed = {'MissingDailyDataHandling', 'DBM_MissingDailyDataHandling'} if name == 'settings' else {'GenerateBPRForMissingInventoryLoc'}
        for row in profile['daily'][name]:
            if not isinstance(row, dict) or set(row) != {'Parameter', 'Value'} or row['Parameter'] not in allowed or type(row['Value']) is not str:
                raise ValueError('Daily configuration settings differ')
    modes = [row['Value'] for row in profile['daily']['settings']
             if row['Parameter'] == 'MissingDailyDataHandling']
    if len(modes) != 1 or modes[0] not in ('1', '2', '3'):
        raise ValueError('One supported MissingDailyDataHandling mode (1, 2 or 3) required')


def initial_state(state, opening_date):
    percentages = state['dbm']['FirstReplenishmentPercentageTbl']
    if len(percentages) != 1 or type(percentages[0]['ReplenishmentPercentage']) is not int:
        raise ValueError('One explicit typed first replenishment percentage required')
    for name in ('SpikeRuleHorizon', 'SpikeRuleParCount'):
        values = [row['Value'] for row in state['dbm']['DBMSettingsTbl']
                  if row['Parameter'] == name]
        if len(values) != 1:
            raise ValueError('One explicit selected DBM setting required: '+name)
        try:
            int(values[0])  # Existing selected producer parser; no new ranges.
        except (ValueError, TypeError) as error:
            raise ValueError('Selected DBM setting integer differs: '+name) from error
    for table in ('BPR', 'RationingHistory'):
        for row in state['btr'].get(table, []):
            value = row.get('ReportDate')
            if not isinstance(value, str) or date.fromisoformat(value[:10]) > opening_date:
                raise ValueError('BTR carry requires a dated historical row: '+table)
    for section, allowed in (('dbm', DBM_CARRY), ('btr', BTR_CARRY)):
        for name, rows in state[section].items():
            if rows and name not in allowed:
                raise ValueError('Initial opening cannot seed calculated output: '+section+'/'+name)
    for section, names in (('complete', COMPLETE_OUTPUTS),
            ('controls', ('suggestions', 'forced', 'triggers', 'accepted', 'raw_master')),
            ('orders', ('ElephantOrders', 'NewSpikeOrders')),
            ('consumer_context', ('GoodsInTransitTransporterMaster',))):
        if any(state[section].get(name) for name in names):
            raise ValueError('Initial opening cannot seed calculated output: '+section)
    if state['controls']['IntermediateTables'] not in ({}, []):
        raise ValueError('Initial opening cannot seed calculation scratch state')
    for section, populations in state.items():
        bags = populations.values() if isinstance(populations, dict) else (populations,)
        for rows in bags:
            if not is_record_rows(rows):
                continue
            for row in rows:
                for field in HISTORY_DATES & set(row):
                    if row[field] is not None and date.fromisoformat(row[field][:10]) > opening_date:
                        raise ValueError('Opening history/date exceeds opening: '+section+'/'+field)
    flags = state['complete']['ScriptExecutedFlag']
    if any(row['IsScriptExecuted'] not in (0, False) for row in flags):
        raise ValueError('Initial completion flags must be inactive')
    for settings in (state['importer_settings'], state['controls']['importer_settings']):
        for name in ('IsBatchFileExecuted', 'IsBPRBatchFileExecuted'):
            if [row['Value'] for row in settings if row['Parameter'] == name] != ['0']:
                raise ValueError('Initial completion setting must be explicitly inactive: '+name)
        if [row['Value'] for row in settings if row['Parameter'] == 'BatchFileExecutionDate'] != [opening_date.isoformat()+'T00:00:00']:
            raise ValueError('Initial completion date differs')


def sha(value, label):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Explicit SHA256 required: '+label)
    return value


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate input object key: '+key)
        result[key] = value
    return result


def decode(raw, expected_sha256, *, expected_configuration, expected_recipe):
    sha(expected_sha256, 'input'); sha(expected_configuration, 'configuration'); sha(expected_recipe, 'recipe')
    if type(raw) is StreamedInput:
        value = raw.snapshot(expected_sha256)
    elif isinstance(raw, bytes) and hashlib.sha256(raw).hexdigest() == expected_sha256:
        def nonfinite(value):
            raise ValueError('Nonfinite input number: '+value)
        value = json.loads(raw, object_pairs_hook=object_pairs, parse_constant=nonfinite)
    else:
        raise ValueError('Operator input bytes differ')
    if not isinstance(value, dict) or set(value) != {'schema', 'recipe', 'configuration', 'masters', 'opening', 'pair_exclusions'}:
        raise ValueError('Complete versioned initialization envelope required')
    if value['schema'] != SCHEMA:
        raise ValueError('Unknown production initialization schema')
    recipe = value['recipe']
    if (not isinstance(recipe, dict) or set(recipe) != {'projection', 'extractor', 'version', 'source_identity'}
            or recipe['projection'] != RECIPE or digest(recipe) != expected_recipe
            or any(not isinstance(recipe[k], str) or not 1 <= len(recipe[k]) <= 256
                   for k in ('extractor', 'version', 'source_identity'))):
        raise ValueError('Explicit extraction/initialization recipe identity differs')
    profile = value['configuration']
    if not isinstance(profile, dict) or digest(profile) != expected_configuration:
        raise ValueError('Initialization configuration identity differs')
    if set(profile) - set(CONTRACT['allowed_profile_keys']):
        raise ValueError('Unknown initialization configuration fields')
    for key in ('daily', 'calculation', 'force_flags', 'delivery', 'complete_pick', 'complete_daily', 'daily_publication_config'):
        if not isinstance(profile.get(key), dict):
            raise ValueError('Explicit engine configuration population required: '+key)
    if (type(profile.get('import_non_nms')) is not bool or profile.get('daily_publication') is not True
            or profile['complete_pick'] != {'policy': 'canonical-tied-order-v1'}
            or not isinstance(profile['delivery'].get('site_code'), str)
            or not 1 <= len(profile['delivery']['site_code']) <= 128):
        raise ValueError('Explicit site and production configuration required')
    configuration(profile)  # Validates the versioned finalization policy and typed horizons; no producer executes.
    daily_required={'settings','vf_settings','shell_flags','distributor_codes','vendor_codes','vector_dms_codes'}
    if not daily_required<=set(profile['daily']) or set(profile['daily'])-daily_required-{'module_sources'}:
        raise ValueError('Daily configuration population roster differs')
    from mta.application.r1_daily_input import validate_module_configuration
    validate_module_configuration(profile['daily']['shell_flags'],profile['daily'].get('module_sources'))
    for name in ('settings', 'vf_settings', 'distributor_codes', 'vendor_codes', 'vector_dms_codes'):
        if not isinstance(profile['daily'][name], list):
            raise ValueError('Daily configuration requires an explicit population: '+name)
    calc = profile['calculation']
    for name in ('skus', 'locations', 'stock_openings', 'policies'):
        if not isinstance(calc.get(name), list):
            raise ValueError('Calculation configuration requires an explicit population: '+name)
    if not isinstance(calc.get('logistics'), dict) or not isinstance(calc.get('stock_configuration'), dict):
        raise ValueError('Calculation logistics/stock configuration required')
    if (not isinstance(profile['delivery'].get('batch'), dict)
            or not isinstance(profile['delivery'].get('controls'), dict)
            or not isinstance(profile['delivery'].get('btr_settings'), dict)):
        raise ValueError('Delivery configuration populations required')
    scalar_configuration(profile)
    masters = value['masters']
    if not isinstance(masters, dict) or set(masters) != set(MASTER_TABLES):
        raise ValueError('Complete explicit master owner groups required')
    for owner, tables in MASTER_TABLES.items():
        if not isinstance(masters[owner], dict) or set(masters[owner]) != set(tables):
            raise ValueError('Master population roster differs: '+owner)
        if any(not isinstance(masters[owner][table], list) for table in tables):
            raise ValueError('Master bags must be explicit lists: '+owner)
    opening = value['opening']
    if (not isinstance(opening, dict) or set(opening) != {'identity', 'date', 'semantics', 'norms_provenance', 'state'}
            or opening['semantics'] != 'declared-initial-facts-and-history-v1'
            or not isinstance(opening['identity'], str) or not 1 <= len(opening['identity']) <= 128
            or not isinstance(opening['norms_provenance'], str) or not 1 <= len(opening['norms_provenance']) <= 1024):
        raise ValueError('Explicit initial facts/history and Norm provenance required')
    if not isinstance(opening['date'], str) or date.fromisoformat(opening['date']).isoformat() != opening['date']:
        raise ValueError('ISO opening date required')
    state = deepcopy(opening['state'])
    if not isinstance(state, dict) or set(state) != STATE_SECTIONS:
        raise ValueError('Opening state section roster differs')
    if not isinstance(state['importer_settings'], list):
        raise ValueError('Explicit opening settings bag required')
    for section in STATE_SECTIONS - {'importer_settings'}:
        if not isinstance(state[section], dict):
            raise ValueError('Opening section must be an explicit object: '+section)
    metadata = state['publication_context']
    if set(metadata) != {'label'} or not isinstance(metadata['label'], str) or len(metadata['label']) > 1024:
        raise ValueError('Opening publication metadata must be a bounded label; no state payload')
    for owner, tables in masters.items():
        for table, rows in tables.items():
            if table in state[owner]:
                raise ValueError('Master population has conflicting opening ownership: '+owner+'/'+table)
            state[owner][table] = deepcopy(rows)
    if set(state['importer']) != set(PRIOR_TABLES):
        raise ValueError('Required importer opening populations differ')
    for section, required in CONTRACT['required_opening_populations'].items():
        if section in ('importer', 'complete'):
            continue
        allowed = set(CONTRACT['allowed_opening_populations'][section])
        if section == 'dbm':
            allowed.add('PhaseOutRecommendation')
        if section == 'btr':
            allowed.add('RationingHistory')
        if section == 'controls':
            required = CONTROL_TABLES
            allowed = set(CONTROL_TABLES)
        if set(state[section]) - allowed or not set(required) <= set(state[section]):
            raise ValueError('Opening population roster differs: '+section)
    if set(state['complete']) - set(CONTRACT['allowed_opening_populations']['complete']):
        raise ValueError('Unknown complete opening populations')
    # A fresh recommendation population is computed empty, never an operator
    # fact or an imported answer. Older initialization envelopes remain valid.
    if state['dbm'].get('PhaseOutRecommendation'):
        raise ValueError('Initial opening cannot seed phase recommendations')
    state['dbm'].setdefault('PhaseOutRecommendation', [])
    state['btr'].setdefault('RationingHistory', [])
    for section in STATE_SECTIONS - {'importer_settings', 'publication_context'}:
        for name, rows in state[section].items():
            if name == 'IntermediateTables' and rows in ({}, []):
                continue
            if not is_record_rows(rows):
                raise ValueError('Explicit opening bag required: '+section+'/'+name)
    for table, fields in BPR_TABLES.items():
        nullable = ('ParentWhCode', 'SKUIntroDate') if table == 'BPRMaster' else ('Stock',) if table == 'DailyConsumption' else ()
        state['bpr'][table] = daily_rows(state['bpr'][table], fields, nullable)
    if any(date.fromisoformat(row['ReportDate']) > date.fromisoformat(opening['date'])
           for row in state['bpr']['DailyConsumption']):
        raise ValueError('Opening history cannot contain future calculated stock')
    if state['controls']['last_batch'] != [{'LastRunDate': opening['date']+'T00:00:00'}]:
        raise ValueError('Opening control date identity differs')
    for section, populations in (
        ('bpr', ('BPRMaster', 'Plants', 'NoNormMaster', 'DailyConsumption')),
        ('supplier', ('SOBData', 'MOQData')),
        ('consumer_context', ('NMSAllItems',)),
        ('complete', REQUIRED), ('dbm', ('DBMMaster', 'Suggestions', 'NormAcceptanceTbl'))):
        if any(name not in state[section] or not is_record_rows(state[section][name]) for name in populations):
            raise ValueError('Required opening populations missing: '+section)
    if state['dbm']['Suggestions'] or state['controls']['suggestions'] or state['complete']['ProdOrderSuggestions']:
        raise ValueError('Initial opening cannot seed future suggestions/results')
    validate_flag_roster(state['complete']['ScriptExecutedFlag'])
    batches = owner_batches(state, strict=True)
    # Master type normalization is explicit and shared with existing projections.
    # Only caller-owned populations are supplied; BPR/use projections are derived.
    for _, _, kwargs, rows, path in batches:
        if ':' not in path and kwargs.get('owner') != 'BPR':
            parts = path.split('/')[3:]
            target = state
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = storage(rows)
    exclusions = value['pair_exclusions']
    if not isinstance(exclusions, list) or any(not isinstance(row, dict)
            or set(row) != {'SKUCode', 'WhCode'}
            or any(item is not None and (not isinstance(item, str) or len(item) > 50)
                   for item in row.values()) for row in exclusions):
        raise ValueError('Explicit typed pair exclusions required')
    frame = dict(recipe=deepcopy(recipe), profile=deepcopy(profile), pair_exclusions=deepcopy(exclusions),
        opening=dict(identity=opening['identity'],
        opening_date=opening['date'], semantics=opening['semantics'],
        norms_provenance=opening['norms_provenance'], state=state))
    from mta.mdm.initialization_rows import validate_tree
    validate_tree(frame)
    initial_state(state, date.fromisoformat(opening['date']))
    if any(profile['delivery']['batch'][name] == 1 for name in (
            'ActivateNorm0Report30Days', 'ActivateNorm0Report60Days', 'ActivateNorm0Report90Days',
            'ActivateNorm1Report30Days', 'ActivateNorm2Report30Days')):
        from mta.domain.dbm_norm012 import selected_report_configuration
        selected_report_configuration(state['dbm']['ui_ReportConfigurations'])
    expected_flags = dict(from_ui=True,
        ignore_master_norm=sum(row == {'Parameter': 'FNC_MatchMasterNorm', 'Value': '0'}
            for row in state['controls']['dbm_settings']) == 1,
        nms_active=sum(row == {'Parameter': 'NMSActive', 'Value': '1'}
            for row in state['controls']['importer_settings']) == 1)
    if profile['force_flags'] != expected_flags or profile['delivery']['controls']['from_ui'] is not True:
        raise ValueError('Initial force/control flags differ from supported persisted configuration')
    return value, frame, batches
