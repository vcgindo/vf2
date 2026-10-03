"""Authorized fixture-only identities through existing local account models.

No existing actor/grant or authentication contract is changed. New actors are
disabled until the bounded MTA fixture window, and disabled again on exit.
"""
import argparse
import json
from pathlib import Path
import secrets
import subprocess

ROOT=Path(__file__).resolve().parents[1]
DATA=Path('D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002')
SECRET=Path('D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json')

SCRIPT=r'''
import os,json,hashlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE','apps.settings')
import django
django.setup()
from django.db import connection,transaction
from api.models import User,Roles,Permission,User_Application_Product_Permission as P,User_Application_Location_Permission as L
with connection.cursor() as cur:
 cur.execute('SELECT current_database(),current_schema()')
 assert cur.fetchone()==('freshvcf','identity')
credentials=json.load(open('/run/secrets/stage2-fixture-accounts.json'))
emails={r['email'] for r in credentials.values()}
assert emails=={'stage2.broad@vectorflow.local','stage2.restricted@vectorflow.local'}
def protected():
 ids=list(User.all_objects.exclude(email__in=emails).values_list('id',flat=True))
 value={'users':list(User.all_objects.filter(id__in=ids).order_by('id').values('id','email','is_admin','is_active','is_deleted')),
 'products':list(P.objects.filter(user_id__in=ids).order_by('id').values()),
 'locations':list(L.objects.filter(user_id__in=ids).order_by('id').values()),
 'roles':list(Roles.user_id.through.objects.filter(user_id__in=ids).order_by('id').values())}
 return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
before=protected()
with transaction.atomic():
 if operation=='create':
  role,new=Roles.objects.get_or_create(name='Stage2 VM fixture reader 20261003',defaults=dict(code='Stage2FixtureReader',description='Isolated native VM dataset read/navigation only',application_id=2,is_visible=False))
  assert role.code=='Stage2FixtureReader' and role.application_id==2
  permissions=list(Permission.objects.filter(url__in=routes))
  assert {p.url for p in permissions}==set(routes)
  if new:role.permission_id.add(*permissions)
  assert set(role.permission_id.values_list('url',flat=True))==set(routes)
  assert not role.feature_id.exists()
 for kind,credential in credentials.items():
  if operation=='create':
   user=User.all_objects.filter(email=credential['email']).first()
   if user is None:
    user=User.all_objects.create_user(email=credential['email'],name='Stage2 VM '+kind+' reader',tc=True,password=credential['password'],is_admin=False)
    user.is_active=False;user.is_changed=True;user.save(update_fields=['is_active','is_changed'])
    role.user_id.add(user)
    for n in plan[kind]['products']:P.objects.create(user_id=user.pk,application_id=2,productfilter_id=n)
    for n in plan[kind]['locations']:L.objects.create(user_id=user.pk,application_id=2,locationfilter_id=n)
  else:user=User.all_objects.get(email=credential['email'])
  assert user.name=='Stage2 VM '+kind+' reader' and not user.is_admin and not user.is_deleted
  assert user.check_password(credential['password'])
  assert list(user.role_id.values_list('code',flat=True))==['Stage2FixtureReader']
  assert sorted(P.objects.filter(user_id=user.pk,application_id=2).values_list('productfilter_id',flat=True))==sorted(plan[kind]['products'])
  assert sorted(L.objects.filter(user_id=user.pk,application_id=2).values_list('locationfilter_id',flat=True))==sorted(plan[kind]['locations'])
  assert not P.objects.filter(user_id=user.pk).exclude(application_id=2).exists()
  assert not L.objects.filter(user_id=user.pk).exclude(application_id=2).exists()
  if operation!='create':
   user.is_active=operation=='enable';user.save(update_fields=['is_active'])
 assert protected()==before
print(json.dumps(dict(operation=operation,protected_actor_grants_sha256=before,existing_actors_unchanged=True,actors=list(User.all_objects.filter(email__in=emails).order_by('email').values('id','email','is_active','is_admin')))))
'''


def main(operation):
    import csv
    if operation=='enable':
        info=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1']))[0]
        env=dict(item.split('=',1) for item in info['Config']['Env'])
        if env.get('VF_DB_NAME')!='test_freshvcf_stage2_vm_20261003_002' or not env.get('VF_MTA_FIXTURE_FILE'):
            raise ValueError('Enable only inside the explicit fixture window')
    if not SECRET.exists():
        if operation!='create':raise ValueError('Fixture credentials absent')
        with SECRET.open('x',encoding='utf-8') as stream:
            json.dump({kind:dict(email='stage2.'+kind+'@vectorflow.local',password='S2!'+secrets.token_urlsafe(24)) for kind in ('broad','restricted')},stream)
    plan=json.loads((DATA/'fixture-scope-plan.json').read_text())
    pages={'P09','P10','P15','P16','P21','P22','P23','P24','P25'}
    with (ROOT/'docs/audit-2026-10-01/PAGE_INTERACTION_INVENTORY.csv').open(encoding='utf-8-sig') as stream:
        routes=[r['contract'] for r in csv.DictReader(stream) if r['page'] in pages and r['kind']=='route']
    script='operation='+repr(operation)+'\nplan='+repr(plan)+'\nroutes='+repr(routes)+'\n'+SCRIPT
    call=subprocess.run(['docker','exec','-i','freshvcf-preview-user-service-1','python','-'],input=script,text=True,capture_output=True)
    if call.returncode:
        # The script never emits credentials; retain diagnostics only.
        (DATA/('accounts-'+operation+'-error.txt')).write_text(call.stderr,encoding='utf-8')
        raise RuntimeError('Account operation failed; retained non-secret diagnostic')
    result=json.loads(call.stdout)
    (DATA/('accounts-'+operation+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['create','enable','disable'])
    main(parser.parse_args().operation)
