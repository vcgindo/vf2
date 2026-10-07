"""Install the explicitly approved 3006 catalogue/run hierarchy, without selection."""
import hashlib
import json
from pathlib import Path
import subprocess
from daily_stack_setup import OWNER, EVIDENCE, PROJECT

RUN = '63c71fa7-944d-4547-a80f-2316a580d3c7'
DIGEST = 'f14806c1397661e2380ae59282db86bd1b5ca629351a61e73a3b09a407a2388b'
CATALOGUE = '18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356'


def immutable(path, raw):
    if path.exists():
        if path.read_bytes() != raw: raise ValueError('Existing access artifact differs')
    else:
        with path.open('xb') as stream: stream.write(raw)


def main():
    receipt = EVIDENCE/'smoke-access-applied-001.json'
    if receipt.exists(): raise ValueError('Actor binding already applied; do not replace its evidence')
    catalogue = (EVIDENCE/'proposed-smoke-permissions-001.json').read_bytes()
    assert hashlib.sha256(catalogue).hexdigest() == CATALOGUE
    plan = json.loads((EVIDENCE/'proposed-smoke-access-binding-001.json').read_text())
    assert plan['run_id'] == RUN and plan['output_digest'] == DIGEST
    manifest = dict(version='fresh-presentation-hierarchy-v1',
        role='presentation-only-retained-hierarchy', catalogue_sha256=CATALOGUE,
        allowed_fields=plan['allowed_fields'], catalogue_counts=dict(products=200, locations=20),
        publications=[dict(run_id=RUN,business_date='2026-06-06',output_digest=DIGEST)],
        authorization='Direct human approval 6 October2026: both pending3006 decisions exactly as proposed; presentation-only; preserve seal and3005.')
    raw = (json.dumps(manifest,indent=2)+'\n').encode()
    hierarchy_sha = hashlib.sha256(raw).hexdigest()
    immutable(OWNER/'inputs'/'smoke-permissions-v1.json', catalogue)
    immutable(OWNER/'inputs'/'smoke-hierarchy-day1-v1.json', raw)
    immutable(EVIDENCE/'smoke-hierarchy-day1-v1.json', raw)
    path = OWNER/'compose.json'
    config = json.loads(path.read_text())
    assert config['name'] == PROJECT
    env = config['services']['mta']['environment']
    assert not env.get('VF_MTA_PUBLISHED_RUN') and not env.get('VF_MTA_PUBLISHED_DIGEST')
    changes = dict(VF_MTA_PERMISSIONS_FILE='/inputs/smoke-permissions-v1.json',
        VF_MTA_PERMISSIONS_SHA256=CATALOGUE,
        VF_MTA_HIERARCHY_FILE='/inputs/smoke-hierarchy-day1-v1.json',
        VF_MTA_HIERARCHY_SHA256=hierarchy_sha)
    for key,value in changes.items():
        assert not env.get(key) or env[key] == value
    env.update(changes)
    path.write_text(json.dumps(config,indent=2))
    # Only the two existing test actors' MTA product/location grants change.
    script = '''import os,json,hashlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE','apps.settings')
import django;django.setup()
from django.db import transaction,connection
from api.models import User,User_Application_Product_Permission as P,User_Application_Location_Permission as L
def fingerprint():
 return hashlib.sha256(json.dumps(list(User.all_objects.order_by('id').values()),sort_keys=True,default=str).encode()).hexdigest()
with transaction.atomic():
 with connection.cursor() as c:
  c.execute('SELECT current_database(),current_schema()')
  assert c.fetchone()==('daily_3006','identity')
 users=list(User.all_objects.filter(id__in=[2,3]).order_by('id').values('id','email','is_active','is_admin'))
 assert [(u['id'],u['email'],u['is_active'],u['is_admin']) for u in users]==[(2,'stage2.broad@vectorflow.local',True,False),(3,'stage2.restricted@vectorflow.local',True,False)]
 before=fingerprint(); result={}
 for model,field,grants in [(P,'productfilter_id',{2:71001,3:71003}),(L,'locationfilter_id',{2:72001,3:72003})]:
  other=list(model.objects.exclude(user_id__in=[2,3],application_id=2).order_by('pk').values())
  old=list(model.objects.filter(user_id__in=[2,3],application_id=2).order_by('pk').values())
  model.objects.filter(user_id__in=[2,3],application_id=2).delete()
  for actor,value in grants.items():model.objects.create(user_id=actor,application_id=2,**{field:value})
  assert other==list(model.objects.exclude(user_id__in=[2,3],application_id=2).order_by('pk').values())
  result[model.__name__]={'before':old,'after':list(model.objects.filter(user_id__in=[2,3],application_id=2).order_by('pk').values())}
 assert before==fingerprint()
 print(json.dumps(dict(grants=result,account_credential_fingerprint_unchanged=True,other_grants_unchanged=True)))
'''
    response = subprocess.run(['docker','exec','-i',PROJECT+'-user-service-1','python','-'],
        input=script,text=True,encoding='utf-8',capture_output=True)
    if response.returncode:
        raise RuntimeError(response.stderr)
    result=json.loads(response.stdout)
    result.update(changes)
    result['selected']=False
    with receipt.open('x') as stream: json.dump(result,stream,indent=2)
    print(json.dumps(dict(status='ACCESS_BOUND_NOT_SELECTED',permissions_sha=CATALOGUE,
        hierarchy_sha=hierarchy_sha,receipt=str(receipt))))


if __name__ == '__main__': main()
