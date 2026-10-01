"""Host driver for isolated HTTP proof, redacted runtime identity and restart reuse."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

target = Path(sys.argv[1])
assert not target.exists(), 'Preserve earlier receipts'
target.mkdir(parents=True)
script = Path('tools/preview_http_probe.py').read_text()
args = ['docker','exec','-i']
if len(sys.argv) > 2:
    args += ['-e', f'PREVIEW_PROBE_BASE={sys.argv[2]}']
if len(sys.argv) > 3 and sys.argv[3] == 'restart':
    args += ['-e', 'PREVIEW_PROBE_RESTART=1']
if len(sys.argv) > 3 and sys.argv[3] == 'layout':
    args += ['-e', 'PREVIEW_PROBE_LAYOUT=1']
if len(sys.argv) > 3 and sys.argv[3] == 'hierarchy':
    args += ['-e', 'PREVIEW_PROBE_HIERARCHY=1']
if len(sys.argv) > 3 and sys.argv[3] == 'visible':
    args += ['-e', 'PREVIEW_PROBE_VISIBLE=1']
args += ['freshvcf-preview-user-service-1', 'python', '-']
result = subprocess.run(args, input=script, text=True, capture_output=True)
(target/'stdout.json').write_text(result.stdout, encoding='utf-8')
(target/'stderr.txt').write_text(result.stderr, encoding='utf-8')
if result.returncode:
    raise SystemExit(f'Probe failed; retained at {target}')
proof = json.loads(result.stdout)
containers = []
for service in ('mta','mto','user-service','frontend','redis'):
    raw = subprocess.run(['docker','inspect',f'freshvcf-preview-{service}-1'],text=True,capture_output=True)
    if raw.returncode:
        continue
    item = json.loads(raw.stdout)[0]
    containers.append(dict(service=service,id=item['Id'],image=item['Image'],
        config_sha256=hashlib.sha256(json.dumps(item['Config'],sort_keys=True).encode()).hexdigest(),
        networks=sorted(item['NetworkSettings']['Networks']),mounts=item['Mounts'],
        port_bindings=item['HostConfig']['PortBindings'],memory=item['HostConfig']['Memory']))
proof['containers'] = containers
proof['probe_sha256'] = hashlib.sha256(script.encode()).hexdigest()
proof['compose_sha256'] = hashlib.sha256(Path('compose.preview.yaml').read_bytes()).hexdigest()
(target/'receipt.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps(dict(status=proof['status'], username=proof['username'], routes=len(proof['observations']),receipt=str(target/'receipt.json'))))
