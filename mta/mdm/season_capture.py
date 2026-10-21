"""Frozen seasonal inputs and atomic reconciliation at execute_day."""
from collections import Counter
from copy import deepcopy
from mta.application.r1_seasonality import REQUEST_FIELDS, SEASON_FIELDS
from mta.mdm.season_revisions import task_revisions
from mta.mdm.task_reads import sql_key
from mta.runtime.mdm_season_models import (MdmSeasonOwner, MdmSeasonQueue,
                                         MdmSeasonCurrent, MdmSeasonConsumed)
from mta.serialization import digest, storage


def native(row, names):
    return {n: row[n] for n in names}


def pair(row):
    return sql_key(row['SKUCode']), sql_key(row['WhCode'])


def capture(source):
    owner = MdmSeasonOwner.objects.select_related('last_run').filter(source=source).first()
    if owner is None:
        return None
    from mta.mdm.season_source import require_installed
    require_installed(source)
    prior = owner.last_run
    if prior is not None and prior.status != 'SUCCEEDED':
        raise ValueError('Seasonality owner requires a successful predecessor')
    result = storage(dict(source_digest=owner.receipt_digest,
        anchor=dict(run_id=str(prior.pk) if prior else None,
            output_digest=prior.output_digest if prior else '', root_state_digest=owner.root_state_digest,
            queue_digest=owner.closing_queue_digest, current_digest=owner.closing_current_digest,
            generation=owner.generation),
        rows=list(MdmSeasonQueue.objects.filter(source=source).order_by('id').values('id', 'revision', *REQUEST_FIELDS)),
        current=list(MdmSeasonCurrent.objects.filter(source=source).order_by('ordinal')
            .values('id', 'revision', 'ordinal', *SEASON_FIELDS)),
        task_revisions=task_revisions(source)))
    result['digest'] = digest(result)
    return result


def replace_working_input(snapshot, prior, day, predecessor):
    apply = prepare_working_input(snapshot, prior, day, predecessor)
    if apply is not None:
        apply()


def prepare_working_input(snapshot, prior, day, predecessor, *, opening_digest=None):
    if 'season' not in snapshot:
        return
    frozen = snapshot['season']
    if digest({k: v for k, v in frozen.items() if k != 'digest'}) != frozen['digest']:
        raise ValueError('Seasonality frozen input identity differs')
    a = frozen['anchor']
    if (a['run_id'] != (str(predecessor.pk) if predecessor else None)
            or a['output_digest'] != (predecessor.output_digest if predecessor else '')
            or predecessor is None and (digest(prior) if opening_digest is None else opening_digest)
                != a['root_state_digest']
            or digest(prior['control_aux']['season_requests']) != a['queue_digest']
            or digest(prior['dbm']['Seasonality']) != a['current_digest']):
        raise ValueError('Seasonality does not descend from its selected opening/predecessor')
    if day.get('control_requests', {}).get('season_requests'):
        raise ValueError('Seasonality capture excludes a second external request feed')
    def apply():
        prior['control_aux']['season_requests'] = [native(r, REQUEST_FIELDS) for r in frozen['rows']]
        prior['dbm']['Seasonality'] = [native(r, SEASON_FIELDS) for r in frozen['current']]
        prior['controls']['seasonality'] = deepcopy(prior['dbm']['Seasonality'])
        # No old accepted calculation is silently reinterpreted.
        day['seasonality_input_validation'] = True
    return apply


