"""Deployed ADD11/12 and STOP/RESUME10 statement effects."""
from datetime import date
import logging
from django.db import DatabaseError
from django.db.models import F

from mta.application.r1_seasonality import REQUEST_FIELDS, SEASON_FIELDS
from mta.mdm.clock import database_now
from mta.mdm.drafts import now, value
from mta.mdm.force_tasks import scopes, _submission_scopes, _auth_key, row_key, payload_key
from mta.mdm.season_configuration import aliases
from mta.mdm.season_revisions import bump_task
from mta.mdm.skuloc_tasks import _approvers
from mta.mdm.supplier_revisions import decision
from mta.mdm.task_reads import TaskDenied, assigned, header, require_requester
from mta.runtime.mdm_models import MdmSubTask, MdmTask
from mta.runtime.mdm_skuloc_models import MdmSkuLocPair
from mta.runtime.mdm_season_models import (MdmSeasonQueue, MdmSeasonCurrent,
    MdmSeasonRequested, MdmSeasonHistory, MdmSeasonStatusRequested,
    MdmSeasonStatusHistory, MdmSeasonEligibility)

log = logging.getLogger(__name__)
UPDATE_FIELDS = ('StartDate', 'EndDate', 'TargetNorm', 'DeltaNormPercentage',
                 'UpperLowerCap', 'BuildupDuration')


def models(master_id):
    return ((MdmSeasonStatusRequested, MdmSeasonStatusHistory) if int(master_id) == 10
            else (MdmSeasonRequested, MdmSeasonHistory))


def convert(row, keys, master_id):
    mapping = aliases(master_id)
    result = {}
    for alias in keys:
        raw = row[alias]
        field = mapping[alias]
        if alias in ('sc', 'wc'):
            if raw is None:
                raise ValueError('native key value.ToString requires a value')
            result[field] = str(raw)
        elif alias in ('sd', 'ed'):
            result[field] = (None if raw is None else
                date.fromisoformat(str(raw)) if str(raw).strip() else date(1900, 1, 1))
        elif alias in ('tn', 'dnp', 'ulc', 'bd', 'cn'):
            number = None if raw is None else int(str(raw).strip() or '0')
            if number is not None and not -2147483648 <= number <= 2147483647:
                raise ValueError('native int32 overflow')
            result[field] = number
        else:
            result[field] = raw
    return result


