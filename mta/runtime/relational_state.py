"""Typed, run-owned relational state. No business calculation or trace storage.

The catalogue maps existing state families to canonical SQL table columns.
Image/ordinal keys preserve independent owners and duplicate rows; they never
invent a business key or allocation priority. Small manifests contain shape,
column wire types and checksums only, not operational row values.
"""
from datetime import date, datetime
from decimal import Decimal
import hashlib
import os
import json
from pathlib import Path
import re
from itertools import islice

from django.db import connection
from mta.serialization import digest, storage, rows_digest, canonical_parts
from mta.row_sequences import RecordRows
from mta.application.stage_observation import stage, summary

CATALOG=json.loads((Path(__file__).resolve().parents[2]/'mta/config/production_state_schema_v1.json').read_text())
if digest(CATALOG)!='84f01ea82866a3898dd134eafac32bca4e35daa193aca9d55da4716074b1e512':
    raise ValueError('Pinned relational storage schema differs')
REPORT_STAGES=frozenset(('norm1-advisory','norm-change-export','norm-change-history',
                        'norm0-export','norm0-60-export','norm0-90-export',
                        'norm1-export','norm2-export','controls'))
PG_TYPES={'int':'bigint','bigint':'bigint','bit':'boolean','date':'date',
    'datetime':'timestamp without time zone','datetimetz':'timestamp with time zone','decimal':'numeric','numeric':'numeric',
    'float':'double precision','real':'double precision',
    'nchar':'text','nvarchar':'text','varchar':'text','xml':'text'}
from mta.runtime.input_tables import TABLES as INPUT_TABLES
from mta.runtime.complete_daily_state import TABLES as COMPLETE_TABLES, BINDINGS as COMPLETE_BINDINGS
from mta.runtime.dbm_phase_storage import TABLES as PHASE_TABLES, BINDINGS as PHASE_BINDINGS, STAGES as PHASE_STAGES, TABLE as PHASE_TABLE
from mta.runtime.btr_history_storage import TABLES as BTR_TABLES, BINDINGS as BTR_BINDINGS, TABLE as BTR_TABLE
from mta.runtime.production_report_storage import TABLES as PRODUCTION_REPORT_TABLES
STORAGE_TABLES = {**CATALOG['tables'], **INPUT_TABLES, **COMPLETE_TABLES, **PHASE_TABLES, **BTR_TABLES, **PRODUCTION_REPORT_TABLES}
REPORT_STAGES = REPORT_STAGES | frozenset(PHASE_STAGES)


def quote(name):return '"'+name.replace('"','""')+'"'


def table_name(key):
    name=re.sub('[^a-z0-9_]','_',key.lower())
    return name if len(name)<=55 else name[:46]+'_'+hashlib.sha256(key.encode()).hexdigest()[:8]


def table_sql(key):return 'mta_state.'+quote(table_name(key))


def schema_statements():
    statements=['CREATE SCHEMA mta_state']
    for key,columns in sorted(CATALOG['tables'].items()):
        fields=', '.join(quote(n)+' '+PG_TYPES[t] for n,t in columns)
        statements.append('CREATE TABLE '+table_sql(key)+' (vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT, '
            'vf_image text NOT NULL, vf_ordinal bigint NOT NULL, '+fields+', PRIMARY KEY(vf_run_id,vf_image,vf_ordinal))')
    statements.append('CREATE TABLE mta_state.report_export_cell (vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT, '
        'vf_image text NOT NULL, row_ordinal bigint NOT NULL, column_ordinal integer NOT NULL, '
        'value_type text NOT NULL, text_value text, integer_value bigint, real_value double precision, boolean_value boolean, '
        'PRIMARY KEY(vf_run_id,vf_image,row_ordinal,column_ordinal))')
    return statements


def wire_type(value):
    if isinstance(value, (Decimal, date, datetime)):return 'str'
    kind=type(value).__name__
    if kind not in ('str','int','float','bool'):raise ValueError('Non-scalar operational column '+kind)
    return kind


