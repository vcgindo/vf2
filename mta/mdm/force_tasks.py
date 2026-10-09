"""Master-13 submission and decisions with deployed statement effects."""
import logging

from django.db import DatabaseError
from django.db.models import F

from mta.mdm.clock import database_now
from mta.mdm.drafts import now, value
from mta.mdm.force import ALIASES
from mta.mdm.force_revisions import bump_task
from mta.mdm.skuloc_tasks import _approvers
from mta.mdm.supplier_permissions import scope
from mta.mdm.supplier_revisions import decision
from mta.mdm.task_reads import TaskDenied, assigned, header, require_requester, sql_key
from mta.runtime.mdm_force_models import (MdmForceHistory, MdmForceQueue,
    MdmForceRequested, MdmForceUploadLog)
from mta.runtime.mdm_models import (MdmLocationAttributes, MdmSkuAttributes,
                                    MdmSubTask, MdmTask)
from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent, MdmSkuLocPair


log = logging.getLogger(__name__)
NAMES = ('SKUCode', 'WhCode')


def row_key(row):
    return sql_key(row.SKUCode), sql_key(row.WhCode)


def payload_key(row):
    return sql_key(row['sc']), sql_key(row['wc'])


def scopes(source, payload):
    skus = scope(source, MdmSkuAttributes, 'SKUCode', 'SL', 'products',
                 payload.get('product_permissions') or [])
    locations = scope(source, MdmLocationAttributes, 'WHCode', 'LL', 'locations',
                      payload.get('location_permissions') or [])
    return ({sql_key(code) for code in skus}, {sql_key(code) for code in locations})


def _auth_key(text):
    """C# ToLower().Trim(), distinct from SQL trailing-space comparison."""
    return text.strip().lower() if text is not None else None


def _submission_scopes(source, payload):
    skus = scope(source, MdmSkuAttributes, 'SKUCode', 'SL', 'products',
                 payload.get('product_permissions') or [])
    locations = scope(source, MdmLocationAttributes, 'WHCode', 'LL', 'locations',
                      payload.get('location_permissions') or [])
    return ({_auth_key(code) for code in skus}, {_auth_key(code) for code in locations})


def convert(row, keys):
    result = {}
    for alias in keys:
        raw = row[alias]
        if alias == 'nn':
            if raw is None:
                result[ALIASES[alias]] = None
            else:
                number = int(str(raw).strip() or '0')
                if not -2147483648 <= number <= 2147483647:
                    raise ValueError('native int32 overflow')
                result[ALIASES[alias]] = number
        else:
            if raw is None:
                raise ValueError('native key value.ToString requires a value')
            result[ALIASES[alias]] = str(raw)
    return result


def _update_old_norms(source, task_id):
    """Native task-wide history UPDATE after the submitted history INSERT."""
    from mta.mdm.force_display import history_model
    current = list(history_model(source, task_id).objects.filter(
        source=source, owner='Importer').order_by('ordinal'))
    updates = []
    for row in MdmForceHistory.objects.filter(source=source, TaskId=task_id).order_by('id'):
        matches = [item.Norm for item in current
                   if sql_key(item.SKUCode) == sql_key(row.SKUCode)
                   and sql_key(item.WhCode) == sql_key(row.WhCode)]
        if matches and any(item != matches[0] for item in matches[1:]):
            raise ValueError('native duplicate current Norm UPDATE is incomparable')
        if matches:
            updates.append((row.pk, matches[0]))
    for pk, norm in updates:
        MdmForceHistory.objects.filter(pk=pk).update(NewNorm=norm)


