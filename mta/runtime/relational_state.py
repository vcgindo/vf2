"""Typed, run-owned relational state. No business calculation or trace storage.

The catalogue maps existing state families to canonical SQL table columns.
Image/ordinal keys preserve independent owners and duplicate rows; they never
invent a business key or allocation priority. Small manifests contain shape,
column wire types and checksums only, not operational row values.
"""
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from django.db import connection
from mta.serialization import digest, storage

CATALOG=json.loads((Path(__file__).resolve().parents[2]/'baseline/production-state-schema.json').read_text())
if digest(CATALOG)!='89201eca8c797bcd70a9f87d9dce31cc2be27636eccc0f6cee027a8bcf09d7aa':
    raise ValueError('Pinned relational storage schema differs')
REPORT_STAGES=frozenset(('norm1-advisory','norm-change-export','norm-change-history',
                        'norm0-export','norm1-export','norm2-export','controls'))
PG_TYPES={'int':'bigint','bigint':'bigint','bit':'boolean','date':'date',
    'datetime':'timestamp without time zone','decimal':'numeric','numeric':'numeric',
    'float':'double precision','real':'double precision',
    'nchar':'text','nvarchar':'text','varchar':'text','xml':'text'}


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
    if kind=='date':return date.fromisoformat(value)
    if kind=='datetime':return datetime.fromisoformat(value)
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
    with connection.cursor() as cursor:
        for start in range(0,len(records),500):cursor.executemany(sql,records[start:start+500])


def save_image(run,image,binding,rows):
    key='/'.join(CATALOG['bindings'][binding])
    metadata=dict(image=image,table=key,count=len(rows),digest=digest(rows),fields=[])
    if not rows:return metadata
    fields=list(rows[0])
    if any(set(row)!=set(fields) for row in rows):raise ValueError('Mixed operational row shape: '+image)
    columns={name.casefold():(name,kind) for name,kind in CATALOG['tables'][key]}
    native=[]
    for field in fields:
        if field.casefold() not in columns:raise ValueError('Unmapped operational column '+image+'/'+field)
        name,kind=columns[field.casefold()]
        types={wire_type(row[field]) for row in rows if row[field] is not None}
        if len(types)>1:raise ValueError('Mixed wire types in operational column '+image+'/'+field)
        metadata['fields'].append([field,name,next(iter(types),'str')])
        native.append((name,kind))
    query='INSERT INTO '+table_sql(key)+' (vf_run_id,vf_image,vf_ordinal,'+','.join(quote(n) for n,_ in native)+') VALUES ('+','.join(['%s']*(len(native)+3))+')'
    records=[(run.pk,image,index,*[db_value(row[field],kind) for field,(_,kind) in zip(fields,native)])
             for index,row in enumerate(rows)]
    bulk(query,records)
    return metadata


def load_image(run,item):
    if item['table'] not in CATALOG['tables']:raise ValueError('Unknown operational table')
    fields=item['fields']
    with connection.cursor() as cursor:
        cursor.execute('SELECT vf_ordinal'+(' ,'+','.join(quote(n) for _,n,_ in fields) if fields else '')+
            ' FROM '+table_sql(item['table'])+' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal',
            [run.pk,item['image']])
        records=cursor.fetchall()
    if [r[0] for r in records]!=list(range(item['count'])):raise ValueError('Operational row count/order drift')
    rows=[{f:wire_value(v,kind) for (f,_,kind),v in zip(fields,r[1:])} for r in records]
    if digest(rows)!=item['digest']:raise ValueError('Operational state value/type/multiplicity drift: '+item['image'])
    return rows


def save_export(run,image,rows):
    records=[];lengths=[]
    for ordinal,row in enumerate(rows):
        if set(row)!={'values'}:raise ValueError('Unexpected report export row shape')
        lengths.append(len(row['values']))
        for column,value in enumerate(row['values']):
            kind='null' if value is None else wire_type(value)
            values=[None,None,None,None]
            if kind!='null':values[('str','int','float','bool').index(kind)]=value
            records.append((run.pk,image,ordinal,column,kind,*values))
    bulk('INSERT INTO mta_state.report_export_cell VALUES ('+','.join(['%s']*9)+')',records)
    return dict(image=image,lengths=lengths,digest=digest(rows))


def load_export(run,item):
    rows=[{'values':[None]*size} for size in item['lengths']]
    expected={(i,j) for i,size in enumerate(item['lengths']) for j in range(size)}
    with connection.cursor() as cursor:
        cursor.execute('SELECT row_ordinal,column_ordinal,value_type,text_value,integer_value,real_value,boolean_value '
            'FROM mta_state.report_export_cell WHERE vf_run_id=%s AND vf_image=%s ORDER BY row_ordinal,column_ordinal',
            [run.pk,item['image']])
        for ordinal,column,kind,*values in cursor.fetchall():
            if (ordinal,column) not in expected:raise ValueError('Report cell population drift')
            expected.remove((ordinal,column))
            selected=None if kind=='null' else ('str','int','float','bool').index(kind)
            if any(v is not None for i,v in enumerate(values) if i!=selected):raise ValueError('Report cell typed columns conflict')
            rows[ordinal]['values'][column]=None if selected is None else values[selected]
    if expected or digest(rows)!=item['digest']:raise ValueError('Report projection drift')
    return rows


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
    for stage in output.get('Reports',[]):
        if stage['stage'] not in REPORT_STAGES:continue
        tables={}
        for name,rows in stage['tables'].items():
            path='reports/'+stage['stage']+'/'+name
            if name in ('ReportHeader','ReportRows'):
                tables[name]={'export':save_export(run,path,rows)}
            else:tables[name]=image(path,path,rows)
        reports.append(dict(stage=stage['stage'],tables=tables))
    bpr={name:image('reports/bpr/'+name,'reports/bpr/'+name,output['BPRFinal'][0][name])
         for name in ('BPR_Table','vf_RationedReqReport')} if output.get('BPRFinal') else {}
    manifest=dict(version=1,closing=template,images=images,reports=reports,bpr=bpr,
        lineage=output['Lineage'],publication=output.get('PublicationContext',[]))
    if len(json.dumps(manifest))>1024*1024:raise ValueError('Operational metadata exceeds bounded manifest size')
    return manifest


def read_daily(run):
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
    result=dict(ClosingState=[closing],DBMFinal=[closing['dbm']],
        Reports=[dict(stage=r['stage'],tables={n:resolve(v) for n,v in r['tables'].items()}) for r in manifest['reports']],
        BPRReports=[{n:resolve(v) for n,v in manifest['bpr'].items()}],
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
