"""Bounded, port-free two-worker startup proof. No state/engine/action writes."""
import json
import re
import subprocess
import sys
from pathlib import Path

target = Path(sys.argv[1])
target.mkdir(parents=True, exist_ok=False)
compose = ['docker', 'compose', '--env-file', 'D:/freshvcf-build/preview/preview.env',
           '-f', 'compose.preview.yaml']
name = 'freshvcf-stage1-preload-proof-003'
bad = subprocess.run(compose + ['run', '--rm', '--no-deps', '-T', '-e',
    'VF_MTA_PUBLISHED_DIGEST=' + '0'*64, 'mta'], capture_output=True, text=True, timeout=45)
(target/'failed-startup.log').write_text(bad.stdout + bad.stderr)
assert bad.returncode != 0 and 'aborting application startup' in bad.stderr
assert 'Booting worker' not in bad.stderr and 'Listening at' not in bad.stderr

# Compose preserves the existing memory/CPU/restart limits; no --service-ports.
created = subprocess.run(compose + ['run', '--rm', '--no-deps', '-d', '--name', name,
    'mta', 'gunicorn', 'vectorflow.wsgi:application', '--preload', '--bind', '0.0.0.0:8000',
    '--workers', '2', '--timeout', '180', '--access-logfile', '-',
    '--access-logformat', '%(p)s %(s)s %(U)s'], capture_output=True, text=True, check=True)
try:
    inspection = json.loads(subprocess.check_output(['docker', 'inspect', name], text=True))[0]
    assert not inspection['HostConfig']['PortBindings']
    assert inspection['HostConfig']['Memory'] == 4*1024**3
    assert inspection['HostConfig']['NanoCpus'] == 2_000_000_000
    assert inspection['HostConfig']['RestartPolicy']['Name'] == 'no'
    source = '''
import concurrent.futures,json,time,urllib.request
from pathlib import Path
deadline=time.monotonic()+50
def read(_):
    return json.load(urllib.request.urlopen('http://127.0.0.1:8000/readyz',timeout=5))
while True:
    try:
        first=read(0); break
    except Exception:
        if time.monotonic()>deadline: raise
        time.sleep(0.5)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    values=list(pool.map(read,range(32)))
assert all(v==first and v['ready'] for v in values)
children=Path('/proc/1/task/1/children').read_text().split()
rss={pid:next(l for l in Path('/proc/'+pid+'/status').read_text().splitlines() if l.startswith('VmRSS:')) for pid in ['1']+children}
print(json.dumps(dict(readiness=first,requests=len(values),process_rss=rss,
    memory_peak_bytes=int(Path('/sys/fs/cgroup/memory.peak').read_text()),
    memory_current_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()))))
'''
    probe = subprocess.run(['docker', 'exec', '-i', name, 'python', '-'], input=source,
                           capture_output=True, text=True, timeout=60)
    (target/'valid-startup.stdout').write_text(probe.stdout)
    (target/'valid-startup.stderr').write_text(probe.stderr)
    assert probe.returncode == 0, probe.stderr
    result = json.loads(probe.stdout)
    log = subprocess.run(['docker', 'logs', name], capture_output=True, text=True, check=True)
    # Docker separates stderr lifecycle and stdout access logs. Lifecycle order
    # is preserved on stderr; use it to prove admission preceded the listener.
    (target/'lifecycle.log').write_text(log.stderr)
    (target/'access.log').write_text(log.stdout)
    assert log.stderr.count('Publication admitted:') == 1
    assert log.stderr.index('Publication admitted:') < log.stderr.index('Listening at:')
    workers = set(re.findall(r'Booting worker with pid: (\d+)', log.stderr))
    served = set(re.findall(r'<(\d+)> 200 /readyz', log.stdout))
    assert len(workers) == 2 and served == workers, (workers, served)
    result.update(status='PASS', image=inspection['Image'], invalid_master_exit=bad.returncode,
        invalid_listener_started=False, invalid_workers_started=0,
        shared_admission_before_listener=True, serving_workers=sorted(workers),
        no_host_port=True, memory_limit_bytes=inspection['HostConfig']['Memory'],
        nano_cpus=inspection['HostConfig']['NanoCpus'], restart='no')
    assert result['memory_peak_bytes'] < result['memory_limit_bytes']
    (target/'receipt.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
finally:
    # Only this exact owned temporary container is stopped; --rm cleans it up.
    subprocess.run(['docker', 'stop', name], check=True, capture_output=True)
