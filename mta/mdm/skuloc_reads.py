"""Master-3 task projections at native SKU/location occurrence grain."""
from collections import defaultdict
import json
from decimal import Decimal
from datetime import timedelta

from mta.mdm.clock import database_now
from mta.mdm.drafts import omit_nulls, value
from mta.mdm.skuloc import ALIASES
from mta.mdm.task_reads import TaskDenied, assigned, displayed_date, header, sql_key
from mta.presentation.context import permission_catalogue
from mta.presentation.permissions import expand_permission_ids
from mta.runtime.mdm_models import MdmLocationAttributes, MdmSkuAttributes, MdmTask
from mta.runtime.mdm_skuloc_models import (
    MdmSkuLocAddRequested, MdmSkuLocHistory, MdmSkuLocModifyRequested,
    MdmSkuLocRemoveRequested,
)

DECISIONS={'3':'Request approved','4':'Request approval reverted/ Rejected'}


def _columns(task):
    names=(task.ColumnList or '').split(',')
    result={}
    for alias, field in ALIASES.items():
        native='StockPercentForRat' if field=='StockPercentForRationing' else field
        if native in names: result[alias]=native
    return result


def _project(row, fields, *, include_nulls=False):
    result={}
    for alias, field in fields.items():
        name=field
        if not hasattr(row,name) and name=='StockPercentForRat': name='StockPercentForRationing'
        result[alias]=getattr(row,name)
    result={key:float(val) if isinstance(val,Decimal) else val for key,val in result.items()}
    return result if include_nulls else omit_nulls(result)


def _review_text(row, fields):
    # Deployed review SQL casts every selected scalar to VARCHAR(max),
    # replaces NULL with '', then returns WITHOUT_ARRAY_WRAPPER JSON text.
    values={}
    for alias,field in fields.items():
        if not hasattr(row,field) and field=='StockPercentForRat':
            field='StockPercentForRationing'
        val=getattr(row,field)
        values[alias]='' if val is None else str(int(val)) if isinstance(val,bool) else str(val)
    return json.dumps(values,ensure_ascii=False,separators=(',',':'))


def _scope_count(source, sku_code, wh_code, payload):
    products=permission_catalogue()['products']['records']
    locations=permission_catalogue()['locations']['records']
    product_ids=payload.get('product_permissions') or []
    location_ids=payload.get('location_permissions') or []
    product_triples={tuple(sql_key(r['level_'+str(i)]) for i in range(1,4)) for r in products if r['id'] in product_ids}
    location_triples={tuple(sql_key(r['level_'+str(i)]) for i in range(1,4)) for r in locations if r['id'] in location_ids}
    sc=sum(sql_key(r.SKUCode)==sql_key(sku_code) and tuple(sql_key(getattr(r,'SL'+str(i))) for i in range(1,4)) in product_triples
           for r in MdmSkuAttributes.objects.filter(source=source,owner='Importer'))
    lc=sum(sql_key(r.WHCode)==sql_key(wh_code) and tuple(sql_key(getattr(r,'LL'+str(i))) for i in range(1,4)) in location_triples
           for r in MdmLocationAttributes.objects.filter(source=source,owner='Importer'))
    return sc*lc


def _requests(source, task):
    model={1:MdmSkuLocAddRequested,2:MdmSkuLocModifyRequested,3:MdmSkuLocRemoveRequested}[task.Actiontype]
    return list(model.objects.filter(source=source,TaskId=task.TaskID))


def details(source, payload, actor, *, download=False):
    task_id=value(payload,'taskId'); task=header(source,task_id)
    if task is None: return None
    if int(task.MasterId)!=3: raise ValueError('MDM family is not delivered')
    fields=_columns(task)
    history=list(MdmSkuLocHistory.objects.filter(source=source,TaskId=task_id))
    complete_history=history
    if download:
        approver_id=str(value(payload,'approverId'))
        requester=MdmTask.objects.filter(source=source,TaskID=task_id,RequesterId=str(actor['id'])).exists()
        selected=approver_id==str(actor['id']) and any(assigned(h.ApproverId,actor['id']) for h in history)
        if not requester and not selected: raise TaskDenied('task_download_actor_required')
        history=[h for h in history if str(h.ApprovedBy)==approver_id]
    else:
        history=[h for h in history if h.Status is None and assigned(h.ApproverId,actor['id'])]
    by_pair=defaultdict(list)
    for row in history: by_pair[(sql_key(row.SKUCode),sql_key(row.WhCode))].append(row)
    requests=_requests(source,task)
    # Native RN sorts SKU ascending, then WH descending for review/modify;
    # add/remove downloads sort both keys ascending.
    requests.sort(key=lambda r:sql_key(r.WhCode),reverse=not download or task.Actiontype==2)
    requests.sort(key=lambda r:sql_key(r.SKUCode))
    rows=[]
    for requested in requests:
        pair=(sql_key(requested.SKUCode),sql_key(requested.WhCode))
        multiplicity=1 if download else _scope_count(source,requested.SKUCode,requested.WhCode,payload)
        for old in by_pair[pair]:
            for _ in range(multiplicity):
                if task.Actiontype==2:
                    if not download:
                        item=dict(new=_review_text(requested,fields),old=_review_text(old,fields))
                    else:
                        encode=lambda row:json.dumps(_project(row,fields),ensure_ascii=False,separators=(',',':'))
                        same=lambda row:(sql_key(row.SKUCode),sql_key(row.WhCode))==pair
                        # Native download reuses A-qualified columns inside
                        # its B subquery: old repeats the outer requested row.
                        item=dict(new=','.join(encode(row) for row in requests if same(row)),
                            old=','.join(encode(requested) for row in complete_history if same(row)))
                else:
                    item=_project(requested,fields,include_nulls=not download)
                    item.update(Status=DECISIONS.get(old.Status) if download else old.Status,Comments=old.Comments)
                    if download: item=omit_nulls(item)
                rows.append({'RN':len(rows)+1,**item})
    paging=value(payload,'paginationParameter')
    if paging is not None:
        page,size=int(value(paging,'pageNumber')),int(value(paging,'recordsPerPage'))
        rows=[r for r in rows if (page-1)*size+1<=r['RN']<=page*size]
    return [{'MasterId':3,'data':rows}]