def db_value(value,kind):
    if value is None:return None
    if kind in ('decimal','numeric'):return Decimal(str(value))
    if kind in ('int','bigint'):
        if Decimal(str(value))!=int(value):raise ValueError('Fraction in canonical integer column')
        return int(value)
    if kind=='bit':
        if value not in (True,False,0,1):raise ValueError('Invalid canonical bit')
        return bool(value)
    if kind=='date':return date.fromisoformat(value) if isinstance(value,str) else value
    if kind in ('datetime','datetimetz'):return datetime.fromisoformat(value) if isinstance(value,str) else value
    if kind in ('float','real'):return float(value)
    return str(value)


def wire_value(value,kind):
    if value is None:return None
    if kind=='str':
        if isinstance(value,(date,datetime)):return value.isoformat()
        if isinstance(value,Decimal):return format(value,'f')
        return str(value)
    return {'int':int,'float':float,'bool':bool}[kind](value)


def bulk(sql,records):
    count=batches=0
    with connection.cursor() as cursor:
        iterator=iter(records)
        while batch:=list(islice(iterator,500)):
            cursor.executemany(sql,batch)
            count+=len(batch);batches+=1
    summary('typed_transport',rows=count,batches=batches)


def describe_rows(rows, columns, image):
    """One complete ordered pass; avoid one history scan per output column."""
    fields=list(rows[0]) if rows else []
    native=[];kinds={field:set() for field in fields}
    for field in fields:
        if field.casefold() not in columns:
            raise ValueError('Unmapped operational column '+image+'/'+field)
        native.append(columns[field.casefold()])
    checksum=hashlib.sha256(b'[');count=0;canonical_bytes=2
    for row in rows:
        if set(row)!=set(fields):raise ValueError('Mixed operational row shape: '+image)
        if count:checksum.update(b',');canonical_bytes+=1
        for part in canonical_parts(row):checksum.update(part);canonical_bytes+=len(part)
        for field in fields:
            if row[field] is not None:kinds[field].add(wire_type(row[field]))
            if len(kinds[field])>1:raise ValueError('Mixed wire types in operational column '+image+'/'+field)
        count+=1
    checksum.update(b']')
    if count!=len(rows):raise ValueError('Operational source population drift')
    metadata=dict(image=image,count=count,digest=checksum.hexdigest(),fields=[
        [field,name,next(iter(kinds[field]),'str')] for field,(name,_) in zip(fields,native)])
    summary('typed_image_shape',image=image,rows=count,columns=len(fields),canonical_bytes=canonical_bytes)
    return metadata,fields,native


def save_image(run,image,binding,rows, *, table=None):
    key=(table if table is not None else BTR_BINDINGS[binding] if binding in BTR_BINDINGS else PHASE_BINDINGS[binding] if binding in PHASE_BINDINGS else COMPLETE_BINDINGS[binding]
         if binding in COMPLETE_BINDINGS else '/'.join(CATALOG['bindings'][binding]))
    if key not in STORAGE_TABLES:raise ValueError('Unknown typed image table')
    from mta.runtime.complete_daily_state import validate_write
    validate_write(key,image,binding)
    if key == PHASE_TABLE:
        from mta.runtime.dbm_phase_storage import validate_write as validate_phase
        validate_phase(image, binding, rows)
    if key == BTR_TABLE:
        from mta.runtime.btr_history_storage import validate_write as validate_btr
        validate_btr(image,binding,rows)
    if key == 'BPR/ElephantOrders':
        from mta.domain.elephant_orders import validate as validate_elephants
        validate_elephants(list(rows))
    columns={name.casefold():(name,kind) for name,kind in STORAGE_TABLES[key]}
    with stage('typed_image_describe',image=image,rows=len(rows)):
        metadata,fields,native=describe_rows(rows,columns,image)
    metadata['table']=key
    if not rows:return metadata
    query='INSERT INTO '+table_sql(key)+' (vf_run_id,vf_image,vf_ordinal,'+','.join(quote(n) for n,_ in native)+') VALUES ('+','.join(['%s']*(len(native)+3))+')'
    records=((run.pk,image,index,*[db_value(row[field],kind) for field,(_,kind) in zip(fields,native)])
             for index,row in enumerate(rows))
    with stage('typed_image_insert',image=image,rows=len(rows)):
        if connection.vendor=='postgresql' and len(rows)>=500:
            # Same typed conversion, indexes, FK/statement/row guards and outer
            # transaction. COPY changes transport only; full readback is retained.
            columns=['vf_run_id','vf_image','vf_ordinal',*[name for name,_ in native]]
            copied=0
            with connection.wrap_database_errors,connection.cursor() as cursor:
                with cursor.copy('COPY '+table_sql(key)+' ('+','.join(quote(name) for name in columns)+') FROM STDIN') as writer:
                    for record in records:
                        writer.write_row(record);copied+=1
            summary('typed_transport',rows=copied,batches=1,transport='copy')
        else:
            bulk(query,records)
    return metadata


