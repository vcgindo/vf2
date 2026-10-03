"""Bulk COPY/readback of the available original VM Stage2 source union.

Fixed owned database, bounded streaming, no source fallback or serving mutation.
Each completed table is transactional and immutable on retry.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import argparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stage2_dataset_load import quote,pg_type,value,encoded
from tools.stage2_vm_dataset import sha
from tools.stage2_vm_contract import sealed,roster,bind,atomic

DATA=Path('/dataset')
DB='test_freshvcf_stage2_vm_20261003_002'
IDENTITY='stage2-vm-dataset-20261003-002'


def main(*,role=None,finalize=False):
    import psycopg
    manifest,manifest_sha=sealed(DATA)
    if manifest['identity']!=IDENTITY or manifest['origin']!='human-supplied-original-vm-backups':raise ValueError('Wrong source identity')
    config=dict(host='postgres',user='freshvcf',password=os.environ['VF_DB_PASSWORD'])
    with psycopg.connect(dbname='postgres',autocommit=True,**config) as admin:
        exists=admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DB,)).fetchone()
        if not exists:admin.execute('CREATE DATABASE '+quote(DB))
    with psycopg.connect(dbname=DB,**config) as pg:
        with pg.transaction():
            if exists and not pg.execute("SELECT to_regclass('stage2_owner.identity')").fetchone()[0]:raise ValueError('Existing DB lacks ownership')
            pg.execute('CREATE SCHEMA IF NOT EXISTS stage2_owner')
            pg.execute('CREATE TABLE IF NOT EXISTS stage2_owner.identity (identity text PRIMARY KEY)')
            owned=pg.execute('SELECT identity FROM stage2_owner.identity').fetchall()
            if owned and owned!=[(IDENTITY,)]:raise ValueError('Different owner')
            if not owned:pg.execute('INSERT INTO stage2_owner.identity VALUES (%s)',(IDENTITY,))
            bind(pg,manifest_sha)
            pg.execute('CREATE TABLE IF NOT EXISTS stage2_owner.sources (source text PRIMARY KEY, backup_sha256 text NOT NULL)')
            pg.execute('CREATE TABLE IF NOT EXISTS stage2_owner.tables (source text, table_name text, file_sha256 text, values_sha256 text, row_count bigint, PRIMARY KEY(source,table_name))')
            pg.execute("SET work_mem='16MB'")
        receipt_path=DATA/'staging-validation.json'
        receipts=json.loads(receipt_path.read_text())['tables'] if receipt_path.exists() else []
        if finalize:
            expected={(s['source'],t['table_name']):(t['sha256'],t['values_sha256'],t['count']) for s,t in roster(manifest).values()}
            actual={(s,n):(f,v,c) for s,n,f,v,c in pg.execute('SELECT * FROM stage2_owner.tables').fetchall()}
            if expected!=actual:raise ValueError('Exact staging ledger roster differs')
            by_key={(r['source'],r['table']):r for r in receipts}
            if set(by_key)!=set(expected):raise ValueError('External receipt roster differs')
            for s,t in roster(manifest).values():
                r=by_key[(s['source'],t['table_name'])]
                if (r['count'],r['values_sha256'],r['null_counts'],r['status'])!=(t['count'],t['values_sha256'],t['null_counts'],'PASS'):raise ValueError('External readback receipt differs')
                target=quote('stage_'+s['source'].lower())+'.'+quote(t['schema_name']+'__'+t['table_name'])
                pg.execute('LOCK TABLE '+target+' IN SHARE MODE')
                h=hashlib.sha256();count=0;nulls=[0]*len(t['columns'])
                with pg.cursor(name='final_readback') as cur:
                    cur.itersize=1000;cur.execute('SELECT * FROM '+target+' ORDER BY vf_source_ordinal')
                    for row in cur:
                        if row[0]!=count:raise ValueError('Final ordinal drift')
                        h.update(encoded(row[1:]));count+=1
                        for i,v in enumerate(row[1:]):
                            if v is None:nulls[i]+=1
                        if count%1000000==0:print('Final readback',s['source'],t['table_name'],count,flush=True)
                if (count,h.hexdigest(),nulls)!=(t['count'],t['values_sha256'],t['null_counts']):raise ValueError('Final full staging readback differs')
                r['schema']='dbo'
                print('Final verified',s['source'],t['table_name'],count,flush=True)
            atomic(receipt_path,dict(identity=IDENTITY,manifest_sha256=manifest_sha,status='STAGING_VERIFIED',missing_required_roles=manifest['missing_roles'],optional_roles_not_supplied=manifest.get('optional_roles_not_supplied',[]),tables=list(by_key.values())))
            print('Exact staging roster verified',len(expected),flush=True);return
        for source in manifest['sources']:
            if role and source['source']!='Demo_'+role+'_1':continue
            with pg.transaction():
                saved=pg.execute('SELECT backup_sha256 FROM stage2_owner.sources WHERE source=%s',(source['source'],)).fetchone()
                if saved and saved[0]!=source['backup_sha256']:raise ValueError('Source backup changed')
                if not saved:pg.execute('INSERT INTO stage2_owner.sources VALUES (%s,%s)',(source['source'],source['backup_sha256']))
            schema='stage_'+source['source'].lower()
            for table in source['tables']:
                if 'file' not in table:continue
                path=DATA/table['file']
                if sha(path)!=table['sha256']:raise ValueError('Frozen export drift')
                target=quote(schema)+'.'+quote(table['schema_name']+'__'+table['table_name'])
                with pg.transaction():
                    pg.execute('CREATE SCHEMA IF NOT EXISTS '+quote(schema))
                    existing=pg.execute('SELECT file_sha256,values_sha256,row_count FROM stage2_owner.tables WHERE source=%s AND table_name=%s',(source['source'],table['table_name'])).fetchone()
                    expected=(table['sha256'],table['values_sha256'],table['count'])
                    if existing and existing!=expected:raise ValueError('Table input changed')
                    if not existing:
                        pg.execute('CREATE TABLE '+target+' (vf_source_ordinal bigint PRIMARY KEY,'+','.join(quote(c['name'])+' '+pg_type(c) for c in table['columns'])+')')
                        with pg.cursor().copy('COPY '+target+' FROM STDIN') as copy,gzip.open(path,'rt',encoding='utf-8') as f:
                            for i,line in enumerate(f):
                                row=json.loads(line)
                                if len(row)!=len(table['columns']):raise ValueError('Source column count changed')
                                copy.write_row([i]+[value(v,c) for v,c in zip(row,table['columns'])])
                                if (i+1)%1000000==0:print('COPY progress',source['source'],table['table_name'],i+1,flush=True)
                    h=hashlib.sha256();count=0;nulls=[0]*len(table['columns'])
                    with pg.cursor(name='readback') as cur:
                        cur.itersize=1000;cur.execute('SELECT * FROM '+target+' ORDER BY vf_source_ordinal')
                        for row in cur:
                            if row[0]!=count:raise ValueError('Ordinal drift')
                            h.update(encoded(row[1:]));count+=1
                            for i,v in enumerate(row[1:]):
                                if v is None:nulls[i]+=1
                            if count%1000000==0:print('Readback progress',source['source'],table['table_name'],count,flush=True)
                    if (count,h.hexdigest(),nulls)!=(table['count'],table['values_sha256'],table['null_counts']):raise ValueError('Full typed readback mismatch: '+target)
                    if not existing:pg.execute('INSERT INTO stage2_owner.tables VALUES (%s,%s,%s,%s,%s)',(source['source'],table['table_name'],*expected))
                receipts=[r for r in receipts if (r['source'],r['table'])!=(source['source'],table['table_name'])]
                receipts.append(dict(source=source['source'],table=table['table_name'],count=count,values_sha256=h.hexdigest(),null_counts=nulls,status='PASS'))
                atomic(receipt_path,dict(identity=IDENTITY,manifest_sha256=manifest_sha,status='IN_PROGRESS',missing_required_roles=manifest['missing_roles'],optional_roles_not_supplied=manifest.get('optional_roles_not_supplied',[]),tables=receipts))
                print('Verified',source['source'],table['table_name'],count,flush=True)
        print('Available source staging verified; missing roles remain explicit',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=['Importer','BPR','BTR','DBM'])
    parser.add_argument('--finalize',action='store_true')
    args=parser.parse_args()
    main(role=args.role,finalize=args.finalize)
