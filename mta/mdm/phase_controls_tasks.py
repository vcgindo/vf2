"""Deployed ADD-only task effects for phase-control masters 7, 8, and 9."""
import logging

from django.db import DatabaseError

from mta.mdm.clock import database_now
from mta.mdm.drafts import now, value
from mta.mdm.force_tasks import (_auth_key, _submission_scopes, payload_key,
                                 row_key, scopes)
from mta.mdm.phase_controls_configuration import ALIASES
from mta.mdm.phase_controls_revisions import bump_task
from mta.mdm.skuloc_tasks import _approvers
from mta.mdm.supplier_revisions import decision
from mta.mdm.task_reads import TaskDenied, assigned, header, require_requester
from mta.runtime.mdm_models import MdmSubTask, MdmTask
from mta.runtime.mdm_phase_controls_models import (
    MdmPhaseInNormHistory, MdmPhaseInNormQueue, MdmPhaseInNormRequested,
    MdmPhaseOutHistory, MdmPhaseOutQueue, MdmPhaseOutRequested)
from mta.runtime.mdm_skuloc_models import MdmSkuLocPair


log = logging.getLogger(__name__)
MASTERS = (7, 8, 9)


def models(master_id):
    if int(master_id) in (7, 8):
        return MdmPhaseOutRequested, MdmPhaseOutHistory, MdmPhaseOutQueue
    if int(master_id) == 9:
        return MdmPhaseInNormRequested, MdmPhaseInNormHistory, MdmPhaseInNormQueue
    raise ValueError('Phase-control family is not delivered')


def _convert(master_id, row, keys):
    converted = {}
    for alias in keys:
        field = ALIASES[master_id][alias]
        raw = row[alias]
        if field == 'TargetNorm':
            if raw is None:
                converted[field] = None
            else:
                number = int(str(raw).strip() or '0')
                if not -2147483648 <= number <= 2147483647:
                    raise ValueError('native int32 overflow')
                converted[field] = number
        else:
            converted[field] = None if raw is None else str(raw)
    return converted


@decision
def submit(source, payload, actor, action):
    master_id = int(value(payload, 'id'))
    if master_id not in MASTERS or action != 1:
        raise ValueError('Phase controls support Add only')
    supplied_id = value(payload, 'taskId')
    if supplied_id:
        require_requester(source, supplied_id, actor)
    data = value(payload, 'data')
    keys = list(data[0])
    task_id = supplied_id or str(actor['id']) + '_' + now().strftime('%Y%m%d%H%M%S')

    # DataValidation silently drops rows missing either key. Pair membership is
    # exact and precedes its case-insensitive hierarchy authorization pass.
    keyed = [row for row in data if 'sc' in row and 'wc' in row]
    pairs = set(MdmSkuLocPair.objects.filter(source=source, owner='Importer')
                .values_list('SKUCode', 'LocCode'))
    missing = [row for row in keyed if (row['sc'], row['wc']) not in pairs]
    allowed = [row for row in keyed if not any(row is item for item in missing)]
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
    if supplied_id is None and allowed:
        raise ValueError('native TaskId.ToString requires a value')
    if any(row['sc'] is None or row['wc'] is None for row in allowed):
        raise ValueError('native phase key value.ToString requires a value')

    requested_model, history_model, _ = models(master_id)
    for offset in range(0, len(allowed), 999):
        chunk = allowed[offset:offset + 999]
        selected = _approvers(source, chunk, payload['all_users'])
        approver_ids = ','.join(str(user['id']) for user in selected)
        approver_names = ','.join(user['name'] for user in selected)
        try:
            converted = [_convert(master_id, row, keys) for row in chunk]
            # UploadPIPO passes 2 to GetValuesSPF even though its task header is
            # ADD/action 1. Preserve that requested/history ActionType defect.
            requested_model.objects.bulk_create([requested_model(source=source,
                ActionType=2, Approved=False, Reverted=False, TaskId=task_id, **row)
                for row in converted])
            history_model.objects.bulk_create([history_model(source=source,
                ActionType=2, TaskId=task_id, **row) for row in converted])
            history_model.objects.filter(source=source, TaskId=task_id).update(
                ApproverId=approver_ids)
            if not supplied_id and offset == 0:
                task_name = {7: 'Add-AddPOMaster', 8: 'Add-AddPIPOMaster',
                             9: 'Add-AddTargetNorm'}[master_id]
                fields = [ALIASES[master_id][alias] for alias in keys]
                MdmTask.objects.create(source=source, TaskID=task_id,
                    PendingSince=database_now(), TaskName=task_name,
                    ApproverId=approver_ids, RequesterId=str(actor['id']),
                    MasterId=str(master_id), Actiontype=1,
                    ColumnList=','.join(fields + [
                        'ActionType', 'Approved', 'Reverted', 'TaskId']),
                    ApproversName=approver_names, RequesterName=actor['name'],
                    TaskStatus='1')
                MdmSubTask.objects.bulk_create([MdmSubTask(source=source,
                    TaskID=task_id, ApproverId=str(user['id']),
                    ApproverName=user['name'], TaskStatus='1') for user in selected])
        except (DatabaseError, ValueError, TypeError):
            # UploadPIPO uses the propagating two-argument PostQuery overload.
            log.exception('Native phase-control submission statement failure')
            raise
    return dict(status=200, msg=None, taskId=task_id,
        errorCount=str(sum(len(item['errorData']) for item in errors)),
        error=errors, conflictErrorCount='0', conflictError=None)


