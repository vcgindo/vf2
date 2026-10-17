"""Offline historical Fulfilment trace installation."""
from django.db import transaction
from mta.runtime.models import CalculationRun, Checkpoint, FulfillmentProjection
from mta.presentation.fulfillment_storage import read_fulfillment, write_fulfillment

@transaction.atomic
def publish_existing(run_id,*,expected_output_digest):
    from mta.runtime.services import read_outputs
    from development.validation_storage import evidence_path
    from parity.output_archive import iter_rows
    run=CalculationRun.objects.select_for_update().get(pk=run_id)
    if (run.kind!='DAILY_CHAIN' or run.status!='SUCCEEDED' or run.output_digest!=expected_output_digest or
        run.parity_summary.get('status') not in ('PASS','PASS_WITH_LEGACY_FLAWS') or
        run.parity_summary.get('comparisons',{}).get('calculation/routes')!='PASS'):
        raise ValueError('Explicit accepted Fulfilment source identity required')
    output=read_outputs(run)
    if FulfillmentProjection.objects.filter(run=run).exists():
        read_fulfillment(run,output=output)
        return FulfillmentProjection.objects.get(run=run)
    checkpoint=Checkpoint.objects.get(run=run,name='CalculationOutputs')
    if checkpoint.rows!=[] or checkpoint.evidence_path!=str(run.pk)+'/CalculationOutputs.jsonl.gz':
        raise ValueError('Retained Fulfilment source owner/storage mismatch')
    # Exhaust all rows to validate the retained checkpoint digest/count, then
    # persist only consumer summary/details, never the full calculation trace.
    calculated=list(iter_rows(evidence_path(run,'CalculationOutputs'),dict(sha256=checkpoint.evidence_sha256,
                    digest=checkpoint.digest,row_count=checkpoint.row_count)))
    return write_fulfillment(run,output,calculated)
