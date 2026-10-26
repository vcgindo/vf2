"""New-request BTR assembly with an explicit boundary before final processing.

The original chain and phase codec stay byte-for-byte unchanged. This bounded
assembly version calls their existing calculation producers; it neither grants
publication authority nor persists a phase. The runtime owner must authenticate
the sources/hook and finish PostBTR publication before calling finish below.
"""
from copy import deepcopy
from dataclasses import dataclass
import inspect

from mta.application import daily_finalization
from mta.application.stage_calculation_sources import CalculationSources
from mta.application.stage_observation import stage
from mta.serialization import digest
from mta.temporal import chain
from mta.temporal.day_phases import DbmDay, ScopedDayOutput

SCHEMA = 'fresh-runtime-report-btr-assembly-v1'


@dataclass(frozen=True)
class BtrBoundary:
    phase: DbmDay
    sources: CalculationSources | None
    pick_source_digests: object
    trend_state: dict
    final_dbm: dict


def recipe_digest():
    return digest(dict(schema=SCHEMA,
        assembly=inspect.getsource(inspect.getmodule(recipe_digest)),
        chain=inspect.getsource(chain), finalization=inspect.getsource(daily_finalization)))


def prepare_btr_boundary(phase, *, sources=None, pick_source_digests=None):
    """Run BTR once; return its actual sources before any generic final gate.

    No finished output or terminal source lookup is used to construct this cut.
    A caller abandoning this in-memory result has not accepted a business phase.
    """
    if (type(phase) is not DbmDay or not phase.context.native_daily
            or phase.delivery is None or phase.context.finalization is None
            or phase.complete is None):
        raise ValueError('Complete native DBM phase required for PostBTR assembly')
    if ((sources is None and phase.calculated is None)
            or (sources is not None and (type(sources) is not CalculationSources
                                         or phase.calculated is not None))):
        raise ValueError('Full or authenticated scoped calculation sources required')
    context=phase.context
    final_dbm=dict(phase.final_dbm)
    facts={**context.prior['consumer_context'], **phase.importer, **final_dbm,
        'vf_RationedReqReport':phase.report, 'BPR_Table':phase.late['BPR_Table'],
        'MasterData':phase.importer['MasterData']}
    if phase.nms is not None:
        facts['NMSAllItems']=phase.nms['NMSAllItems']
    bands=phase.calculated['r1_ration_bifurcation'] if sources is None else sources.pick_bands
    pick_keys={(row['sku_code'],row['location_code'],row['parent_location_code']) for row in bands}
    master_by_key={}
    for row in phase.importer['MasterData']:
        master_by_key.setdefault((row['SKUCode'],row['WhCode']),[]).append(row)
    facts['ExpediteDispatches']=[
        dict(SKUCode=row['SKUCode'],WhCode=row['WhCode'],
             BRAge=None,BRAgeRedCount=None,BRAgeBlackCount=None)
        for row in phase.report
        for _master in master_by_key.get((row['SKUCode'],row['WhCode']),())
        if (row['SKUCode'],row['WhCode'],row['ParentWhCode']) in pick_keys
        and row['WhCode']!=row['ParentWhCode'] and row['DispatchColor'] in ('Black','Red','Yellow')]
    trend_state=None
    with stage('btr'):
        for _name,trend_state in chain.connected_btr_stages(context.today,
                context.prior['btr'],facts,phase.delivery,
                bpr_daily=phase.late['BPRDailyConsumption'],
                supplier_dispatch_req=phase.complete['SupplierDispatchReq']):
            pass
    if trend_state is None:
        raise ValueError('BTR producer did not yield its completed stage')
    if str(phase.delivery['btr_settings']['CaptureDispatchExecutionEfficiency'])=='1':
        from mta.domain.btr_rationing_history import STAGE
        daily_finalization.mark(phase.complete,STAGE)
    phase.completed_boundaries.append('btr-insights')
    final_dbm['SKULocStandardAttributes']=deepcopy(trend_state['SKULocStandardAttributes'])
    return BtrBoundary(phase,sources,pick_source_digests,trend_state,final_dbm)


