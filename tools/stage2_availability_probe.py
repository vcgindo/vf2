"""Four-page restricted reads through the existing authenticated3005 gateway.

Execute inside user-service through Python stdin. Credentials and cookies stay
in the process. Login uses the same existing encrypted-password contract as
stage2_visible_probe.py.
Browser rendering is proved separately; these reads do not certify whole pages.
"""
import base64
import hashlib
import json
import os
import time

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


def availability():
    credentials = json.load(open('/run/secrets/stage2-fixture-accounts.json'))
    session = login(credentials['restricted'])
    observations = []
    payload = dict(paginationParameter=dict(pageNumber=1, recordsPerPage=5))
    forged = dict(payload, product_permissions=list(range(1, 11)),
                  location_permissions=list(range(1, 78)))

    def read(route, body):
        start = time.monotonic()
        response = session.post('http://frontend/api/mta/' + route, json=body, timeout=65)
        value = response.json()
        observations.append(dict(route=route, status=response.status_code,
            seconds=round(time.monotonic()-start, 3),
            sha256=hashlib.sha256(response.content).hexdigest(), body=value))
        assert response.status_code == 200, (route, response.status_code, value)
        return value

    for page, count_route, grid_route, maximum in (
        ('RRR', 'RRRDataCount', 'RRRData', 8063),
        ('BPR', 'GetBPRDataCount', 'GetBPRData', 97097),
        ('BTR', 'GetBTRDataCount', 'GetBTRData', 97299),
        ('DBM', 'DBMDataCount', 'DBMData', 11158),
    ):
        counted = read(count_route, payload)
        assert read(count_route, forged) == counted, 'Forged scope changed count: ' + page
        counts = counted['data'].values() if page == 'BTR' else [counted['recordCount']]
        assert all(0 < int(n) < maximum for n in counts), (page, counted)
        grid = read(grid_route, payload)['data']
        if isinstance(grid, str):
            grid = json.loads(grid)
        assert grid and (page != 'BTR' or grid['tech'] and grid['eco']), page
    return dict(status='PASS', actor='restricted', forged_grants_ignored=True,
                pages=['RRR', 'BPR', 'BTR', 'DBM'], observations=observations)


def latency():
    """Real gateway wall times at unchanged UI page sizes; no profiler/cache."""
    from concurrent.futures import ThreadPoolExecutor
    credentials = json.load(open('/run/secrets/stage2-fixture-accounts.json'))
    authenticated = login(credentials['broad'])
    observations = []
    for repetition in range(3):
        for page, grid, count, size in (
            ('RRR', 'RRRData', 'RRRDataCount', 5000),
            ('BPR', 'GetBPRData', 'GetBPRDataCount', 50),
            ('BTR', 'GetBTRData', 'GetBTRDataCount', 5000),
            ('DBM', 'DBMData', 'DBMDataCount', 5000),
        ):
            payload = dict(paginationParameter=dict(pageNumber=1, recordsPerPage=size),
                           name='both', filters={})
            def read(route):
                session = requests.Session()
                session.headers.update(authenticated.headers)
                session.cookies.update(authenticated.cookies)
                started = time.monotonic()
                response = session.post('http://frontend/api/mta/' + route, json=payload, timeout=65)
                elapsed = time.monotonic() - started
                assert response.status_code == 200, (route, response.status_code)
                body = response.json()
                data = body.get('data')
                if isinstance(data, str):
                    data = json.loads(data)
                rows = ({key: len(data[key]) for key in ('tech','eco')} if page == 'BTR' else len(data)) if route == grid else None
                return dict(route=route, seconds=round(elapsed,3), status=response.status_code,
                    bytes=len(response.content), sha256=hashlib.sha256(response.content).hexdigest(),
                    rows=rows, counts=data if page == 'BTR' and route == count else body.get('recordCount'))
            started = time.monotonic()
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(read, (grid, count)))
            observations.append(dict(page=page, repetition=repetition + 1, page_size=size,
                concurrent_wall_seconds=round(time.monotonic()-started,3), requests=results))
    return dict(status='PASS', actor='broad', concurrency=2, profiler=False,
                acceptance='Observed gateway timings, not a matched legacy performance benchmark',
                observations=observations)


if __name__ == '__main__':
    import sys
    print(json.dumps(latency() if sys.argv[1:] == ['latency'] else availability()))
