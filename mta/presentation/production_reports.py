"""Transactional source adapters; application admission remains a separate owner."""
from mta.row_sequences import is_record_rows
import inspect
from copy import deepcopy

from django.db import transaction
from mta.application import operational_bor, production_rrr, production_output_policy, production_bor_contract
from mta.application.operational_capture import capture_rows, _population
from mta.domain.complete_daily_scalars import ascii_equal
from mta.runtime import production_report_storage as typed
from mta.serialization import digest


def _project(owner, name, fields):
    if not isinstance(owner, dict) or not is_record_rows(owner.get(name)):
        raise ValueError('Native report producer population missing: '+name)
    if any(not isinstance(row, dict) or not set(fields) <= set(row) for row in owner[name]):
        raise ValueError('Native report producer fields missing: '+name)
    return [{field: deepcopy(row[field]) for field in fields} for row in owner[name]]


def current(output, opening):
    """BOROA uses pre-refresh supplier facts; RRR uses actual computed allocations."""
    calculated = output['CalculationOutputs']
    bands = capture_rows(calculated)
    closing, report = output['ClosingState'][0], output['BPRFinal'][0]
    rationed = _project(report, 'vf_RationedReqReport', tuple(
        'LeftoverParentStock' if name == 'LeftOverParentStock' else name
        for name in operational_bor.RATIONED_FIELDS))
    for row in rationed:
        row['LeftOverParentStock'] = row.pop('LeftoverParentStock')
    bor = operational_bor.collect_bor_order_allocation(
        bpr_master=_project(closing['bpr'],'BPRMaster',operational_bor.BPR_MASTER_FIELDS),
        sob_data=_project(opening['supplier'],'SOBData',operational_bor.SOB_FIELDS),
        moq_data=_project(opening['supplier'],'MOQData',operational_bor.MOQ_FIELDS),
        requirements=bands['requirement_bands'], rationed_report=rationed,
        bpr_table=_project(report,'BPR_Table',operational_bor.BPR_TABLE_FIELDS), equal=ascii_equal)
    allocated = _population(calculated,'r1_allocated_orders')
    rrr = production_rrr.produce(rationed_report=report['vf_RationedReqReport'],
        requirement_bands=_population(calculated,'r1_requirement_band'),
        bpr_master=closing['bpr']['BPRMaster'],
        advance_stock_allocations=_population(calculated,'r1_advance_stock_allocation'),
        allocated_orders=allocated)
    from mta.application.row_bag_lookup import AsciiBagLookup
    advances=AsciiBagLookup(bands['advance_stock_allocations'], ('sku_code','source_location_code'), ascii_equal)
    requirements=[]
    for row in bands['requirement_bands']:
        amounts=[item['allocated_quantity'] for item in advances.candidates(row, ('SKUCode','WhCode'))
            if ascii_equal(item['sku_code'],row['SKUCode']) and ascii_equal(item['source_location_code'],row['WhCode'])]
        requirements.append(dict(SKUCode=row['SKUCode'],WhCode=row['WhCode'],
                                 AdvAllocDone=operational_bor._int(sum(amounts))))
    values = dict(BORWithOrderAllocation=bor,RRR_OrderAllocation=rrr,
                  AllocatedOrders=allocated,BOROARequirement=requirements)
    if opening.get('production_report_schema') == production_output_policy.SOURCE_SCHEMA:
        policy = production_output_policy.require(opening['production_report_policy']['output_contract'])
        for requirement, band in zip(requirements, bands['requirement_bands'], strict=True):
            requirement['ParentWhCode'] = band['ParentWhCode']
        values['BORWithOrderAllocation'] = production_output_policy.bor_oa(bor, policy)
        values['SupplierDispatchReq'] = production_bor_contract.produce(
            supplier_dispatch_rows=closing['complete']['SupplierDispatchReq'],
            dispatch_colours=[dict(SKUCode=row['sku_code'], WHCode=row['location_code'],
                                  DispatchColor=row['colours']['dispatch']['band'])
                              for row in _population(calculated, 'r1_requirement')],
            policy=policy['normal_bor'])
    return values