def iter_image(run,item):
    if item['table'] not in STORAGE_TABLES:raise ValueError('Unknown operational table')
    fields=item['fields']
    checksum=hashlib.sha256(b'[');count=0
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT vf_ordinal'+(' ,'+','.join(quote(n) for _,n,_ in fields) if fields else '')+
            ' FROM '+table_sql(item['table'])+' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal',
            [run.pk,item['image']])
        while records:=cursor.fetchmany(500):
            for record in records:
                if record[0]!=count:raise ValueError('Operational row count/order drift')
                row={f:wire_value(v,kind) for (f,_,kind),v in zip(fields,record[1:])}
                if count:checksum.update(b',')
                for part in canonical_parts(row):checksum.update(part)
                count+=1
                yield row
    checksum.update(b']')
    if count!=item['count'] or checksum.hexdigest()!=item['digest']:
        raise ValueError('Operational state value/type/multiplicity drift: '+item['image'])


def load_image(run,item):
    if item['count'] > 10000:
        if os.environ.get('VF_WORK_ROOT'):
            return RecordRows.from_rows(iter_image(run,item))
        # Serving roots are read-only. Certify the complete immutable typed
        # image before returning, then rescan without an application spool.
        # Installer/daily workers use the existing writable disk cache above.
        for _ in iter_image(run,item):pass
        return RecordRows(item['count'],lambda:iter_image(run,item))
    return list(iter_image(run,item))


def save_export(run,image,rows):
    def lengths():
        for ordinal,row in enumerate(rows):
            if set(row)!={'values'}:raise ValueError('Unexpected report export row shape')
            yield (run.pk,image,ordinal,len(row['values']))
    bulk('INSERT INTO mta_state.report_export_row VALUES (%s,%s,%s,%s)',lengths())
    def cells():
        for ordinal,row in enumerate(rows):
            for column,value in enumerate(row['values']):
                kind='null' if value is None else wire_type(value)
                values=[None,None,None,None]
                if kind!='null':values[('str','int','float','bool').index(kind)]=wire_value(value,kind)
                yield (run.pk,image,ordinal,column,kind,*values)
    bulk('INSERT INTO mta_state.report_export_cell VALUES ('+','.join(['%s']*9)+')',cells())
    return dict(version=2,image=image,count=len(rows),digest=rows_digest(rows))


