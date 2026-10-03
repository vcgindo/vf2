"""Small live security check for the four-page availability handoff.

Run inside the existing user-service. Credentials/cookies never leave process.
The browser supplies the separate visible-data proof.
"""
import base64
import json
import os
import requests
from Crypto.Cipher import AES


def login(credential):
    session=requests.Session();session.headers['Host']='localhost:3005'
    iv=os.urandom(16)
    cipher=AES.new(os.environ['SECRET_KEY_FOR_PASSWORD'].encode(),AES.MODE_CTR,nonce=b'',initial_value=int.from_bytes(iv,'big'))
    encrypted=base64.b64encode(iv+cipher.encrypt(credential['password'].encode())).decode()
    response=session.post('http://frontend/api/user/login/',json=dict(email=credential['email'],password=encrypted),timeout=30)
    assert response.status_code==200,response.status_code
    assert response.json()['data']['user']['email']==credential['email']
    return session


def main():
    credentials=json.load(open('/run/secrets/stage2-fixture-accounts.json'))
    observations=[]
    def read(session,actor,route,payload,expected):
        response=session.post('http://frontend/api/mta/'+route,json=payload,timeout=70)
        assert response.status_code==expected,(route,response.status_code)
        body=response.json()
        observations.append(dict(actor=actor,route=route,status=response.status_code,body=body))
        return body
    broad=login(credentials['broad']);restricted=login(credentials['restricted'])
    for route in ('DBMApplySelectedNorms','DBMUpdateSleepTbl'):
        read(broad,'broad',route,{'data':[]},403)
    payload=dict(paginationParameter=dict(pageNumber=1,recordsPerPage=5))
    count=read(restricted,'restricted','DBMDataCount',payload,200)['recordCount']
    forged=read(restricted,'restricted-forged-body','DBMDataCount',
        {**payload,'product_permissions':list(range(1,10)),'location_permissions':list(range(1,61))},200)['recordCount']
    assert int(count)==1036 and count==forged
    normal=login(dict(email=os.environ['VECTORFLOW_TEST_USERNAME'],password=os.environ['VECTORFLOW_TEST_PASSWORD']))
    read(normal,'normal-preview-denied','DBMDataCount',payload,403)
    unauth=requests.post('http://frontend/api/mta/DBMDataCount',json=payload,headers={'Host':'localhost:3005'},timeout=30)
    assert unauth.status_code in (401,403)
    print(json.dumps(dict(status='PASS',actions_disabled=True,normal_actor_denied=True,
        unauthenticated_denied=True,restricted_count=int(count),forged_grants_ignored=True,observations=observations)))


if __name__=='__main__':main()