@decision
def delete(source, task_id, actor):
    require_requester(source, task_id, actor)
    task = header(source, task_id)
    if task is None or int(task.MasterId) not in MASTERS:
        raise TaskDenied('task_requester_required')
    requested_model, history_model, _ = models(task.MasterId)
    for model, field in ((history_model, 'TaskId'), (requested_model, 'TaskId'),
                         (MdmTask, 'TaskID'), (MdmSubTask, 'TaskID')):
        model.objects.filter(source=source, **{field: task_id}).delete()


@decision
def approve(source, payload, actor):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if (task is None or int(task.MasterId) not in MASTERS
            or task.Actiontype != 1):
        raise TaskDenied('task_reviewer_required')
    master_id = int(task.MasterId)
    requested_model, history_model, queue_model = models(master_id)
    history = list(history_model.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    requested = list(requested_model.objects.filter(
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
        result = str(row['status']), str(row['comments'])
        if identity in decisions and decisions[identity] != result:
            raise ValueError('native duplicate decision UPDATE is incomparable')
        decisions[identity] = result
    if not decisions:
        raise TaskDenied('task_row_reviewer_scope_required')

    bump_task(source, master_id, task_id)
    try:
        for item in requested:
            result = decisions.get(row_key(item))
            if result:
                requested_model.objects.filter(pk=item.pk).update(
                    Approved=result[0] == '3', Reverted=result[0] == '4')
        for item in history:
            result = decisions.get(row_key(item))
            if result:
                history_model.objects.filter(pk=item.pk).update(
                    Status=result[0], Comments=result[1],
                    ApprovedBy=str(actor['id']))

        incoming = list(requested_model.objects.filter(
            source=source, TaskId=task_id, Approved=True).order_by('id'))
        if master_id == 7:
            incoming = [item for item in incoming if item.PhaseInSKUCode is None]
        elif master_id == 8:
            incoming = [item for item in incoming if item.PhaseInSKUCode is not None]
        existing = {row_key(item) for item in queue_model.objects.filter(source=source)
                    if item.SKUCode is not None and item.WhCode is not None}
        columns = ('SKUCode', 'WhCode',
                   'TargetNorm' if master_id == 9 else 'PhaseInSKUCode')
        queue_model.objects.bulk_create([queue_model(source=source,
            Approved=item.Approved,
            **{name: getattr(item, name) for name in columns}) for item in incoming
            if item.SKUCode is None or item.WhCode is None
            or row_key(item) not in existing])
    except DatabaseError:
        # UpdateApprovedData's one-argument PostQuery logs and returns before
        # the caller continues with task-status processing.
        log.exception('Native phase-control approval statement failure')

    all_history = list(history_model.objects.filter(source=source, TaskId=task_id))
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
