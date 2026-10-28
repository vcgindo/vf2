"""Observe the real BTR current-master writer inside its existing transaction.

These cuts describe SQL-owned revisions. They never predict business rows,
increment a counter, replace a producer or relax a pending-phase guard.
"""
from django.db import connection

SCHEMA = 'vectorflow-scoped-current-master-cut-v1'


def _owner(run):
    from mta.runtime.scoped_final import require_pending_final
    from mta.runtime.scope_revisions import identity
    require_pending_final(run)
    capture=identity(run)
    if capture is None:
        raise ValueError('Current master publication requires its native capture')
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_phase',true)")
        phase=cursor.fetchone()[0]
    return capture,phase


def _epochs(initialization_id):
    from mta.runtime.accepted_daily import epochs
    return epochs(initialization_id,lock=True)


def begin(run):
    capture,phase=_owner(run)
    return dict(schema=SCHEMA,run_id=str(run.pk),initialization_id=capture['initialization_id'],
        source_digest=capture['source_digest'],pending_final_id=phase,
        before=_epochs(capture['initialization_id']))


def require_delta(before,after):
    if (type(before) is not list or type(after) is not list or len(before)!=5 or len(after)!=5
            or any(type(value) is not int or value<0 for value in before+after)):
        raise ValueError('Current master publication requires exact typed revision cuts')
    increment=after[0]-before[0]
    if increment<0 or after!=[before[0]+increment,before[1]+increment,*before[2:]]:
        raise ValueError('BTR current writer changed a non-master revision domain')
    return increment


def end(run,cut):
    capture,phase=_owner(run)
    if (cut.get('schema')!=SCHEMA or cut.get('run_id')!=str(run.pk)
            or cut.get('initialization_id')!=capture['initialization_id']
            or cut.get('source_digest')!=capture['source_digest'] or cut.get('pending_final_id')!=phase):
        raise ValueError('Current master publication owner changed')
    after=_epochs(capture['initialization_id'])
    return dict(cut,after=after,master_increment=require_delta(cut['before'],after))


def seal(run,cut,receipt):
    from mta.mdm.location_transition import verified_receipt
    actual=verified_receipt(run,run.mdm_input_capture.source)
    if receipt is None or actual.pk!=receipt.pk:
        raise ValueError('Current master publication requires its actual sealed projection')
    return dict(cut,projection_id=str(actual.pk),projection_digest=actual.digest)


def validate(run,capture,cut,*,parent,final_id):
    from mta.mdm.location_transition import verified_receipt
    fields={'schema','run_id','initialization_id','source_digest','pending_final_id','before','after',
            'master_increment','projection_id','projection_digest'}
    if type(cut) is not dict or set(cut)!=fields:
        raise ValueError('Current master publication cut is absent or differs')
    increment=require_delta(cut['before'],cut['after'])
    if (cut['schema']!=SCHEMA
            or cut['run_id']!=str(run.pk) or cut['initialization_id']!=capture['initialization_id']
            or cut['source_digest']!=capture['source_digest'] or cut['pending_final_id']!=str(final_id)
            or cut['before'][:2]!=[parent.master_epoch,parent.configuration_epoch]
            or type(cut['master_increment']) is not int
            or increment!=cut['master_increment']):
        raise ValueError('Current master publication revision/phase custody differs')
    projection=verified_receipt(run,run.mdm_input_capture.source)
    if cut['projection_id']!=str(projection.pk) or cut['projection_digest']!=projection.digest:
        raise ValueError('Current master publication projection custody differs')
    return cut['master_increment']
