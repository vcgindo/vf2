"""Private real-gateway action proof on the retained two-day trial.

No host ports, serving rebind, account reset, calculation change or SQL replay.
The short-lived login cookie is saved outside Git/evidence; receipts are redacted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


GATEWAY = 'freshvcf-f3-action-gateway'
WORKER = 'freshvcf-f3-action-mta'
PERMISSION_SHA = '18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356'
LOGIN = '''
import base64, json, os, time
import requests
from Crypto.Cipher import AES
base = 'http://127.0.0.1:10016'
session = requests.Session()
session.headers['Host'] = 'localhost'
for attempt in range(30):
    try:
        ready = session.get(base + '/api/mta/GetEnvironmentConfiguration', timeout=5)
        assert ready.status_code == 401, ready.status_code
        break
    except requests.ConnectionError:
        if attempt == 29: raise
        time.sleep(0.5)
iv = os.urandom(16)
cipher = AES.new(os.environ['SECRET_KEY_FOR_PASSWORD'].encode(), AES.MODE_CTR,
                 nonce=b'', initial_value=int.from_bytes(iv, 'big'))
encrypted = base64.b64encode(iv + cipher.encrypt(os.environ['VECTORFLOW_TEST_PASSWORD'].encode())).decode()
response = session.post(base + '/api/user/login/', json={
    'email': os.environ['VECTORFLOW_TEST_USERNAME'], 'password': encrypted}, timeout=60)
assert response.status_code == 200, response.status_code
user = response.json()['data']['user']
assert user['email'] == 'fresh.preview@vectorflow.local'
token = session.cookies.get('access_token')
assert token
print(json.dumps(dict(username=user['email'],user_id=user['id'],access_token=token)))
'''


def inspect(name):
    result = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True)
    if result.returncode:
        return None
    item = json.loads(result.stdout)[0]
    return dict(name=name, id=item['Id'], image=item['Image'],
        config_sha256=hashlib.sha256(json.dumps(item['Config'], sort_keys=True).encode()).hexdigest(),
        memory=item['HostConfig']['Memory'], memory_swap=item['HostConfig']['MemorySwap'],
        nano_cpus=item['HostConfig']['NanoCpus'],
        port_bindings=item['HostConfig']['PortBindings'],
        networks=sorted(item['NetworkSettings']['Networks']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    target = args.evidence.resolve()
    evidence_root = Path('D:/freshvcf-build/evidence').resolve()
    if target.parent != evidence_root or target.exists():
        raise SystemExit('Use a new direct child of the approved evidence root')
    if inspect(GATEWAY) or inspect(WORKER):
        raise SystemExit('Private worker already exists; inspect it, do not restart a live attempt')
    target.mkdir()
    secret_dir = Path('D:/freshvcf-build/preview') / target.name
    secret_dir.mkdir(exist_ok=False)
    session_file = secret_dir / 'gateway-session.json'
    receipt = dict(status='FAILED', boundary='F3.2 real cookie gateway retained action trial',
        containers=[], serving_changes=False, host_ports_allocated=0,
        driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    gateway_started = False
    try:
        start = subprocess.run(['docker', 'compose', '--env-file',
            'D:/freshvcf-build/preview/preview.env', '-f', 'compose.preview.yaml',
            'run', '--rm', '-d', '--no-deps', '--name', GATEWAY,
            '-e', 'MTA_BACKEND_URL=http://' + WORKER + ':8000', 'user-service'],
            capture_output=True, text=True)
        (target / 'gateway-start.log').write_text(start.stderr, encoding='utf-8')
        start.check_returncode()
        gateway_started = True
        receipt['containers'].append(inspect(GATEWAY))
        login = subprocess.run(['docker', 'exec', '-i', GATEWAY, 'python', '-'],
            input=LOGIN, capture_output=True, text=True)
        (target / 'login-stderr.log').write_text(login.stderr, encoding='utf-8')
        login.check_returncode()
        identity = json.loads(login.stdout)
        session_file.write_text(json.dumps(identity), encoding='utf-8')
        receipt['login'] = dict(username=identity['username'], user_id=identity['user_id'],
                               authentication='unchanged encrypted-password login and cookie JWT')
        command = ['docker', 'compose', '-f', 'compose.test.yaml', 'run', '--rm', '-T',
            '--no-deps', '--name', WORKER,
            '-v', 'F:/freshvcf/vectorflow:/app/vectorflow:ro',
            '-v', secret_dir.as_posix() + ':/trial:ro',
            '-e', 'VF_ALLOWED_HOSTS=' + WORKER + ',localhost,127.0.0.1,testserver',
            '-e', 'VF_MTA_PERMISSIONS_FILE=/inputs/permission-input-v1.json',
            '-e', 'VF_MTA_PERMISSIONS_SHA256=' + PERMISSION_SHA,
            'mta', 'python', 'manage.py', 'prove_action_http',
            '--input', '/inputs/representative-bridge-input.json',
            '--retained-replay', '/evidence/f2-auto-sql-012/replay.json',
            '--evidence', '/evidence/' + target.name + '/proof',
            '--revision', args.revision, '--gateway-url', 'http://' + GATEWAY + ':10016',
            '--gateway-session', '/trial/gateway-session.json']
        with (target / 'worker.log').open('w', encoding='utf-8') as log:
            worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True)
            for _ in range(30):
                state = inspect(WORKER)
                if state:
                    receipt['containers'].append(state)
                    break
                if worker.poll() is not None:
                    break
                time.sleep(0.5)
            receipt['worker_exit_code'] = worker.wait()
        if receipt['worker_exit_code']:
            raise RuntimeError('Retained gateway proof failed; inspect preserved worker/proof logs')
        proof_path = target / 'proof/receipt.json'
        proof = json.loads(proof_path.read_text())
        if proof.get('real_gateway_acceptance') != 'PASS' or proof.get('comparisons') != 62:
            raise RuntimeError('Gateway/complete retained comparison exit not met')
        if len(receipt['containers']) != 2 or any(c['port_bindings'] for c in receipt['containers']):
            raise RuntimeError('Private no-host-port isolation not proved')
        receipt.update(status='PASS_REAL_GATEWAY_ACTIONS_AND_OWN_NEXT_DAY',
            proof_sha256=hashlib.sha256(proof_path.read_bytes()).hexdigest(), comparisons=62,
            private_run_ids=[d['run_id'] for d in proof['days']])
    except Exception as exc:
        receipt['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        if gateway_started:
            cleanup = subprocess.run(['docker', 'stop', '--time', '10', GATEWAY],
                                     capture_output=True, text=True)
            receipt['private_gateway_stop_exit_code'] = cleanup.returncode
        # Disposable JWT is not parity evidence. Keep no reusable login token.
        if session_file.exists():
            session_file.unlink()
        (target / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'], comparisons=receipt['comparisons'],
                          receipt=str(target / 'receipt.json'))), flush=True)


if __name__ == '__main__':
    main()
