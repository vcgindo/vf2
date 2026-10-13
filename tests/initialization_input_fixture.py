"""Small supplied-input component fixture; never an engine/scenario generator."""
from copy import deepcopy
import hashlib
import json

from mta.serialization import digest
from mta.mdm.master_owners import business_fields
from mta.mdm.initialization_contract import CONTRACT, MASTER_TABLES, STATE_SECTIONS
from mta.runtime import mdm_models, mdm_skuloc_models
from mta.application.r1_importer_master import PRIOR_TABLES
from mta.application.daily_finalization import FLAG_SEED
from mta.application.r1_daily_input import FLAGS
from mta.domain.control_carry import TABLES as CONTROL_TABLES


def supplied_row(model, sku='SUPPLIED-Z9', location='OWN-WH8'):
    values = {}
    for field in business_fields(model):
        if field.null:
            values[field.name] = None
            continue
        kind = field.get_internal_type()
        values[field.name] = ('2001-02-03' if kind == 'DateField' else
            False if kind == 'BooleanField' else 7 if 'IntegerField' in kind else
            1.25 if kind == 'FloatField' else '1.00' if kind == 'DecimalField' else 'Provided')
    for name in values:
        if name == 'SKUCode':
            values[name] = sku
        if name in ('WHCode', 'WhCode', 'LocCode', 'ParentWhCode'):
            values[name] = location
    if 'Weight' in values:
        values['Weight'] = '2.125'
    return values


