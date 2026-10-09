"""Serialize supplier decisions without replacing native statement commits."""
from contextlib import contextmanager
from functools import wraps

from django.db import connection
from django.db.models import F, Q

from mta.runtime.mdm_supplier_models import MdmSupplierTaskRevision


def _key(source_id):
    return 'fresh-mdm-supplier:' + str(source_id)


def lock_transaction(source_id):
    if not connection.in_atomic_block:
        raise ValueError('Supplier publication/capture requires an atomic owner')
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', [_key(source_id)])


@contextmanager
def source_lock(source_id, *, deciding=False):
    if source_id is None:
        yield
        return
    local = connection.in_atomic_block
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_' + ('xact_' if local else '') +
            'lock(hashtextextended(%s,0))', [_key(source_id)])
        cursor.execute("SELECT current_setting('fresh.supplier_deciding_source',true)")
        prior = cursor.fetchone()[0] or ''
        if deciding:
            cursor.execute("SELECT set_config('fresh.supplier_deciding_source',%s,%s)",
                           [str(source_id), local])
    try:
        yield
    finally:
        # Inside an existing transaction a SQL failure retains the xact lock
        # until its owner rolls back; the local setting rolls back with it.
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                if deciding:
                    cursor.execute("SELECT set_config('fresh.supplier_deciding_source',%s,%s)", [prior, local])
                if not local:
                    cursor.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))', [_key(source_id)])


def decision(function):
    @wraps(function)
    def wrapped(source, *args, **kwargs):
        with source_lock(source.pk, deciding=True):
            return function(source, *args, **kwargs)
    return wrapped


def bump_task(source, master_id, task_id):
    token, _ = MdmSupplierTaskRevision.objects.get_or_create(
        source=source, master_id=master_id, task_id=task_id)
    MdmSupplierTaskRevision.objects.filter(pk=token.pk).update(revision=F('revision') + 1)


def task_revisions(source):
    from mta.runtime.mdm_models import MdmTask
    live = Q()
    for master_id in (4, 5):
        live |= Q(master_id=master_id, task_id__in=MdmTask.objects.filter(
            source=source, MasterId=str(master_id)).values('TaskID'))
    return list(MdmSupplierTaskRevision.objects.filter(live, source=source)
                .order_by('master_id', 'task_id').values('master_id', 'task_id', 'revision'))


def superseded_tasks(snapshot):
    supplier = snapshot.get('supplier')
    if supplier is None:
        return set()
    frozen = {(r['master_id'], r['task_id']): r['revision'] for r in supplier['task_revisions']}
    current = {(r['master_id'], r['task_id']): r['revision']
               for r in task_revisions(snapshot['source_id'])}
    if any(current.get(key, -1) < revision for key, revision in frozen.items()):
        raise ValueError('Supplier task revision regressed or disappeared')
    return {(master_id, task_id) for (master_id, task_id), revision in current.items()
            if revision > frozen.get((master_id, task_id), 0)}
