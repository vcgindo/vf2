"""Frozen native input occurrences, own predecessor and atomic queue publication."""
from mta.mdm.phase_controls_source import FIELDS, QUEUES, require_installed
from mta.mdm.phase_controls_revisions import task_revisions
from mta.runtime.mdm_phase_controls_models import (
    MdmPhaseControlsOwner, MdmPhaseOutConsumed, MdmPhaseInNormConsumed)
from mta.serialization import digest, storage

CONSUMED = {'phase_requests': MdmPhaseOutConsumed, 'phase_in_requests': MdmPhaseInNormConsumed}


def native(row, name):
    return {f: row[f] for f in FIELDS[name]}


def capture(source):
    if not MdmPhaseControlsOwner.objects.filter(source=source).exists():
        return None
    owner = require_installed(source)
    native = owner.provenance.get('schema') == 'fresh-production-mdm-opening-owner-v1'
    if owner.last_run is None and not native:
        raise ValueError('Phase controls require a successful own predecessor')
    if owner.last_run is not None and owner.last_run.status != 'SUCCEEDED':
        from mta.runtime.prepared_effects import prepared_family_owner
        accepted = prepared_family_owner(source,owner,'phase_controls')
    else:accepted = None
    anchor = dict(run_id=str(owner.last_run_id) if owner.last_run_id else None,
            output_digest=owner.last_run.output_digest if owner.last_run_id else '',
            queue_digest=owner.closing_queue_digest, generation=owner.generation)
    if native:
        anchor['root_state_digest'] = owner.root_state_digest
    if accepted is not None:anchor['phase_acceptance_digest'] = accepted.digest
    result = storage(dict(source_digest=owner.receipt_digest, anchor=anchor,
        **{name: list(model.objects.filter(source=source).order_by('id')
            .values('id', 'revision', *FIELDS[name])) for name, model in QUEUES.items()},
        task_revisions=task_revisions(source)))
    result['digest'] = digest(result)
    return result


def replace_working_input(snapshot, prior, day, predecessor, *, opening_digest=None):
    if 'phase_controls' not in snapshot:
        return
    frozen = snapshot['phase_controls']
    if digest({k: v for k, v in frozen.items() if k != 'digest'}) != frozen['digest']:
        raise ValueError('Phase controls frozen input digest differs')
    anchor = frozen['anchor']
    native_anchor = 'root_state_digest' in anchor
    if (anchor['run_id'] != (str(predecessor.pk) if predecessor else None)
            or anchor['output_digest'] != (predecessor.output_digest if predecessor else '')
            or predecessor is None and (not native_anchor or (opening_digest or digest(prior)) != anchor['root_state_digest'])
            or digest({n: prior['control_aux'][n] for n in FIELDS}) != anchor['queue_digest']):
        raise ValueError('Phase controls do not descend from their own closing')
    for name in FIELDS:
        if day['control_requests'][name]:
            raise ValueError('Phase controls exclude a second external phase feed')
        # The captured owner includes remaining old rows and later approved
        # additions. Feed it once, not once as carry plus again as daily input.
        prior['control_aux'][name] = []
        day['control_requests'][name] = [native(r, name) for r in frozen[name]]
    day['phase_controls_input_validation'] = True


def finalize(run, snapshot, output):
    if 'phase_controls' not in snapshot:
        return
    if output is None:
        raise ValueError('Phase controls require actual closing state')
    frozen = snapshot['phase_controls']
    from mta.application.accepted_inputs import accepted
    admitted = accepted()
    owner = MdmPhaseControlsOwner.objects.select_for_update().get(source_id=snapshot['source_id'])
    anchor = frozen['anchor']
    if (owner.receipt_digest != frozen['source_digest']
            or (str(owner.last_run_id) if owner.last_run_id else None) != anchor['run_id']
            or 'root_state_digest' in anchor
            and owner.root_state_digest != anchor['root_state_digest']
            or owner.closing_queue_digest != anchor['queue_digest']
            or owner.generation < anchor['generation']):
        raise ValueError('Phase controls closing owner changed during execution')
    closing = output['ClosingState'][0]['control_aux']
    remaining = {name: storage(closing[name]) for name in FIELDS}
    for name, model in QUEUES.items():
        if not admitted and any(set(r) != set(FIELDS[name]) for r in remaining[name]):
            raise ValueError('Phase controls closing fields differ')
        # Native validation trims and DISTINCTs input before canonical clearing.
        # Record every original occurrence, then rebuild only this capture's own
        # produced remaining bag. Never invent which duplicate occurrence won.
        if not admitted:
            normalized = [{f: (v.strip(' ') if isinstance(v, str) else v)
                           for f, v in native(r, name).items()} for r in frozen[name]]
            allowed = {digest(r) for r in normalized}
            if any(r['Approved'] == 1 or digest(r) not in allowed for r in remaining[name]):
                raise ValueError('Phase controls closing contains an unowned or uncleared row')
            if len({digest(r) for r in remaining[name]}) != len(remaining[name]):
                raise ValueError('Phase controls closing retained duplicate native DISTINCT rows')
        live = {r.pk: r for r in model.objects.select_for_update().filter(source=owner.source)}
        for ordinal, before in enumerate(frozen[name]):
            row = live.get(before['id'])
            if (row is None or row.revision != before['revision']
                    or not admitted and storage({f: getattr(row, f) for f in FIELDS[name]}) != native(before, name)):
                raise ValueError('Captured phase control occurrence changed or disappeared')
            CONSUMED[name].objects.create(source=owner.source, run=run, ordinal=ordinal,
                source_pk=row.pk, revision=row.revision, **native(before, name))
            row.delete()
        model.objects.bulk_create([model(source=owner.source, **r) for r in remaining[name]])
    owner.last_run = run
    owner.closing_queue_digest = digest(remaining)
    owner.save(update_fields=['last_run', 'closing_queue_digest'])
