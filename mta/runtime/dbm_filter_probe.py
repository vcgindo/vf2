"""Finite pre-action reads on a newly accepted retained trial; no row writes."""
from copy import deepcopy
import gzip
import json
from django.test import Client
from mta.presentation.context import publication
from mta.runtime.management.commands.verify_application_reads import run_identity
from parity.dbm_filter_cases import cases
from parity.output_archive import file_sha


def export_reads(target,post,stdout):
    context=publication(); before=run_identity(context.run)
    if context.hierarchy_receipt is None: raise ValueError('Explicit retained hierarchy binding required')
    roster=cases(); (target/'dbm-cases.json').write_text(json.dumps(dict(cases=roster),indent=2))
    result=dict(boundary='RETAINED_DAY_ZERO_PRE_ACTION_DBM_FILTERS',run=before,
        hierarchy_supplement=context.hierarchy_receipt,cases_sha256=file_sha(target/'dbm-cases.json'),observations=[])
    status,_=post('DBMDataCount',roster[0]['payload'],False)
    if status!=401:raise ValueError('Missing-cookie DBM request was not rejected')
    result['unauthenticated_status']=status
    client=Client(); private_headers={'HTTP_X_VECTORFLOW_IDENTITY':'{"id":"isolated-dbm-leaf-contract"}'}
    for index,case in enumerate(roster):
        payload=case['payload']
        root=payload['product_permissions']==[71001] and payload['location_permissions']==[72001]
        for route in ('DBMDataCount','DBMData'):
            wire=deepcopy(payload)
            if root:
                wire.update(product_permissions=[],location_permissions=[],user={'id':'forged-body'})
                status,response=post(route,wire)
                transport='ACTUAL_COOKIE_GATEWAY_STORED_ROOTS'
            else:
                response_obj=client.post('/api/mta/'+route,json.dumps(payload),content_type='application/json',**private_headers)
                status,response=response_obj.status_code,response_obj.json()
                transport='PRIVATE_ASSERTED_LEAF_SCOPE_NOT_LEAF_LOGIN'
            name='dbm-response-%02d-%s.json.gz'%(index,route)
            with gzip.open(target/name,'wt') as stream:
                json.dump(dict(case_id=case['id'],route=route,request=payload,wire_request=wire,
                    transport=transport,status=status,response=response),stream)
            result['observations'].append(dict(case_id=case['id'],route=route,file=name,sha256=file_sha(target/name),transport=transport))
            if status!=(503 if case['sql_error'] else 200):raise ValueError('Unexpected DBM status: '+case['id']+' '+route)
        stdout.write(case['id']+' DBM readback exported');stdout.flush()
    if before!=run_identity(context.run):raise ValueError('Read-only DBM request changed run/actions')
    result.update(accepted_pre_action_run_unchanged=True,requests=len(result['observations']),
        real_gateway_requests=sum(r['transport']=='ACTUAL_COOKIE_GATEWAY_STORED_ROOTS' for r in result['observations']))
    return result
