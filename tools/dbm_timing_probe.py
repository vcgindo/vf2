"""One offline sample per engine; external DBM-only scalar instrumentation."""
import argparse
import cProfile
from collections import defaultdict
from copy import deepcopy
import functools
import hashlib
import json
import os
from pathlib import Path
import pstats
import sys
import time
import traceback

SHA = 'ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56'
OWNER = 'dbm-33733-001'
ROOT = Path('/app' if os.name != 'nt' else 'F:/freshvcf')
sys.path.insert(0, str(ROOT))


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def function_name(key):
    file, line, name = key
    return f'{file}:{line}:{name}'


class ModernProfile:
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.stages = []

    def wrap(self, function):
        @functools.wraps(function)
        def generate(*args, **kwargs):
            iterator = function(*args, **kwargs)
            while True:
                wall, cpu = time.perf_counter(), time.process_time()
                self.profiler.enable()
                finished = False
                try:
                    name, state = next(iterator)
                except StopIteration:
                    name, state, finished = 'generator-exhaustion', {}, True
                finally:
                    self.profiler.disable()
                    elapsed, used = time.perf_counter()-wall, time.process_time()-cpu
                self.stages.append(dict(stage=name, wall_seconds=elapsed,
                    cpu_seconds=used, calls=1,
                    cardinalities={n:len(v) for n,v in state.items() if isinstance(v,list)}))
                if finished:
                    return
                yield name, state
        return generate

    def result(self):
        rows = []
        stats=pstats.Stats(self.profiler).stats if self.profiler.getstats() else {}
        for key, (primitive, calls, own, cumulative, callers) in stats.items():
            rows.append(dict(function=function_name(key), primitive_calls=primitive,
                calls=calls, exclusive_seconds=own, inclusive_seconds=cumulative,
                callers={function_name(k):list(v) for k,v in callers.items()}))
        return dict(stages=self.stages, functions=sorted(rows,key=lambda r:-r['exclusive_seconds']),
            dbm_wall_seconds=sum(r['wall_seconds'] for r in self.stages),
            dbm_cpu_seconds=sum(r['cpu_seconds'] for r in self.stages),
            profiler_exclusive_seconds=sum(r['exclusive_seconds'] for r in rows),
            limitations='cProfile enabled only during selected_stages next(); overhead is not independently measured. Inclusive times overlap; sum exclusive times only.')


def modern(result):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()
    from django.core.management import call_command
    from django.db import connection
    from io import StringIO
    from mta.runtime.models import CalculationRun, MdmSource
    from mta.temporal import chain
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        assert cursor.fetchone()[0]=='daily_3006'
    assert os.environ['VF_DB_HOST']=='freshvcf-dbm33733-001-postgres'
    assert not CalculationRun.objects.exists(), 'Probe database must contain no calculation runs'
    source=MdmSource.objects.get(receipt__offline_owner=OWNER)
    assert source.receipt['artifact_sha256']==SHA
    profile=ModernProfile()
    original=chain.selected_stages
    chain.selected_stages=profile.wrap(original)
    try:
        output=StringIO()
        call_command('run_daily','/input/full-input.json',sha256=SHA,day_index=0,
            revision=OWNER,mdm_source=str(source.pk),mdm_source_digest=source.digest,
            bpr_remark_horizon=90,evidence_mode='production',stdout=output)
        result['run']=json.loads(output.getvalue())
    finally:
        chain.selected_stages=original
        result['dbm']=profile.result()


