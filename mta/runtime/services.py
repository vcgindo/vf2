"""Atomic publication boundary: never publish partial outputs or bless drift."""
from django.db import transaction
from django.utils import timezone

from mta.planning.engine import calculate_current_day
from mta.runtime.models import CalculationRun, Checkpoint
from mta.runtime.input_reader import read_input
from mta.serialization import storage, digest
from mta.application.stage_observation import stage


def read_outputs(run, *, include_reports=True):
    run.refresh_from_db()
    if run.production_manifest.get('version') in (2,3):
        from mta.runtime.receipt_integrity import verify
        from mta.runtime.relational_state import read_daily
        if run.status!='SUCCEEDED':raise ValueError('Only a completed run may be read as an output')
        # A certified native preparation already admitted the immutable source
        # and its closed predecessor. Re-auditing that predecessor's complete
        # original opening here would reconstruct it before every successor.
        # Explicit receipt audits and all ordinary non-preparation readers keep
        # their exhaustive input verification below.
        from mta.runtime.opening_scope import current_certified_opening
        initialized=None
        if run.production_manifest.get('ingestion_preparation'):
            from mta.runtime.models import ProductionInitialization
            initialized=ProductionInitialization.objects.select_related('source').filter(
                pk=run.production_manifest['ingestion_preparation'].get('initialization_id')).first()
        if initialized is not None and current_certified_opening(initialized) is not None:
            from mta.runtime.receipt_integrity import verify_root
            verify_root(run)
        else:
            verify(run)
        output=read_daily(run,include_reports=include_reports)
        if run.production_manifest.get('version')==3 and include_reports:
            from mta.presentation.operational_reports import include_generation
            include_generation(run,output)
        return output
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
    # Immutable profile reconstruction happens once before the atomic writer.
    # The full input audit and run/input digest checks remain inside it.
    producer_preparation=output.pop('_MasterPreparation',None)
    with stage('persistence_profile_reconstruction'):
        frozen_profile = (read_input(run, components=('profile',))['profile']
                          if run.kind == 'DAILY_CHAIN' else None)
    with transaction.atomic():
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from mta.mdm.supplier_revisions import lock_transaction
        source_id = MdmDailyInputCapture.objects.filter(run=run).values_list('source_id', flat=True).first()
        if source_id is not None:
            lock_transaction(source_id)
        run = CalculationRun.objects.select_for_update().get(pk=run.pk)
        if run.status != 'RUNNING' or run.checkpoints.exists() or run.scope_attempts.exists():
            raise ValueError('Run changed during calculation')
        from mta.runtime.capture_preparation import require_commit
        prepared_capture=require_commit(run)
        from mta.runtime.captured_input import SCHEMAS as CAPTURED
        typed=run.input_payload.get('schema') in ('fresh-daily-input-manifest-v2','fresh-daily-input-manifest-v3',*CAPTURED)
        if run.kind == 'DAILY_CHAIN' and (not typed or run.evidence_mode != 'production'):
            raise ValueError('Native daily publication requires typed production input')
        if typed:
            from mta.runtime.receipt_integrity import audit_input
            with stage('persistence_input_audit'):
                audit_input(run)
        if run.input_digest != expected_digest or (not typed and digest(read_input(run)) != expected_digest):
            raise ValueError('Input snapshot changed during calculation')
        lineage = output.get('Lineage') or [{}]
        from mta.application.native_report_disposition import verify_commit
        admitted_disposition = run.production_manifest.get('native_report_disposition')
        if admitted_disposition is not None and run.production_manifest != {'native_report_disposition': admitted_disposition}:
            raise ValueError('Native report disposition admission metadata differs')
        verify_commit(admitted_disposition, lineage, run)
        cohort = lineage[0].get('cohort1')
        if run.kind=='DAILY_CHAIN':
            from mta.application.daily_finalization import configuration,verify_finalization_identity
            if configuration(frozen_profile) is not None or cohort is not None:
                verify_finalization_identity(output,frozen_profile,run.business_date.isoformat())
        if cohort is not None:
            if run.kind!='DAILY_CHAIN':raise ValueError('Complete finalization requires a daily-chain owner')
            configured_policy=configuration(frozen_profile)['policy']
            # Queue/task finalization and typed output commit share this one
            # transaction. Any later writer/readback failure rolls both back.
            from mta.mdm.daily_input import finalize_consumption
            from mta.runtime.mdm_daily_models import MdmDailyInputCapture
            from mta.application.daily_finalization import mark
            with stage('persistence_input_consumption'):
                finalize_consumption(run, output=output)
            if not MdmDailyInputCapture.objects.filter(run=run, status='CONSUMED').exists():
                raise ValueError('Cohort1 task source was not consumed')
            complete = output['ClosingState'][0]['complete']
            mark(complete, 'NMSTaskStatusUpdate.sql')
            from mta.application.daily_finalization import ACTIVE_POLICY, finish
            if configured_policy == ACTIVE_POLICY:
                captured = MdmDailyInputCapture.objects.get(run=run, status='CONSUMED')
                if not captured.nms_active:
                    raise ValueError('Active completion requires its consumed NMS input')
                # Only after actual capture composition and atomic native archive/
                # clear/task writers, never from a requested or missing source.
                mark(complete, 'NMSImportData.sql', 'NMSArchiveInputData.sql', 'NMSClearInputTables.sql')
                closing = output['ClosingState'][0]
                closing['importer_settings'] = finish(complete, closing['importer_settings'],
                    run.business_date.isoformat(), policy=ACTIVE_POLICY)
            from mta.mdm.initialization_contract import SOURCE_SCHEMA
            captured = MdmDailyInputCapture.objects.select_related('source').get(run=run, status='CONSUMED')
            if configured_policy == ACTIVE_POLICY or captured.source.receipt.get('schema') == SOURCE_SCHEMA:
                from mta.mdm.daily_current import publish as publish_mdm_current
                with stage('persistence_current_masters'):
                    publish_mdm_current(run, captured, output['ClosingState'][0])
            cohort['flag_digest'] = digest(complete['ScriptExecutedFlag'])
            # Verify the same complete boundary after its actual owned writers,
            # inside the transaction so any failure rolls every writer back.
            if configured_policy == ACTIVE_POLICY:
                from mta.application.daily_finalization import verify_successor
                verify_successor(output, frozen_profile,
                                 run.business_date.isoformat())
        # Keep one atomic publication, but serialize/write one checkpoint at
        # a time rather than retaining a second whole temporal output graph.
        if run.kind=='DAILY_CHAIN':
            from mta.runtime.relational_state import save_daily,read_daily,production_projection
            with stage('persistence_typed_snapshots'):
                run.production_manifest=save_daily(run,output)
            if prepared_capture is not None:
                # Input/audit readers inside this same atomic publication still
                # require the already sealed native initialization authority.
                run.production_manifest['ingestion_preparation']=prepared_capture
            if typed:
                from mta.runtime.receipt_integrity import audit_output
                run.production_manifest['version']=3 if output.get('_ReportBoundary') else 2
                run.production_digest=digest(run.production_manifest)
                with stage('persistence_full_output_readback'):
                    audit_output(run)
            else:
                run.production_digest=digest(production_projection(output))
                if digest(read_daily(run))!=run.production_digest:
                    raise ValueError('Relational production readback differs from calculated state')
            # F3 consumer-only projection: copy produced bands without changing
            # calculations, existing manifests, checkpoints or output digests.
            from mta.presentation.pick_storage import write_pick_bands
            calculation_digest=digest(output['CalculationOutputs'])
            capture_policy = frozen_profile.get('operational_sources')
            if capture_policy is not None:
                from mta.application.operational_capture import CAPTURE_POLICY
                from mta.runtime.operational_source import write_source
                if capture_policy != CAPTURE_POLICY:
                    raise ValueError('Unsupported operational source capture policy')
                write_source(run, output['CalculationOutputs'], calculation_digest=calculation_digest)
            input_capture = frozen_profile.get('operational_input_sources')
            if input_capture is not None:
                from mta.runtime.operational_input_source import write_input_source
                write_input_source(run, output.pop('_OperationalInputTables', None))
            elif '_OperationalInputTables' in output:
                raise ValueError('Unexpected processed input capture without opt-in')
            force_capture = frozen_profile.get('operational_force_sources')
            if force_capture is not None:
                from mta.runtime.operational_force_source import write_force_source
                write_force_source(run, output.pop('_OperationalForceSources', None))
            elif '_OperationalForceSources' in output:
                raise ValueError('Unexpected force capture without opt-in')
            write_pick_bands(run, output['CalculationOutputs'],
                             provenance={'origin': 'production-calculation'},calculation_digest=calculation_digest)
            if run.production_manifest.get('version')==3:
                from mta.runtime.report_sources import write_routes
                run.production_manifest['report_sources']=dict(
                    contract=output['_ReportBoundary'],routes=write_routes(run,output['CalculationOutputs'],
                        output['ClosingState'][0]['orders']['SpikeOrderData']))
            else:
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
        if run.kind != 'DAILY_CHAIN':
            for name, rows in output.items():
                Checkpoint.objects.create(run=run, name=name,
                    rows=storage(rows), row_count=len(rows), digest=digest(rows))
        # Consuming captured MDM rows is part of the same committed boundary.
        # A readback/storage failure leaves both queues and run unconsumed.
        from mta.mdm.daily_input import finalize_consumption
        finalize_consumption(run, output=output)
        if typed:
            from mta.mdm.native_audit import finalize as finalize_native_audit
            finalize_native_audit(run)
        if prepared_capture is not None:
            from mta.runtime.capture_preparation import publication_metadata
            publication_metadata(run,prepared_capture,producer_preparation)
        run.status = 'SUCCEEDED'
        if typed:
            from mta.runtime.receipt_integrity import operational_roster, output_root, source_receipts
            run.production_manifest['sources']=storage(source_receipts(run))
            run.production_digest=digest(run.production_manifest)
            run.output_roster=list(operational_roster(run))
            run.output_digest=output_root(run)
        else:
            run.output_roster = sorted(output)
            run.output_digest = digest(output)
        if run.kind!='DAILY_CHAIN':run.production_digest=digest(output)
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'output_roster', 'output_digest', 'production_digest', 'production_manifest', 'completed_at'])
        if prepared_capture is not None:
            from mta.runtime.master_revisions import accept
            accept(run,prepared_capture['initialization_id'],prepared_capture['base_revision_id'])
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
