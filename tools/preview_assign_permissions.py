"""Assign only retained root scopes to the approved isolated preview account.

No credential/account reset, no other user/application update. Catalogue IDs and
application mapping are verified before the atomic insert. Retain an audit receipt.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    target=Path(sys.argv[1])
    if target.exists(): raise ValueError('Preserve earlier receipts')
    catalogue_path=Path('D:/freshvcf-build/inputs/permission-input-v1.json')
    expected='18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356'
    if hashlib.sha256(catalogue_path.read_bytes()).hexdigest()!=expected:
        raise ValueError('Retained permission catalogue changed')
    catalogue=json.loads(catalogue_path.read_text())
    roots={kind:[r['id'] for r in catalogue[kind]['records'] if r['level_2'] is None] for kind in ('products','locations')}
    if roots!={'products':[71001],'locations':[72001]}: raise ValueError('Unexpected retained root roster')
    script='''import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','apps.settings')
import django
django.setup()
from django.db import transaction,connection
from api.models import User,User_Application_Product_Permission as P,User_Application_Location_Permission as L
from api_gateway.service_config.config import service_map
assert service_map['mta']['application_id']==2
with connection.cursor() as c:
 c.execute('SELECT current_database(),current_schema()'); database,schema=c.fetchone()
assert (database,schema)==('freshvcf','identity')
user=User.objects.get(email=os.environ['VECTORFLOW_TEST_USERNAME'])
assert user.email=='fresh.preview@vectorflow.local'
def memberships(model,field):
 return list(model.objects.filter(user_id=user.pk,application_id=2).order_by(field).values_list(field,flat=True))
with transaction.atomic():
 before={'products':memberships(P,'productfilter_id'),'locations':memberships(L,'locationfilter_id')}
 assert set(before['products']) <= {71001} and set(before['locations']) <= {72001}
 P.objects.get_or_create(user_id=user.pk,application_id=2,productfilter_id=71001)
 L.objects.get_or_create(user_id=user.pk,application_id=2,locationfilter_id=72001)
 after={'products':memberships(P,'productfilter_id'),'locations':memberships(L,'locationfilter_id')}
 assert after=={'products':[71001],'locations':[72001]}
print(json.dumps({'user_id':user.pk,'username':user.email,'application_id':2,'database':database,'schema':schema,'before':before,'after':after,'account_reset':False}))
'''
    result=subprocess.run(['docker','exec','-i','freshvcf-preview-user-service-1','python','-'],
                          input=script,text=True,capture_output=True)
    target.mkdir(parents=True)
    (target/'stdout.json').write_text(result.stdout,encoding='utf-8')
    (target/'stderr.txt').write_text(result.stderr,encoding='utf-8')
    if result.returncode: raise RuntimeError('Assignment failed; receipt retained')
    value=json.loads(result.stdout)
    value.update(catalogue_sha256=expected,status='RETAINED_ROOT_ASSIGNMENT_APPLIED',scope='isolated preview account only')
    (target/'receipt.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(value))


if __name__=='__main__': main()
