"""Location submission and decisions from pinned master2 SQL."""
from collections import defaultdict
from contextlib import nullcontext
import logging

from django.db import DatabaseError
from django.db.models import Max
from mta.mdm.drafts import now, value
from mta.mdm.clock import database_now
from mta.mdm.location import ALIASES
from mta.mdm.task_reads import (TaskDenied, assigned, header,
    require_requester, sql_key)
from mta.presentation.context import permission_catalogue
from mta.runtime.mdm_models import (MdmTask,MdmSubTask,MdmLocationAttributes,MdmLocationDescription,
    MdmLocationRequested,MdmLocationHistory,MdmLocationApproved,MdmLocationUploadLog,MdmLocationUse)

log = logging.getLogger(__name__)
BUSINESS = tuple(ALIASES.values())


class NativeSqlValueError(Exception):
    """A value accepted by request assembly but rejected by SQL conversion."""


def fields(row, names=BUSINESS):
    return {name:getattr(row,name) for name in names}


def response(action, task_id, errors, conflicts=None, conflict_count=0):
    return dict(status=200,msg={1:' Data Saved Sucessfully',2:' Data modified Sucessfully',3:' Data removed Sucessfully'}[action],
        taskId=task_id,errorCount=str(sum(len(error['errorData']) for error in errors)),
        error=errors,conflictErrorCount=str(conflict_count),conflictError=conflicts)


def convert(row, keys):
    result = {}
    for alias in keys:
        field = ALIASES[alias]
        raw = row[alias]
        if raw is None:
            raise ValueError('native value.ToString requires a value')
        raw = str(raw)
        result[field] = raw
    # TaskNMSNewLocations.WHDescription is NOT NULL and has no SQL default.
    # Django CharField would otherwise synthesize an empty string for omission.
    if 'WHDescription' not in result:
        raise NativeSqlValueError('native required WHDescription column omitted')
    return result


def hierarchy_count(row, permission_ids):
    levels=[sql_key(getattr(row,'LL'+str(i))) for i in range(1,4)]
    if None in levels: return 0
    return sum(levels==[sql_key(p['level_'+str(i)]) for i in range(1,4)]
        for p in permission_catalogue()['locations']['records'] if p['id'] in permission_ids)


def eligible_approvers(rows, users):
    levels = [set(','.join(dict.fromkeys(row['LL'+str(i)] for row in rows)).split(',')) for i in range(1,4)]
    ids = {p['id'] for p in permission_catalogue()['locations']['records']
        if all(sql_key(p['level_'+str(i)]) in {sql_key(v) for v in levels[i-1]} for i in range(1,4))}
    return [user for user in users if ids.intersection(user['location_id'])]


def before_rows(source, codes, names):
    descriptions=defaultdict(list)
    for description in MdmLocationDescription.objects.filter(source=source,owner='Importer'):
        descriptions[sql_key(description.WHCode)].append(description)
    wanted={sql_key(code) for code in codes}
    rows=[]
    for attr in MdmLocationAttributes.objects.filter(source=source,owner='Importer'):
        if sql_key(attr.WHCode) not in wanted:
            continue
        for description in descriptions[sql_key(attr.WHCode)]:
            rows.append({name:getattr(description if name=='WHDescription' else attr,name) for name in names})
    return rows


