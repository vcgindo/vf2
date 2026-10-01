"""Read-only BTR requests over one checksum-verified relational publication.

Freeze one native read snapshot for this finite batch; no calculations or writes.
Independent SQL and representative real-gateway proof remain separate exits.
"""
import gzip
import json
from pathlib import Path
from unittest.mock import patch
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from mta.presentation.context import publication
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.btr_filter_cases import cases
from parity.output_archive import file_sha


class Command(BaseCommand):
    def add_arguments(self,parser): parser.add_argument('--evidence',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Use a new evidence directory')
        target.mkdir(parents=True); root=Path(__file__).resolve().parents[4]
        files=[*sorted((root/'mta/presentation').glob('*.py')),*sorted((root/'mta/config').glob('*.json')),
            root/'vectorflow/settings.py',root/'vectorflow/urls.py',root/'parity/btr_filter_cases.py',
            root/'parity/rrr_filter_cases.py',Path(__file__)]
        sources={p.relative_to(root).as_posix():file_sha(p) for p in files}
        context=publication(); before=run_identity(context.run)
        if context.hierarchy_receipt is None: raise CommandError('Run-bound retained supplement required')
        result=dict(status='FAILED',run=before,sources=sources,hierarchy_supplement=context.hierarchy_receipt,
            observations=[],calculations_executed=0,serving_changes=False,
            boundary='BTR_READONLY_SINGLE_RELATIONAL_SNAPSHOT_PRIVATE_IDENTITY')
        roster=cases(); (target/'cases.json').write_text(json.dumps(dict(cases=roster),indent=2))
        result['cases_sha256']=file_sha(target/'cases.json')
        client=Client(); headers={'HTTP_X_VECTORFLOW_IDENTITY':'{"id":"isolated-btr-filter-reader"}'}
        try:
            with patch('mta.presentation.views.publication',return_value=context):
                for index,case in enumerate(roster):
                    for path in ('GetBTRDataCount','GetBTRData'):
                        response=client.post('/api/mta/'+path,json.dumps(case['payload']),content_type='application/json',**headers)
                        expected=503 if path in case['sql_errors'] else 200
                        name='response-%02d-%s.json.gz'%(index,path)
                        with gzip.open(target/name,'wt',encoding='utf-8') as stream:
                            json.dump(dict(case_id=case['id'],request=case['payload'],path=path,
                                status=response.status_code,response=response.json()),stream)
                        result['observations'].append(dict(case_id=case['id'],path=path,payload=name,sha256=file_sha(target/name)))
                        if response.status_code!=expected: raise CommandError('Unexpected BTR status: '+case['id']+' '+path)
                    self.stdout.write(case['id']); self.stdout.flush()
            if before!=run_identity(context.run): raise CommandError('Accepted run changed')
            if any(file_sha(root/n)!=value for n,value in sources.items()): raise CommandError('Source changed')
            result.update(status='BTR_FILTER_READBACK_EXPORTED_COMPARISON_REQUIRED',accepted_run_unchanged=True,
                cases=len(roster),requests=len(result['observations']))
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally: (target/'receipt.json').write_text(json.dumps(result,indent=2))
        self.stdout.write(json.dumps(dict(status=result['status'],receipt_sha256=file_sha(target/'receipt.json'))))
