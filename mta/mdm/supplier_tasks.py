"""SOB/MOQ native task staging and row decisions.

Raw masters are deliberately not changed here. Approved queues are consumed at
the importer boundary; whole-task DB-updated status belongs to that boundary.
"""
from collections import defaultdict
import logging
import math

from django.db import DatabaseError
from django.db.models import F
from mta.mdm.supplier_revisions import decision, bump_task
from mta.mdm.clock import database_now
from mta.mdm.drafts import now, value
from mta.mdm.supplier import CONFIG, setting
from mta.mdm.skuloc_tasks import _approvers
from mta.mdm.supplier_permissions import scope
from mta.mdm.task_reads import TaskDenied, assigned, header, require_requester, sql_key
from mta.presentation.context import permission_catalogue
from mta.runtime.mdm_models import (MdmSkuAttributes, MdmLocationAttributes,
    MdmSkuDescription, MdmTask, MdmSubTask)
from mta.runtime.mdm_skuloc_models import MdmSkuLocPair
from mta.runtime.mdm_supplier_models import (MdmSupplierConfiguration, MdmSobRaw,
    MdmMoqRaw1, MdmMoqRaw2, MdmSobRequested, MdmMoqRequested, MdmSobHistory,
    MdmMoqHistory, MdmSobApproved, MdmMoqWithDestinationApproved,
    MdmMoqWithoutDestinationApproved, MdmSobUploadLog, MdmMoqUploadLog)

log = logging.getLogger(__name__)


def models_for(source, master_id):
    if master_id == 4:
        return MdmSobRaw, MdmSobRequested, MdmSobHistory, MdmSobApproved, MdmSobUploadLog
    if master_id == 5:
        dest = setting(source) == 'WithDestLoc'
        return (MdmMoqRaw2 if dest else MdmMoqRaw1, MdmMoqRequested, MdmMoqHistory,
                MdmMoqWithDestinationApproved if dest else MdmMoqWithoutDestinationApproved,
                MdmMoqUploadLog)
    raise ValueError('Not a supplier family')


def key_names(source, master_id):
    return ('SKUCode', 'WhCode', 'SupplierCode') if master_id == 4 or setting(source) == 'WithDestLoc' else ('SKUCode', 'SupplierCode')


def row_key(row, names, *, raw=False, sql=True):
    values = tuple(getattr(row, 'WHCode' if raw and n == 'WhCode' else n) for n in names)
    return tuple(sql_key(v) for v in values) if sql else values


def payload_key(row, names, *, sql=True):
    aliases = {'SKUCode': 'sc', 'WhCode': 'wc', 'SupplierCode': 'spc'}
    values = tuple(row[aliases[n]] for n in names)
    return tuple(sql_key(v) for v in values) if sql else values


def scopes(source, payload):
    sku = scope(source, MdmSkuAttributes, 'SKUCode', 'SL', 'products', payload.get('product_permissions') or [])
    loc = scope(source, MdmLocationAttributes, 'WHCode', 'LL', 'locations', payload.get('location_permissions') or [])
    return ({code.lower().strip() for code in sku}, {code.lower().strip() for code in loc})


def approvers(source, rows, users, destination):
    if destination:
        return _approvers(source, rows, users)
    skus = {sql_key(r['sc']) for r in rows}
    triples = {tuple(sql_key(getattr(r, 'SL' + str(i))) for i in range(1, 4))
        for r in MdmSkuAttributes.objects.filter(source=source, owner='Importer') if sql_key(r.SKUCode) in skus}
    ids = {r['id'] for r in permission_catalogue()['products']['records']
           if tuple(sql_key(r['level_' + str(i)]) for i in range(1, 4)) in triples}
    result = []
    for user in users:
        if ids.intersection(user['product_id']) and not any(str(u['id']) == str(user['id']) for u in result):
            result.append(user)
    return result


def convert(master_id, row, keys):
    aliases = {r['Col_Code']: r['TableField'] for r in CONFIG[master_id]['UI_MDMConfig']}
    result = {}
    for alias in keys:
        raw = row[alias]
        if raw is None:
            raise ValueError('native value.ToString requires a value')
        text = str(raw)
        if alias == 'sb':
            if text.strip().upper() == 'NULL':
                result[aliases[alias]] = None
                continue
            number = float(text)
            if not math.isfinite(number):
                raise ValueError('native float53 requires a finite value')
            result[aliases[alias]] = number
        elif alias == 'mq':
            number = int(text.strip() or '0')
            if not -2147483648 <= number <= 2147483647:
                raise ValueError('native int32 overflow')
            result[aliases[alias]] = number
        else:
            result[aliases[alias]] = text
    return result


