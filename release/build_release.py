"""Build four application images from one clean committed production export.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

from release.export import export
from release.build_mta import build as build_mta


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def installation_files(source, output, proof, public_cipher, repository=None):
    """Use the normal runbook with these exact newly built image identities."""
    images={name:row['id'] for name,row in proof['images'].items()}
    locks=json.loads((source/'release/images.lock.json').read_text())
    for name in ('postgres','redis'):
        reference=locks[name]
        checked=subprocess.run(['docker','image','inspect',reference],capture_output=True,text=True)
        if checked.returncode:
            subprocess.run(['docker','pull','--platform','linux/amd64',reference],check=True)
            checked=subprocess.run(['docker','image','inspect',reference],check=True,capture_output=True,text=True)
        inspected=json.loads(checked.stdout)[0]
        if (inspected['Architecture'],inspected['Os'])!=('amd64','linux'):
            raise ValueError('Unexpected platform: '+name)
        images[name]=inspected['Id']
    services={name:{'image':image,'pull_policy':'never'} for name,image in images.items()}
    for name,component in (('mta-install','mta'),('auth-install','auth'),('mto-install','mto'),('provision','mta')):
        services[name]={'image':images[component],'pull_policy':'never'}
    # JSON is a YAML subset understood by Docker Compose.
    (output/'source-build-images.yaml').write_text(json.dumps({'x-restriction':proof['restriction'],'services':services},indent=2)+'\n')
    release={'restriction':proof['restriction'],'schema':'vectorflow-source-build-install-v1',
        'code_commit':proof['source_commit'],
        'component_sources':{name:proof['source_commit'] for name in proof['images']},
        'images':images,'native_manifest_sha256':proof['native_sha256'],
        'mta_source_manifest_sha256':proof['source_sha256'],
        'public_origin':proof['public_origin'],'websocket_origin':proof['websocket_origin'],
        'public_client_cipher_key':public_cipher,
        'optional_raw_inputs':json.loads((source/'release/windows-final-release.json').read_text())['optional_raw_inputs'],
        'verification_boundary':'Built from Git; blank and connected runtime acceptance remain separate.'}
    (output/'installation-release.json').write_text(json.dumps(release,indent=2)+'\n')
    values={'VF_RELEASE':proof['source_commit'],'VF_NATIVE_RELEASE_COMMIT':proof['source_commit'],
        'VF_NATIVE_RELEASE_SHA256':proof['native_sha256'],'VF_SOURCE_MANIFEST_SHA256':proof['source_sha256'],
        'VF_PUBLIC_URL':proof['public_origin'],'VF_PUBLIC_WS_URL':proof['websocket_origin'],
        'VF_HTTP_PORT':str(urlsplit(proof['public_origin']).port or (443 if proof['public_origin'].startswith('https:') else 80)),
        'VF_CLIENT_CIPHER_KEY':public_cipher}
    lines=(source/'release/.env.example').read_text().splitlines()
    lines=[line.split('=',1)[0]+'='+values[line.split('=',1)[0]]
        if '=' in line and line.split('=',1)[0] in values else line for line in lines]
    (output/'operator.env.template').write_text('# '+proof['restriction']+'\n'+'\n'.join(lines)+'\n')
    proof['installation_files']={name:digest(output/name) for name in
        ('source-build-images.yaml','installation-release.json','operator.env.template')}
    if repository is not None:
        # Operator scripts stay outside all application images. Copy committed
        # bytes, never an uncommitted workstation helper.
        for name in ('release/run_daily.ps1', 'release/CSV_DAILY_RUN.md'):
            raw = subprocess.check_output(['git','-C',str(repository),'show',proof['source_commit']+':'+name])
            target = output/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            proof['installation_files'][name] = digest(target)


def wheels(source, destination):
    """Download only independently hash-pinned wheels, or verify a cache."""
    destination.mkdir(exist_ok=True)
    pins=json.loads((source/'release/mta-wheels.lock.json').read_text())['files']
    expected={row['filename'] for row in pins}
    if any(p.name not in expected for p in destination.iterdir()):
        raise ValueError('Wheel cache contains undeclared files')
    for row in pins:
        target=destination/row['filename']
        if not target.exists():
            with urlopen('https://pypi.org/pypi/'+row['name']+'/'+row['version']+'/json',timeout=30) as response:
                record=json.load(response)
            candidates=[item for item in record['urls'] if item['filename']==row['filename'] and item['digests']['sha256']==row['sha256']]
            if len(candidates)!=1:raise ValueError('Pinned wheel unavailable: '+row['filename'])
            with urlopen(candidates[0]['url'],timeout=60) as response:
                data=response.read(row['bytes']+1)
            if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
                raise ValueError('Downloaded wheel identity differs: '+row['filename'])
            target.write_bytes(data)
        if target.stat().st_size!=row['bytes'] or digest(target)!=row['sha256']:
            raise ValueError('Wheel cache identity differs: '+row['filename'])
    return destination


def build(repository, revision, output, *, image_prefix, public_origin, websocket_origin,
          public_cipher, wheelhouse=None):
    repository=Path(repository).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Choose a new external build output; never overwrite')
    if repository==output or repository in output.parents:raise ValueError('Build output must be outside source')
    if subprocess.check_output(['git','-C',str(repository),'status','--porcelain']):
        raise ValueError('Commit or preserve source changes before building')
    if not re.fullmatch(r'[a-z0-9][a-z0-9./_-]{0,120}',image_prefix):raise ValueError('Invalid image prefix')
    origin=urlsplit(public_origin);ws=urlsplit(websocket_origin)
    if origin.scheme not in ('http','https') or not origin.hostname or origin.path not in ('','/'):
        raise ValueError('Explicit HTTP/HTTPS origin required')
    if ws.scheme!=('wss' if origin.scheme=='https' else 'ws') or ws.netloc!=origin.netloc or ws.path not in ('','/'):
        raise ValueError('WebSocket origin must match the application origin')
    if len(public_cipher.encode()) not in (16,24,32):raise ValueError('Public client cipher must match auth')
    output.mkdir()
    proof={'restriction':__doc__.splitlines()[2], 'status':'BUILDING', 'runtime_started':False,
           'public_origin':public_origin,'websocket_origin':websocket_origin,'images':{},
           'qualification':'Build/file/config verification is separate from blank/connected runtime acceptance.'}
    def save():
        (output/'build-receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
    save()
    source=output/'export'
    record=export(repository,revision,source)
    config=json.loads((source/'frontend/tsconfig.json').read_text())
    extends=config.get('extends')
    if extends and (not extends.startswith('./') or not (source/'frontend'/extends).is_file()):
        raise ValueError('Frontend TypeScript parent configuration absent from committed export')
    commit=record['source_commit'];tag=commit[:12]
    proof.update(source_commit=commit,source_sha256=digest(source/'release-source.json'),
                 native_sha256=digest(source/'release-native-source.json'))
    save()
    env={**os.environ,'DOCKER_BUILDKIT':'0'}
    initial_free=shutil.disk_usage(output).free
    if initial_free<20*1024**3:raise ValueError('Less than 20GiB free before build')
    proof['storage_monitor']={'initial_free_bytes':initial_free,'abort_consumption_bytes':14*1024**3,
        'minimum_free_bytes':20*1024**3,'qualification':'Conservative host free-space observation, not a hard Docker quota'}
    def run(arguments, **kwargs):
        component=proof.get('active_component','mta')
        logfile=output/(component+'-build.log')
        started=time.monotonic()
        with logfile.open('a',encoding='utf-8') as log:
            process=subprocess.Popen(arguments,env=kwargs.get('env',env),stdout=log,stderr=subprocess.STDOUT)
            try:
                while process.poll() is None:
                    free=shutil.disk_usage(output).free
                    if free<20*1024**3 or initial_free-free>14*1024**3:
                        raise ValueError('Storage safety threshold reached; stop/preserve')
                    if time.monotonic()-started>1800:raise TimeoutError(component+' build deadline')
                    time.sleep(1)
            except BaseException:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
                # Classic-builder RUN IDs originate only in this exact call's log.
                # Stop them if cancellation left one running; never touch other IDs.
                for cid in set(re.findall(r'Running in ([0-9a-f]{12,64})',logfile.read_text())):
                    state=subprocess.run(['docker','inspect',cid],capture_output=True,text=True)
                    if state.returncode==0 and json.loads(state.stdout)[0]['State']['Running']:
                        subprocess.run(['docker','stop','--time','5',cid],check=True,capture_output=True)
                raise
            return subprocess.CompletedProcess(arguments,process.returncode)
    try:
        proof['active_component']='mta';save()
        wheelroot=Path(wheelhouse).resolve() if wheelhouse else output/'wheels'
        wheels(source,wheelroot)
        image=image_prefix+'/mta:'+tag
        build_mta(source,output/'mta-context',wheelroot,commit=commit,
            source_sha256=proof['source_sha256'],native_sha256=proof['native_sha256'],image=image,runner=run,
            owner='clean-git-build-'+tag)
        proof['images']['mta']={'tag':image};save()
        for component in ('auth','mto','frontend'):
            proof['active_component']=component;save()
            image=image_prefix+'/'+component+':'+tag
            command=['docker','build','--pull=false','--rm=false',
                '--label','vectorflow.owner=clean-git-build-'+tag,
                '-f',str(source/'release'/ (component+'.Dockerfile')),'-t',image]
            if component=='frontend':
                for key,value in {'REACT_APP_API_HOST':'/','REACT_APP_VF_API_HOST_MTO':'/api/mto',
                    'REACT_APP_WS_API_HOST':websocket_origin,'REACT_APP_SECRET_KEY':public_cipher,
                    'REACT_APP_AG_GRID_LICENSE_KEY':''}.items():
                    command.extend(['--build-arg',key+'='+value])
            command.append(str(source))
            result=run(command)
            if result.returncode:raise ValueError(component+' build failed; preserve logs/attempts')
            if component=='frontend' and 'TS5083:' in (output/'frontend-build.log').read_text():
                raise ValueError('Frontend build lost a required TypeScript configuration')
            proof['images'][component]={'tag':image};save()
        for component,value in proof['images'].items():
            inspected=json.loads(subprocess.check_output(['docker','image','inspect',value['tag']]))[0]
            value.update(id=inspected['Id'],architecture=inspected['Architecture'],os=inspected['Os'])
            if (value['architecture'],value['os'])!=('amd64','linux'):raise ValueError('Unexpected image platform')
        installation_files(source,output,proof,public_cipher,repository)
        proof['status']='BUILT_FROM_ONE_COMMITTED_EXPORT_RUNTIME_ACCEPTANCE_PENDING'
        proof.pop('active_component',None);save()
        return proof
    except BaseException as error:
        proof.update(status='FAILED_PRESERVED',error=str(error));save()
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--revision',required=True)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--image-prefix',default='vectorflow-git')
    p.add_argument('--public-origin',required=True)
    p.add_argument('--websocket-origin',required=True)
    p.add_argument('--public-client-cipher',required=True)
    p.add_argument('--wheelhouse',type=Path)
    a=p.parse_args()
    result=build(a.repository,a.revision,a.output,image_prefix=a.image_prefix,
        public_origin=a.public_origin,websocket_origin=a.websocket_origin,
        public_cipher=a.public_client_cipher,wheelhouse=a.wheelhouse)
    print(json.dumps(result,indent=2))
