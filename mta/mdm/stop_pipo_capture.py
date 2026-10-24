"""Freeze approved stops and consume only their owned occurrence generations."""
from collections import Counter
from mta.mdm.stop_pipo_revisions import task_revisions
from mta.runtime.mdm_stop_pipo_models import (
    MdmStopPipoOwner, MdmStopPipoQueue, MdmStopPipoConsumed)
from mta.serialization import digest, storage

FIELDS = ('SKUCode', 'WhCode')


def values(row):
    return {name: row[name] for name in FIELDS}


def capture(source):
    if not MdmStopPipoOwner.objects.filter(source=source).exists():
        return None
    from mta.mdm.stop_pipo_source import require_installed
    owner = require_installed(source)
    native = owner.provenance.get('schema') == 'fresh-production-mdm-opening-owner-v1'
    if owner.last_run is None and not native:
        raise ValueError('StopPIPO requires a successful own predecessor')
    if owner.last_run is not None and owner.last_run.status != 'SUCCEEDED':
        from mta.runtime.prepared_effects import prepared_family_owner
        accepted = prepared_family_owner(source,owner,'stop_pipo')
    else:accepted = None
    anchor = dict(run_id=str(owner.last_run_id) if owner.last_run_id else None,
            output_digest=owner.last_run.output_digest if owner.last_run_id else '',
            queue_digest=owner.closing_queue_digest, generation=owner.generation)
    if native:
        anchor['root_state_digest'] = owner.root_state_digest
    if accepted is not None:anchor['phase_acceptance_digest'] = accepted.digest
    result = storage(dict(source_digest=owner.receipt_digest, anchor=anchor,
        rows=list(MdmStopPipoQueue.objects.filter(source=source).order_by('id')
            .values('id', 'revision', *FIELDS)), task_revisions=task_revisions(source)))
    result['digest'] = digest(result)
    return result


def replace_working_input(snapshot, prior, day, predecessor, *, opening_digest=None):
    if 'stop_pipo' not in snapshot:
        return
    frozen = snapshot['stop_pipo']
    if digest({k: v for k, v in frozen.items() if k != 'digest'}) != frozen['digest']:
        raise ValueError('StopPIPO frozen input digest differs')
    anchor = frozen['anchor']
    native = 'root_state_digest' in anchor
    if (anchor['run_id'] != (str(predecessor.pk) if predecessor else None)
            or anchor['output_digest'] != (predecessor.output_digest if predecessor else '')
            or predecessor is None and (not native or (opening_digest or digest(prior)) != anchor['root_state_digest'])
            or digest(prior['control_aux']['phase_stops']) != anchor['queue_digest']):
        raise ValueError('StopPIPO does not descend from its own bound closing')
    if day.get('control_requests', {}).get('phase_stops'):
        raise ValueError('StopPIPO cannot merge a second external stop feed')
    prior['control_aux']['phase_stops'] = [values(r) for r in frozen['rows']]


def finalize(run, snapshot, output):
    if 'stop_pipo' not in snapshot:
        return
    if output is None:
        raise ValueError('StopPIPO requires produced closing state')
    frozen = snapshot['stop_pipo']
    owner = MdmStopPipoOwner.objects.select_for_update().get(source_id=snapshot['source_id'])
    anchor = frozen['anchor']
    if (owner.receipt_digest != frozen['source_digest']
            or (str(owner.last_run_id) if owner.last_run_id else None) != anchor['run_id']
            or 'root_state_digest' in anchor
            and owner.root_state_digest != anchor['root_state_digest']
            or owner.closing_queue_digest != anchor['queue_digest']
            or owner.generation < anchor['generation']):
        raise ValueError('StopPIPO closing owner changed during execution')
    remaining = storage(output['ClosingState'][0]['control_aux']['phase_stops'])
    if any(set(r) != set(FIELDS) for r in remaining):
        raise ValueError('StopPIPO closing fields differ')
    counts = Counter(digest(r) for r in remaining)
    original = Counter(digest(values(r)) for r in frozen['rows'])
    if any(0 < counts[k] < n for k, n in original.items()):
        raise ValueError('StopPIPO duplicate consumption provenance is ambiguous')
    live = {r.pk: r for r in MdmStopPipoQueue.objects.select_for_update().filter(source=owner.source)}
    for ordinal, before in enumerate(frozen['rows']):
        row = live.get(before['id'])
        if (row is None or row.revision != before['revision']
                or {n: getattr(row, n) for n in FIELDS} != values(before)):
            raise ValueError('Captured StopPIPO occurrence changed or disappeared')
        key = digest(values(before))
        retained = counts[key] > 0
        if retained:
            counts[key] -= 1
        MdmStopPipoConsumed.objects.create(source=owner.source, run=run,
            source_pk=row.pk, ordinal=ordinal, revision=row.revision,
            cleared=not retained, **values(before))
        if not retained:
            row.delete()
    if any(counts.values()):
        raise ValueError('StopPIPO produced an unowned stop input')
    owner.last_run = run
    owner.closing_queue_digest = digest(remaining)
    owner.save(update_fields=['last_run', 'closing_queue_digest'])
