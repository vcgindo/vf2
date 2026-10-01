"""Transactional typed post-ration report projection, never a trace fallback."""
from django.db import transaction
from mta.presentation.pick_post import produce,FIELDS,SOURCE_HASHES
from mta.presentation.pick_storage import read_pick_bands
from mta.presentation.rrr import pick_rows
from mta.runtime.models import CalculationRun,PickPostProjection,PickPostRow
from mta.serialization import digest,storage


def inputs(output,bands):
    bpr=output['BPRFinal'][0] if 'BPRFinal' in output else output['BPRReports'][0]
    return storage(pick_rows(bpr['vf_RationedReqReport'],bands))


def read_pick_post(run,*,output,bands=None):
    if bands is None: bands=read_pick_bands(run)
    source=inputs(output,bands); receipt=PickPostProjection.objects.get(run=run)
    if receipt.source_digest!=digest(source) or receipt.producers_digest!=digest(SOURCE_HASHES):
        raise ValueError('Post-ration source identity drift')
    records=list(PickPostRow.objects.filter(run=run).order_by('ordinal').values('ordinal',*FIELDS))
    if [r['ordinal'] for r in records]!=list(range(receipt.row_count)) or len(source)!=receipt.row_count:
        raise ValueError('Post-ration population/order drift')
    rows=storage([{f:r[f] for f in FIELDS} for r in records])
    if digest(rows)!=receipt.rows_digest: raise ValueError('Post-ration typed values/multiplicity drift')
    if any(any(a[n]!=b[n] for n in FIELDS[:3]) for a,b in zip(source,rows)):
        raise ValueError('Post-ration source ordinal identity drift')
    return [{**a,**b} for a,b in zip(source,rows)]


def write_pick_post(run,output,*,bands):
    if transaction.get_autocommit(): raise ValueError('Post-ration requires publication transaction')
    source=inputs(output,bands); rows=produce(source)
    receipt=PickPostProjection.objects.create(run=run,source_digest=digest(source),producers_digest=digest(SOURCE_HASHES),
        rows_digest=digest(rows),row_count=len(rows))
    PickPostRow.objects.bulk_create([PickPostRow(run=run,ordinal=i,**r) for i,r in enumerate(rows)],batch_size=500)
    expected=[{**a,**b} for a,b in zip(source,rows)]
    if read_pick_post(run,output=output,bands=bands)!=expected: raise ValueError('Post-ration readback differs')
    return receipt


@transaction.atomic
def publish_existing(run_id,*,expected_output_digest):
    from mta.runtime.services import read_outputs
    run=CalculationRun.objects.select_for_update().get(pk=run_id)
    if (run.kind!='DAILY_CHAIN' or run.status!='SUCCEEDED' or run.output_digest!=expected_output_digest or
            run.parity_summary.get('status') not in ('PASS','PASS_WITH_LEGACY_FLAWS')):
        raise ValueError('Explicit accepted source run required')
    output=read_outputs(run); bands=read_pick_bands(run)
    if PickPostProjection.objects.filter(run=run).exists():
        read_pick_post(run,output=output,bands=bands)
        return PickPostProjection.objects.get(run=run)
    return write_pick_post(run,output,bands=bands)
