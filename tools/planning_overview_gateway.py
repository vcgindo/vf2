"""Verify deployed3005 overview against the retained SQL count receipt."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
target=Path(sys.argv[1]); target.mkdir(parents=True,exist_ok=False)
parent=Path(sys.argv[2])
result=dict(status='FAILED')
try:
    receipt=json.loads((parent/'receipt.json').read_text())
    assert receipt['status']=='PASS_TEN_PLANNING_OVERVIEW_COUNTS' and not receipt['differences']
    assert sha(parent/'legacy.json.gz')==receipt['file_hashes']['legacy.json.gz']
    for name,digest in receipt['source_hashes'].items(): assert sha(ROOT/name)==digest,name
    with gzip.open(parent/'legacy.json.gz','rt') as stream:
        expected=next(c['data'] for c in json.load(stream) if c['id']=='root-regression')
    # Reuse only the existing login transport; secrets stay in the owned auth
    # container environment and never enter a file or command-line argument.
    source=(ROOT/'tools/bpr_gateway_probe.py').read_text().split('observed=[]',1)[0]
    source+='\nEXPECTED='+repr(expected)+'\n'
    source+='''
observed=[]
for forged in (False,True):
    payload={'filters':{}}
    if forged: payload.update(product_permissions=[],location_permissions=[],user={'id':'forged'})
    started=time.monotonic()
    reply=session.post(base+'/api/mta/GetPlanningDataCount',json=payload,timeout=30)
    assert reply.status_code==200,(reply.status_code,reply.text[:300])
    assert reply.json()['data']==EXPECTED,('exact ten-count mismatch',reply.json())
    observed.append(dict(forged_scope=forged,response_sha256=hashlib.sha256(reply.content).hexdigest(),
        seconds=round(time.monotonic()-started,4),data=reply.json()['data']))
denied=requests.post(base+'/api/mta/GetPlanningDataCount',json={},headers={'Host':'localhost'},timeout=10)
assert denied.status_code==401
filtered=session.post(base+'/api/mta/GetPlanningDataCount',json={'filters':{'productFilter':{
    'filters':[{'attributeName':'SKUCode','value':'337'}]}}},timeout=15)
assert filtered.status_code==503
print(json.dumps(dict(status='PASS_ACTUAL_3005_OVERVIEW',observations=observed,
    unauthenticated_status=denied.status_code,unsupported_filter_status=filtered.status_code,
    actions_submitted=False,layout_writes=False)))
'''
    process=subprocess.run(['docker','exec','-i','freshvcf-preview-user-service-1','python','-'],
        input=source,text=True,capture_output=True)
    (target/'stdout.json').write_text(process.stdout); (target/'stderr.log').write_text(process.stderr)
    if process.returncode: raise RuntimeError('Gateway proof failed; see stderr.log')
    runtime=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
    for name in receipt['source_hashes']:
        if name.startswith('tools/'): continue
        embedded=subprocess.check_output(['docker','exec','freshvcf-preview-mta-1','sha256sum','/app/'+name],text=True).split()[0]
        assert embedded==sha(ROOT/name),name
    result.update(status='PASS',proof=json.loads(process.stdout),image=runtime['Image'],
        parent_receipt_sha256=sha(parent/'receipt.json'),source_hashes=receipt['source_hashes'],
        memory=runtime['HostConfig']['Memory'],swap=runtime['HostConfig']['MemorySwap'],
        cpus=runtime['HostConfig']['NanoCpus'])
except Exception as exc:
    result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
finally:
    (target/'receipt.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(status=result['status'],image=result['image'],observations=result['proof']['observations'])))
