"""Connected daily calculation with one owner for every persisted closing table.

External day facts are separate from state. The R1 calculation input below is
an internal projection of actual current producers, never an external answer.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.
"""

from copy import deepcopy
from dataclasses import replace
from mta.temporal.day_phases import DayContext, PreparedDay, ReadyBprDay, BprDay, DbmDay
from mta.application import accepted_inputs
from mta.serialization import digest
from mta.application.stage_observation import operation, stage, summary

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

from mta.application.r1_input import (_prepare_r1_operation_context, calculation_order_rows,
    _ready_r1_for_owned_orders)

from mta.domain.control_carry import control_stages

from mta.domain.order_closing import order_stages

from mta.domain.bpr_construction import constructor_then_late

from mta.domain.dbm_selected_chain import selected_stages
from mta.domain.dbm_norm012 import NORM0_EXPORT_STAGES
from mta.runtime.dbm_phase_storage import STAGES as PHASE_STAGES, POPULATION as PHASE_POPULATION


def _observe_dbm(state, point, name=None):
    """Bounded owner/representation observations; never consume a row factory."""
    try:
        from pathlib import Path
        populations={table:{'rows':len(state[table]),'representation':type(state[table]).__name__}
            for table in ('DBMMaster','SKULocStandardAttributes','DailyConsumption','SuspendHistory',
                'OrderDataSummary','SuspendStockType','SuspendConsumptionType','SuspendOrderType',
                'Suggestions','NormChangeLogTbl') if table in state}
        memory={}
        try:
            line=next(line for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('VmRSS:'))
            memory['rss_bytes']=int(line.split()[1])*1024
        except (OSError,ValueError,StopIteration):pass
        for field in ('current','peak'):
            try:memory['cgroup_'+field+'_bytes']=int(Path('/sys/fs/cgroup/memory.'+field).read_text())
            except (OSError,ValueError):pass
        try:
            events=dict(line.split() for line in Path('/sys/fs/cgroup/memory.events').read_text().splitlines())
            memory.update({'cgroup_'+field:int(events[field]) for field in ('max','oom','oom_kill')})
        except (OSError,ValueError,KeyError):pass
        summary('dbm_ownership',point=point,name=name,populations=populations,**memory)
    except Exception:
        pass


def connected_dbm_stages(today, state, facts, delivery, report_exceptions=None):
    """Daily dispatch consumes the explicitly typed Importer settings owner."""
    from mta.application.native_output_contracts import validate_dbm_writer,producing_native
    stages=selected_stages(today, state, facts,
        None if delivery is None else delivery['batch'], report_exceptions,
        _owned=True, _defer_exports=producing_native(),
        conditional_settings=None if delivery is None else
            delivery.get('conditional_dbm', {}).get('importer_vf_settings'))
    stopped=object();ordinal=0;previous=None
    while True:
        # End each observation before yielding to the report/snapshot consumer.
        with stage('dbm_dispatch',ordinal=ordinal,after=previous):
            item=next(stages,stopped)
            if item is not stopped:
                name,current=item
                if producing_native():validate_dbm_writer(current,name)
        if item is stopped:return
        if producing_native():_observe_dbm(current,'stage_ready',name)
        ordinal+=1;previous=name
        yield name,current


def connected_btr_stages(today, prior, facts, delivery, *, bpr_daily, supplier_dispatch_req):
    """History uses actual BPR owners; DBM daily history is a different population."""
    from mta.domain.btr_finalization import btr_stages
    settings=delivery['btr_settings']
    owner=delivery.get('btr_history',{}).get('importer_vf_settings')
    current={**facts,'LastBatchRunTbl':[{'LastRunDate':today+'T00:00:00'}],
             'BPRDailyConsumption':bpr_daily,'SupplierDispatchReq':supplier_dispatch_req}
    from mta.application.native_output_contracts import CurrentGenerations,BTR_CURRENT,validate_rows,producing_native
    generations=CurrentGenerations(BTR_CURRENT,'BTR',prior)
    for name,produced in btr_stages(today,prior,current,settings,importer_vf_settings=owner,_owned=True,
            _reporting=not producing_native()):
        if producing_native():generations.validate(produced,'btr/'+name)
        if producing_native() and name=='UpdateBRAge.sql':
            validate_rows(produced['ExpediteDispatches'],'BPR/ExpediteDispatches',
                fields=('SKUCode','WhCode','BRAge','BRAgeRedCount','BRAgeBlackCount'),stage='btr/'+name)
        if producing_native() and name=='UpdateCategoryCol.sql':
            validate_rows(produced['SKULocStandardAttributes'],'Importer/SKULocStandardAttributes',stage='btr/'+name)
        yield name,produced


