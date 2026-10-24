"""Receipt-bound live ForceNormChange input and atomic closing reconciliation."""
from collections import Counter
from copy import deepcopy
from zoneinfo import ZoneInfo
from django.conf import settings

from mta.serialization import digest, storage
from mta.runtime.mdm_force_models import (MdmForceOwner, MdmForceQueue,
    MdmForceConsumed, MdmForceUploadLog)
from mta.mdm.force_revisions import task_revisions

FIELDS = ('SKUCode', 'WhCode', 'NewNorm', 'Approved', 'RequestedBy')
LOG_FIELDS = ('SKUCode', 'WHCode', 'OldNorm', 'NewNorm', 'Approved',
              'RequestedBy', 'ActionTimeStamp', 'ActionId')


def native_log(row):
    result = dict(row)
    stamp = result['ActionTimeStamp']
    if not isinstance(stamp, str):
        if stamp.tzinfo is not None:
            stamp = stamp.astimezone(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).replace(tzinfo=None)
        result['ActionTimeStamp'] = stamp.isoformat()
    return storage(result)


def native(row):
    return {name: row[name] for name in FIELDS}


def capture(source):
    owner = MdmForceOwner.objects.select_related('last_run').filter(source=source).first()
    if owner is None:
        return None
    from mta.mdm.force_source import require_installed
    require_installed(source)
    prior = owner.last_run
    accepted = None
    if prior is not None and prior.status != 'SUCCEEDED':
        from mta.runtime.prepared_effects import prepared_family_owner
        accepted = prepared_family_owner(source,owner,'force')
    result = dict(source_digest=owner.receipt_digest,
        anchor=dict(run_id=str(prior.pk) if prior else None,
                    output_digest=prior.output_digest if prior else '',
                    queue_digest=owner.closing_digest,
                    root_state_digest=owner.root_state_digest,
                    log_digest=owner.closing_log_digest,
                    generation=owner.generation),
        rows=list(MdmForceQueue.objects.filter(source=source).order_by('id')
                  .values('id', 'revision', *FIELDS)),
        upload_log=[native_log(row) for row in MdmForceUploadLog.objects
                    .filter(source=source).order_by('id').values('id', *LOG_FIELDS)],
        task_revisions=task_revisions(source))
    if accepted is not None:result['anchor']['phase_acceptance_digest'] = accepted.digest
    result['digest'] = digest(result)
    return storage(result)


def replace_working_input(snapshot, prior, day, predecessor):
    """Reconstruct one live table; never append survivors a second time."""
    apply = prepare_working_input(snapshot, prior, day, predecessor)
    if apply is not None:
        apply()


def prepare_working_input(snapshot, prior, day, predecessor, *, opening_digest=None):
    """Validate the unmodified opening before any combined family overlay."""
    if 'force' not in snapshot:
        return
    force = snapshot['force']
    if digest({k: v for k, v in force.items() if k != 'digest'}) != force['digest']:
        raise ValueError('Force capture identity differs')
    anchor = force['anchor']
    expected_id = str(predecessor.pk) if predecessor else None
    expected_digest = predecessor.output_digest if predecessor else ''
    if (anchor['run_id'] != expected_id or anchor['output_digest'] != expected_digest
            or predecessor is None and (digest(prior) if opening_digest is None else opening_digest)
                != anchor['root_state_digest']
            or digest(prior['importer']['ForceNormChange']) != anchor['queue_digest']
            or digest(prior['controls']['upload_log']) != anchor['log_digest']):
        raise ValueError('Force source does not descend from selected opening/predecessor')
    if day['new_force_requests']:
        raise ValueError('Captured ForceNormChange excludes a second external request feed')
    def apply():
        from mta.mdm.force_source import apply_working_fixture_setting
        apply_working_fixture_setting(snapshot, prior)
        # Only this calculation copy changes; original opening and frozen rows stay.
        prior['importer']['ForceNormChange'] = [native(row) for row in force['rows']]
        prior['controls']['upload_log'] = [
            {('WhCode' if name == 'WHCode' else name): row[name] for name in LOG_FIELDS}
            for row in force['upload_log']]
    return apply


