"""Read-only protected-runtime and accepted Fresh state receipt for F3 preview."""
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path


def run(*args):
    return subprocess.check_output(args, text=True, encoding='utf-8').strip()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def snapshot():
    names = [n for n in run('docker', 'ps', '--format', '{{.Names}}').splitlines()
             if n.startswith(('vectorflow-integrated-', 'vectorflow-demo-0acabc0-'))]
    containers = {}
    for name in sorted(names):
        obj = json.loads(run('docker', 'inspect', name))[0]
        containers[name] = dict(id=obj['Id'], image=obj['Image'],
            config_sha256=digest(json.dumps(obj['Config'], sort_keys=True)),
            mounts=obj['Mounts'], networks=obj['NetworkSettings']['Networks'],
            started=obj['State']['StartedAt'], running=obj['State']['Running'],
            health=obj['State'].get('Health', {}).get('Status'))
    http = {}
    for route in ('healthz', 'login', 'mta/dbm/dbm-norm-suggestions'):
        with urllib.request.urlopen(f'http://localhost:3004/{route}', timeout=30) as response:
            http[route] = dict(status=response.status, sha256=hashlib.sha256(response.read()).hexdigest())
    protected_sql = "SELECT md5(COALESCE(string_agg(row_to_json(t)::text,E'\\n' ORDER BY row_to_json(t)::text),'')) FROM public.mta_run t; SELECT md5(COALESCE(string_agg(row_to_json(t)::text,E'\\n' ORDER BY row_to_json(t)::text),'')) FROM public.mta_demo_dataset_run t;"
    protected = run('docker', 'exec', 'vectorflow-integrated-postgres-1', 'psql',
        '-U', 'vectorflow_integrated', '-d', 'vectorflow_integrated_mta', '-At', '-c', protected_sql)
    fresh = run('docker', 'exec', 'freshvcf-test-postgres-1', 'psql', '-U', 'freshvcf',
        '-d', 'freshvcf', '-At', '-c',
        "SELECT md5(row_to_json(t)::text) FROM mta.fresh_mta_calculationrun t WHERE id='ac1612c8-0e49-4155-83c3-f59f41422293'; SELECT count(*),md5(COALESCE(string_agg(row_to_json(t)::text,E'\\n' ORDER BY row_to_json(t)::text),'')) FROM mta.fresh_mta_runcommand t;")
    return dict(containers=containers, http3004=http, protected_publication=protected,
                fresh_publication_and_actions=fresh)


if __name__ == '__main__':
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    value = snapshot()
    if len(sys.argv) > 2:
        before = json.loads(Path(sys.argv[2]).read_text())
        assert value == before, 'Protected runtime/publication snapshot changed'
    with target.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
    print(f'Protected snapshot preserved: {target}')
