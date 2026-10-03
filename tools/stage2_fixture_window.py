"""Prepare/prove/restore the expressly authorized MTA-only fixture window."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stage2_vm_dataset import DEST,sha
from tools.stage2_vm_load import DB
from tools.stage2_vm_contract import atomic,sealed
from tools.preview_snapshot import snapshot

COMPOSE=['docker','compose','--env-file','D:/freshvcf-build/preview/preview.env','-f',str(ROOT/'compose.preview.yaml')]
FIXTURE_IMAGE='freshvcf-stage2-fixture:20261003'
MTA='freshvcf-preview-mta-1'
WINDOW=DEST/'fixture-window-001'


def inspect(name):
    return json.loads(subprocess.check_output(['docker','inspect',name]))[0]


def runtime(item):
    config=item['Config'];host=item['HostConfig']
    return dict(image=item['Image'],environment_sha256=hashlib.sha256(json.dumps(sorted(config['Env'])).encode()).hexdigest(),
        command=config['Cmd'],entrypoint=config['Entrypoint'],mounts=sorted([m['Source'],m['Destination'],m['RW']] for m in item['Mounts']),
        networks=sorted(item['NetworkSettings']['Networks']),memory=host['Memory'],memory_swap=host['MemorySwap'],cpus=host['NanoCpus'],restart=host['RestartPolicy'],ports=host['PortBindings'])


def protected():
    names=['freshvcf-preview-'+name+'-1' for name in ('user-service','frontend','mto','redis')]
    return dict(accepted=snapshot(),preview={name:dict(id=inspect(name)['Id'],runtime=runtime(inspect(name))) for name in names})


def ready():
    script="import urllib.request;print(urllib.request.urlopen('http://mta:8000/readyz',timeout=10).read().decode())"
    for attempt in range(30):
        call=subprocess.run(['docker','exec','freshvcf-preview-user-service-1','python','-c',script],capture_output=True,text=True)
        if call.returncode==0:
            value=json.loads(call.stdout)
            if value.get('ready'):return value
        time.sleep(2)
    raise RuntimeError('MTA readiness not established')


def verify_restoration_plan():
    original=inspect(MTA)
    rendered=json.loads(subprocess.check_output(COMPOSE+['-f',str(DEST/'compose.restore.json'),'config','--format','json']))
    service=rendered['services']['mta']
    image=json.loads(subprocess.check_output(['docker','image','inspect',service['image']]))[0]
    image_env=dict(v.split('=',1) for v in image['Config']['Env'])
    image_env.update({k:str(v) for k,v in service['environment'].items()})
    candidate=dict(image=image['Id'],environment_sha256=hashlib.sha256(json.dumps(sorted(k+'='+v for k,v in image_env.items())).encode()).hexdigest(),
        command=service.get('command',image['Config']['Cmd']),entrypoint=service.get('entrypoint',image['Config'].get('Entrypoint')),
        mounts=sorted([v['source'],v['target'],not v.get('read_only',False)] for v in service['volumes']),
        networks=sorted(rendered['networks'][n]['name'] for n in service['networks']),
        memory=int(service['mem_limit']),memory_swap=int(service['memswap_limit']),cpus=int(float(service['cpus'])*1000000000),
        restart=dict(Name=service.get('restart','no'),MaximumRetryCount=0),ports={})
    if service.get('ports') or candidate!=runtime(original):raise ValueError('Rendered restoration plan does not reproduce original runtime')
    return dict(status='PASS',runtime=candidate)


def prepare():
    manifest,manifest_sha=sealed(DEST)
    final=json.loads((DEST/'consumer-publication.json').read_text())
    scope=json.loads((DEST/'fixture-scope-plan.json').read_text())
    actors=json.loads((DEST/'accounts-create.json').read_text())['actors']
    freeze=json.loads((DEST/'freeze-receipt.json').read_text())
    fixture_image=json.loads(subprocess.check_output(['docker','image','inspect',FIXTURE_IMAGE]))[0]['Id']
    policy=dict(version='legacy-ui-fixture-v1',identity=manifest['identity'],database=DB,run_id=final['run_id'],
        business_date='2026-04-07',manifest_sha256=manifest_sha,consumer_publication=final,
        freeze_digest=freeze['digest'],permissions_sha256=scope['catalogue_sha256'],image_sha256=fixture_image,actors=[])
    for actor in actors:
        kind='restricted' if 'restricted' in actor['email'] else 'broad'
        policy['actors'].append(dict(id=actor['id'],email=actor['email'],**scope[kind]))
    atomic(DEST/'fixture-serving.json',policy)
    env={name:'' for name in ('VF_MTA_PUBLISHED_RUN','VF_MTA_PUBLISHED_DIGEST','VF_MTA_HIERARCHY_FILE','VF_MTA_HIERARCHY_SHA256',
        'VF_MTA_TERMINAL_FILE','VF_MTA_TERMINAL_SHA256','VF_MTA_EXCESS_HISTORY_FILE','VF_MTA_EXCESS_HISTORY_SHA256')}
    env.update(VF_DB_NAME=DB,VF_MTA_ACTIONS_ENABLED='0',VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY='0',
        VF_MTA_FIXTURE_FILE='/fixture/fixture-serving.json',VF_MTA_FIXTURE_SHA256=sha(DEST/'fixture-serving.json'),
        VF_MTA_PERMISSIONS_FILE='/fixture/fixture-permissions.json',VF_MTA_PERMISSIONS_SHA256=scope['catalogue_sha256'])
    atomic(DEST/'compose.fixture.json',dict(services=dict(mta=dict(image=fixture_image,environment=env,
        volumes=[str(DEST/name)+':/fixture/'+name+':ro' for name in ('fixture-serving.json','fixture-permissions.json')]))))
    original=inspect(MTA)
    if dict(v.split('=',1) for v in original['Config']['Env']).get('VF_DB_NAME')!='freshvcf':raise ValueError('Normal baseline not selected')
    atomic(DEST/'compose.restore.json',dict(services=dict(mta=dict(image=original['Image']))))
    atomic(DEST/'restoration-preflight.json',verify_restoration_plan())
    print('Prepared explicit fixture and exact-image restoration configuration')


def compose(file):
    call=subprocess.run(COMPOSE+['-f',str(DEST/file),'up','-d','--no-deps','--force-recreate','mta'],capture_output=True,text=True)
    WINDOW.mkdir(exist_ok=True)
    (WINDOW/(file+'.log')).write_text(call.stdout+call.stderr,encoding='utf-8')
    call.check_returncode()


def accounts(operation):
    subprocess.run([sys.executable,str(ROOT/'tools/stage2_fixture_accounts.py'),operation],check=True)
    WINDOW.mkdir(exist_ok=True)
    (WINDOW/('accounts-'+operation+'.json')).write_bytes((DEST/('accounts-'+operation+'.json')).read_bytes())


def restore():
    for attempt in range(3):
        try:
            accounts('disable');break
        except Exception:
            if attempt==2:
                # Never leave the fixture listener exposed after its controlled
                # window if authentication storage cannot disable its actors.
                subprocess.run(['docker','stop',MTA],check=True)
                raise RuntimeError('Fixture stopped; account disable and normal restoration require recovery')
            time.sleep(2)
    compose('compose.restore.json')
    result=ready()
    before=json.loads((WINDOW/'window-before.json').read_text())
    if runtime(inspect(MTA))!=before['mta']:raise ValueError('Restored MTA configuration differs')
    if protected()!=before['protected']:raise ValueError('Protected runtime/publication changed')
    if result!=before['ready']:raise ValueError('Restored admission identity differs')
    script=r'''
import os,json,base64,requests
from Crypto.Cipher import AES
proof=[]
for item in json.load(open('/run/secrets/stage2-fixture-accounts.json')).values():
 iv=os.urandom(16)
 cipher=AES.new(os.environ['SECRET_KEY_FOR_PASSWORD'].encode(),AES.MODE_CTR,nonce=b'',initial_value=int.from_bytes(iv,'big'))
 encrypted=base64.b64encode(iv+cipher.encrypt(item['password'].encode())).decode()
 response=requests.post('http://frontend/api/user/login/',headers={'Host':'localhost:3005'},json={'email':item['email'],'password':encrypted},timeout=60)
 assert response.status_code in (400,401,403),response.status_code
 proof.append({'actor':item['email'],'status':response.status_code,'login_denied':True})
print(json.dumps(proof))
'''
    disabled=subprocess.run(['docker','exec','-i','freshvcf-preview-user-service-1','python','-'],input=script,text=True,capture_output=True)
    disabled.check_returncode()
    atomic(WINDOW/'disabled-login-proof.json',json.loads(disabled.stdout))
    atomic(WINDOW/'window-restoration.json',dict(status='PASS',ready=result,mta=runtime(inspect(MTA)),protected_unchanged=True,fixture_accounts_disabled=True))
    print('Normal June17 MTA restored; protected resources and admission unchanged')


def prove():
    if WINDOW.exists():raise ValueError('Preserve window attempt; inspect before a new identity')
    verify_restoration_plan()
    WINDOW.mkdir()
    for name in ('fixture-serving.json','compose.fixture.json','compose.restore.json'):
        (WINDOW/name).write_bytes((DEST/name).read_bytes())
    atomic(WINDOW/'window-before.json',dict(mta=runtime(inspect(MTA)),protected=protected(),ready=ready(),
        restoration_command=COMPOSE+['-f',str(DEST/'compose.restore.json'),'up','-d','--no-deps','--force-recreate','mta']))
    try:
        compose('compose.fixture.json')
        admission=ready();atomic(WINDOW/'fixture-readiness.json',admission)
        accounts('enable')
        call=subprocess.run(['docker','exec','-i','freshvcf-preview-user-service-1','python','-'],
            input=(ROOT/'tools/stage2_fixture_probe.py').read_text(),capture_output=True,text=True)
        (WINDOW/'authenticated-fixture-proof.json').write_text(call.stdout,encoding='utf-8')
        (WINDOW/'authenticated-fixture-proof.stderr.txt').write_text(call.stderr,encoding='utf-8')
        call.check_returncode()
        print('Representative authenticated fixture proof passed')
    finally:
        restore()


def serve():
    """Bounded browser verification lease; retain only explicit successful proof."""
    if WINDOW.exists():raise ValueError('Preserve window attempt; use a new identity')
    verify_restoration_plan()
    WINDOW.mkdir()
    for name in ('fixture-serving.json','compose.fixture.json','compose.restore.json'):
        (WINDOW/name).write_bytes((DEST/name).read_bytes())
    before=dict(mta=runtime(inspect(MTA)),protected=protected(),ready=ready())
    atomic(WINDOW/'window-before.json',before)
    retained=False
    try:
        compose('compose.fixture.json')
        admission=ready();atomic(WINDOW/'fixture-readiness.json',admission)
        accounts('enable')
        print('Fixture ready for browser verification; restore automatically after 25 minutes without successful proof',flush=True)
        deadline=time.monotonic()+1500
        while time.monotonic()<deadline:
            proof=WINDOW/'visible-data-proof.json'
            if proof.exists():
                value=json.loads(proof.read_text())
                if value.get('status')!='PASS':raise ValueError('Visible-data verification failed')
                if set(value.get('pages',{}))!={'RRR','BPR','BTR','DBM'}:raise ValueError('Four-page proof required')
                if any(not page.get('visible_rows') for page in value['pages'].values()):raise ValueError('Visible records required')
                if not value.get('real_login') or not value.get('filter_verified'):raise ValueError('Login/filter proof required')
                security=json.loads((WINDOW/'visible-security-proof.json').read_text())
                if security.get('status')!='PASS' or not security.get('actions_disabled'):raise ValueError('Fixture security proof required')
                if protected()!=before['protected']:raise ValueError('Protected resources changed')
                if ready()!=admission:raise ValueError('Fixture admission changed')
                atomic(WINDOW/'serving-handoff.json',dict(status='SERVING_FOR_HUMAN_INSPECTION',
                    ready=admission,mta=runtime(inspect(MTA)),protected_unchanged=True,
                    restoration='python tools/stage2_fixture_window.py restore --attempt '+WINDOW.name[-3:]))
                retained=True
                print('Four-page proof accepted; fixture remains available on3005',flush=True)
                return
            time.sleep(2)
        raise TimeoutError('Browser verification lease expired')
    finally:
        if not retained:restore()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['prepare','prove','serve','restore'])
    parser.add_argument('--attempt',default='001')
    args=parser.parse_args()
    if not args.attempt.isdigit() or len(args.attempt)!=3:raise ValueError('Three-digit explicit attempt required')
    WINDOW=DEST/('fixture-window-'+args.attempt)
    globals()[args.operation]()