def finalize(run, snapshot, output):
    if 'force' not in snapshot:
        return
    if output is None:
        raise ValueError('Force publication requires actual closing output')
    frozen = snapshot['force']
    owner = MdmForceOwner.objects.select_for_update().get(source_id=snapshot['source_id'])
    anchor = frozen['anchor']
    if (owner.receipt_digest != frozen['source_digest']
            or (str(owner.last_run_id) if owner.last_run_id else None) != anchor['run_id']
            or owner.closing_digest != anchor['queue_digest']
            or owner.root_state_digest != anchor['root_state_digest']
            or owner.closing_log_digest != anchor['log_digest']
            or owner.generation < anchor['generation']):
        raise ValueError('Force closing owner changed before publication')
    closing = storage(output['ClosingState'][0]['importer']['ForceNormChange'])
    logs = storage(output['ClosingState'][0]['controls']['upload_log'])
    if len(logs) != len(frozen['upload_log']):
        raise ValueError('Force upload-log terminal occurrence roster differs')
    for before, after in zip(frozen['upload_log'], logs):
        expected = {('WhCode' if name == 'WHCode' else name): before[name]
                    for name in LOG_FIELDS}
        if (set(after) != set(expected)
                or any(after[name] != value for name, value in expected.items() if name != 'OldNorm')):
            raise ValueError('Force upload log changed outside its canonical OldNorm writer')
        current = MdmForceUploadLog.objects.select_for_update().get(
            source_id=snapshot['source_id'], pk=before['id'])
        if native_log({name: getattr(current, name) for name in LOG_FIELDS}) != {
                name: before[name] for name in LOG_FIELDS}:
            raise ValueError('Frozen force upload-log occurrence changed')
        current.OldNorm = after['OldNorm']
        current.save(update_fields=['OldNorm'])
    if any(set(row) != set(FIELDS) for row in closing):
        raise ValueError('Force terminal native field roster differs')
    # Canonical force clear is a stable filter of occurrences. Match exact native
    # rows, never SKU/location deduplication or a replacement clear predicate.
    counts = Counter(digest(row) for row in closing)
    original = Counter(digest(native(row)) for row in frozen['rows'])
    for key, number in original.items():
        if 0 < counts[key] < number:
            raise ValueError('Force terminal duplicate occurrence provenance is ambiguous')
    live = {row.pk: row for row in MdmForceQueue.objects.select_for_update()
            .filter(source_id=snapshot['source_id']).order_by('id')}
    frozen_by_id = {row['id']: row for row in frozen['rows']}
    later_keys = set()
    for pk, current in live.items():
        captured = frozen_by_id.get(pk)
        if captured is None or current.revision > captured['revision']:
            later_keys.add((current.SKUCode.rstrip(' ').lower() if current.SKUCode is not None else None,
                            current.WhCode.rstrip(' ').lower() if current.WhCode is not None else None))
    for ordinal, row in enumerate(frozen['rows']):
        current = live.get(row['id'])
        if current is None or current.revision < row['revision']:
            raise ValueError('Captured force occurrence disappeared or regressed')
        values = native(row)
        current_values = {name: getattr(current, name) for name in FIELDS}
        if any(current_values[name] != values[name] for name in FIELDS
               if current.revision == row['revision'] or name != 'NewNorm'):
            raise ValueError('Captured force occurrence changed outside its native scalar writer')
        key = digest(values)
        retained = counts[key] > 0
        if retained:
            counts[key] -= 1
        MdmForceConsumed.objects.create(source_id=snapshot['source_id'], run=run,
            source_pk=current.pk, revision=row['revision'], ordinal=ordinal,
            cleared=not retained, **values)
        if current.revision == row['revision'] and not retained:
            current.delete()
    # The existing importer may produce auto-force requests before the force
    # stage. A later UI generation for the same key supersedes that stale
    # terminal occurrence. Frozen duplicates remain occurrence-counted above.
    for row in closing:
        key = digest(row)
        if counts[key]:
            identity = (row['SKUCode'].rstrip(' ').lower() if row['SKUCode'] is not None else None,
                        row['WhCode'].rstrip(' ').lower() if row['WhCode'] is not None else None)
            if identity not in later_keys:
                MdmForceQueue.objects.create(source_id=snapshot['source_id'], **row)
            counts[key] -= 1
    owner.last_run = run
    owner.closing_digest = digest(closing)
    owner.closing_log_digest = digest(logs)
    owner.save(update_fields=['last_run', 'closing_digest', 'closing_log_digest'])
