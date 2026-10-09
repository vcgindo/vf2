"""Deployed master-6 StopPIPO review, download, and history projections."""
from collections import defaultdict
from datetime import timedelta

from mta.mdm.clock import database_now
from mta.mdm.drafts import omit_nulls, value
from mta.mdm.force_reads import _scope_count
from mta.mdm.force_tasks import row_key, scopes
from mta.mdm.task_reads import TaskDenied, assigned, displayed_date, header, sql_key
from mta.runtime.mdm_models import MdmLocationDescription, MdmSkuDescription, MdmTask
from mta.runtime.mdm_stop_pipo_models import MdmStopPipoHistory, MdmStopPipoRequested


DECISIONS = {'3': 'Request approved', '4': 'Request approval reverted/ Rejected'}
FIELD_ALIASES = (('sc', 'SKUCode'), ('wc', 'WhCode'))


def _fields(task):
    names = (task.ColumnList or '').split(',')
    return [(alias, name) for alias, name in FIELD_ALIASES if name in names]


def _same_pair(left, right):
    """Model SQL's equality join: NULL never equals NULL."""
    return (left.SKUCode is not None and right.SKUCode is not None
            and left.WhCode is not None and right.WhCode is not None
            and sql_key(left.SKUCode) == sql_key(right.SKUCode)
            and sql_key(left.WhCode) == sql_key(right.WhCode))


def details(source, payload, actor, *, download=False):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if task is None:
        return None
    if task.MasterId != '6' or task.Actiontype != 2:
        raise ValueError('StopPIPO supports Modify only')

    complete_history = list(MdmStopPipoHistory.objects.filter(
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
    requested = list(MdmStopPipoRequested.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    # SQL Server orders NULL first for ASC and last for DESC.
    requested.sort(key=lambda row: (sql_key(row.WhCode) is not None,
                                     sql_key(row.WhCode) or ''), reverse=not download)
    requested.sort(key=lambda row: (sql_key(row.SKUCode) is not None,
                                     sql_key(row.SKUCode) or ''))

    fields = _fields(task)
    if not fields:
        raise ValueError('Native StopPIPO task column list is empty')
    sku_descriptions = list(MdmSkuDescription.objects.filter(
        source=source, owner='Importer').order_by('id')) if not download else []
    location_descriptions = list(MdmLocationDescription.objects.filter(
        source=source, owner='Importer').order_by('id')) if not download else []
    rows = []
    for requested_row in requested:
        # SQL equality joins exclude every row with a NULL key.
        matches = [old for old in histories[row_key(requested_row)]
                   if _same_pair(requested_row, old)]
        if download:
            projections = [omit_nulls({alias: getattr(requested_row, name)
                                       for alias, name in fields})]
            multiplicity = 1
        else:
            sku_matches = [item for item in sku_descriptions
                if requested_row.SKUCode is not None and item.SKUCode is not None
                and sql_key(item.SKUCode) == sql_key(requested_row.SKUCode)] or [None]
            location_matches = [item for item in location_descriptions
                if requested_row.WhCode is not None and item.WHCode is not None
                and sql_key(item.WHCode) == sql_key(requested_row.WhCode)] or [None]
            projections = [omit_nulls(dict(
                sc=requested_row.SKUCode, wc=requested_row.WhCode,
                posn=sku.SKUDescription if sku is not None else None,
                ln=location.WHDescription if location is not None else None))
                for sku in sku_matches for location in location_matches]
            multiplicity = _scope_count(source, requested_row, payload)
        for old in matches:
            for projection in projections:
                for _ in range(multiplicity):
                    rows.append(omit_nulls(dict(RN=len(rows) + 1, **projection,
                        Status=DECISIONS.get(old.Status) if download else old.Status,
                        Comments=old.Comments)))

    paging = value(payload, 'paginationParameter')
    if paging is not None:
        page = int(value(paging, 'pageNumber'))
        size = int(value(paging, 'recordsPerPage'))
        rows = [row for row in rows
                if (page - 1) * size + 1 <= row['RN'] <= page * size]
    return [{'MasterId': 6, 'data': rows}]


def count(source, task_id, actor):
    return sum(assigned(row.ApproverId, actor['id']) for row in
               MdmStopPipoHistory.objects.filter(source=source, TaskId=task_id))


def history(source, payload, actor):
    if int(value(payload, 'masterId')) != 6:
        raise ValueError('StopPIPO family is not delivered')
    sku, wh = value(payload, 'skuCode'), value(payload, 'whCode')
    sku_scope, location_scope = scopes(source, payload)
    if sql_key(sku) not in sku_scope or sql_key(wh) not in location_scope:
        raise TaskDenied('sku_location_scope_required')
    tasks = list(MdmTask.objects.filter(source=source, MasterId='6')
        .exclude(TaskStatus='1').exclude(TaskStatus=None).order_by('PendingSince', 'id'))
    requested = list(MdmStopPipoRequested.objects.filter(source=source).order_by('id'))
    histories = list(MdmStopPipoHistory.objects.filter(source=source).order_by('id'))
    result = []
    for task in tasks:
        fields = _fields(task)
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
    if int(value(payload, 'masterId')) != 6:
        raise ValueError('StopPIPO family is not delivered')
    if payload.get('product_permissions') is None or payload.get('location_permissions') is None:
        raise ValueError('native permission lists are required')
    sku_scope, location_scope = scopes(source, payload)
    upper = database_now().replace(hour=0, minute=0, second=0, microsecond=0)
    task_ids = set(MdmTask.objects.filter(source=source, MasterId='6', Actiontype=2,
        PendingSince__gte=upper - timedelta(days=90), PendingSince__lte=upper)
        .values_list('TaskID', flat=True))
    result = {}
    for row in MdmStopPipoHistory.objects.filter(source=source,
                                                  TaskId__in=task_ids).order_by('id'):
        identity = row_key(row)
        if (row.SKUCode is not None and row.WhCode is not None
                and identity[0] in sku_scope and identity[1] in location_scope
                and identity not in result):
            result[identity] = {'SKUCode': row.SKUCode, 'WHCode': row.WhCode}
    return list(result.values())
