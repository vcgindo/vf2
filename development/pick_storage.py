"""Offline historical Pick trace installation; never a production fallback."""
from django.db import transaction
from mta.runtime.models import CalculationRun, Checkpoint, PickProjection
from mta.presentation.pick_storage import read_pick_bands, write_pick_bands

@transaction.atomic
def restore_pick_bands(run_id, *, expected_output_digest):
    """Explicit, idempotent read-model publication of an accepted retained run."""
    from mta.runtime.services import read_outputs
    from development.validation_storage import evidence_path
    from parity.output_archive import iter_rows

    run = CalculationRun.objects.select_for_update().get(pk=run_id)
    if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED' or
            run.output_digest != expected_output_digest or
            run.parity_summary.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS') or
            run.parity_summary.get('comparisons', {}).get('calculation/bifurcation') != 'PASS'):
        raise ValueError('Accepted explicit Pick calculation identity required')
    read_outputs(run)  # Validate unchanged native production/input identity first.
    if PickProjection.objects.filter(run=run).exists():
        read_pick_bands(run)
        return PickProjection.objects.get(run=run)
    checkpoint = Checkpoint.objects.get(run=run, name='CalculationOutputs')
    expected_path = str(run.pk) + '/CalculationOutputs.jsonl.gz'
    if checkpoint.evidence_path != expected_path or checkpoint.rows != []:
        raise ValueError('Retained Pick source owner/storage mismatch')
    metadata = dict(sha256=checkpoint.evidence_sha256,
                    digest=checkpoint.digest, row_count=checkpoint.row_count)
    # Exhaust the iterator: final count/logical-digest verification is mandatory.
    calculated = list(iter_rows(evidence_path(run, 'CalculationOutputs'), metadata))
    return write_pick_bands(run, calculated, provenance=dict(
        origin='retained-modern-calculation', output_digest=run.output_digest,
        production_digest=run.production_digest, evidence_path=checkpoint.evidence_path,
        evidence_sha256=checkpoint.evidence_sha256,
        parity_receipt_sha256=run.parity_summary['sha256']))