def retain_dbm_stages(selected,completed_boundaries):
    """Retain each report before staging tables clear; never key by norm alone."""
    required_reports=('norm-change-export','norm-change-history','norm1-advisory',
                      *NORM0_EXPORT_STAGES.values(),'norm1-export','norm2-export',*PHASE_STAGES)
    tables=('ReportHeader','ReportRows','Norm0Norm1Norm2Report',
            'Norm0_1_2ReportDetails','Norm1IncreaseSuggestions')
    stages=[];last=None
    for name,current in selected:
        last=(name,current)
        boundary={'ingestion':'dbm-imported','suspension26':'final-suspensions',
                  'discard':'final-suggestions','daily-cleanup':'post-rule-reports'}.get(name)
        if boundary:completed_boundaries.append(boundary)
        if name in required_reports:
            selected_tables = (PHASE_POPULATION,) if name in PHASE_STAGES else tables
            captured={n:deepcopy(current[n]) for n in selected_tables if n in current}
            if current.get('_DeferredExport') and (name in ('norm-change-export','norm-change-history') or name.startswith(('norm0-','norm1-','norm2-')) and name.endswith('-export')):
                from mta.domain.deferred_dbm_exports import SOURCES
                marker=current['_DeferredExport']
                captured['_DeferredExport']=deepcopy(marker)
                export_sources=current.get('_OccurrenceExportSources',current)
                captured['_ReportSourceFacts']={n:deepcopy(export_sources[n]) for n in SOURCES[marker['kind']]}
            stages.append((name,captured))
    if last is None:raise ValueError('Connected DBM stages required')
    stages.append(last)
    return stages


def dbm_report_images(stages):
    """Capture each phase horizon before overwrite, in actual dispatch order."""
    reports=[]
    for name,value in stages:
        if name in PHASE_STAGES:
            tables=(PHASE_POPULATION,)
        elif name in ('norm-change-export','norm-change-history','norm1-advisory') or name.startswith(('norm0-', 'norm1-', 'norm2-')):
            tables=('ReportHeader','ReportRows','Norm0Norm1Norm2Report','Norm0_1_2ReportDetails','Norm1IncreaseSuggestions')
        else:
            continue
        report={'stage':name,'tables':{n:deepcopy(value[n]) for n in tables if n in value}}
        if value.get('_DeferredExport'):
            report.update(deferred=deepcopy(value['_DeferredExport']),sources=value['_ReportSourceFacts'])
        reports.append(report)
    return reports

CAPABILITY='r2_calculation_timeline'


SHARED_CONTROLS={'dbm_master':'DBMMaster','suggestions':'Suggestions','reason_codes':'ReasonCodes',
    'acceptance':'NormAcceptanceTbl','phase_out':'PhaseOutTbl','phase_in':'PhaseInTbl','seasonality':'Seasonality',
    'forced':'ForcedNormChangeTbl','log':'NormChangeLogTbl','suggestions_log':'SuggestionsLog',
    'order_summary':'OrderDataSummary','suspend_order_type':'SuspendOrderType','dbm_settings':'DBMSettingsTbl'}


def carry_dbm_controls(controls, dbm):
    """Shared controls always come from this run's own DBM closing owner."""
    result = deepcopy(controls)
    for target, source in SHARED_CONTROLS.items():
        result[target] = control_rows(dbm[source])
    return result

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
    if not isinstance(fields,(tuple,list)) or not fields or len(set(fields))!=len(fields):
        raise ValueError('Explicit unique native control field roster required')
    result=[]
    for ordinal,row in enumerate(rows):
        if 'WHCode' in row and 'WhCode' in row and row['WHCode'] != row['WhCode']:
            raise ValueError('Conflicting native WHCode/WhCode aliases at occurrence '+str(ordinal))
        projected={}
        for field in fields:
            if field in row:projected[field]=row[field]
            elif field=='WHCode' and 'WhCode' in row:projected[field]=row['WhCode']
            else:raise ValueError('Missing native control field '+field+' at occurrence '+str(ordinal))
        result.append(projected)
    return result

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

def entry_inputs(prior, opening_date, day, profile, identity, *, _include_master=True):
    today=day['business_date']
    master=None
    if _include_master:
        master={'schema':'r1-importer-master-input-v1','business_date':today,'run_timestamp':today+'T00:00:00',
            'import_non_nms':profile['import_non_nms'],'settings':[
                {'Parameter':r['Parameter'],'Value':int(r['Value'])} for r in prior['importer_settings']
                if r['Parameter'] in ('NMSActive','DBMActive','UpdatePWh_RLT_RCP_GCP')],
            'prior_provenance':{'kind':'SYNTHETIC_PRIOR_IMPORTER','identity':identity,'business_date':opening_date},
            'prior':deepcopy(prior['importer']), 'raw_master':day['raw_master'],
            'raw_non_nms':day['raw_non_nms'],'raw_no_norm':day['raw_no_norm']}
        # SQL BIT values retain booleans in closing state; the established importer
        # typed input contract represents BIT as0/1. This is a declared type adapter.
        from mta.row_sequences import RecordRows
        def bit_row(row):
            return {key:int(value) if type(value) is bool else deepcopy(value)
                    for key,value in row.items()}
        for name,rows in master['prior'].items():
            if isinstance(rows,RecordRows):
                # deepcopy deliberately shares immutable generations. Adapt
                # values in a new lazy generation, never in the sealed source.
                master['prior'][name]=RecordRows(len(rows),
                    lambda rows=rows:(bit_row(row) for row in rows),
                    getitem=lambda ordinal,rows=rows:bit_row(rows[ordinal]))
            else:
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
    from mta.row_sequences import RecordRows
    result = {name:([] if name == 'items' else
                    [deepcopy(row) for row in value] if isinstance(value,RecordRows) else deepcopy(value))
              for name, value in logistics.items()}
    for item in logistics['items']:
        for sku in skus.get(_sql_key(item['sku_code']), []):
            if sku['Weight'] is None and sku['Volume'] is None:
                continue
            for location in locations.get(_sql_key(item['to_location']), []):
                result['items'].append({**deepcopy(item), 'weight': sku['Weight'],
                    'volume': sku['Volume'], 'logistics_location': location['LogisticsLocation']})
    return result


