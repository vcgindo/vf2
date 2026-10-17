"""Typed daily Fulfilment read model; no trace reads from production HTTP."""
from django.db import transaction
from mta.presentation.fulfillment import (
    PRODUCER_SHA,SUMMARY_FIELDS,DETAIL_FIELDS,produce_summary,produce_details,routes_for_orders)
from mta.runtime.models import CalculationRun,Checkpoint,FulfillmentProjection,FulfillmentSummaryRow,FulfillmentDetailRow
from mta.serialization import digest,storage


def inputs(output,business_date):
    closing=output['ClosingState'][0]
    bpr=output['BPRFinal'][0] if 'BPRFinal' in output else output['BPRReports'][0]
    return dict(rationed=bpr['vf_RationedReqReport'],standards=closing['dbm']['SKULocStandardAttributes'],
                orders=closing['orders']['SpikeOrderData'],business_date=str(business_date))


def _read(run,receipt):
    result={}
    for name,model,fields in (('summary',FulfillmentSummaryRow,SUMMARY_FIELDS),('details',FulfillmentDetailRow,DETAIL_FIELDS)):
        records=list(model.objects.filter(run=run).order_by('ordinal').values('ordinal',*fields))
        if [r['ordinal'] for r in records]!=list(range(getattr(receipt,name+'_count'))):
            raise ValueError('Fulfilment population/order drift: '+name)
        rows=storage([{k:r[k] for k in fields} for r in records])
        if digest(rows)!=getattr(receipt,name+'_digest'):
            raise ValueError('Fulfilment typed value/multiplicity drift: '+name)
        result[name]=rows
    return result


def read_fulfillment(run, *, output):
    receipt = FulfillmentProjection.objects.get(run=run)
    if run.production_manifest.get('version') == 2:
        from mta.runtime.receipt_integrity import verify_root
        verify_root(run)
    elif receipt.calculation_digest != Checkpoint.objects.get(run=run, name='CalculationOutputs').digest:
        raise ValueError('Fulfilment calculation identity differs')
    if receipt.producer_sha256 != PRODUCER_SHA or receipt.source_digest != digest(inputs(output, run.business_date)):
        raise ValueError('Fulfilment producer/input identity differs')
    return _read(run, receipt)


def write_fulfillment(run,output,calculated, *, calculation_digest=None):
    if transaction.get_autocommit():
        raise ValueError('Fulfilment requires publication transaction')
    source=inputs(output,run.business_date)
    routes=routes_for_orders(calculated,source['orders'])
    rows=dict(summary=produce_summary(source['rationed'],source['standards']),
              details=produce_details(source['orders'],routes,source['standards'],source['business_date']))
    receipt=FulfillmentProjection.objects.create(run=run,producer_sha256=PRODUCER_SHA,
        source_digest=digest(source),calculation_digest=calculation_digest or digest(calculated),
        **{name+suffix:value for name,records in rows.items() for suffix,value in
           (('_count',len(records)),('_digest',digest(records)))})
    for name,model in (('summary',FulfillmentSummaryRow),('details',FulfillmentDetailRow)):
        model.objects.bulk_create([model(run=run,ordinal=i,**row) for i,row in enumerate(rows[name])],batch_size=500)
    if _read(run,receipt)!=rows:
        raise ValueError('Fulfilment typed readback differs')
    return receipt
