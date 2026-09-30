"""Atomic publication boundary: never publish partial outputs or bless drift."""
from django.db import transaction
from django.utils import timezone

from mta.planning.engine import calculate_current_day
from mta.runtime.models import CalculationRun, Checkpoint
from mta.serialization import storage, digest


def read_outputs(run):
    run.refresh_from_db()
    if digest(run.input_payload) != run.input_digest:
        raise ValueError('Immutable input drift')
    if run.status != 'SUCCEEDED':
        raise ValueError('Only a completed run may be read as an output')
    outputs = {}
    for row in run.checkpoints.all():
        if row.row_count != len(row.rows) or row.digest != digest(row.rows):
            raise ValueError('Checkpoint storage drift: ' + row.name)
        outputs[row.name] = row.rows
    if sorted(outputs) != run.output_roster or digest(outputs) != run.output_digest:
        raise ValueError('Output roster or checksum drift')
    return outputs


def execute_current_day(payload, *, execution_revision):
    if not isinstance(execution_revision, str) or not execution_revision or len(execution_revision) > 80:
        raise ValueError('Explicit execution revision required')
    if not transaction.get_autocommit():
        raise ValueError('The run service owns its durable transaction boundary')
    raw = storage(payload)
    input_digest = digest(raw)
    source = raw['standard_input'] if raw.get('schema') == 'r1-gulfoil-file-input-v1' else raw
    today = source['foundation']['snapshot']['business_date']
    with transaction.atomic():
        run, created = CalculationRun.objects.get_or_create(
            input_digest=input_digest, execution_revision=execution_revision,
            defaults={'input_payload': raw, 'business_date': today})
        if not created:
            if run.input_payload != raw or digest(run.input_payload) != run.input_digest:
                raise ValueError('Immutable input drift')
            # A failed/running attempt cannot be silently relabelled as success.
            read_outputs(run)
            return run
    try:
        # The durable source facts, not the caller's still-mutable object, own
        # this execution. JSON readback must reproduce precisely these inputs.
        output = storage(calculate_current_day(raw))
        with transaction.atomic():
            run = CalculationRun.objects.select_for_update().get(pk=run.pk)
            if run.status != 'RUNNING' or run.checkpoints.exists():
                raise ValueError('Run changed during calculation')
            Checkpoint.objects.bulk_create([Checkpoint(
                run=run, name=name, rows=rows, row_count=len(rows), digest=digest(rows))
                for name, rows in output.items()])
            run.status = 'SUCCEEDED'
            run.output_roster = sorted(output)
            run.output_digest = digest(output)
            run.completed_at = timezone.now()
            run.save(update_fields=['status', 'output_roster', 'output_digest', 'completed_at'])
        return run
    except Exception as error:
        CalculationRun.objects.filter(pk=run.pk, status='RUNNING').update(
            status='FAILED', failure={'type': type(error).__name__, 'message': str(error)},
            completed_at=timezone.now())
        raise
