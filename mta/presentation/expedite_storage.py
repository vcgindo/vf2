"""Typed report publication; accepted calculations and ageing stay unchanged."""
from django.db import transaction
from mta.presentation.expedite import FIELDS,PRODUCER_SHA,produce
from mta.presentation.pick_storage import read_pick_bands,selected_bands
from mta.presentation.rrr import pick_rows
from mta.runtime.models import CalculationRun,ExpediteProjection,ExpediteRow
from mta.serialization import digest,storage


def inputs(output,bands):
    closing=output['ClosingState'][0]
    report=(output['BPRFinal'][0] if 'BPRFinal' in output else output['BPRReports'][0])['vf_RationedReqReport']
    return dict(pick=storage(pick_rows(report,bands)),masters=closing['importer']['MasterData'],
        standards=closing['dbm']['SKULocStandardAttributes'],rationed=report,
        ages=closing['btr']['ExpediteDispatches'])


def read_expedite(run, *, output, bands=None):
    if bands is None:
        bands = read_pick_bands(run)
    receipt = ExpediteProjection.objects.get(run=run)
    if receipt.producer_sha256 != PRODUCER_SHA or receipt.source_digest != digest(inputs(output, bands)):
        raise ValueError('Expedite projection source identity differs')
    records = list(ExpediteRow.objects.filter(run=run).order_by('ordinal').values('ordinal', *FIELDS))
    if [r['ordinal'] for r in records] != list(range(receipt.row_count)):
        raise ValueError('Expedite projection population/order drift')
    rows = storage([{name: row[name] for name in FIELDS} for row in records])
    if digest(rows) != receipt.rows_digest:
        raise ValueError('Expedite projection values/types/multiplicity drift')
    return rows


def write_expedite(run,output,*,bands):
    if transaction.get_autocommit(): raise ValueError('Expedite requires the publication transaction')
    source=inputs(output,bands); rows=produce(**source)
    receipt=ExpediteProjection.objects.create(run=run,producer_sha256=PRODUCER_SHA,
        source_digest=digest(source),rows_digest=digest(rows),row_count=len(rows))
    ExpediteRow.objects.bulk_create([ExpediteRow(run=run,ordinal=i,**row) for i,row in enumerate(rows)],batch_size=500)
    if read_expedite(run,output=output,bands=bands)!=rows: raise ValueError('Expedite readback differs')
    return receipt
