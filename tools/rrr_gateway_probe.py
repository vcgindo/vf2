"""Actual authenticated 3005 gateway timing/read proof; no browser claim."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import time

import requests
from Crypto.Cipher import AES

base='http://host.docker.internal:3005'
session=requests.Session(); session.headers['Host']='localhost'
iv=os.urandom(16)
cipher=AES.new(os.environ['SECRET_KEY_FOR_PASSWORD'].encode(),AES.MODE_CTR,nonce=b'',initial_value=int.from_bytes(iv,'big'))
encrypted=base64.b64encode(iv+cipher.encrypt(os.environ['VECTORFLOW_TEST_PASSWORD'].encode())).decode()
denied=session.get(base+'/api/mta/RRRDataCount',timeout=10)
assert denied.status_code in (401,403)
login=session.post(base+'/api/user/login/',json={'email':os.environ['VECTORFLOW_TEST_USERNAME'],'password':encrypted},timeout=15)
assert login.status_code==200
assert '/mta/supply-chain-intelligence-hub/rrr' in login.json()['data']['url_permission']
payload={'paginationParameter':{'pageNumber':1,'recordsPerPage':5000},'filters':{}}
observations=[]


def request(route,body=None,phase='warm'):
    local=requests.Session(); local.headers.update(session.headers); local.cookies.update(session.cookies)
    started=time.monotonic()
    response=local.request('POST' if body is not None else 'GET',base+'/api/mta/'+route,json=body,timeout=10)
    seconds=time.monotonic()-started
    assert response.status_code==200,(route,response.status_code,response.text[:300])
    assert seconds<=2,(route,seconds)
    value=response.json()
    if route=='RRRDataCount':
        expected='3' if (body.get('filters') or {}).get('supplyChainFilter') else '14'
        assert value['recordCount']==expected
    if route=='RRRData':
        expected=3 if (body.get('filters') or {}).get('supplyChainFilter') else 14
        assert len(value['data'])==expected
        if expected==3: assert {r['WhCode'] for r in value['data']}=={'AG515802'}
    if route=='GetLastRunDate': assert value['data'][0]['rawDate']=='2026-06-17'
    return dict(route=route,phase=phase,status=response.status_code,seconds=round(seconds,4),
        body=value,body_sha256=hashlib.sha256(response.content).hexdigest())


for phase in ('first_gateway_read_after_deploy','warm'):
    for route,body in (('GetLastRunDate',None),('LocationType',None),('RRRDataCount',payload),('RRRData',payload)):
        observations.append(request(route,body,phase))
filtered={**payload,'filters':{'supplyChainFilter':{'filters':[dict(attributeName='forlocation',operator='equalto',value='Agen')]}}}
for route in ('RRRDataCount','RRRData'): observations.append(request(route,filtered,'selected_filter'))
# The gateway must replace asserted permission lists, not trust client scope.
observations.append(request('RRRDataCount',{**payload,'product_permissions':[],'location_permissions':[]},'forged_scope_ignored'))
started=time.monotonic()
with ThreadPoolExecutor(max_workers=4) as executor:
    jobs=[executor.submit(request,route,body,'concurrent_four') for route,body in
          (('GetLastRunDate',None),('LocationType',None),('RRRDataCount',payload),('RRRData',payload))]
    observations.extend(job.result() for job in jobs)
concurrent_seconds=round(time.monotonic()-started,4)
assert concurrent_seconds<=5,concurrent_seconds
print(json.dumps(dict(status='RRR_REAL_GATEWAY_TIMING_READBACK_PASS_NOT_BROWSER_ACCEPTANCE',
    username=os.environ['VECTORFLOW_TEST_USERNAME'],date='2026-06-17',
    unauthenticated_status=denied.status_code,concurrent_seconds=concurrent_seconds,
    thresholds=dict(individual_seconds=2,batch_seconds=5),
    actions_submitted=False,observations=observations,
    qualification='First gateway reads after candidate deployment; database pages already warm from retained semantic proof. No cold-disk claim or legacy timing claim.')))