def _calculation_source_values(today, opening_date, profile, importer, dbm_master, processed, sourcing, supplier_prior,
                               identity, phase_out=None):
    from mta.row_sequences import RecordRows
    config={}
    for name,value in profile['calculation'].items():
        if name=='logistics':
            config[name]=producer_owned_logistics(value,importer)
        elif name in ('skus','locations','replenishment_exclusions') and isinstance(value,RecordRows):
            # These current configuration arrays enter the existing list-based
            # R1/JSON contract. They are not opening/history populations.
            config[name]=[deepcopy(row) for row in value]
        else:
            config[name]=deepcopy(value)
    attrs={(r['SKUCode'],r['LocCode']):r for r in importer['SkuLocAttributeData']}
    skus={r['SKUCode']:r for r in importer['SkuAttributeData']}
    project=lambda rows:[{f:r[s] for f,s in MASTER_SOURCE_MAP.items()} for r in rows]
    masters=project(importer['MasterData'])
    active={(r['sku_code'],r['location_code']) for r in masters}
    for name in ('stock_openings','policies'):
        rows=config[name]
        # Persisted populations share immutable generations through deepcopy.
        # Only these filtered current-day transform rows need mutable ownership.
        config[name]=[deepcopy(r) if isinstance(rows,RecordRows) else r for r in rows
                      if (r['sku_code'],r['location_code']) in active]
    for r in masters:
        a=attrs[r['sku_code'],r['location_code']]
        r.update(pack_size=a['PackSize'],elephant_order_capping=skus[r['sku_code']]['ElephantOrderCapping'])
    processed_by_key = {}
    for p in processed:
        processed_by_key.setdefault((p['SKUCode'], p['WhCode'], p['ReportDate']), []).append(p)
    positions=[]
    for r in masters:
        matches=processed_by_key.get((r['sku_code'],r['location_code'],today), ())
        if len(matches)!=1 or matches[0]['Stock'] is None:
            from mta.application.stage_observation import stock_rejection
            stock_rejection(sku_code=r['sku_code'], location_code=r['location_code'],
                business_date=today, match_count=len(matches), identity=identity,
                reason='missing' if not matches else 'duplicate' if len(matches)!=1 else 'null')
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
    return result


def calculation_source(today, opening_date, profile, importer, dbm_master, processed, sourcing, supplier_prior,
                       identity, phase_out=None):
    result=_calculation_source_values(today,opening_date,profile,importer,dbm_master,processed,
        sourcing,supplier_prior,identity,phase_out)
    # Only this post-control source enters the calculation/identity contract.
    # The earlier master-refresh projection is validated by its own producer
    # and never publishes or consumes this derived checksum.
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
                  report_exceptions=None, *, native_daily=False, prepared_master=None, master_snapshot=None):
    # Native producers retain only their required business outputs/captures.
    from mta.application.native_output_contracts import native_assignments
    with operation(identity), stage('daily_calculation'), native_assignments(native_daily):
        result = _calculate_day_native(prior, opening_date, day, profile, identity,
                                       execute_calculation, report_exceptions,
                                       **({'native_daily':True} if native_daily else {}),
                                       **({'prepared_master':prepared_master} if prepared_master is not None else {}),
                                       **({'master_snapshot':master_snapshot} if master_snapshot is not None else {}))
    return result


def _calculate_day_native(prior, opening_date, day, profile, identity, execute_calculation,
                          report_exceptions=None, *, native_daily=False, prepared_master=None, master_snapshot=None):
    """Run the same four ordered producers and return the unchanged full result."""
    phase = prepare_day(prior, opening_date, day, profile, identity, execute_calculation,
                        report_exceptions, native_daily=native_daily,
                        prepared_master=prepared_master, master_snapshot=master_snapshot)
    phase = produce_bpr(phase)
    phase = produce_dbm(phase)
    return produce_btr(phase)


