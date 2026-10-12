"""Connected daily calculation with one owner for every persisted closing table.

External day facts are separate from state. The R1 calculation input below is
an internal projection of actual current producers, never an external answer.
"""

from copy import deepcopy
from mta.evidence import validating, final_stage

from decimal import Decimal

from datetime import date, datetime

import hashlib

import json

from mta.application.r1_importer_master import process_importer_master, PRIOR_TABLES, _sql_key

from mta.application.r1_supplier_input import process_supplier_validation, supplier_calculation_state, STAGES as SUPPLIER_STAGES

from mta.application.r1_daily_input import process_daily_validation, STAGES as DAILY_STAGES

from mta.application.r1_daily_entry import generated_bpr_daily_state

from mta.application.r1_master_state import MASTER_FIELDS, reconcile_master_state

from mta.application.r1_raw_master_entry import MASTER_SOURCE_MAP

from mta.application.r1_input import prepare_r1_current_day

from mta.domain.control_carry import control_stages

from mta.domain.order_closing import order_stages

from mta.domain.bpr_construction import constructor_then_late

from mta.domain.dbm_selected_chain import selected_stages

CAPABILITY='r2_calculation_timeline'

TABLES=('ClosingState','MasterValidation','SupplierStages','DailyStages','ControlStages','OrderStages',
        'CalculationInput','CalculationOutputs','CalculationRun','BPRStages','DBMStages')

DELIVERY_TABLES = TABLES + ('BPRFinal', 'DBMFinal', 'Reports', 'BTRFinal', 'BTRStages',
                           'MajorBoundaries', 'Lineage', 'PublicationContext')

SHARED_CONTROLS={'dbm_master':'DBMMaster','suggestions':'Suggestions','reason_codes':'ReasonCodes',
    'acceptance':'NormAcceptanceTbl','phase_out':'PhaseOutTbl','phase_in':'PhaseInTbl','seasonality':'Seasonality',
    'forced':'ForcedNormChangeTbl','log':'NormChangeLogTbl','suggestions_log':'SuggestionsLog',
    'order_summary':'OrderDataSummary','suspend_order_type':'SuspendOrderType','dbm_settings':'DBMSettingsTbl'}

EMPTY_NATIVE_FIELDS = {
    'PhaseOutTbl': ('SKUCode', 'WHCode', 'OldNorm', 'NewNorm', 'PhaseOutFinished',
                    'PhaseOutStartDate', 'LastProcessedDate', 'PhaseInSKUCode'),
    'PhaseInTbl': ('SKUCode', 'WHCode', 'OldNorm', 'NewNorm', 'TargetNorm',
                   'PhaseOutSKUOrigNorm', 'PhaseInStartDate', 'LastProcessedDate'),
}

