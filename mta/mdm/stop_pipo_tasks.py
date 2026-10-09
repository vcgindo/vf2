"""Deployed master-6 StopPIPO submission and approval statement effects."""
import logging

from django.db import DatabaseError

from mta.mdm.clock import database_now
from mta.mdm.drafts import now, value
from mta.mdm.force_tasks import (_auth_key, _submission_scopes, payload_key,
                                 row_key, scopes)
from mta.mdm.skuloc_tasks import _approvers
from mta.mdm.stop_pipo_revisions import bump_task
from mta.mdm.supplier_revisions import decision
from mta.mdm.task_reads import (TaskDenied, assigned, header,
                                require_requester)
from mta.runtime.mdm_models import MdmSubTask, MdmTask
from mta.runtime.mdm_skuloc_models import MdmSkuLocPair
from mta.runtime.mdm_stop_pipo_models import (MdmStopPipoHistory,
                                              MdmStopPipoQueue,
                                              MdmStopPipoRequested)


log = logging.getLogger(__name__)


def _project(row):
    """StopPhaseOut replaces every supplied row with exactly sc/wc."""
    return {'sc': row['sc'] if 'sc' in row else None,
            'wc': row['wc'] if 'wc' in row else None}


@decision
def submit(source, payload, actor, action):
    if int(value(payload, 'id')) != 6 or action != 2:
        raise ValueError('StopPIPO supports Modify only')
    supplied_id = value(payload, 'taskId')
    if supplied_id:
        require_requester(source, supplied_id, actor)
    projected = [_project(row) for row in value(payload, 'data')]
    task_id = supplied_id or str(actor['id']) + '_' + now().strftime('%Y%m%d%H%M%S')

    pairs = set(MdmSkuLocPair.objects.filter(source=source, owner='Importer')
                .values_list('SKUCode', 'LocCode'))
    missing = [row for row in projected if (row['sc'], row['wc']) not in pairs]
    allowed = [row for row in projected if not any(row is item for item in missing)]
    errors = []
    if missing:
        errors.append(dict(errorType='SKU and Location Code does not exists ',
                           errorData=missing))
    sku_scope, location_scope = _submission_scopes(source, payload)
    denied = [row for row in allowed
              if _auth_key(row['sc']) not in sku_scope
              or _auth_key(row['wc']) not in location_scope]
    allowed = [row for row in allowed if not any(row is item for item in denied)]
    if denied:
        errors.append(dict(errorType='UnAuthorized SKUCodes OR Location codes',
                           errorData=denied))

    # StopPhaseOut calls requestdata.TaskId.ToString while assembling the first
    # accepted batch. A missing property fails before its PostQuery statement.
    if supplied_id is None and allowed:
        raise ValueError('native TaskId.ToString requires a value')
    if any(row['sc'] is None or row['wc'] is None for row in allowed):
        raise ValueError('native stop key value.ToString requires a value')

    for offset in range(0, len(allowed), 999):
        chunk = allowed[offset:offset + 999]
        selected = _approvers(source, chunk, payload['all_users'])
        approver_ids = ','.join(str(user['id']) for user in selected)
        approver_names = ','.join(user['name'] for user in selected)
        converted = [{'SKUCode': str(row['sc']), 'WhCode': str(row['wc'])}
                     for row in chunk]
        MdmStopPipoRequested.objects.bulk_create([
            MdmStopPipoRequested(source=source, ActionType=2, Approved=False,
                Reverted=False, TaskId=task_id, **row) for row in converted])
        MdmStopPipoHistory.objects.bulk_create([
            MdmStopPipoHistory(source=source, ActionType=2, TaskId=task_id,
                **row) for row in converted])
        # Native UPDATE is task-wide, including rows forwarded earlier under
        # this task identity.
        MdmStopPipoHistory.objects.filter(source=source, TaskId=task_id).update(
            ApproverId=approver_ids)
        if not supplied_id and offset == 0:
            MdmTask.objects.create(source=source, TaskID=task_id,
                PendingSince=database_now(), TaskName='Modify-StopPIPO',
                ApproverId=approver_ids, RequesterId=str(actor['id']),
                MasterId='6', Actiontype=2,
                ColumnList='SKUCode,WhCode,ActionType,Approved,Reverted,TaskId',
                ApproversName=approver_names, RequesterName=actor['name'],
                TaskStatus='1')
            MdmSubTask.objects.bulk_create([MdmSubTask(source=source,
                TaskID=task_id, ApproverId=str(user['id']),
                ApproverName=user['name'], TaskStatus='1') for user in selected])
    return dict(status=200, msg=None, taskId=task_id,
        errorCount=str(sum(len(item['errorData']) for item in errors)),
        error=errors, conflictErrorCount='0', conflictError=None)


