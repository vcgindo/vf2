"""Package one explicit immutable Git tree; never calculate or serve."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

BASE_TAG = 'freshvcf-cohort4:operational-004'
BASE_ID = 'sha256:0a8ca22f471386ec6ce8dd3e59cd3fb5b1f5e56cfc525e32a6f30e3a2adb5dff'
ROOT = Path(__file__).resolve().parents[2]
ROOTS = ['mta','vectorflow','baseline','parity','user-service/api_gateway',
         'tools/cohort6_actions.py','tools/cohort6_settings.py',
         'tools/cohort6_bind_day.py','tools/cohort3_database_router.py',
         'packaging/cohort6/execute-approved.sh']

def output(*args):
    return subprocess.check_output(args, cwd=ROOT)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree',required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--tag',required=True)
    args=parser.parse_args()
    source=output('git','rev-parse',args.tree+'^{tree}').decode().strip()
    dest=args.destination.resolve();tag=args.tag
    evidence=Path('D:/freshvcf-build/evidence').resolve()
    if not dest.is_relative_to(evidence) or dest.exists():
        raise ValueError('New package destination beneath owned evidence required')
    base=json.loads(output('docker','image','inspect',BASE_TAG))[0]
    assert base['Id']==BASE_ID and base['Architecture']=='amd64'
    dest.mkdir(parents=True)
    context=dest/'context'; context.mkdir()
    rows=[]
    for name in output('git','ls-tree','-r','--name-only',source,'--',*ROOTS).decode().splitlines():
        raw=output('git','show',source+':'+name)
        target=name.replace('user-service/api_gateway/','api_gateway/',1)
        path=context/'app'/target;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        rows.append(dict(path='/app/'+target,sha256=hashlib.sha256(raw).hexdigest()))
    (context/'source-manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    dockerfile='FROM '+BASE_TAG+'\nCOPY app/ /app/\nCOPY source-manifest.json /opt/fresh/cohort6-source-manifest.json\nENV VF_MTA_OPERATIONAL_POLICY="" VF_MTA_OPERATIONAL_RECEIPT=""\n'
    (context/'Dockerfile').write_text(dockerfile,encoding='utf-8')
    p=subprocess.run(['docker','build','--pull=false','--network=none','-t',tag,str(context)],capture_output=True,text=True)
    (dest/'build.log').write_text(p.stdout+p.stderr,encoding='utf-8');p.check_returncode()
    image=json.loads(output('docker','image','inspect',tag))[0]['Id']
    code="""import hashlib,json,importlib.metadata as m,subprocess,shutil
from pathlib import Path
rows=json.loads(Path('/opt/fresh/cohort6-source-manifest.json').read_text())
for row in rows: assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
import django,rest_framework,rest_framework_simplejwt,psycopg,psycopg2,Crypto,requests
tools={n:dict(path=shutil.which(n),sha256=hashlib.sha256(Path(shutil.which(n)).read_bytes()).hexdigest()) for n in ('python','pg_dump','pg_restore')}
print(json.dumps(dict(source_files=len(rows),dependencies={n:m.version(n) for n in ('Django','djangorestframework','djangorestframework-simplejwt','psycopg','psycopg2-binary','pycryptodome','requests')},tools=tools,pg_dump=subprocess.check_output(['pg_dump','--version'],text=True).strip(),pg_restore=subprocess.check_output(['pg_restore','--version'],text=True).strip())))
"""
    audit=json.loads(output('docker','run','--rm','--network','none','--memory','4g','--cpus','2','--restart','no','--read-only','--entrypoint','python',image,'-c',code))
    receipt=dict(status='PINNED_PACKAGE_PASS',source_tree=source,image=image,tag=tag,base=BASE_ID,source_manifest_sha256=hashlib.sha256((context/'source-manifest.json').read_bytes()).hexdigest(),**audit)
    (dest/'package.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))

if __name__=='__main__': main()
