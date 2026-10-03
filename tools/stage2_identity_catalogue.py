"""Coordinate the bounded 3005 catalogue selection and normal restoration.

No catalogue generation. Configuration comes from the selected MTA deployment;
the existing fixture policy or normal hierarchy binding is mounted read-only.
External checkpoints preserve the earlier stabilization evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import stage2_fixture_window as window

EVIDENCE = Path('D:/freshvcf-build/evidence/3005-login-decoupling-20261004-001')
GATEWAY = 'freshvcf-preview-user-service-1'
FRONTEND = 'freshvcf-preview-frontend-1'
KEYS = ('VF_MTA_PERMISSIONS_FILE', 'VF_MTA_PERMISSIONS_SHA256',
        'VF_MTA_FIXTURE_FILE', 'VF_MTA_FIXTURE_SHA256',
        'VF_MTA_HIERARCHY_FILE', 'VF_MTA_HIERARCHY_SHA256',
        'VF_MTA_PUBLISHED_RUN', 'VF_MTA_PUBLISHED_DIGEST')


def selection(env, mounts):
    environment = {key: env.get(key, '') for key in KEYS}
    environment['VF_MTA_LOCAL_PERMISSIONS'] = '1'
    volumes = []
    for prefix in ('VF_MTA_PERMISSIONS', 'VF_MTA_FIXTURE', 'VF_MTA_HIERARCHY'):
        path = environment[prefix + '_FILE']
        if not path:
            continue
        source = mounts.get(path)
        if source is None and path == '/app/baseline/presentation-hierarchy-v1.json':
            source = str(window.ROOT / 'baseline/presentation-hierarchy-v1.json')
        if source is None:
            raise ValueError('Selected catalogue binding lacks an owned read-only source: ' + path)
        if hashlib.sha256(Path(source).read_bytes()).hexdigest() != environment[prefix + '_SHA256']:
            raise ValueError('Selected catalogue binding checksum mismatch: ' + path)
        volumes.append(str(source).replace('\\', '/') + ':' + path + ':ro')
    return dict(environment=environment, volumes=volumes)


def live_selection():
    item = window.inspect(window.MTA)
    return selection(dict(v.split('=', 1) for v in item['Config']['Env']),
                     {v['Destination']: v['Source'] for v in item['Mounts'] if not v['RW']})


def gateway_selection():
    item = window.inspect(GATEWAY)
    env = dict(v.split('=', 1) for v in item['Config']['Env'])
    if env.get('VF_MTA_LOCAL_PERMISSIONS') != '1':
        raise ValueError('Gateway local catalogue mode not configured')
    return selection(env, {v['Destination']: v['Source'] for v in item['Mounts'] if not v['RW']})


def saved(name):
    return json.loads((EVIDENCE / name).read_text())


def compose(name, *services):
    subprocess.run(window.COMPOSE + ['-f', str(EVIDENCE / name), 'up', '-d',
                   '--no-deps', '--no-build', *services], check=True)


def prepare():
    if (EVIDENCE / 'before.json').exists():
        raise ValueError('Preserve the existing deployment checkpoint')
    current = live_selection()
    # Render only in memory: the compose output includes secrets, never log it.
    normal = json.loads(subprocess.check_output(window.COMPOSE + ['-f',
        str(window.DEST / 'compose.restore.json'), 'config', '--format', 'json']))['services']['mta']
    normal_selection = selection(normal['environment'],
        {v['target']: v['source'] for v in normal['volumes'] if v.get('read_only')})
    images = dict(gateway=window.inspect(GATEWAY)['Image'], frontend=window.inspect(FRONTEND)['Image'])
    window.atomic(EVIDENCE / 'before.json', dict(protected=window.protected(),
        mta=window.runtime(window.inspect(window.MTA)), ready=window.ready(), selection=current))
    for name, selected in (('candidate', current), ('normal', normal_selection)):
        services = {'user-service': dict(image='freshvcf-preview-user:login-decoupling-20261004', **selected)}
        if name == 'candidate':
            services['frontend'] = dict(image='freshvcf-preview-frontend:login-decoupling-20261004')
        else:
            services['mta'] = json.loads((window.DEST / 'compose.restore.json').read_text())['services']['mta']
        window.atomic(EVIDENCE / ('compose.' + name + '.json'), dict(services=services))
    window.atomic(EVIDENCE / 'compose.rollback.json', dict(services={
        'user-service': dict(image=images['gateway']), 'frontend': dict(image=images['frontend'])}))
    print('Prepared fixture and normal catalogue configuration; no serving mutation')


def check_current():
    after = saved('after.json')
    if window.protected() != after['protected'] or window.runtime(window.inspect(window.MTA)) != after['mta']:
        raise ValueError('Runtime or protected state changed after catalogue deployment')
    if live_selection() != saved('before.json')['selection']:
        raise ValueError('MTA catalogue selection changed')
    if gateway_selection() != live_selection():
        raise ValueError('Gateway and MTA catalogue selection differ')
    for name in ('candidate', 'normal'):
        service = saved('compose.' + name + '.json')['services']['user-service']
        # Recheck the retained input bytes without selecting another dataset.
        sources = {v.rsplit(':', 2)[1]: v.rsplit(':', 2)[0] for v in service['volumes']}
        if selection(service['environment'], sources) != {k: service[k] for k in ('environment', 'volumes')}:
            raise ValueError('Restoration catalogue configuration changed')
    print('Current runtime and both restoration catalogue inputs verified')


def gateway_ready():
    code = "import urllib.request;print(urllib.request.urlopen('http://localhost:10016/readyz',timeout=6).read().decode())"
    for _ in range(30):
        call = subprocess.run(['docker', 'exec', GATEWAY, 'python', '-c', code], capture_output=True, text=True)
        if call.returncode == 0:
            result = json.loads(call.stdout)
            if result.get('status') == 'ready' and result['checks'].get('mta_catalogue'):
                return result
        time.sleep(2)
    raise RuntimeError('Gateway catalogue/dependency readiness not established')


def deploy():
    before = saved('before.json')
    if window.protected() != before['protected'] or window.runtime(window.inspect(window.MTA)) != before['mta']:
        raise ValueError('Runtime changed before deployment')
    if live_selection() != before['selection']:
        raise ValueError('MTA catalogue selection changed before deployment')
    candidate = saved('compose.candidate.json')['services']['user-service']
    if {k: candidate[k] for k in ('environment', 'volumes')} != live_selection():
        raise ValueError('Candidate gateway catalogue differs from serving MTA')
    compose('compose.candidate.json', 'user-service', 'frontend')
    gateway_ready()
    if gateway_selection() != live_selection():
        raise ValueError('Deployed gateway catalogue differs from serving MTA')
    after = dict(protected=window.protected(), mta=window.runtime(window.inspect(window.MTA)), ready=window.ready())
    if after['mta'] != before['mta'] or after['ready'] != before['ready']:
        raise ValueError('MTA selection changed during gateway deployment')
    if after['protected']['accepted'] != before['protected']['accepted']:
        raise ValueError('Accepted state changed')
    for service in ('mto', 'redis'):
        name = 'freshvcf-preview-' + service + '-1'
        if after['protected']['preview'][name] != before['protected']['preview'][name]:
            raise ValueError('Protected service changed: ' + name)
    window.atomic(EVIDENCE / 'after.json', after)


def restore():
    check_current()
    before = saved('before.json')
    target = json.loads((window.DEST / 'fixture-window-010/window-before.json').read_text())
    destination = EVIDENCE / 'normal-restoration'
    destination.mkdir(exist_ok=False)
    # Close public ingress throughout the coordinated selection change. On error
    # leave ingress stopped, preserving evidence instead of exposing a mismatch.
    subprocess.run(['docker', 'stop', FRONTEND], check=True)
    window.WINDOW = destination
    window.accounts('disable')
    compose('compose.normal.json', 'mta', 'user-service')
    ready = window.ready()
    if window.runtime(window.inspect(window.MTA)) != target['mta'] or ready != target['ready']:
        raise ValueError('Normal MTA restoration differs from retained target')
    if live_selection() != {k: saved('compose.normal.json')['services']['user-service'][k]
                            for k in ('environment', 'volumes')}:
        raise ValueError('Gateway and MTA normal selection differ')
    gateway_ready()
    if gateway_selection() != live_selection():
        raise ValueError('Restored gateway and MTA catalogue differ')
    current = window.protected()
    if current['accepted'] != before['protected']['accepted']:
        raise ValueError('Protected accepted state changed')
    for service in ('mto', 'redis'):
        name = 'freshvcf-preview-' + service + '-1'
        if current['preview'][name] != before['protected']['preview'][name]:
            raise ValueError('Protected service changed')
    subprocess.run(['docker', 'start', FRONTEND], check=True)
    window.atomic(destination / 'restored.json', dict(ready=ready, protected=window.protected(),
        mta=window.runtime(window.inspect(window.MTA)), catalogue_selection='normal'))
    print('Normal MTA and gateway catalogue restored together; fixture accounts disabled')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'deploy', 'check', 'restore'))
    args = parser.parse_args()
    {'prepare': prepare, 'deploy': deploy, 'check': check_current, 'restore': restore}[args.operation]()
