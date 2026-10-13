"""Apply independently configured limits to an existing Docker service.

No creation, database operation or restart. For changed worker counts, render the
normal Compose overlay and use the documented targeted recreation separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True, encoding='utf-8')


def inspect(name):
    return json.loads(run('docker', 'inspect', name))[0]


def snapshot(value):
    host = value['HostConfig']
    return dict(id=value['Id'], image=value['Image'], started=value['State']['StartedAt'],
        running=value['State']['Running'], mounts=value['Mounts'],
        command=value['Config']['Cmd'], entrypoint=value['Config']['Entrypoint'],
        env_sha256=hashlib.sha256(json.dumps(sorted(value['Config']['Env'])).encode()).hexdigest(),
        ports=host['PortBindings'], networks=sorted(value['NetworkSettings']['Networks']),
        restart=host['RestartPolicy'], memory=host['Memory'], swap=host['MemorySwap'],
        cpus=host['NanoCpus'], tmpfs=host.get('Tmpfs'),
        compose_files=value['Config'].get('Labels', {}).get('com.docker.compose.project.config_files'))


def read_settings(path):
    settings = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            if not key.startswith('SERVE_'):
                raise ValueError('Only resource settings belong in this file')
            settings[key] = value.strip()
    return settings


def memory_bytes(value):
    suffix = value[-1].lower()
    return int(float(value[:-1]) * {'k':1024, 'm':1024**2, 'g':1024**3}[suffix]) if suffix in 'kmg' else int(value)


def apply(container, service, settings, record, execute=False):
    prefix = 'SERVE_' + service.upper() + '_'
    cpu = float(settings[prefix + 'CPUS'])
    memory = memory_bytes(settings[prefix + 'MEMORY'])
    swap = memory_bytes(settings[prefix + 'MEMORY_SWAP'])
    if cpu <= 0 or memory <= 0 or swap < memory:
        raise ValueError('Positive CPU/RAM and finite combined swap >= RAM are required')
    before = snapshot(inspect(container))
    if not before['running']:
        raise ValueError('Existing running service required')
    if service == 'pg' and before['tmpfs']:
        raise ValueError('Review database durable storage before changing resources')
    target = dict(cpus=round(cpu * 1e9), memory=memory, swap=swap)
    path = Path(record)
    if path.exists():
        raise ValueError('Use a new evidence record; never overwrite a prior application')
    path.parent.mkdir(parents=True, exist_ok=True)
    evidence = dict(container=container, service=service, before=before, target=target,
                    status='PLANNED', rollback=['docker','update','--cpus',str(before['cpus']/1e9),
                    '--memory',str(before['memory']),'--memory-swap',str(before['swap']),container])
    path.write_text(json.dumps(evidence, indent=2))
    if execute:
        if any(before[k] != v for k,v in target.items()):
            run('docker','update','--cpus',str(cpu),'--memory',str(memory),
                '--memory-swap',str(swap),container)
        after = snapshot(inspect(container))
        assert all(after[k] == v for k,v in target.items()), 'Resource application mismatch'
        assert {k:v for k,v in after.items() if k not in target} == {
            k:v for k,v in before.items() if k not in target}, 'Non-resource state changed'
        evidence.update(status='APPLIED',after=after)
        path.write_text(json.dumps(evidence, indent=2))
    print(json.dumps(dict(status=evidence['status'],container=container,target=target,record=str(path))))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container',required=True)
    parser.add_argument('--service',choices=['mta','auth','mto','frontend','redis','pg'],required=True)
    parser.add_argument('--settings',required=True)
    parser.add_argument('--record',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    apply(args.container,args.service,read_settings(args.settings),args.record,args.apply)