@decision
def submit(source, payload, actor, action):
    if int(value(payload, 'id')) != 13:
        raise ValueError('MDM family is not delivered')
    if action != 2:
        raise ValueError('Force Norm Change supports Modify only')
    supplied_id = value(payload, 'taskId')
    if supplied_id:
        require_requester(source, supplied_id, actor)
    data = value(payload, 'data')
    keys = list(data[0])
    task_id = supplied_id or str(actor['id']) + '_' + now().strftime('%Y%m%d%H%M%S')

    # DataValidation silently omits missing-key rows. Exact pair membership is
    # evaluated before the case-insensitive hierarchy authorization pass.
    keyed = [row for row in data if 'sc' in row and 'wc' in row]
    pairs = set(MdmSkuLocPair.objects.filter(source=source, owner='Importer')
                .values_list('SKUCode', 'LocCode'))
    missing = [row for row in keyed if (row['sc'], row['wc']) not in pairs]
    allowed = [row for row in keyed if not any(row is item for item in missing)]
    errors = []
    if missing:
        errors.append(dict(errorType='SKU and Location Code does not exists ', errorData=missing))
    sku_scope, location_scope = _submission_scopes(source, payload)
    denied = [row for row in allowed if _auth_key(row['sc']) not in sku_scope
              or _auth_key(row['wc']) not in location_scope]
    allowed = [row for row in allowed if not any(row is item for item in denied)]
    if denied:
        errors.append(dict(errorType='UnAuthorized SKUCodes OR Location codes', errorData=denied))

    # DataValidation accepts null and generates a task ID, but the upload method
    # calls requestdata.TaskId.ToString while assembling the first accepted
    # chunk. PostQuery has not run yet, so the failure leaves no statement
    # effects. With no accepted rows that call is never reached.
    if supplied_id is None and allowed:
        raise ValueError('native TaskId.ToString requires a value')

    for offset in range(0, len(allowed), 999):
        chunk = allowed[offset:offset + 999]
        selected = _approvers(source, chunk, payload['all_users'])
        approver_ids = ','.join(str(user['id']) for user in selected)
        approver_names = ','.join(user['name'] for user in selected)
        try:
            converted = [convert(row, keys) for row in chunk]
            MdmForceRequested.objects.bulk_create([MdmForceRequested(source=source,
                ActionType=2, Approved=False, Reverted=False, TaskId=task_id, **row)
                for row in converted])
            # Native statement is task-wide, including rows supplied in an
            # earlier forwarded batch under the same task identity.
            MdmForceRequested.objects.filter(source=source, TaskId=task_id).update(
                RequestedBy=str(actor['id']))
            MdmForceHistory.objects.bulk_create([MdmForceHistory(source=source,
                SKUCode=row['SKUCode'], WhCode=row['WhCode'], NewNorm=row.get('NewNorm'),
                ActionType=2, TaskId=task_id) for row in converted])
            _update_old_norms(source, task_id)
            MdmForceUploadLog.objects.bulk_create([MdmForceUploadLog(source=source,
                SKUCode=row['SKUCode'], WHCode=row['WhCode'], NewNorm=row.get('NewNorm'),
                Approved=False, RequestedBy=actor['name'], ActionTimeStamp=database_now(),
                ActionId=1) for row in converted])
            MdmForceHistory.objects.filter(source=source, TaskId=task_id).update(
                ApproverId=approver_ids)
            if not supplied_id and offset == 0:
                fields = [ALIASES[key] for key in keys]
                MdmTask.objects.create(source=source, TaskID=task_id,
                    PendingSince=database_now(), TaskName='Modify-ForceNormChange',
                    ApproverId=approver_ids, RequesterId=str(actor['id']), MasterId='13',
                    Actiontype=2, ColumnList=','.join(fields + [
                        'ActionType', 'Approved', 'Reverted', 'TaskId']),
                    ApproversName=approver_names,
                    RequesterName=actor['name'], TaskStatus='1')
                MdmSubTask.objects.bulk_create([MdmSubTask(source=source, TaskID=task_id,
                    ApproverId=str(user['id']), ApproverName=user['name'], TaskStatus='1')
                    for user in selected])
        except (DatabaseError, ValueError, TypeError):
            # The deployed PostQuery logs failures and submission still returns
            # its assembled response. Earlier statements remain committed.
            log.exception('Native Force Norm submission statement failure')
    return dict(status=200, msg=' Data Saved Sucessfully', taskId=task_id,
        errorCount=str(sum(len(item['errorData']) for item in errors)), error=errors,
        conflictErrorCount='0', conflictError=None)


def delete(source, task_id, actor):
    require_requester(source, task_id, actor)
    for model, field in ((MdmForceHistory, 'TaskId'), (MdmForceRequested, 'TaskId'),
                         (MdmTask, 'TaskID'), (MdmSubTask, 'TaskID')):
        model.objects.filter(source=source, **{field: task_id}).delete()


