"""BTR-only real authenticated gateway and scope proof; execute in user-service."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import requests

from stage2_availability_probe import login


def main():
    root = Path(sys.argv[1])
    root.mkdir(exist_ok=False)
    credentials = json.load(open('/run/secrets/stage2-fixture-accounts.json'))
    results = []
    payload = dict(name='both', filters={'horizonFilter': {'filters': []}},
                   paginationParameter=dict(pageNumber=1, recordsPerPage=5000))
    for actor in ('broad', 'restricted'):
        with login(credentials[actor]) as session:
            for route in ('GetBTRDataCount', 'GetBTRData'):
                outcomes = []
                bodies = [payload]
                if actor == 'restricted':
                    bodies.append({**payload, 'product_permissions': list(range(1, 11)),
                                   'location_permissions': list(range(1, 78))})
                for index, body in enumerate(bodies):
                    started = time.monotonic()
                    response = session.post('http://frontend/api/mta/' + route, json=body, timeout=60)
                    seconds = time.monotonic() - started
                    assert response.status_code == 200, (actor, route, response.status_code)
                    value = response.json()
                    assert value['status'] == 200
                    filename = actor + '-' + route + '-' + str(index) + '.json.gz'
                    with gzip.open(root / filename, 'wb') as stream:
                        stream.write(response.content)
                    results.append(dict(actor=actor, route=route, forged=index == 1, status=response.status_code,
                        seconds=seconds, bytes=len(response.content), sha256=hashlib.sha256(response.content).hexdigest(),
                        file=filename, counts=value['data'] if route.endswith('Count') else None))
                    outcomes.append(value)
                assert all(value == outcomes[0] for value in outcomes), 'Body scopes escaped gateway grants'
    broad = next(r['counts'] for r in results if r['actor'] == 'broad' and r['counts'])
    restricted = next(r['counts'] for r in results if r['actor'] == 'restricted' and r['counts'])
    assert broad == dict(TechCount='97299', EcoCount='97299')
    assert restricted == dict(TechCount='5082', EcoCount='5082')
    denied = []
    with login(dict(email=os.environ['VECTORFLOW_TEST_USERNAME'],
                    password=os.environ['VECTORFLOW_TEST_PASSWORD'])) as session:
        for route in ('GetBTRDataCount', 'GetBTRData'):
            response = session.post('http://frontend/api/mta/' + route, json=payload, timeout=30)
            assert response.status_code == 403, (route, response.status_code)
            denied.append(dict(actor='normal-preview', route=route, status=response.status_code))
    for route in ('GetBTRDataCount', 'GetBTRData'):
        response = requests.post('http://frontend/api/mta/' + route, json=payload,
                                 headers={'Host': 'localhost:3005'}, timeout=30)
        assert response.status_code in (401, 403), (route, response.status_code)
        denied.append(dict(actor='unauthenticated', route=route, status=response.status_code))
    (root / 'result.json').write_text(json.dumps(dict(status='PASS', observations=results,
                                                   denied=denied), indent=2))
    print(json.dumps(dict(status='PASS', broad=broad, restricted=restricted)))


if __name__ == '__main__':
    main()