def prepare_day(prior, opening_date, day, profile, identity, execute_calculation,
                          report_exceptions=None, *, native_daily=False, prepared_master=None, master_snapshot=None):
    """PRE_BPR: prepare owned inputs and finish controls before any R1 calculation."""
    today=day['business_date'];now=today+'T00:00:00'
    from mta.application.occurrence_text_policy import KEY, require_binding
    occurrence_policy=(report_exceptions or {}).get(KEY)
    if occurrence_policy is not None:
        require_binding(occurrence_policy)
        owner=occurrence_policy['owner']
        if (owner['run_id']!=str(identity) or owner['business_date']!=today
                or owner['configuration_digest']!=digest(profile)):
            raise ValueError('Occurrence policy prepared run/profile/date differs')
    from mta.application import daily_finalization
    from mta.temporal.entry_preparation import prepare
    with stage('entry_preparation'):
        entry=prepare(prior,opening_date,day,profile,identity,prepared_master=prepared_master)
    prior,day=entry['prior'],entry['day']
    finalization,completion=entry['finalization'],entry['completion']
    master,daily_input=entry['master'],entry['daily_input']
    supplier_final,daily,daily_final=entry['supplier_final'],entry['daily'],entry['daily_final']
    importer=deepcopy(master['tables'])
    importer['SiteDescriptionTbl']=deepcopy(supplier_final['SiteDescriptionTbl'])
    importer['RejectedMaster']=deepcopy(daily_final['RejectedMaster'])
    with stage('control_processing'):
        supplier_state,old_sourcing,new_sourcing=supplier_calculation_state(prior['supplier'],supplier_final,importer['MasterData'],vendor_codes=profile['daily']['vendor_codes'])
        source=_calculation_source_values(today,opening_date,profile,importer,prior['dbm']['DBMMaster'],daily_final['DailyDataProcessed'],new_sourcing,old_sourcing,identity)
        refreshed=reconcile_master_state(source)
        controls=deepcopy(prior['controls'])
        controls['IntermediateTables']=scratch_tables(controls['IntermediateTables'])
        controls=carry_dbm_controls(controls, prior['dbm'])
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
            for _, complete, diagnostics in timeline_control_stages(today, opening_date, controls,
                    prior['control_aux'], day, {**delivery['controls'], 'force_flags': profile['force_flags']},
                    daily_final['DailyDataProcessed'], importer['SkuLocAttributeData'],
                    force_alert_capture=force_alert_capture):
                pass
            delivery_control_types(complete)
            if completion is not None:
                # All ordered control statements finish before completion is marked.
                daily_finalization.mark(completion, 'UpdateNormChanges.sql')
            control_final = {n: deepcopy(complete[n]) for n in CONTROL_TABLES}
            control_aux = {n: deepcopy(complete[n]) for n in EXTRA_TABLES}
        else:
            for _, control_state in control_stages(today,opening_date,controls,profile['force_flags'],day['accepted_feed'],day['new_force_requests']):
                pass
            control_final=deepcopy(control_state)
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
    context = DayContext(
        prior=prior,
        day=day,
        opening_date=opening_date,
        profile=profile,
        identity=identity,
        execute_calculation=execute_calculation,
        report_exceptions=report_exceptions,
        native_daily=native_daily,
        master_snapshot=master_snapshot,
        today=today,
        now=now,
        finalization=finalization,
        completion=completion,
        master=master,
        master_reused=entry['reused'], master_work=entry['master_work'])
    return PreparedDay(
        context=context,
        importer=importer,
        control_final=control_final,
        control_aux=control_aux,
        diagnostics=diagnostics,
        force_alert_capture=force_alert_capture,
        completed_boundaries=completed_boundaries,
        nms=nms,
        delivery=delivery,
        daily_input=daily_input,
        supplier_final=supplier_final,
        daily=daily,
        daily_final=daily_final,
        old_sourcing=old_sourcing,
        new_sourcing=new_sourcing,
        standard_attributes=standard_attributes,
        supplier_sob=supplier_state['refreshed_sob'],
        supplier_moq=supplier_state['refreshed_moq'])


def prepare_bpr_inputs(phase: PreparedDay) -> ReadyBprDay:
    """Produce the owned BPR inputs once, before requirements/rationing/Pick."""
    if type(phase) is not PreparedDay:
        raise ValueError('BPR input preparation requires its prepared day owner')
    from mta.application import daily_finalization
    context = phase.context
    prior = context.prior
    day = context.day
    opening_date = context.opening_date
    profile = context.profile
    identity = context.identity
    today = context.today
    completion = context.completion
    importer = phase.importer
    control_final = phase.control_final
    daily_final = phase.daily_final
    old_sourcing = phase.old_sourcing
    new_sourcing = phase.new_sourcing
    with stage('bpr_input_preparation'):
        with stage('r1_source_context_preparation'):
            source=calculation_source(today,opening_date,profile,importer,control_final['dbm_master'],daily_final['DailyDataProcessed'],deepcopy(new_sourcing),deepcopy(old_sourcing),identity,control_final['phase_out'])
            if 'requirement_stock' in day:
                from mta.application.requirement_stock import apply as apply_requirement_stock
                apply_requirement_stock(source,day['requirement_stock'],today)
            r1_context=_prepare_r1_operation_context(source)
        prepared=r1_context.prepared
        bpr_master=[{'SKUCode':r['sku_code'],'WHCode':r['location_code'],'Norm':r['norm'],
                     'ParentWhCode':r['parent_location_code'],'SKUIntroDate':r['sku_intro_date']} for r in prepared.master_state['bpr_master']]
        order_input={**deepcopy(prior['orders']),'BPRMaster':bpr_master,'DBMMaster':deepcopy(control_final['dbm_master']),
            'AdditionalMasterData':additional_native(prepared,importer),'LastBatchRunTbl':[{'LastRunDate':opening_date+'T00:00:00'}],
            'PSOData':[],'IntermediateTables':deepcopy(control_final['IntermediateTables'])}
        from mta.row_sequences import RecordRows
        # The existing order producer owns mutable current orders and feed rows;
        # keep its list contract without materializing unrelated prior history.
        if isinstance(order_input['SpikeOrderData'],RecordRows):
            order_input['SpikeOrderData']=[deepcopy(row) for row in order_input['SpikeOrderData']]
        order_feed=day['order_feed']
        if isinstance(order_feed,RecordRows):
            order_feed=[deepcopy(row) for row in order_feed]
        with stage('r1_order_reconciliation'):
            for _, order_state in order_stages(today,opening_date,order_input,day['order_feed_status'],order_feed):
                pass
        if completion is not None:
            daily_finalization.mark(completion, 'ImportSpikeOrders.sql', 'CalculateDD.sql')
        source['orders'].extend(calculation_order_rows(order_state))
        ready = _ready_r1_for_owned_orders(r1_context, source, order_state)
        auxiliary = None
        if context.native_daily:
            from mta.application.r1_daily_entry import native_auxiliary_stock_balances
            if phase.daily_consumption is None:
                phase.daily_consumption = generated_bpr_daily_state(
                    {'raw_master_entry': {'business_date': today},
                     'raw_daily_entry': phase.daily_input}, phase.daily)
            auxiliary = native_auxiliary_stock_balances(phase.daily_consumption,
                ready.prepared.stock_balances, importer['SkuLocAttributeData'], today,
                source['stock_configuration']['reservation_type'])
        from mta.application.r1_calculation import _prepare_r1_track_a, _OwnedTrackAInputs
        prepared_r1 = replace(ready.prepared,
            _track_a_preparation=_OwnedTrackAInputs(_prepare_r1_track_a(ready.prepared)))
        ready = replace(ready, prepared=prepared_r1, auxiliary_stock=auxiliary)
        if context.native_daily:
            from mta.application.persistent_master import qualify
            # The NMS snapshot and static settings are already produced at
            # intake. Qualify this representation there, before calculation;
            # final publication consumes the result without comparing it again.
            consumer = dict(prior['consumer_context'])
            if phase.nms is not None:
                consumer['NMSAllItems'] = phase.nms['NMSAllItems']
            context.master_qualified = (True if context.master_reused else qualify(
                context.master, profile, day,
                dict(importer_settings=prior['importer_settings'], consumer_context=consumer),
                snapshot=context.master_snapshot))
    return ReadyBprDay(phase=phase, source=source, bpr_master=bpr_master,
        order_state=order_state, r1=ready)


