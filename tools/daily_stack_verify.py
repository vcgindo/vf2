"""Read-only startup/isolation proof for the owned, unselected 3006 shell."""
import argparse
import json
from pathlib import Path
import subprocess
import urllib.request

from daily_stack_setup import EVIDENCE, PROJECT, snapshot


def execute(container, code):
    return json.loads(subprocess.check_output(
        ['docker', 'exec', '-i', container, 'python', '-'], input=code, text=True))


def verify(label):
    target = EVIDENCE / (label + '.json')
    if target.exists():
        raise ValueError('Proof identity already exists')
    before = json.loads((EVIDENCE / 'protected-before.json').read_text())
    if before != snapshot():
        raise ValueError('Protected service/configuration changed')
    owned = {}
    for name in ('postgres', 'redis', 'mta', 'user-service', 'mto', 'frontend'):
        data = json.loads(subprocess.check_output(
            ['docker', 'inspect', PROJECT + '-' + name + '-1'], text=True))[0]
        assert data['State']['Running'] and data['HostConfig']['RestartPolicy']['Name'] == 'no'
        bindings = data['HostConfig'].get('PortBindings') or {}
        assert bindings == ({'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '3006'}]}
                            if name == 'frontend' else {})
        owned[name] = dict(id=data['Id'], image=data['Image'], started=data['State']['StartedAt'],
                           memory=data['HostConfig']['Memory'], nano_cpus=data['HostConfig']['NanoCpus'])
    health = execute(PROJECT + '-mta-1', '''import json,urllib.request,urllib.error
result={}
for path in ('/healthz','/readyz','/api/mta/GetBPRData'):
    try: response=urllib.request.urlopen('http://localhost:8000'+path)
    except urllib.error.HTTPError as error: response=error
    result[path]={'status':response.status,'body':json.loads(response.read())}
print(json.dumps(result))
''')
    assert health['/healthz']['status'] == 200
    assert health['/readyz'] == dict(status=503, body=dict(ready=False))
    assert health['/api/mta/GetBPRData'] == dict(status=503, body=dict(error='publication_not_admitted'))
    fresh = execute(PROJECT + '-mta-1', '''import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django;django.setup()
from django.conf import settings
from mta.runtime.models import CalculationRun,DailyUiPublication,MdmSource
print(json.dumps(dict(runs=CalculationRun.objects.count(),publications=DailyUiPublication.objects.count(),
mdm_sources=MdmSource.objects.count(),selected_run=settings.VF_MTA_PUBLISHED_RUN,
selected_digest=settings.VF_MTA_PUBLISHED_DIGEST)))
''')
    assert fresh == dict(runs=0, publications=0, mdm_sources=0, selected_run='', selected_digest='')
    protected = execute('freshvcf-preview-mta-1', '''import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django;django.setup()
from django.conf import settings
from mta.runtime.models import CalculationRun,MdmSource
from mta.presentation.fixture import binding
run,source=binding()
print(json.dumps(dict(run=str(run.pk),output=run.output_digest,fixture=source,
mdm_sources=list(MdmSource.objects.values_list('digest',flat=True)),
selected=settings.VF_MTA_PUBLISHED_RUN)))
''')
    assert protected['run'] == 'bfd75b4b-a9df-4a08-82d3-852e3324b623'
    assert protected['fixture'] == '4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73'
    assert protected['mdm_sources'] == ['eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d']
    with urllib.request.urlopen('http://localhost:3006/healthz') as response:
        frontend = json.load(response)
    target.write_text(json.dumps(dict(owned=owned, health=health, frontend=frontend,
        fresh=fresh, protected=protected, protected_identity_configuration_unchanged=True), indent=2))
    print('PASS: isolated shell alive, reports unready, no daily data selected; protected3005 identity unchanged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    verify(parser.parse_args().label)