def iter_export(run,item):
    checksum=hashlib.sha256(b'[');count=0
    with connection.chunked_cursor() as cursor:
        if item.get('version')==2:
            cursor.execute('SELECT r.row_ordinal,r.column_count,c.column_ordinal,c.value_type,'
                'c.text_value,c.integer_value,c.real_value,c.boolean_value '
                'FROM mta_state.report_export_row r LEFT JOIN mta_state.report_export_cell c '
                'ON c.vf_run_id=r.vf_run_id AND c.vf_image=r.vf_image AND c.row_ordinal=r.row_ordinal '
                'WHERE r.vf_run_id=%s AND r.vf_image=%s ORDER BY r.row_ordinal,c.column_ordinal',
                [run.pk,item['image']])
            def records():
                while batch:=cursor.fetchmany(500):yield from batch
            iterator=iter(records());pending=next(iterator,None)
            for ordinal in range(item['count']):
                if pending is None or pending[0]!=ordinal:raise ValueError('Report row population drift')
                size=pending[1];values=[]
                if size<0:raise ValueError('Report row length drift')
                for column in range(size):
                    if pending is None or pending[:3]!=(ordinal,size,column):raise ValueError('Report cell population drift')
                    kind,*typed=pending[3:]
                    selected=None if kind=='null' else ('str','int','float','bool').index(kind)
                    if any(v is not None for i,v in enumerate(typed) if i!=selected):
                        raise ValueError('Report cell typed columns conflict')
                    values.append(None if selected is None else typed[selected])
                    pending=next(iterator,None)
                if not size:
                    if any(v is not None for v in pending[2:]):raise ValueError('Empty report row has cells')
                    pending=next(iterator,None)
                row={'values':values}
                if count:checksum.update(b',')
                for part in canonical_parts(row):checksum.update(part)
                count+=1
                yield row
            if pending is not None:raise ValueError('Extra report rows')
    # A named server cursor owns one statement. Use a separate cursor for the
    # orphan check after the streamed export result has been exhausted.
    if item.get('version')==2:
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM mta_state.report_export_cell c WHERE c.vf_run_id=%s '
                'AND c.vf_image=%s AND NOT EXISTS (SELECT 1 FROM mta_state.report_export_row r '
                'WHERE r.vf_run_id=c.vf_run_id AND r.vf_image=c.vf_image AND r.row_ordinal=c.row_ordinal)',
                [run.pk,item['image']])
            if cursor.fetchone()[0]:raise ValueError('Orphan report cells')
    else:
        with connection.chunked_cursor() as cursor:
            # Accepted version-one receipts retain their original row-length manifest.
            cursor.execute('SELECT row_ordinal,column_ordinal,value_type,text_value,integer_value,real_value,boolean_value '
                'FROM mta_state.report_export_cell WHERE vf_run_id=%s AND vf_image=%s ORDER BY row_ordinal,column_ordinal',
                [run.pk,item['image']])
            for ordinal,size in enumerate(item['lengths']):
                values=[]
                for column in range(size):
                    record=cursor.fetchone()
                    if record is None or record[:2]!=(ordinal,column):raise ValueError('Report cell population drift')
                    kind,*typed=record[2:]
                    selected=None if kind=='null' else ('str','int','float','bool').index(kind)
                    if any(v is not None for i,v in enumerate(typed) if i!=selected):raise ValueError('Report cell typed columns conflict')
                    values.append(None if selected is None else typed[selected])
                row={'values':values}
                if count:checksum.update(b',')
                for part in canonical_parts(row):checksum.update(part)
                count+=1
                yield row
            if cursor.fetchone() is not None:raise ValueError('Extra report cells')
    checksum.update(b']')
    if checksum.hexdigest()!=item['digest']:raise ValueError('Report projection drift')


def load_export(run,item):
    if item['count'] > 10000:
        # Export rows contain nested variable-width cells and cannot use the
        # flat RecordRows spool. Reiterate the fully checked typed relation.
        for _ in iter_export(run,item):
            pass
        return RecordRows(item['count'], lambda: iter_export(run,item))
    return list(iter_export(run,item))