def produce_bpr(phase: PreparedDay | ReadyBprDay) -> BprDay:
    ready = phase if type(phase) is ReadyBprDay else prepare_bpr_inputs(phase)
    accepted_inputs._complete(ready.context)
    with accepted_inputs.consume(ready.context):
        return _produce_bpr(ready)


def _produce_bpr(phase: ReadyBprDay) -> BprDay:
    """Consume prepared BPR inputs and run the unchanged calculation tail."""
    ready = phase if type(phase) is ReadyBprDay else prepare_bpr_inputs(phase)
    phase = ready.phase
    context = phase.context
    prior, day, profile = context.prior, context.day, context.profile
    today, now = context.today, context.now
    execute_calculation = context.execute_calculation
    native_daily = context.native_daily
    finalization, completion = context.finalization, context.completion
    importer, control_final = phase.importer, phase.control_final
    completed_boundaries = phase.completed_boundaries
    daily_input, daily = phase.daily_input, phase.daily
    supplier_final = phase.supplier_final
    daily_final = phase.daily_final
    standard_attributes = phase.standard_attributes
    source, bpr_master, order_state = ready.source, ready.bpr_master, ready.order_state
    pick_sources = None
    from mta.application import daily_finalization
    with stage('r1_orders_requirements_rationing'):
        native_stock = {}
        if 'production_report_policy' in day:
            native_stock['_production_sources'] = True
        if native_daily:
            native_stock['_owned_daily_stock'] = dict(daily_consumption=generated_bpr_daily_state(
                {'raw_master_entry':{'business_date':today},'raw_daily_entry':daily_input},daily)
                if phase.daily_consumption is None else phase.daily_consumption,
                attributes=importer['SkuLocAttributeData'])
        calculated,calculation_id=execute_calculation(source, _owned_order_closing=order_state,
            _owned_r1_ready=ready.r1, **native_stock)
    if completion is not None:
        daily_finalization.mark(completion, *daily_finalization.CALCULATION_SCRIPTS)
    from mta.application.r1_rationed_report import rationed_report
    with stage('r1_rationed_report'):
        report=rationed_report(source,calculated,
            [{'sku_code':r['SKUCode'],'description':r['SKUDescription']} for r in importer['SKUDescriptionTbl']],
            [{'location_code':r['WHCode'],'description':r['WHDescription']} for r in importer['SiteDescriptionTbl']])
    if 'production_report_policy' in day:
        from mta.application.production_order_sources import produce as produce_order_sources
        with stage('r1_native_order_source'):
            calculated['r1_allocated_orders'] = produce_order_sources(today=today, calculated=calculated,
                orders=order_state['SpikeOrderData'], dbm_master=control_final['dbm_master'],
                attributes=importer['SkuLocAttributeData'], daily_consumption=native_stock['_owned_daily_stock']['daily_consumption'])
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
        with stage('pick'):
            pick_state = calculate_native_pick(**pick_sources)
        calculated['r1_pick_list'] = [r for r in pick_state['allocations'] if r['truck'] is not None]
        calculated['r1_pick_remaining'] = [r for r in pick_state['allocations'] if r['truck'] is None]
        if completion is not None:
            daily_finalization.mark(completion, 'GenerateLogisticPickList.sql')
    with stage('remaining_bpr'):
        early_daily=(generated_bpr_daily_state({'raw_master_entry':{'business_date':today},'raw_daily_entry':daily_input},daily)
                     if phase.daily_consumption is None else phase.daily_consumption)
        constructor={'BPRMaster':bpr_master,'BPRDailyConsumption':early_daily,
            'RequirementBlue':[{'SKUCode':r['sku_code'],'WhCode':r['location_code'],'BlueReq':int(Decimal(r['virtual_norm']['blue_requirement']))} for r in calculated['r1_requirement']],
            **{n:deepcopy(importer[n]) for n in ('SKUDescriptionTbl','SiteDescriptionTbl','SkuLocAttributeData')},
            'ColorSequence':[{'Color':c,'SequenceNo':i} for i,c in enumerate(('Black','Red','Yellow','Green','Blue','White','Grey'),1)],
            'PhaseInTbl':control_final['phase_in'],'PhaseOutTbl':control_final['phase_out'],'LastBatchRunTbl':[{'LastRunDate':now}],
            'DailyDataForBPR':[],'PenetrationAndColor':[],'BPRExceptions':[],'BPR_Table':[],
            'IntermediateTables':deepcopy(control_final['IntermediateTables'])}
        _,late=constructor_then_late(today,constructor,report)
        completed_boundaries.append('final-bpr-bluezone')
        if completion is not None:
            daily_finalization.mark(completion, '01. ImportData.sql', 'CollectDataForBPR.sql',
                'CalculatePenetrationAndColor.sql', 'GenerateBPR.sql', 'UpdateBPR.sql')
    complete = None
    if finalization is not None:
        complete, retained_daily = daily_finalization.production_and_retention(
            complete=prior['complete'], source=source, calculated=calculated,
            bpr_master=bpr_master, importer=importer, plants=prior['bpr']['Plants'],
            report=report, late=late, today=today, config=finalization,_owned=True)
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
    return BprDay(
        context=context,
        importer=phase.importer,
        control_final=phase.control_final,
        control_aux=phase.control_aux,
        diagnostics=phase.diagnostics,
        force_alert_capture=phase.force_alert_capture,
        completed_boundaries=phase.completed_boundaries,
        nms=phase.nms,
        delivery=phase.delivery,
        supplier_sob=phase.supplier_sob,
        supplier_moq=phase.supplier_moq,
        daily_final=daily_final,
        standard_attributes=standard_attributes,
        bpr_master=bpr_master,
        order_state=order_state,
        calculated=calculated,
        report=report,
        late=late,
        complete=complete,
        operational_input_tables=operational_input_tables,
        pick_state=pick_state,
        pick_sources=pick_sources,
    )


