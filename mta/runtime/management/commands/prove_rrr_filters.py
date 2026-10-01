"""RRR selected filters/scopes on accepted relational rows; no calculation."""
import gzip
import hashlib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from mta.presentation.context import publication
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.rrr_filter_cases import cases


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class Command(BaseCommand):
    def add_arguments(self,parser): parser.add_argument('--evidence',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Use a new evidence directory')
        target.mkdir(parents=True)
        root=Path(__file__).resolve().parents[4]
        files=[*sorted((root/'mta/presentation').glob('*.py')),*sorted((root/'mta/config').glob('*.json')),
            root/'vectorflow/settings.py',root/'vectorflow/urls.py',root/'parity/rrr_filter_cases.py',Path(__file__)]
        sources={p.relative_to(root).as_posix():sha(p) for p in files}
        context=publication(); before=run_identity(context.run)
        if context.hierarchy_receipt is None: raise CommandError('Approved run-bound supplement required')
        result=dict(status='FAILED',run=before,sources=sources,hierarchy_supplement=context.hierarchy_receipt,
                    observations=[],calculations_executed=0,serving_changes=False)
        client=Client(); headers={'HTTP_X_VECTORFLOW_IDENTITY':'{"id":"isolated-rrr-filter-reader"}'}
        roster=cases()
        (target/'cases.json').write_text(json.dumps(dict(cases=roster),indent=2))
        result['cases_sha256']=sha(target/'cases.json')
        try:
            for index,case in enumerate(roster):
                for path in ('RRRDataCount','RRRData'):
                    response=client.post('/api/mta/'+path,json.dumps(case['payload']),
                        content_type='application/json',**headers)
                    expected=503 if case['canonical_sql_error'] else 200
                    name='response-%02d-%s.json.gz'%(index,path)
                    with gzip.open(target/name,'wt',encoding='utf-8') as stream:
                        json.dump(dict(case_id=case['id'],request=case['payload'],path=path,
                                       status=response.status_code,response=response.json()),stream)
                    result['observations'].append(dict(case_id=case['id'],path=path,payload=name,sha256=sha(target/name)))
                    if response.status_code!=expected:
                        raise CommandError('Unexpected RRR status: '+case['id']+' '+path+' '+str(response.status_code))
                self.stdout.write(case['id']+' HTTP'+str(expected)); self.stdout.flush()
            if before!=run_identity(context.run): raise CommandError('Accepted publication mutated')
            if any(sha(root/n)!=value for n,value in sources.items()): raise CommandError('Source changed during proof')
            result.update(status='RRR_FILTER_READBACK_EXPORTED_COMPARISON_REQUIRED',accepted_run_unchanged=True,
                          cases=len(roster),requests=len(result['observations']))
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally:
            (target/'receipt.json').write_text(json.dumps(result,indent=2))
        self.stdout.write(json.dumps(dict(status=result['status'],cases=len(roster),receipt_sha256=sha(target/'receipt.json'))))
