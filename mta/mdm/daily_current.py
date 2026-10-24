"""Typed current master publication within the existing atomic day boundary."""
from copy import deepcopy
from django.db import connection

from mta.mdm.master_owners import owner_batches, business_fields
from mta.serialization import digest, storage


_WRITE_BATCH = 500


def _scalar_storage(value):
    # Current business fields are typed scalars. Avoid the graph/RecordRows
    # dispatch for primitives while retaining the canonical conversion for
    # Decimal, dates and any unqualified value.
    return value if value is None or type(value) in (str, int, float, bool) else storage(value)


def _chunks(values, size=_WRITE_BATCH):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _verify_written(base, names, expected, ordinals, retained_pks, path):
    actual = list(base.filter(ordinal__in=ordinals).order_by('ordinal')
                  .values('pk', 'ordinal', *names))
    if [row['ordinal'] for row in actual] != list(ordinals):
        raise ValueError('MDM current written occurrence differs: ' + path)
    for row in actual:
        ordinal = row.pop('ordinal')
        pk = row.pop('pk')
        if (ordinal in retained_pks and pk != retained_pks[ordinal]) or \
                storage(row) != storage(expected[ordinal - 1]):
            raise ValueError('MDM current written values differ: ' + path)


def _flush_updates(model, base, names, expected, updates, retained_pks, path):
    for changed, rows in updates.items():
        if connection.vendor != 'postgresql':
            model.objects.bulk_update(rows, list(changed), batch_size=_WRITE_BATCH)
            continue
        # Keep exactly the original changed-field groups and statement batches:
        # statement/row guards and revision epochs retain their invocation grain.
        # Only replace Django's per-cell CASE expression construction with a
        # bounded typed VALUES transport. No persistent staging or checkpoint.
        fields = [model._meta.get_field(name) for name in changed]
        pk = model._meta.pk
        quote = connection.ops.quote_name
        columns = [quote(field.column) for field in (pk, *fields)]
        slot = '(' + ','.join('%s::' + field.db_type(connection) for field in (pk, *fields)) + ')'
        for batch in _chunks(rows):
            params = []
            for row in batch:
                params.append(pk.get_db_prep_save(row.pk, connection))
                params.extend(field.get_db_prep_save(getattr(row, field.attname), connection) for field in fields)
            params.extend(pk.get_db_prep_save(row.pk, connection) for row in batch)
            sql = ('UPDATE ' + quote(model._meta.db_table) + ' AS target SET ' +
                   ','.join(quote(field.column) + '=incoming.' + quote(field.column) for field in fields) +
                   ' FROM (VALUES ' + ','.join(slot for _ in batch) + ') AS incoming (' + ','.join(columns) + ')' +
                   ' WHERE target.' + quote(pk.column) + '=incoming.' + quote(pk.column) +
                   ' AND target.' + quote(pk.column) + ' IN (' + ','.join('%s' for _ in batch) + ')')
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
    ordinals = sorted(retained_pks)
    _verify_written(base, names, expected, ordinals, retained_pks, path)
    updates.clear()
    retained_pks.clear()


def _flush_deletes(model, base, pks, path):
    model.objects.filter(pk__in=pks).delete()
    if base.filter(pk__in=pks).exists():
        raise ValueError('MDM current deleted occurrence remains: ' + path)
    pks.clear()


def _write_partition(source, model, partition, expected, path):
    """Replace one ordered projection logically while retaining equal occurrences.

    Ordinal is the occurrence identity at this projection boundary.  Existing
    occurrences keep both ordinal and primary key; only differing business
    fields are updated.  The complete pre-write scan proves every untouched
    occurrence, and the bounded post-write read proves every written occurrence
    plus the final population count.
    """
    fields = business_fields(model)
    names = [field.name for field in fields]
    if any(not isinstance(row, dict) or set(row) != set(names) for row in expected):
        raise ValueError('MDM current projected fields differ: ' + path)
    base = model.objects.filter(source=source, **partition)
    updates = {}
    update_pks = {}
    pending_updates = 0
    tail_pks = []
    existing_count = 0
    updated = 0
    deleted = 0
    for row in base.order_by('ordinal').only('pk', 'ordinal', *names).iterator(
            chunk_size=_WRITE_BATCH):
        existing_count += 1
        if row.ordinal != existing_count:
            raise ValueError('MDM current ordinal gap: ' + path)
        if row.ordinal > len(expected):
            tail_pks.append(row.pk)
            deleted += 1
            if len(tail_pks) == _WRITE_BATCH:
                _flush_deletes(model, base, tail_pks, path)
            continue
        target = expected[row.ordinal - 1]
        changed = tuple(name for name in names
                        if _scalar_storage(getattr(row, name)) != _scalar_storage(target[name]))
        if changed:
            for name in changed:
                setattr(row, name, target[name])
            updates.setdefault(changed, []).append(row)
            update_pks[row.ordinal] = row.pk
            pending_updates += 1
            updated += 1
            if pending_updates == _WRITE_BATCH:
                _flush_updates(model, base, names, expected, updates, update_pks, path)
                pending_updates = 0

    if pending_updates:
        _flush_updates(model, base, names, expected, updates, update_pks, path)
    if tail_pks:
        _flush_deletes(model, base, tail_pks, path)
    inserted = max(0, len(expected) - existing_count)
    for ordinals in _chunks(range(existing_count + 1, len(expected) + 1)):
        model.objects.bulk_create([
            model(source=source, ordinal=ordinal, **partition, **expected[ordinal - 1])
            for ordinal in ordinals], batch_size=_WRITE_BATCH)
        _verify_written(base, names, expected, ordinals, {}, path)

    if base.count() != len(expected):
        raise ValueError('MDM current written row count differs: ' + path)
    return {'updated': updated, 'inserted': inserted, 'deleted': deleted}


