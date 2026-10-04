"""Run the retained nine-request proof on existing services at serving limits.

No build, restart, limit change or new container. Full responses and drain
observations stay in a newly named external evidence directory.
"""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

APP = 'freshvcf-preview-mta-1'
CLIENT = 'freshvcf-preview-user-service-1'
PG = 'freshvcf-test-postgres-1'
DATABASE = 'test_freshvcf_stage2_vm_20261003_002'


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True)


def limits(generation):
    rows = []
    for name, memory, cpus in ((APP, 4*1024**3, 2*10**9), (PG, 1024**3, 10**9)):
        item = json.loads(docker('inspect', name))[0]
        assert item['State']['Running']
        actual = item['HostConfig']
        assert (actual['Memory'], actual['NanoCpus']) == (memory, cpus), 'Not fixed serving limits'
        if name == APP:
            environment = dict(value.split('=', 1) for value in item['Config']['Env'] if '=' in value)
            assert environment.get('VF_BTR_REPORTING_GENERATION') == generation, 'Wrong reporting selection'
        rows.append(dict(name=name, id=item['Id'], image=item['Image'],
                         memory=actual['Memory'], nano_cpus=actual['NanoCpus']))
    return rows


RESOURCE = """import json, pathlib, os, time
p=pathlib.Path('/sys/fs/cgroup'); cpu=0
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdigit() or int(process.name)==os.getpid(): continue
 try:
  if b'/usr/local/bin/gunicorn' not in process.joinpath('cmdline').read_bytes().split(bytes([0])): continue
  fields=process.joinpath('stat').read_text().rsplit(')',1)[1].split()
  cpu+=(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
 except FileNotFoundError: pass
print(json.dumps(dict(at=time.time(),worker_cpu_seconds=cpu,memory=int((p/'memory.current').read_text()),events=(p/'memory.events').read_text())))
"""
ACTIVITY = ("SELECT COALESCE(json_agg(t),'[]') FROM (SELECT pid,state,wait_event_type,wait_event "
            "FROM pg_stat_activity WHERE datname='" + DATABASE + "' AND pid<>pg_backend_pid()) t")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--generation', required=True)
    parser.add_argument('--reference', type=Path, required=True,
                        help='Retained fixture-contract directory with complete baseline bodies')
    args = parser.parse_args()
    root = args.evidence.resolve()
    assert root.is_relative_to(Path('D:/freshvcf-build/evidence').resolve())
    root.mkdir(exist_ok=False)
    before = limits(args.generation)
    (root/'limits-before.json').write_text(json.dumps(before, indent=2))
    remote = '/tmp/' + root.name
    docker('exec', CLIENT, 'mkdir', remote)
    for filename in ('stage2_report_contention_probe.py', 'stage2_availability_probe.py'):
        docker('cp', str(Path(__file__).with_name(filename)), CLIENT + ':' + remote + '/' + filename)
    results = []
    for number in range(1, 4):
        phase = 'reporting-nine-' + str(number)
        stop = threading.Event()
        state = {}
        errors = []

        def observe():
            try:
                with (root/(phase+'-resources.jsonl')).open('x') as output:
                    while not stop.is_set():
                        app = json.loads(docker('exec', APP, 'python', '-c', RESOURCE))
                        db = json.loads(docker('exec', PG, 'psql', '-U', 'freshvcf', '-d', DATABASE,
                                               '-At', '-c', ACTIVITY))
                        state['latest'] = dict(app=app, database=db)
                        output.write(json.dumps(state['latest'])+'\n')
                        output.flush()
                        stop.wait(1)
            except Exception as exc:
                errors.append(repr(exc))

        watcher = threading.Thread(target=observe)
        watcher.start()
        try:
            with (root/(phase+'.log')).open('x') as log:
                code = subprocess.call(['docker', 'exec', '-e', 'PROFILE_ROUTE='+phase,
                    '-e', 'PROFILE_EVIDENCE_ROOT='+remote, CLIENT, 'python',
                    remote+'/stage2_report_contention_probe.py'], stdout=log, stderr=subprocess.STDOUT)
            finished = time.monotonic()
            previous = None
            quiet = 0
            drain = []
            while quiet < 3 and time.monotonic()-finished < 240:
                if errors:
                    raise RuntimeError(errors)
                sample = state.get('latest')
                if sample and (previous is None or sample['app']['at'] != previous['at']):
                    app = sample['app']
                    rate = None if previous is None else ((app['worker_cpu_seconds']-previous['worker_cpu_seconds']) /
                                                          (app['at']-previous['at']))
                    active = [r for r in sample['database'] if r['state'] != 'idle']
                    quiet = quiet+1 if rate is not None and rate < .1 and not active else 0
                    drain.append(dict(at=app['at'], cpu_cores=rate, nonidle=len(active), quiet=quiet))
                    previous = app
                stop.wait(1)
            (root/(phase+'-drain.json')).write_text(json.dumps(dict(quiet_samples=quiet,
                post_client_seconds=time.monotonic()-finished, samples=drain), indent=2))
            assert quiet >= 3, 'Serving work did not drain'
            assert code == 0, 'Probe process failed; retain log and response files'
        finally:
            stop.set()
            watcher.join()
            # Preserve completed and partial bodies even on failed assertions.
            docker('cp', CLIENT+':'+remote+'/'+phase, str(root/phase))
        result = json.loads((root/phase/'result.json').read_text())
        for path in (root/phase).glob('*.json.gz'):
            with gzip.open(path, 'rt') as stream:
                body = json.load(stream)
            assert isinstance(body, dict) and body.get('status', 200) == 200, path.name
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from parity.btr_benchmark_contract import compare, MANIFEST
        comparisons = []
        for route in ('GetBTRData', 'GetBTRDataCount'):
            with gzip.open(root/phase/(route+'.json.gz'), 'rt') as stream:
                actual = json.load(stream)
            with gzip.open(args.reference/('broad-first-'+route+'-baseline.json.gz'), 'rt') as stream:
                expected = json.load(stream)
            comparison = (compare(actual, expected, manifest_sha256=MANIFEST,
                business_date='2026-04-07', route=route) if route == 'GetBTRData' else
                dict(status='PASS_STRICT' if actual == expected else 'FAIL'))
            comparisons.append(dict(route=route, **comparison))
        (root/(phase+'-comparison.json')).write_text(json.dumps(comparisons, indent=2))
        assert all(row['status'].startswith('PASS') for row in comparisons)
        assert result['failures'] == result['profile_failures'] == 0
        assert len(result['requests']) == 10
        assert all(r['seconds'] < 60 for r in result['requests']), '60-second request gate failed'
        results.append(result)
        print(json.dumps(dict(phase=phase, status='PASS', max_seconds=max(r['seconds'] for r in result['requests']))), flush=True)
    assert limits(args.generation) == before, 'Serving identity or limits changed during proof'
    (root/'result.json').write_text(json.dumps(dict(status='PASS', bursts=results, limits=before), indent=2))


if __name__ == '__main__':
    main()
