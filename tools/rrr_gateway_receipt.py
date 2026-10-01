"""Retain redacted 3005 HTTP receipt with exact candidate image/source identity."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

target=Path(sys.argv[1]); target.mkdir(parents=True,exist_ok=False)
source=Path('tools/rrr_gateway_probe.py').read_bytes()
result=subprocess.run(['docker','exec','-i','freshvcf-preview-user-service-1','python','-'],
    input=source.decode(),text=True,capture_output=True)
(target/'stdout.json').write_text(result.stdout,encoding='utf-8')
(target/'stderr.txt').write_text(result.stderr,encoding='utf-8')
(target/'probe-source.py').write_bytes(source)
runtime=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
receipt=dict(exit_code=result.returncode,container=runtime['Id'],image=runtime['Image'],
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    dirty_source_hashes={str(p).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path('mta/presentation')/name for name in ('context.py','selective.py','rrr_sql.py','views.py')]},
    probe_sha256=hashlib.sha256(source).hexdigest())
if result.returncode==0: receipt['proof']=json.loads(result.stdout)
(target/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(dict(exit_code=result.returncode,receipt=str(target/'receipt.json'),stderr=result.stderr[-1200:])))
raise SystemExit(result.returncode)
