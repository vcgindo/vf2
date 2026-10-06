"""Copy only the two authorized local test identity contracts into empty3006.

The source is read-only. Password hashes, grants and actor IDs remain unchanged;
no business rows, sessions, tokens, layouts, or other accounts are imported.
"""
import hashlib
import json
from pathlib import Path
import subprocess

OWNER = Path('D:/freshvcf-build/daily-3006')
EVIDENCE = Path('D:/freshvcf-build/evidence/daily-publication-3006-20261006-001')
EXPORT = r'''
import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','apps.settings')
import django;django.setup()
from django.core import serializers
from api.models import (User,Roles,Permission,FeatureMaster,ApplicationMaster,
    UserserviceConfig,User_Application_Product_Permission as P,User_Application_Location_Permission as L)
users=list(User.all_objects.filter(email__in=['stage2.broad@vectorflow.local','stage2.restricted@vectorflow.local']).order_by('id'))
assert len(users)==2 and all(u.is_active and not u.is_admin for u in users)
ids=[u.pk for u in users]
roles=list(Roles.objects.filter(user_id__in=ids).distinct().order_by('id'))
rids=[r.pk for r in roles]
objects=[*ApplicationMaster.objects.filter(application_id__in=[2,3]),*users,*roles,
    *Permission.objects.filter(role_id__in=rids).distinct().order_by('id'),
    *FeatureMaster.objects.filter(role_id__in=rids).distinct().order_by('id'),
    *P.objects.filter(user_id__in=ids).order_by('id'),*L.objects.filter(user_id__in=ids).order_by('id'),
    *UserserviceConfig.objects.filter(flag__in=['Is_ADS_ACTIVE','IDLE_TIMEOUT'])]
value=json.loads(serializers.serialize('json',objects))
for item in value:
 if item['model']=='api.roles':item['fields']['user_id']=[u for u in item['fields']['user_id'] if u in ids]
 if item['model'] in ['api.permission','api.featuremaster']:item['fields']['role_id']=[r for r in item['fields']['role_id'] if r in rids]
 if item['model']=='api.user':
  for name in ['groups','user_permissions']:
   if name in item['fields']:item['fields'][name]=[]
print(json.dumps(value))
'''

IMPORT = r'''
import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','apps.settings')
import django;django.setup()
from django.db import connection,transaction
from django.core import serializers
from django.core.management.color import no_style
from api.models import User
with connection.cursor() as c:
 c.execute('SELECT current_database(),current_schema()')
 assert c.fetchone()==('daily_3006','identity')
assert not User.all_objects.exists(), 'Never reset or replace existing target actors'
objects=list(serializers.deserialize('json',payload))
with transaction.atomic():
 for item in objects:item.save()
 models=list({type(item.object) for item in objects})
 with connection.cursor() as c:
  for sql in connection.ops.sequence_reset_sql(no_style(),models):c.execute(sql)
print(json.dumps(dict(actors=list(User.all_objects.order_by('id').values('id','email','is_active','is_admin')),business_data_imported=False)))
'''


if __name__ == '__main__':
    raw = subprocess.check_output(['docker','exec','-i','freshvcf-preview-user-service-1','python','-'],
                                  input=EXPORT, text=True, encoding='utf-8')
    json.loads(raw)
    path = OWNER / 'secrets' / 'test-auth-contract-002.json'
    with path.open('x', encoding='utf-8') as stream:
        stream.write(raw)
    script = 'payload=' + repr(raw) + '\n' + IMPORT
    result = subprocess.run(['docker','compose','-f',str(OWNER/'compose.json'),'run','--rm','--no-deps',
        '-T','--entrypoint','python','user-service','-'], input=script, text=True, capture_output=True)
    if result.returncode:
        (EVIDENCE/'auth-bootstrap-error.txt').write_text(result.stderr)
        raise RuntimeError('Owned authentication bootstrap failed; external diagnostic retained')
    receipt = json.loads(result.stdout)
    receipt['source_contract_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
    (EVIDENCE/'auth-bootstrap.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))