@decision
def approve(source, payload, actor):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if task is None or task.MasterId != '13' or task.Actiontype != 2:
        raise TaskDenied('task_reviewer_required')
    rows = value(payload, 'data')
    history = list(MdmForceHistory.objects.filter(source=source, TaskId=task_id))
    requested = list(MdmForceRequested.objects.filter(source=source, TaskId=task_id))
    sku_scope, location_scope = scopes(source, payload)
    decisions = {}
    for row in rows:
        # Decision getValues permits null nn; key/status/comment assembly does not.
        if any(row.get(name) is None for name in ('sc', 'wc', 'status', 'comments')):
            raise ValueError('native decision key/status value.ToString requires a value')
        identity = payload_key(row)
        matching_history = [item for item in history if row_key(item) == identity]
        if (not matching_history
                or not all(assigned(item.ApproverId, actor['id']) for item in matching_history)
                or identity[0] not in sku_scope or identity[1] not in location_scope):
            raise TaskDenied('task_row_reviewer_scope_required')
        decision_value = (str(row['status']), str(row['comments']))
        if identity in decisions and decisions[identity] != decision_value:
            raise ValueError('native duplicate decision UPDATE is incomparable')
        decisions[identity] = decision_value
    if not decisions:
        raise TaskDenied('task_row_reviewer_scope_required')

    bump_task(source, task_id)
    for item in requested:
        result = decisions.get(row_key(item))
        if result:
            MdmForceRequested.objects.filter(pk=item.pk).update(
                Approved=result[0] == '3', Reverted=result[0] == '4')
    for item in history:
        result = decisions.get(row_key(item))
        if result:
            MdmForceHistory.objects.filter(pk=item.pk).update(Status=result[0],
                Comments=result[1], ApprovedBy=str(actor['id']))

    incoming = list(MdmForceRequested.objects.filter(
        source=source, TaskId=task_id, Approved=True))
    existing = {row_key(item) for item in MdmForceQueue.objects.filter(source=source)}
    MdmForceQueue.objects.bulk_create([MdmForceQueue(source=source,
        SKUCode=item.SKUCode, WhCode=item.WhCode, NewNorm=item.NewNorm,
        Approved=item.Approved, RequestedBy=item.RequestedBy)
        for item in incoming if row_key(item) not in existing])
    for target in MdmForceQueue.objects.filter(source=source):
        matches = [item for item in incoming if row_key(item) == row_key(target)]
        updates = [target.NewNorm if item.NewNorm is None or item.NewNorm == 0 else item.NewNorm
                   for item in matches]
        if updates and any(item != updates[0] for item in updates[1:]):
            raise ValueError('native duplicate ForceNormChange UPDATE is incomparable')
        if updates:
            # Native UPDATE runs even when fallback or equality leaves NewNorm
            # unchanged; revision records that semantic write occurrence.
            MdmForceQueue.objects.filter(pk=target.pk).update(
                NewNorm=updates[0], revision=F('revision') + 1)

    for status in ('4', '3'):
        MdmForceUploadLog.objects.bulk_create([MdmForceUploadLog(source=source,
            SKUCode=row['sc'], WHCode=row['wc'],
            RequestedBy=actor['name'], ActionTimeStamp=database_now(), ActionId=int(status),
            ) for row in rows if str(row['status']) == status])

    all_history = list(MdmForceHistory.objects.filter(source=source, TaskId=task_id))
    mine = [item for item in all_history if assigned(item.ApproverId, actor['id'])]
    completed = bool(mine) and all(item.Status in ('3', '4') for item in mine)
    stamp = database_now().strftime('%d/%m/%Y %I:%M %p')
    MdmSubTask.objects.filter(source=source, TaskID=task_id,
        ApproverId=str(actor['id'])).update(ApprovedOrRejectedDate=stamp)
    if completed:
        for sub in MdmSubTask.objects.filter(source=source, TaskID=task_id).exclude(
                ApprovedOrRejectedDate=None):
            assigned_rows = [item for item in all_history if assigned(item.ApproverId, sub.ApproverId)]
            if assigned_rows and all(item.Status in ('3', '4') for item in assigned_rows):
                status = ('2' if all(item.Status == '3' for item in assigned_rows) else
                          '6' if all(item.Status == '4' for item in assigned_rows) else '3')
                MdmSubTask.objects.filter(pk=sub.pk).update(
                    TaskStatus=status, ApprovedOrRejectedDate=stamp)
        MdmSubTask.objects.filter(source=source, TaskID=task_id,
                                  ApprovedOrRejectedDate=None).update(TaskStatus='8')
    else:
        MdmSubTask.objects.filter(source=source, TaskID=task_id,
            ApproverId=str(actor['id'])).update(TaskStatus='3')
    return dict(status=200,
        msg='Data submitted successfully' + (' and Task status updated' if completed
            else 'Task status not updated') + ' ', taskId=task_id, errorCount=None,
        error=None, conflictErrorCount=None, conflictError=None)
