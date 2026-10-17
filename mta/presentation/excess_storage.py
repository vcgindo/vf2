"""Transactional current-day report projection; no F2 state/receipt updates."""
from django.db import transaction

from mta.presentation.excess import FIELDS, PRODUCER_SHA, produce
from mta.runtime.models import CalculationRun, ExcessInventoryRow, ExcessProjection
from mta.serialization import digest, storage


def inputs(output, business_date):
    bpr = output['BPRFinal'][0] if 'BPRFinal' in output else output['BPRReports'][0]
    return dict(rationed=bpr['vf_RationedReqReport'],
                standards=output['ClosingState'][0]['dbm']['SKULocStandardAttributes'],
                business_date=str(business_date))


def read_excess(run, *, output):
    receipt = ExcessProjection.objects.get(run=run)
    if receipt.producer_sha256 != PRODUCER_SHA or receipt.source_digest != digest(inputs(output, run.business_date)):
        raise ValueError('Excess projection source identity differs')
    records = list(ExcessInventoryRow.objects.filter(run=run).order_by('ordinal').values('ordinal', *FIELDS))
    if [r['ordinal'] for r in records] != list(range(receipt.row_count)):
        raise ValueError('Excess projection population/order drift')
    rows = storage([{name: row[name] for name in FIELDS} for row in records])
    if digest(rows) != receipt.rows_digest:
        raise ValueError('Excess projection values/types/multiplicity drift')
    return rows


def write_excess(run, output):
    if transaction.get_autocommit():
        raise ValueError('Excess projection requires the publication transaction')
    source = inputs(output,run.business_date)
    rows = produce(**source)
    receipt = ExcessProjection.objects.create(run=run,producer_sha256=PRODUCER_SHA,
        source_digest=digest(source),rows_digest=digest(rows),row_count=len(rows))
    ExcessInventoryRow.objects.bulk_create([
        ExcessInventoryRow(run=run,ordinal=i,**row) for i,row in enumerate(rows)],batch_size=500)
    if read_excess(run,output=output)!=rows:
        raise ValueError('Excess projection readback differs')
    return receipt