def count(source, task_id, actor):
    return sum(assigned(row.ApproverId,actor['id']) for row in MdmSkuLocHistory.objects.filter(source=source,TaskId=task_id))


def history(source, payload, actor):
    sku=value(payload,'skuCode'); wh=value(payload,'whCode')
    if int(value(payload,'masterId'))!=3: raise ValueError('MDM family is not delivered')
    if not _scope_count(source,sku,wh,payload): raise TaskDenied('sku_location_scope_required')
    candidates=list(MdmTask.objects.filter(source=source,MasterId='3').exclude(TaskStatus='1').exclude(TaskStatus=None).order_by('PendingSince'))
    selected=[]; names=set()
    for task in candidates:
        rows=[row for row in _requests(source,task) if sql_key(row.SKUCode)==sql_key(sku) and sql_key(row.WhCode)==sql_key(wh)]
        if rows:
            selected.append((task,rows));names.update((task.ColumnList or '').split(','))
    fields={alias:('StockPercentForRat' if field=='StockPercentForRationing' else field)
            for alias,field in ALIASES.items()
            if ('StockPercentForRat' if field=='StockPercentForRationing' else field) in names}
    if not fields:return None
    result=[];all_history=list(MdmSkuLocHistory.objects.filter(source=source))
    for task,requests in selected:
        for requested in requests:
            matches=[h for h in all_history if h.TaskId==task.TaskID and sql_key(h.SKUCode)==sql_key(sku) and sql_key(h.WhCode)==sql_key(wh)] or [None]
            for old in matches:
                if task.Actiontype==3:
                    projected={alias:(requested.SKUCode if field=='SKUCode' else requested.WhCode if field=='WhCode' else None)
                               for alias,field in fields.items()}
                else:
                    # Native builds one global column list for all matching add
                    # and modify owners. A physical-column mismatch fails here.
                    projected=_project(requested,fields,include_nulls=True)
                result.append(omit_nulls(dict(**projected,TaskId=task.TaskID,
                    PendingSince=displayed_date(task.PendingSince),RequesterName=task.RequesterName,
                    ApproverName=old.ApprovedBy if old else None)))
    return sorted(result,key=lambda row:row.get('PendingSince') or '') or None


def history_skus(source, payload):
    if int(value(payload,'masterId'))!=3: raise ValueError('MDM family is not delivered')
    if payload.get('product_permissions') is None or payload.get('location_permissions') is None:
        raise ValueError('native permission lists are required')
    products=permission_catalogue()['products']['records']; locations=permission_catalogue()['locations']['records']
    pids=expand_permission_ids(products,payload['product_permissions']); lids=expand_permission_ids(locations,payload['location_permissions'])
    ptriples={tuple(sql_key(p['level_'+str(i)]) for i in range(1,4)) for p in products if p['id'] in pids}
    ltriples={tuple(sql_key(p['level_'+str(i)]) for i in range(1,4)) for p in locations if p['id'] in lids}
    skus={sql_key(r.SKUCode) for r in MdmSkuAttributes.objects.filter(source=source,owner='Importer')
          if tuple(sql_key(getattr(r,'SL'+str(i))) for i in range(1,4)) in ptriples}
    whs={sql_key(r.WHCode) for r in MdmLocationAttributes.objects.filter(source=source,owner='Importer')
         if tuple(sql_key(getattr(r,'LL'+str(i))) for i in range(1,4)) in ltriples}
    upper=database_now().replace(hour=0,minute=0,second=0,microsecond=0)
    task_ids=set(MdmTask.objects.filter(source=source,MasterId='3',Actiontype=2,
        PendingSince__gte=upper-timedelta(days=90),PendingSince__lte=upper).values_list('TaskID',flat=True))
    result={}
    for row in MdmSkuLocHistory.objects.filter(source=source,TaskId__in=task_ids):
        pair=(sql_key(row.SKUCode),sql_key(row.WhCode))
        if pair[0] in skus and pair[1] in whs and pair not in result:
            result[pair]={'SKUCode':row.SKUCode,'WHCode':row.WhCode}
    return list(result.values())
