"""Native flat Seasonality review/download projections and scoped history."""
from datetime import timedelta
from mta.application.r1_seasonality import SEASON_FIELDS
from mta.mdm.clock import database_now
from mta.mdm.drafts import omit_nulls, value
from mta.mdm.force_reads import _scope_count
from mta.mdm.force_tasks import row_key, scopes
from mta.mdm.season_configuration import fields
from mta.mdm.season_tasks import models
from mta.mdm.task_reads import TaskDenied, assigned, displayed_date, header, sql_key
from mta.runtime.mdm_models import MdmSkuDescription, MdmLocationDescription, MdmTask

DECISIONS = {'3': 'Request approved', '4': 'Request approval reverted/ Rejected'}


def _fields(task):
    names = (task.ColumnList or '').split(',')
    return [(alias, r['TableField'].rstrip()) for alias, r in fields(int(task.MasterId)).items()
            if r['TableField'].rstrip() in names]


def details(source, payload, actor, *, download=False):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if task is None:
        return None
    master_id = int(task.MasterId)
    if master_id not in (10, 11, 12):
        raise ValueError('Seasonality family is not delivered')
    requested_model, history_model = models(master_id)
    history = list(history_model.objects.filter(source=source, TaskId=task_id).order_by('id'))
    if download:
        approver = str(value(payload, 'approverId'))
        requester = str(task.RequesterId) == str(actor['id'])
        reviewer = approver == str(actor['id']) and any(assigned(r.ApproverId, actor['id']) for r in history)
        if not requester and not reviewer:
            raise TaskDenied('task_download_actor_required')
        history = [r for r in history if str(getattr(r, 'ApproverBy' if master_id == 10 else 'ApprovedBy')) == approver]
    else:
        history = [r for r in history if r.Status is None and assigned(r.ApproverId, actor['id'])]
    requested = list(requested_model.objects.filter(source=source, TaskId=task_id).order_by('id'))
    requested.sort(key=lambda r: sql_key(r.WhCode), reverse=True)
    requested.sort(key=lambda r: sql_key(r.SKUCode))
    selected_fields = _fields(task)
    if not selected_fields:
        raise ValueError('Native seasonal task column list is empty')
    skus = list(MdmSkuDescription.objects.filter(source=source, owner='Importer'))
    locations = list(MdmLocationDescription.objects.filter(source=source, owner='Importer'))
    run = statuses = None
    if master_id == 10:
        from mta.mdm.season_current import publication
        from mta.mdm.target_fixture import consumer_rows
        run = publication(source)
        statuses = consumer_rows(source, run, 'closing/control_aux/season_status')
    result = []
    for row in requested:
        matches = [r for r in history if row_key(r) == row_key(row)]
        weight = 1 if download else _scope_count(source, row, payload)
        if master_id == 10:
            from mta.mdm.season_current import projected
            season = {n: getattr(row, 'Status1' if n == 'Status' else n) for n in SEASON_FIELDS}
            # Native task queries join Importer descriptions, unlike current.
            projections = projected(source, run, [season], descriptions=(
                [dict(SKUCode=r.SKUCode, SKUDescription=r.SKUDescription) for r in skus],
                [dict(WHCode=r.WHCode, WHDescription=r.WHDescription) for r in locations]))
            projections = [{**r, 'sts': status['Status'] if status else None}
                for r in projections for status in ([s for s in statuses if s['Id'] == row.Status1] or [None])]
        else:
            sku_matches = [r for r in skus if sql_key(r.SKUCode) == sql_key(row.SKUCode)] or [None]
            location_matches = [r for r in locations if sql_key(r.WHCode) == sql_key(row.WhCode)] or [None]
            projections = [{alias: getattr(row, name) for alias, name in selected_fields}
                for _ in sku_matches for _ in location_matches]
        for old in matches:
            for projected_row in projections:
                for _ in range(weight):
                    result.append(omit_nulls(dict(RN=len(result) + 1, **projected_row,
                        Status=DECISIONS.get(old.Status) if download else old.Status, Comments=old.Comments)))
    paging = value(payload, 'paginationParameter')
    if paging:
        page, size = int(value(paging, 'pageNumber')), int(value(paging, 'recordsPerPage'))
        result = result[(page - 1) * size:page * size]
    return [dict(MasterId=master_id, data=result)]


def count(source, task_id, actor):
    task = header(source, task_id)
    _, history_model = models(task.MasterId)
    return sum(assigned(r.ApproverId, actor['id']) for r in history_model.objects.filter(source=source, TaskId=task_id))


def history(source, payload, actor):
    master_id = int(value(payload, 'masterId'))
    sku, wh = value(payload, 'skuCode'), value(payload, 'whCode')
    sku_scope, location_scope = scopes(source, payload)
    if sql_key(sku) not in sku_scope or sql_key(wh) not in location_scope:
        raise TaskDenied('sku_location_scope_required')
    requested_model, history_model = models(master_id)
    tasks = list(MdmTask.objects.filter(source=source, MasterId=str(master_id))
        .exclude(TaskStatus='1').exclude(TaskStatus=None).order_by('PendingSince', 'id'))
    requested = list(requested_model.objects.filter(source=source).order_by('id'))
    histories = list(history_model.objects.filter(source=source).order_by('id'))
    result = []
    for task in tasks:
        for row in requested:
            if row.TaskId != task.TaskID or row_key(row) != (sql_key(sku), sql_key(wh)):
                continue
            for old in [r for r in histories if r.TaskId == task.TaskID and row_key(r) == row_key(row)] or [None]:
                projected = {alias: getattr(row, name) for alias, name in _fields(task)}
                projected.update(TaskId=task.TaskID, PendingSince=displayed_date(task.PendingSince),
                    RequesterName=task.RequesterName, ApproverName=(getattr(old,
                        'ApproverBy' if master_id == 10 else 'ApprovedBy') if old else None))
                result.append(omit_nulls(projected))
    return sorted(result, key=lambda r: r.get('PendingSince') or '') or None


def history_skus(source, payload):
    master_id = int(value(payload, 'masterId'))
    sku_scope, location_scope = scopes(source, payload)
    upper = database_now().replace(hour=0, minute=0, second=0, microsecond=0)
    task_ids = set(MdmTask.objects.filter(source=source, MasterId=str(master_id), Actiontype=2,
        PendingSince__gte=upper - timedelta(days=90), PendingSince__lte=upper).values_list('TaskID', flat=True))
    _, model = models(master_id)
    result = {}
    for r in model.objects.filter(source=source, TaskId__in=task_ids).order_by('id'):
        key = row_key(r)
        if key[0] in sku_scope and key[1] in location_scope and key not in result:
            result[key] = dict(SKUCode=r.SKUCode, WHCode=r.WhCode)
    return list(result.values())
