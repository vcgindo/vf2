"""Package only the delivered Cohort5 revision; never calculate or serve."""
import hashlib
import json
from pathlib import Path
import subprocess

COMMIT = 'c5a3e9c80c930b35e22671ba1488869977199376'
BASE_TAG = 'freshvcf-cohort4:operational-004'
BASE_ID = 'sha256:0a8ca22f471386ec6ce8dd3e59cd3fb5b1f5e56cfc525e32a6f30e3a2adb5dff'
TAG = 'freshvcf-cohort6:preparation-001'
ROOT = Path(__file__).resolve().parents[2]
DEST = Path('D:/freshvcf-build/evidence/cohort6-20261009-001/package')
ROOTS = ['mta','vectorflow','baseline','parity','user-service/api_gateway']

def output(*args):
    return subprocess.check_output(args, cwd=ROOT)

def main():
    if DEST.exists(): raise ValueError('One new package destination required; never overwrite proof')
    base=json.loads(output('docker','image','inspect',BASE_TAG))[0]
    assert base['Id']==BASE_ID and base['Architecture']=='amd64'
    DEST.mkdir(parents=True)
    context=DEST/'context'; context.mkdir()
    rows=[]
    for name in output('git','ls-tree','-r','--name-only',COMMIT,'--',*ROOTS).decode().splitlines():
        raw=output('git','show',COMMIT+':'+name)
        target=name.replace('user-service/api_gateway/','api_gateway/',1)
        path=context/'app'/target;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        rows.append(dict(path='/app/'+target,sha256=hashlib.sha256(raw).hexdigest()))
    (context/'source-manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    dockerfile='FROM '+BASE_TAG+'\nCOPY app/ /app/\nCOPY source-manifest.json /opt/fresh/cohort6-source-manifest.json\nENV VF_MTA_OPERATIONAL_POLICY="" VF_MTA_OPERATIONAL_RECEIPT=""\n'
    (context/'Dockerfile').write_text(dockerfile,encoding='utf-8')
    p=subprocess.run(['docker','build','--pull=false','--network=none','-t',TAG,str(context)],capture_output=True,text=True)
    (DEST/'build.log').write_text(p.stdout+p.stderr,encoding='utf-8');p.check_returncode()
    image=json.loads(output('docker','image','inspect',TAG))[0]['Id']
    code="""import hashlib,json,importlib.metadata as m,subprocess,shutil
from pathlib import Path
rows=json.loads(Path('/opt/fresh/cohort6-source-manifest.json').read_text())
for row in rows: assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
import django,rest_framework,rest_framework_simplejwt,psycopg,psycopg2,Crypto,requests
tools={n:dict(path=shutil.which(n),sha256=hashlib.sha256(Path(shutil.which(n)).read_bytes()).hexdigest()) for n in ('python','pg_dump','pg_restore')}
print(json.dumps(dict(source_files=len(rows),dependencies={n:m.version(n) for n in ('Django','djangorestframework','djangorestframework-simplejwt','psycopg','psycopg2-binary','pycryptodome','requests')},tools=tools,pg_dump=subprocess.check_output(['pg_dump','--version'],text=True).strip(),pg_restore=subprocess.check_output(['pg_restore','--version'],text=True).strip())))
"""
    audit=json.loads(output('docker','run','--rm','--network','none','--memory','4g','--cpus','2','--restart','no','--read-only','--entrypoint','python',image,'-c',code))
    receipt=dict(status='PINNED_PACKAGE_PASS',commit=COMMIT,image=image,tag=TAG,base=BASE_ID,source_manifest_sha256=hashlib.sha256((context/'source-manifest.json').read_bytes()).hexdigest(),**audit)
    (DEST/'package.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))

if __name__=='__main__': main()
