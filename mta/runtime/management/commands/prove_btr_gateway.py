"""Representative real-cookie-gateway BTR reads over accepted SQL receipts."""
from copy import deepcopy
import gzip
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
from parity.output_archive import file_sha
from parity.temporal import differences


MODERN_SHA='11eb19e745f9f1a80d36da60899e516783506ec05383029a6cc0ed09c2f9303f'
COMPARISON_SHA='fae017590847e047805d65883979b31e96fbdd2f9bdeb03b89f1f2f54e1a79b9'
SELECTED=('root-regression','cross-attribute-AND','category-code',
          'raw-null-hasnovalue','parent-type-join','green-age','page-two')


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--evidence',type=Path,required=True)
        parser.add_argument('--gateway-session',type=Path,required=True)

    def handle(self,*args,**options):
        target=options['evidence']
        if target.exists(): raise CommandError('Use a new evidence directory')
        target.mkdir(parents=True)
        result=dict(status='FAILED',observations=[],calculations_executed=0,legacy_replays=0,serving_changes=False)
        server=None
        try:
            modern=Path('/evidence/f3-btr-filters-modern-001')
            comparison=Path('/evidence/f3-btr-filters-comparison-001/receipt.json')
            if file_sha(modern/'receipt.json')!=MODERN_SHA or file_sha(comparison)!=COMPARISON_SHA:
                raise CommandError('Pinned accepted consumer receipt changed')
            retained=json.loads((modern/'receipt.json').read_text()); oracle=json.loads(comparison.read_text())
            if oracle['status']!='PASS_SELECTED_BTR_FILTERS_WITH_DECLARED_LEGACY_FLAWS' or oracle['modern_receipt_sha256']!=MODERN_SHA:
                raise CommandError('Retained independent comparison is not accepted')
            root=Path(__file__).resolve().parents[4]
            if any(file_sha(root/n)!=value for n,value in retained['sources'].items()):
                raise CommandError('Affected source changed; reconcile before reuse')
            if file_sha(modern/'cases.json')!=retained['cases_sha256']: raise CommandError('Request roster changed')
            cases={r['id']:r for r in json.loads((modern/'cases.json').read_text())['cases']}
            accepted={(r['id'],r['route']):r for r in oracle['cases']}
            observations={(r['case_id'],r['path']):r for r in retained['observations']}
            session=json.loads(options['gateway_session'].read_text())
            if session['username']!='fresh.preview@vectorflow.local': raise CommandError('Isolated preview identity required')
            context=publication(); before=run_identity(context.run); all_before=frozen_existing()
            if context.hierarchy_receipt!=retained['hierarchy_supplement'] or before!=retained['run']:
                raise CommandError('Native publication or read-time hierarchy binding differs')
            server=make_server('0.0.0.0',8000,get_wsgi_application())
            Thread(target=server.serve_forever,daemon=True).start()

            def post(route,body,authenticated=True):
                headers={'Host':'localhost','Content-Type':'application/json',
                         'X-VectorFLOW-Identity':'{"id":"forged-header"}'}
                if authenticated: headers['Cookie']='access_token='+session['access_token']
                request=Request('http://freshvcf-f3-action-gateway:10016/api/mta/'+route,
                    data=json.dumps(body).encode(),headers=headers,method='POST')
                try:
                    with urlopen(request,timeout=180) as response: return response.status,json.loads(response.read())
                except HTTPError as exc: return exc.code,json.loads(exc.read())

            status,_=post('GetBTRDataCount',cases['root-regression']['payload'],False)
            if status!=401: raise CommandError('Missing-cookie request reached MTA')
            result['unauthenticated_status']=status
            for case_id in (*SELECTED,'positive-stock'):
                case=cases[case_id]
                routes=('GetBTRData',) if case_id=='positive-stock' else ('GetBTRDataCount','GetBTRData')
                for route in routes:
                    flaw=route in case['sql_errors']
                    if accepted[case_id,route]['status']!=('LEGACY_FLAW_NOT_PARITY' if flaw else 'PASS'):
                        raise CommandError('Selected retained contract is not proved')
                    obs=observations[case_id,route]; path=modern/obs['payload']
                    if file_sha(path)!=obs['sha256']: raise CommandError('Retained response changed')
                    with gzip.open(path,'rt') as stream: expected=json.load(stream)
                    body=deepcopy(case['payload']); body.update(product_permissions=[],location_permissions=[],user={'id':'forged-body'})
                    status,value=post(route,body)
                    row=dict(case_id=case_id,route=route,status=status,request=body,response=value)
                    if flaw:
                        if status!=503 or 'LEG-BTR-FILTER-INVALID-SQL' not in json.dumps(value):
                            raise CommandError('Source flaw hidden or repaired')
                        row['classification']='LEGACY_FLAW_NOT_PARITY'
                    else:
                        delta=differences(expected['response'],value,'/'+case_id+'/'+route)
                        if route=='GetBTRData':
                            for branch in ('tech','eco'):
                                keys=lambda rows:[(r['SKUCode'],r['WhCode']) for r in rows]
                                delta+=differences(keys(expected['response']['data'][branch]),keys(value['data'][branch]),'/ordered/'+branch)
                        row.update(classification='PASS' if status==200 and not delta else 'FAIL',differences=delta,
                                   retained_response_sha256=obs['sha256'])
                        if row['classification']!='PASS':
                            result['observations'].append(row); raise CommandError('Gateway changed proved full response')
                    result['observations'].append(row)
                self.stdout.write(case_id+' gateway '+('NOT_PARITY' if case_id=='positive-stock' else 'PASS')); self.stdout.flush()
            if before!=run_identity(context.run) or all_before!=frozen_existing(): raise CommandError('Run/action identities changed')
            result.update(status='PASS_RETAINED_BTR_REAL_GATEWAY_FILTERS',real_gateway_acceptance='PASS',comparisons=14,
                source_flaw_not_parity=1,run=before,hierarchy_supplement=context.hierarchy_receipt,
                existing_runs_and_commands_unchanged=True,username=session['username'],user_id=session['user_id'],
                retained_modern_sha256=MODERN_SHA,retained_sql_comparison_sha256=COMPARISON_SHA,
                command_sha256=file_sha(Path(__file__)),
                qualification='Seven representative stored-root requests; finite leaf SQL/snapshot proof is not leaf login/browser acceptance')
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
        finally:
            if server: server.shutdown(); server.server_close()
            (target/'receipt.json').write_text(json.dumps(result,indent=2))
        self.stdout.write(json.dumps(dict(status=result['status'],comparisons=14,receipt_sha256=file_sha(target/'receipt.json'))))
