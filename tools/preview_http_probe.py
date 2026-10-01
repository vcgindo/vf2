"""Real preview login/read-only gateway proof; no token/password in receipts.

Run inside the preview user-service (installed requests/PyCryptodome).
The host driver may feed this file to docker exec -i ... python -.
"""
import base64
import hashlib
import json
import os
import time

import requests
from Crypto.Cipher import AES


def probe(base):
    session = requests.Session()
    session.headers['Host'] = 'localhost'
    iv = os.urandom(16)
    cipher = AES.new(os.environ['SECRET_KEY_FOR_PASSWORD'].encode(), AES.MODE_CTR,
                     nonce=b'', initial_value=int.from_bytes(iv, 'big'))
    encrypted = base64.b64encode(iv + cipher.encrypt(os.environ['VECTORFLOW_TEST_PASSWORD'].encode())).decode()
    denied = session.get(base + '/api/mta/GetEnvironmentConfiguration', timeout=30)
    assert denied.status_code in (401, 403), denied.status_code
    result = session.post(base + '/api/user/login/', json={
        'email': os.environ['VECTORFLOW_TEST_USERNAME'], 'password': encrypted}, timeout=60)
    assert result.status_code == 200, (result.status_code, result.text)
    login = result.json()['data']
    assert login['user']['email'] == os.environ['VECTORFLOW_TEST_USERNAME']
    urls = login['url_permission']
    assert '/mta/dbm/dbm-norm-suggestions' in urls
    assert '/mta/insights-and-trends/buffer-trend-report' in urls
    assert session.cookies.get('access_token')
    payload = {'paginationParameter': {'pageNumber': 1, 'recordsPerPage': 10}}
    roster = [('GET', 'GetEnvironmentConfiguration', None),
              ('GET', 'LocationType', None),
              ('GET', 'GetAllReports', None), ('GET', 'GetLastRunDate', None),
              ('GET', 'GetUIConfig?reportName=NormSuggestion', None),
              ('POST', 'DBMDataCount', payload), ('POST', 'DBMData', payload),
              ('POST', 'GetBTRDataCount', payload), ('POST', 'GetBTRData', payload),
              ('POST', 'GetBufferTrendGraphData', {**payload, 'days': 12, 'bufferTrendType': 'tech'}),
              ('POST', 'RRRDataCount', payload),
              ('POST', 'GetPlanningDataGridCount', {**payload, 'category': 'orderFulfillment','type':'parent'})]
    if os.environ.get('PREVIEW_PROBE_RESTART') == '1':
        roster = [item for item in roster if item[1] in ('GetLastRunDate', 'LocationType', 'DBMData')]
    if os.environ.get('PREVIEW_PROBE_LAYOUT') == '1':
        roster = [('GET','GetUIConfig?reportName=NormSuggestion',None),
                  ('POST','GetState',{'reportname':'DBMNorm'}),
                  ('GET','GetLastRunDate',None),('POST','DBMData',payload)]
    hierarchy_mode=os.environ.get('PREVIEW_PROBE_HIERARCHY')=='1'
    visible_mode=os.environ.get('PREVIEW_PROBE_VISIBLE')=='1'
    if hierarchy_mode:
        payload['paginationParameter']['recordsPerPage']=5000
        roster=[('GET','GetLastRunDate',None),('POST','DBMDataCount',payload),('POST','DBMData',payload),
                ('POST','RRRDataCount',payload),('POST','RRRData',payload),
                ('POST','GetBTRDataCount',payload),('POST','GetBTRData',payload),
                ('POST','DailyDataGraph',{**payload,'SKUCode':'337','WHCode':'AG515802'})]
    if visible_mode:
        # Read-only landed-consumer roster. This is not independent parity or
        # browser acceptance; preserve bodies/populations for the UI matrix.
        empty_filters={name:dict(filters=[]) for name in ('supplyChainFilter',
            'locationFilter','productFilter','availabilityFilter','coverageFilter',
            'colorFilter','generalFilter','customAttributeFilter','horizonFilter')}
        payload={**payload,'filters':empty_filters}
        roster=[('GET','GetLastRunDate',None),('GET','GetAllReports',None)]
        roster += [('POST','GetBufferTrendGraphData',{**payload,'days':30,'bufferTrendType':kind}) for kind in ('tech','eco')]
        roster += [('POST',route,{**payload,'horison':9,'ageing':1}) for route in (
            'AvailabilityTrend','AvailabilityAgeing','DBMNormSuggestionLoc','DBMNormSuggestionSKUs',
            'DBMNormSuggestionPie','DBMNormSuggestionAgeing','ChronicUnavailabilityLoc',
            'ChronicUnavailabilitySku','ChronicUnavailabilityGridViewData')]
        roster += [('POST','GetResearchInsightData',{**payload,'data':[dict(SKUCode='337',WhCode='AG515802')]}),
                   ('GET','GetHistroricalAvailabilityBPRData',None)]
        for category in ('orderFulfillment','excessInventory'):
            roster += [('POST',route,{**payload,'category':category,'type':'parent'})
                       for route in ('GetPlanningDataGridCount','GetPlanningDataGrid','GetPlanningDataGraph')]
    observations = []
    for method, route, body in roster:
        started = time.monotonic()
        response = session.request(method, base + '/api/mta/' + route, json=body, timeout=180)
        assert response.status_code == 200, (route, response.status_code, response.text[:500])
        if os.environ.get('PREVIEW_PROBE_LAYOUT') == '1' and route.startswith('GetUIConfig'):
            rows=response.json()['data']
            assert len(rows)==16 and all(r['Visible'] and 'DataType' in r for r in rows)
        if os.environ.get('PREVIEW_PROBE_LAYOUT') == '1' and route=='GetState':
            assert response.json()['data']=='', 'Do not overwrite an existing preview layout'
        if hierarchy_mode:
            value=response.json()
            if route=='GetLastRunDate': assert value['data'][0]['rawDate']=='2026-06-17'
            elif route=='DBMDataCount': assert value['recordCount']=='0'
            elif route=='DBMData': assert value['data'] is None
            elif route=='RRRDataCount': assert value['recordCount']=='14'
            elif route=='RRRData': assert len(value['data'])==14
            elif route=='DailyDataGraph': assert value['data'] is not None
        observations.append(dict(route=route, status=response.status_code,
            sha256=hashlib.sha256(response.content).hexdigest(),
            body=response.json(), seconds=round(time.monotonic()-started,3)))
    return dict(status='PREVIEW_LOGIN_READBACK_PASS_NOT_F3_ACCEPTANCE',
        username=login['user']['email'], unauthenticated_status=denied.status_code,
        navigation=sorted(urls), observations=observations,
        qualification=('Landed-consumer visible-checkpoint API roster; exact terminal run and existing empty filters; not browser/independent parity proof.30-day charts include retained historical opening plus12 computed days.' if visible_mode else
            'Approved retained hierarchy supplement and root assignments; latest terminal day. Real gateway reads only; no actions submitted.'
            if hierarchy_mode else 'Inspect assignments and selected supplement from the matching receipt. This readback probe does not itself certify independent legacy parity. No actions submitted.'))


if __name__ == '__main__':
    print(json.dumps(probe(os.environ.get('PREVIEW_PROBE_BASE', 'http://host.docker.internal:3005'))))
