"""Bind 3005 exact-wire proof to accepted oracle, source bytes and runtime image."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
target=Path(sys.argv[1]); target.mkdir(parents=True,exist_ok=False)
parent=Path('D:/freshvcf-build/evidence/f3-bpr-wire-001')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=dict(status='FAILED')
try:
    old=json.loads((parent/'receipt.json').read_text())
    assert old['status']=='PASS_TERMINAL_BPR_HTTP_WIRE'
    expected_path=parent/'expected.json.gz'
    assert sha(expected_path)==old['evidence_hashes']['expected.json.gz']
    expected=json.load(gzip.open(expected_path,'rt'))
    code='EXPECTED = json.loads('+repr(json.dumps(expected))+')\n'
    source=(root/'tools/bpr_gateway_probe.py').read_text().replace('base=\'http',code+'\nbase=\'http',1)
    run=subprocess.run(['docker','exec','-i','freshvcf-preview-user-service-1','python','-'],
        input=source,text=True,capture_output=True)
    (target/'stdout.json').write_text(run.stdout); (target/'stderr.log').write_text(run.stderr)
    if run.returncode: raise RuntimeError('Gateway proof failed; see stderr.log')
    runtime=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
    files=('mta/presentation/bpr.py','mta/presentation/bpr_read.py','mta/presentation/bpr_response.py',
        'mta/presentation/terminal_supplement.py','mta/presentation/views.py','baseline/presentation-terminal-v1.json')
    for name in files:
        embedded=subprocess.check_output(['docker','exec','freshvcf-preview-mta-1','sha256sum','/app/'+name],text=True).split()[0]
        assert embedded==sha(root/name),name
    result.update(status='PASS',proof=json.loads(run.stdout),runtime_image=runtime['Image'],
        source_hashes={n:sha(root/n) for n in files},caps=dict(memory=runtime['HostConfig']['Memory'],
            swap=runtime['HostConfig']['MemorySwap'],cpus=runtime['HostConfig']['NanoCpus']),
        parent_receipt_sha256=sha(parent/'receipt.json'),expected_wire_sha256=sha(expected_path),
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
except Exception as exc:
    result['error']=dict(type=type(exc).__name__,message=str(exc)); raise
finally:
    (target/'receipt.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(status=result['status'],image=result['runtime_image'],observations=result['proof']['observations'])))