@decision
def submit(source, payload, actor, action):
    master_id = int(value(payload, 'id'))
    if master_id not in (10, 11, 12) or action != (2 if master_id == 10 else 1):
        raise ValueError('Seasonality operation is not delivered')
    supplied_id = value(payload, 'taskId')
    if supplied_id:
        require_requester(source, supplied_id, actor)
    data = value(payload, 'data')
    keys = list(data[0])
    task_id = supplied_id or str(actor['id']) + '_' + now().strftime('%Y%m%d%H%M%S')
    requested_model, history_model = models(master_id)
    pairs = set(MdmSkuLocPair.objects.filter(source=source, owner='Importer')
        .values_list('SKUCode', 'LocCode'))
    keyed = [r for r in data if 'sc' in r and 'wc' in r]
    missing = [r for r in keyed if (r['sc'], r['wc']) not in pairs]
    allowed = [r for r in keyed if not any(r is x for x in missing)]
    errors = []
    if missing:
        errors.append(dict(errorType='SKU and Location Code does not exists ', errorData=missing))
    sku_scope, location_scope = _submission_scopes(source, payload)
    denied = [r for r in allowed if _auth_key(r['sc']) not in sku_scope
              or _auth_key(r['wc']) not in location_scope]
    allowed = [r for r in allowed if not any(r is x for x in denied)]
    if denied:
        errors.append(dict(errorType='UnAuthorized SKUCodes OR Location codes', errorData=denied))
    error_count = sum(len(e['errorData']) for e in errors)
    if master_id in (11, 12) and allowed:
        # The approved fixture is used exclusively for this second native lookup.
        eligible = {(_auth_key(r.SKUCode), _auth_key(r.WhCode))
                    for r in MdmSeasonEligibility.objects.filter(source=source)}
        missing = [r for r in allowed if (_auth_key(r['sc']), _auth_key(r['wc'])) not in eligible]
        allowed = [r for r in allowed if not any(r is x for x in missing)]
        if missing:
            errors.append(dict(errorType='SKU Code and WHCode does not exist.', errorData=missing))
        error_count = len(missing)  # Native replaces the count, retaining earlier error bags.
    if supplied_id is None and allowed:
        raise ValueError('native TaskId.ToString requires a value')
    mapping = aliases(master_id)
    for offset in range(0, len(allowed), 999):
        chunk = allowed[offset:offset + 999]
        approvers = _approvers(source, chunk, payload['all_users'])
        approver_ids = ','.join(str(u['id']) for u in approvers)
        try:
            if master_id == 10:
                stamp = now()
                stopped = value(payload, 'action') == 'stop'
                status = 23 if stopped else -1
                comment = ('Stopped manually on ' if stopped else 'Resumed on ') + f'{stamp.year}.{stamp.month}.{stamp.day}'
                live = list(MdmSeasonCurrent.objects.filter(source=source).order_by('ordinal'))
                old = [{name: getattr(item, name) for name in SEASON_FIELDS}
                       for item in live for row in chunk if row_key(item) == payload_key(row)]
                requested = [{**r, 'Status': status, 'Comment': comment} for r in old]
                for rows in (old, requested):
                    for r in rows:
                        r['Status1'] = r.pop('Status')
            else:
                requested = [convert(r, keys, master_id) for r in chunk]
                old = [dict(r) for r in requested]
            # GetValuesSPF passes actiontype2 even for ADD; the parent header is1.
            requested_model.objects.bulk_create([requested_model(source=source,
                TaskId=task_id, ActionType=2, Approved=False, Reverted=False, **r)
                for r in requested])
            if master_id != 10:
                MdmSeasonRequested.objects.filter(source=source, ActivateDBM=None).update(ActivateDBM=False)
            history_model.objects.bulk_create([history_model(source=source,
                TaskId=task_id, ActionType=2, **r) for r in old])
            history_model.objects.filter(source=source, TaskId=task_id).update(ApproverId=approver_ids)
            if not supplied_id and offset == 0:
                name = {10: 'Modify-SeasonlityStatus', 11: 'Add-AbsoluteValueSeasonality',
                        12: 'Add-DeltaPercentageSeasonality'}[master_id]
                MdmTask.objects.create(source=source, TaskID=task_id, PendingSince=database_now(),
                    TaskName=name, ApproverId=approver_ids, RequesterId=str(actor['id']),
                    MasterId=str(master_id), Actiontype=action,
                    ColumnList=','.join([mapping[k] for k in keys] +
                        ['ActionType', 'Approved', 'Reverted', 'TaskId']),
                    ApproversName=','.join(u['name'] for u in approvers),
                    RequesterName=actor['name'], TaskStatus='1')
                MdmSubTask.objects.bulk_create([MdmSubTask(source=source, TaskID=task_id,
                    ApproverId=str(u['id']), ApproverName=u['name'], TaskStatus='1') for u in approvers])
        except (DatabaseError, ValueError, TypeError):
            log.exception('Native Seasonality submission statement failure')
            raise  # The two-argument PostQuery propagates; the upload ends at500.
    return dict(status=200, msg=None, taskId=task_id, errorCount=str(error_count),
                error=errors, conflictErrorCount='0', conflictError=None)


@decision
def delete(source, task_id, actor):
    task = require_requester(source, task_id, actor)
    task = header(source, task_id)
    for model in (*models(task.MasterId), MdmTask, MdmSubTask):
        model.objects.filter(source=source, **{
            'TaskID' if model in (MdmTask, MdmSubTask) else 'TaskId': task_id}).delete()


def _effect(source, master_id, incoming):
    if master_id == 10:
        for target in MdmSeasonCurrent.objects.filter(source=source).order_by('ordinal'):
            values = [(r.Status1, r.Comment) for r in incoming if row_key(r) == row_key(target)]
            if values and any(v != values[0] for v in values[1:]):
                raise ValueError('native duplicate status UPDATE is incomparable')
            if values:
                MdmSeasonCurrent.objects.filter(pk=target.pk).update(Status=values[0][0],
                    Comment=values[0][1], revision=F('revision') + 1)
        return
    existing = {row_key(r) for r in MdmSeasonQueue.objects.filter(source=source)}
    MdmSeasonQueue.objects.bulk_create([MdmSeasonQueue(source=source,
        **{n: getattr(r, n) for n in REQUEST_FIELDS if n != 'ActivateDBM'}, ActivateDBM=False)
        for r in incoming if row_key(r) not in existing])
    for target in MdmSeasonQueue.objects.filter(source=source).order_by('id'):
        matches = [r for r in incoming if row_key(r) == row_key(target)]
        updates = [{n: (getattr(target, n) if getattr(r, n) in (None, 0, date(1900, 1, 1))
                       else getattr(r, n)) for n in UPDATE_FIELDS} for r in matches]
        if updates and any(v != updates[0] for v in updates[1:]):
            raise ValueError('native duplicate seasonal UPDATE is incomparable')
        if updates:
            MdmSeasonQueue.objects.filter(pk=target.pk).update(**updates[0], revision=F('revision') + 1)