def write(run, output, opening):
    return _write_sources(run,opening,lambda:current(output,opening))


def _write_report_rows(run, values, opening):
    """Original BPR-produced populations; histories still use this run's parent."""
    expected={'BORWithOrderAllocation','RRR_OrderAllocation','AllocatedOrders','BOROARequirement'}
    if opening.get('production_report_schema')==production_output_policy.SOURCE_SCHEMA:
        expected.add('SupplierDispatchReq')
    if not isinstance(values,dict) or set(values)!=expected:
        raise ValueError('Captured production report population roster differs')
    return _write_sources(run,opening,lambda:dict(values))


def _write_sources(run,opening,produce):
    if transaction.get_autocommit() or run.kind!='DAILY_CHAIN' or run.status!='RUNNING':
        raise ValueError('Native report sources require the running day transaction')
    policy=opening['production_report_policy']
    initial=opening['production_report_opening']
    if run.predecessor_id is None:
        if initial != {'BOR_OrderAllocationHistory': [], 'RRR_OrderAllocationHistory': []}:
            raise ValueError('Explicit fresh report-history opening required')
        history=initial
    else:
        if initial is not None:
            raise ValueError('Successor report history must come from its own persisted predecessor')
        parent=run.predecessor
        if parent.status!='SUCCEEDED' or parent.business_date>=run.business_date:
            raise ValueError('Native report predecessor is not a completed prior day')
        history={name:typed.read(parent,name) for name in
                 ('BOR_OrderAllocationHistory','RRR_OrderAllocationHistory')}
    values=produce()
    expanded = opening.get('production_report_schema') == production_output_policy.SOURCE_SCHEMA
    if expanded:
        values['BOR_OrderAllocationHistory']=production_output_policy.bor_oa_history(
            opening=history['BOR_OrderAllocationHistory'],current=values['BORWithOrderAllocation'],
            business_date=run.business_date.isoformat(),horizon=policy['bor_history_horizon'],
            policy=policy['output_contract'])
    else:
        values['BOR_OrderAllocationHistory']=operational_bor.collect_bor_order_allocation_history(
            opening_history=history['BOR_OrderAllocationHistory'],current_bor=values['BORWithOrderAllocation'],
            business_date=run.business_date.isoformat(),horizon=policy['bor_history_horizon'])
    values['RRR_OrderAllocationHistory']=operational_bor.collect_rrr_order_allocation_history(
        opening_history=history['RRR_OrderAllocationHistory'],current_rrr=values['RRR_OrderAllocation'],
        business_date=run.business_date.isoformat(),horizon=policy['rrr_history_horizon'])
    recipe=recipe_digest()
    images={}
    for name,rows in values.items():
        item=typed.save(run,name,rows,expanded=expanded)
        item['producer']=dict(recipe_digest=recipe,policy=policy,input_digest=run.input_digest,
            business_date=run.business_date.isoformat(),
            predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
            predecessor_output_digest=run.predecessor.output_digest if run.predecessor_id else None,
            supplier_opening_digest=digest(opening['supplier']))
        images[typed.PATHS[name]]=item
    return images


def recipe_digest():
    from mta.application import production_order_allocation, production_order_sources, row_bag_lookup
    from mta.presentation import daily_rrr_colour
    return digest(dict(adapter=inspect.getsource(current),writer=inspect.getsource(write),
        finite_writer=inspect.getsource(_write_report_rows),source_writer=inspect.getsource(_write_sources),
        rrr=inspect.getsource(production_rrr),bor=inspect.getsource(operational_bor),
        source_lookups=inspect.getsource(row_bag_lookup),norm_rrr=inspect.getsource(daily_rrr_colour),
        allocation=inspect.getsource(production_order_allocation),
        order_sources=inspect.getsource(production_order_sources),
        output_policy=inspect.getsource(production_output_policy),
        normal_bor=inspect.getsource(production_bor_contract)))
