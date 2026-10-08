"""Real persisted-cookie gateway proof over existing owners; never calculates."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import traceback
from copy import deepcopy

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tools.cohort3_settings')
import django
django.setup()

from django.test import Client
from django.db import connections
from mta.presentation import qualified_consumption as policy, admission
from mta.presentation.qualified_session import selected
from mta.runtime.models import CalculationRun
from tools.cohort3_auth import issue_actor_tokens


def content(response):
    if not response.streaming:
        return response.content
    if response.is_async:
        async def collect():
            return b''.join([chunk async for chunk in response.streaming_content])
        return asyncio.run(collect())
    return b''.join(response.streaming_content)


def actor_client(actor):
    client = Client(raise_request_exception=False)
    client.cookies['access_token'] = issue_actor_tokens(actor)['access']
    client.cohort3_actor = actor
    return client


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date-index', choices=(0, 1), type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Proof receipt already exists; choose a new attempt path')
    pin = policy.pins()['runs'][args.date_index]
    run = CalculationRun.objects.get(pk=pin['run_id'])
    evidence = dict(run=pin['run_id'], date=pin['date'], output=pin['output_digest'],
                    calculation_calls=0, observations=[], failures=[], status='RUNNING')
    retained = {}
    if args.resume:
        prior = json.loads(args.resume.read_text())
        assert (prior['run'], prior['date'], prior['output']) == (pin['run_id'], pin['date'], pin['output_digest'])
        retained = {row['label']: row for row in prior['observations']
                    if (row['status'] == 200 or
                        (row['status'] == 503 and row['label'] in (
                            'orderFulfillment-custom', 'git-child-GetPlanningDataGrid')))
                    and not row['route'].startswith('DownloadReports/')}
        evidence['reused_receipt'] = dict(path=str(args.resume),
            sha256=hashlib.sha256(args.resume.read_bytes()).hexdigest(), labels=[])

    def request(client, route, payload=None, *, method='POST', expected=200, label=None):
        name = label or route
        if name in retained and retained[name]['route'] == route:
            observation = retained[name]
            evidence['observations'].append(observation)
            evidence['reused_receipt']['labels'].append(name)
            if observation['status'] != expected:
                evidence['failures'].append(dict(label=name, expected=expected,
                    actual=observation['status'], body=observation['body']))
            print(json.dumps(dict(label=name, reused=True)), flush=True)
            return observation['body'], b'', observation
        if hasattr(client, 'cohort3_actor'):
            # Issue a real retained token for each unresolved request. Long
            # proof duration must not alter the production token lifetime.
            client.cookies['access_token'] = issue_actor_tokens(client.cohort3_actor)['access']
        response = (client.get('/api/mta/'+route) if method == 'GET' else
                    client.post('/api/mta/'+route, data=payload or {}, content_type='application/json'))
        raw = content(response)
        body = json.loads(raw) if 'json' in response.get('Content-Type', '') else None
        observation = dict(route=route, label=label or route, status=response.status_code,
                           sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), body=body,
                           disposition=response.get('Content-Disposition'))
        evidence['observations'].append(observation)
        print(json.dumps({k:observation[k] for k in ('label','status','bytes')}), flush=True)
        response.close()
        if response.status_code != expected:
            evidence['failures'].append(dict(label=observation['label'], expected=expected,
                                            actual=response.status_code, body=body))
        return body, raw, observation

    try:
        with selected(run) as selection:
            evidence['selection'] = selection
            from tools.cohort3_wsgi import build_application
            build_application()  # actual production startup/request admission
            broad, restricted = actor_client(2), actor_client(3)
            request(Client(), 'GetLastRunDate', method='GET', expected=401, label='unauthenticated')
            base = dict(paginationParameter=dict(pageNumber=1, recordsPerPage=1000),
                        filters={name:dict(filters=[]) for name in (
                            'supplyChainFilter','locationFilter','productFilter','availabilityFilter',
                            'coverageFilter','colorFilter','generalFilter','customAttributeFilter','horizonFilter')})
            # Deliberately supplied browser scopes/user must be overwritten by
            # the real gateway's persisted application2 identity and grants.
            forged = dict(base, product_permissions=[71001], location_permissions=[72001],
                          user={'id':2,'name':'forged'})
            request(broad,'GetLastRunDate',method='GET')
            for route in ('DBMDataCount','DBMData','GetBPRDataCount','GetBPRData',
                          'GetBTRDataCount','GetBTRData','RRRDataCount','RRRData'):
                request(broad,route,base,label='broad-'+route)
                request(restricted,route,forged,label='restricted-'+route)
            observed = {item['label']: item['body'] for item in evidence['observations']}
            assert observed['GetLastRunDate']['data'][0]['rawDate'] == pin['date']
            for actor in ('broad', 'restricted'):
                bpr = observed[actor+'-GetBPRData']['data']
                assert len(bpr) == int(observed[actor+'-GetBPRDataCount']['recordCount'])
                assert bpr, 'BPR must have a real positive population'
                btr = observed[actor+'-GetBTRData']['data']
                counts = observed[actor+'-GetBTRDataCount']['data']
                for branch in ('tech', 'eco'):
                    assert len(btr[branch]) == int(counts[branch.title()+'Count'])
                    assert btr[branch], 'BTR must have a real positive population'
                if actor == 'restricted':
                    assert all(row['SKUCode']=='6120' and row['WHCode']=='DP010290' for row in bpr)
                    assert all(row['SKUCode']=='6120' and row['WhCode']=='DP010290'
                               for branch in ('tech','eco') for row in btr[branch])
            # Exact page slices, then a real filter with complete row equality.
            for page in (1, 2):
                payload = dict(base, paginationParameter=dict(pageNumber=page,recordsPerPage=3))
                body, _, _ = request(broad,'GetBPRData',payload,label='bpr-page-'+str(page))
                assert body['data'] == observed['broad-GetBPRData']['data'][(page-1)*3:page*3]
                body, _, _ = request(broad,'GetBTRData',payload,label='btr-page-'+str(page))
                for branch in ('tech','eco'):
                    assert body['data'][branch] == observed['broad-GetBTRData']['data'][branch][(page-1)*3:page*3]
            payload = deepcopy(base)
            payload['filters']['locationFilter']['filters'] = [dict(attributeName='location',value='DP010290')]
            body, _, _ = request(broad,'GetBPRData',payload,label='bpr-filter')
            assert body['data'] == [row for row in observed['broad-GetBPRData']['data'] if row['WHCode']=='DP010290']
            body, _, _ = request(broad,'GetBTRData',payload,label='btr-filter')
            for branch in ('tech','eco'):
                assert body['data'][branch] == [row for row in observed['broad-GetBTRData']['data'][branch] if row['WhCode']=='DP010290']
            request(broad,'GetRemarkDetails',dict(skucode='6120',whcode='DP010290'),label='declared-empty-remarks')
            for family in ('BPR','BTR','RRR'):
                request(broad,'GetExportDataAsync',dict(base,reportName=family),label=family+'-export')
            request(broad,'DailyDataGraph',dict(base,SKUCode='6120',WHCode='DP010290'))
            for kind in ('tech','eco'):
                request(broad,'GetBufferTrendGraphData',dict(base,days=2,bufferTrendType=kind),label='buffer-'+kind)
            request(broad,'GetResearchInsightData',dict(base,data=[dict(SKUCode='6120',WhCode='DP010290')]))
            request(broad,'GetHistroricalAvailabilityBPRData',method='GET')
            for route in ('AvailabilityTrend','AvailabilityAgeing','DBMNormSuggestionLoc',
                          'DBMNormSuggestionSKUs','DBMNormSuggestionPie','DBMNormSuggestionAgeing',
                          'ChronicUnavailabilityLoc','ChronicUnavailabilitySku','ChronicUnavailabilityGridViewData'):
                request(broad,route,dict(base,horison=2,ageing=1))
            request(broad,'GetPlanningDataCount',base)
            for category in ('excessInventory','orderFulfillment','git','expedite'):
                for kind in ('parent','child'):
                    payload = dict(base,category=category,type=kind)
                    for route in ('GetPlanningDataGrid','GetPlanningDataGridCount'):
                        request(broad,route,payload,label=category+'-'+kind+'-'+route)
                    if category != 'git' or kind == 'child':
                        request(broad,'GetPlanningDataGraph',payload,label=category+'-'+kind+'-graph')
                request(broad,'GetPlanningDataCustom',dict(base,category=category,type='custom'),label=category+'-custom')
            from mta.presentation.pick_downloads import REPORTS, _owned_file
            for report, filename in REPORTS.items():
                _, raw, observation = request(broad,'DownloadReports/'+report,method='GET')
                if observation['status'] == 200:
                    assert filename in observation['disposition']
                    assert raw == _owned_file(run,filename).read_bytes()
                request(restricted,'DownloadReports/'+report,method='GET',expected=403,label='restricted-'+report)
            request(broad,'BORData',base,expected=503,label='deferred-BOR')
            request(broad,'GetBOROrderAllocationReportData',base,expected=503,label='deferred-BOROA')
            before = admission.require_admission()
            connections.close_all()
            restarted = admission.admit()
            assert admission.require_admission() == before == restarted['admission_digest']
            request(broad,'GetLastRunDate',method='GET',label='readmitted-date')
            evidence['readmission'] = restarted
        assert admission._admitted is None
        assert not evidence['failures'], evidence['failures']
        evidence['status'] = 'AUTHENTICATED_CONSUMER_READBACK_PASS'
    except BaseException:
        evidence['status'] = 'FAILED'
        evidence['failure'] = traceback.format_exc()
        raise
    finally:
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump(evidence,stream,indent=2,default=str)


if __name__ == '__main__':
    main()