def _closing_projection(closing, *, version=None):
    """Prepare one private generation for writes and its receipt identity."""
    # Persisted verification may reload immutable RecordRows. Keep the shared
    # installation/master producer APIs unchanged: adapt only their selected
    # post-DBM projection inputs, never materialize the full closing histories.
    from mta.row_sequences import RecordRows
    projected = dict(closing)
    selected = {
        'importer': ('SkuAttributeData', 'SKUDescriptionTbl', 'LocationAttributeData',
                     'SiteDescriptionTbl', 'SkuLocAttributeData', 'MasterData'),
        'dbm': ('SkuAttributeData', 'SKUDescriptionTbl', 'LocationAttributeData', 'SiteDescriptionTbl'),
        'btr': ('SkuAttributeData', 'SKUDescriptionTbl', 'LocationAttributeData', 'SiteDescriptionTbl'),
        'consumer_context': ('NMSAllItems',),
    }
    for section, names in selected.items():
        state = closing.get(section, {})
        spooled = {name: list(state[name]) for name in names if isinstance(state.get(name), RecordRows)}
        if spooled:
            projected[section] = dict(state, **spooled)
    batches = owner_batches(projected)
    proof = None
    if version is not None:
        from mta.mdm.location_projection import additional_owners, VERSION
        if version != VERSION:
            raise ValueError('Unsupported closing projection version')
        additional, proof = additional_owners(projected)
        batches += additional
    return batches, proof


def closing_owners(closing, *, version=None):
    """Reuse the exact installation projection, including its BPR copy source."""
    return _closing_projection(closing, version=version)[0]


def _partition_identity(batches):
    return [dict(family=family, model=model.__name__, **partition,
                 fields=[f.name for f in business_fields(model)],
                 rows=len(rows), digest=digest(storage(rows)))
            for family, model, partition, rows, _path in batches]


def identity(closing, *, version=None):
    return _partition_identity(closing_owners(closing, version=version))


def verify_current(source, closing, *, version=None):
    for _family, model, partition, expected, path in closing_owners(closing, version=version):
        fields = [f.name for f in business_fields(model)]
        actual = list(model.objects.filter(source=source, **partition)
                      .order_by('ordinal').values('ordinal', *fields))
        ordinals = [row.pop('ordinal') for row in actual]
        if (ordinals != list(range(1, len(expected) + 1))
                or storage(actual) != storage(expected)):
            raise ValueError('MDM current full typed readback differs: ' + path)


def publish(run, capture, closing, *, _accepted_prefix=False):
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
        from mta.mdm.location_projection import VERSION
        from mta.runtime.mdm_projection_models import MdmClosingProjectionReceipt
        code_identity = run_identity(run, source)
        if code_identity['version'] != VERSION:
            raise ValueError('New native publication requires the corrected projection')
        admit(source, run.business_date, run.predecessor)
        version = VERSION
    batches, proof = _closing_projection(closing, version=version)
    if _accepted_prefix:
        from mta.runtime.scoped_final import require_pending_final
        require_pending_final(run)
        # Accepted Importer/BPR/DBM copies are compared in full, never repaired
        # or silently overwritten at finalization. Only BTR remains to publish.
        retained=[batch for batch in batches if batch[2].get('owner')!='BTR']
        from mta.mdm.master_owners import phase_copy_batches
        retained.extend(phase_copy_batches('BPR',closing['importer']))
        retained.extend(phase_copy_batches('DBM',closing['dbm']))
        for _family,model,partition,expected,path in retained:
            fields=[f.name for f in business_fields(model)]
            rows=list(model.objects.filter(source=source,**partition).order_by('ordinal')
                      .values('ordinal',*fields))
            ordinals=[row.pop('ordinal') for row in rows]
            if ordinals!=list(range(1,len(expected)+1)) or storage(rows)!=storage(expected):
                raise ValueError('Accepted scoped current partition differs: '+path)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_current_run',%s,true)", [str(run.pk)])
    try:
        if native:
            receipt = MdmClosingProjectionReceipt.objects.create(run=run,
                capture_digest=capture_identity(capture), **code_identity)
        for _family, model, partition, rows, path in batches:
            if _accepted_prefix and partition.get('owner')!='BTR':
                continue
            _write_partition(source, model, partition, rows, path)
        if receipt is not None:
            receipt.metadata = dict(version=VERSION, partitions=_partition_identity(batches),
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
    closing = (read_outputs(leaf,include_reports=False) if leaf.production_manifest.get('version')==3 else read_outputs(leaf))['ClosingState'][0]
    def projection_version(item):
        if not native:
            return None
        from mta.mdm.location_transition import verified_receipt
        receipt = verified_receipt(item, source)
        return receipt.version if receipt is not None else None
    verify_current(source, closing, version=projection_version(leaf))
    # Never return the changing leaf identity as part of an old receipt.
    if leaf.pk != run.pk:
        closing = (read_outputs(run,include_reports=False) if run.production_manifest.get('version')==3 else read_outputs(run))['ClosingState'][0]
    return identity(closing, version=projection_version(run))