def supplied_input():
    models = {'SkuAttributeData': mdm_models.MdmSkuAttributes,
        'SKUDescriptionTbl': mdm_models.MdmSkuDescription,
        'LocationAttributeData': mdm_models.MdmLocationAttributes,
        'SiteDescriptionTbl': mdm_models.MdmLocationDescription,
        'SkuLocAttributeData': mdm_skuloc_models.MdmSkuLocPair,
        'MasterData': mdm_skuloc_models.MdmSkuLocMasterPair}
    masters = {owner: {name: [supplied_row(models[name]), supplied_row(models[name])]
        for name in tables} for owner, tables in MASTER_TABLES.items()}
    state = {section: {} for section in sorted(STATE_SECTIONS)}
    for section, names in CONTRACT['required_opening_populations'].items():
        state[section] = {name: [] for name in names}
    state['importer'] = {name: [] for name in PRIOR_TABLES if name not in MASTER_TABLES['importer']}
    for owner, tables in MASTER_TABLES.items():
        for name in tables:
            state[owner].pop(name, None)
    state['importer_settings'] = [dict(Parameter=name, Value=value) for name, value in (
        ('NMSActive', '1'), ('DBMActive', '1'), ('UpdatePWh_RLT_RCP_GCP', '1'),
        ('TaskStatusLogHorizon', '7'), ('IsBatchFileExecuted', '0'),
        ('IsBPRBatchFileExecuted', '0'), ('BatchFileExecutionDate', '2037-04-09T00:00:00'))]
    state['controls'] = {name: [] for name in CONTROL_TABLES}
    state['controls']['IntermediateTables'] = {}
    state['controls']['last_batch'] = [{'LastRunDate': '2037-04-09T00:00:00'}]
    state['controls']['importer_settings'] = deepcopy(state['importer_settings'])
    state['controls']['log'] = [dict(SKUCode='SUPPLIED-Z9', WHCode='OWN-WH8',
        OldNorm=7, NewNorm=8, NormChangeDate='2037-04-08', NormChangeReason=5)] * 2
    state['complete']['ScriptExecutedFlag'] = deepcopy(FLAG_SEED)
    state['consumer_context']['NMSAllItems'] = [supplied_row(mdm_skuloc_models.MdmSkuLocCurrent)] * 3
    state['dbm']['FirstReplenishmentPercentageTbl'] = [dict(ReplenishmentPercentage=50)]
    state['dbm']['DBMSettingsTbl'] = [dict(Parameter='SpikeRuleHorizon', Value='7'),
                                   dict(Parameter='SpikeRuleParCount', Value='3')]
    state['dbm']['IntermediateTables'] = []
    state['dbm']['ui_ReportConfigurations'] = [dict(ReportName='Norm_0_1_2Report',
        Col_Code=code, Col_Position=position, Header=code, Visible=True,
        CellAlignment=None, Value=None, TagID=None) for position, code in enumerate(
        ('SKUCode', 'SKUName', 'WHCode', 'WhName', 'ParentWhCode', 'ParentNorm',
         'NumOfDaysSold', 'TotalSale', 'Occurances'), 1)]
    state['publication_context'] = {'label': 'supplied opening; no accepted day'}
    profile = dict(import_non_nms=False, daily_publication=True,
        daily_publication_config={'bpr_remark_horizon': 13},
        daily=dict(settings=[dict(Parameter='MissingDailyDataHandling', Value='1')],
            vf_settings=[dict(Parameter='GenerateBPRForMissingInventoryLoc', Value='0')],
            shell_flags=dict.fromkeys(FLAGS, 0),
            distributor_codes=['OWN-WH8', 'OWN-WH8'], vendor_codes=[], vector_dms_codes=[]),
        calculation=dict(skus=[dict(sku_code='SUPPLIED-Z9', description='Provided')]*2,
            locations=[dict(location_code='OWN-WH8', description='Provided', location_type='WH')],
            stock_openings=[dict(sku_code='SUPPLIED-Z9', location_code='OWN-WH8', stock=20,
                utilized_stock=0, stock_percent_reservation=0, norm_percent_reservation=0)],
            policies=[dict(sku_code='SUPPLIED-Z9', location_code='OWN-WH8', rationing_priority=3,
                policy=dict(pso_high=50, pso_low=30, pso_override=None,
                    spike_high=60, spike_low=40, spike_override=None))],
            logistics=dict(items=[], vehicles=[], location_vehicles=[]),
            stock_configuration={'reservation_type': 0, 'reservation_for_rationing_only': True}),
        force_flags=dict(from_ui=True, ignore_master_norm=False, nms_active=True),
        delivery=dict(site_code='SUPPLIED-INSTANCE', batch=dict(
            AutoDBMActive=0, PhaseOutRecommendation30Days=0, PhaseOutRecommendation60Days=0,
            PhaseOutRecommendation90Days=0, DBMNormChangeReportHorizon=1, NormChangeLogHorizon=7,
            GatherSuspensionHistory=1, ActivateNormChangeLogReport=1, DailyConsumptionHorizonDBM=370,
            ActivateNorm0Report30Days=1, ActivateNorm0Report60Days=1, ActivateNorm0Report90Days=1,
            ActivateNorm1Report30Days=1, ActivateNorm2Report30Days=1),
            controls=dict(from_ui=True, start_percent=50, history_horizon=7),
            btr_settings=dict(CaptureDispatchExecutionEfficiency=0, GenerateColorAgeingReport=1,
                BRAgeColorTolerance=1, CARNoColorToleranceDuration=2,
                NormSuggestion_Upward='3', NormSuggestion_Downward='4')),
        complete_pick={'policy': 'canonical-tied-order-v1'},
        complete_daily=dict(policy='generic-finalization-active-nms-v1', consumption_days=43, remark_days=13))
    profile['calculation']['allocation'] = {'advance_stock_threshold_percent': 50}
    profile['calculation']['replenishment_exclusions'] = []
    return dict(schema='fresh-production-initialization-input-v1',
        recipe=dict(projection='native-base-owner-projection-v1', extractor='already-supplied-input',
            version='operator-contract-test-v7', source_identity='independent-supplied-source-K8'),
        configuration=profile, masters=masters,
        opening=dict(identity='SUPPLIED-OPENING-K8', date='2037-04-09',
            semantics='declared-initial-facts-and-history-v1', norms_provenance='Explicit supplied starting Norms', state=state),
        pair_exclusions=[])


def encoded(value):
    raw = (json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n').encode('utf-8')
    return raw, hashlib.sha256(raw).hexdigest(), dict(
        expected_configuration=digest(value['configuration']), expected_recipe=digest(value['recipe']))
