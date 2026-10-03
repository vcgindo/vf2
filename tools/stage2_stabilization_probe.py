"""Bounded full-fixture traffic through3005, run in an isolated probe container.

No engine/database mutation. Credentials remain process-local. /proof is the
owned external evidence directory; report bodies are compressed there, not Git.
"""
import concurrent.futures
import gzip
import hashlib
import json
from pathlib import Path
import threading
import time

import requests
from stage2_availability_probe import login

PAGES = (
    ('RRR', 'RRRData', 'RRRDataCount', 5000),
    ('BPR', 'GetBPRData', 'GetBPRDataCount', 50),
    ('BTR', 'GetBTRData', 'GetBTRDataCount', 5000),
    ('DBM', 'DBMData', 'DBMDataCount', 5000),
)


def run(phase, *, overlap=False, overlap_rounds=2, include_chronic=True, repetitions=2,
        login_during_overlap=False):
    root = Path('/proof') / phase
    root.mkdir(exist_ok=False)
    credentials = json.load(open('/run/secrets/stage2-fixture-accounts.json'))
    authenticated = login(credentials['broad'])
    observations, profiles = [], []
    stop = threading.Event()

    def session():
        result = requests.Session()
        result.headers.update(authenticated.headers)
        result.cookies.update(authenticated.cookies)
        return result

    def profile_loop():
        with session() as client:
            while not stop.is_set():
                started = time.monotonic()
                try:
                    response = client.get('http://frontend/api/user/profile/', timeout=65)
                    status = response.status_code
                except requests.RequestException as error:
                    status = type(error).__name__
                profiles.append(dict(status=status, seconds=round(time.monotonic()-started,3)))
                stop.wait(1)

    def read(route, size, repetition, body=None, abort=False):
        payload = body if body is not None else dict(name='both', filters={},
            paginationParameter=dict(pageNumber=1, recordsPerPage=size))
        started = time.monotonic()
        path = root / f'{repetition}-{route}.json.gz'
        try:
            with session() as client, client.post('http://frontend/api/mta/'+route,
                    json=payload, timeout=65, stream=True) as response:
                first = time.monotonic()-started
                digest, count = hashlib.sha256(), 0
                with gzip.open(path,'wb') as output:
                    for chunk in response.iter_content(65536):
                        output.write(chunk); digest.update(chunk); count += len(chunk)
                        if abort:
                            break
                return dict(route=route,status=response.status_code,bytes=count,
                    sha256=digest.hexdigest(),seconds=round(time.monotonic()-started,3),
                    headers_seconds=round(first,3),aborted=abort,body=path.name)
        except requests.RequestException as error:
            return dict(route=route,status=type(error).__name__,seconds=round(time.monotonic()-started,3))

    monitor = threading.Thread(target=profile_loop)
    monitor.start()
    try:
        # Sequential page journeys, each with its actual concurrent count/grid.
        for repetition in range(repetitions):
            for page, grid, count, size in PAGES:
                started = time.monotonic()
                with concurrent.futures.ThreadPoolExecutor(2) as pool:
                    pending = [pool.submit(read, route, size, repetition) for route in (grid,count)]
                    result = [item.result() for item in pending]
                observations.append(dict(page=page,repetition=repetition,
                    seconds=round(time.monotonic()-started,3),requests=result))
                print(json.dumps(observations[-1]),flush=True)
        if overlap:
            def concurrent_login():
                time.sleep(1)  # Let the report burst enter the upstream queue.
                started = time.monotonic()
                try:
                    with login(credentials['broad']):
                        return dict(route='real_login_during_overlap',status=200,
                                    seconds=round(time.monotonic()-started,3))
                except (requests.RequestException, AssertionError) as error:
                    return dict(route='real_login_during_overlap',status=type(error).__name__,
                                seconds=round(time.monotonic()-started,3))
            # All four supported page pairs outstanding, then the observed
            # Chronic request. No claim of whole-page Guided acceptance.
            for repetition in range(overlap_rounds):
                with concurrent.futures.ThreadPoolExecutor(10) as pool:
                    pending = [pool.submit(read,route,size,'overlap'+str(repetition))
                        for _,grid,count,size in PAGES for route in (grid,count)]
                    if include_chronic:
                        pending.append(pool.submit(read,'ChronicUnavailabilityLoc',0,
                            'overlap'+str(repetition),{}))
                    if login_during_overlap:
                        pending.append(pool.submit(concurrent_login))
                    result=[item.result() for item in pending]
                observations.append(dict(pattern='overlap',repetition=repetition,requests=result))
                print(json.dumps(observations[-1]),flush=True)
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                aborted=list(pool.map(lambda route: read(route,5000,'abort',abort=True),
                    ('GetBTRData','RRRData')))
            observations.append(dict(pattern='abort_during_body',requests=aborted))
        # A fresh real login, not merely reuse of a previous cookie.
        with login(credentials['broad']) as fresh:
            last=fresh.get('http://frontend/api/user/profile/',timeout=10)
            assert last.status_code==200,last.status_code
    finally:
        stop.set();monitor.join()
        result=dict(phase=phase,observations=observations,profiles=profiles,
                    profile_failures=sum(item['status']!=200 for item in profiles))
        (root/'result.json').write_text(json.dumps(result,indent=2))
    return result
