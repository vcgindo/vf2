"""Master-3 submission and approval with native per-statement effects."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import logging

from django.db import DatabaseError
from django.db.models import CharField
from django.db.models.functions import Cast, Lower
from django.db import models

from mta.mdm.clock import database_now
from mta.mdm import skuloc_audit
from mta.mdm.drafts import now, value
from mta.mdm.skuloc import ALIASES, FIELDS
from mta.mdm.task_reads import TaskDenied, assigned, header, require_requester, sql_key
from mta.presentation.context import permission_catalogue
from mta.runtime.mdm_models import MdmLocationAttributes, MdmSkuAttributes, MdmSubTask, MdmTask
from mta.runtime.mdm_skuloc_models import (
    MdmSkuLocAddApproved, MdmSkuLocAddRequested, MdmSkuLocCurrent, MdmSkuLocHistory,
    MdmSkuLocMasterPair, MdmSkuLocModifyApproved, MdmSkuLocModifyRequested, MdmSkuLocPair,
    MdmSkuLocRemoveApproved, MdmSkuLocRemoveRequested,
)

log = logging.getLogger(__name__)
NUMERIC = {'n','mn','rlt','rcp','gcp','ocp','ps','st','pso','spr','npr','moc','pt'}


class NativeSqlValueError(Exception):
    pass


def response(action, task_id, errors, conflicts=None, conflict_count=0, missing_count=0):
    msg={1:' Data Add Sucessfully',2:' Data Saved Sucessfully',3:' Data removed Sucessfully'}[action]
    if action==2 and missing_count: msg+=' .'+str(missing_count)+' items do not exist in VectorFLOW'
    return dict(status=200,msg=msg,
        taskId=task_id,errorCount=str(sum(len(item['errorData']) for item in errors)),error=errors,
        conflictErrorCount=str(conflict_count),conflictError=conflicts)


def convert(row, keys):
    result = {}
    for alias in keys:
        raw = row[alias]
        if raw is None:
            raise ValueError('native value.ToString requires a value')
        text = str(raw)
        name = ALIASES[alias]
        if name == 'StockPercentForRationing':
            name = 'StockPercentForRat'
        try:
            if alias in ('spr', 'npr') and text == '':
                result[name] = 100 if alias == 'spr' else 0
            elif alias in NUMERIC:
                result[name] = Decimal(text) if alias in ('st','pso','pt') and text else (int(text) if text else None)
            elif alias == 'da':
                result[name] = text.lower() in ('yes','1','y')
            else:
                result[name] = text
        except (InvalidOperation, ValueError) as exc:
            raise NativeSqlValueError from exc
    return result


def _scope(source, model, owner, code_name, level_prefix, permission_kind, permission_ids):
    records = permission_catalogue()[permission_kind]['records']
    triples = {tuple(sql_key(row['level_'+str(i)]) for i in range(1,4))
               for row in records if row['id'] in permission_ids}
    return {getattr(row,code_name) for row in model.objects.filter(source=source,owner=owner)
            if tuple(sql_key(getattr(row,level_prefix+str(i))) for i in range(1,4)) in triples}


def _key_expression(name):
    return Lower(models.Func(Cast(name,CharField()),models.Value(' '),function='rtrim'))


def _pair_rows(queryset, sku_codes, wh_codes, wh_field):
    return queryset.annotate(_sku_key=_key_expression('SKUCode'),
        _wh_key=_key_expression(wh_field)).filter(_sku_key__in={sql_key(x) for x in sku_codes},
        _wh_key__in={sql_key(x) for x in wh_codes})


def _approvers(source, rows, users):
    sku_codes = {sql_key(row['sc']) for row in rows}
    wh_codes = {sql_key(row['wc']) for row in rows}
    products = permission_catalogue()['products']['records']
    locations = permission_catalogue()['locations']['records']
    sku_triples = {tuple(sql_key(getattr(row,'SL'+str(i))) for i in range(1,4))
        for row in MdmSkuAttributes.objects.filter(source=source,owner='Importer') if sql_key(row.SKUCode) in sku_codes}
    loc_triples = {tuple(sql_key(getattr(row,'LL'+str(i))) for i in range(1,4))
        for row in MdmLocationAttributes.objects.filter(source=source,owner='Importer') if sql_key(row.WHCode) in wh_codes}
    product_ids = {p['id'] for p in products if tuple(sql_key(p['level_'+str(i)]) for i in range(1,4)) in sku_triples}
    location_ids = {p['id'] for p in locations if tuple(sql_key(p['level_'+str(i)]) for i in range(1,4)) in loc_triples}
    result=[]
    for user in users:
        if product_ids.intersection(user['product_id']) and location_ids.intersection(user['location_id']):
            if not any(str(item['id'])==str(user['id']) for item in result): result.append(user)
    return result


def _history_values(row, names):
    values={name:getattr(row,name) for name in names if hasattr(row,name)}
    if 'StockPercentForRat' in names and hasattr(row,'StockPercentForRationing'):
        # The native history INSERT rewrites the staging column spelling.
        values['StockPercentForRationing']=row.StockPercentForRationing
    return values


def submit(source, payload, actor, action):
    if int(value(payload,'id')) != 3:
        raise ValueError('MDM family is not delivered')
    supplied_id=value(payload,'taskId')
    if supplied_id is None:
        raise ValueError('native TaskId.ToString requires a value')
    if supplied_id:
        require_requester(source,supplied_id,actor)
    rows=value(payload,'data')
    keys=list(rows[0])
    names=[('StockPercentForRat' if ALIASES[k]=='StockPercentForRationing' else ALIASES[k]) for k in keys]
    product_ids=payload.get('product_permissions') or []
    location_ids=payload.get('location_permissions') or []
    sku_scope=_scope(source,MdmSkuAttributes,'Importer','SKUCode','SL','products',product_ids)
    loc_scope=_scope(source,MdmLocationAttributes,'Importer','WHCode','LL','locations',location_ids)
    if action==3:
        allowed=[row for row in rows if row['sc'] in sku_scope and row['wc'] in loc_scope]
    else:
        sku_keys={sql_key(x) for x in sku_scope}; loc_keys={sql_key(x) for x in loc_scope}
        allowed=[row for row in rows if sql_key(row['sc']) in sku_keys and sql_key(row['wc']) in loc_keys]
    errors=[]
    excluded=[row for row in rows if not any(row is x for x in allowed)]
    if excluded:
        errors.append(dict(errorType=('Unauthorized SKU and Location Codes exist ' if action==3 else
            'Either you are Unauthorized for SKU Code or Location Code or both'),errorData=excluded))
    sku_codes=[row['sc'] for row in allowed]; wh_codes=[row['wc'] for row in allowed]
    pair_query=_pair_rows(MdmSkuLocPair.objects.filter(source=source,owner='Importer'),sku_codes,wh_codes,'LocCode')
    pairs={(sql_key(sc),sql_key(wc)) for sc,wc in pair_query.values_list('SKUCode','LocCode')}
    if action==1:
        invalid=[row for row in allowed if (sql_key(row['sc']),sql_key(row['wc'])) in pairs]
        category='SKU Code & Location Codes already exist.'
    elif action==2:
        invalid=[row for row in allowed if (sql_key(row['sc']),sql_key(row['wc'])) not in pairs]
        category='Either SKU Code or Location code or both does not exist '
    else:
        # Native delete bug tests the submitted SKU and location independently.
        skus=set(MdmSkuLocPair.objects.filter(source=source,owner='Importer',SKUCode__in=sku_codes).values_list('SKUCode',flat=True))
        locs=set(MdmSkuLocPair.objects.filter(source=source,owner='Importer',LocCode__in=wh_codes).values_list('LocCode',flat=True))
        invalid=[row for row in allowed if row['sc'] not in skus or row['wc'] not in locs]
        category='SKU and location code not exist '
    if invalid: errors.append(dict(errorType=category,errorData=invalid))
    allowed=[row for row in allowed if not any(row is x for x in invalid)]
    conflicts=None; conflict_count=0
    if action==2 and not value(payload,'isOverwrite',False):
        pending={(h.SKUCode,h.WhCode) for h in MdmSkuLocHistory.objects.filter(source=source,Status=None)}
        conflicting=[row for row in allowed if (row['sc'],row['wc']) in pending]
        if conflicting:
            conflict_count=len(conflicting); conflicts=[]
            wanted={(row['sc'],row['wc']):row for row in conflicting}
            pending_history=defaultdict(list)
            for h in MdmSkuLocHistory.objects.filter(source=source,Status=None):
                pair=(h.SKUCode,h.WhCode)
                if pair in wanted: pending_history[(h.TaskId,pair)].append(h)
            grouped={}
            for task in MdmTask.objects.filter(source=source,Actiontype=2).order_by('RequesterId'):
                group=(task.RequesterId,task.RequesterName)
                for staged in MdmSkuLocModifyRequested.objects.filter(source=source,TaskId=task.TaskID):
                    pair=(staged.SKUCode,staged.WhCode)
                    for _ in pending_history[(task.TaskID,pair)]:
                        old={alias:getattr(staged,('StockPercentForRat' if field=='StockPercentForRationing' else field))
                             for alias,field in ALIASES.items() if alias in keys}
                        grouped.setdefault(group,[]).append(dict(oldData=old,requestedData=wanted[pair]))
            conflicts=[dict(user=name,conflictdetails=details) for (_,name),details in grouped.items()]
            allowed=[row for row in allowed if not any(row is x for x in conflicting)]
    stamp=now(); task_id=supplied_id or str(actor['id'])+'_'+stamp.strftime('%Y%m%d%H%M%S')
    missing_count=0
    for offset in range(0,len(allowed),999):
        chunk=allowed[offset:offset+999]
        approvers=_approvers(source,chunk,payload['all_users'])
        approver_ids=','.join(str(a['id']) for a in approvers)
        approver_names=','.join(a['name'] for a in approvers)
        try:
            converted=[convert(row,keys) for row in chunk]
        except (NativeSqlValueError, TypeError):
            log.exception('master3 native submission value failure')
            continue
        # Native SQL construction resolves this setting before PostQuery.
        # Its failure is not swallowed by the statement-error handler below.
        audit_enabled = skuloc_audit.enabled(source)
        try:
            audit_rows = converted
            if action==1:
                MdmSkuLocAddRequested.objects.bulk_create([MdmSkuLocAddRequested(source=source,Approved=False,TaskId=task_id,**row) for row in converted])
                history=[{('StockPercentForRationing' if key=='StockPercentForRat' else key):val
                          for key,val in row.items()} for row in converted]
            elif action==2:
                master=defaultdict(list)
                mq=_pair_rows(MdmSkuLocMasterPair.objects.filter(source=source,owner='Importer'),
                    [r['sc'] for r in chunk],[r['wc'] for r in chunk],'WhCode')
                for old in mq: master[(sql_key(old.SKUCode),sql_key(old.WhCode))].append(old)
                accepted=[]
                audit_rows=[]
                for row in converted:
                    matches=master[(sql_key(row['SKUCode']),sql_key(row['WhCode']))]
                    if not matches: missing_count+=1
                    for old in matches:
                        item=dict(row);item['ParentWhCode']=old.ParentWhCode;accepted.append(item)
                        audit_rows.append(dict(row))
                MdmSkuLocModifyRequested.objects.bulk_create([MdmSkuLocModifyRequested(source=source,Approved=False,TaskId=task_id,**row) for row in accepted])
                current=_pair_rows(MdmSkuLocCurrent.objects.filter(source=source,owner='Importer'),
                    [r['sc'] for r in chunk],[r['wc'] for r in chunk],'WhCode')
                history=[_history_values(old,names) for old in current for row in chunk
                    if sql_key(old.SKUCode)==sql_key(row['sc']) and sql_key(old.WhCode)==sql_key(row['wc'])]
            else:
                MdmSkuLocRemoveRequested.objects.bulk_create([MdmSkuLocRemoveRequested(source=source,SKUCode=row['sc'],WhCode=row['wc'],Approved=False,TaskId=task_id) for row in chunk])
                current=MdmSkuLocCurrent.objects.filter(source=source,owner='Importer',SKUCode__in=[r['sc'] for r in chunk],WhCode__in=[r['wc'] for r in chunk])
                history=[_history_values(old,names) for old in current for row in chunk
                    if old.SKUCode==row['sc'] and old.WhCode==row['wc']]
            if action in (2, 3):
                # Modify/RemoveSKULocMaster record GETDATE(), not the current
                # pair's introduction date, in TaskNMSAllItemsHistory.
                history_date = database_now().date()
                for item in history:
                    item['SKUIntroDate'] = history_date
            MdmSkuLocHistory.objects.bulk_create([MdmSkuLocHistory(source=source,TaskId=task_id,ApproverId=approver_ids,**row) for row in history])
            skuloc_audit.submitted(source, action, audit_rows, actor, active=audit_enabled)
            if not supplied_id and offset==0:
                task_names=names if action!=3 else ['SKUCode','WhCode']
                MdmTask.objects.create(source=source,TaskID=task_id,PendingSince=database_now(),
                    TaskName={1:'Add',2:'Modify',3:'Remove'}[action]+'-SkuLocationMaster',
                    ApproverId=approver_ids,ApproversName=approver_names,RequesterId=str(actor['id']),
                    RequesterName=actor['name'],TaskStatus='1',MasterId='3',Actiontype=action,
                    ColumnList=','.join(task_names))
                MdmSubTask.objects.bulk_create([MdmSubTask(source=source,TaskID=task_id,ApproverId=str(a['id']),ApproverName=a['name'],TaskStatus='1') for a in approvers])
        except (DatabaseError,NativeSqlValueError,TypeError):
            log.exception('master3 native submission statement failure')
    return response(action,task_id,errors,conflicts,conflict_count,missing_count)


def delete(source, task_id, actor):
    require_requester(source,task_id,actor)
    for model,field in ((MdmSkuLocHistory,'TaskId'),(MdmSkuLocAddRequested,'TaskId'),
            (MdmSkuLocModifyRequested,'TaskId'),(MdmSkuLocRemoveRequested,'TaskId'),
            (MdmTask,'TaskID'),(MdmSubTask,'TaskID')):
        model.objects.filter(source=source,**{field:task_id}).delete()


def _copy_approved(source, task_id, action):
    if action in (1,2):
        requested_model,target_model=(MdmSkuLocAddRequested,MdmSkuLocAddApproved) if action==1 else (MdmSkuLocModifyRequested,MdmSkuLocModifyApproved)
        rows=list(requested_model.objects.filter(source=source,TaskId=task_id,Approved=True))
        existing=list(target_model.objects.filter(source=source))
        existing_keys={(sql_key(row.SKUCode),sql_key(row.WhCode)) for row in existing}
        names=[f.name for f in target_model._meta.fields if f.name not in ('id','source')]
        target_model.objects.bulk_create([target_model(source=source,
            **{name:getattr(row,name) for name in names}) for row in rows
            if (sql_key(row.SKUCode),sql_key(row.WhCode)) not in existing_keys])
        incoming=defaultdict(list)
        for row in rows: incoming[(sql_key(row.SKUCode),sql_key(row.WhCode))].append(row)
        for target in target_model.objects.filter(source=source):
            candidates=incoming[(sql_key(target.SKUCode),sql_key(target.WhCode))]
            if not candidates: continue
            values=[tuple(getattr(row,name) for name in names) for row in candidates]
            if any(item!=values[0] for item in values[1:]):
                raise ValueError('native duplicate approved-input UPDATE is incomparable')
            row=candidates[0]; changed=[]
            for name in names:
                if name in ('SKUCode','WhCode','Approved'): continue
                incoming_value=getattr(row,name)
                # SQL NULLIF(value,'') treats typed numeric/bit zero as empty.
                keep=incoming_value is None or incoming_value=='' or incoming_value==0
                if action==2 and name=='SKULocAtt07': keep=incoming_value is None
                if not keep: setattr(target,name,incoming_value);changed.append(name)
            if changed: target.save(update_fields=changed)
    else:
        rows=list(MdmSkuLocRemoveRequested.objects.filter(source=source,TaskId=task_id,Approved=True))
        existing={(sql_key(sc),sql_key(wc)) for sc,wc in MdmSkuLocRemoveApproved.objects.filter(source=source).values_list('SKUCode','WhCode')}
        seen=set(); additions=[]
        for row in rows:
            pair=(sql_key(row.SKUCode),sql_key(row.WhCode))
            if pair not in existing and pair not in seen:
                seen.add(pair);additions.append(MdmSkuLocRemoveApproved(source=source,SKUCode=row.SKUCode,WhCode=row.WhCode,Approved=True))
        MdmSkuLocRemoveApproved.objects.bulk_create(additions)


def approve(source, payload, actor):
    task_id=value(payload,'taskId'); task=header(source,task_id)
    if task is None or task.MasterId!='3': raise TaskDenied('task_reviewer_required')
    rows=value(payload,'data'); valid=[row for row in rows if 'sc' in row and 'wc' in row]
    history=list(MdmSkuLocHistory.objects.filter(source=source,TaskId=task_id))
    affected={(sql_key(r['sc']),sql_key(r['wc'])) for r in valid}
    affected_history=[h for h in history if (sql_key(h.SKUCode),sql_key(h.WhCode)) in affected]
    if not valid or not affected_history or not all(assigned(h.ApproverId,actor['id']) for h in affected_history):
        raise TaskDenied('task_row_reviewer_scope_required')
    product_scope={sql_key(code) for code in _scope(source,MdmSkuAttributes,'Importer','SKUCode','SL','products',payload.get('product_permissions') or [])}
    location_scope={sql_key(code) for code in _scope(source,MdmLocationAttributes,'Importer','WHCode','LL','locations',payload.get('location_permissions') or [])}
    if any(pair[0] not in product_scope or pair[1] not in location_scope for pair in affected):
        raise TaskDenied('task_row_reviewer_scope_required')
    decisions={}
    for row in valid:
        pair=(sql_key(row['sc']),sql_key(row['wc'])); decision=(str(row['status']),str(row['comments']))
        if pair in decisions and decisions[pair] != decision:
            raise ValueError('native duplicate decision UPDATE is incomparable')
        decisions[pair]=decision
    request_model={1:MdmSkuLocAddRequested,2:MdmSkuLocModifyRequested,3:MdmSkuLocRemoveRequested}[task.Actiontype]
    try:
        for row in request_model.objects.filter(source=source,TaskId=task_id):
            decision=decisions.get((sql_key(row.SKUCode),sql_key(row.WhCode)))
            if decision: request_model.objects.filter(pk=row.pk).update(Approved=decision[0]=='3')
        for row in history:
            decision=decisions.get((sql_key(row.SKUCode),sql_key(row.WhCode)))
            if decision: MdmSkuLocHistory.objects.filter(pk=row.pk).update(Status=decision[0],Comments=decision[1],ApprovedBy=str(actor['id']))
        _copy_approved(source,task_id,task.Actiontype)
        if task.Actiontype==2:
            rejected={(sql_key(r['sc']),sql_key(r['wc'])) for r in valid if str(r['status'])=='4'}
            for row in MdmSkuLocModifyRequested.objects.filter(source=source,TaskId=task_id):
                if (sql_key(row.SKUCode),sql_key(row.WhCode)) in rejected:
                    MdmSkuLocModifyRequested.objects.filter(pk=row.pk).update(Approved=True)
    except DatabaseError:
        log.exception('master3 native decision SQL failure')
    audit_enabled = skuloc_audit.enabled(source)
    try:
        skuloc_audit.reviewed(source, task.Actiontype, valid, actor, active=audit_enabled)
    except DatabaseError:
        log.exception('master3 native decision audit failure')
    mine=[h for h in MdmSkuLocHistory.objects.filter(source=source,TaskId=task_id) if assigned(h.ApproverId,actor['id'])]
    completed=bool(mine) and all(h.Status in ('3','4') for h in mine)
    date=database_now().strftime('%d/%m/%Y %I:%M %p')
    MdmSubTask.objects.filter(source=source,TaskID=task_id,ApproverId=str(actor['id'])).update(ApprovedOrRejectedDate=date)
    all_history=list(MdmSkuLocHistory.objects.filter(source=source,TaskId=task_id))
    if completed:
        for sub in MdmSubTask.objects.filter(source=source,TaskID=task_id).exclude(ApprovedOrRejectedDate=None):
            assigned_rows=[h for h in all_history if assigned(h.ApproverId,sub.ApproverId)]
            if assigned_rows and all(h.Status in ('3','4') for h in assigned_rows):
                status='2' if all(h.Status=='3' for h in assigned_rows) else '6' if all(h.Status=='4' for h in assigned_rows) else '3'
                MdmSubTask.objects.filter(pk=sub.pk).update(TaskStatus=status,
                    ApprovedOrRejectedDate=database_now().strftime('%d/%m/%Y %I:%M %p'))
        MdmSubTask.objects.filter(source=source,TaskID=task_id,ApprovedOrRejectedDate=None).update(TaskStatus='8')
    else:
        MdmSubTask.objects.filter(source=source,TaskID=task_id,ApproverId=str(actor['id'])).update(TaskStatus='3')
    return dict(status=200,msg='Data submitted successfully'+(' and Task status updated' if completed else 'Task status not updated')+' ',
        taskId=task_id,errorCount=None,error=None,conflictErrorCount=None,conflictError=None)