@decision
def approve(source, payload, actor):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if task is None or task.MasterId not in ('10', '11', '12'):
        raise TaskDenied('task_reviewer_required')
    master_id = int(task.MasterId)
    requested_model, history_model = models(master_id)
    history = list(history_model.objects.filter(source=source, TaskId=task_id).order_by('id'))
    requested = list(requested_model.objects.filter(source=source, TaskId=task_id).order_by('id'))
    sku_scope, location_scope = scopes(source, payload)
    decisions = {}
    for row in value(payload, 'data'):
        if any(row.get(n) is None for n in ('sc', 'wc', 'status', 'comments')):
            raise ValueError('native decision key/status value.ToString requires a value')
        key = payload_key(row)
        matching = [r for r in history if row_key(r) == key]
        if (not matching or not all(assigned(r.ApproverId, actor['id']) for r in matching)
                or key[0] not in sku_scope or key[1] not in location_scope):
            raise TaskDenied('task_row_reviewer_scope_required')
        result = (str(row['status']), str(row['comments']))
        if key in decisions and decisions[key] != result:
            raise ValueError('native duplicate decision UPDATE is incomparable')
        decisions[key] = result
    if not decisions:
        raise TaskDenied('task_row_reviewer_scope_required')
    bump_task(source, master_id, task_id)
    try:
        for row in requested:
            result = decisions.get(row_key(row))
            if result:
                requested_model.objects.filter(pk=row.pk).update(Approved=result[0] == '3', Reverted=result[0] == '4')
        for row in history:
            result = decisions.get(row_key(row))
            if result:
                history_model.objects.filter(pk=row.pk).update(Status=result[0], Comments=result[1],
                    **{'ApproverBy' if master_id == 10 else 'ApprovedBy': str(actor['id'])})
        _effect(source, master_id, list(requested_model.objects.filter(
            source=source, TaskId=task_id, Approved=True).order_by('id')))
    except DatabaseError:
        # UpdateApprovedData uses the one-argument PostQuery, whose native SQL
        # exception handler logs and returns before task-status processing.
        log.exception('Native Seasonality approval statement failure')
    all_history = list(history_model.objects.filter(source=source, TaskId=task_id))
    mine = [r for r in all_history if assigned(r.ApproverId, actor['id'])]
    completed = bool(mine) and all(r.Status in ('3', '4') for r in mine)
    stamp = database_now().strftime('%d/%m/%Y %I:%M %p')
    MdmSubTask.objects.filter(source=source, TaskID=task_id,
        ApproverId=str(actor['id'])).update(ApprovedOrRejectedDate=stamp)
    if completed:
        for sub in MdmSubTask.objects.filter(source=source, TaskID=task_id).exclude(ApprovedOrRejectedDate=None):
            rows = [r for r in all_history if assigned(r.ApproverId, sub.ApproverId)]
            if rows and all(r.Status in ('3', '4') for r in rows):
                status = (('4' if master_id == 10 else '2') if all(r.Status == '3' for r in rows)
                          else '6' if all(r.Status == '4' for r in rows)
                          else ('5' if master_id == 10 else '3'))
                MdmSubTask.objects.filter(pk=sub.pk).update(TaskStatus=status, ApprovedOrRejectedDate=stamp)
        MdmSubTask.objects.filter(source=source, TaskID=task_id,
            ApprovedOrRejectedDate=None).update(TaskStatus='8')
    else:
        MdmSubTask.objects.filter(source=source, TaskID=task_id,
            ApproverId=str(actor['id'])).update(TaskStatus='3')
    return dict(status=200, msg='Data submitted successfully' +
        (' and Task status updated' if completed else 'Task status not updated') + ' ',
        taskId=task_id, errorCount=None, error=None, conflictErrorCount=None, conflictError=None)
