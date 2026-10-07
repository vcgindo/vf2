"""One owned fresh PostgreSQL migration proof; retain database, never reset one."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ['VFTEST_OFFLINE_POSTGRES']='1'
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.test.runner import DiscoverRunner

name='test_freshvcf_offline_20261007_001'
with connection.cursor() as cursor:
    cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[name])
    if cursor.fetchone():
        raise ValueError('Fresh migration proof database already exists; preserve it')
settings.DATABASES['default']['TEST']['NAME']=name
result=DiscoverRunner(verbosity=2,interactive=False,keepdb=True).run_tests(['tests.test_offline_postgres'])
raise SystemExit(result)
