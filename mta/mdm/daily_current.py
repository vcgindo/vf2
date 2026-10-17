"""Typed current master publication within the existing atomic day boundary."""
from copy import deepcopy
from django.db import connection

from mta.mdm.master_owners import owner_batches, business_fields
from mta.serialization import digest, storage


def closing_owners(closing, *, version=None):
    """Reuse the exact installation projection, including its BPR copy source."""
    batches = owner_batches(closing)
    if version is not None:
        from mta.mdm.location_projection import additional_owners, VERSION
        if version != VERSION:
            raise ValueError('Unsupported closing projection version')
        batches += additional_owners(closing)[0]
    return batches


def identity(closing, *, version=None):
    return [dict(family=family, model=model.__name__, **partition,
                 fields=[f.name for f in business_fields(model)],
                 rows=len(rows), digest=digest(storage(rows)))
            for family, model, partition, rows, _path in closing_owners(closing, version=version)]


def verify_current(source, closing, *, version=None):
    for _family, model, partition, expected, path in closing_owners(closing, version=version):
        fields = [f.name for f in business_fields(model)]
        actual = list(model.objects.filter(source=source, **partition)
                      .order_by('ordinal').values('ordinal', *fields))
        ordinals = [row.pop('ordinal') for row in actual]
        if (ordinals != list(range(1, len(expected) + 1))
                or storage(actual) != storage(expected)):
            raise ValueError('MDM current full typed readback differs: ' + path)


def publish(run, capture, closing):
    from mta.mdm.daily_source import APPROVAL_DAY_ARTIFACT_SHA, SCHEMA
    from mta.application.daily_finalization import ACTIVE_POLICY, POLICY, finish
    from mta.runtime.input_reader import read_input
    from mta.runtime.mdm_models import MdmSource
    if not connection.in_atomic_block:
        raise ValueError('Current master publication requires the day transaction')
    source = MdmSource.objects.select_for_update().get(pk=capture.source_id)
    native = source.receipt.get('schema') == 'fresh-production-mdm-source-v1'
    if native:
        from mta.mdm.production_families import require_binding
        require_binding(source)
    policy = read_input(run, components=('profile',))['profile'].get('complete_daily', {}).get('policy')
    if (capture.run_id != run.pk or capture.status != 'CONSUMED'
            or run.kind != 'DAILY_CHAIN' or run.status != 'RUNNING'
            or policy not in (ACTIVE_POLICY, POLICY)
            or capture.nms_active != (policy == ACTIVE_POLICY)
            or not native and (source.receipt.get('schema') != SCHEMA
                or source.receipt.get('artifact_sha256') != APPROVAL_DAY_ARTIFACT_SHA
                or policy != ACTIVE_POLICY)):
        raise ValueError('Current master publication requires its mode-bound consumed day')
    if finish(deepcopy(closing['complete']), closing['importer_settings'],
              run.business_date.isoformat(), policy=policy) != closing['importer_settings']:
        raise ValueError('Current master publication completion differs')
    # Validate the whole typed projection before touching any partition.
    version = None
    receipt = None
    if native:
        from mta.mdm.location_transition import run_identity, admit, capture_identity
        from mta.mdm.location_projection import VERSION, additional_owners
        from mta.runtime.mdm_projection_models import MdmClosingProjectionReceipt
        code_identity = run_identity(run, source)
        if code_identity['version'] != VERSION:
            raise ValueError('New native publication requires the corrected projection')
        admit(source, run.business_date, run.predecessor)
        version = VERSION
    batches = closing_owners(closing, version=version)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_current_run',%s,true)", [str(run.pk)])
    try:
        if native:
            receipt = MdmClosingProjectionReceipt.objects.create(run=run,
                capture_digest=capture_identity(capture), **code_identity)
        for _family, model, partition, rows, _path in batches:
            model.objects.filter(source=source, **partition).delete()
            model.objects.bulk_create([model(source=source, ordinal=i, **partition, **row)
                for i, row in enumerate(rows, 1)], batch_size=500)
        verify_current(source, closing, version=version)
        if receipt is not None:
            proof = additional_owners(closing)[1]
            receipt.metadata = dict(version=VERSION, partitions=identity(closing, version=version),
                sources=proof['sources'])
            receipt.digest = digest(receipt.metadata)
            receipt.status = 'SEALED'
            receipt.save(update_fields=['metadata','digest','status'])
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
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    native = source.receipt.get('schema') == SOURCE_SCHEMA
    captures = list(MdmDailyInputCapture.objects.filter(source=source, status='CONSUMED',
                    run__status='SUCCEEDED').select_related('run'))
    by_id = {c.run_id: c for c in captures}
    if run.pk not in by_id or any(c.run.kind != 'DAILY_CHAIN'
            or not native and not c.nms_active for c in captures):
        raise ValueError('Current owner chain is unavailable')
    from mta.application.daily_finalization import ACTIVE_POLICY, POLICY
    from mta.runtime.input_reader import read_input
    for capture in captures:
        profile=read_input(capture.run,components=('profile',))['profile']
        policy=profile.get('complete_daily',{}).get('policy')
        if policy not in (ACTIVE_POLICY,POLICY) or capture.nms_active != (policy==ACTIVE_POLICY):
            raise ValueError('Current owner mode differs from its frozen policy')
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
    def projection_version(item):
        if not native:
            return None
        from mta.mdm.location_transition import verified_receipt
        receipt = verified_receipt(item, source)
        return receipt.version if receipt is not None else None
    verify_current(source, closing, version=projection_version(leaf))
    # Never return the changing leaf identity as part of an old receipt.
    if leaf.pk != run.pk:
        closing = read_outputs(run)['ClosingState'][0]
    return identity(closing, version=projection_version(run))
