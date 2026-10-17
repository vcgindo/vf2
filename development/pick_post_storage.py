"""Offline accepted-run publication wrapper; native writers/readers remain production."""
from django.db import transaction
from mta.runtime.models import CalculationRun, PickPostProjection
from mta.presentation.pick_post_storage import read_pick_post, write_pick_post
from mta.presentation.pick_storage import read_pick_bands

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
