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


def _current_recipe_digest():
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
        scoped_batch_files, scoped_batch_downloads, scoped_dbm_stop, scoped_dbm_view)
    return digest({m.__name__: inspect.getsource(m) for m in
        (inspect.getmodule(recipe_digest), phase_selection, scoped_api, scoped_overview, scoped_rrr, rrr_prepared_sql,
         views, bpr_prepared, bpr_response, bpr_export, rrr_export, rrr_types, planning_git_sql,
         daily_git_custom, daily_git_read, planning_chart_sql, planning_custom_sql, bpr_remarks, scoped_remark_writer,
         scoped_dbm, dbm, dbm_filters, scoped_action_writer, scoped_history, scoped_artifacts,
         scoped_btr, btr_sql, btr, btr_display, btr_export, buffer_trends_sql, mdm_views, season_current,
         scoped_logistics, logistics_read, scoped_bor, bor_sql, boroa_sql,
         bor_preparation, boroa_preparation, native_report_colours,
         production_bor_contract, production_output_policy, daily_rrr_read,
         scoped_batch_files, scoped_batch_downloads, scoped_dbm_stop, scoped_dbm_view)})


def recipe_digest():
    """The exact59ca6cd3 selection contract, with finite dependency pin checks."""
    from mta.presentation.runtime_report_view import legacy_selection_recipe
    return legacy_selection_recipe()


def publication_recipe_digest():
    from mta.presentation.legacy_scope_read_compatibility import verify,POSTBPR_SELECTION_RECIPE
    verify()
    return POSTBPR_SELECTION_RECIPE


def registered_recipe_digest(configuration=None):
    from mta.presentation import registered_report_view
    from mta.presentation.registered_read_compatibility import selection_recipe, SELECTION_RECIPE
    if registered_report_view.production_configuration(configuration):
        # V1 phase-anchor format; original run/phase/permission and reference
        # seals still decide whether this selection may actually be served.
        return SELECTION_RECIPE
    observed = digest(dict(selection=_current_recipe_digest(),registered=registered_report_view.recipe_digest()))
    return selection_recipe(observed)


def recipe_for_run(run):
    from mta.presentation import registered_report_view
    if registered_report_view.applicable_run(run):
        configuration, _request_digest = registered_report_view.configuration(run)
        return registered_recipe_digest(configuration)
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import PUBLICATION_SCHEMA
    request=read_input(run,components=('scope_request',)).get('scope_request',{})
    if request.get('schema')==PUBLICATION_SCHEMA:
        from mta.presentation.runtime_report_view import configuration
        configuration(run)
        return publication_recipe_digest()
    return recipe_digest()


def native_identity(view):
    """Initialized source proof for an accepted phase, without a terminal fiction."""
    from datetime import timedelta
    from mta.presentation.context import PublicationUnavailable
    from mta.presentation.native_publication import require_mode
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    from mta.runtime.models import ProductionInitialization, MdmDailyInputCapture
    from mta.runtime.input_reader import read_input
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
        ('initialization_binding', 'lineage', 'profile','execution_settings'))
    from mta.runtime.capture_preparation import effective_configuration
    body=run.production_manifest.get('ingestion_preparation')
    configuration=effective_configuration(body) if body else owner.configuration_digest
    if (inputs.get('initialization_binding') != binding
            or view.bpr.reports.generation.configuration_digest != configuration):
        raise PublicationUnavailable('phase_native_initialization_changed')
    if not referenced:
        from mta.runtime.execution_settings import require_snapshot
        try:require_snapshot(owner,inputs.get('profile'),inputs.get('execution_settings'),run.business_date)
        except ValueError as error:
            raise PublicationUnavailable('phase_native_initialization_changed') from error
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
    from mta.presentation import runtime_report_view
    selected_recipe=recipe_for_run(view.run)
    value.update(schema=SCHEMA, native_digest=digest(native_identity(view)),
        capture_digest=view.bpr.reports.generation.phase.capture_digest,
        permissions_sha256=settings.VF_MTA_PERMISSIONS_SHA256, recipe_digest=selected_recipe,
        business_date=view.run.business_date.isoformat())
    value['selection_digest'] = digest(value)
    return validate(value)


