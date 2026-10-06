"""Build3006 from accepted runtime assets plus the explicit connection diff."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OWNER = Path('D:/freshvcf-build/daily-3006')
EVIDENCE = Path('D:/freshvcf-build/evidence/daily-publication-3006-20261006-001')
BASE = 'sha256:1192c35d8d1789dc1d2dc8a240ad71b2afc43eb2fd54b5e753730c10c85ad9ed'


def call(*args):
    subprocess.run(args, check=True)


def frontend():
    build = OWNER/'build'/'frontend-002'
    build.mkdir(exist_ok=False)
    call('docker','cp','freshvcf-preview-frontend-1:/usr/share/nginx/html',str(build/'html'))
    changes = []
    for path in (build/'html').rglob('*.js'):
        before = path.read_bytes()
        after = before.replace(b'ws://localhost:3005', b'ws://localhost:3006')
        if before != after:
            path.write_bytes(after)
            changes.append(dict(file=str(path.relative_to(build)), occurrences=before.count(b'ws://localhost:3005'),
                before=hashlib.sha256(before).hexdigest(),after=hashlib.sha256(after).hexdigest()))
    if not changes:
        raise ValueError('Expected accepted frontend websocket binding was not found')
    shutil.copyfile(ROOT/'infrastructure/docker/frontend-nginx.conf',build/'default.conf')
    image = json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-frontend-1']))[0]['Image']
    call('docker','image','tag',image,'freshvcf-daily3006-frontend:accepted-base')
    (build/'Dockerfile').write_text('FROM freshvcf-daily3006-frontend:accepted-base\nCOPY html /usr/share/nginx/html\nCOPY default.conf /etc/nginx/conf.d/default.conf\n')
    call('docker','build','-t','freshvcf-daily3006-frontend:connections-001',str(build))
    (EVIDENCE/'frontend-build.json').write_text(json.dumps(dict(base=image,changes=changes,
        contract='Only compiled websocket host changed from3005 to3006; same application assets'),indent=2))


def mta(tag):
    build = OWNER/'build'/('mta-'+tag)
    build.mkdir(exist_ok=False)
    tracked = subprocess.check_output(['git','diff','--name-only','d17925c','--','mta','vectorflow'],cwd=ROOT,text=True).splitlines()
    new = subprocess.check_output(['git','ls-files','--others','--exclude-standard','mta','vectorflow'],cwd=ROOT,text=True).splitlines()
    files = sorted(set(tracked+new))
    manifest = {}
    for name in files:
        path = ROOT/name
        if not path.is_file() or path.suffix != '.py':
            raise ValueError('Unexpected overlay file: '+name)
        dest = build/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest)
        manifest[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    call('docker','image','tag',BASE,'freshvcf-daily3006-mta:accepted-base')
    (build/'Dockerfile').write_text('FROM freshvcf-daily3006-mta:accepted-base\n' + ''.join(
        'COPY --chown=10001:10001 '+name+' /app/'+name+'\n' for name in files))
    call('docker','build','-t','freshvcf-daily3006-mta:'+tag,str(build))
    (EVIDENCE/('mta-build-'+tag+'.json')).write_text(json.dumps(dict(base=BASE,files=manifest),indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',choices=['frontend','mta'])
    parser.add_argument('--tag',default='connections-001')
    args=parser.parse_args()
    frontend() if args.target=='frontend' else mta(args.tag)