def submit(source, payload, actor, action):
    master_id = int(value(payload, 'id'))
    raw_model, requested_model, history_model, _, audit_model = models_for(source, master_id)
    names = key_names(source, master_id); destination = 'WhCode' in names
    supplied_id = value(payload, 'taskId')
    if supplied_id is None:
        raise ValueError('native TaskId.ToString requires a value')
    if supplied_id:
        require_requester(source, supplied_id, actor)
    data = value(payload, 'data'); keys = list(data[0])
    sku_scope, loc_scope = scopes(source, payload)
    allowed = [r for r in data if r['sc'].lower().strip() in sku_scope
               and (not destination or r['wc'].lower().strip() in loc_scope)]
    errors = []
    def exclude(rows, message):
        nonlocal allowed
        if rows:
            errors.append(dict(errorType=message, errorData=rows))
            allowed = [r for r in allowed if not any(r is other for other in rows)]
    denied = [r for r in data if not any(r is other for other in allowed)]
    if master_id == 5 and destination:
        sku_denied = [r for r in data if r['sc'].lower().strip() not in sku_scope]
        if sku_denied:
            errors.append(dict(errorType='UnAuthorized SKU Codes', errorData=sku_denied))
    if denied:
        errors.append(dict(errorType=('Either you are Unauthorized for SKUCode or Location Code or both '
            if master_id == 4 else 'UnAuthorized SKU & Location Codes' if destination else 'UnAuthorized SKU Codes'), errorData=denied))
    if master_id == 4 and action != 3:
        pairs = set(MdmSkuLocPair.objects.filter(source=source, owner='Importer').values_list('SKUCode', 'LocCode'))
        exclude([r for r in allowed if (r['sc'], r['wc']) not in pairs],
                'Either SKU Code or Location code or both does not exist ')
    raw_rows = list(raw_model.objects.filter(source=source).order_by('ordinal'))
    eligibility_names = names[:2] if master_id == 5 and destination and action == 3 else names
    existing = {row_key(r, eligibility_names, raw=True, sql=False) for r in raw_rows}
    if master_id == 4:
        message = (' These are Duplicate SKUCodes , Location Codes and SupplierCode ' if action == 1 else
                   'SKU , Location code,SupplierCode not exist ' if action == 3 else
                   'SKUCodes , Location Codes,Supplier Code Does not Exist ')
    else:
        grain = 'SKUCodes-WHcode-SupplierCode' if destination else 'SKUCodes-SupplierCode'
        message = 'MOQ For these ' + grain + (' already exist' if action == 1 else ' does  not exist.' if destination else ' does not exist.')
    exclude([r for r in allowed if (payload_key(r, eligibility_names, sql=False) in existing) == (action == 1)], message)
    conflicts = None; conflict_count = 0
    if (action == 2 or master_id == 5 and action == 1) and not value(payload, 'isOverwrite', False):
        conflict_names = ('SKUCode', 'WhCode') if master_id == 4 else ('SKUCode', 'SupplierCode')
        pending = list(history_model.objects.filter(source=source, Status=None))
        pending_keys = {row_key(h, conflict_names, sql=False) for h in pending}
        conflicting = [r for r in allowed if payload_key(r, conflict_names, sql=False) in pending_keys]
        if conflicting:
            conflict_count = len(conflicting); grouped = defaultdict(list)
            for task in MdmTask.objects.filter(source=source, MasterId=str(master_id), Actiontype=2).order_by('RequesterId'):
                for request in requested_model.objects.filter(source=source, TaskId=task.TaskID):
                    for old in pending:
                        if old.TaskId != task.TaskID or row_key(old, conflict_names) != row_key(request, conflict_names):
                            continue
                        for row in conflicting:
                            if payload_key(row, conflict_names) == row_key(request, conflict_names):
                                aliases = {r['Col_Code']: r['TableField'] for r in CONFIG[master_id]['UI_MDMConfig']}
                                grouped[(task.RequesterId, task.RequesterName)].append(dict(
                                    oldData={k: getattr(request, aliases[k]) for k in keys}, RequestedData=row))
            conflicts = [dict(user=name, conflictdetails=rows) for (_, name), rows in grouped.items()]
            allowed = [r for r in allowed if not any(r is other for other in conflicting)]
    task_id = supplied_id or str(actor['id']) + '_' + now().strftime('%Y%m%d%H%M%S')
    config = MdmSupplierConfiguration.objects.get(source=source)
    for offset in range(0, len(allowed), 999):
        chunk = allowed[offset:offset + 999]
        assignment_rows = data if master_id == 4 or action == 3 else chunk
        selected = approvers(source, assignment_rows, payload['all_users'], destination)
        ids = ','.join(str(u['id']) for u in selected); user_names = ','.join(u['name'] for u in selected)
        # Preserve the deployed Remove failure. The explicitly approved
        # destination-Modify correction below uses its own matching Raw2 rows.
        if master_id == 5 and action == 3 and 'wc' in keys:
            log.warning('Native MOQ history batch contains unavailable Raw1.WhCode')
            continue
        try:
            converted = [convert(master_id, row, keys) for row in chunk]
            fields = list(converted[0])
            requested_model.objects.bulk_create([requested_model(source=source, **r,
                TaskId=task_id, ActionType=(1 if master_id == 4 and action != 3 else action),
                Approved=False, Reverted=False) for r in converted])
            if action == 1:
                history = converted
            elif master_id == 4:
                wanted = {payload_key(r, names) for r in chunk}
                history = [{n: getattr(r, 'WHCode' if n == 'WhCode' else n) for n in fields}
                           for r in raw_rows if row_key(r, names, raw=True) in wanted]
            elif destination and action == 2:
                wanted = {payload_key(r, names) for r in chunk}
                history = [{n: getattr(r, 'WHCode' if n == 'WhCode' else n) for n in fields}
                           for r in raw_rows if row_key(r, names, raw=True) in wanted]
            else:
                skus = {sql_key(r['sc']) for r in chunk}; suppliers = {sql_key(r['spc']) for r in chunk}
                history = []
                for r in MdmMoqRaw1.objects.filter(source=source).order_by('ordinal'):
                    if action == 2:
                        copies = int(sql_key(r.SKUCode) in skus and sql_key(r.SupplierCode) in suppliers)
                    else:
                        copies = sum(payload_key(row, ('SKUCode', 'SupplierCode')) == row_key(r, ('SKUCode', 'SupplierCode')) for row in chunk)
                        copies *= sum(sql_key(d.SKUCode) == sql_key(r.SKUCode) for d in MdmSkuDescription.objects.filter(source=source, owner='Importer'))
                    history.extend([{n: getattr(r, n) for n in fields}] * copies)
            history_model.objects.bulk_create([history_model(source=source, TaskId=task_id, ApproverId=ids, **r) for r in history])
            if action == 1:
                history_model.objects.filter(source=source, TaskId=task_id).update(ApproverId=ids)
            if config.upload_log_active:
                audit_model.objects.bulk_create([audit_model(source=source, **r, UserName=actor['name'],
                    ActionTimeStamp=database_now(), ActionId=6 if action == 3 else 5) for r in converted])
            if not supplied_id and offset == 0:
                MdmTask.objects.create(source=source, TaskID=task_id, PendingSince=database_now(), MasterId=str(master_id),
                    TaskName={1:'Add',2:'Modify',3:'Remove'}[action] + ('-SOBMaster' if master_id == 4 else '-MOQMaster'),
                    Actiontype=action, ColumnList=','.join(fields), RequesterId=str(actor['id']), RequesterName=actor['name'],
                    ApproverId=ids, ApproversName=user_names, TaskStatus='1')
                sub_users = selected if master_id == 4 and action != 3 else payload['all_users']
                MdmSubTask.objects.bulk_create([MdmSubTask(source=source, TaskID=task_id,
                    ApproverId=str(u['id']), ApproverName=u['name'], TaskStatus='1') for u in sub_users])
        except (DatabaseError, ValueError, TypeError):
            log.exception('Native supplier submission statement failure')
    return dict(status=200, msg={1:' Data Saved Sucessfully',2:' Data modified Sucessfully',3:' Data removed Sucessfully'}[action],
        taskId=task_id, errorCount=str(sum(len(e['errorData']) for e in errors)), error=errors,
        conflictErrorCount=str(conflict_count), conflictError=conflicts)


