"""Bounded RRR diagnostics against the sealed VM fixture, without serving."""
import argparse
import json
import os
from pathlib import Path
import time

from tools.stage2_vm_load import DATA,DB
from tools.stage2_vm_contract import atomic


def main(mode,routes=None):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()
    from django.db import connection
    from mta.presentation.fixture import binding,policy
    from mta.presentation.rrr_sql import read_rrr
    if connection.settings_dict['NAME']!=DB:raise ValueError('Wrong isolated database')
    run,before=binding()
    actor=next(a for a in policy()['actors'] if 'broad' in a['email'])
    payload=dict(product_permissions=actor['products'],location_permissions=actor['locations'],
        paginationParameter=dict(pageNumber=1,recordsPerPage=5))
    plans=[]
    def capture(execute,sql,params,many,context):
        if sql.startswith('WITH positions') or sql.startswith('WITH R AS') or (mode=='btr-plan' and sql.startswith('WITH ')):
            execute('EXPLAIN (FORMAT JSON) '+sql,params,many,context)
            plan=context['cursor'].fetchone()[0]
            plans.append(dict(kind='position_guard' if sql.startswith('WITH positions') else 'consumer',
                query=sql,parameters=[str(v) if not isinstance(v,(str,int,float,type(None),bool)) else v for v in params],plan=plan))
            return execute('SELECT 0 WHERE FALSE' if sql.startswith('WITH positions') or mode=='btr-plan' else 'SELECT 0',[],False,context)
        return execute(sql,params,many,context)
    start=time.monotonic()
    if mode in ('plan','btr-plan'):
        with connection.execute_wrapper(capture):
            if mode=='plan':read_rrr(run,payload,paging=(1,5),count=True)
            else:
                from mta.presentation.btr_sql import read_btr
                read_btr(run,{**payload,'name':'tech'},paging=(1,5))
        result=dict(mode=mode,plans=plans)
    elif mode=='measure':
        with connection.cursor() as cur:cur.execute("SET statement_timeout='55000ms'")
        outcomes=[]
        for count in (True,False):
            started=time.monotonic()
            try:
                value=read_rrr(run,payload,paging=(1,5),count=count)
                outcomes.append(dict(count=count,status='PASS',seconds=time.monotonic()-started,value=value))
            except Exception as exc:
                outcomes.append(dict(count=count,status='FAILED',seconds=time.monotonic()-started,error=str(exc)))
        result=dict(mode=mode,outcomes=outcomes)
    else:
        from django.test import Client,override_settings
        client=Client();outcomes=[]
        with connection.cursor() as cur:cur.execute("SET statement_timeout='55000ms'")
        for route in routes or ('GetBPRDataCount','GetBPRData','GetBTRDataCount','GetBTRData','DBMDataCount','DBMData'):
            started=time.monotonic()
            try:
                with override_settings(ALLOWED_HOSTS=['testserver']):
                    response=client.post('/api/mta/'+route,json.dumps(payload),content_type='application/json',
                        HTTP_X_VECTORFLOW_IDENTITY=json.dumps(dict(id=actor['id'],email=actor['email'])))
                if response.status_code in (401,403):raise RuntimeError('Security failure: '+route)
                value=response.json()
                outcomes.append(dict(route=route,status=response.status_code,seconds=time.monotonic()-started,value=value))
            except RuntimeError:raise
            except Exception as exc:
                outcomes.append(dict(route=route,status='FAILED',seconds=time.monotonic()-started,error=str(exc)))
            if binding()[1]!=before:raise ValueError('Fixture identity changed during page diagnostic')
            print(route,outcomes[-1]['status'],round(outcomes[-1]['seconds'],3),flush=True)
        result=dict(mode=mode,outcomes=outcomes)
    if binding()[1]!=before:raise ValueError('Fixture identity changed during probe')
    result.update(run_id=str(run.pk),business_date=str(run.business_date),seconds=time.monotonic()-start)
    atomic(DATA/('rrr-'+mode+'.json'),json.loads(json.dumps(result,default=str)))
    summary={k:v for k,v in result.items() if k not in ('plans','outcomes')}
    summary['outcomes']=[{k:(len(v) if isinstance(v,(list,dict)) else v) for k,v in item.items()} for item in result.get('outcomes',[])]
    print(json.dumps(summary,default=str))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['plan','measure','pages','btr-plan'])
    parser.add_argument('--routes',nargs='+');args=parser.parse_args();main(args.mode,args.routes)
