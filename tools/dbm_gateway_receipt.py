"""Retain isolated preview readback and source/image binding."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

target = Path(sys.argv[1])
target.mkdir(parents=True, exist_ok=False)
source = Path('tools/dbm_gateway_probe.py').read_text()
call = subprocess.run(['docker', 'exec', '-i', 'freshvcf-preview-user-service-1', 'python', '-'],
                      input=source, text=True, capture_output=True)
(target/'stdout.json').write_text(call.stdout)
(target/'stderr.log').write_text(call.stderr)
runtime = json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
receipt = dict(exit_code=call.returncode, image=runtime['Image'], container=runtime['Id'],
    memory_cap=runtime['HostConfig']['Memory'], base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    source_hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in (
        'mta/presentation/dbm_read.py','mta/presentation/views.py','tools/dbm_gateway_probe.py')})
if call.returncode == 0:
    receipt['proof'] = json.loads(call.stdout)
(target/'receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(dict(exit_code=call.returncode,receipt=str(target/'receipt.json'),stderr=call.stderr[-1400:])))
raise SystemExit(call.returncode)
