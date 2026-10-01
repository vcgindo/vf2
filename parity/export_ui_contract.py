"""Django/PostgreSQL layout sequence, always rolled back; no engine execution."""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.db import transaction
from django.test import Client
from mta.runtime.models import UserReportLayout
from parity.output_archive import file_sha


def main():
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    user = 'f3-ui-contract-isolated-A'
    report = 'DBM'
    state = '{"columns":[{"colId":"SKUCode","hide":false}],"charts":[],"pivot":false}'
    result = {'status':'FAILED','username':user,'reportname':report,'state':state}
    try:
        if UserReportLayout.objects.filter(username=user).exists():
            raise ValueError('Isolated identity already has state; do not overwrite')
        client = Client()
        headers = {'HTTP_X_VECTORFLOW_IDENTITY':json.dumps({'id':user})}
        config = client.get('/api/mta/GetUIConfig?reportName=NormSuggestion',**headers)
        assert config.status_code == 200
        result['config'] = config.json()['data']
        observations = []
        with transaction.atomic():
            for action,value in [('GetState',None),('SaveState',state),('GetState',None),
                                 ('SaveState',state),('GetState',None),('ResetState',None),
                                 ('ResetState',None),('GetState',None),('SaveState',''),('GetState',None)]:
                response = client.post('/api/mta/'+action, json.dumps({'reportname':report,'state':value}),
                                       content_type='application/json',**headers)
                assert response.status_code == 200
                observations.append({'action':action,'input_state':value,'data':response.json()['data']})
            transaction.set_rollback(True)
        assert not UserReportLayout.objects.filter(username=user).exists()
        result.update(status='POSTGRES_LAYOUT_SEQUENCE_PASS_COMPARISON_REQUIRED',observations=observations,
                      no_persisted_test_rows=True,engine_replays=0)
        result['source_hashes']={p:file_sha(Path(p)) for p in (
            'mta/presentation/ui_state.py','mta/presentation/views.py','mta/presentation/urls.py',
            'mta/runtime/models.py','mta/runtime/migrations/0012_user_report_layout.py')}
    finally:
        (target/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(result['status'])


if __name__ == '__main__':
    main()
