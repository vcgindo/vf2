"""One-time bulk loader into a fixed owned database; no engine/auth/service writes."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import date, datetime
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = Path(os.environ.get('VF_STAGE2_DATA', '/dataset'))
DB = 'test_freshvcf_stage2_dataset_20261003_001'
IDENTITY = 'stage2-shared-dataset-20261003-001'


def quote(name): return '"' + name.replace('"', '""') + '"'


def pg_type(column):
    kind = column['type']
    if kind in ('decimal', 'numeric'): return f'numeric({column["precision"]},{column["scale"]})'
    return {'int':'integer','bigint':'bigint','bit':'boolean','float':'double precision',
        'real':'double precision','date':'date','datetime':'timestamp without time zone',
        'datetime2':'text','nchar':'text','nvarchar':'text','varchar':'text','xml':'text'}[kind]


def value(v, column):
    if v is None: return None
    kind = column['type']
    if kind in ('decimal','numeric'): return Decimal(v)
    if kind == 'date': return date.fromisoformat(v)
    if kind == 'datetime': return datetime.fromisoformat(v)
    return v


def encoded(row):
    def scalar(v):
        if isinstance(v, Decimal): return str(v)
        if isinstance(v, (date, datetime)): return v.isoformat()
        return v
    return (json.dumps([scalar(v) for v in row],ensure_ascii=False,separators=(',', ':'),allow_nan=False)+'\n').encode()


def main():
    from tools.stage2_dataset import require_reconciled_source
    require_reconciled_source()
    import psycopg
    manifest_raw = (DATA / 'dataset-manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest['identity'] != IDENTITY or len(manifest['sources']) != 8: raise ValueError('Unexpected dataset')
    config = dict(host='postgres',user='freshvcf',password=os.environ['VF_DB_PASSWORD'])
    with psycopg.connect(dbname='postgres',autocommit=True,**config) as admin:
        exists = admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DB,)).fetchone()
        if not exists:
            admin.execute('CREATE DATABASE ' + quote(DB))
    with psycopg.connect(dbname=DB,**config) as pg:
        with pg.transaction():
            pg.execute('CREATE SCHEMA IF NOT EXISTS stage2_owner')
            pg.execute('CREATE TABLE IF NOT EXISTS stage2_owner.identity (identity text PRIMARY KEY, manifest_sha256 text NOT NULL)')
            identity = pg.execute('SELECT identity,manifest_sha256 FROM stage2_owner.identity').fetchall()
            expected = [(IDENTITY,hashlib.sha256(manifest_raw).hexdigest())]
            if identity:
                if identity != expected: raise ValueError('Existing database ownership or input differs')
            else:
                if pg.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema','stage2_owner')").fetchone()[0]:
                    raise ValueError('Refuse existing unowned database')
                pg.execute('INSERT INTO stage2_owner.identity VALUES (%s,%s)',expected[0])
        receipts = []
        for source in manifest['sources']:
            schema = 'stage_' + source['source'].lower()
            for table in source['tables']:
                if 'exclusion' in table: continue
                path = DATA / table['file']
                if hashlib.sha256(path.read_bytes()).hexdigest() != table['sha256']: raise ValueError('Export file drift')
                target = quote(schema)+'.'+quote(table['schema_name']+'__'+table['table_name'])
                with pg.transaction():
                    pg.execute('CREATE SCHEMA IF NOT EXISTS '+quote(schema))
                    exists = pg.execute('SELECT to_regclass(%s)',(target,)).fetchone()[0]
                    if not exists:
                        pg.execute('CREATE TABLE '+target+' (vf_source_ordinal bigint PRIMARY KEY,'+','.join(quote(c['name'])+' '+pg_type(c) for c in table['columns'])+')')
                        with pg.cursor().copy('COPY '+target+' FROM STDIN') as copy, gzip.open(path,'rt',encoding='utf-8') as f:
                            for i,line in enumerate(f):
                                row=json.loads(line)
                                copy.write_row([i]+[value(v,c) for v,c in zip(row,table['columns'])])
                    h=hashlib.sha256();count=0;nulls=[0]*len(table['columns'])
                    with pg.cursor(name='readback') as cur:
                        cur.execute('SELECT * FROM '+target+' ORDER BY vf_source_ordinal')
                        for row in cur:
                            if row[0]!=count: raise ValueError('Ordinal drift')
                            h.update(encoded(row[1:]));count+=1
                            nulls=[n+(v is None) for n,v in zip(nulls,row[1:])]
                    if (count,h.hexdigest(),nulls)!=(table['count'],table['values_sha256'],table['null_counts']):
                        raise ValueError('Complete staging readback differs: '+target)
                    receipts.append(dict(source=source['source'],table=table['table_name'],count=count,values_sha256=h.hexdigest(),null_counts=nulls,status='PASS'))
            print('Verified staging',source['source'],flush=True)
        (DATA/'staging-validation.json').write_text(json.dumps(dict(identity=IDENTITY,tables=receipts,status='PASS'),indent=2))


if __name__=='__main__': main()