def submit(source,payload,actor,action):
    if int(value(payload,'id'))!=2:
        raise ValueError('MDM family is not delivered')
    supplied_id=value(payload,'taskId')
    if supplied_id is None:
        raise ValueError('native TaskId.ToString requires a value')
    if supplied_id:
        require_requester(source,supplied_id,actor)
    rows=value(payload,'data')
    keys=list(rows[0])
    names=[ALIASES[k] for k in keys]
    permissions=payload.get('location_permissions') or []
    catalogue=permission_catalogue()['locations']['records']
    levels=[tuple(p['level_'+str(i)].lower().strip() for i in range(1,4)) for p in catalogue
            if p['id'] in permissions and all(p['level_'+str(i)] is not None for i in range(1,4))]
    existing=set(MdmLocationAttributes.objects.filter(source=source,owner='Importer').values_list('WHCode',flat=True))
    errors=[]
    if action==3:
        accessible={row.WHCode for row in MdmLocationAttributes.objects.filter(source=source,owner='Importer') if hierarchy_count(row,permissions)}
        allowed=[row for row in rows if row['wc'] in accessible]
    else:
        allowed=[row for row in rows if tuple(row['LL'+str(i)].lower().strip() for i in range(1,4)) in levels]
    excluded=[row for row in rows if not any(row is candidate for candidate in allowed)]
    if excluded: errors.append(dict(errorType=('Either You are UnAuthorized Location Code or Location Code Does not Exist'
        if action==3 else 'UnAuthorized Location Codes'),errorData=excluded))
    excluded=[row for row in allowed if (row['wc'] in existing)==(action==1)]
    category='Duplicate Location Codes' if action==1 else 'Location Codes Does not Exist'
    if excluded: errors.append(dict(errorType=category,errorData=excluded))
    allowed=[row for row in allowed if not any(row is candidate for candidate in excluded)]
    if action==3:
        for kind,category in (
            ('direct',"You can't remove these Location Codes as they are already existing in SKULocation Combination"),
            ('parent',"You can't remove these Location Codes as they are already existing in SKULocation Combination as Parent Location Code")):
            used=set(MdmLocationUse.objects.filter(source=source,use_kind=kind,
                WHCode__in=[r['wc'] for r in allowed]).values_list('WHCode',flat=True))
            excluded=[row for row in allowed if row['wc'] in used]
            if excluded: errors.append(dict(errorType=category,errorData=excluded))
            allowed=[row for row in allowed if not any(row is candidate for candidate in excluded)]
    conflicts=None
    conflict_count=0
    if action==2 and not value(payload,'isOverwrite',False):
        pending=list(MdmLocationHistory.objects.filter(source=source,Status=None))
        codes={row.WHCode for row in pending}
        conflicting=[row for row in allowed if row['wc'] in codes]
        if conflicting:
            conflict_count=len(conflicting)
            conflicts=[]
            # Native DISTINCT is over requester identity plus the configured
            # old projection. Pending history supplies only the global code set.
            grouped={}
            seen=set()
            wanted={sql_key(row['wc']) for row in conflicting}
            for task in MdmTask.objects.filter(source=source).order_by('RequesterId'):
                group=(task.RequesterId,task.RequesterName)
                for requested in MdmLocationRequested.objects.filter(source=source,TaskId=task.TaskID,Approved=False,Reverted=False):
                    if sql_key(requested.WHCode) not in wanted: continue
                    old={key:getattr(requested,ALIASES[key]) for key in keys}
                    distinct=(*group,*(sql_key(v) if isinstance(v,str) else v for v in old.values()))
                    if distinct in seen: continue
                    seen.add(distinct)
                    for row in conflicting:
                        if row['wc']==requested.WHCode:
                            grouped.setdefault(group,[]).append(dict(oldData=old,requestedData=row))
                            break
            by_requester=defaultdict(list)
            for (requester,_),details in grouped.items():
                by_requester[requester].extend(details)
            conflicts=[dict(user=name,conflictdetails=by_requester[requester])
                for requester,name in grouped]
            allowed=[row for row in allowed if not any(row is candidate for candidate in conflicting)]
    stamp=now()
    task_id=supplied_id or str(actor['id'])+'_'+stamp.strftime('%Y%m%d%H%M%S')
    for offset in range(0,len(allowed),999):
        chunk=allowed[offset:offset+999]
        approvers=eligible_approvers(chunk,payload['all_users'])
        approver_ids=','.join(str(a['id']) for a in approvers)
        approver_names=','.join(a['name'] for a in approvers)
        task_names=names if action!=3 else ['WHCode','WHDescription','LogisticsLocation']
        try:
            if action==3:
                converted=[dict(WHCode=row['wc'],WHDescription='',LogisticsLocation='',
                    **{'LL'+str(i):row['LL'+str(i)] for i in range(1,4)}) for row in chunk]
            else:
                converted=[convert(row,keys) for row in chunk]
            # Each operation below is a separate native SQL statement. Do not wrap
            # the batch or chunks in an application transaction.
            MdmLocationRequested.objects.bulk_create([MdmLocationRequested(source=source,TaskId=task_id,
                Approved=False,Reverted=False,ActionType=0 if action==3 else 1,**row) for row in converted])
            history=converted if action==1 else before_rows(source,[r['wc'] for r in chunk],task_names)
            MdmLocationHistory.objects.bulk_create([MdmLocationHistory(source=source,TaskId=task_id,
                ApproverId=None if action==1 else approver_ids,**row) for row in history])
            if action==1:
                MdmLocationHistory.objects.filter(source=source,TaskId=task_id).update(ApproverId=approver_ids)
            logged=converted if action!=3 else [dict(WHCode=r['WHCode'],**{'LL'+str(i):r['LL'+str(i)] for i in range(1,4)}) for r in converted]
            audit_stamp=database_now()
            MdmLocationUploadLog.objects.bulk_create([MdmLocationUploadLog(source=source,UserName=str(actor['id']),
                ActionTimeStamp=audit_stamp,ActionId=6 if action==3 else 5,**row) for row in logged])
            if not supplied_id and offset==0:
                MdmTask.objects.create(source=source,TaskID=task_id,PendingSince=database_now(),
                    TaskName={1:'Add',2:'Modify',3:'Remove'}[action]+'-LocationMaster',ApproverId=approver_ids,
                    ApproversName=approver_names,RequesterId=str(actor['id']),RequesterName=actor['name'],
                    TaskStatus='1',MasterId='2',Actiontype=action,ColumnList=','.join(task_names))
                MdmSubTask.objects.bulk_create([MdmSubTask(source=source,TaskID=task_id,
                    ApproverId=str(a['id']),ApproverName=a['name'],TaskStatus='1') for a in approvers])
        except (DatabaseError, NativeSqlValueError):
            # PostQuery logs/returns0; submit does not inspect that return value.
            log.exception('MDM native submission statement failure')
    return response(action,task_id,errors,conflicts,conflict_count)