def json_value(value):
    """Storage representation only; preserve NULL, booleans and row multiplicity."""
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, Decimal): return format(value, 'f')
    if isinstance(value, dict): return {k: json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [json_value(v) for v in value]
    return value

def scratch_tables(value):
    if isinstance(value, dict): return deepcopy(value)
    return {r['table']: deepcopy(r['rows']) for r in value}

def control_rows(rows):
    return [{('WhCode' if k=='WHCode' else k):v for k,v in r.items()} for r in rows]

def native_rows(rows,fields):
    """Exact native case projection; no value defaults or business calculation."""
    return [{f:r[f] if f in r else r['WhCode'] for f in fields} for r in rows]

def delivery_control_types(state):
    """Represent SQL BIT control fields with the selected driver's bool type."""
    for row in state['phase_out']:
        if row['PhaseOutFinished'] is not None:
            row['PhaseOutFinished'] = bool(row['PhaseOutFinished'])
    return state

def initialise_sku_loc_standard_attributes(importer):
    """Reproduce the canonical daily Importer TRUNCATE/INSERT boundary."""
    result = []
    seen = set()
    for table in ('MasterDataRaw', 'MasterDataRawNonNMS'):
        for row in importer[table]:
            key = (row['SKUCode'], row['WhCode'])
            if key in seen:
                continue
            seen.add(key)
            result.append({'SKUCode': key[0], 'WhCode': key[1], 'Price': None,
                           'SLT': None, 'Tags': None, 'Category': None,
                           'ExtendedOCP': None})
    return result

def entry_inputs(prior, opening_date, day, profile, identity):
    today=day['business_date']
    master={'schema':'r1-importer-master-input-v1','business_date':today,'run_timestamp':today+'T00:00:00',
        'import_non_nms':profile['import_non_nms'],'settings':[
            {'Parameter':r['Parameter'],'Value':int(r['Value'])} for r in prior['importer_settings']
            if r['Parameter'] in ('NMSActive','DBMActive','UpdatePWh_RLT_RCP_GCP')],
        'prior_provenance':{'kind':'SYNTHETIC_PRIOR_IMPORTER','identity':identity,'business_date':opening_date},
        'prior':deepcopy(prior['importer']), 'raw_master':day['raw_master'],
        'raw_non_nms':day['raw_non_nms'],'raw_no_norm':day['raw_no_norm']}
    # SQL BIT values retain booleans in closing state; the established importer
    # typed input contract represents BIT as0/1. This is a declared type adapter.
    for rows in master['prior'].values():
        for row in rows:
            for k,v in row.items():
                if type(v) is bool:row[k]=int(v)
    daily={'schema':'r1-daily-input-v1','raw_daily_data':day['raw_daily'],**deepcopy(profile['daily']),
        'prior_bpr':{**deepcopy(prior['bpr']),'opening_provenance':{
            'kind':'SYNTHETIC_PRIOR_BPR_DAILY','identity':identity,'business_date':opening_date}}}
    return master,daily

def project_phase_out_calculation_membership(policies, phase_out):
    """Project the two-key PhaseOutTbl membership consumed by BPR calculation."""
    by_key = {(row['sku_code'], row['location_code']): row for row in policies}
    if len(by_key) != len(policies):
        raise ValueError('Ambiguous calculation policy key')
    seen = set()
    membership = []
    for row in phase_out:
        key = (row['SKUCode'], row['WhCode'])
        if key in seen:
            raise ValueError('Ambiguous PhaseOutTbl calculation membership')
        seen.add(key)
        if key not in by_key:
            raise ValueError('PhaseOutTbl calculation membership lies outside policy closure')
        membership.append({'SKUCode': key[0], 'WhCode': key[1]})
    return membership

def producer_owned_logistics(logistics, importer):
    """Project the canonical Pick attribute joins, not retained profile overrides.

    GenerateLogisticPickList.sql joins SKU/location attributes and excludes
    only rows whose Weight AND Volume are NULL. Keep candidate/join duplicates;
    NULL LogisticsLocation remains NULL for the existing Pick ISNULL fallback.
    """
    skus, locations = {}, {}
    for row in importer['SkuAttributeData']:
        skus.setdefault(_sql_key(row['SKUCode']), []).append(row)
    for row in importer['LocationAttributeData']:
        locations.setdefault(_sql_key(row['WHCode']), []).append(row)
    result = deepcopy(logistics)
    result['items'] = []
    for item in logistics['items']:
        for sku in skus.get(_sql_key(item['sku_code']), []):
            if sku['Weight'] is None and sku['Volume'] is None:
                continue
            for location in locations.get(_sql_key(item['to_location']), []):
                result['items'].append({**deepcopy(item), 'weight': sku['Weight'],
                    'volume': sku['Volume'], 'logistics_location': location['LogisticsLocation']})
    return result


def calculation_source(today, opening_date, profile, importer, dbm_master, processed, sourcing, supplier_prior,
                       identity, phase_out=None):
    config=deepcopy(profile['calculation'])
    config['logistics'] = producer_owned_logistics(config['logistics'], importer)
    attrs={(r['SKUCode'],r['LocCode']):r for r in importer['SkuLocAttributeData']}
    skus={r['SKUCode']:r for r in importer['SkuAttributeData']}
    project=lambda rows:[{f:r[s] for f,s in MASTER_SOURCE_MAP.items()} for r in rows]
    masters=project(importer['MasterData'])
    for r in masters:
        a=attrs[r['sku_code'],r['location_code']]
        r.update(pack_size=a['PackSize'],elephant_order_capping=skus[r['sku_code']]['ElephantOrderCapping'])
    positions=[]
    for r in masters:
        matches=[p for p in processed if (p['SKUCode'],p['WhCode'],p['ReportDate'])==(r['sku_code'],r['location_code'],today)]
        if len(matches)!=1 or matches[0]['Stock'] is None:
            raise ValueError('Missing/ambiguous current physical stock reaches calculation; no substituted input')
        p=matches[0]
        positions.append({'sku_code':p['SKUCode'],'location_code':p['WhCode'],'business_date':today,
                          'stock_quantity':p['Stock'],'goods_in_transit_quantity':p['GIT']})
    stock={(r['sku_code'],r['location_code']):r['stock_quantity'] for r in positions}
    for r in config['stock_openings']:
        a=attrs[r['sku_code'],r['location_code']]
        r.update(stock=stock[r['sku_code'],r['location_code']],stock_percent_reservation=a['StockPercentForRationing'],norm_percent_reservation=a['NormPercentReservation'])
    for r in config['policies']:
        a=attrs[r['sku_code'],r['location_code']]
        r['policy'].update(spike_override=a['SpikeThreshold'],pso_override=a['PSOThreshold'])
    for r in sourcing+supplier_prior:r['pack_size']=attrs[r['sku_code'],r['location_code']]['PackSize']
    result={'schema':'r1-current-day-input-v5','foundation':{
        'snapshot':{'snapshot_id':identity+'-'+today,'business_date':today,'source_kind':'SYNTHETIC_R1',
                    'site_code':'VECTORFLOW-DEMO','configuration_version':'block3-calculation-timeline-v1',
                    'captured_at':today+'T00:00:00+00:00'},
        'skus':config.pop('skus'),'locations':config.pop('locations'),'inventory_positions':positions},
        'master_state':{'importer_master':masters,'dbm_opening':project(dbm_master),
            'opening_provenance':{'kind':'SYNTHETIC_PRIOR_DBM','identity':identity+'-own-produced-controls','business_date':opening_date}},
        'orders':[],'sourcing':sourcing,'supplier_openings':supplier_prior,**config}
    if phase_out is not None:
        result['master_state']['phase_out_membership'] = project_phase_out_calculation_membership(
            result['policies'], phase_out)
    result['foundation']['snapshot']['source_manifest_checksum']=hashlib.sha256(
        json.dumps(json_value(result),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result

def additional_native(prepared, importer):
    caps={r['SKUCode']:r['ElephantOrderCapping'] for r in importer['SkuAttributeData']}
    return [{'SKUCode':r['sku_code'],'WhCode':r['location_code'],'TopmostWhCode':r['topmost_location_code'],
        'ElephantOrderCapping':caps[r['sku_code']],**{a:int(Decimal(str(r[b]))) for a,b in (
            ('WhLevel','wh_level'),('TopmostWhNorm','topmost_norm'),('TopmostWhPacksize','topmost_pack_size'),('RLTTillPlantSupplier','cumulative_rlt_days'))},
        'SpikeThreshold':format(Decimal(str(r['spike_threshold_percent'])),'.2f'),
        'PSOThreshold':format(Decimal(str(r['pso_threshold_percent'])),'.2f')} for r in prepared.additional_master]

def calculate_day(prior, opening_date, day, profile, identity, execute_calculation,
                  report_exceptions=None):
    # Finish calculation before normalization so its temporary frames are gone.
    # Replacing one owned checkpoint at a time preserves the exact json_value
    # representation without a simultaneous second copy of the complete trace.
    result = _calculate_day_native(prior, opening_date, day, profile, identity,
                                   execute_calculation, report_exceptions)
    if validating():
        for name in result:
            result[name] = json_value(result[name])
    return result


def _calculate_day_native(prior, opening_date, day, profile, identity, execute_calculation,
                          report_exceptions=None):
    """execute_calculation runs the existing modern R1 producer and returns outputs/id."""
    today=day['business_date'];now=today+'T00:00:00'
    from mta.application import daily_finalization
    finalization = daily_finalization.configuration(profile)
    if finalization is not None:
        prior = daily_finalization.begin(prior, today, policy=finalization['policy'])
        day = daily_finalization.fresh_feeds(prior, day, policy=finalization['policy'])
    completion = prior['complete'] if finalization is not None else None
    master_input,daily_input=entry_inputs(prior,opening_date,day,profile,identity)
    master=process_importer_master(master_input)
    if master['outcome']!='APPLIED':raise ValueError('Connected master producer did not apply')
    if completion is not None:
        daily_finalization.mark(completion, 'ValidateAndProcessMaster.sql')
    supplier=process_supplier_validation(day['supplier_feeds'],master,master_input['settings'],now)
    supplier_final=supplier[SUPPLIER_STAGES[-1]]['tables']
    if any(v['outcome']=='SQL_ERROR' for v in supplier.values()):raise ValueError('Supplier producer failed')
    daily_master=deepcopy(master)
    for table in ('SiteDescriptionTbl','RejectedMaster'):daily_master['tables'][table]=supplier_final[table]
    daily=process_daily_validation(daily_input,daily_master,today,now)
    if any(v['outcome']=='SQL_ERROR' for v in daily.values()):raise ValueError('Daily producer failed')
    daily_final=daily[DAILY_STAGES[-1]]['tables']
    importer=deepcopy(master['tables'])
    importer['SiteDescriptionTbl']=deepcopy(supplier_final['SiteDescriptionTbl'])
    importer['RejectedMaster']=deepcopy(daily_final['RejectedMaster'])
    supplier_state,old_sourcing,new_sourcing=supplier_calculation_state(prior['supplier'],supplier_final,importer['MasterData'],vendor_codes=profile['daily']['vendor_codes'])
    source=calculation_source(today,opening_date,profile,importer,prior['dbm']['DBMMaster'],daily_final['DailyDataProcessed'],new_sourcing,old_sourcing,identity)
    refreshed=reconcile_master_state(source)
    controls=deepcopy(prior['controls'])
    controls['IntermediateTables']=scratch_tables(controls['IntermediateTables'])
    for target,src in SHARED_CONTROLS.items():controls[target]=control_rows(prior['dbm'][src])
    controls['dbm_master']=[{s:r[f] for f,s in MASTER_SOURCE_MAP.items()} for r in refreshed['dbm_master']]
    controls.update(importer_master=deepcopy(importer['MasterData']),raw_master=deepcopy(importer['MasterDataRaw']),
        force_requests=deepcopy(importer['ForceNormChange']),importer_settings=[{'Parameter':r['Parameter'],'Value':str(r['Value'])} for r in supplier_final['ImporterSettingsTbl']])
    if finalization is not None:
        controls['importer_settings'] = daily_finalization.preserve_settings(
            prior['importer_settings'], controls['importer_settings'])
    if day.get('phase_controls_input_validation'):
        from mta.application.phase_input_validation import validate_phase_inputs
        names = ('phase_requests', 'phase_stops', 'phase_in_requests')
        inputs = [prior['control_aux'][name] + day['control_requests'][name] for name in names]
        validated_phase = validate_phase_inputs(*inputs, importer['RejectedMaster'], now)
        for name in names:
            prior['control_aux'][name] = []
            day['control_requests'][name] = validated_phase[name]
        importer['RejectedMaster'] = validated_phase['rejected_master']
        if completion is not None:
            daily_finalization.mark(completion, 'ValidatePhaseout.sql', 'ValidatePhaseInNorms.sql')
    if day.get('seasonality_input_validation'):
        from mta.application.seasonality_validation import validate_seasonality_data
        validated_season = validate_seasonality_data(prior['control_aux']['season_requests'],
            importer['MasterData'], importer['RejectedMaster'], now)
        prior['control_aux']['season_requests'] = validated_season['seasonality']
        importer['RejectedMaster'] = validated_season['rejected_master']
    delivery = profile.get('delivery')
    control_aux = diagnostics = None
    force_alert_capture = None
    if profile.get('operational_force_sources') is not None:
        from mta.application.timeline_controls import FORCE_CAPTURE_POLICY
        from mta.application.operational_capture import CAPTURE_POLICY
        if (profile['operational_force_sources'] != FORCE_CAPTURE_POLICY
                or profile.get('operational_sources') != CAPTURE_POLICY or delivery is None):
            raise ValueError('Explicit operational force capture policies and delivery required')
        force_alert_capture = {}
    if delivery is not None:
        controls['importer_settings'].extend(deepcopy(profile['daily']['settings']))
        from mta.application.timeline_controls import timeline_control_stages, EXTRA_TABLES
        from mta.domain.control_carry import TABLES as CONTROL_TABLES
        connected = final_stage(timeline_control_stages(today, opening_date, controls,
            prior['control_aux'], day, {**delivery['controls'], 'force_flags': profile['force_flags']},
            daily_final['DailyDataProcessed'], importer['SkuLocAttributeData'],
            force_alert_capture=force_alert_capture))
        for _, state, _ in connected:
            delivery_control_types(state)
        if completion is not None:
            # The accepted compound control generator is fully consumed even
            # when evidence mode retains only its final snapshot.
            daily_finalization.mark(completion, 'UpdateNormChanges.sql')
        control = [(name, state) for name, state, _ in connected]
        complete = connected[-1][1]
        control_final = {n: deepcopy(complete[n]) for n in CONTROL_TABLES}
        control_aux = {n: deepcopy(complete[n]) for n in EXTRA_TABLES}
        diagnostics = connected[-1][2]
    else:
        control=final_stage(control_stages(today,opening_date,controls,profile['force_flags'],day['accepted_feed'],day['new_force_requests']))
        control_final=deepcopy(control[-1][1])
    completed_boundaries=['controls']
    importer['MasterData']=deepcopy(control_final['importer_master'])
    importer['ForceNormChange']=deepcopy(control_final['force_requests'])
    nms = None
    standard_attributes = None
    if finalization is not None:
        nms = daily_finalization.nms_snapshot(importer, control_final, prior, day['exclusions'])
        importer['MasterData'] = nms['MasterData']
        control_final['importer_master'] = deepcopy(nms['MasterData'])
        from mta.application.r1_transit_tags import update_transit_tags
        standard_attributes = initialise_sku_loc_standard_attributes(importer)
        tagged = update_transit_tags(
            [{name: row[name] for name in ('SKUCode', 'WhCode', 'Tags')}
             for row in standard_attributes], control_final['seasonality'],
            control_final['phase_out'])
        for row, tag in zip(standard_attributes, tagged, strict=True):
            row['Tags'] = tag['Tags']
        daily_finalization.mark(completion, 'NMSCreateSnapshot.sql', 'UpdateInTransitDataTags.sql')
    source=calculation_source(today,opening_date,profile,importer,control_final['dbm_master'],daily_final['DailyDataProcessed'],deepcopy(new_sourcing),deepcopy(old_sourcing),identity,control_final['phase_out'])
    prepared=prepare_r1_current_day(source)
    bpr_master=[{'SKUCode':r['sku_code'],'WHCode':r['location_code'],'Norm':r['norm'],
                 'ParentWhCode':r['parent_location_code'],'SKUIntroDate':r['sku_intro_date']} for r in prepared.master_state['bpr_master']]
    order_input={**deepcopy(prior['orders']),'BPRMaster':bpr_master,'DBMMaster':deepcopy(control_final['dbm_master']),
        'AdditionalMasterData':additional_native(prepared,importer),'LastBatchRunTbl':[{'LastRunDate':opening_date+'T00:00:00'}],
        'PSOData':[],'IntermediateTables':deepcopy(control_final['IntermediateTables'])}
    orders=final_stage(order_stages(today,opening_date,order_input,day['order_feed_status'],day['order_feed']))
    if completion is not None:
        daily_finalization.mark(completion, 'ImportSpikeOrders.sql', 'CalculateDD.sql')
    for r in orders[-1][1]['SpikeOrderData']:
        source['orders'].append({'order_id':r['CustomerOrderId'],'sku_code':r['SKUCode'],'location_code':r['WhCode'],
            'outstanding_quantity':r['Qty'],'accepted_on':r['IntroDate'],'customer_expected_date':r['CustomerExpectedDate'],
            'established_is_spike':r['IsSpike'],'established_due_date':r['DueDate'],
            'first_servicing_location_code':r['FirstServicingWhCode'],'established_order_key':r['OrderKey']})
    calculated,calculation_id=execute_calculation(source)
    if completion is not None:
        daily_finalization.mark(completion, *daily_finalization.CALCULATION_SCRIPTS)
    from mta.application.r1_rationed_report import rationed_report
    report=rationed_report(source,calculated,
        [{'sku_code':r['SKUCode'],'description':r['SKUDescription']} for r in importer['SKUDescriptionTbl']],
        [{'location_code':r['WHCode'],'description':r['WHDescription']} for r in importer['SiteDescriptionTbl']])
    if completion is not None:
        daily_finalization.mark(completion, 'GenerateRationReqReport.sql')
    pick_state = None
    if profile.get('complete_pick') is not None:
        if profile['complete_pick'] != {'policy': 'canonical-tied-order-v1'}:
            raise ValueError('Explicit supported complete Pick policy required')
        from mta.application.complete_daily_inputs import pick_report
        from mta.application.complete_daily_pick import calculate_native_pick
        logistics = profile['calculation']['logistics']
        if 'vehicle' in logistics or not {'vehicles', 'location_vehicles'} <= logistics.keys():
            raise ValueError('Complete Pick requires explicit vehicle IDs and parent mappings')
        pick_sources = dict(
            pick_rows=pick_report(rationed=report, bands=calculated['r1_ration_bifurcation']),
            sku_attributes=importer['SkuAttributeData'], location_attributes=importer['LocationAttributeData'],
            vehicles=[dict(VehicleID=v['vehicle_id'], VehicleName=v['name'], Weight=v['weight_capacity'],
                           Volume=v['volume_capacity']) for v in logistics['vehicles']],
            location_vehicles=[dict(LocationID=v['location_code'], VehicleID=v['vehicle_id'])
                               for v in logistics['location_vehicles']])
        pick_state = calculate_native_pick(**pick_sources)
        calculated['r1_pick_list'] = [r for r in pick_state['allocations'] if r['truck'] is not None]
        calculated['r1_pick_remaining'] = [r for r in pick_state['allocations'] if r['truck'] is None]
        if completion is not None:
            daily_finalization.mark(completion, 'GenerateLogisticPickList.sql')
    early_daily=generated_bpr_daily_state({'raw_master_entry':{'business_date':today},'raw_daily_entry':daily_input},daily)
    constructor={'BPRMaster':bpr_master,'BPRDailyConsumption':early_daily,
        'RequirementBlue':[{'SKUCode':r['sku_code'],'WhCode':r['location_code'],'BlueReq':int(Decimal(r['virtual_norm']['blue_requirement']))} for r in calculated['r1_requirement']],
        **{n:deepcopy(importer[n]) for n in ('SKUDescriptionTbl','SiteDescriptionTbl','SkuLocAttributeData')},
        'ColorSequence':[{'Color':c,'SequenceNo':i} for i,c in enumerate(('Black','Red','Yellow','Green','Blue','White','Grey'),1)],
        'PhaseInTbl':control_final['phase_in'],'PhaseOutTbl':control_final['phase_out'],'LastBatchRunTbl':[{'LastRunDate':now}],
        'DailyDataForBPR':[],'PenetrationAndColor':[],'BPRExceptions':[],'BPR_Table':[],
        'IntermediateTables':deepcopy(control_final['IntermediateTables'])}
    bpr_stages,late=constructor_then_late(today,constructor,report)
    completed_boundaries.append('final-bpr-bluezone')
    bpr_stages.append(('UpdateBPR.sql',{**late,'vf_RationedReqReport':report}))
    if completion is not None:
        daily_finalization.mark(completion, '01. ImportData.sql', 'CollectDataForBPR.sql',
            'CalculatePenetrationAndColor.sql', 'GenerateBPR.sql', 'UpdateBPR.sql')
    complete = None
    if finalization is not None:
        complete, retained_daily = daily_finalization.production_and_retention(
            complete=prior['complete'], source=source, calculated=calculated,
            bpr_master=bpr_master, importer=importer, plants=prior['bpr']['Plants'],
            report=report, late=late, today=today, config=finalization)
        complete.update({name: deepcopy(supplier_final[name])
                         for name in daily_finalization.SUPPLIER_RAW})
        late = {**late, 'BPRDailyConsumption': retained_daily}
        daily_finalization.mark(complete, 'GenSupplierWiseReq.sql',
            'ProdOrderSuggestions.sql', 'ClearHistoryData_BPR.sql')
        control_final['importer_settings'] = daily_finalization.validate_completion(
            complete, control_final['importer_settings'], today, kind='BPR')
    operational_input_tables = None
    if profile.get('operational_input_sources') is not None:
        from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY, capture_input_tables
        from mta.application.operational_capture import CAPTURE_POLICY
        if (profile['operational_input_sources'] != INPUT_CAPTURE_POLICY
                or profile.get('operational_sources') != CAPTURE_POLICY):
            raise ValueError('Explicit operational source capture policies required')
        operational_input_tables = capture_input_tables(
            controls=control_final, daily=daily_final, supplier=supplier_final)
    dbm=deepcopy(prior['dbm'])
    # ImportMasterDataComponents.bat runs the deployed Importer initializer on
    # every day before DBM/BTR. Its TRUNCATE plus distinct two-key INSERT
    # discards all prior standard-attribute values.
    dbm['SKULocStandardAttributes'] = (standard_attributes if finalization is not None
        else initialise_sku_loc_standard_attributes(importer))
    # 01.ImportMasterData replaces these complete metadata tables from this
    # day's actual Importer producer before the DBM sequence consumes them.
    for table in ('SKUDescriptionTbl','SiteDescriptionTbl','SkuAttributeData','LocationAttributeData','SkuLocAttributeData'):
        dbm[table]=deepcopy(importer[table])
    for row in dbm['SkuLocAttributeData']:
        if row['NonNMS'] is not None: row['NonNMS']=bool(row['NonNMS'])
    for n,src in SHARED_CONTROLS.items():
        if dbm[src]:fields=tuple(dbm[src][0])
        else:fields=EMPTY_NATIVE_FIELDS.get(src)
        dbm[src]=native_rows(control_final[n],fields) if fields else deepcopy(control_final[n])
    dbm['NormChangeLogTbl']=native_rows(control_final['log'],('SKUCode','WHCode','OldNorm','NewNorm','NormChangeDate','NormChangeReason'))
    dbm['LastBatchRunTbl']=[{'LastRunDate':now}]
    facts={n:deepcopy(day[n]) for n in ('order_raw','exclusions','distributor_transactions','vendor_transactions')}
    facts.update(daily_raw=deepcopy(daily_final['DailyDataRaw']),bpr_daily=deepcopy(late['BPRDailyConsumption']))
    selected = selected_stages(today, dbm, facts,
                              None if delivery is None else delivery['batch'], report_exceptions)
    required_reports = ('norm-change-export', 'norm-change-history', 'norm1-advisory',
                        'norm0-export', 'norm1-export', 'norm2-export')
    report_tables = ('ReportHeader', 'ReportRows', 'Norm0Norm1Norm2Report',
                     'Norm0_1_2ReportDetails', 'Norm1IncreaseSuggestions')
    if validating():
        dbm_stages = list(selected)
    else:
        # Copy only overwritten consumer reports, never complete intermediate states.
        dbm_stages = []
        for name, current in selected:
            boundary={'ingestion':'dbm-imported','suspension26':'final-suspensions',
                      'discard':'final-suggestions','daily-cleanup':'post-rule-reports'}.get(name)
            if boundary:completed_boundaries.append(boundary)
            if name in required_reports:
                dbm_stages.append((name, {n: deepcopy(current[n]) for n in report_tables if n in current}))
        dbm_stages.append((name, current))
    final_dbm={n:deepcopy(dbm_stages[-1][1][n]) for n in prior['dbm']}
    for n,src in SHARED_CONTROLS.items():control_final[n]=control_rows(final_dbm[src])
    if delivery is not None:
        control_final['importer_settings'].append({'Parameter': 'StockReservationType',
            'Value': str(profile['calculation']['stock_configuration']['reservation_type'])})
    closing={'importer':{n:deepcopy(importer[n]) for n in PRIOR_TABLES},'importer_settings':control_final['importer_settings'],
        'bpr':{'BPRMaster':bpr_master,'Plants':deepcopy(prior['bpr']['Plants']),'NoNormMaster':deepcopy(prior['bpr']['NoNormMaster']),
               'DailyConsumption':deepcopy(late['BPRDailyConsumption'])},
        'supplier':{'SOBData':supplier_state['refreshed_sob'],'MOQData':supplier_state['refreshed_moq']},
        'orders':{n:deepcopy(orders[-1][1][n]) for n in prior['orders']},'controls':control_final,'dbm':final_dbm}
    snapshots=lambda stages:[{'stage':n,'state':v} for n,v in stages]
    if complete is not None:
        closing['complete'] = complete
    if pick_state is not None:
        closing.setdefault('complete', {}).update({name: pick_state[name] for name in
                              ('LogisticPickList', 'PickListDataForTruckFormation')})
    result = {'ClosingState':[closing],
        'CalculationOutputs':[{'capability':n,'rows':v} for n,v in calculated.items()]}
    if pick_state is not None:
        from mta.serialization import digest
        result['_PickSourceDigests'] = {name: digest(rows) for name, rows in pick_sources.items()}
    if validating():
        result.update({'MasterValidation':[master],
        'SupplierStages':[{'stage':n,**v} for n,v in supplier.items()],
        'DailyStages':[{'stage':n,**v} for n,v in daily.items()],
        'ControlStages':snapshots(control),'OrderStages':snapshots(orders),'CalculationInput':[source],
        'CalculationOutputs':[{'capability':n,'rows':v} for n,v in calculated.items()],
        'CalculationRun':[{'run_id':calculation_id}], 'BPRStages':snapshots(bpr_stages),'DBMStages':snapshots(dbm_stages)})
    if delivery is not None:
        from mta.domain.btr_finalization import btr_stages
        for attr in closing['importer']['SkuLocAttributeData']:
            if attr['NonNMS'] is not None:
                attr['NonNMS'] = bool(attr['NonNMS'])
        btr_facts = {**deepcopy(prior['consumer_context']), **deepcopy(importer),
                     **deepcopy(final_dbm), 'vf_RationedReqReport': report,
                     'BPR_Table': late['BPR_Table'], 'MasterData': importer['MasterData']}
        if nms is not None:
            btr_facts['NMSAllItems'] = nms['NMSAllItems']
        # UpdateBRAge changes these three fields on the current Pick-based
        # expedite population. Reuse the accepted R1 Pick membership producer;
        # an opening/current-day prepared expedite result is never the input.
        pick_keys = {(r['sku_code'], r['location_code'], r['parent_location_code'])
                     for r in calculated['r1_ration_bifurcation']}
        btr_facts['ExpediteDispatches'] = [
            {'SKUCode': r['SKUCode'], 'WhCode': r['WhCode'],
             'BRAge': None, 'BRAgeRedCount': None, 'BRAgeBlackCount': None}
            for r in report for m in importer['MasterData']
            if (r['SKUCode'], r['WhCode'], r['ParentWhCode']) in pick_keys
            and (r['SKUCode'], r['WhCode']) == (m['SKUCode'], m['WhCode'])
            and r['WhCode'] != r['ParentWhCode'] and r['DispatchColor'] in ('Black', 'Red', 'Yellow')]
        trends = final_stage(btr_stages(today, prior['btr'], btr_facts, delivery['btr_settings']))
        completed_boundaries.append('btr-insights')
        # ExtendedOCP and Category share the Importer standard-attribute table.
        # Its final writer is BTR UpdateCategoryCol, after the DBM snapshot.
        final_dbm['SKULocStandardAttributes'] = deepcopy(trends[-1][1]['SKULocStandardAttributes'])
        closing['dbm'] = deepcopy(final_dbm)
        closing.update(control_aux=control_aux, btr=deepcopy(trends[-1][1]),
                       consumer_context=deepcopy(prior['consumer_context']),
                       publication_context=deepcopy(prior['publication_context']))
        if nms is not None:
            closing['consumer_context']['NMSAllItems'] = nms['NMSAllItems']
        stages = dict(dbm_stages)
        # Reports that overwrite the same legacy staging tables stay separate
        # consumer-visible families in the enclosing immutable run.
        reports = [{'stage': name, 'tables': {n: deepcopy(value[n]) for n in
                    ('ReportHeader', 'ReportRows', 'Norm0Norm1Norm2Report',
                     'Norm0_1_2ReportDetails', 'Norm1IncreaseSuggestions') if n in value}}
                   for name, value in dbm_stages if name in ('norm-change-export', 'norm-change-history',
                       'norm1-advisory') or name.startswith(('norm0-', 'norm1-', 'norm2-'))]
        reports.append({'stage': 'controls', 'tables': diagnostics})
        result.update(BPRFinal=[late], DBMFinal=[final_dbm], Reports=reports,
            BTRFinal=[trends[-1][1]],
            PublicationContext=[deepcopy(prior['publication_context'])], Lineage=[])
        if validating():
            result.update(BTRStages=snapshots(trends),
                MajorBoundaries=[{'boundary': n, 'state': v} for n, v in (
                ('controls', {'controls': control[-1][1], 'diagnostics': diagnostics}),
                ('final-bpr-bluezone', late), ('dbm-imported', stages['ingestion']),
                ('final-suspensions', stages['suspension26']),
                ('final-suggestions', stages['discard']), ('post-rule-reports', dbm_stages[-1][1]),
                ('btr-insights', trends[-1][1]), ('closing-state', closing))])
        else:
            result['_CompletedBoundaries']=[*completed_boundaries,'closing-state']
        if finalization is not None:
            if finalization['policy'] != daily_finalization.ACTIVE_POLICY:
                closing['importer_settings'] = daily_finalization.finish(
                    closing['complete'], closing['importer_settings'], today)
            from mta.serialization import digest
            result['_Cohort1'] = dict(policy=finalization['policy'], business_date=today,
                configuration_digest=digest(profile),
                qualification=daily_finalization.qualification(finalization['policy']),
                flag_digest=digest(closing['complete']['ScriptExecutedFlag']))
    if operational_input_tables is not None:
        result['_OperationalInputTables'] = operational_input_tables
    if force_alert_capture is not None:
        result['_OperationalForceSources'] = force_alert_capture
    return result
