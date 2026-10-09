"""Native task review/download/history projections for masters 7, 8, and 9."""
from collections import defaultdict
from datetime import timedelta

from mta.mdm.clock import database_now
from mta.mdm.drafts import omit_nulls, value
from mta.mdm.force_reads import _scope_count
from mta.mdm.force_tasks import row_key, scopes
from mta.mdm.phase_controls_configuration import ALIASES
from mta.mdm.phase_controls_tasks import MASTERS, models
from mta.mdm.task_reads import TaskDenied, assigned, displayed_date, header, sql_key
from mta.runtime.mdm_models import MdmLocationDescription, MdmSkuDescription, MdmTask


DECISIONS = {'3': 'Request approved', '4': 'Request approval reverted/ Rejected'}


def _fields(task, master_id):
    names = (task.ColumnList or '').split(',')
    return [(alias, name) for alias, name in ALIASES[master_id].items()
            if name in names]


def _same_pair(left, right):
    return (left.SKUCode is not None and right.SKUCode is not None
            and left.WhCode is not None and right.WhCode is not None
            and sql_key(left.SKUCode) == sql_key(right.SKUCode)
            and sql_key(left.WhCode) == sql_key(right.WhCode))


def details(source, payload, actor, *, download=False):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if task is None:
        return None
    master_id = int(task.MasterId)
    if master_id not in MASTERS or task.Actiontype != 1:
        raise ValueError('Phase controls support Add only')
    requested_model, history_model, _ = models(master_id)
    complete_history = list(history_model.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    if download:
        approver = str(value(payload, 'approverId'))
        requester = str(task.RequesterId) == str(actor['id'])
        reviewer = approver == str(actor['id']) and any(
            assigned(row.ApproverId, actor['id']) for row in complete_history)
        if not requester and not reviewer:
            raise TaskDenied('task_download_actor_required')
        visible_history = [row for row in complete_history
                           if str(row.ApprovedBy) == approver]
    else:
        visible_history = [row for row in complete_history
            if row.Status is None and assigned(row.ApproverId, actor['id'])]
    histories = defaultdict(list)
    for old in visible_history:
        histories[row_key(old)].append(old)

    requested = list(requested_model.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    requested.sort(key=lambda row: (sql_key(row.WhCode) is not None,
                                     sql_key(row.WhCode) or ''), reverse=not download)
    requested.sort(key=lambda row: (sql_key(row.SKUCode) is not None,
                                     sql_key(row.SKUCode) or ''))
    fields = _fields(task, master_id)
    if not fields:
        raise ValueError('Native phase-control task column list is empty')
    sku_descriptions = list(MdmSkuDescription.objects.filter(
        source=source, owner='Importer').order_by('id')) if not download else []
    location_descriptions = list(MdmLocationDescription.objects.filter(
        source=source, owner='Importer').order_by('id')) if not download else []

    rows = []
    for requested_row in requested:
        matches = [old for old in histories[row_key(requested_row)]
                   if _same_pair(requested_row, old)]
        projection = omit_nulls({alias: getattr(requested_row, name)
                                 for alias, name in fields})
        if download:
            multiplicity = 1
            description_weight = 1
        else:
            sku_matches = [item for item in sku_descriptions
                if requested_row.SKUCode is not None and item.SKUCode is not None
                and sql_key(item.SKUCode) == sql_key(requested_row.SKUCode)] or [None]
            location_matches = [item for item in location_descriptions
                if requested_row.WhCode is not None and item.WHCode is not None
                and sql_key(item.WHCode) == sql_key(requested_row.WhCode)] or [None]
            phase_in_matches = [None]
            if master_id in (7, 8) and requested_row.PhaseInSKUCode is not None:
                phase_in_matches = [item for item in sku_descriptions
                    if item.SKUCode is not None and sql_key(item.SKUCode)
                    == sql_key(requested_row.PhaseInSKUCode)] or [None]
            description_weight = (len(sku_matches) * len(location_matches)
                                  * len(phase_in_matches))
            multiplicity = _scope_count(source, requested_row, payload)
        for old in matches:
            for _ in range(multiplicity * description_weight):
                rows.append(omit_nulls(dict(RN=len(rows) + 1, **projection,
                    Status=DECISIONS.get(old.Status) if download else old.Status,
                    Comments=old.Comments)))
    paging = value(payload, 'paginationParameter')
    if paging is not None:
        page = int(value(paging, 'pageNumber'))
        size = int(value(paging, 'recordsPerPage'))
        rows = [row for row in rows
                if (page - 1) * size + 1 <= row['RN'] <= page * size]
    return [{'MasterId': master_id, 'data': rows}]


def count(source, task_id, actor):
    task = header(source, task_id)
    if task is None or int(task.MasterId) not in MASTERS:
        raise ValueError('Phase-control family is not delivered')
    _, history_model, _ = models(task.MasterId)
    return sum(assigned(row.ApproverId, actor['id']) for row in
               history_model.objects.filter(source=source, TaskId=task_id))


def history(source, payload, actor):
    master_id = int(value(payload, 'masterId'))
    if master_id not in MASTERS:
        raise ValueError('Phase-control family is not delivered')
    sku, wh = value(payload, 'skuCode'), value(payload, 'whCode')
    sku_scope, location_scope = scopes(source, payload)
    if sql_key(sku) not in sku_scope or sql_key(wh) not in location_scope:
        raise TaskDenied('sku_location_scope_required')
    requested_model, history_model, _ = models(master_id)
    tasks = list(MdmTask.objects.filter(source=source, MasterId=str(master_id))
        .exclude(TaskStatus='1').exclude(TaskStatus=None).order_by('PendingSince', 'id'))
    requested = list(requested_model.objects.filter(source=source).order_by('id'))
    histories = list(history_model.objects.filter(source=source).order_by('id'))
    result = []
    for task in tasks:
        fields = _fields(task, master_id)
        for row in requested:
            if (row.TaskId != task.TaskID or row.SKUCode is None or row.WhCode is None
                    or sql_key(row.SKUCode) != sql_key(sku)
                    or sql_key(row.WhCode) != sql_key(wh)):
                continue
            matches = [old for old in histories
                       if old.TaskId == task.TaskID and _same_pair(row, old)] or [None]
            for old in matches:
                projected = omit_nulls({alias: getattr(row, name)
                                        for alias, name in fields})
                projected.update(TaskId=task.TaskID,
                    PendingSince=displayed_date(task.PendingSince),
                    RequesterName=task.RequesterName,
                    ApproverName=old.ApprovedBy if old is not None else None)
                result.append(omit_nulls(projected))
    return sorted(result, key=lambda row: row.get('PendingSince') or '') or None


def history_skus(source, payload):
    master_id = int(value(payload, 'masterId'))
    if master_id not in MASTERS:
        raise ValueError('Phase-control family is not delivered')
    if payload.get('product_permissions') is None or payload.get('location_permissions') is None:
        raise ValueError('native permission lists are required')
    sku_scope, location_scope = scopes(source, payload)
    upper = database_now().replace(hour=0, minute=0, second=0, microsecond=0)
    task_ids = set(MdmTask.objects.filter(source=source,
        MasterId=str(master_id), Actiontype=1,
        PendingSince__gte=upper - timedelta(days=90), PendingSince__lte=upper)
        .values_list('TaskID', flat=True))
    _, history_model, _ = models(master_id)
    result = {}
    for row in history_model.objects.filter(source=source,
                                             TaskId__in=task_ids).order_by('id'):
        identity = row_key(row)
        if (row.SKUCode is not None and row.WhCode is not None
                and identity[0] in sku_scope and identity[1] in location_scope
                and identity not in result):
            result[identity] = {'SKUCode': row.SKUCode, 'WHCode': row.WhCode}
    return list(result.values())