def delete(source, task_id, actor):
    require_requester(source, task_id, actor)
    task = header(source, task_id)
    _, requested, history, _, _ = models_for(source, int(task.MasterId))
    for model, field in ((history, 'TaskId'), (requested, 'TaskId'), (MdmTask, 'TaskID'), (MdmSubTask, 'TaskID')):
        model.objects.filter(source=source, **{field: task_id}).delete()


@decision
def approve(source, payload, actor):
    task_id = value(payload, 'taskId'); task = header(source, task_id)
    if task is None or task.MasterId not in ('4', '5'):
        raise TaskDenied('task_reviewer_required')
    master_id = int(task.MasterId)
    _, requested_model, history_model, queue_model, audit_model = models_for(source, master_id)
    names = key_names(source, master_id); scalar = 'SOB' if master_id == 4 else 'MOQ'
    history = list(history_model.objects.filter(source=source, TaskId=task_id))
    rows = value(payload, 'data'); decisions = {}
    # Native getValues calls ToString on every first-row column before SQL.
    if rows and any(row[key] is None for row in rows for key in rows[0]):
        raise ValueError('native approval value.ToString requires a value')
    sku_scope, loc_scope = scopes(source, payload)
    for row in rows:
        identity = payload_key(row, names)
        matching = [h for h in history if row_key(h, names) == identity]
        if (not matching or not all(assigned(h.ApproverId, actor['id']) for h in matching)
                or row['sc'].lower().strip() not in sku_scope
                or 'WhCode' in names and row['wc'].lower().strip() not in loc_scope):
            raise TaskDenied('task_row_reviewer_scope_required')
        decision = (str(row['status']), str(row['comments']))
        if identity in decisions and decisions[identity] != decision:
            raise ValueError('native duplicate decision UPDATE is incomparable')
        decisions[identity] = decision
    if not decisions:
        raise TaskDenied('task_row_reviewer_scope_required')
    bump_task(source, master_id, task_id)
    for request in requested_model.objects.filter(source=source, TaskId=task_id):
        decision = decisions.get(row_key(request, names))
        if decision:
            requested_model.objects.filter(pk=request.pk).update(Approved=decision[0] == '3', Reverted=decision[0] == '4')
    for old in history:
        decision = decisions.get(row_key(old, names))
        if decision:
            history_model.objects.filter(pk=old.pk).update(Status=decision[0], Comments=decision[1],
                ApprovedBy=str(actor['id']) if master_id == 4 else int(actor['id']))
    incoming = list(requested_model.objects.filter(source=source, TaskId=task_id, Approved=True))
    existing = {row_key(r, names) for r in queue_model.objects.filter(source=source)}
    columns = [f.name for f in queue_model._meta.fields if f.name not in ('id', 'source', 'revision')]
    queue_model.objects.bulk_create([queue_model(source=source, **{n: getattr(r, n) for n in columns})
        for r in incoming if row_key(r, names) not in existing])
    for target in queue_model.objects.filter(source=source):
        matches = [r for r in incoming if row_key(r, names) == row_key(target, names)]
        values = [getattr(r, scalar) for r in matches]
        updates = [getattr(target, scalar) if v is None or v == 0 else v for v in values]
        if updates and any(v != updates[0] for v in updates[1:]):
            raise ValueError('native duplicate approved-input UPDATE is incomparable')
        if updates:
            queue_model.objects.filter(pk=target.pk).update(**{scalar: updates[0], 'revision': F('revision') + 1})
    if MdmSupplierConfiguration.objects.get(source=source).upload_log_active:
        aliases = {'sc':'SKUCode', 'wc':'WhCode', 'spc':'SupplierCode'}
        for status in ('4', '3'):
            audit_model.objects.bulk_create([audit_model(source=source,
                **{aliases[k]: r[k] for k in aliases if aliases[k] in names},
                UserName=actor['name'], ActionTimeStamp=database_now(), ActionId=int(status))
                for r in rows if str(r['status']) == status])
    all_history = list(history_model.objects.filter(source=source, TaskId=task_id))
    mine = [h for h in all_history if assigned(h.ApproverId, actor['id'])]
    completed = bool(mine) and all(h.Status in ('3', '4') for h in mine)
    stamp = database_now().strftime('%d/%m/%Y %I:%M %p')
    MdmSubTask.objects.filter(source=source, TaskID=task_id, ApproverId=str(actor['id'])).update(ApprovedOrRejectedDate=stamp)
    if completed:
        for sub in MdmSubTask.objects.filter(source=source, TaskID=task_id).exclude(ApprovedOrRejectedDate=None):
            assigned_rows = [h for h in all_history if assigned(h.ApproverId, sub.ApproverId)]
            if assigned_rows and all(h.Status in ('3', '4') for h in assigned_rows):
                status = '2' if all(h.Status == '3' for h in assigned_rows) else '6' if all(h.Status == '4' for h in assigned_rows) else '3'
                MdmSubTask.objects.filter(pk=sub.pk).update(TaskStatus=status, ApprovedOrRejectedDate=stamp)
        MdmSubTask.objects.filter(source=source, TaskID=task_id, ApprovedOrRejectedDate=None).update(TaskStatus='8')
    else:
        MdmSubTask.objects.filter(source=source, TaskID=task_id, ApproverId=str(actor['id'])).update(TaskStatus='3')
    return dict(status=200, msg='Data submitted successfully' + (' and Task status updated' if completed else 'Task status not updated') + ' ',
        taskId=task_id, errorCount=None, error=None, conflictErrorCount=None, conflictError=None)