def _cut(run_id):
    from mta.runtime.models import CalculationRun, RemarkOwner
    from mta.runtime.scoped_actions import revision
    from mta.presentation.ancillary_live import BPR
    return revision(CalculationRun(pk=run_id)), RemarkOwner.objects.get(pk=BPR).next_ordinal


@validated_read
def _selected(*, prepared=None):
    from django.conf import settings
    from mta.presentation.context import PublicationUnavailable
    from mta.runtime.models import ScopeReadReference
    from mta.presentation import scoped_view
    from django.core.exceptions import ObjectDoesNotExist, ValidationError
    try:
        if prepared is not None:
            from django.db import connection
            from mta.presentation.request_scope import in_validation_reads
            if (not connection.in_atomic_block or not in_validation_reads()
                    or type(prepared) is not scoped_view.ViewBinding
                    or prepared.reference._state.adding or prepared.reference._state.db != 'default'):
                raise PublicationUnavailable('phase_prepared_reference_requires_owner_transaction')
        if any(getattr(settings, field, '') for field in
                ('VF_MTA_SELECTION_FILE', 'VF_MTA_PUBLISHED_RUN', 'VF_MTA_PUBLISHED_DIGEST')):
            raise PublicationUnavailable('phase_full_selection_conflict')
        anchor = read(settings.VF_MTA_PHASE_SELECTION_FILE)
        if anchor != getattr(settings, 'VF_MTA_PHASE_SELECTION', None):
            raise PublicationUnavailable('phase_selection_changed_restart_required')
        cut = _cut(anchor['run_id'])
        if anchor['schema']==DBM_SCHEMA:
            if prepared is not None:
                raise PublicationUnavailable('phase_prepared_reference_scope_differs')
            from mta.presentation import scoped_dbm_view
            view = scoped_dbm_view.selected(anchor,cut)
            if candidate(view)!=anchor or _cut(anchor['run_id'])!=cut:
                raise PublicationUnavailable('pre_btr_selection_changed')
            return view
        from mta.runtime.models import CalculationRun
        from mta.runtime.input_reader import read_input
        from mta.runtime.production_scope import PUBLICATION_SCHEMA
        from mta.presentation import runtime_report_view
        run=CalculationRun.objects.get(pk=anchor['run_id'])
        publication=(read_input(run,components=('scope_request',)).get('scope_request',{}).get('schema')
            == PUBLICATION_SCHEMA)
        expected_selection_recipe=recipe_for_run(run)
        if anchor['recipe_digest']!=expected_selection_recipe:
            raise PublicationUnavailable('phase_selection_recipe_differs')
        reference_recipe=(runtime_report_view.recipe_digest() if publication else
            scoped_view.recipe_for_configuration(scoped_view._configuration(run)[0]))
        rows = list(ScopeReadReference.objects.filter(report_generation__run_id=anchor['run_id'],
            action_command__isnull=True,
            report_generation__phase_id=anchor['phase_id'], report_generation__action_revision=cut[0],
            recipe_digest=reference_recipe, metadata__bpr__remarks__live_highwater=cut[1])[:2])
        if len(rows) != 1: raise PublicationUnavailable('phase_current_reference_missing_or_ambiguous')
        if prepared is None:
            view = scoped_view.bind(rows[0].pk, expected_digest=rows[0].digest)
        else:
            # prepare() already read back and admitted this immutable graph in
            # the same locked action transaction. Recheck the live selection,
            # unique current row and every reference field; do not rebuild the
            # admitted dependency graph a second time merely to discard it.
            if any(getattr(rows[0], field.attname) != getattr(prepared.reference, field.attname)
                   for field in ScopeReadReference._meta.concrete_fields):
                raise PublicationUnavailable('phase_prepared_reference_not_current')
            view = prepared
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
