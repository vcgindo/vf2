"""Run the read-only reader proof with exact source and image bindings."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
target = Path(sys.argv[1])
target.mkdir(parents=True, exist_ok=False)
runtime = json.loads(subprocess.check_output(['docker', 'inspect', 'freshvcf-preview-mta-1'], text=True))[0]
args = ['docker', 'run', '--rm', '--name', 'freshvcf-dbm-selective-proof', '--network', 'freshvcf-test_default',
        '--memory', '4g', '--memory-swap', '4g', '--cpus', '2',
        '-v', str(root).replace('\\', '/') + ':/app:ro',
        '-v', 'D:/freshvcf-build/evidence:/evidence:ro', '-e', 'PYTHONPATH=/app']
for value in runtime['Config']['Env']:
    if value.startswith(('VF_', 'MTA_')):
        args += ['-e', 'VF_EVIDENCE_ROOT=/evidence/runtime' if value.startswith('VF_EVIDENCE_ROOT=') else value]
for mount in runtime['Mounts']:
    if mount['Destination'] != '/app':
        args += ['-v', mount['Source'] + ':' + mount['Destination'] + ':ro']
result = subprocess.run(args + [runtime['Image'], 'python', 'tools/dbm_selective_probe.py'], capture_output=True, text=True)
(target / 'stdout.json').write_text(result.stdout)
(target / 'stderr.log').write_text(result.stderr)
files = ('mta/presentation/dbm_read.py', 'mta/presentation/views.py', 'mta/presentation/dbm.py',
         'mta/presentation/dbm_filters.py', 'mta/presentation/daily_history.py', 'mta/presentation/selective.py',
         'tools/dbm_selective_probe.py')
receipt = dict(exit_code=result.returncode, base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    worker_image=runtime['Image'], source_hashes={name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files})
if result.returncode == 0:
    receipt['proof'] = json.loads(result.stdout)
(target / 'receipt.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(dict(exit_code=result.returncode, receipt=str(target/'receipt.json'), stderr=result.stderr[-1600:])))
raise SystemExit(result.returncode)