def legacy(result):
    from tools.offline_temporal_validation import bind_namespace
    isolation=bind_namespace(OWNER)
    from parity.adapters.legacy import temporal_day, temporal_delivery
    raw=Path('D:/freshvcf-build/synthetic/rlt-4-7-v1/scenario-004/full-input.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SHA
    case=json.loads(raw)['case']
    day={**deepcopy(case['days'][0]),**deepcopy(case['static_day'])}
    opening, opening_date, config=case['opening'],case['opening_date'],case['profile']
    assert day['business_date']=='2026-06-06'
    del raw, case
    scripts=[]
    active=[]
    execute=temporal_delivery.DeliverySQL.execute
    cursor_execute=isolation.Cursor.execute
    original_methods={n:getattr(isolation.Cursor,n,None) for n in ('fetchall','nextset')}

    def observe(cursor):
        if active:
            # These ODBC observations can overlap. Never sum as server totals.
            for message in getattr(cursor.raw,'messages',[]) or []:
                active[-1]['server_messages'][str(message)] += 1

    def method(name, original):
        def call(cursor,*args,**kwargs):
            if not active:
                return original(cursor,*args,**kwargs)
            wall,cpu=time.perf_counter(),time.process_time()
            try:
                return original(cursor,*args,**kwargs)
            finally:
                row=active[-1]['client_operations'][name]
                row['wall_seconds']+=time.perf_counter()-wall
                row['cpu_seconds']+=time.process_time()-cpu
                row['calls']+=1
                observe(cursor)
        return call

    isolation.Cursor.execute=method('execute',cursor_execute)
    for name in ('fetchall','nextset'):
        setattr(isolation.Cursor,name,method(name,lambda cursor,*a,_name=name,**kw:getattr(cursor.raw,_name)(*a,**kw)))

    def script(self,role,path,extra=None):
        if role!='DBM' or 'DailyDataImportExport' in path:
            return execute(self,role,path,extra)
        self.raw.execute('SET STATISTICS TIME ON; SET STATISTICS IO ON')
        row=dict(path=path,client_operations=defaultdict(lambda:dict(wall_seconds=0.0,cpu_seconds=0.0,calls=0)),server_messages=defaultdict(int))
        active.append(row)
        wall,cpu=time.perf_counter(),time.process_time()
        try:
            return execute(self,role,path,extra)
        finally:
            row.update(wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,calls=1)
            active.pop();scripts.append(row)
            self.raw.execute('SET STATISTICS TIME OFF; SET STATISTICS IO OFF')

    temporal_delivery.DeliverySQL.execute=script
    try:
        with isolation.exclusive_replay():
            output=temporal_day.execute_day(opening,opening_date,day,config,None,
                initial=True,commands=(),post_policy=None)
            result['returned_sections']=sorted(output)
            del output
    finally:
        temporal_delivery.DeliverySQL.execute=execute
        isolation.Cursor.execute=cursor_execute
        for name,original in original_methods.items():
            if original is None:delattr(isolation.Cursor,name)
            else:setattr(isolation.Cursor,name,original)
        result['dbm']=dict(scripts=scripts,
            dbm_wall_seconds=sum(r['wall_seconds'] for r in scripts),
            dbm_client_cpu_seconds=sum(r['cpu_seconds'] for r in scripts),
            limitations='Client execute includes SQL execution/transfer/driver work; client CPU is not SQL server CPU. STATISTICS observations may overlap; no summed CPU/read or wait attribution is claimed.')
        result['namespace']=dict(isolation.MAPPING)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine',choices=['modern','legacy'])
    parser.add_argument('--evidence',type=Path,required=True)
    options=parser.parse_args()
    save(options.evidence/(options.engine+'-started.json'),dict(owner=OWNER,engine=options.engine,time=time.time()))
    result=dict(owner=OWNER,engine=options.engine,artifact_sha256=SHA,date='2026-06-06',
        pairs=1240,status='FAILED',actions=False,parity=False,report_preparation=False,
        worker_memory_limit_bytes=4294967296,worker_cpus=2)
    try:
        (modern if options.engine=='modern' else legacy)(result)
        result['status']='COMPLETED_DIAGNOSTIC_ONLY'
    except BaseException:
        result['error']=traceback.format_exc()
        raise
    finally:
        save(options.evidence/(options.engine+'-dbm.json'),result)


if __name__=='__main__':
    main()