def dbm_action_state(phase: BprDay):
    """The four exact pre-DBM command inputs, after already accepted controls."""
    from mta.application.native_output_contracts import control_fields
    result={'NormsInSleepModeTbl':deepcopy(phase.context.prior['dbm']['NormsInSleepModeTbl'])}
    for name,table in (('dbm_master','DBMMaster'),('suggestions','Suggestions'),
                       ('acceptance','NormAcceptanceTbl')):
        result[table]=native_rows(phase.control_final[name],EMPTY_NATIVE_FIELDS.get(table) or control_fields(table))
    return result


@accepted_inputs.phase
def produce_dbm(phase: BprDay, *, _action_state=None, _action_revision=0) -> DbmDay:
    """Run the unchanged DBM chain and carry its controls, before BTR."""
    context = phase.context
    prior = context.prior
    day = context.day
    profile = context.profile
    report_exceptions = context.report_exceptions
    today = context.today
    now = context.now
    finalization = context.finalization
    importer = phase.importer
    control_final = phase.control_final
    completed_boundaries = phase.completed_boundaries
    delivery = phase.delivery
    daily_final = phase.daily_final
    standard_attributes = phase.standard_attributes
    late = phase.late
    reports = None
    from mta.application.native_output_contracts import producing_native
    if producing_native():_observe_dbm(prior['dbm'],'assembly_input')
    # These generations are replaced below before a DBM consumer can see them.
    # Retain the original mapping order after assembly without copying discarded
    # metadata/current-control rows or changing the prior snapshot.
    replaced = {'SKULocStandardAttributes', 'SKUDescriptionTbl', 'SiteDescriptionTbl',
                'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData',
                'LastBatchRunTbl', *SHARED_CONTROLS.values()}
    dbm = {name:deepcopy(rows) for name, rows in prior['dbm'].items() if name not in replaced}
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
        from mta.application.native_output_contracts import control_fields,validate_rows
        fields=EMPTY_NATIVE_FIELDS.get(src) or control_fields(src)
        dbm[src]=native_rows(control_final[n],fields)
        if src not in ('NormChangeLogTbl','SuggestionsLog'):
            validate_rows(dbm[src],'DBM/'+src,fields=fields,stage='controls/'+src)
    if _action_state is not None:
        from mta.serialization import storage
        if (type(_action_revision) is not int or _action_revision<=0
                or set(_action_state)!=set(dbm_action_state(phase))
                or storage(_action_state['DBMMaster'])!=storage(dbm['DBMMaster'])):
            raise ValueError('Scoped DBM action revision/master differs')
        for name in ('NormAcceptanceTbl','NormsInSleepModeTbl','Suggestions'):
            dbm[name]=deepcopy(_action_state[name])
    elif _action_revision!=0:
        raise ValueError('Scoped DBM action revision requires its exact state')
    dbm['LastBatchRunTbl']=[{'LastRunDate':now}]
    dbm = {**{name:dbm[name] for name in prior['dbm']}, **dbm}
    facts={n:deepcopy(day[n]) for n in ('order_raw','exclusions','distributor_transactions','vendor_transactions')}
    facts.update(daily_raw=deepcopy(daily_final['DailyDataRaw']),bpr_daily=deepcopy(late['BPRDailyConsumption']))
    from mta.row_sequences import RecordRows
    # Suspension stages update these CURRENT flags in place. Their persisted
    # input generation stays immutable; histories remain shared/streamed.
    for name in ('SuspendStockType','SuspendConsumptionType','SuspendOrderType'):
        if isinstance(dbm[name],RecordRows):
            dbm[name]=[deepcopy(row) for row in dbm[name]]
    if producing_native():_observe_dbm(dbm,'assembly_ready')
    with stage('dbm'):
        selected = connected_dbm_stages(today, dbm, facts, delivery, report_exceptions)
        dbm_stages = retain_dbm_stages(selected,completed_boundaries)
    final_dbm={n:deepcopy(dbm_stages[-1][1][n]) for n in prior['dbm']}
    if delivery is not None:
        reports = dbm_report_images(dbm_stages)
    # Each required report now owns its retained image. Neither the DBM input
    # nor its terminal working generation is a consumer of the later BTR work.
    del selected, dbm_stages, dbm, facts
    control_final=carry_dbm_controls(control_final, final_dbm)
    if delivery is not None:
        control_final['importer_settings'].append({'Parameter': 'StockReservationType',
            'Value': str(profile['calculation']['stock_configuration']['reservation_type'])})
    return DbmDay(
        context=context if not _action_revision else replace(context,action_revision=_action_revision),
        pick_source_digests=phase.pick_source_digests,
        importer=phase.importer,
        control_final=control_final,
        control_aux=phase.control_aux,
        diagnostics=phase.diagnostics,
        force_alert_capture=phase.force_alert_capture,
        completed_boundaries=phase.completed_boundaries,
        nms=phase.nms,
        delivery=phase.delivery,
        supplier_sob=phase.supplier_sob,
        supplier_moq=phase.supplier_moq,
        bpr_master=phase.bpr_master,
        order_state=phase.order_state,
        calculated=phase.calculated,
        report=phase.report,
        late=phase.late,
        complete=phase.complete,
        operational_input_tables=phase.operational_input_tables,
        pick_state=phase.pick_state,
        pick_sources=phase.pick_sources,
        final_dbm=final_dbm,
        reports=reports,
    )