@decision
def delete(source, task_id, actor):
    require_requester(source, task_id, actor)
    for model, field in ((MdmStopPipoHistory, 'TaskId'),
                         (MdmStopPipoRequested, 'TaskId'),
                         (MdmTask, 'TaskID'), (MdmSubTask, 'TaskID')):
        model.objects.filter(source=source, **{field: task_id}).delete()


@decision
def approve(source, payload, actor):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if task is None or task.MasterId != '6' or task.Actiontype != 2:
        raise TaskDenied('task_reviewer_required')
    history = list(MdmStopPipoHistory.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    requested = list(MdmStopPipoRequested.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    sku_scope, location_scope = scopes(source, payload)
    decisions = {}
    for row in value(payload, 'data'):
        if any(row.get(name) is None for name in ('sc', 'wc', 'status', 'comments')):
            raise ValueError('native decision key/status value.ToString requires a value')
        identity = payload_key(row)
        matching = [item for item in history if row_key(item) == identity]
        if (not matching
                or not all(assigned(item.ApproverId, actor['id']) for item in matching)
                or identity[0] not in sku_scope or identity[1] not in location_scope):
            raise TaskDenied('task_row_reviewer_scope_required')
        result = (str(row['status']), str(row['comments']))
        if identity in decisions and decisions[identity] != result:
            raise ValueError('native duplicate decision UPDATE is incomparable')
        decisions[identity] = result
    if not decisions:
        raise TaskDenied('task_row_reviewer_scope_required')

    bump_task(source, 6, task_id)
    try:
        for item in requested:
            result = decisions.get(row_key(item))
            if result:
                MdmStopPipoRequested.objects.filter(pk=item.pk).update(
                    Approved=result[0] == '3', Reverted=result[0] == '4')
        for item in history:
            result = decisions.get(row_key(item))
            if result:
                MdmStopPipoHistory.objects.filter(pk=item.pk).update(
                    Status=result[0], Comments=result[1], ApprovedBy=int(actor['id']))

        incoming = list(MdmStopPipoRequested.objects.filter(
            source=source, TaskId=task_id, Approved=True).order_by('id'))
        existing = {row_key(item) for item in MdmStopPipoQueue.objects.filter(source=source)
                    if item.SKUCode is not None and item.WhCode is not None}
        # The native LEFT JOIN cannot match either NULL key. It also evaluates
        # every approved source row against the old target, so duplicate
        # incoming rows all survive when the non-NULL key was absent before
        # the statement.
        MdmStopPipoQueue.objects.bulk_create([MdmStopPipoQueue(source=source,
            SKUCode=item.SKUCode, WhCode=item.WhCode) for item in incoming
            if item.SKUCode is None or item.WhCode is None
            or row_key(item) not in existing])
    except DatabaseError:
        # UpdateApprovedData uses TaskStatusProcessor's one-argument PostQuery;
        # that wrapper logs the SQL failure and returns to task-status handling.
        log.exception('Native StopPIPO approval statement failure')

    all_history = list(MdmStopPipoHistory.objects.filter(
        source=source, TaskId=task_id))
    mine = [item for item in all_history if assigned(item.ApproverId, actor['id'])]
    completed = bool(mine) and all(item.Status in ('3', '4') for item in mine)
    stamp = database_now().strftime('%d/%m/%Y %I:%M %p')
    MdmSubTask.objects.filter(source=source, TaskID=task_id,
        ApproverId=str(actor['id'])).update(ApprovedOrRejectedDate=stamp)
    if completed:
        for sub in MdmSubTask.objects.filter(source=source, TaskID=task_id).exclude(
                ApprovedOrRejectedDate=None):
            rows = [item for item in all_history
                    if assigned(item.ApproverId, sub.ApproverId)]
            if rows and all(item.Status in ('3', '4') for item in rows):
                status = ('2' if all(item.Status == '3' for item in rows) else
                          '6' if all(item.Status == '4' for item in rows) else '3')
                MdmSubTask.objects.filter(pk=sub.pk).update(
                    TaskStatus=status, ApprovedOrRejectedDate=stamp)
        MdmSubTask.objects.filter(source=source, TaskID=task_id,
            ApprovedOrRejectedDate=None).update(TaskStatus='8')
    else:
        MdmSubTask.objects.filter(source=source, TaskID=task_id,
            ApproverId=str(actor['id'])).update(TaskStatus='3')
    return dict(status=200,
        msg='Data submitted successfully' + (' and Task status updated' if completed
            else 'Task status not updated') + ' ', taskId=task_id,
        errorCount=None, error=None, conflictErrorCount=None, conflictError=None)
