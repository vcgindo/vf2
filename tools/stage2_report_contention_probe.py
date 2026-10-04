"""Finite full-fixture report diagnostic; bodies stay in owned external evidence.

Run in the isolated probe container with PROFILE_ROUTE selecting one phase.
Failures are retained, never treated as expected successful report responses.
"""
import concurrent.futures
import gzip
import hashlib
import json
import os
from pathlib import Path
import threading
import time

import requests
from stage2_availability_probe import login

ROUTES = (('RRRData', 5000), ('RRRDataCount', 5000),
          ('GetBPRData', 50), ('GetBPRDataCount', 50),
          ('GetBTRData', 5000), ('GetBTRDataCount', 5000),
          ('DBMData', 5000), ('DBMDataCount', 5000), ('ChronicUnavailabilityLoc', 0))


def run(phase):
    root = Path(os.environ.get('PROFILE_EVIDENCE_ROOT', '/proof')) / phase
    root.mkdir(exist_ok=False)
    credentials = json.load(open('/run/secrets/stage2-fixture-accounts.json'))
    authenticated = login(credentials['broad'])
    active = set()
    lock = threading.Lock()
    stopped = threading.Event()
    profiles = []
    results = []

    def pending():
        with lock:
            return sorted(active)

    def session():
        result = requests.Session()
        result.headers.update(authenticated.headers)
        result.cookies.update(authenticated.cookies)
        return result

    def read(route, size):
        start = time.time()
        with lock:
            active.add(route)
        payload = {} if not size else dict(name='both', filters={},
            paginationParameter=dict(pageNumber=1, recordsPerPage=size))
        try:
            with session() as client, client.post('http://frontend/api/mta/' + route,
                    json=payload, timeout=65, stream=True) as response:
                headers_at = time.time()
                digest = hashlib.sha256()
                count = 0
                with gzip.open(root / (route + '.json.gz'), 'wb') as output:
                    for chunk in response.iter_content(65536):
                        output.write(chunk)
                        digest.update(chunk)
                        count += len(chunk)
                return dict(route=route, status=response.status_code, started_at=start,
                    headers_at=headers_at, completed_at=time.time(), seconds=time.time()-start,
                    bytes=count, sha256=digest.hexdigest())
        except requests.RequestException as exc:
            return dict(route=route, status=type(exc).__name__, started_at=start,
                        completed_at=time.time(), seconds=time.time()-start)
        finally:
            with lock:
                active.discard(route)

    def profile_loop():
        with session() as client:
            while not stopped.is_set():
                start = time.time()
                before = pending()
                try:
                    response = client.get('http://frontend/api/user/profile/', timeout=10)
                    status = response.status_code
                except requests.RequestException as exc:
                    status = type(exc).__name__
                profiles.append(dict(status=status, started_at=start, seconds=time.time()-start,
                                     outstanding_before=before, outstanding_after=pending()))
                stopped.wait(1)

    def fresh_login():
        time.sleep(1)
        start = time.time()
        before = pending()
        try:
            with login(credentials['broad']):
                status = 200
        except (requests.RequestException, AssertionError) as exc:
            status = type(exc).__name__
        return dict(route='fresh_login', status=status, started_at=start,
                    seconds=time.time()-start, outstanding_before=before, outstanding_after=pending())

    watcher = threading.Thread(target=profile_loop)
    watcher.start()
    try:
        if phase.endswith('individual'):
            for route, size in ROUTES:
                result = read(route, size)
                results.append(result)
                print(json.dumps(result), flush=True)
        elif phase.endswith('pairs'):
            for index in range(0, 8, 2):
                with concurrent.futures.ThreadPoolExecutor(2) as pool:
                    values = [pool.submit(read, *r) for r in ROUTES[index:index+2]]
                    results.extend(f.result() for f in values)
        else:
            routes = ROUTES[:8] if phase.endswith('eight') else ROUTES
            with concurrent.futures.ThreadPoolExecutor(10) as pool:
                values = [pool.submit(read, *r) for r in routes]
                identity = pool.submit(fresh_login)
                results.extend(f.result() for f in values)
                results.append(identity.result())
    finally:
        stopped.set()
        watcher.join()
        result = dict(phase=phase, requests=results, profiles=profiles,
            failures=sum(r['status'] != 200 for r in results),
            profile_failures=sum(r['status'] != 200 for r in profiles))
        (root / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(phase=phase, failures=result['failures'],
        profile_failures=result['profile_failures'], max_seconds=max(r['seconds'] for r in results))), flush=True)


if __name__ == '__main__':
    run(os.environ['PROFILE_ROUTE'])