@accepted_inputs.phase
def produce_btr(phase: DbmDay):
    """Run BTR and the original full result/closing assembly; no persistence."""
    if phase.calculated is None:
        raise ValueError('Full BTR assembly requires the live calculation graph')
    return _produce_btr(phase)


@accepted_inputs.phase
def produce_btr_from_snapshot(phase: DbmDay, sources, *, pick_source_digests):
    """Continue the typed phase without inventing discarded diagnostics."""
    from mta.application.stage_calculation_sources import CalculationSources
    from mta.temporal.day_phases import ScopedDayOutput
    if (not phase.context.native_daily or phase.calculated is not None
            or not isinstance(sources, CalculationSources)):
        raise ValueError('Typed native continuation and its calculation sources required')
    result = _produce_btr(phase, sources=sources, pick_source_digests=pick_source_digests)
    return ScopedDayOutput(result, sources)


def _produce_btr(phase: DbmDay, *, sources=None, pick_source_digests=None):
    from mta.serialization import digest
    from mta.application import daily_finalization
    context = phase.context
    prior = context.prior
    day = context.day
    profile = context.profile
    native_daily = context.native_daily
    master_snapshot = context.master_snapshot
    today = context.today
    finalization = context.finalization
    master = context.master
    importer = phase.importer
    control_final = phase.control_final
    control_aux = phase.control_aux
    diagnostics = phase.diagnostics
    force_alert_capture = phase.force_alert_capture
    completed_boundaries = phase.completed_boundaries
    nms = phase.nms
    delivery = phase.delivery
    bpr_master = phase.bpr_master
    order_state = phase.order_state
    calculated = phase.calculated
    report = phase.report
    late = phase.late
    complete = phase.complete
    operational_input_tables = phase.operational_input_tables
    pick_state = phase.pick_state
    pick_sources = phase.pick_sources
    final_dbm = phase.final_dbm
    reports = phase.reports
    # Continuation replaces only this mapping's standards entry. Keep the
    # callable DBM phase's pre-BTR mapping/list intact without another deep copy.
    final_dbm = dict(final_dbm)
    supplier_state = {'refreshed_sob': phase.supplier_sob,
                      'refreshed_moq': phase.supplier_moq}
    def assemble_closing():
        # These independent closing copies are required at commit, but need not
        # overlap the BTR scratch generations. Keep the existing alias contract
        # for complete/controls; commit still owns their final flag writers.
        closing={'importer':{n:deepcopy(importer[n]) for n in PRIOR_TABLES},'importer_settings':control_final['importer_settings'],
            'bpr':{'BPRMaster':bpr_master,'Plants':deepcopy(prior['bpr']['Plants']),'NoNormMaster':deepcopy(prior['bpr']['NoNormMaster']),
                   'DailyConsumption':deepcopy(late['BPRDailyConsumption'])},
            'supplier':{'SOBData':supplier_state['refreshed_sob'],'MOQData':supplier_state['refreshed_moq']},
            'orders':{n:deepcopy(order_state[n]) for n in prior['orders']},'controls':control_final,'dbm':final_dbm}
        if complete is not None:
            closing['complete'] = complete
        if pick_state is not None:
            closing.setdefault('complete', {}).update({name: pick_state[name] for name in
                                  ('LogisticPickList', 'PickListDataForTruckFormation')})
        return closing
    result = {'ClosingState':None}
    if sources is None:
        result['CalculationOutputs'] = [{'capability':n,'rows':v} for n,v in calculated.items()]
    if pick_state is not None:
        from mta.serialization import digest
        result['_PickSourceDigests'] = ({name: digest(rows) for name, rows in pick_sources.items()}
            if sources is None else pick_source_digests)
    if delivery is not None:
        from mta.domain.btr_finalization import btr_stages
        # BTR treats incoming facts as read-only and copies its mutated tables.
        btr_facts = {**prior['consumer_context'], **importer,
                     **final_dbm, 'vf_RationedReqReport': report,
                     'BPR_Table': late['BPR_Table'], 'MasterData': importer['MasterData']}
        if nms is not None:
            btr_facts['NMSAllItems'] = nms['NMSAllItems']
        # UpdateBRAge changes these three fields on the current Pick-based
        # expedite population. Reuse the accepted R1 Pick membership producer;
        # an opening/current-day prepared expedite result is never the input.
        pick_keys = {(r['sku_code'], r['location_code'], r['parent_location_code'])
                     for r in (calculated['r1_ration_bifurcation'] if sources is None else sources.pick_bands)}
        master_by_key = {}
        for m in importer['MasterData']:
            master_by_key.setdefault((m['SKUCode'], m['WhCode']), []).append(m)
        btr_facts['ExpediteDispatches'] = [
            {'SKUCode': r['SKUCode'], 'WhCode': r['WhCode'],
             'BRAge': None, 'BRAgeRedCount': None, 'BRAgeBlackCount': None}
            for r in report for m in master_by_key.get((r['SKUCode'], r['WhCode']), ())
            if (r['SKUCode'], r['WhCode'], r['ParentWhCode']) in pick_keys
            and r['WhCode'] != r['ParentWhCode'] and r['DispatchColor'] in ('Black', 'Red', 'Yellow')]
        with stage('btr'):
            for _, trend_state in connected_btr_stages(today, prior['btr'], btr_facts, delivery,
                    bpr_daily=late['BPRDailyConsumption'],
                    supplier_dispatch_req=None if complete is None else complete['SupplierDispatchReq']):
                pass
        del btr_facts, master_by_key, pick_keys
        if complete is not None and str(delivery['btr_settings']['CaptureDispatchExecutionEfficiency'])=='1':
            from mta.domain.btr_rationing_history import STAGE
            daily_finalization.mark(complete, STAGE)
        completed_boundaries.append('btr-insights')
        # ExtendedOCP and Category share the Importer standard-attribute table.
        # Its final writer is BTR UpdateCategoryCol, after the DBM snapshot.
        final_dbm['SKULocStandardAttributes'] = deepcopy(trend_state['SKULocStandardAttributes'])
        closing=assemble_closing()
        for attr in closing['importer']['SkuLocAttributeData']:
            if attr['NonNMS'] is not None:
                attr['NonNMS'] = bool(attr['NonNMS'])
        closing['dbm'] = deepcopy(final_dbm)
        closing.update(control_aux=control_aux, btr=deepcopy(trend_state),
                       consumer_context=deepcopy(prior['consumer_context']),
                       publication_context=deepcopy(prior['publication_context']))
        if nms is not None:
            closing['consumer_context']['NMSAllItems'] = nms['NMSAllItems']
        # Reports that overwrite the same legacy staging tables stay separate
        # consumer-visible families in the enclosing immutable run.
        reports.append({'stage': 'controls', 'tables': diagnostics})
        result.update(BPRFinal=[late], DBMFinal=[final_dbm], Reports=reports,
            BTRFinal=[trend_state],
            PublicationContext=[deepcopy(prior['publication_context'])], Lineage=[])
        result['_CompletedBoundaries']=[*completed_boundaries,'closing-state']
        if finalization is not None:
            if finalization['policy'] != daily_finalization.ACTIVE_POLICY:
                closing['importer_settings'] = daily_finalization.finish(
                    closing['complete'], closing['importer_settings'], today)
            from mta.serialization import digest
            profile_digest=digest(profile)
            result['_Cohort1'] = dict(policy=finalization['policy'], business_date=today,
                configuration_digest=profile_digest,
                qualification=daily_finalization.qualification(finalization['policy']),
                flag_digest=digest(closing['complete']['ScriptExecutedFlag']))
    else:
        closing=assemble_closing()
    result['ClosingState']=[closing]
    del assemble_closing
    if native_daily:
        result['_ReportBoundary']='fresh-operational-report-boundary-v3'
        from mta.application.persistent_master import CONTRACT
        result['_MasterPreparation'] = dict(contract=CONTRACT,
            qualified=context.master_qualified,
            configuration_digest=(profile_digest if delivery is not None and finalization is not None
                                  else digest(profile)), reused=context.master_reused,
            full_master_producer_calls=(0 if context.master_reused else
                context.master_work['producer_calls'] if context.master_work else 1),
            changed_work=context.master_work)
    if operational_input_tables is not None:
        result['_OperationalInputTables'] = operational_input_tables
    if force_alert_capture is not None:
        result['_OperationalForceSources'] = force_alert_capture
    return result
