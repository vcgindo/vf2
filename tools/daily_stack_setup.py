"""Create the owned 3006 configuration; never operate the protected preview.

Configuration and credentials remain outside Git. This provisions no calculation,
fixture, selected run, or parity receipt. Existing local test identities are copied
as a narrow authentication contract, not as a database or business-data copy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import socket
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OWNER = Path('D:/freshvcf-build/daily-3006')
EVIDENCE = Path('D:/freshvcf-build/evidence/daily-publication-3006-20261006-001')
PROJECT = 'freshvcf-daily3006'


def run(*args, input=None):
    return subprocess.check_output(args, input=input, text=True, encoding='utf-8')


def snapshot():
    result = {}
    names = run('docker', 'ps', '--format', '{{.Names}}').splitlines()
    for name in sorted(n for n in names if not n.startswith(PROJECT + '-')):
        value = json.loads(run('docker', 'inspect', name))[0]
        result[name] = dict(id=value['Id'], image=value['Image'],
            started=value['State']['StartedAt'],
            config_digest=hashlib.sha256(json.dumps(value['Config'], sort_keys=True).encode()).hexdigest(),
            host_digest=hashlib.sha256(json.dumps(value['HostConfig'], sort_keys=True).encode()).hexdigest(),
            mounts=value['Mounts'])
    return result


def prepare():
    if (OWNER / 'compose.json').exists():
        raise ValueError('Configuration already exists; inspect/reuse it, never reset')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 3006))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / 'protected-before.json').write_text(json.dumps(snapshot(), indent=2))
    OWNER.mkdir(parents=True, exist_ok=True)
    private = OWNER / 'secrets'
    private.mkdir(exist_ok=True)
    for name in ('runtime', 'inputs', 'build'):
        (OWNER / name).mkdir(exist_ok=True)
    # The unchanged compiled frontend and user service share this client key.
    old = json.loads(run('docker', 'inspect', 'freshvcf-preview-user-service-1'))[0]
    oldenv = dict(x.split('=', 1) for x in old['Config']['Env'])
    password = secrets.token_urlsafe(36)
    secret = secrets.token_hex(40)
    # Use the accepted image's bundled cryptography package in an owned,
    # networkless transient process, never install into a serving container.
    script = ("import os\nos.environ['USER_SERVICE_DATABASE_PASSWORD']=" + repr(password) +
        "\nos.environ['USER_SERVICE_SECRET_DIR']='/owned'\n" +
        (ROOT / 'infrastructure/docker/user-service-key-init.py').read_text())
    run('docker','run','--rm','--network','none','--memory','1g','--cpus','1',
        '--user','0','-i','-v',str(private)+':/owned','--entrypoint','python',old['Image'],'-',input=script)
    common = dict(restart='no', networks=['daily'])
    database = dict(DB_HOST='postgres', DB_PORT='5432', DB_NAME='daily_3006', DB_USER='daily_3006')
    services = {
        'postgres': dict(image='postgres:16.15-alpine', **common, mem_limit='1g', cpus=1,
            environment=dict(POSTGRES_DB='daily_3006', POSTGRES_USER='daily_3006', POSTGRES_PASSWORD=password),
            volumes=['daily-db:/var/lib/postgresql/data',
                str(ROOT / 'infrastructure/fresh/init.sql').replace('\\', '/') + ':/docker-entrypoint-initdb.d/01-schemas.sql:ro'],
            healthcheck=dict(test=['CMD-SHELL', 'pg_isready -U daily_3006 -d daily_3006'], interval='3s', timeout='3s', retries=20)),
        'mta': dict(image='freshvcf-daily3006-mta:connections-001', **common,
            mem_limit='4g', memswap_limit='4g', cpus=2,
            environment=dict(VF_SECRET_KEY=secret, VF_DB_HOST='postgres', VF_DB_NAME='daily_3006',
                VF_DB_USER='daily_3006', VF_DB_PASSWORD=password, VF_EVIDENCE_ROOT='/runtime',
                VF_MTA_ALLOW_UNSELECTED_STARTUP='1', VF_MTA_DAILY_PUBLICATION='1'),
            volumes=[str(OWNER / 'runtime').replace('\\', '/') + ':/runtime',
                     str(OWNER / 'inputs').replace('\\', '/') + ':/inputs:ro'],
            entrypoint=['gunicorn', 'vectorflow.wsgi:application', '--preload', '--bind', '0.0.0.0:8000',
                        '--workers', '2', '--timeout', '180']),
        'user-service': dict(image=old['Image'], **common, mem_limit='1g', cpus=1,
            entrypoint=['uvicorn', 'apps.asgi:application', '--host', '0.0.0.0', '--port', '10016'],
            environment={**database, 'PGOPTIONS':'-c search_path=identity',
                'DB_PASSWORD_FILE':'/run/secrets/user-service-db-password.enc',
                'USER_SERVICE_RSA_PRIVATE_KEY_PATH':'/run/secrets/user-service-private-key.pem',
                'USER_SERVICE_RSA_PUBLIC_KEY_PATH':'/run/secrets/user-service-public-key.pem',
                'SECRET_KEY':secret, 'SECRET_KEY_FOR_PASSWORD':oldenv['SECRET_KEY_FOR_PASSWORD'],
                'BASE_CLIENT_URL':'http://localhost:3006', 'ALLOWED_SSL':'localhost,127.0.0.1,user-service',
                'MTA_BACKEND_URL':'http://mta:8000', 'MTO_BACKEND_URL':'http://mto:10015',
                'DEBUG':'false', 'PASSWORD_RESET_TIMEOUT':'28800', 'EMAIL_HOST':'',
                'EMAIL_HOST_USER':'', 'EMAIL_HOST_PASSWORD':'',
                'CELERY_BROKER_URL':'redis://redis:6379/0', 'CELERY_RESULT_BACKEND':'redis://redis:6379/0'},
            volumes=[str(private).replace('\\', '/') + ':/run/secrets:ro']),
        'mto': dict(image=json.loads(run('docker','inspect','freshvcf-preview-mto-1'))[0]['Image'],
            **common, mem_limit='1g', cpus=1,
            entrypoint=['uvicorn','MTO_API.asgi:application','--host','0.0.0.0','--port','10015'],
            environment={**database, 'DB_PASSWORD':password, 'PGOPTIONS':'-c search_path=mto',
                'SECRET_KEY':secret, 'REDIS_HOST':'redis', 'REDIS_PORT':'6379', 'DEBUG':'false',
                'CORS_ALLOWED_ORIGINS':'http://localhost:3006','MTO_STAGE7B_ENABLE_DDQ_UI':'false'}),
        'redis': dict(image='redis:7.4-alpine', **common, mem_limit='128m', cpus=.5),
        'frontend': dict(image='freshvcf-daily3006-frontend:connections-001', **common,
            mem_limit='128m', cpus=.5, ports=['127.0.0.1:3006:80']),
    }
    config = dict(name=PROJECT, services=services, networks=dict(daily={}), volumes={'daily-db':{}})
    (OWNER / 'compose.json').write_text(json.dumps(config, indent=2))
    (EVIDENCE / 'ownership.json').write_text(json.dumps(dict(project=PROJECT,
        database='daily_3006', network=PROJECT+'_daily', public_port='127.0.0.1:3006',
        owner=str(OWNER), volumes=[PROJECT+'_daily-db'], selected_run=None,
        copied_business_data=False, credentials='private external configuration'), indent=2))
    print('Created private isolated3006 configuration; no service started or dataset selected')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare','verify-protected'])
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    else:
        before = json.loads((EVIDENCE / 'protected-before.json').read_text())
        after = snapshot()
        (EVIDENCE / 'protected-after.json').write_text(json.dumps(after, indent=2))
        if before != after:
            raise ValueError('Protected service identity/configuration changed')
        print('All protected service identities, start times, configuration and mounts unchanged')