def finish_btr_boundary(boundary):
    """Assemble the existing complete output after the caller's PostBTR barrier.

    Active NMS completion remains in services.finish_run; this function cannot
    certify Final placement readiness ahead of those transactional writers.
    """
    if type(boundary) is not BtrBoundary:
        raise ValueError('Prepared native PostBTR boundary required')
    phase=boundary.phase
    context=phase.context
    prior=context.prior
    final_dbm=boundary.final_dbm
    closing={
        'importer':{name:deepcopy(phase.importer[name]) for name in chain.PRIOR_TABLES},
        'importer_settings':phase.control_final['importer_settings'],
        'bpr':dict(BPRMaster=phase.bpr_master, Plants=deepcopy(prior['bpr']['Plants']),
            NoNormMaster=deepcopy(prior['bpr']['NoNormMaster']),
            DailyConsumption=deepcopy(phase.late['BPRDailyConsumption'])),
        'supplier':dict(SOBData=phase.supplier_sob,MOQData=phase.supplier_moq),
        'orders':{name:deepcopy(phase.order_state[name]) for name in prior['orders']},
        'controls':phase.control_final,'dbm':final_dbm,'complete':phase.complete}
    if phase.pick_state is not None:
        closing['complete'].update({name:phase.pick_state[name] for name in
            ('LogisticPickList','PickListDataForTruckFormation')})
    for row in closing['importer']['SkuLocAttributeData']:
        if row['NonNMS'] is not None:row['NonNMS']=bool(row['NonNMS'])
    closing['dbm']=deepcopy(final_dbm)
    closing.update(control_aux=phase.control_aux,btr=deepcopy(boundary.trend_state),
        consumer_context=deepcopy(prior['consumer_context']),
        publication_context=deepcopy(prior['publication_context']))
    if phase.nms is not None:
        closing['consumer_context']['NMSAllItems']=phase.nms['NMSAllItems']
    phase.reports.append(dict(stage='controls',tables=phase.diagnostics))
    result=dict(ClosingState=[closing],BPRFinal=[phase.late],DBMFinal=[final_dbm],
        Reports=phase.reports,BTRFinal=[boundary.trend_state],
        PublicationContext=[deepcopy(prior['publication_context'])],Lineage=[],
        _CompletedBoundaries=[*phase.completed_boundaries,'closing-state'])
    if boundary.sources is None:
        result['CalculationOutputs']=[dict(capability=name,rows=values)
                                     for name,values in phase.calculated.items()]
    if phase.pick_state is not None:
        result['_PickSourceDigests']=({name:digest(rows) for name,rows in phase.pick_sources.items()}
            if boundary.sources is None else boundary.pick_source_digests)
    finalization=context.finalization
    if finalization['policy']!=daily_finalization.ACTIVE_POLICY:
        closing['importer_settings']=daily_finalization.finish(
            closing['complete'],closing['importer_settings'],context.today)
    profile_digest=digest(context.profile)
    result['_Cohort1']=dict(policy=finalization['policy'],business_date=context.today,
        configuration_digest=profile_digest,
        qualification=daily_finalization.qualification(finalization['policy']),
        flag_digest=digest(closing['complete']['ScriptExecutedFlag']))
    result['_ReportBoundary']='fresh-operational-report-boundary-v3'
    from mta.application.persistent_master import qualify,CONTRACT
    result['_MasterPreparation']=dict(contract=CONTRACT,
        qualified=(True if context.master_reused else qualify(context.master,
            context.profile,context.day,closing,snapshot=context.master_snapshot)),
        configuration_digest=profile_digest,reused=context.master_reused,
        full_master_producer_calls=(0 if context.master_reused else
            context.master_work['producer_calls'] if context.master_work else 1),
        changed_work=context.master_work)
    if phase.operational_input_tables is not None:
        result['_OperationalInputTables']=phase.operational_input_tables
    if phase.force_alert_capture is not None:
        result['_OperationalForceSources']=phase.force_alert_capture
    return result if boundary.sources is None else ScopedDayOutput(result,boundary.sources)
