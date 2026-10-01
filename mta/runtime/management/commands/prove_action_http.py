"""Bounded F3.2 retained two-day HTTP/action/own-predecessor evidence.

Uses unchanged retained facts and accepted independent SQL captures as oracle.
Only clock is fixed to the retained scenario date. No scope/calculation/publication
mock and no serving account/accepted F2 run mutation.
"""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from wsgiref.simple_server import make_server

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.wsgi import get_wsgi_application
from django.test import Client, override_settings

from mta.presentation.context import publication
from mta.runtime.models import CalculationRun, RunCommand
from mta.runtime.services import read_outputs
from mta.runtime.temporal import execute_day, command_state
from mta.runtime.validation_storage import export_run
from mta.serialization import digest
from parity.output_archive import OutputArchive
from parity.replay_temporal import compare_day, independent_contracts_pass
from parity.temporal import differences
from parity.temporal_policy import POLICY, commands_for_day

INPUT_SHA = '458c7c661cc2e6b2e65f30415042b98ab889c6e151aeaf086c00029c6528c92f'
REPLAY_SHA = '316070183c5be144042736e314dfb0eb95a83e4833ae4882457a5bf4ac55dfd5'
PERMISSION_SHA = '18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_existing():
    return dict(runs={str(r.pk):digest(dict(input=r.input_digest, output=r.output_digest,
        production=r.production_digest, parity=r.parity_summary, status=r.status))
        for r in CalculationRun.objects.all()},
        commands={str(r.pk):digest(dict(run=str(r.run_id),payload=r.payload,digest=r.digest,
            before=r.before_digest,after=r.after_digest,manifest=r.state_manifest))
            for r in RunCommand.objects.all()})


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--input', type=Path, required=True)
        parser.add_argument('--retained-replay', type=Path, required=True)
        parser.add_argument('--evidence', type=Path, required=True)
        parser.add_argument('--revision', required=True)
        parser.add_argument('--gateway-url')
        parser.add_argument('--gateway-session',type=Path)
        parser.add_argument('--dbm-filters',action='store_true',help='One retained day0, pre-action DBM reads, then unchanged day0 actions')

    def handle(self, *args, **options):
        target = options['evidence']
        if target.exists(): raise CommandError('Preserve earlier attempts; use a new evidence directory')
        target.mkdir(parents=True)
        if sha(options['input']) != INPUT_SHA or sha(options['retained_replay']) != REPLAY_SHA:
            raise CommandError('Retained input or independent accepted capture receipt changed')
        if settings.VF_MTA_PERMISSIONS_SHA256 != PERMISSION_SHA:
            raise CommandError('Exact retained permission catalogue required')
        case = json.loads(options['input'].read_text())['case']
        retained = json.loads(options['retained_replay'].read_text())
        if retained['status'] != 'PASS' or retained['input_sha256'] != INPUT_SHA or retained['action_policy'] != POLICY:
            raise CommandError('Wrong retained shallow acceptance boundary')
        root = Path(__file__).resolve().parents[4]
        sources = {str(p.relative_to(root)):sha(p) for p in sorted((root/'mta').rglob('*.py'))}
        before = frozen_existing()
        previous, days, comparisons, observations = None, [], [], []
        result = dict(status='FAILED', artifact_sha256=INPUT_SHA, retained_replay_sha256=REPLAY_SHA,
                      boundary='F3.2 two retained days; real Django/PostgreSQL routes; gateway/browser remain separate',
                      sources=sources, observations=observations)
        client = Client()
        headers = {'HTTP_X_VECTORFLOW_IDENTITY':json.dumps({'id':'f3-retained-action-actor'})}
        server = None
        gateway = options['gateway_url']
        dbm_mode=options['dbm_filters']
        if dbm_mode and not gateway:raise CommandError('DBM pre-action mode requires the actual cookie gateway')
        actor = 'f3-retained-action-actor'
        session = None
        if gateway:
            if gateway!='http://freshvcf-f3-action-gateway:10016' or not options['gateway_session']:
                raise CommandError('Explicit private retained-action gateway/session required')
            session=json.loads(options['gateway_session'].read_text())
            if session['username']!='fresh.preview@vectorflow.local':
                raise CommandError('Only approved isolated preview identity permitted')
            actor=str(session['user_id'])
            server=make_server('0.0.0.0',8000,get_wsgi_application())
            Thread(target=server.serve_forever,daemon=True).start()
            result['boundary']='F3.2 private real cookie-login gateway → Django/PostgreSQL actions → own next day'
            result['gateway_identity']=dict(username=session['username'],user_id=session['user_id'],
                authentication='existing cookie JWT login; unchanged gateway and stored permission assignments')

        def post(route, body, authenticated=True):
            if not gateway:
                response=client.post('/api/mta/'+route,json.dumps(body),content_type='application/json',
                                     **(headers if authenticated else {}))
                return response.status_code,response.json()
            request_headers={'Host':'localhost','Content-Type':'application/json',
                             'X-VectorFLOW-Identity':'{"id":"forged-header-actor"}'}
            if authenticated: request_headers['Cookie']='access_token='+session['access_token']
            request=Request(gateway+'/api/mta/'+route,data=json.dumps(body).encode(),headers=request_headers,method='POST')
            try:
                with urlopen(request,timeout=180) as response:
                    return response.status,json.loads(response.read())
            except HTTPError as exc:
                return exc.code,json.loads(exc.read())
        payload = dict(product_permissions=[71001], location_permissions=[72001],
                       paginationParameter=dict(pageNumber=1,recordsPerPage=5000))
        try:
            for index in ((0,) if dbm_mode else (0,1)):
                entry = retained['days'][index]
                if len(entry['comparisons']) != 31 or not independent_contracts_pass(entry['comparisons']):
                    raise CommandError('Retained day lacks complete accepted comparisons')
                # Paths are already registered in the accepted receipt. No SQL replay.
                registered = entry['legacy_capture_path'].replace('\\','/')
                if not registered.startswith('D:/freshvcf-build/evidence/'):
                    raise CommandError('Retained capture is outside the approved evidence root')
                capture_path = Path(os.environ['VF_EVIDENCE_ROOT']).parent / registered[len('D:/freshvcf-build/evidence/'):]
                if sha(capture_path) != entry['legacy_capture_sha256']:
                    raise CommandError('Independent retained capture hash differs')
                with gzip.open(capture_path,'rt',encoding='utf-8') as stream: legacy = json.load(stream)
                if digest(legacy['closing']) != entry['closing_digest']:
                    raise CommandError('Independent closing-state provenance differs')
                day = {**deepcopy(case['days'][index]), **deepcopy(case['static_day'])}
                run = execute_day(day=day, profile=case['profile'], execution_revision=options['revision'],
                    predecessor=previous, opening=None if previous else dict(state=case['opening'],
                        opening_date=case['opening_date'],identity='f3-http-'+target.name+'-'+INPUT_SHA))
                archive = OutputArchive(export_run(run,target/('day-%03d'%index)))
                checks = compare_day(legacy, archive)
                if len(checks)!=29 or not independent_contracts_pass(checks):
                    raise CommandError('Retained pre-action calculation mismatch: '+json.dumps(checks))
                current = dict(day_index=index,run_id=str(run.pk),input_digest=run.input_digest,
                               output_digest=run.output_digest)
                days.append(current)
                comparisons.append(dict(day_index=index,date=str(run.business_date),modern_run=str(run.pk),
                    modern_output_digest=run.output_digest,status='PASS',comparisons=deepcopy(checks)))
                # Existing recorder verifies the complete 29-contract pre-action
                # boundary. This does not claim automatic-action acceptance.
                modern = dict(artifact_sha256=INPUT_SHA, action_policy='retained-fixed-actions',
                              revision=options['revision'], days=days)
                modern_path = target/('pre-action-modern-%d.json'%index)
                modern_path.write_text(json.dumps(modern,indent=2))
                pre = dict(status='PASS',input_sha256=INPUT_SHA,action_policy='retained-fixed-actions',
                    modern_execution_sha256=sha(modern_path),requested_days=index+1,days=comparisons)
                pre_path = target/('pre-action-comparison-%d.json'%index)
                pre_path.write_text(json.dumps(pre,indent=2))
                call_command('record_parity',replay=pre_path,modern_execution=modern_path)
                output = read_outputs(run)
                commands = commands_for_day(case,index,output['DBMFinal'][0]['Suggestions'])
                supplement = json.loads((root/'baseline/presentation-hierarchy-v1.json').read_text())
                supplement['publications'] = [dict(run_id=str(run.pk),business_date=str(run.business_date),
                                                  output_digest=run.output_digest)]
                supplement_path = target/('hierarchy-day-%d.json'%index)
                supplement_path.write_text(json.dumps(supplement,indent=2))
                with override_settings(VF_MTA_PUBLISHED_RUN=str(run.pk),VF_MTA_PUBLISHED_DIGEST=run.output_digest,
                        VF_MTA_HIERARCHY_FILE=str(supplement_path),VF_MTA_HIERARCHY_SHA256=sha(supplement_path),
                        VF_MTA_ACTIONS_ENABLED=True):
                    if dbm_mode:
                        from mta.runtime.dbm_filter_probe import export_reads
                        result['dbm_filters']=export_reads(target,post,self.stdout)
                        result['dbm_filters']['retained_capture_path']=registered
                        result['dbm_filters']['retained_capture_sha256']=entry['legacy_capture_sha256']
                        result['dbm_filters']['legacy_closing_digest']=entry['closing_digest']
                        result['dbm_filters']['hierarchy_file']=supplement_path.name
                    # Actual scope rejects a selected identity when no permission
                    # is assigned, before it reaches the real command writer.
                    selection = commands[0]['selected'][0]
                    denied = {**payload,'product_permissions':[], 'data':[dict(SKUCode=selection[0],WHCode=selection[1])]}
                    if gateway:
                        # Gateway owns permissions, so browser-supplied lists
                        # cannot deny/grant scope. An unknown entity tests denial.
                        denied={**payload,'data':[dict(SKUCode='outside-retained-catalogue',WHCode=selection[1])]}
                    count_before = run.commands.count()
                    status, value=post('DBMApplySelectedNorms',denied)
                    observations.append(dict(day_index=index,route='DBMApplySelectedNorms',case='outside-scope',
                                             status=status,response=value))
                    if status!=403 or run.commands.count()!=count_before:
                        raise CommandError('Real permission rejection changed state')
                    status,value=post('DBMApplySelectedNorms',denied,authenticated=False)
                    if status not in ((401,) if gateway else (403,)) or run.commands.count()!=count_before:
                        raise CommandError('Unauthenticated action reached a writer')
                    observations.append(dict(day_index=index,case='unauthenticated',status=status))
                    for command in commands:
                        route = 'DBMApplySelectedNorms' if command['operation']=='APPLY' else 'DBMUpdateSleepTbl'
                        request = {**payload,'user':{'id':'forged'},'data':[
                            dict(SKUCode=sku,WHCode=loc) for sku,loc in command['selected']]}
                        if gateway:
                            request.update(product_permissions=[],location_permissions=[])
                        # Frozen scenario clock models canonical GETDATE(). Its
                        # own facts/actions are unchanged from the retained trial.
                        with patch('mta.presentation.actions.timestamp',return_value=command['timestamp']):
                            status,value=post(route,request)
                        expected = dict(recordCount=None,data='' if command['operation']=='APPLY' else None,
                            status=200,msg='Saved Succesfully',errorCount=None,error=None,
                            conflictErrorCount=None,conflictError=None)
                        observations.append(dict(day_index=index,route=route,request=request,
                            response=value,status=status,expected=expected))
                        if status!=200 or value!=expected:
                            raise CommandError('Canonical positive action response differs')
                    context = publication()
                    if context.hierarchy_receipt is None: raise CommandError('Approved supplement not applied')
                after, events = command_state(run, read_outputs(run)['DBMFinal'][0])
                delta = differences(legacy['post_commands'],commands,'/own-action-selection')
                checks += [dict(contract='own-action-selection',status='FAIL' if delta else 'PASS',differences=delta)]
                delta = differences(legacy['post_command_state'],after,'/post-action-state')
                checks += [dict(contract='post-action-state',status='FAIL' if delta else 'PASS',differences=delta)]
                if len(checks)!=31 or not independent_contracts_pass(checks):
                    raise CommandError('Retained post-action comparison differs: '+json.dumps(checks))
                if any(e.payload['actor']!=actor for e in run.commands.all()):
                    raise CommandError('Payload actor overrode trusted identity')
                current.update(date=str(run.business_date),predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
                    post_action_digest=digest(after),commands=commands,command_lineage=events,
                    retained_capture_sha256=sha(capture_path),comparisons=checks)
                previous=run
                self.stdout.write(json.dumps(dict(day=index+1,run_id=str(run.pk),contracts=31,status='PASS')))
                self.stdout.flush()
            final_modern = dict(artifact_sha256=INPUT_SHA,action_policy=POLICY,revision=options['revision'],days=days)
            final_modern_path=target/'execution.json'
            final_modern_path.write_text(json.dumps(final_modern,indent=2))
            final_replay=dict(status='PASS',input_sha256=INPUT_SHA,action_policy=POLICY,
                modern_execution_sha256=sha(final_modern_path),requested_days=len(days),
                kind='RETAINED_CAPTURE_COMPARISON_WITH_F3_HTTP_ACTIONS',
                retained_replay_sha256=REPLAY_SHA,days=[dict(day_index=i,date=d['date'],
                    modern_run=d['run_id'],modern_output_digest=d['output_digest'],status='PASS',
                    comparisons=d['comparisons']) for i,d in enumerate(days)])
            final_replay_path=target/'comparison.json'
            final_replay_path.write_text(json.dumps(final_replay,indent=2))
            call_command('record_parity',replay=final_replay_path,modern_execution=final_modern_path)
            final=frozen_existing()
            if any(final[k].get(identifier)!=value for k,rows in before.items() for identifier,value in rows.items()):
                raise CommandError('Pre-existing run or action identity changed')
            result.update(status='RETAINED_DBM_GATEWAY_READBACK_EXPORTED_COMPARISON_REQUIRED' if dbm_mode else 'PASS_RETAINED_HTTP_ACTIONS_AND_OWN_NEXT_DAY',days=days,
                comparisons=31*len(days),existing_runs_and_commands_unchanged=True,
                legacy_replays=0,serving_changes=False,real_gateway_acceptance='PASS' if gateway else 'OPEN')
        except Exception as exc:
            result['error']=dict(type=type(exc).__name__,message=str(exc))
            raise
        finally:
            if server:
                server.shutdown()
                server.server_close()
            result['days']=days
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(status=result['status'],days=len(days),comparisons=31*len(days),receipt_sha256=sha(target/'receipt.json'))))
