"""Explicit isolated legacy UI fixture boundary; never an engine publication.

The fixture owns an immutable consumer receipt roster and dedicated actors.
Normal production selection, calculations and provenance remain separate.
"""
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import connection

from mta.runtime.models import CalculationRun
from mta.runtime.relational_state import CATALOG,wire_value
from mta.serialization import digest


def enabled():
    return bool(getattr(settings,'VF_MTA_FIXTURE_FILE','') or getattr(settings,'VF_MTA_FIXTURE_SHA256',''))


def unavailable(reason):
    from mta.presentation.context import PublicationUnavailable
    raise PublicationUnavailable('fixture_'+reason)


def policy():
    if not settings.VF_MTA_FIXTURE_FILE or not settings.VF_MTA_FIXTURE_SHA256:
        unavailable('explicit_identity_required')
    if (settings.VF_MTA_PUBLISHED_RUN or settings.VF_MTA_PUBLISHED_DIGEST or settings.VF_MTA_ACTIONS_ENABLED or
        settings.VF_MTA_HIERARCHY_FILE or settings.VF_MTA_HIERARCHY_SHA256 or
        settings.VF_MTA_TERMINAL_FILE or settings.VF_MTA_TERMINAL_SHA256 or
        settings.VF_MTA_EXCESS_HISTORY_FILE or settings.VF_MTA_EXCESS_HISTORY_SHA256 or
        settings.VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY):
        unavailable('production_settings_must_be_unset')
    raw=Path(settings.VF_MTA_FIXTURE_FILE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=settings.VF_MTA_FIXTURE_SHA256:unavailable('policy_changed')
    value=json.loads(raw)
    if value.get('version')!='legacy-ui-fixture-v1' or value.get('database')!=connection.settings_dict['NAME']:
        unavailable('isolated_database_required')
    if value['permissions_sha256']!=settings.VF_MTA_PERMISSIONS_SHA256:unavailable('catalogue_changed')
    return value


def selected_run():
    value=policy()
    run=CalculationRun.objects.filter(pk=value['run_id'],kind='LEGACY_UI_FIXTURE',status='FIXTURE_BLOCKED').first()
    if run is None:unavailable('run_identity_changed')
    expected=dict(origin='human-supplied-original-vm-backups',dataset=value['identity'],manifest_sha256=value['manifest_sha256'])
    if (run.input_payload!=expected or run.input_digest!=digest(expected) or str(run.business_date)!=value['business_date'] or
        run.execution_revision!='stage2-vm-source-copy-v1' or run.output_digest or run.production_digest or
        run.production_manifest or run.parity_summary or run.output_roster or run.failure or run.opening_key or
        run.predecessor_id or run.completed_at or run.checkpoints.exists() or run.commands.exists()):
        unavailable('run_invariant_changed')
    return run


def receipts():
    with connection.cursor() as cur:
        cur.execute('SELECT binding,metadata FROM stage2_owner.consumer_receipts ORDER BY binding')
        return {k:json.loads(v) if isinstance(v,str) else v for k,v in cur.fetchall()}


def binding():
    value=policy();run=selected_run();items=receipts()
    with connection.cursor() as cur:
        cur.execute('SELECT metadata FROM stage2_owner.consumer_publication WHERE identity=%s',[value['identity']])
        result=cur.fetchone()
        if not result:unavailable('final_receipt_required')
        final=json.loads(result[0]) if isinstance(result[0],str) else result[0]
    if final!=value['consumer_publication'] or final['receipts_digest']!=digest(items):unavailable('receipt_roster_changed')
    if digest(freeze_state())!=value['freeze_digest']:unavailable('immutability_changed')
    from mta.presentation.context import permission_catalogue
    catalogue=permission_catalogue()
    if catalogue.get('manifest_sha256')!=value['manifest_sha256']:unavailable('catalogue_source_changed')
    return run,digest(dict(policy_sha256=settings.VF_MTA_FIXTURE_SHA256,publication=final,receipts=items,catalogue=catalogue))


def freeze_state():
    with connection.cursor() as cur:
        cur.execute("SELECT n.nspname,c.relname,t.tgenabled,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE t.tgname='stage2_immutable' ORDER BY 1,2")
        triggers=cur.fetchall()
        cur.execute("SELECT pg_get_functiondef('stage2_owner.deny_fixture_mutation()'::regprocedure)")
        function=cur.fetchone()[0]
    return dict(triggers=triggers,function=function)


def pair_rows(run,path,sku,location,cutoff=None):
    """Read only a named pair from frozen relational history, retaining bags."""
    from mta.runtime.relational_state import table_sql,quote
    item=image_metadata(run,path)
    fields=item['fields'];columns={name.casefold():column for name,column,kind in fields}
    sku_column=columns['skucode']
    location_column=next(columns[k] for k in ('whcode','loccode') if k in columns)
    where='vf_run_id=%s AND vf_image=%s AND '+quote(sku_column)+'=%s AND '+quote(location_column)+'=%s'
    params=[run.pk,path,sku,location]
    if cutoff:
        date_column=columns['reportdate'] if 'reportdate' in columns else columns['suggestiondate']
        where+=' AND '+quote(date_column)+'>=%s';params.append(cutoff)
    with connection.cursor() as cur:
        cur.execute('SELECT '+','.join(quote(column) for name,column,kind in fields)+' FROM '+table_sql(item['table'])+' WHERE '+where+' ORDER BY vf_ordinal',params)
        return [{name:wire_value(v,kind) for (name,column,kind),v in zip(fields,row)} for row in cur.fetchall()]


def bpr_ancillary(run):
    """Two explicit native ancillary bags from sealed, frozen typed staging."""
    from datetime import date,datetime
    from decimal import Decimal
    selected,_=binding()
    if run.pk!=selected.pk:unavailable('ancillary_run_changed')
    populations={
        'InTransitData':('Demo_Importer_1','SKUCode WhCode ParentWhCode CurrentLocationCode LRCode OrderNo CreationDate GateOutDate InTransitQty TransporterCode Ageing ETA TLT SLT Remark ReportDate'.split()),
        'BPRReport_RemarkDetails':('Demo_BPR_1','SKUCode WhCode Remark Username RemarkDate'.split())}
    result={}
    with connection.cursor() as cur:
        cur.execute('SELECT manifest_sha256 FROM stage2_owner.manifest')
        if cur.fetchall()!=[(policy()['manifest_sha256'],)]:unavailable('ancillary_manifest_changed')
        for name,(source,fields) in populations.items():
            cur.execute('SELECT values_sha256,row_count FROM stage2_owner.tables WHERE source=%s AND table_name=%s',[source,name])
            receipt=cur.fetchone()
            if not receipt:unavailable('ancillary_source_missing:'+name)
            # This fixture's native populations are0 and5 rows. Refuse a broader
            # population without an explicit new bounded adapter decision.
            if receipt[1]>(0 if name=='InTransitData' else 5):unavailable('ancillary_population_changed:'+name)
            quote=connection.ops.quote_name
            cur.execute('SELECT * FROM '+quote('stage_'+source.lower())+'.'+quote('dbo__'+name)+' ORDER BY vf_source_ordinal')
            if [column[0] for column in cur.description]!=['vf_source_ordinal',*fields]:unavailable('ancillary_columns_changed:'+name)
            rows=[];checksum=hashlib.sha256()
            for ordinal,record in enumerate(cur.fetchall()):
                if record[0]!=ordinal:unavailable('ancillary_ordinal_changed:'+name)
                raw=[v.isoformat() if isinstance(v,(date,datetime)) else str(v) if isinstance(v,Decimal) else v for v in record[1:]]
                checksum.update((json.dumps(raw,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode())
                rows.append(dict(zip(fields,record[1:])))
            if (checksum.hexdigest(),len(rows))!=receipt:unavailable('ancillary_values_changed:'+name)
            result[name]=rows
    return result


def bpr_image_rows(run,path):
    """Read BPR's seven frozen inputs, reusing the completed full-value proof."""
    from django.db import transaction
    from mta.runtime.relational_state import table_sql,quote
    allowed={'closing/importer/'+name for name in ('SkuAttributeData','LocationAttributeData','SkuLocAttributeData')}
    allowed.update(('reports/bpr/BPR_Table','reports/bpr/vf_RationedReqReport',
        'closing/dbm/SKULocStandardAttributes','closing/btr/BufferTrendPhysicalInv'))
    if path not in allowed:unavailable('bpr_input_outside_boundary')
    # bpr_context first calls bpr_ancillary, which binds the immutable tables,
    # finalized manifest and receipt roster. No cached or recalculated rows.
    item=image_metadata(run,path);fields=item['fields'];rows=[]
    if path=='reports/bpr/vf_RationedReqReport':
        used={'SKUCode','WhCode','VirtualNorm','PhysicalInventoryColorSequence',
              'PhysicalInventoryPen','DispatchPen','PhysicalInventoryColor','DispatchColor'}
        fields=[field for field in fields if field[0] in used]
    if path=='closing/btr/BufferTrendPhysicalInv':
        # BPR uses availability/count fields, never the ninety daily colours.
        # Retain every source row and all fields used by its joins/filters.
        daily={f'D{i}' for i in range(1,91)}
        fields=[field for field in fields if field[0] not in daily]
    with transaction.atomic():
        with connection.connection.cursor(name='fixture_bpr_input') as cur:
            cur.itersize=1000
            cur.execute('SELECT vf_ordinal,'+','.join(quote(c) for _,c,_ in fields)+' FROM '+table_sql(item['table'])+
                ' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal',[run.pk,path])
            for ordinal,record in enumerate(cur):
                if record[0]!=ordinal:unavailable('bpr_input_ordinal_changed')
                rows.append({name:wire_value(value,kind) for (name,column,kind),value in zip(fields,record[1:])})
    if len(rows)!=item['count']:unavailable('bpr_input_count_changed')
    return rows


def receipt(run,binding):
    if not enabled() or run.pk!=selected_run().pk:unavailable('not_selected')
    value=policy()
    with connection.cursor() as cur:
        cur.execute('SELECT metadata FROM stage2_owner.consumer_receipts WHERE binding=%s',[binding])
        row=cur.fetchone()
    if not row:unavailable('binding_unavailable:'+binding)
    item=json.loads(row[0]) if isinstance(row[0],str) else row[0]
    if item['provenance']['manifest_sha256']!=value['manifest_sha256']:unavailable('source_manifest_changed')
    return item


def image_metadata(run,path):
    item=receipt(run,path)
    expected='/'.join(CATALOG['bindings'].get(path,[]))
    if item.get('image')!=path or item.get('table')!=expected or expected not in CATALOG['tables']:unavailable('image_contract_changed')
    allowed={name for name,kind in CATALOG['tables'][item['table']]}
    if any(source!=target or target not in allowed for source,target,kind in item['fields']):unavailable('image_columns_changed')
    return item


def projection_rows(run,model,*,report_date=None):
    item=receipt(run,'projection/'+model.__name__)
    fields=item['fields']
    if item.get('model')!=model.__name__ or len(item['wire'])!=len(fields):unavailable('projection_contract_changed')
    if fields!=[f.name for f in model._meta.fields if f.name not in ('id','run','ordinal')]:unavailable('projection_columns_changed')
    if report_date is not None:
        # Admission binds the full loader checksum and immutable table guards.
        # A current-day consumer must not transfer/hash every historical date.
        selected, _ = binding()
        if selected.pk != run.pk:unavailable('projection_selected_run_changed')
        records = model.objects.filter(run=run,ReportDate=report_date).order_by('ordinal').values_list('ordinal',*fields)
        rows=[]; previous=-1
        for record in records.iterator(chunk_size=1000):
            if not previous < record[0] < item['count']:unavailable('projection_selected_ordinal_changed')
            previous=record[0]
            rows.append({name:wire_value(v,kind) for name,kind,v in zip(fields,item['wire'],record[1:])})
        return rows
    rows=[];h=hashlib.sha256(b'[');count=0
    for ordinal,record in enumerate(model.objects.filter(run=run).order_by('ordinal').values_list('ordinal',*fields).iterator(chunk_size=1000)):
        if record[0]!=ordinal:unavailable('projection_ordinal_changed')
        row={name:wire_value(v,kind) for name,kind,v in zip(fields,item['wire'],record[1:])}
        if count:h.update(b',')
        h.update(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode());count+=1
        if report_date is None or row['ReportDate']==report_date:rows.append(row)
    h.update(b']')
    if count!=item['count'] or h.hexdigest()!=item['digest']:unavailable('projection_values_changed')
    return rows


def actor_allowed(identity,payload):
    if not identity:return False
    actor=next((a for a in policy()['actors'] if a['id']==identity.get('id') and a['email']==identity.get('email')),None)
    return bool(actor and sorted(payload.get('product_permissions',[]))==sorted(actor['products']) and
                sorted(payload.get('location_permissions',[]))==sorted(actor['locations']))


def grid_subjects(state,payload=None):
    """Bound native DBM joins to their actual Suggestions subjects.

    The unchanged DBM selector only joins these pair-owned rows to Suggestions.
    Keep every matching occurrence and ordinal; scope multiplicity is still
    applied by the existing final selector. Global attributes stay complete.
    """
    from mta.presentation.dbm import key
    selected=state['Suggestions']
    if payload is not None:
        from mta.presentation.context import scope
        products,locations=scope(payload,attributes=state)
        selected=[row for row in selected if key(row)[0] in products and key(row)[1] in locations]
    pairs={key(row) for row in selected}
    result={**state,'Suggestions':selected}
    for name in ('DBMMaster','NormAcceptanceTbl','SkuLocAttributeData'):
        result[name]=[row for row in state[name] if key(row) in pairs]
    return result


def dbm_grid_rows(state, *, predicate=None):
    """Feed native presentation joins bounded, order-preserving subject bags."""
    from collections import defaultdict
    from mta.presentation.dbm import dbm_rows,key
    selectors={'DBMMaster':key,'NormAcceptanceTbl':key,
        'SKUDescriptionTbl':lambda r:r['SKUCode'],'SiteDescriptionTbl':lambda r:r['WHCode'],
        'ReasonCodes':lambda r:r['Id'],'SkuAttributeData':lambda r:r['SKUCode'],
        'SkuLocAttributeData':lambda r:(r['SKUCode'],r['LocCode']),
        'LocationAttributeData':lambda r:r['WHCode']}
    indexes={}
    for table,selector in selectors.items():
        index=defaultdict(list)
        for row in state[table]:index[selector(row)].append(row)
        indexes[table]=index
    rows=[]
    for suggestion in state['Suggestions']:
        pair=key(suggestion);sku,location=pair
        keys=dict(DBMMaster=pair,NormAcceptanceTbl=pair,SKUDescriptionTbl=sku,
            SiteDescriptionTbl=location,ReasonCodes=suggestion['Type'],SkuAttributeData=sku,
            SkuLocAttributeData=pair,LocationAttributeData=location)
        subject={table:indexes[table].get(value,[]) for table,value in keys.items()}
        rows.extend(dbm_rows({**subject,'Suggestions':[suggestion]},predicate=predicate))
    rows.sort(key=lambda r:(r['SKUCode'],r['LocCode']))
    return [dict(row,RN=i) for i,row in enumerate(rows,1)]


def verify(run):
    # Full source and target checksums were verified by the bounded loader.
    # Startup binds that exact finalized roster; requests verify selected rows.
    _,before=binding()
    from mta.presentation.selective import image_rows
    image_rows(run,'closing/dbm/LastBatchRunTbl')
    _,after=binding()
    if before!=after:unavailable('changed_during_admission')
