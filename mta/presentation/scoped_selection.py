"""Explicit phase anchor; current immutable dependencies are admitted per request."""
import json
from pathlib import Path
from mta.serialization import digest
from mta.presentation.request_scope import validated_read
from release.phase_selection import SCHEMA, DBM_SCHEMA, FIELDS, validate, read


def write(path, value):
    # Reuse atomic file replacement, with this schema's own readback validator.
    import os
    import tempfile
    validate(value)
    target = Path(path).resolve()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent, prefix='.' + target.name + '.', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(value, sort_keys=True) + '\n').encode('utf-8'))
            stream.flush(); os.fsync(stream.fileno())
        if read(temporary) != value: raise ValueError('Phase selection readback differs')
        os.replace(temporary, target); temporary = None
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def enabled():
    from django.conf import settings
    return bool(getattr(settings, 'VF_MTA_PHASE_SELECTION_FILE', ''))


def recipe_digest():
    import inspect
    from mta.mdm import season_current
    from mta.application import production_bor_contract, production_output_policy
    from release import phase_selection
    from mta.presentation import (scoped_api, scoped_overview, scoped_rrr, rrr_prepared_sql, views,
        bpr_prepared, bpr_response, bpr_export, rrr_export, rrr_types, planning_git_sql,
        daily_git_custom, daily_git_read, planning_chart_sql, planning_custom_sql, bpr_remarks, scoped_remark_writer,
        scoped_dbm, dbm, dbm_filters, scoped_action_writer, scoped_history, scoped_artifacts,
        scoped_btr, btr_sql, btr, btr_display, btr_export, buffer_trends_sql, mdm_views,
        scoped_logistics, logistics_read, scoped_bor, bor_sql, boroa_sql,
        bor_preparation, boroa_preparation, native_report_colours, daily_rrr_read,
        scoped_batch_files, scoped_batch_downloads, scoped_dbm_stop, scoped_dbm_view, selected_input)
    return digest({m.__name__: inspect.getsource(m) for m in
        (inspect.getmodule(recipe_digest), phase_selection, scoped_api, scoped_overview, scoped_rrr, rrr_prepared_sql,
         views, bpr_prepared, bpr_response, bpr_export, rrr_export, rrr_types, planning_git_sql,
         daily_git_custom, daily_git_read, planning_chart_sql, planning_custom_sql, bpr_remarks, scoped_remark_writer,
         scoped_dbm, dbm, dbm_filters, scoped_action_writer, scoped_history, scoped_artifacts,
         scoped_btr, btr_sql, btr, btr_display, btr_export, buffer_trends_sql, mdm_views, season_current,
         scoped_logistics, logistics_read, scoped_bor, bor_sql, boroa_sql,
         bor_preparation, boroa_preparation, native_report_colours,
         production_bor_contract, production_output_policy, daily_rrr_read,
         scoped_batch_files, scoped_batch_downloads, scoped_dbm_stop, scoped_dbm_view, selected_input)})


def native_identity(view):
    """Initialized source proof for an accepted phase, without a terminal fiction."""
    from datetime import timedelta
    from mta.presentation.context import PublicationUnavailable
    from mta.presentation.native_publication import require_mode
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    from mta.runtime.models import ProductionInitialization, MdmDailyInputCapture
    from mta.presentation.selected_input import read_input
    from mta.presentation.report_verification import profile_reference
    require_mode()
    run = view.run
    if run.kind != 'DAILY_CHAIN' or run.evidence_mode != 'production' or run.status not in ('RUNNING', 'SUCCEEDED'):
        raise PublicationUnavailable('phase_native_day_required')
    capture = MdmDailyInputCapture.objects.select_related('source').get(run=run)
    phase = view.bpr.reports.generation.phase
    if (capture.status != ('CONSUMED' if run.status == 'SUCCEEDED' else 'CAPTURED')
            or capture.source.receipt.get('schema') != SOURCE_SCHEMA
            or phase.source_id != capture.source_id or phase.capture_digest != capture.revision_digest):
        raise PublicationUnavailable('phase_native_initialization_required')
    owner = ProductionInitialization.objects.select_related('source').get(source=capture.source)
    binding = dict(id=str(owner.pk), source_digest=owner.source.digest, input_sha256=owner.input_sha256,
        content_digest=owner.input_digest, configuration_digest=owner.configuration_digest)
    referenced = profile_reference(run, owner)
    inputs = read_input(run, components=('initialization_binding', 'lineage') if referenced else
        ('initialization_binding', 'lineage', 'profile'))
    if (inputs.get('initialization_binding') != binding or not referenced and digest(inputs.get('profile')) != owner.configuration_digest
            or view.bpr.reports.generation.configuration_digest != owner.configuration_digest):
        raise PublicationUnavailable('phase_native_initialization_changed')
    if run.predecessor_id:
        parent = run.predecessor
        previous = read_input(parent, components=('initialization_binding',))
        lineage = inputs.get('lineage', {})
        if (parent.kind != 'DAILY_CHAIN' or parent.status != 'SUCCEEDED' or previous.get('initialization_binding') != binding
                or parent.business_date + timedelta(days=1) != run.business_date
                or lineage.get('run_id') != str(parent.pk) or lineage.get('output_digest') != parent.output_digest):
            raise PublicationUnavailable('phase_native_predecessor_changed')
    elif owner.opening_date + timedelta(days=1) != run.business_date:
        raise PublicationUnavailable('phase_native_opening_date_changed')
    value = dict(initialization=binding, source_id=capture.source_id, capture_digest=capture.revision_digest)
    from django.conf import settings
    if getattr(settings, 'VF_MTA_SCOPED_BOR_OUTPUT_POLICY', None) is not None:
        from mta.presentation.scoped_bor import policy
        value['bor_output_policy'] = policy(view)
    from mta.presentation import scoped_batch_downloads
    batch = scoped_batch_downloads.selected(view)
    if batch is not None:
        value['batch_files'] = batch
    return value


