"""Location requester/reviewer projections with native master2 grains."""
from collections import defaultdict
import json
from zoneinfo import ZoneInfo
from datetime import timedelta

from django.conf import settings
from mta.mdm.drafts import omit_nulls, value
from mta.mdm.clock import database_now
from mta.mdm.location import ALIASES
from mta.mdm.task_reads import TaskDenied
from mta.presentation.context import permission_catalogue
from mta.presentation.permissions import expand_permission_ids
from mta.runtime.mdm_models import (MdmTask, MdmSubTask, MdmLocationRequested,
    MdmLocationHistory, MdmLocationAttributes, MdmLocationDescription)

STATUS = {'1':'Pending','2':'Approved - DB update Pending',
    '3':'Partially Approved - DB update Pending','4':'Approved - DB Updated',
    '5':'Partially Approved - DB Updated','6':'Rejected','7':'Completed'}
DECISIONS = {'3':'Request approved','4':'Request approval reverted/ Rejected'}


def sql_key(text):
    return text.rstrip(' ').lower() if text is not None else None


def assigned(ids, actor_id):
    return str(actor_id) in (ids or '').split(',')


def hierarchy_count(row, permission_ids):
    levels = [sql_key(getattr(row, 'LL'+str(i))) for i in range(1,4)]
    if None in levels:
        return 0
    return sum(levels == [sql_key(p['level_'+str(i)]) for i in range(1,4)]
        for p in permission_catalogue()['locations']['records'] if p['id'] in permission_ids)


def header(source, task_id):
    return MdmTask.objects.filter(source=source,TaskID=task_id).first()


def require_requester(source, task_id, actor):
    if not MdmTask.objects.filter(source=source,TaskID=task_id,RequesterId=str(actor['id'])).exists():
        raise TaskDenied('task_requester_required')


def require_location_scope(source, wh_code, payload):
    if not any(sql_key(row.WHCode)==sql_key(wh_code) and hierarchy_count(row,payload.get('location_permissions') or [])
        for row in MdmLocationAttributes.objects.filter(source=source,owner='Importer')):
        raise TaskDenied('location_scope_required')


def displayed_date(stamp):
    return stamp.astimezone(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).strftime('%d/%m/%Y %I:%M %p') if stamp else None


def status_rows(source, actor):
    result = []
    subtasks = defaultdict(list)
    for item in MdmSubTask.objects.filter(source=source).exclude(ApproverId=None):
        subtasks[item.TaskID].append(item)
    for task in MdmTask.objects.filter(source=source,RequesterId=str(actor['id'])).exclude(ApproverId=None).order_by('PendingSince'):
        if task.TaskStatus not in STATUS:
            continue
        nested = []
        for sub in subtasks[task.TaskID]:
            if sub.TaskStatus in STATUS:
                nested.append(omit_nulls(dict(TaskID=task.TaskID,PendingSince=displayed_date(task.PendingSince),
                    TaskName=task.TaskName,Approver=sub.ApproverName,Requester=task.RequesterName,
                    TaskStatus=STATUS[sub.TaskStatus],ApprovedDate=sub.ApprovedOrRejectedDate,
                    DBUpdatedDate=sub.DBUpdatedDate,ApproverId=sub.ApproverId,Actiontype=task.Actiontype)))
        result.append(omit_nulls(dict(TaskID=task.TaskID,PendingSince=displayed_date(task.PendingSince),
            TaskName=task.TaskName,Approver=task.ApproversName,Requester=task.RequesterName,
            TaskStatus=STATUS[task.TaskStatus],Approvers=nested)))
    return sorted(result,key=lambda row:row.get('PendingSince') or '')


def pending_rows(source, actor):
    result = []
    today = database_now().date()
    for task in MdmTask.objects.filter(source=source).order_by('PendingSince'):
        for sub in MdmSubTask.objects.filter(source=source,TaskID=task.TaskID,TaskStatus='1',ApproverId=str(actor['id'])):
            result.append(omit_nulls(dict(TaskID=task.TaskID,PendingSince=displayed_date(task.PendingSince),
                ageing=(today-task.PendingSince.astimezone(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).date()).days if task.PendingSince else None,
                TaskName=task.TaskName,RequesterName=task.RequesterName,Actiontype=task.Actiontype)))
    return result


def columns(task):
    names = (task.ColumnList or '').split(',')
    return {alias: field for alias,field in ALIASES.items() if field in names}


def project(row, fields, *, include_nulls=False):
    result = {alias:getattr(row,field) for alias,field in fields.items()}
    return result if include_nulls else omit_nulls(result)