def save_daily(run,output):
    closing=output['ClosingState'][0]
    images={};template={}
    def image(path,binding,rows):
        images[path]=save_image(run,path,binding,rows)
        return {'image':path}
    for section,state in closing.items():
        if section=='publication_context':
            template[section]={'metadata':state}
        elif section=='importer_settings':
            template[section]=image('closing/importer_settings','closing/importer_settings',state)
        else:
            tables={}
            for name,rows in state.items():
                path='closing/'+section+'/'+name
                if name=='IntermediateTables':
                    records=rows.items() if isinstance(rows,dict) else ((r['table'],r['rows']) for r in rows)
                    tables[name]={'scratch_kind':'dict' if isinstance(rows,dict) else 'list','items':[
                        [table,image(path+'/'+table,'scratch/'+table,values)] for table,values in records]}
                else:tables[name]=image(path,path,rows)
            template[section]={'tables':tables}
    reports=[]
    seen_reports=set()
    for stage in output.get('Reports',[]):
        if stage['stage'] not in REPORT_STAGES:continue
        if stage['stage'] in seen_reports:raise ValueError('Duplicate owned report family')
        seen_reports.add(stage['stage'])
        tables={}
        for name,rows in stage['tables'].items():
            path='reports/'+stage['stage']+'/'+name
            if name in ('ReportHeader','ReportRows'):
                tables[name]={'export':save_export(run,path,rows)}
            else:
                # New horizons reuse the same typed columns, with separate
                # run/image/ordinal ownership. The pinned catalogue is unchanged.
                binding_stage='norm0-export' if stage['stage'] in ('norm0-60-export','norm0-90-export') else stage['stage']
                tables[name]=image(path,'reports/'+binding_stage+'/'+name,rows)
        report=dict(stage=stage['stage'],tables=tables)
        if 'deferred' in stage:
            report['deferred']=stage['deferred']
            report['sources']={name:image('report-facts/'+stage['stage']+'/'+name,'closing/dbm/'+name,rows)
                for name,rows in stage['sources'].items()}
        reports.append(report)
    bpr={name:image('reports/bpr/'+name,'reports/bpr/'+name,output['BPRFinal'][0][name])
         for name in ('BPR_Table','vf_RationedReqReport')} if output.get('BPRFinal') else {}
    manifest=dict(version=1,closing=template,images=images,reports=reports,bpr=bpr,
        lineage=output['Lineage'],publication=output.get('PublicationContext',[]))
    if len(json.dumps(manifest))>1024*1024:raise ValueError('Operational metadata exceeds bounded manifest size')
    return manifest


def read_daily(run, *, include_reports=True):
    manifest=run.production_manifest
    def resolve(node):
        if 'image' in node:return load_image(run,manifest['images'][node['image']])
        if 'metadata' in node:return node['metadata']
        if 'export' in node:return load_export(run,node['export'])
        if 'scratch_kind' in node:
            records=[(n,resolve(v)) for n,v in node['items']]
            return dict(records) if node['scratch_kind']=='dict' else [{'table':n,'rows':v} for n,v in records]
        return {name:resolve(value) for name,value in node['tables'].items()}
    closing={section:resolve(state) for section,state in manifest['closing'].items()}
    reports=[]
    if include_reports:
        for row in manifest['reports']:
            report=dict(stage=row['stage'],tables={n:resolve(v) for n,v in row['tables'].items()})
            if 'deferred' in row:
                report.update(deferred=row['deferred'],sources={n:resolve(v) for n,v in row['sources'].items()})
            reports.append(report)
    result=dict(ClosingState=[closing],DBMFinal=[closing['dbm']],Reports=reports,
        BPRReports=[{n:resolve(v) for n,v in manifest['bpr'].items()}] if include_reports else [],
        Lineage=manifest['lineage'],PublicationContext=manifest['publication'])
    if 'btr' in closing:result['BTRFinal']=[closing['btr']]
    return result


def production_projection(output):
    closing=output['ClosingState'][0]
    result=dict(ClosingState=[closing],DBMFinal=[closing['dbm']],
        Reports=[r for r in output.get('Reports',[]) if r['stage'] in REPORT_STAGES],
        BPRReports=[{n:output['BPRFinal'][0][n] for n in ('BPR_Table','vf_RationedReqReport')}
                    if output.get('BPRFinal') else {}],
        Lineage=output['Lineage'],PublicationContext=output.get('PublicationContext',[]))
    if 'btr' in closing:result['BTRFinal']=[closing['btr']]
    return result
