"""Representative real-cookie-gateway RRR reads; reuse accepted SQL receipts."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from wsgiref.simple_server import make_server

from django.core.management.base import BaseCommand, CommandError
from django.core.wsgi import get_wsgi_application
from mta.presentation.context import publication
from mta.runtime.management.commands.prove_action_http import frozen_existing
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.temporal import differences


MODERN_SHA='f96cc963afce16ce3342ab49b7448ecea047159e71efe745bf81b568049c0dff'
COMPARISON_SHA='1cb7ff7fbd5952320d4a4e47242e722c0db5f11939dae5450bd319f08a9527b8'
SELECTED=('root-regression','cross-attribute-AND','positive-stock',
          'raw-null-hasnovalue','parent-type-join','empty-hasvalue','page-two')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--evidence',type=Path,required=True)
        parser.add_argument('--gateway-session',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Use a new evidence directory')
        target.mkdir(parents=True)
        result=dict(status='FAILED',observations=[],calculations_executed=0,
                    legacy_replays=0,serving_changes=False)
        server=None
        try:
            modern=Path('/evidence/f3-rrr-filters-modern-001')
            comparison=Path('/evidence/f3-rrr-filters-comparison-001/receipt.json')
            if sha(modern/'receipt.json')!=MODERN_SHA or sha(comparison)!=COMPARISON_SHA:
                raise CommandError('Retained consumer proof changed')
            retained=json.loads((modern/'receipt.json').read_text())
            oracle=json.loads(comparison.read_text())
            if (oracle['status']!='PASS_SELECTED_RRR_FILTERS_WITH_DECLARED_LEGACY_FLAWS' or
                oracle['strict_pass']!=44 or oracle['modern_receipt_sha256']!=MODERN_SHA):
                raise CommandError('Retained oracle pairing is not accepted')
            root=Path(__file__).resolve().parents[4]
            if any(sha(root/n)!=value for n,value in retained['sources'].items()):
                raise CommandError('An affected source changed; do not silently reuse the receipt')
            if sha(modern/'cases.json')!=retained['cases_sha256']:
                raise CommandError('Retained API request roster changed')
            cases={c['id']:c for c in json.loads((modern/'cases.json').read_text())['cases']}
            accepted={c['id']:c for c in oracle['cases']}
            observed={(o['case_id'],o['path']):o for o in retained['observations']}
            session=json.loads(options['gateway_session'].read_text())
            if session['username']!='fresh.preview@vectorflow.local':
                raise CommandError('Only the approved isolated preview identity is permitted')
            context=publication();before=run_identity(context.run);all_before=frozen_existing()
            if context.hierarchy_receipt!=retained['hierarchy_supplement'] or before!=retained['run']:
                raise CommandError('Publication or approved read-time hierarchy binding differs')
            server=make_server('0.0.0.0',8000,get_wsgi_application())
            Thread(target=server.serve_forever,daemon=True).start()

            def post(route,body,authenticated=True):
                headers={'Host':'localhost','Content-Type':'application/json',
                         'X-VectorFLOW-Identity':'{"id":"forged-header"}'}
                if authenticated: headers['Cookie']='access_token='+session['access_token']
                request=Request('http://freshvcf-f3-action-gateway:10016/api/mta/'+route,
                    data=json.dumps(body).encode(),headers=headers,method='POST')
                try:
                    with urlopen(request,timeout=180) as response:
                        return response.status,json.loads(response.read())
                except HTTPError as exc: return exc.code,json.loads(exc.read())

            status,value=post('RRRDataCount',cases['root-regression']['payload'],False)
            if status!=401: raise CommandError('Unauthenticated request reached MTA')
            result['unauthenticated_status']=status
            for case_id in (*SELECTED,'missing-category'):
                case=cases[case_id]
                if accepted[case_id]['status']!=('LEGACY_FLAW_NOT_PARITY' if case['canonical_sql_error'] else 'PASS'):
                    raise CommandError('Selected retained contract is not proved')
                for route in ('RRRDataCount','RRRData'):
                    obs=observed[case_id,route]; path=modern/obs['payload']
                    if sha(path)!=obs['sha256']: raise CommandError('Retained response changed')
                    with gzip.open(path,'rt') as stream: expected=json.load(stream)
                    body=deepcopy(case['payload'])
                    body.update(product_permissions=[],location_permissions=[],user={'id':'forged-body'})
                    status,value=post(route,body)
                    row=dict(case_id=case_id,route=route,status=status,request=body,response=value)
                    if case['canonical_sql_error']:
                        if status!=503 or 'LEG-RRR-FILTER-INVALID-SQL' not in json.dumps(value):
                            raise CommandError('Source flaw was hidden/repaired by the gateway')
                        row['classification']='LEGACY_FLAW_NOT_PARITY'
                    else:
                        delta=differences(expected['response'],value,'/'+case_id+'/'+route)
                        if route=='RRRData':
                            keys=('DispatchColorSequence','DispatchPen','WhCode','SKUCode')
                            delta+=differences([tuple(r[k] for k in keys) for r in expected['response']['data']],
                                              [tuple(r[k] for k in keys) for r in value.get('data',[])],'/ordered-keys')
                        row.update(classification='PASS' if status==200 and not delta else 'FAIL',differences=delta,
                                   retained_response_sha256=obs['sha256'])
                        if row['classification']!='PASS':
                            result['observations'].append(row)
                            raise CommandError('Actual gateway changed the proved full response')
                    result['observations'].append(row)
                self.stdout.write(case_id+' gateway '+('NOT_PARITY' if case['canonical_sql_error'] else 'PASS'))
                self.stdout.flush()
            if before!=run_identity(context.run) or all_before!=frozen_existing():
                raise CommandError('Read-only gateway proof changed a run/action identity')
            result.update(status='PASS_RETAINED_RRR_REAL_GATEWAY_FILTERS',real_gateway_acceptance='PASS',
                comparisons=14,source_flaw_not_parity=1,run=before,
                hierarchy_supplement=context.hierarchy_receipt,existing_runs_and_commands_unchanged=True,
                username=session['username'],user_id=session['user_id'],
                retained_modern_sha256=MODERN_SHA,retained_sql_comparison_sha256=COMPARISON_SHA,
                command_sha256=sha(Path(__file__)),qualification='Seven representative root-scope cases; existing leaf expansion SQL/Django proof is not a new leaf login or browser proof')
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc));raise
        finally:
            if server: server.shutdown();server.server_close()
            (target/'receipt.json').write_text(json.dumps(result,indent=2))
        self.stdout.write(json.dumps(dict(status=result['status'],comparisons=14,receipt_sha256=sha(target/'receipt.json'))))
