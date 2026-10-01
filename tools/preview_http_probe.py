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
        observations.append(dict(route=route, status=response.status_code,
            sha256=hashlib.sha256(response.content).hexdigest(),
            body=response.json(), seconds=round(time.monotonic()-started,3)))
    return dict(status='PREVIEW_LOGIN_READBACK_PASS_NOT_F3_ACCEPTANCE',
        username=login['user']['email'], unauthenticated_status=denied.status_code,
        navigation=sorted(urls), observations=observations,
        qualification='No product/location assignments provisioned; native NULL hierarchy remains unchanged. Empty scoped rows are not positive parity. No actions submitted.')


if __name__ == '__main__':
    print(json.dumps(probe(os.environ.get('PREVIEW_PROBE_BASE', 'http://host.docker.internal:3005'))))
