"""Offline accepted-run publication wrapper; native writers/readers remain production."""
from django.db import transaction
from mta.runtime.models import CalculationRun, ExcessProjection
from mta.presentation.excess_storage import read_excess, write_excess
from mta.presentation.pick_storage import read_pick_bands

@transaction.atomic
def publish_existing(run_id, *, expected_output_digest):
    from mta.runtime.services import read_outputs
    run = CalculationRun.objects.select_for_update().get(pk=run_id)
    if (run.kind!='DAILY_CHAIN' or run.status!='SUCCEEDED' or run.output_digest!=expected_output_digest or
            run.parity_summary.get('status') not in ('PASS','PASS_WITH_LEGACY_FLAWS')):
        raise ValueError('Explicit accepted source run required')
    output = read_outputs(run)
    if ExcessProjection.objects.filter(run=run).exists():
        read_excess(run,output=output)
        return ExcessProjection.objects.get(run=run)
    return write_excess(run,output)