def finalize(run, snapshot, output):
    if 'season' not in snapshot:
        return
    if output is None:
        raise ValueError('Seasonality publication requires actual closing output')
    frozen = snapshot['season']
    owner = MdmSeasonOwner.objects.select_for_update().get(source_id=snapshot['source_id'])
    a = frozen['anchor']
    if (owner.receipt_digest != frozen['source_digest']
            or (str(owner.last_run_id) if owner.last_run_id else None) != a['run_id']
            or owner.root_state_digest != a['root_state_digest']
            or owner.closing_queue_digest != a['queue_digest']
            or owner.closing_current_digest != a['current_digest']
            or owner.generation < a['generation']):
        raise ValueError('Seasonality closing owner changed before publication')
    # Only these two owned populations participate in seasonal publication.
    # Converting the entire closing graph duplicates unrelated daily/history rows.
    closing = output['ClosingState'][0]
    queue = storage(closing['control_aux']['season_requests'])
    current = storage(closing['dbm']['Seasonality'])
    if any(set(r) != set(REQUEST_FIELDS) for r in queue) or any(set(r) != set(SEASON_FIELDS) for r in current):
        raise ValueError('Seasonality terminal field roster differs')
    live = {r.pk: r for r in MdmSeasonQueue.objects.select_for_update().filter(source=owner.source)}
    counts = Counter(digest(native(r, REQUEST_FIELDS)) for r in queue)
    original = Counter(digest(native(r, REQUEST_FIELDS)) for r in frozen['rows'])
    if any(0 < counts[k] < n for k, n in original.items()):
        raise ValueError('Seasonality duplicate consumption provenance is ambiguous')
    for ordinal, before in enumerate(frozen['rows']):
        row = live.get(before['id'])
        if row is None or row.revision < before['revision']:
            raise ValueError('Captured seasonal input disappeared or regressed')
        expected = native(before, REQUEST_FIELDS)
        if row.revision == before['revision'] and storage({n: getattr(row, n) for n in REQUEST_FIELDS}) != expected:
            raise ValueError('Captured seasonal input changed without revision')
        key = digest(expected)
        retained = counts[key] > 0
        if retained:
            counts[key] -= 1
        MdmSeasonConsumed.objects.create(source=owner.source, run=run, ordinal=ordinal,
            source_pk=row.pk, revision=before['revision'], cleared=not retained, **expected)
        if not retained and row.revision == before['revision']:
            row.delete()
    if any(counts.values()):
        raise ValueError('Seasonality collector produced an unowned importer input')
    live_current = list(MdmSeasonCurrent.objects.select_for_update().filter(source=owner.source).order_by('ordinal'))
    captured = {r['id']: r for r in frozen['current']}
    if set(captured) != {r.pk for r in live_current}:
        raise ValueError('Seasonality current occurrence roster changed before publication')
    later = {}
    for row in live_current:
        before = captured[row.pk]
        actual = storage({n: getattr(row, n) for n in SEASON_FIELDS})
        if row.revision < before['revision'] or any(actual[n] != before[n] for n in SEASON_FIELDS
                if row.revision == before['revision'] or n not in ('Status', 'Comment')):
            raise ValueError('Seasonality current changed outside its status writer')
        if row.revision > before['revision']:
            key = pair(actual)
            values = (actual['Status'], actual['Comment'])
            if key in later and values != later[key]:
                raise ValueError('Seasonality later duplicate status is incomparable')
            later[key] = values
    # A late status write targets the captured live generation. Never transfer
    # it to a possible ADD replacement. Publication failure rolls back all writes
    # here, preserving the old owner and every later decision for explicit retry.
    candidates = {pair(r) for r in frozen['rows'] if r['Approved'] is True}
    if candidates.intersection(later):
        raise ValueError('Seasonality late status conflicts with captured ADD generation')
    if set(later) - {pair(r) for r in current}:
        raise ValueError('Seasonality late status target disappeared')
    MdmSeasonCurrent.objects.filter(source=owner.source).delete()
    rows = []
    for ordinal, row in enumerate(current, 1):
        values = dict(row)
        override = later.get(pair(row))
        if override:
            values.update(Status=override[0], Comment=override[1])
        rows.append(MdmSeasonCurrent(source=owner.source, ordinal=ordinal, **values))
    MdmSeasonCurrent.objects.bulk_create(rows)
    owner.last_run = run
    owner.closing_queue_digest = digest(queue)
    owner.closing_current_digest = digest(current)
    owner.save(update_fields=['last_run', 'closing_queue_digest', 'closing_current_digest'])
