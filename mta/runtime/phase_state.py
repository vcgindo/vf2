"""Typed live-out snapshots before BPR, after BPR and before BTR.

A sealed snapshot is calculation storage, not phase business acceptance, file
readiness, selection or a successful predecessor. The scoped transaction owner
must commit its mapped effects and acceptance separately before exposing it.
"""
import inspect

from django.db import connection, transaction
from mta.serialization import digest
from mta.runtime import relational_state as typed
from mta.runtime import phase_state_layout as layout, phase_state_contract as contract
from mta.runtime.phase_state_layout import SCHEMA, REGISTRY, TABLES, PRIOR_REFS, DAY_REFS, OPTIONAL_DAY_REFS


def recipe_digest():
    from mta.temporal import chain, day_phases
    from mta.runtime import phase_image_storage, inherited_history_image, transition_history_image
    return digest(dict(codec=inspect.getsource(inspect.getmodule(recipe_digest)),
        logical=inspect.getsource(layout), contract=inspect.getsource(contract),
        physical=inspect.getsource(phase_image_storage),
        inherited_history=inspect.getsource(inherited_history_image),
        history_transition=inspect.getsource(transition_history_image),
        chain=inspect.getsource(chain), phases=inspect.getsource(day_phases), registry=REGISTRY))


_references = layout._references
_table = layout._table


def _write_rows(run, path, table, rows, *, description=None):
    """Same scalar conversion/ordinal transport as daily storage, own namespace."""
    columns = {name.casefold(): (name, kind) for name, kind in REGISTRY[table]}
    meta, fields, native = (typed.describe_rows(rows, columns, path)
                            if description is None else description)
    meta['table'] = table
    if rows:
        query = ('INSERT INTO '+typed.table_sql(table)+
            ' (vf_run_id,vf_image,vf_ordinal,'+
            ','.join(typed.quote(name) for name, _ in native)+') VALUES ('+
            ','.join(['%s']*(len(native)+3))+')')
        records = ((run.pk, path, ordinal, *[
            typed.db_value(row[field], kind)
            for field, (_, kind) in zip(fields, native)])
            for ordinal, row in enumerate(rows))
        if connection.vendor == 'postgresql' and len(rows) >= 500:
            typed.copy_rows(typed.table_sql(table),
                ['vf_run_id', 'vf_image', 'vf_ordinal', *[name for name, _ in native]], records)
        else:
            typed.bulk(query, records)
    # The accepted phase is written once; diagnostics own complete readback.
    return meta


def encode(phase, sources, *, row_writer, export_writer, parent_manifest=None,
           _described_writer=None, _prior_writer=None, _history_writer=None):
    from mta.runtime.phase_image_storage import ImageWriter, FORMAT
    writer = ImageWriter(lambda path, table, rows, description:
        row_writer(path, table, rows) if _described_writer is None else
        _described_writer(path, table, rows, description), parent_manifest=parent_manifest,
        prior_writer=_prior_writer,history_writer=_history_writer)
    manifest = layout.encode(phase, sources, image_writer=writer, export_writer=export_writer)
    if phase.context.history_changes is None:
        # An old in-flight phase has no producer delta. Continue its original
        # logical layout and full-image storage; never invent provenance.
        manifest.update(phase_contract=dict(schema=contract.SCHEMA,digest=contract.LEGACY_LOGICAL),
            storage_format='fresh-phase-image-references-v4')
    else:
        manifest.update(phase_contract=contract.describe(), storage_format=FORMAT)
    return manifest


def decode(manifest, **kwargs):
    return layout.decode(manifest, **kwargs)


def _decode_accepted(manifest, **kwargs):
    return layout._decode_accepted(manifest, **kwargs)


def save(run, phase, sources, *, parent=None, acceptance=None):
    """Seal typed storage atomically. Does not expose/accept a scope command."""
    from mta.runtime.models import CalculationRun, DailyPhaseSnapshot
    if transaction.get_autocommit():
        raise ValueError('Phase snapshot requires its owning transaction')
    with transaction.atomic():
        return _save(run, phase, sources, parent=parent, acceptance=acceptance)


def _save(run, phase, sources, *, parent, acceptance):
    from mta.runtime.models import CalculationRun, DailyPhaseSnapshot
    owner = CalculationRun.objects.select_for_update().get(pk=run.pk)
    if (owner.status != 'RUNNING' or owner.kind != 'DAILY_CHAIN'
            or owner.output_digest or owner.checkpoints.exists()):
        raise ValueError('Phase snapshot requires its uncompleted daily owner')
    if parent is not None:
        parent = DailyPhaseSnapshot.objects.get(pk=parent.pk)
    if parent is not None and (parent.run_id != owner.pk or parent.phase not in ('PRE_BPR', 'BPR')
            or parent.state_digest != digest(parent.manifest)
            or not contract.compatible(parent)):
        raise ValueError('Continuation parent snapshot differs')
    from mta.temporal.day_phases import PreparedDay, BprDay, DbmDay
    if type(phase) is PreparedDay:
        valid_parent = parent is None
    elif type(phase) is BprDay:
        valid_parent = parent is None or parent.phase == 'PRE_BPR'
    elif type(phase) is DbmDay:
        valid_parent = parent is not None and parent.phase == 'BPR'
    else:
        valid_parent = False
    if (phase.context.identity != str(owner.pk)
            or phase.context.today != owner.business_date.isoformat()
            or not valid_parent):
        raise ValueError('Phase snapshot run/date/parent differs')
    from mta.runtime.inherited_history_image import ReferenceWriter
    from mta.runtime.transition_history_image import ReferenceWriter as TransitionWriter
    manifest = encode(phase, sources,
        row_writer=lambda path, table, values: _write_rows(owner, path, table, values),
        _described_writer=lambda path, table, values, description:
            _write_rows(owner, path, table, values, description=description),
        export_writer=lambda path, values: typed.save_export(owner, path, values),
        parent_manifest=parent.manifest if parent else None,
        _prior_writer=ReferenceWriter(owner),
        _history_writer=TransitionWriter(owner,phase.context.history_changes))
    if parent is not None:
        if manifest['references'] != parent.manifest['references']:
            raise ValueError('Continuation parent dependency revision differs')
        if parent.phase == 'BPR' and consumer_identity(manifest) != consumer_identity(parent.manifest):
            raise ValueError('Continuation calculation consumers changed after BPR')
    return DailyPhaseSnapshot.objects.create(run=owner, phase=manifest['phase'], parent=parent,
        acceptance=acceptance,
        input_digest=owner.input_digest, recipe_digest=recipe_digest(),
        state_digest=digest(manifest), manifest=manifest)


def read(snapshot, **references):
    """Read the sealed snapshot; caller still owns action/effect/claim checks."""
    from mta.runtime.models import DailyPhaseSnapshot
    snapshot = DailyPhaseSnapshot.objects.select_related('run').get(pk=snapshot.pk)
    if (snapshot.input_digest != snapshot.run.input_digest
            or not contract.compatible(snapshot)
            or snapshot.state_digest != digest(snapshot.manifest)):
        raise ValueError('Continuation snapshot input/code/storage identity differs')
    from mta.runtime.accepted_state_read import load_accepted_image, load_accepted_export
    return _decode_accepted(snapshot.manifest, **references,
        row_reader=lambda item: load_accepted_image(snapshot.run, item, table_registry=REGISTRY),
        export_reader=lambda item: load_accepted_export(snapshot.run, item))


def consumer_identity(manifest):
    return layout.consumer_identity(manifest)
