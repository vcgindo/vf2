"""Existing-stack native-API BTR benchmark; full responses and fixed requests.

The native API series does not certify browser/gateway or application-cold gates.
Windows budgets are controlled separately by btr_windows_budget.py. Both engines
use the same isolated HTTP client, and each paired grid/count journey is concurrent.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = Path('D:/freshvcf-build/evidence/3005-btr-performance-20261004-001')
APP = 'freshvcf-preview-mta-1'
PG = 'freshvcf-test-postgres-1'
CLIENT = 'freshvcf-preview-user-service-1'
IMAGE = 'sha256:761719e96c0f95ccdb5f0ad79f7e96125b172ab79fafac72e3a3790615bc952a'
ROUTES = ('GetBTRData', 'GetBTRDataCount')


def docker(*args):
    return subprocess.check_output(['docker', *args])


def prepare():
    # Read-only check of the existing application/database/client. No new
    # container, database, volume, port, secret file or resource mutation.
    summary=[]
    for name in (PG,APP,CLIENT):
        item=json.loads(docker('inspect',name))[0]
        assert item['State']['Running'],name
        if name==APP:assert item['Image']==IMAGE
        summary.append(dict(name=name,image=item['Image'],memory=item['HostConfig']['Memory'],
                            cpus=item['HostConfig']['NanoCpus']))
    (ROOT/'benchmark-existing-runtime.json').write_text(json.dumps(summary,indent=2))


def client(config):
    """Runs inside the identical client process boundary for either API."""
    payload = json.dumps(config['payload']).encode()
    count = config['concurrency']*2
    barrier = threading.Barrier(count)
    def request(index):
        route = ROUTES[index % 2]
        name = config['sample']+'-'+str(index)+'-'+route
        headers = {'Content-Type': 'application/json', 'Host': 'localhost'}
        if config['engine'] == 'fresh':
            headers['X-Vectorflow-Identity'] = json.dumps(config['actor'])
        url = ('http://'+APP+':8000' if config['engine']=='fresh' else
               'http://host.docker.internal:5153')+'/api/mta/'+route
        req = urllib.request.Request(url, data=payload, headers=headers)
        barrier.wait(timeout=20)
        started = time.perf_counter(); body = b''; error = None; status = None
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                status = response.status; body = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code; body = exc.read(); error = repr(exc)
        except Exception as exc:
            error = repr(exc)
        elapsed = time.perf_counter()-started
        return dict(route=route, seconds=elapsed, http_status=status,
                    error=error, bytes=len(body), body=name+'.json.gz',
                    journey=index//2,content=body)
    with ThreadPoolExecutor(max_workers=count) as pool:
        observations = list(pool.map(request, range(count)))
    # Finish every request before compressing/hashing any response, so evidence
    # work cannot contend with another in-flight body transfer in this batch.
    for observation in observations:
        body=observation.pop('content')
        observation['sha256']=hashlib.sha256(body).hexdigest()
        observation['compressed_body']=base64.b64encode(gzip.compress(body)).decode('ascii')
    print(json.dumps(observations), flush=True)


def check_outputs(root, observations):
    from parity.btr_benchmark_contract import compare, MANIFEST
    results=[]
    for item in observations:
        reference = ROOT/'fixture-contract'/('broad-first-'+item['route']+'-baseline.json.gz')
        with gzip.open(reference, 'rt') as stream: expected=json.load(stream)
        try:
            with gzip.open(root/item['body'], 'rt') as stream: actual=json.load(stream)
        except ValueError:
            results.append(dict(body=item['body'], status='FAIL_INVALID_JSON'));continue
        if item['route']=='GetBTRData':
            result=compare(actual, expected, manifest_sha256=MANIFEST,
                           business_date='2026-04-07', route=item['route'])
        else:
            result=dict(status='PASS_STRICT' if actual==expected else 'FAIL',
                        actual=actual, expected=expected)
        results.append(dict(body=item['body'], **result))
    return results


def resources():
    """Read-only counters outside request timing; retain competing SQL activity."""
    from tools.stage2_vm_dataset import connect
    result=dict(at=time.time(),containers=[])
    for name in (PG,APP,CLIENT):
        cpu=docker('exec',name,'cat','/sys/fs/cgroup/cpu.stat').decode()
        memory=docker('exec',name,'cat','/sys/fs/cgroup/memory.current').decode()
        result['containers'].append(dict(name=name,cpu=cpu,memory_bytes=int(memory)))
    with connect() as connection:
        cursor=connection.cursor()
        cursor.execute("SELECT DB_NAME(database_id),session_id,status,cpu_time,total_elapsed_time "
                       "FROM sys.dm_exec_requests WHERE session_id<>@@SPID AND session_id>50")
        result['sql_requests']=[dict(database=r[0],session=r[1],status=r[2],cpu_ms=r[3],elapsed_ms=r[4]) for r in cursor]
        cursor.execute("SELECT session_id,cpu_time,reads,writes,logical_reads FROM sys.dm_exec_sessions "
                       "WHERE is_user_process=1 AND session_id<>@@SPID")
        result['sql_sessions']=[dict(session=r[0],cpu_ms=r[1],reads=r[2],writes=r[3],logical_reads=r[4]) for r in cursor]
        cursor.execute('SELECT * FROM sys.dm_os_job_object')
        columns=[column[0] for column in cursor.description]
        result['sql_job']=[dict(zip(columns,row)) for row in cursor]
    command="Get-Process | Select-Object Id,ProcessName,CPU,WorkingSet64,PrivateMemorySize64 | ConvertTo-Json -Compress"
    result['host_processes']=json.loads(subprocess.check_output(
        ['powershell','-NoProfile','-Command',command]))
    return result


def series(name, budget_directory, measured, concurrencies=(1,4)):
    from parity.legacy_isolation import exclusive_replay
    os.environ['VFTEST_PROFILE']='fresh'
    root=ROOT/name;root.mkdir(exist_ok=False)
    budget=Path(budget_directory)
    ready=json.loads((budget/'budget-ready.json').read_text())
    windows=[item for item in ready if 'pid' in item]
    postgres=[item for item in ready if item.get('container')==PG]
    assert len(windows)==2 and all(item['cpu_rate']==1250 for item in windows)
    assert sorted(item['memory_bytes'] for item in windows)==[3*1024**3,4*1024**3]
    assert len(postgres)==1 and postgres[0]['memory_bytes']==3*1024**3 and postgres[0]['nano_cpus']==2*10**9
    assert not (budget/'budget-result.json').exists(), 'Resource window already ended'
    policy=json.loads(Path('D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/fixture-serving.json').read_text())
    actor=next(a for a in policy['actors'] if 'broad' in a['email'])
    payload=dict(name='both', filters={'horizonFilter':{'filters':[]}},
                 paginationParameter=dict(pageNumber=1,recordsPerPage=5000),
                 product_permissions=actor['products'], location_permissions=actor['locations'])
    stop=threading.Event()
    def heartbeat():
        while not stop.wait(10): (budget/'budget-heartbeat').touch()
    (budget/'budget-heartbeat').touch()
    worker=threading.Thread(target=heartbeat);worker.start()
    records=[]
    try:
        with exclusive_replay(validate_schema=False):
            for concurrency in concurrencies:
                for number in range(5+measured):
                    # Alternate first engine to reduce monotonic host/cache bias.
                    for engine in (('legacy','fresh') if number%2==0 else ('fresh','legacy')):
                        assert not (budget/'budget-result.json').exists(), 'Resource window ended'
                        sample=f'c{concurrency}-{number:02d}-{engine}'
                        config=dict(series=name,sample=sample,engine=engine,concurrency=concurrency,
                                    payload=payload,actor=dict(id=actor['id'],email=actor['email']))
                        before=resources()
                        source=Path(__file__).read_text()
                        invocation='namespace={"__name__":"btr_http_client"}; exec('+repr(source)+',namespace); namespace["client"]('+repr(config)+')'
                        raw=subprocess.check_output(['docker','exec','-i',CLIENT,'python','-'],
                                                    input=invocation.encode(),timeout=210)
                        observations=json.loads(raw)
                        for observation in observations:
                            (root/observation['body']).write_bytes(base64.b64decode(observation.pop('compressed_body')))
                        # Preserve every response before ancillary monitoring:
                        # a resource-counter failure cannot erase request evidence.
                        (root/(sample+'-requests.json')).write_text(json.dumps(observations,indent=2))
                        try:
                            after=resources()
                        except Exception as exc:
                            after=dict(error=repr(exc),at=time.time())
                        (root/(sample+'-resources.json')).write_text(json.dumps(dict(before=before,after=after),indent=2))
                        comparisons=check_outputs(root,observations)
                        (root/(sample+'-comparison.json')).write_text(json.dumps(comparisons,indent=2))
                        record=dict(sample=sample,engine=engine,concurrency=concurrency,
                                    warmup=number<5,requests=observations,
                                    valid=all(c['status'].startswith('PASS') for c in comparisons)
                                      and all(o['http_status']==200 and o['error'] is None for o in observations),
                                    resource_observation_valid='error' not in after)
                        records.append(record)
                        with (root/'observations.jsonl').open('a') as output:output.write(json.dumps(record)+'\n')
                        print(sample, 'valid='+str(record['valid']),
                              'max_seconds='+str(round(max(o['seconds'] for o in observations),3)),flush=True)
                        # Invalid full responses block comparability, never drop failures.
                        if not record['valid']:raise RuntimeError('Full response or request failure; retained in '+sample)
                        if not record['resource_observation_valid']:raise RuntimeError('Resource observation failed; responses retained in '+sample)
                        assert not (budget/'budget-result.json').exists(), 'Resource window ended during sample'
        summary=[]
        for concurrency in concurrencies:
            for engine in ('legacy','fresh'):
                batches=[r for r in records if r['concurrency']==concurrency and r['engine']==engine and not r['warmup']]
                batch_durations=[max(o['seconds'] for o in r['requests']) for r in batches]
                durations=[max(o['seconds'] for o in batch['requests'] if o['journey']==journey)
                           for batch in batches for journey in range(concurrency)]
                ordered=sorted(durations)
                summary.append(dict(engine=engine,concurrency=concurrency,batches=len(batches),
                    journeys=len(durations),
                    median=statistics.median(durations),p95=ordered[max(0,__import__('math').ceil(.95*len(ordered))-1)],
                    journeys_per_second=len(batches)*concurrency/sum(batch_durations)))
        (root/'summary.json').write_text(json.dumps(dict(native_api_only=True,measured=measured,summary=summary),indent=2))
    finally:
        stop.set();worker.join();(budget/'budget-stop').touch()


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('prepare','client','series'))
    parser.add_argument('--name');parser.add_argument('--budget-directory')
    parser.add_argument('--measured',type=int,default=30)
    parser.add_argument('--concurrency',type=int,choices=(1,4),nargs='+',default=[1,4])
    args=parser.parse_args()
    if args.operation=='prepare':prepare()
    elif args.operation=='client':client(json.load(sys.stdin))
    else:series(args.name,args.budget_directory,args.measured,args.concurrency)
