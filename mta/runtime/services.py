"""Atomic publication boundary: never publish partial outputs or bless drift."""
from django.db import transaction
from django.utils import timezone

from mta.planning.engine import calculate_current_day
from mta.runtime.models import CalculationRun, Checkpoint
from mta.runtime.validation_storage import persist_trace, read_input
from mta.serialization import storage, digest


def read_outputs(run):
    run.refresh_from_db()
    if run.production_manifest.get('version')==2:
        from mta.runtime.receipt_integrity import verify
        from mta.runtime.relational_state import read_daily
        if run.status!='SUCCEEDED':raise ValueError('Only a completed run may be read as an output')
        verify(run)
        return read_daily(run)
    if digest(read_input(run)) != run.input_digest:
        raise ValueError('Immutable input drift')
    if run.status != 'SUCCEEDED':
        raise ValueError('Only a completed run may be read as an output')
    if run.production_manifest:
        from mta.runtime.relational_state import read_daily
        if sorted(run.checkpoints.values_list('name',flat=True))!=run.output_roster:
            raise ValueError('Output roster or checksum drift')
        outputs=read_daily(run)
        if digest(outputs)!=run.production_digest:raise ValueError('Operational output checksum drift')
        return outputs
    outputs = {}
    roster = []
    for row in run.checkpoints.all().iterator(chunk_size=1):
        roster.append(row.name)
        if row.evidence_path:
            if row.rows != [] or not row.evidence_sha256:
                raise ValueError('Validation/production storage boundary drift')
            continue
        values = row.rows
        if row.row_count != len(values) or row.digest != digest(values):
            raise ValueError('Checkpoint storage drift: ' + row.name)
        outputs[row.name] = values
    if sorted(roster) != run.output_roster or digest(outputs) != (run.production_digest or run.output_digest):
        raise ValueError('Output roster or checksum drift')
    return outputs


def finish_run(run, output, *, expected_digest, publication_opening=None):
    """Only writer of a run's complete output, shared by both engine entries."""
    with transaction.atomic():
        run = CalculationRun.objects.select_for_update().get(pk=run.pk)
        if run.status != 'RUNNING' or run.checkpoints.exists():
            raise ValueError('Run changed during calculation')
        typed=run.input_payload.get('schema')=='fresh-daily-input-manifest-v2'
        if typed:
            from mta.runtime.receipt_integrity import audit_input
            audit_input(run)
        if run.input_digest != expected_digest or (not typed and digest(read_input(run)) != expected_digest):
            raise ValueError('Input snapshot changed during calculation')
        # Keep one atomic publication, but serialize/write one checkpoint at
        # a time rather than retaining a second whole temporal output graph.
        if run.kind=='DAILY_CHAIN':
            from mta.runtime.relational_state import save_daily,read_daily,production_projection
            run.production_manifest=save_daily(run,output)
            if typed:
                from mta.runtime.receipt_integrity import audit_output
                run.production_manifest['version']=2
                run.production_digest=digest(run.production_manifest)
                audit_output(run)
            else:
                run.production_digest=digest(production_projection(output))
                if digest(read_daily(run))!=run.production_digest:
                    raise ValueError('Relational production readback differs from calculated state')
            # F3 consumer-only projection: copy produced bands without changing
            # calculations, existing manifests, checkpoints or output digests.
            from mta.presentation.pick_storage import write_pick_bands
            calculation_digest=digest(output['CalculationOutputs'])
            write_pick_bands(run, output['CalculationOutputs'],
                             provenance={'origin': 'production-calculation'},calculation_digest=calculation_digest)
            from mta.presentation.excess_storage import write_excess
            write_excess(run,output)
            from mta.presentation.fulfillment_storage import write_fulfillment
            write_fulfillment(run,output,output['CalculationOutputs'],calculation_digest=calculation_digest)
            from mta.presentation.expedite_storage import write_expedite, selected_bands
            write_expedite(run,output,bands=selected_bands(output['CalculationOutputs']))
            from mta.presentation.pick_post_storage import write_pick_post
            write_pick_post(run,output,bands=selected_bands(output['CalculationOutputs']))
            # execute_day captured these inputs before calculation. A serving
            # environment flag must not independently enable an uncaptured write.
            if publication_opening is not None:
                from mta.presentation.daily_sources import write_sources
                write_sources(run, output, opening=publication_opening)
                from mta.presentation.offline_rrr import write as write_offline_rrr
                write_offline_rrr(run, output)
        for name, rows in output.items():
            if typed and run.evidence_mode=='production':break
            fields = (persist_trace(run, name, rows) if run.kind == 'DAILY_CHAIN'
                      else dict(rows=storage(rows), row_count=len(rows), digest=digest(rows)))
            Checkpoint.objects.create(run=run, name=name, **fields)
        # Consuming captured MDM rows is part of the same committed boundary.
        # A readback/storage failure leaves both queues and run unconsumed.
        from mta.mdm.daily_input import finalize_consumption
        finalize_consumption(run)
        run.status = 'SUCCEEDED'
        if typed:
            from mta.runtime.receipt_integrity import OPERATIONAL_ROSTER, output_root, source_receipts
            run.production_manifest['sources']=storage(source_receipts(run))
            run.production_digest=digest(run.production_manifest)
            run.output_roster=list(OPERATIONAL_ROSTER)
            run.output_digest=output_root(run)
            run.validation_digest=digest(output) if run.evidence_mode=='validation' else ''
        else:
            run.output_roster = sorted(output)
            run.output_digest = digest(output)
        if run.kind!='DAILY_CHAIN':run.production_digest=digest(output)
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'output_roster', 'output_digest', 'production_digest', 'production_manifest', 'completed_at','validation_digest'])
    return run


def fail_run(run, error):
    CalculationRun.objects.filter(pk=run.pk, status='RUNNING').update(
        status='FAILED', failure={'type': type(error).__name__, 'message': str(error)},
        completed_at=timezone.now())


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
        return finish_run(run, calculate_current_day(raw), expected_digest=input_digest)
    except Exception as error:
        fail_run(run, error)
        raise