def candidate(view):
    from mta.presentation import scoped_dbm_view
    if isinstance(view,scoped_dbm_view.DbmViewBinding):
        return scoped_dbm_view.candidate(view)
    from django.conf import settings
    from mta.presentation.context import permission_catalogue
    permission_catalogue()
    metadata = view.reference.metadata
    value = {key: metadata[key] for key in ('run_id', 'phase_id', 'phase_digest', 'snapshot_digest',
        'input_digest', 'input_manifest_digest', 'configuration_digest')}
    value.update(schema=SCHEMA, native_digest=digest(native_identity(view)),
        capture_digest=view.bpr.reports.generation.phase.capture_digest,
        permissions_sha256=settings.VF_MTA_PERMISSIONS_SHA256, recipe_digest=recipe_digest(),
        business_date=view.run.business_date.isoformat())
    value['selection_digest'] = digest(value)
    return validate(value)


def _cut(run_id):
    from mta.runtime.models import CalculationRun, RemarkOwner
    from mta.runtime.scoped_actions import revision
    from mta.presentation.ancillary_live import BPR
    return revision(CalculationRun(pk=run_id)), RemarkOwner.objects.get(pk=BPR).next_ordinal


@validated_read
def _selected():
    from django.conf import settings
    from mta.presentation.context import PublicationUnavailable
    from mta.runtime.models import ScopeReadReference
    from mta.presentation import scoped_view
    from django.core.exceptions import ObjectDoesNotExist, ValidationError
    try:
        if any(getattr(settings, field, '') for field in
                ('VF_MTA_SELECTION_FILE', 'VF_MTA_PUBLISHED_RUN', 'VF_MTA_PUBLISHED_DIGEST')):
            raise PublicationUnavailable('phase_full_selection_conflict')
        anchor = read(settings.VF_MTA_PHASE_SELECTION_FILE)
        if anchor != getattr(settings, 'VF_MTA_PHASE_SELECTION', None):
            raise PublicationUnavailable('phase_selection_changed_restart_required')
        cut = _cut(anchor['run_id'])
        from mta.presentation.selected_input import selection
        with selection(anchor['run_id']):
            if anchor['schema']==DBM_SCHEMA:
                from mta.presentation import scoped_dbm_view
                view = scoped_dbm_view.selected(anchor,cut)
                if candidate(view)!=anchor or _cut(anchor['run_id'])!=cut:
                    raise PublicationUnavailable('pre_btr_selection_changed')
                return view
            rows = list(ScopeReadReference.objects.filter(report_generation__run_id=anchor['run_id'],
                action_command__isnull=True,
                report_generation__phase_id=anchor['phase_id'], report_generation__action_revision=cut[0],
                recipe_digest=scoped_view.recipe_digest(), metadata__bpr__remarks__live_highwater=cut[1])[:2])
            if len(rows) != 1: raise PublicationUnavailable('phase_current_reference_missing_or_ambiguous')
            view = scoped_view.bind(rows[0].pk, expected_digest=rows[0].digest)
            if candidate(view) != anchor: raise PublicationUnavailable('phase_selection_identity_changed')
            if _cut(anchor['run_id']) != cut: raise PublicationUnavailable('phase_current_reference_changed')
            return view
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ObjectDoesNotExist, ValidationError) as error:
        if isinstance(error, PublicationUnavailable): raise
        raise PublicationUnavailable('phase_selection_unavailable') from error


def selected():
    return _request_selected()


# Delay Django/model imports until the app registry is ready. The wrapper is
# shared across calls and scoped only to read_request/metadata_operation.
from mta.presentation.request_scope import once_per_request
_request_selected = once_per_request(_selected)