def delete(source,task_id,actor):
    require_requester(source,task_id,actor)
    # Task deletion is not an undo of approved staging/master/audit effects.
    for model,field in ((MdmLocationHistory,'TaskId'),(MdmLocationRequested,'TaskId'),(MdmTask,'TaskID'),(MdmSubTask,'TaskID')):
        model.objects.filter(source=source,**{field:task_id}).delete()


def publish_add(source, task):
    """Pinned synchronous add copy into four independently owned master bags."""
    from mta.mdm.location_publication import publication_statement
    from mta.mdm.supplier_revisions import source_lock
    native = source.receipt.get('schema') == 'fresh-production-mdm-source-v1'
    # The API already owns this lock for the whole decision. Retain it here too
    # for direct callers so capture cannot interleave the eight native INSERTs.
    with source_lock(source.pk) if native else nullcontext():
        _publish_add(source, task, publication_statement if native else None)


def _publish_add(source, task, statement):
    # getCollist reads this task's physical ColumnList; it does not select all
    # queue fields. Publication itself is deliberately not task-filtered.
    names=(task.ColumnList or '').replace('WHDescription,','').split(',')
    if 'WHDescription' in names:
        raise ValueError('native attribute insert contains WHDescription')
    queued=MdmLocationApproved.objects.filter(source=source)
    queue=list(queued.order_by('pk') if statement else queued)
    for owner in ('Importer','BPR','BTR','DBM'):
        for model, selected in ((MdmLocationAttributes,names),(MdmLocationDescription,['WHCode','WHDescription'])):
            existing={sql_key(code) for code in model.objects.filter(source=source,owner=owner).values_list('WHCode',flat=True)}
            additions=[row for row in queue if sql_key(row.WHCode) not in existing]
            ordinal=model.objects.filter(source=source,owner=owner).aggregate(n=Max('ordinal'))['n'] or 0
            with statement(source, task) if statement else nullcontext():
                model.objects.bulk_create([model(source=source,owner=owner,ordinal=ordinal+i,
                    **fields(row,selected)) for i,row in enumerate(additions,1)])


def update_approved_queue(source,task_id):
    requested=list(MdmLocationRequested.objects.filter(source=source,TaskId=task_id,Approved=True))
    queue=list(MdmLocationApproved.objects.filter(source=source))
    codes={sql_key(row.WHCode) for row in queue}
    # One INSERT SELECT preserves duplicate absent rows from the submitted bag.
    MdmLocationApproved.objects.bulk_create([MdmLocationApproved(source=source,**fields(row),
        ActionType=row.ActionType,Approved=row.Approved,Reverted=row.Reverted)
        for row in requested if sql_key(row.WHCode) not in codes])
    for staged in MdmLocationApproved.objects.filter(source=source):
        matches=[r for r in requested if sql_key(r.WHCode)==sql_key(staged.WHCode)]
        if not matches:
            continue
        values=[fields(row) for row in matches]
        if any(row!=values[0] for row in values[1:]):
            raise ValueError('native duplicate UPDATE source is incomparable')
        incoming=values[0]
        for name in BUSINESS:
            if name=='WHCode': continue
            val=incoming[name]
            if val is not None and val!='':
                setattr(staged,name,val)
        staged.save(update_fields=[name for name in BUSINESS if name!='WHCode'])


