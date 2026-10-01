"""Actual3005 cookie gateway for selective current DBM and daily history."""
import base64
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from Crypto.Cipher import AES

base = 'http://host.docker.internal:3005'
session = requests.Session()
session.headers['Host'] = 'localhost'
iv = os.urandom(16)
cipher = AES.new(os.environ['SECRET_KEY_FOR_PASSWORD'].encode(), AES.MODE_CTR,
                 nonce=b'', initial_value=int.from_bytes(iv, 'big'))
password = base64.b64encode(iv + cipher.encrypt(os.environ['VECTORFLOW_TEST_PASSWORD'].encode())).decode()
login = session.post(base + '/api/user/login/', json={'email': os.environ['VECTORFLOW_TEST_USERNAME'],
                    'password': password}, timeout=15)
assert login.status_code == 200
assert '/mta/dbm/dbm-norm-suggestions' in login.json()['data']['url_permission']
base_payload = {'paginationParameter': {'pageNumber': 1, 'recordsPerPage': 5000}, 'filters': {},
                'product_permissions': [], 'location_permissions': [], 'user': {'id': 'forged'}}


def request(route, payload):
    local = requests.Session()
    local.cookies.update(session.cookies)
    local.headers.update(session.headers)
    started = time.monotonic()
    response = local.post(base + '/api/mta/' + route, json=payload, timeout=15)
    seconds = time.monotonic() - started
    assert response.status_code == 200, (route, response.status_code, response.text[:300])
    value = response.json()
    if route == 'DBMDataCount':
        assert value['recordCount'] == '0'
    elif route == 'DBMData':
        assert value['data'] is None
    else:
        assert len(value['data']) == 1 and value['data'][0]['RunDate'][:10] == '2026-06-17'
        assert value['data'][0]['StockData'] and value['data'][0]['MasterData']
    return dict(route=route, seconds=round(seconds, 4), status=response.status_code,
        response_sha256=hashlib.sha256(response.content).hexdigest(),
        populations={k: len(v or []) for k, v in value['data'][0].items() if isinstance(v, list) or v is None}
                    if route == 'DailyDataGraph' else None)


graph = {**base_payload, 'SKUCode': '337', 'WHCode': 'AG515802'}
observations = [request(route, body) for route, body in (
    ('DBMDataCount', base_payload), ('DBMData', base_payload), ('DailyDataGraph', graph))]
with ThreadPoolExecutor(max_workers=3) as executor:
    jobs = [executor.submit(request, route, body) for route, body in (
        ('DBMDataCount', base_payload), ('DBMData', base_payload), ('DailyDataGraph', graph))]
    observations += [job.result() for job in jobs]
denied = requests.post(base+'/api/mta/DBMData', json=base_payload, headers={'Host': 'localhost'}, timeout=10)
assert denied.status_code in (401, 403)
print(json.dumps(dict(status='PASS_3005_CURRENT_DBM_HISTORY_REAL_COOKIE_GATEWAY',
    username=os.environ['VECTORFLOW_TEST_USERNAME'], terminal_current_count=0,
    forged_identity_and_scopes_overwritten=True, unauthenticated_status=denied.status_code,
    observations=observations, actions_submitted=False, scope='Current terminal and selected337/AG515802 history; not eligible-action UI acceptance')))
