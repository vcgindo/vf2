"""Actual3005 cookie BPR readback. Expected wire rows injected by owned runner."""
import base64
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
password=base64.b64encode(iv+cipher.encrypt(os.environ['VECTORFLOW_TEST_PASSWORD'].encode())).decode()
login=session.post(base+'/api/user/login/',json={'email':os.environ['VECTORFLOW_TEST_USERNAME'],'password':password},timeout=15)
assert login.status_code==200
observed=[]
for case_id,page,size in (('root-regression',1,5000),('root-page-2',2,5),('root-page-249',249,5)):
    payload=dict(product_permissions=[],location_permissions=[],user={'id':'forged'},filters={},
        paginationParameter=dict(pageNumber=page,recordsPerPage=size))
    expected=next(c for c in EXPECTED if c['id']==case_id)
    for route,key,wanted in (('GetBPRDataCount','recordCount',expected['count']),('GetBPRData','data',expected['grid'])):
        started=time.monotonic()
        reply=session.post(base+'/api/mta/'+route,json=payload,timeout=15)
        elapsed=time.monotonic()-started
        assert reply.status_code==200,(route,reply.status_code,reply.text[:200])
        assert reply.json()[key]==wanted,(case_id,route,'complete wire mismatch')
        observed.append(dict(case=case_id,route=route,status=reply.status_code,seconds=round(elapsed,4),
            response_sha256=hashlib.sha256(reply.content).hexdigest(),rows=len(wanted) if key=='data' else wanted))
denied=requests.post(base+'/api/mta/GetBPRData',json={},headers={'Host':'localhost'},timeout=10)
assert denied.status_code==401
print(json.dumps(dict(status='PASS_ACTUAL_3005_BPR_COOKIE_READBACK',observations=observed,
    forged_scope_and_identity_overwritten=True,unauthenticated_status=denied.status_code,
    actions_submitted=False,layout_writes=False)))
