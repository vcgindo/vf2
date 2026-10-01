"""Bounded worker driver; preserve success/failure, never write serving state."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

target=Path(sys.argv[1]); target.mkdir(parents=True,exist_ok=False)
runtime=json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
args=['docker','run','--rm','--name','freshvcf-rrr-selective-proof','--network','freshvcf-test_default',
      '--memory','4g','--memory-swap','4g','--cpus','2',
      '-v',str(Path.cwd()).replace('\\','/')+':/app:ro',
      '-v','D:/freshvcf-build/evidence:/evidence:ro','-e','PYTHONPATH=/app']
for value in runtime['Config']['Env']:
    if value.startswith(('VF_','MTA_')): args+=['-e',value]
if len(sys.argv)>2 and sys.argv[2]=='plan': args+=['-e','RRR_SELECTIVE_PLAN=1']
if len(sys.argv)>2 and sys.argv[2]=='integrity': args+=['-e','RRR_SELECTIVE_INTEGRITY=1']
for mount in runtime['Mounts']:
    if mount['Destination']!='/app': args+=['-v',mount['Source']+':'+mount['Destination']+':ro']
args+=[runtime['Image'],'python','tools/rrr_selective_probe.py']
result=subprocess.run(args,text=True,capture_output=True)
(target/'stdout.json').write_text(result.stdout,encoding='utf-8')
(target/'stderr.txt').write_text(result.stderr,encoding='utf-8')
(target/'probe-source.py').write_bytes(Path('tools/rrr_selective_probe.py').read_bytes())
receipt=dict(exit_code=result.returncode,image=runtime['Image'],
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    source_hashes={str(p).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path('mta/presentation')/name for name in ('context.py','selective.py','rrr_sql.py','views.py')]},
    probe_sha256=hashlib.sha256(Path('tools/rrr_selective_probe.py').read_bytes()).hexdigest(),
    qualification='Mounted candidate read-only; image identifies dependencies, not committed candidate application. No browser acceptance.')
if result.returncode==0: receipt['proof']=json.loads(result.stdout)
(target/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(dict(exit_code=result.returncode,receipt=str(target/'receipt.json'),stderr=result.stderr[-1700:])))
raise SystemExit(result.returncode)
