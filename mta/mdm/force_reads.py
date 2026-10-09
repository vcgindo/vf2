"""Master-13 task projections at native SKU/location occurrence grain."""
from collections import defaultdict
from datetime import timedelta
import json

from mta.mdm.clock import database_now
from mta.mdm.drafts import omit_nulls, value
from mta.mdm.force import CONFIG
from mta.mdm.force_tasks import row_key, scopes
from mta.mdm.supplier_permissions import hierarchy_key, triples
from mta.mdm.task_reads import TaskDenied, assigned, displayed_date, header, sql_key
from mta.runtime.mdm_force_models import MdmForceHistory, MdmForceRequested
from mta.runtime.mdm_models import MdmLocationAttributes, MdmSkuAttributes, MdmTask


DECISIONS = {'3': 'Request approved', '4': 'Request approval reverted/ Rejected'}


def _fields(task):
    names = (task.ColumnList or '').split(',')
    return [(row['Col_Code'], row['TableField']) for row in sorted(
        CONFIG['UI_MDMConfig'], key=lambda item: item['Col_Position'])
        if row['TableField'] in names]


def _project(row, fields):
    return omit_nulls({alias: getattr(row, field) for alias, field in fields})


def _review_text(row, fields):
    return json.dumps(_project(row, fields), ensure_ascii=False, separators=(',', ':'))


def _scope_count(source, row, payload):
    product_triples = triples('products', payload.get('product_permissions'))
    location_triples = triples('locations', payload.get('location_permissions'))
    products = sum(product_triples[tuple(hierarchy_key(getattr(item, 'SL' + str(i)))
        for i in range(1, 4))] for item in MdmSkuAttributes.objects.filter(
            source=source, owner='Importer') if row.SKUCode is not None
            and sql_key(item.SKUCode) == sql_key(row.SKUCode))
    locations = sum(location_triples[tuple(hierarchy_key(getattr(item, 'LL' + str(i)))
        for i in range(1, 4))] for item in MdmLocationAttributes.objects.filter(
            source=source, owner='Importer') if row.WhCode is not None
            and sql_key(item.WHCode) == sql_key(row.WhCode))
    return products * locations


def details(source, payload, actor, *, download=False):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if task is None:
        return None
    if task.MasterId != '13' or task.Actiontype != 2:
        raise ValueError('MDM family is not delivered')
    fields = _fields(task)
    if not fields:
        raise ValueError('native Force Norm task column list is empty')
    complete_history = list(MdmForceHistory.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    if download:
        approver_id = str(value(payload, 'approverId'))
        requester = MdmTask.objects.filter(source=source, TaskID=task_id,
                                           RequesterId=str(actor['id'])).exists()
        selected = approver_id == str(actor['id']) and any(
            assigned(item.ApproverId, actor['id']) for item in complete_history)
        if not requester and not selected:
            raise TaskDenied('task_download_actor_required')
        visible_history = [item for item in complete_history
                           if str(item.ApprovedBy) == approver_id]
    else:
        visible_history = [item for item in complete_history
            if item.Status is None and assigned(item.ApproverId, actor['id'])]
    by_pair = defaultdict(list)
    for item in visible_history:
        by_pair[row_key(item)].append(item)
    requested = list(MdmForceRequested.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    requested.sort(key=lambda item: (sql_key(item.WhCode) is not None,
                                     sql_key(item.WhCode) or ''), reverse=True)
    requested.sort(key=lambda item: (sql_key(item.SKUCode) is not None,
                                     sql_key(item.SKUCode) or ''))
    rows = []
    for item in requested:
        identity = row_key(item)
        multiplicity = 1 if download else _scope_count(source, item, payload)
        for old in by_pair[identity]:
            for _ in range(multiplicity):
                same = lambda candidate: row_key(candidate) == identity
                row = dict(
                    new=','.join(_review_text(candidate, fields)
                                 for candidate in requested if same(candidate)),
                    old=','.join(_review_text(candidate, fields)
                                 for candidate in complete_history if same(candidate)))
                rows.append({'RN': len(rows) + 1, **row})
    paging = value(payload, 'paginationParameter')
    if paging is not None:
        page, size = int(value(paging, 'pageNumber')), int(value(paging, 'recordsPerPage'))
        rows = [row for row in rows if (page - 1) * size + 1 <= row['RN'] <= page * size]
    return [{'MasterId': 13, 'data': rows}]


def count(source, task_id, actor):
    return sum(assigned(item.ApproverId, actor['id']) for item in
               MdmForceHistory.objects.filter(source=source, TaskId=task_id))


def history(source, payload, actor):
    if int(value(payload, 'masterId')) != 13:
        raise ValueError('MDM family is not delivered')
    sku, wh = value(payload, 'skuCode'), value(payload, 'whCode')
    sku_scope, location_scope = scopes(source, payload)
    if sql_key(sku) not in sku_scope or sql_key(wh) not in location_scope:
        raise TaskDenied('sku_location_scope_required')
    tasks = list(MdmTask.objects.filter(source=source, MasterId='13')
        .exclude(TaskStatus='1').exclude(TaskStatus=None).order_by('PendingSince', 'id'))
    requests = list(MdmForceRequested.objects.filter(source=source).order_by('id'))
    selected = [(task, row) for task in tasks for row in requests
        if row.TaskId == task.TaskID and sql_key(row.SKUCode) == sql_key(sku)
        and sql_key(row.WhCode) == sql_key(wh)]
    names = {name for task, _ in selected for name in (task.ColumnList or '').split(',')}
    fields = [(row['Col_Code'], row['TableField']) for row in sorted(
        CONFIG['UI_MDMConfig'], key=lambda item: item['Col_Position'])
        if row['TableField'] in names]
    if not fields:
        return None
    histories = list(MdmForceHistory.objects.filter(source=source).order_by('id'))
    result = []
    for task, requested in selected:
        matches = [item for item in histories if item.TaskId == task.TaskID
            and row_key(item) == row_key(requested)] or [None]
        for old in matches:
            item = _project(requested, fields)
            item.update(TaskId=requested.TaskId, PendingSince=displayed_date(task.PendingSince),
                RequesterName=task.RequesterName,
                ApproverName=old.ApprovedBy if old is not None else None)
            result.append(omit_nulls(item))
    return sorted(result, key=lambda row: row.get('PendingSince') or '') or None


def history_skus(source, payload):
    if int(value(payload, 'masterId')) != 13:
        raise ValueError('MDM family is not delivered')
    if payload.get('product_permissions') is None or payload.get('location_permissions') is None:
        raise ValueError('native permission lists are required')
    sku_scope, location_scope = scopes(source, payload)
    upper = database_now().replace(hour=0, minute=0, second=0, microsecond=0)
    task_ids = set(MdmTask.objects.filter(source=source, MasterId='13', Actiontype=2,
        PendingSince__gte=upper - timedelta(days=90), PendingSince__lte=upper)
        .values_list('TaskID', flat=True))
    result = {}
    for item in MdmForceHistory.objects.filter(source=source,
                                                TaskId__in=task_ids).order_by('id'):
        identity = row_key(item)
        if identity[0] in sku_scope and identity[1] in location_scope and identity not in result:
            result[identity] = {'SKUCode': item.SKUCode, 'WHCode': item.WhCode}
    return list(result.values())
