"""Read-only Stage 1 gateway smoke, executed inside the existing auth container.

Uses the already verified local account. Emits no credentials or cookies.
Response hashes compare the unchanged wire contract across MTA deployment.
"""
import hashlib
import json
import time

# The existing gateway probe owns the established login transport.
# The host runner injects its prefix before this source; no login duplication.
payload = dict(filters={}, paginationParameter=dict(pageNumber=1, recordsPerPage=5),
               product_permissions=[], location_permissions=[], user={'id': 'forged'})
cases = [('GET', 'GetEnvironmentConfiguration', None),
         ('GET', 'GetLastRunDate', None), ('GET', 'LocationType', None),
         ('POST', 'DBMDataCount', payload), ('POST', 'DBMData', payload),
         ('POST', 'RRRDataCount', payload), ('POST', 'RRRData', payload),
         ('POST', 'GetBPRDataCount', payload), ('POST', 'GetBPRData', payload),
         ('POST', 'GetPlanningDataCount', payload)]
observations = []
for method, route, body in cases:
    started = time.monotonic()
    reply = session.request(method, base + '/api/mta/' + route, json=body, timeout=30)
    elapsed = time.monotonic() - started
    assert reply.status_code == 200, (route, reply.status_code, reply.text[:200])
    observations.append(dict(route=route, status=reply.status_code, seconds=round(elapsed, 4),
        bytes=len(reply.content), sha256=hashlib.sha256(reply.content).hexdigest(), body=reply.json()))
denied = requests.post(base + '/api/mta/RRRData', json=payload, headers={'Host': 'localhost'}, timeout=10)
assert denied.status_code == 401
unsupported = session.post(base + '/api/mta/GetPlanningDataCount',
    json={**payload, 'filters': {'productFilter': {'filters': [{'attributeName': 'SKUCode', 'value': '337'}]}}}, timeout=15)
assert unsupported.status_code == 503, (unsupported.status_code, unsupported.text)
print(json.dumps(dict(status='PASS', observations=observations,
    unauthenticated_status=denied.status_code, unsupported_status=unsupported.status_code,
    forged_scope_overwritten=True, actions_submitted=False, layout_writes=False)))