def details(source, payload, actor, *, download=False):
    task_id = value(payload,'taskId')
    task = header(source,task_id)
    if task is None:
        return None
    fields = columns(task)
    if int(task.MasterId) != 2:
        raise ValueError('MDM family is not delivered')
    history = list(MdmLocationHistory.objects.filter(source=source,TaskId=task_id))
    complete_history = history
    if download:
        approver_id = str(value(payload,'approverId'))
        is_requester = MdmTask.objects.filter(source=source,TaskID=task_id,RequesterId=str(actor['id'])).exists()
        is_selected_reviewer = approver_id==str(actor['id']) and any(assigned(h.ApproverId,actor['id']) for h in history)
        if not is_requester and not is_selected_reviewer:
            raise TaskDenied('task_download_actor_required')
        history = [h for h in history if str(h.ApprovedBy)==approver_id]
    else:
        history = [h for h in history if h.Status is None and assigned(h.ApproverId,actor['id'])]
    by_location = defaultdict(list)
    for row in history:
        by_location[sql_key(row.WHCode)].append(row)
    descriptions = defaultdict(list)
    if not download:
        for row in MdmLocationDescription.objects.filter(source=source,owner='Importer'):
            descriptions[sql_key(row.WHCode)].append(row.WHDescription)
    rows = []
    requests = list(MdmLocationRequested.objects.filter(source=source,TaskId=task_id))
    requests.sort(key=lambda r:sql_key(r.WHCode),reverse=task.Actiontype==2 or not download)
    for requested in requests:
        multiplicity = 1 if download else hierarchy_count(requested,payload.get('location_permissions') or [])
        for old in by_location[sql_key(requested.WHCode)]:
            descs = [None] if download or task.Actiontype==2 else descriptions[sql_key(requested.WHCode)] or [None]
            for description in descs:
                for _ in range(multiplicity):
                    if task.Actiontype==2:
                        # Native correlated FOR JSON WITHOUT_ARRAY_WRAPPER is
                        # text, including comma-separated objects for duplicates.
                        # Its subqueries do not inherit the outer reviewer filter.
                        encode = lambda row: json.dumps(project(row,fields),ensure_ascii=False,separators=(',',':'))
                        key = sql_key(requested.WHCode)
                        item = dict(new=','.join(encode(row) for row in requests if sql_key(row.WHCode)==key),
                            # Human-approved review-only repair: use history
                            # values so the unchanged UI can detect modifications.
                            # Downloads retain the native A-qualified projection.
                            old=','.join(encode(requested if download else row)
                                for row in complete_history if sql_key(row.WHCode)==key))
                    else:
                        item = project(requested,fields,include_nulls=not download)
                        if task.Actiontype==3 and not download and 'wd' in item:
                            item['wd'] = description
                        item.update(Status=DECISIONS.get(old.Status) if download else old.Status,Comments=old.Comments)
                        if download: item=omit_nulls(item)
                    rows.append({'RN':len(rows)+1,**item})
    paging = value(payload,'paginationParameter')
    if paging is not None:
        page,size=int(value(paging,'pageNumber')),int(value(paging,'recordsPerPage'))
        rows=[r for r in rows if (page-1)*size+1<=r['RN']<=page*size]
    return [{'MasterId':2,'data':rows}]


def count(source, task_id, actor):
    return sum(assigned(row.ApproverId,actor['id']) for row in MdmLocationHistory.objects.filter(source=source,TaskId=task_id))


def history(source, payload, actor):
    wh_code=value(payload,'whCode')
    require_location_scope(source,wh_code,payload)
    if int(value(payload,'masterId'))!=2:
        raise ValueError('MDM family is not delivered')
    requests=[r for r in MdmLocationRequested.objects.filter(source=source) if sql_key(r.WHCode)==sql_key(wh_code)]
    tasks=list(MdmTask.objects.filter(source=source).exclude(TaskStatus='1').exclude(TaskStatus=None).order_by('PendingSince'))
    selected=[(task,r) for task in tasks for r in requests if task.TaskID==r.TaskId]
    names={name for task,_ in selected for name in (task.ColumnList or '').split(',')}
    fields={alias:field for alias,field in ALIASES.items() if field in names}
    if not fields:
        return None
    result=[]
    history=list(MdmLocationHistory.objects.filter(source=source))
    for task,requested in selected:
        matches=[h for h in history if h.TaskId==requested.TaskId and sql_key(h.WHCode)==sql_key(requested.WHCode)] or [None]
        for h in matches:
            result.append(omit_nulls(dict(**project(requested,fields),TaskId=requested.TaskId,
                PendingSince=displayed_date(task.PendingSince),RequesterName=task.RequesterName,
                ApproverName=h.ApprovedBy if h else None)))
    return sorted(result,key=lambda row:row.get('PendingSince') or '')


def history_skus(source,payload):
    """Location selector for modification history through today's midnight."""
    if int(value(payload,'masterId'))!=2:
        raise ValueError('MDM family is not delivered')
    if payload.get('location_permissions') is None:
        raise ValueError('native permission lists are required')
    upper=database_now().replace(hour=0,minute=0,second=0,microsecond=0)
    task_ids=set(MdmTask.objects.filter(source=source,MasterId='2',Actiontype=2,
        PendingSince__gte=upper-timedelta(days=90),PendingSince__lte=upper).values_list('TaskID',flat=True))
    accessible={sql_key(row.WHCode) for row in MdmLocationAttributes.objects.filter(source=source,owner='Importer')
        if hierarchy_count(row,payload['location_permissions'])}
    result={}
    for row in MdmLocationHistory.objects.filter(source=source,TaskId__in=task_ids):
        code=sql_key(row.WHCode)
        if code in accessible and code not in result: result[code]={'WHCode':row.WHCode}
    return list(result.values())
