"""Typed current master publication within the existing atomic day boundary."""
from django.db import connection

from mta.mdm.daily_source_install import owners, business_fields
from mta.serialization import digest, storage


def closing_owners(closing):
    """Reuse the exact installation projection, including its BPR copy source."""
    return owners({'case': {'opening': closing}})


def identity(closing):
    return [dict(family=family, model=model.__name__, **partition,
                 fields=[f.name for f in business_fields(model)],
                 rows=len(rows), digest=digest(storage(rows)))
            for family, model, partition, rows, _path in closing_owners(closing)]


def verify_current(source, closing):
    for _family, model, partition, expected, path in closing_owners(closing):
        fields = [f.name for f in business_fields(model)]
        actual = list(model.objects.filter(source=source, **partition)
                      .order_by('ordinal').values('ordinal', *fields))
        ordinals = [row.pop('ordinal') for row in actual]
        if (ordinals != list(range(1, len(expected) + 1))
                or storage(actual) != storage(expected)):
            raise ValueError('MDM current full typed readback differs: ' + path)


def publish(run, capture, closing):
    from mta.mdm.daily_source import APPROVAL_DAY_ARTIFACT_SHA, SCHEMA
    from mta.application.daily_finalization import ACTIVE_POLICY
    from mta.runtime.validation_storage import read_input
    from mta.runtime.mdm_models import MdmSource
    if not connection.in_atomic_block:
        raise ValueError('Current master publication requires the day transaction')
    source = MdmSource.objects.select_for_update().get(pk=capture.source_id)
    if (capture.run_id != run.pk or capture.status != 'CONSUMED' or not capture.nms_active
            or run.kind != 'DAILY_CHAIN' or run.status != 'RUNNING'
            or source.receipt.get('schema') != SCHEMA
            or source.receipt.get('artifact_sha256') != APPROVAL_DAY_ARTIFACT_SHA
            or read_input(run, components=('profile',))['profile'].get(
                'complete_daily', {}).get('policy') != ACTIVE_POLICY):
        raise ValueError('Current master publication requires its active consumed day')
    # Validate the whole typed projection before touching any partition.
    batches = closing_owners(closing)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_current_run',%s,true)", [str(run.pk)])
    try:
        for _family, model, partition, rows, _path in batches:
            model.objects.filter(source=source, **partition).delete()
            model.objects.bulk_create([model(source=source, ordinal=i, **partition, **row)
                for i, row in enumerate(rows, 1)], batch_size=500)
        verify_current(source, closing)
    finally:
        # A database error has already marked the enclosing atomic block for
        # rollback. Do not mask that error with a cleanup query on a broken
        # transaction; rollback also restores its transaction-local setting.
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.mdm_current_run','',true)")


def verify_published(run, source):
    """Stable per-run identity plus a separate full live-leaf consistency check."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.services import read_outputs
    captures = list(MdmDailyInputCapture.objects.filter(source=source, status='CONSUMED',
                    run__status='SUCCEEDED').select_related('run'))
    by_id = {c.run_id: c for c in captures}
    if run.pk not in by_id or any(not c.nms_active or c.run.kind != 'DAILY_CHAIN' for c in captures):
        raise ValueError('Active current owner chain is unavailable')
    parent_ids = [c.run.predecessor_id for c in captures if c.run.predecessor_id is not None]
    leaves = set(by_id) - set(parent_ids)
    if len(leaves) != 1 or len(parent_ids) != len(set(parent_ids)):
        raise ValueError('Active current owner chain is branched')
    leaf_id = next(iter(leaves)); walk = leaf_id; visited = set()
    while walk is not None:
        if walk in visited or walk not in by_id:
            raise ValueError('Active current owner chain is disconnected')
        visited.add(walk)
        walk = by_id[walk].run.predecessor_id
    if visited != set(by_id):
        raise ValueError('Active current owner chain is disconnected')
    leaf = by_id[leaf_id].run
    closing = read_outputs(leaf)['ClosingState'][0]
    verify_current(source, closing)
    # Never return the changing leaf identity as part of an old receipt.
    if leaf.pk != run.pk:
        closing = read_outputs(run)['ClosingState'][0]
    return identity(closing)