def approve(source,payload,actor):
    task_id=value(payload,'taskId')
    task=header(source,task_id)
    if task is None or task.MasterId!='2':
        raise TaskDenied('task_reviewer_required')
    rows=value(payload,'data')
    keys=list(rows[0])
    history=list(MdmLocationHistory.objects.filter(source=source,TaskId=task_id))
    requested=list(MdmLocationRequested.objects.filter(source=source,TaskId=task_id))
    permissions=payload.get('location_permissions') or []
    valid=[row for row in rows if 'wc' in row]
    if not valid or not any(assigned(h.ApproverId,actor['id']) for h in history):
        raise TaskDenied('task_row_reviewer_scope_required')
    for decision in valid:
        matching_history=[h for h in history if sql_key(h.WHCode)==sql_key(decision['wc'])]
        matching_requests=[r for r in requested if sql_key(r.WHCode)==sql_key(decision['wc'])]
        current_scoped = any(sql_key(row.WHCode)==sql_key(decision['wc']) and
            hierarchy_count(row,permissions) for row in MdmLocationAttributes.objects.filter(
                source=source,owner='Importer'))
        if (not matching_history or not matching_requests or
                not all(assigned(h.ApproverId,actor['id']) for h in matching_history) or
                not all(hierarchy_count(row,permissions) for row in matching_requests) or
                (task.Actiontype!=1 and not current_scoped)):
            raise TaskDenied('task_row_reviewer_scope_required')
    for offset in range(0,len(valid),999):
        chunk=valid[offset:offset+999]
        for row in chunk:
            if any(row[k] is None for k in keys):
                raise ValueError('native decision value.ToString requires a value')
        decisions={}
        for row in chunk:
            current=(str(row['status']),str(row['comments']))
            key=sql_key(row['wc'])
            if key in decisions and decisions[key]!=current:
                raise ValueError('native duplicate decision UPDATE is incomparable')
            decisions[key]=current
        try:
            for row in requested:
                decision=decisions.get(sql_key(row.WHCode))
                if decision is not None:
                    MdmLocationRequested.objects.filter(pk=row.pk).update(Approved=decision[0]=='3',Reverted=decision[0]=='4')
            for row in history:
                decision=decisions.get(sql_key(row.WHCode))
                if decision is not None:
                    MdmLocationHistory.objects.filter(pk=row.pk).update(Status=decision[0],Comments=decision[1],ApprovedBy=int(actor['id']))
            update_approved_queue(source,task_id)
        except DatabaseError:
            log.exception('MDM native decision SQL failure')
        # The upload audit is a separately executed native command.
        try:
            for status in ('4','3'):
                stamp=database_now()
                MdmLocationUploadLog.objects.bulk_create([MdmLocationUploadLog(source=source,WHCode=row['wc'],
                    UserName=actor['name'],ActionTimeStamp=stamp,ActionId=int(status))
                    for row in chunk if str(row['status'])==status])
        except DatabaseError:
            log.exception('MDM native decision audit failure')
    if task.Actiontype==1:
        try: publish_add(source,task)
        except (DatabaseError,ValueError): log.exception('MDM native synchronous publication failure')
    history=list(MdmLocationHistory.objects.filter(source=source,TaskId=task_id))
    mine=[h for h in history if assigned(h.ApproverId,actor['id'])]
    completed=sum(h.Status in ('3','4') for h in mine)==len(mine)
    date=database_now().strftime('%d/%m/%Y %I:%M %p')
    MdmSubTask.objects.filter(source=source,TaskID=task_id,ApproverId=str(actor['id'])).update(ApprovedOrRejectedDate=date)
    if completed:
        for sub in MdmSubTask.objects.filter(source=source,TaskID=task_id).exclude(ApprovedOrRejectedDate=None):
            assigned_rows=[h for h in history if assigned(h.ApproverId,sub.ApproverId)]
            if assigned_rows and all(h.Status in ('3','4') for h in assigned_rows):
                status='2' if all(h.Status=='3' for h in assigned_rows) else '6' if all(h.Status=='4' for h in assigned_rows) else '3'
                MdmSubTask.objects.filter(pk=sub.pk).update(TaskStatus=status,
                    ApprovedOrRejectedDate=database_now().strftime('%d/%m/%Y %I:%M %p'))
        MdmSubTask.objects.filter(source=source,TaskID=task_id,ApprovedOrRejectedDate=None).update(TaskStatus='8')
    else:
        MdmSubTask.objects.filter(source=source,TaskID=task_id,ApproverId=str(actor['id'])).update(TaskStatus='3')
    if task.Actiontype==1:
        if any(h.Status=='3' for h in history):
            updated_date=database_now().strftime('%d/%m/%Y %I:%M%p')
            for old,new in (('2','4'),('3','5')):
                MdmSubTask.objects.filter(source=source,TaskID=task_id,TaskStatus=old).update(TaskStatus=new,DBUpdatedDate=updated_date)
        statuses=list(MdmSubTask.objects.filter(source=source,TaskID=task_id).values_list('TaskStatus',flat=True))
        if statuses and all(s in ('4','5','6','8') for s in statuses):
            MdmTask.objects.filter(source=source,TaskID=task_id).update(TaskStatus='7')
        codes={sql_key(h.WHCode) for h in history}
        for row in MdmLocationApproved.objects.filter(source=source):
            if sql_key(row.WHCode) in codes: row.delete()
    return dict(status=200,msg='Data submitted successfully'+(' and Task status updated' if completed else 'Task status not updated')+' ',
        taskId=task_id,errorCount=None,error=None,conflictErrorCount=None,conflictError=None)
