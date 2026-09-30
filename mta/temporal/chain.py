"""Connected daily calculation with one owner for every persisted closing table.

External day facts are separate from state. The R1 calculation input below is
an internal projection of actual current producers, never an external answer.
"""

from copy import deepcopy

from decimal import Decimal

from datetime import date, datetime

import hashlib

import json

from mta.application.r1_importer_master import process_importer_master, PRIOR_TABLES

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

def calculation_source(today, opening_date, profile, importer, dbm_master, processed, sourcing, supplier_prior,
                       identity, phase_out=None):
    config=deepcopy(profile['calculation'])
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
    """execute_calculation runs the existing modern R1 producer and returns outputs/id."""
    today=day['business_date'];now=today+'T00:00:00'
    master_input,daily_input=entry_inputs(prior,opening_date,day,profile,identity)
    master=process_importer_master(master_input)
    if master['outcome']!='APPLIED':raise ValueError('Connected master producer did not apply')
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
    delivery = profile.get('delivery')
    control_aux = diagnostics = None
    if delivery is not None:
        controls['importer_settings'].extend(deepcopy(profile['daily']['settings']))
        from mta.application.timeline_controls import timeline_control_stages, EXTRA_TABLES
        from mta.domain.control_carry import TABLES as CONTROL_TABLES
        connected = list(timeline_control_stages(today, opening_date, controls,
            prior['control_aux'], day, {**delivery['controls'], 'force_flags': profile['force_flags']},
            daily_final['DailyDataProcessed'], importer['SkuLocAttributeData']))
        for _, state, _ in connected:
            delivery_control_types(state)
        control = [(name, state) for name, state, _ in connected]
        complete = connected[-1][1]
        control_final = {n: deepcopy(complete[n]) for n in CONTROL_TABLES}
        control_aux = {n: deepcopy(complete[n]) for n in EXTRA_TABLES}
        diagnostics = connected[-1][2]
    else:
        control=list(control_stages(today,opening_date,controls,profile['force_flags'],day['accepted_feed'],day['new_force_requests']))
        control_final=deepcopy(control[-1][1])
    importer['MasterData']=deepcopy(control_final['importer_master'])
    importer['ForceNormChange']=deepcopy(control_final['force_requests'])
    source=calculation_source(today,opening_date,profile,importer,control_final['dbm_master'],daily_final['DailyDataProcessed'],deepcopy(new_sourcing),deepcopy(old_sourcing),identity,control_final['phase_out'])
    prepared=prepare_r1_current_day(source)
    bpr_master=[{'SKUCode':r['sku_code'],'WHCode':r['location_code'],'Norm':r['norm'],
                 'ParentWhCode':r['parent_location_code'],'SKUIntroDate':r['sku_intro_date']} for r in prepared.master_state['bpr_master']]
    order_input={**deepcopy(prior['orders']),'BPRMaster':bpr_master,'DBMMaster':deepcopy(control_final['dbm_master']),
        'AdditionalMasterData':additional_native(prepared,importer),'LastBatchRunTbl':[{'LastRunDate':opening_date+'T00:00:00'}],
        'PSOData':[],'IntermediateTables':deepcopy(control_final['IntermediateTables'])}
    orders=list(order_stages(today,opening_date,order_input,day['order_feed_status'],day['order_feed']))
    for r in orders[-1][1]['SpikeOrderData']:
        source['orders'].append({'order_id':r['CustomerOrderId'],'sku_code':r['SKUCode'],'location_code':r['WhCode'],
            'outstanding_quantity':r['Qty'],'accepted_on':r['IntroDate'],'customer_expected_date':r['CustomerExpectedDate'],
            'established_is_spike':r['IsSpike'],'established_due_date':r['DueDate'],
            'first_servicing_location_code':r['FirstServicingWhCode'],'established_order_key':r['OrderKey']})
    calculated,calculation_id=execute_calculation(source)
    from mta.application.r1_rationed_report import rationed_report
    report=rationed_report(source,calculated,
        [{'sku_code':r['SKUCode'],'description':r['SKUDescription']} for r in importer['SKUDescriptionTbl']],
        [{'location_code':r['WHCode'],'description':r['WHDescription']} for r in importer['SiteDescriptionTbl']])
    early_daily=generated_bpr_daily_state({'raw_master_entry':{'business_date':today},'raw_daily_entry':daily_input},daily)
    constructor={'BPRMaster':bpr_master,'BPRDailyConsumption':early_daily,
        'RequirementBlue':[{'SKUCode':r['sku_code'],'WhCode':r['location_code'],'BlueReq':int(Decimal(r['virtual_norm']['blue_requirement']))} for r in calculated['r1_requirement']],
        **{n:deepcopy(importer[n]) for n in ('SKUDescriptionTbl','SiteDescriptionTbl','SkuLocAttributeData')},
        'ColorSequence':[{'Color':c,'SequenceNo':i} for i,c in enumerate(('Black','Red','Yellow','Green','Blue','White','Grey'),1)],
        'PhaseInTbl':control_final['phase_in'],'PhaseOutTbl':control_final['phase_out'],'LastBatchRunTbl':[{'LastRunDate':now}],
        'DailyDataForBPR':[],'PenetrationAndColor':[],'BPRExceptions':[],'BPR_Table':[],
        'IntermediateTables':deepcopy(control_final['IntermediateTables'])}
    bpr_stages,late=constructor_then_late(today,constructor,report)
    bpr_stages.append(('UpdateBPR.sql',{**late,'vf_RationedReqReport':report}))
    dbm=deepcopy(prior['dbm'])
    # ImportMasterDataComponents.bat runs the deployed Importer initializer on
    # every day before DBM/BTR. Its TRUNCATE plus distinct two-key INSERT
    # discards all prior standard-attribute values.
    dbm['SKULocStandardAttributes'] = initialise_sku_loc_standard_attributes(importer)
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
    dbm_stages=list(selected_stages(
        today, dbm, facts, None if delivery is None else delivery['batch'], report_exceptions))
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
    result = {'ClosingState':[closing],'MasterValidation':[master],
        'SupplierStages':[{'stage':n,**v} for n,v in supplier.items()],
        'DailyStages':[{'stage':n,**v} for n,v in daily.items()],
        'ControlStages':snapshots(control),'OrderStages':snapshots(orders),'CalculationInput':[source],
        'CalculationOutputs':[{'capability':n,'rows':v} for n,v in calculated.items()],
        'CalculationRun':[{'run_id':calculation_id}], 'BPRStages':snapshots(bpr_stages),'DBMStages':snapshots(dbm_stages)}
    if delivery is not None:
        from mta.domain.btr_finalization import btr_stages
        for attr in closing['importer']['SkuLocAttributeData']:
            if attr['NonNMS'] is not None:
                attr['NonNMS'] = bool(attr['NonNMS'])
        btr_facts = {**deepcopy(prior['consumer_context']), **deepcopy(importer),
                     **deepcopy(final_dbm), 'vf_RationedReqReport': report,
                     'BPR_Table': late['BPR_Table'], 'MasterData': importer['MasterData']}
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
        trends = list(btr_stages(today, prior['btr'], btr_facts, delivery['btr_settings']))
        # ExtendedOCP and Category share the Importer standard-attribute table.
        # Its final writer is BTR UpdateCategoryCol, after the DBM snapshot.
        final_dbm['SKULocStandardAttributes'] = deepcopy(trends[-1][1]['SKULocStandardAttributes'])
        closing['dbm'] = deepcopy(final_dbm)
        closing.update(control_aux=control_aux, btr=deepcopy(trends[-1][1]),
                       consumer_context=deepcopy(prior['consumer_context']),
                       publication_context=deepcopy(prior['publication_context']))
        stages = dict(dbm_stages)
        # Reports that overwrite the same legacy staging tables stay separate
        # consumer-visible families in the enclosing immutable run.
        reports = [{'stage': name, 'tables': {n: deepcopy(value[n]) for n in
                    ('ReportHeader', 'ReportRows', 'Norm0Norm1Norm2Report',
                     'Norm0_1_2ReportDetails', 'Norm1IncreaseSuggestions') if n in value}}
                   for name, value in dbm_stages if name in ('norm-change-export', 'norm-change-history',
                       'norm1-advisory') or name.startswith(('norm0-', 'norm1-', 'norm2-'))]
        reports.append({'stage': 'controls', 'tables': diagnostics})
        result.update(BPRFinal=[deepcopy(late)], DBMFinal=[deepcopy(final_dbm)], Reports=reports,
            BTRFinal=[deepcopy(trends[-1][1])], BTRStages=snapshots(trends),
            PublicationContext=[deepcopy(prior['publication_context'])], Lineage=[],
            MajorBoundaries=[{'boundary': n, 'state': v} for n, v in (
                ('controls', {'controls': control[-1][1], 'diagnostics': diagnostics}),
                ('final-bpr-bluezone', late), ('dbm-imported', stages['ingestion']),
                ('final-suspensions', stages['suspension26']),
                ('final-suggestions', stages['discard']), ('post-rule-reports', dbm_stages[-1][1]),
                ('btr-insights', trends[-1][1]), ('closing-state', closing))])
    return json_value(result)
