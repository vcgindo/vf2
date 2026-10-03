"""Run inside existing user-service: encrypted login and real gateway reads.

Secrets and cookies stay in process; only response bodies/digests leave it.
"""
import base64
import hashlib
import json
import os
import time
import requests
from Crypto.Cipher import AES

BASE='http://frontend'
credentials=json.load(open('/run/secrets/stage2-fixture-accounts.json'))
observations=[]


def login(credential):
    session=requests.Session();session.headers['Host']='localhost:3005'
    iv=os.urandom(16)
    cipher=AES.new(os.environ['SECRET_KEY_FOR_PASSWORD'].encode(),AES.MODE_CTR,nonce=b'',initial_value=int.from_bytes(iv,'big'))
    encrypted=base64.b64encode(iv+cipher.encrypt(credential['password'].encode())).decode()
    response=session.post(BASE+'/api/user/login/',json=dict(email=credential['email'],password=encrypted),timeout=90)
    if response.status_code!=200:raise RuntimeError('Fixture login status '+str(response.status_code))
    data=response.json()['data']
    assert data['user']['email']==credential['email']
    if credential['email'].startswith('stage2.'):assert not data['user']['is_admin']
    assert '/mta/dbm/dbm-norm-suggestions' in data['url_permission']
    assert session.cookies.get('access_token')
    return session


def read(session,actor,route,payload=None,expected=200,method='POST'):
    started=time.monotonic()
    response=session.request(method,BASE+'/api/mta/'+route,json=payload,timeout=175)
    try:body=response.json()
    except ValueError:body={'non_json_response':response.text[:1000]}
    observations.append(dict(actor=actor,route=route,status=response.status_code,seconds=round(time.monotonic()-started,3),sha256=hashlib.sha256(response.content).hexdigest(),body=body))
    if response.status_code!=expected:raise RuntimeError('Fixture route '+route+' status '+str(response.status_code)+': '+str(body)[:500])
    return body


def rows(value):
    value=value.get('data')
    return json.loads(value) if isinstance(value,str) and value else value


try:
    unauth=requests.get(BASE+'/api/mta/DBMData',headers={'Host':'localhost:3005'},timeout=30)
    assert unauth.status_code in (401,403)
    payload=dict(paginationParameter=dict(pageNumber=1,recordsPerPage=5))
    sessions={kind:login(credential) for kind,credential in credentials.items()}
    broad=sessions['broad'];restricted=sessions['restricted']
    date=read(broad,'broad','GetLastRunDate',method='GET')
    assert date['data'][0]['rawDate']=='2026-04-07'
    counts={kind:int(read(session,kind,'DBMDataCount',payload)['recordCount']) for kind,session in sessions.items()}
    assert 0<counts['restricted']<counts['broad']
    grids={kind:rows(read(session,kind,'DBMData',payload)) for kind,session in sessions.items()}
    assert all(grids.values())
    forged=read(restricted,'restricted-forged-body','DBMDataCount',{**payload,'product_permissions':list(range(1,10)),'location_permissions':list(range(1,61))})
    assert int(forged['recordCount'])==counts['restricted']
    sample=grids['restricted'][0]
    pair=dict(SKUCode=str(sample['SKUCode']),WHCode=str(sample.get('LocCode',sample.get('WhCode'))))
    graph=read(restricted,'restricted','DailyDataGraph',pair)
    assert rows(graph)
    for route in ('DBMApplySelectedNorms','DBMUpdateSleepTbl'):
        read(broad,'broad',route,{'data':[pair]},expected=403)
    # The unchanged normal preview account is deliberately outside fixture policy.
    normal=login(dict(email=os.environ['VECTORFLOW_TEST_USERNAME'],password=os.environ['VECTORFLOW_TEST_PASSWORD']))
    read(normal,'normal-preview-denied','DBMDataCount',payload,expected=403)
    # These existing readers still require production-only full output/ancillary
    # contracts; explicitly record unavailability rather than inventing them.
    for route,method,body in [('GetResearchInsightData','POST',{'data':[pair]}),('GetHistroricalAvailabilityBPRData','GET',None),('GetRemarkDetails','POST',pair),('GetBPRData','POST',payload)]:
        read(broad,'bounded-unavailable',route,body,expected=503,method=method)
    read(broad,'bounded-unavailable','GetPlanningDataGraph',{**payload,'category':'expedite','type':'parent'},expected=503)
    # Access/action denial evidence precedes wider reads so a retained consumer
    # timeout does not conceal the fixture boundary's safety proof.
    read(broad,'broad','RRRDataCount',payload)
    read(broad,'broad','RRRData',payload)
    read(broad,'broad','GetBTRData',payload)
    read(broad,'broad','GetPlanningDataGridCount',{**payload,'category':'orderFulfillment','type':'parent'})
    read(broad,'broad','GetPlanningDataGrid',{**payload,'category':'orderFulfillment','type':'parent'})
    print(json.dumps(dict(status='PASS_REPRESENTATIVE_AUTHENTICATED_FIXTURE',counts=counts,pair=pair,observations=observations)))
except Exception as exc:
    print(json.dumps(dict(status='FAILED',error=str(exc),counts=locals().get('counts'),pair=locals().get('pair'),observations=observations)))
    raise SystemExit(1)
