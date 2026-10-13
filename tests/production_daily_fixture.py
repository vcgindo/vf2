"""Finite supplied H3 test facts; no production extractor/scenario generator."""
from copy import deepcopy
from tests.initialization_input_fixture import supplied_input, supplied_row
from mta.runtime import mdm_models, mdm_skuloc_models

SKU = 'SUPPLIEDZ9'
CHILD = 'OWN-WH8'
ROOT = 'OWN-ROOT7'
OPENING_DATE = '2037-04-09'


def initialized_input():
    # Controller-declared H3 proof-only identity delta; no operator filtering.
    # Preserve every other value, duplicate and ordinal from the supplied bag.
    def identity_delta(value):
        if isinstance(value, dict):
            return {key: identity_delta(item) for key, item in value.items()}
        if isinstance(value, list):
            return [identity_delta(item) for item in value]
        return SKU if value == 'SUPPLIED-Z9' else value
    value = identity_delta(supplied_input())
    master = value['masters']['importer']
    sku = supplied_row(mdm_models.MdmSkuAttributes, sku=SKU)
    sku.update(ElephantOrderCapping=None, Weight='2.125', Volume='1.000')
    master['SkuAttributeData'] = [sku]
    master['SKUDescriptionTbl'] = [dict(SKUCode=SKU, SKUDescription='Supplied product')]
    master['LocationAttributeData'] = []
    master['SiteDescriptionTbl'] = []
    master['SkuLocAttributeData'] = []
    master['MasterData'] = []
    current = []
    for location in (CHILD, ROOT):
        attributes = supplied_row(mdm_models.MdmLocationAttributes, location=location)
        attributes.update(LocationType='Plant' if location == ROOT else 'Warehouse', LogisticsLocation=None)
        master['LocationAttributeData'].append(attributes)
        master['SiteDescriptionTbl'].append(dict(WHCode=location, WHDescription='Supplied '+location))
        pair = supplied_row(mdm_skuloc_models.MdmSkuLocPair, sku=SKU, location=location)
        pair.update(PackSize=1, SpikeThreshold=None, PSOThreshold=None, FGRMFlag='FG',
            StockPercentForRationing=0, NormPercentReservation=0, NonNMS=False)
        master['SkuLocAttributeData'].append(pair)
        norm = dict(SKUCode=SKU, WhCode=location, Norm=12, MinNorm=1, RLT=3, RCP=3,
            GCP=3, OCP=3, MinOrderCount=1, ParentWhCode=ROOT, SKUIntroDate='2001-02-03')
        if location == CHILD:
            master['MasterData'].append(norm)
        item = supplied_row(mdm_skuloc_models.MdmSkuLocCurrent, sku=SKU, location=location)
        item.update(**norm, SKUDescription='Supplied product', WHDescription='Supplied '+location,
            ParentDescription='Supplied '+ROOT, PackSize=1, StockPercentForRationing=0,
            NormPercentReservation=0, Weight='2.125', Volume='1.000', ElephantOrderCapping=None,
            FGRMFlag='FG', DBMActive=True, LocationType=attributes['LocationType'], LogisticsLocation=None)
        if location == CHILD:
            current.append(item)
    for owner in ('btr', 'dbm'):
        value['masters'][owner] = {name: deepcopy(master[name]) for name in ('SkuAttributeData', 'SKUDescriptionTbl')}
    state = value['opening']['state']
    state['consumer_context']['NMSAllItems'] = current
    state['bpr']['BPRMaster'] = [dict(SKUCode=SKU, WHCode=location, Norm=12,
        ParentWhCode=ROOT, SKUIntroDate='2001-02-03') for location in (CHILD,)]
    state['bpr']['Plants'] = [dict(PlantCode=ROOT, PlantName='Supplied root')]
    state['dbm']['DBMMaster'] = deepcopy(master['MasterData'])
    state['controls']['dbm_master'] = deepcopy(master['MasterData'])
    state['controls']['importer_master'] = deepcopy(master['MasterData'])
    state['controls']['log'] = []
    state['orders']['OrderIdentity'] = [dict(Seed=1, Increment=1, LastValue=1)]
    state['importer_settings'].extend([dict(Parameter='NMSMOQInputDataFormat', Value='WithDestLoc'),
        dict(Parameter='ActivateNMSUIUploadLogs', Value='0')])
    state['controls']['importer_settings'] = deepcopy(state['importer_settings'])
    calculation = value['configuration']['calculation']
    # Explicit controller-selected ownership proof profile. Unsupported 60/90
    # output capabilities remain H4 exits, not inferred deployment defaults.
    value['configuration']['delivery']['batch'].update(
        ActivateNorm0Report60Days=0, ActivateNorm0Report90Days=0)
    calculation['skus'] = [dict(sku_code=SKU, description='Supplied product')]
    calculation['locations'] = [dict(location_code=location, description='Supplied '+location,
        location_type='Plant' if location == ROOT else 'Warehouse') for location in (CHILD, ROOT)]
    calculation['stock_openings'] = [dict(sku_code=SKU, location_code=location, stock=40,
        utilized_stock=0, stock_percent_reservation=0, norm_percent_reservation=0) for location in (CHILD,)]
    calculation['policies'] = [dict(sku_code=SKU, location_code=location, rationing_priority=3,
        policy=dict(pso_high=50, pso_low=30, pso_override=None, spike_high=60,
            spike_low=40, spike_override=None)) for location in (CHILD,)]
    value['configuration']['daily']['distributor_codes'] = []
    return value


def day_input(day, *, root=False):
    return dict(schema='fresh-production-day-input-v1',
        consumer_opening=dict(requests=[], remarks=dict(bpr=[], bor=[], boroa=[])) if root else None,
        day=dict(business_date=day, raw_non_nms=[], raw_no_norm=[],
            raw_daily=[dict(SKUCode=SKU, WhCode=location, Stock=40 if location == ROOT else 10,
                Consumption=2, GIT=0, Receipts=0, PSO=0, ReportDate=day) for location in (CHILD, ROOT)],
            accepted_feed=[], order_feed_status='PRESENT', order_feed=[], order_raw=[],
            distributor_transactions=[dict(WhCode=CHILD, TransactedItemCount=2, TotalItems=2, ReportDate=day)],
            vendor_transactions=[], new_force_requests=[],
            control_requests=dict(phase_requests=[], phase_stops=[], phase_in_requests=[], season_requests=[]),
            phase_controls_input_validation=True, seasonality_input_validation=True))
