"""Streaming, partial-source copy into the actual consumer schema; never served.

No calculation, producer function, accepted-run record or authentication change.
Absent sources/columns remain explicit gaps. Each image is atomic and read back.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
import argparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stage2_vm_load import DATA,DB,IDENTITY,quote
from tools.stage2_consumer_load import PREFIXES,PROJECTIONS,RENAMES
from tools.stage2_vm_dataset import selected_tables
from tools.stage2_vm_contract import sealed,atomic
from tools.stage2_dataset_load import encoded

RUN=uuid.UUID('bfd75b4b-a9df-4a08-82d3-852e3324b623')


def main(*,verify_binding=None):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()
    from django.db import connection,transaction
    from mta.runtime import models
    from mta.runtime.relational_state import CATALOG,table_sql,wire_value
    from mta.serialization import storage,digest
    if connection.settings_dict['NAME']!=DB:raise ValueError('Wrong isolated database')
    manifest,manifest_sha=sealed(DATA)
    if manifest['identity']!=IDENTITY:raise ValueError('Wrong dataset')
    staging=json.loads((DATA/'staging-validation.json').read_text())
    if staging['status']!='STAGING_VERIFIED' or staging['identity']!=IDENTITY or staging['manifest_sha256']!=manifest_sha:raise ValueError('Final staging proof required')
    tables={(s['source'].removeprefix('Demo_').removesuffix('_1'),t['table_name'].casefold()):(s,t)
        for s in manifest['sources'] for t in s['tables'] if 'file' in t}
    dates={r['LastRunDate'][:10] for s in manifest['sources'] for r in (s.get('last_batch') or [])}
    if len(dates)!=1:raise ValueError('Inconsistent source dates')
    mapping=dict(identity=IDENTITY,manifest_sha256=manifest_sha,run_id=str(RUN),status='IN_PROGRESS',images=[],projections=[],gaps=[])
    payload=dict(origin='human-supplied-original-vm-backups',dataset=IDENTITY,manifest_sha256=manifest_sha)
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute('SELECT identity FROM stage2_owner.identity')
            if cur.fetchall()!=[(IDENTITY,)]:raise ValueError('Wrong staging owner')
            cur.execute('SELECT manifest_sha256 FROM stage2_owner.manifest')
            if cur.fetchall()!=[(manifest_sha,)]:raise ValueError('Staging manifest differs')
            expected={(s['source'],t['table_name']):(t['sha256'],t['values_sha256'],t['count']) for s,t in tables.values()}
            cur.execute('SELECT * FROM stage2_owner.tables')
            if {(s,n):(f,v,c) for s,n,f,v,c in cur.fetchall()}!=expected:raise ValueError('Staging ledger roster differs')
            cur.execute('CREATE TABLE IF NOT EXISTS stage2_owner.consumer_receipts (binding text PRIMARY KEY,metadata jsonb NOT NULL)')
        run,created=models.CalculationRun.objects.get_or_create(id=RUN,defaults=dict(kind='LEGACY_UI_FIXTURE',
            status='FIXTURE_BLOCKED',input_payload=payload,input_digest=digest(payload),
            execution_revision='stage2-vm-source-copy-v1',business_date=next(iter(dates))))
        if (run.kind,run.status,run.input_payload)!=('LEGACY_UI_FIXTURE','FIXTURE_BLOCKED',payload):raise ValueError('Fixture identity differs')
        if run.input_digest!=digest(payload) or str(run.business_date)!=next(iter(dates)) or run.execution_revision!='stage2-vm-source-copy-v1':raise ValueError('Fixture identity fields differ')
        if models.CalculationRun.objects.exclude(pk=RUN).exists():raise ValueError('Unrelated runs in fixture database')
        if (run.checkpoints.exists() or run.commands.exists() or run.parity_summary or run.production_manifest or run.output_digest or run.production_digest or run.output_roster or run.failure or run.opening_key or run.predecessor_id or run.completed_at):raise ValueError('Fixture falsely claims engine state')

    def source(role,name):
        s,t=tables[(role,name.casefold())]
        return t,quote('stage_'+s['source'].lower())+'.'+quote(t['schema_name']+'__'+t['table_name'])

    def provenance(role,name):
        s,t=tables[(role,name.casefold())]
        return dict(manifest_sha256=manifest_sha,source=s['source'],schema=t['schema_name'],table=t['table_name'],backup_sha256=s['backup_sha256'],file_sha256=t['sha256'],values_sha256=t['values_sha256'])

    def source_proof(role,name,src):
        s,t=tables[(role,name.casefold())]
        with connection.cursor() as cur:
            cur.execute('LOCK TABLE '+src+' IN SHARE MODE')
            cur.execute('SELECT file_sha256,values_sha256,row_count FROM stage2_owner.tables WHERE source=%s AND table_name=%s',[s['source'],t['table_name']])
            if cur.fetchone()!=(t['sha256'],t['values_sha256'],t['count']):raise ValueError('Staging ledger differs')

    def checksum(query,params,fields,wire,raw_table=None,source_fields=None):
        h=hashlib.sha256(b'[');count=0
        raw_hash=hashlib.sha256();nulls=[0]*len(raw_table['columns']) if raw_table else []
        indices=([next(i for i,c in enumerate(raw_table['columns']) if c['name'].casefold()==n.casefold()) for n in source_fields] if raw_table else None)
        # Named psycopg cursor limits memory even for multi-million-row history.
        with connection.connection.cursor(name='stage2_image_readback') as cur:
            cur.itersize=1000;cur.execute(query,params)
            for record in cur:
                if record[0]!=count:raise ValueError('Noncontiguous consumer ordinal')
                values=record[1:]
                if raw_table:
                    raw_hash.update(encoded(values))
                    for i,v in enumerate(values):
                        if v is None:nulls[i]+=1
                    values=[values[i] for i in indices]
                row={name:wire_value(v,kind) for name,kind,v in zip(fields,wire,values)}
                if count:h.update(b',')
                h.update(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
                count+=1
                if count%1000000==0:print('Consumer readback progress',count,flush=True)
        if raw_table and (count,raw_hash.hexdigest(),nulls)!=(raw_table['count'],raw_table['values_sha256'],raw_table['null_counts']):raise ValueError('Staging rows differ from frozen manifest')
        h.update(b']');return count,h.hexdigest()

    for path,(role,name) in CATALOG['bindings'].items():
        if verify_binding and path!=verify_binding:continue
        if not path.startswith(PREFIXES):continue
        if (role,name.casefold()) not in selected_tables():continue
        if (role,name.casefold()) not in tables:
            mapping['gaps'].append(dict(binding=path,reason='source_not_supplied_or_not_exported'));continue
        t,src=source(role,name)
        columns={c['name'].casefold():c for c in t['columns']}
        target_columns=CATALOG['tables'][role+'/'+name]
        missing=[n for n,k in target_columns if n.casefold() not in columns]
        if missing:
            mapping['gaps'].append(dict(binding=path,reason='source_columns_absent',columns=missing));continue
        fields=[n for n,k in target_columns]
        source_columns=[columns[n.casefold()] for n in fields]
        wire=[{'int':'int','bigint':'int','bit':'bool','float':'float','real':'float'}.get(c['type'],'str') for c in source_columns]
        cols=','.join(quote(n) for n in fields)
        src_cols=','.join(quote(c['name']) for c in source_columns)
        with transaction.atomic():
            source_proof(role,name,src)
            with connection.cursor() as cur:
                cur.execute('SELECT metadata FROM stage2_owner.consumer_receipts WHERE binding=%s',[path]);prior=cur.fetchone()
                if prior and isinstance(prior[0],str):prior=(json.loads(prior[0]),)
                if verify_binding and not prior:raise ValueError('Retry verification requires an existing receipt')
                if not prior:
                    cur.execute('INSERT INTO '+table_sql(role+'/'+name)+' (vf_run_id,vf_image,vf_ordinal,'+cols+') SELECT %s,%s,vf_source_ordinal,'+src_cols+' FROM '+src,[RUN,path])
            expected=checksum('SELECT * FROM '+src+' ORDER BY vf_source_ordinal',[],fields,wire,t,[c['name'] for c in source_columns])
            actual=checksum('SELECT vf_ordinal,'+cols+' FROM '+table_sql(role+'/'+name)+' WHERE vf_run_id=%s AND vf_image=%s ORDER BY vf_ordinal',[RUN,path],fields,wire)
            if expected!=actual or actual[0]!=t['count']:raise ValueError('Mapped values/types/multiplicity differ: '+path)
            metadata=dict(image=path,table=role+'/'+name,count=actual[0],digest=actual[1],fields=[[n,n,k] for n,k in zip(fields,wire)],provenance=provenance(role,name))
            if prior and prior[0]!=metadata:raise ValueError('Existing image receipt differs')
            if not prior:
                with connection.cursor() as cur:cur.execute('INSERT INTO stage2_owner.consumer_receipts VALUES (%s,%s::jsonb)',[path,json.dumps(metadata)])
        mapping['images'].append(dict(binding=path,source='Demo_'+role+'_1.dbo.'+name,target=table_sql(role+'/'+name),
            columns=[dict(source=c['name'],target=n,wire=k) for c,n,k in zip(source_columns,fields,wire)],metadata=metadata,
            source_only_columns=[c['name'] for c in t['columns'] if c['name'].casefold() not in {n.casefold() for n in fields}]))
        if not verify_binding:atomic(DATA/'mapping.json',mapping)
        print('Verified existing' if verify_binding else 'Mapped',path,actual[0],flush=True)
    # Direct legacy report rows; no production provenance/producer receipts.
    for model_name,source_name in PROJECTIONS.items():
        if verify_binding and 'projection/'+model_name!=verify_binding:continue
        if ('BPR',source_name.casefold()) not in tables:
            mapping['gaps'].append(dict(projection=model_name,reason='source_absent'));continue
        model=getattr(models,model_name);t,src=source('BPR',source_name)
        fields=[f.name for f in model._meta.fields if f.name not in ('id','run','ordinal')]
        columns={c['name'].casefold():c for c in t['columns']}
        pairs=[(columns[RENAMES.get(n,n).casefold()],n) for n in fields]
        wire=[{'int':'int','bigint':'int','bit':'bool','float':'float','real':'float'}.get(c['type'],'str') for c,n in pairs]
        src_cols=','.join(quote(c['name']) for c,n in pairs);cols=','.join(quote(n) for n in fields)
        binding='projection/'+model_name
        with transaction.atomic():
            source_proof('BPR',source_name,src)
            with connection.cursor() as cur:
                cur.execute('SELECT metadata FROM stage2_owner.consumer_receipts WHERE binding=%s',[binding]);prior=cur.fetchone()
                if prior and isinstance(prior[0],str):prior=(json.loads(prior[0]),)
                if verify_binding and not prior:raise ValueError('Retry verification requires an existing receipt')
                if not prior:cur.execute('INSERT INTO '+quote(model._meta.db_table)+' (run_id,ordinal,'+cols+') SELECT %s,vf_source_ordinal,'+src_cols+' FROM '+src,[RUN])
            expected=checksum('SELECT * FROM '+src+' ORDER BY vf_source_ordinal',[],fields,wire,t,[c['name'] for c,n in pairs])
            actual=checksum('SELECT ordinal,'+cols+' FROM '+quote(model._meta.db_table)+' WHERE run_id=%s ORDER BY ordinal',[RUN],fields,wire)
            if actual!=expected:raise ValueError('Projection values differ: '+model_name)
            metadata=dict(model=model_name,count=actual[0],digest=actual[1],fields=fields,wire=wire,provenance=provenance('BPR',source_name))
            if prior and prior[0]!=metadata:raise ValueError('Projection receipt changed')
            if not prior:
                with connection.cursor() as cur:cur.execute('INSERT INTO stage2_owner.consumer_receipts VALUES (%s,%s::jsonb)',[binding,json.dumps(metadata)])
        mapping['projections'].append(dict(**metadata,source='Demo_BPR_1.dbo.'+source_name,
            target=model._meta.db_table,columns=[dict(source=c['name'],target=n) for c,n in pairs]))
        if not verify_binding:atomic(DATA/'mapping.json',mapping)
        print('Verified existing' if verify_binding else 'Mapped',model_name,actual[0],flush=True)
    if verify_binding:
        if len(mapping['images'])+len(mapping['projections'])!=1:raise ValueError('Unknown or unavailable verification binding')
        atomic(DATA/'consumer-retry-validation.json',dict(identity=IDENTITY,manifest_sha256=manifest_sha,binding=verify_binding,status='PASS',inserts=0,receipt=(mapping['images']+mapping['projections'])[0]))
        return
    mapped={i['source'].casefold() for i in mapping['images']+mapping['projections']}
    mapping['exports']=[dict(source=s['source']+'.'+t['schema_name']+'.'+t['table_name'],disposition='mapped' if (s['source']+'.'+t['schema_name']+'.'+t['table_name']).casefold() in mapped else 'staging_only',reason='Existing consumer binding' if (s['source']+'.'+t['schema_name']+'.'+t['table_name']).casefold() in mapped else 'Preserved native ancillary, configuration, permission evidence or additional history; no authorized serving adapter') for s,t in tables.values()]
    with connection.cursor() as cur:
        cur.execute('SELECT binding FROM stage2_owner.consumer_receipts')
        if {r[0] for r in cur.fetchall()}!={i['binding'] for i in mapping['images']}|{'projection/'+i['model'] for i in mapping['projections']}:raise ValueError('Consumer receipt roster differs')
    mapping['status']='CONSUMER_MAPPED_FIXTURE_BLOCKED'
    atomic(DATA/'mapping.json',mapping)
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute('SELECT binding,metadata FROM stage2_owner.consumer_receipts ORDER BY binding')
            receipts={k:json.loads(v) if isinstance(v,str) else v for k,v in cur.fetchall()}
            publication=dict(identity=IDENTITY,manifest_sha256=manifest_sha,run_id=str(RUN),status=mapping['status'],receipts_digest=digest(receipts),mapping_sha256=hashlib.sha256((DATA/'mapping.json').read_bytes()).hexdigest())
            cur.execute('CREATE TABLE IF NOT EXISTS stage2_owner.consumer_publication (identity text PRIMARY KEY, metadata jsonb NOT NULL)')
            cur.execute('SELECT metadata FROM stage2_owner.consumer_publication WHERE identity=%s',[IDENTITY]);prior=cur.fetchone()
            if prior:
                value=json.loads(prior[0]) if isinstance(prior[0],str) else prior[0]
                if value!=publication:raise ValueError('Final publication receipt changed')
            else:cur.execute('INSERT INTO stage2_owner.consumer_publication VALUES (%s,%s::jsonb)',[IDENTITY,json.dumps(publication)])
    atomic(DATA/'consumer-publication.json',publication)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-binding',help='Read back one existing binding with zero consumer inserts; preserve full mapping')
    main(verify_binding=parser.parse_args().verify_binding)
