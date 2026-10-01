"""Finite, MTA-only3005 DBM browser window with unconditional normal restoration.

No business algorithm/route/admission edit. A disposable WSGI import wrapper fixes
only actions.timestamp to the registered scenario's civil instant. It is removed
after normal compose configuration is restored. Evidence survives cleanup.
"""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NORMAL_RUN = 'ac1612c8-0e49-4155-83c3-f59f41422293'
NORMAL_DIGEST = 'bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d'
TRIAL = '20261d94-b78a-4141-8770-2fe2d5b3354b'
TRIAL_DIGEST = '12722fa8f8dc1d8d1c3d4f379e9702e5af3827fd16bee35052dab598dda24a88'


def run(args):
    return subprocess.check_output(args, text=True, encoding='utf-8', stderr=subprocess.STDOUT)


def inspect():
    return json.loads(run(['docker', 'inspect', 'freshvcf-preview-mta-1']))[0]


def identity(obj):
    return dict(id=obj['Id'], image=obj['Image'], started=obj['State']['StartedAt'],
                config_sha256=hashlib.sha256(json.dumps(obj['Config'], sort_keys=True).encode()).hexdigest(),
                mounts=obj['Mounts'], memory=obj['HostConfig']['Memory'],
                memory_swap=obj['HostConfig']['MemorySwap'], nano_cpus=obj['HostConfig']['NanoCpus'],
                restart=obj['HostConfig']['RestartPolicy'], ports=obj['HostConfig']['PortBindings'])


def operative_config(obj):
    """Docker assigns a new hostname and may reorder environment on recreation."""
    config = deepcopy(obj['Config'])
    assert config['Hostname'] == obj['Id'][:12]
    config.pop('Hostname')
    config['Env'] = sorted(config['Env'])
    return config


def ready():
    for _ in range(60):
        try:
            return json.loads(run(['docker', 'exec', 'freshvcf-preview-mta-1', 'python', '-c',
                "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/readyz',timeout=5).read().decode())"]))
        except subprocess.CalledProcessError:
            time.sleep(1)
    raise RuntimeError('MTA did not become ready within bounded startup window')


def main():
    target = Path(sys.argv[1]).resolve()
    assert target.parent == Path('D:/freshvcf-build/evidence').resolve() and not target.exists()
    target.mkdir()
    temporary = Path('D:/freshvcf-build/preview') / target.name
    temporary.mkdir(exist_ok=False)
    before = inspect()
    env = dict(v.split('=', 1) for v in before['Config']['Env'])
    assert env['VF_MTA_PUBLISHED_RUN'] == NORMAL_RUN and env['VF_MTA_PUBLISHED_DIGEST'] == NORMAL_DIGEST
    assert env.get('VF_MTA_ACTIONS_ENABLED', '0') == '0'
    assert before['HostConfig']['Memory'] == 4 * 1024**3 and before['HostConfig']['NanoCpus'] == 2 * 10**9
    source = Path('D:/freshvcf-build/evidence/f3-stage2-dbm-prepare-001')
    proof = json.loads((source / 'scope-admission-readback.json').read_text())
    assert proof['status'] == 'PASS_EXACT_TRIAL_SCOPE_AND_STARTUP_ADMISSION'
    planned = json.loads((source / 'readback.json').read_text())['planned_commands']
    commands = json.loads(run(['docker', 'exec', 'freshvcf-preview-mta-1', 'python', '-c',
        "import os,json;os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings');"
        "import django;django.setup();from mta.runtime.models import CalculationRun;"
        f"r=CalculationRun.objects.get(pk='{TRIAL}');"
        f"assert r.output_digest=='{TRIAL_DIGEST}';"
        "print(json.dumps(list(r.commands.order_by('id').values_list('payload',flat=True))))"]))
    assert len(commands) < len(planned), 'Trial already consumed; never reset/replay it'
    for actual, expected in zip(commands, planned):
        assert actual == {k: expected[k] for k in ('operation', 'selected', 'timestamp')} | {'actor': '1'}
    hp = source / 'hierarchy-trial.json'
    assert hashlib.sha256(hp.read_bytes()).hexdigest() == proof['hierarchy_sha256']
    wrapper = """import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.conf import settings
assert settings.VF_MTA_PUBLISHED_RUN == '20261d94-b78a-4141-8770-2fe2d5b3354b'
assert settings.VF_MTA_PUBLISHED_DIGEST == '12722fa8f8dc1d8d1c3d4f379e9702e5af3827fd16bee35052dab598dda24a88'
from mta.presentation import actions
actions.timestamp = lambda: '2026-06-06T12:00:00+05:30'
from vectorflow.wsgi import application
"""
    wrapper_path = temporary / 'trial_wsgi.py'
    wrapper_path.write_text(wrapper)
    (target / 'trial_wsgi.py.evidence').write_text(wrapper)
    overlay = {'services': {'mta': {'environment': {
        'VF_MTA_PUBLISHED_RUN': TRIAL, 'VF_MTA_PUBLISHED_DIGEST': TRIAL_DIGEST,
        'VF_MTA_HIERARCHY_FILE': '/trial/hierarchy.json', 'VF_MTA_HIERARCHY_SHA256': proof['hierarchy_sha256'],
        'VF_MTA_TERMINAL_FILE': '', 'VF_MTA_TERMINAL_SHA256': '', 'VF_MTA_ACTIONS_ENABLED': '1',
        'PYTHONPATH': '/trial:/app'}, 'volumes': [
            hp.as_posix()+':/trial/hierarchy.json:ro', wrapper_path.as_posix()+':/trial/trial_wsgi.py:ro',
            f'D:/freshvcf-build/evidence/runtime/{TRIAL}/InputSnapshot.jsonl.gz:/input-identity/{TRIAL}/InputSnapshot.jsonl.gz:ro'],
        'command': ['gunicorn', 'trial_wsgi:application', '--preload', '--bind', '0.0.0.0:8000',
                    '--workers', '2', '--timeout', '180']}}}
    overlay_path = temporary / 'compose.json'
    overlay_path.write_text(json.dumps(overlay, indent=2))
    (target / 'compose-overlay.json.evidence').write_text(json.dumps(overlay, indent=2))
    normal = ['docker', 'compose', '--env-file', 'D:/freshvcf-build/preview/preview.env',
              '-f', str(ROOT / 'compose.preview.yaml')]
    up = ['up', '-d', '--no-deps', '--no-build', '--force-recreate', 'mta']
    result = dict(status='STARTING', normal_before=identity(before), trial_run=TRIAL,
                  trial_digest=TRIAL_DIGEST, clock='2026-06-06T12:00:00+05:30',
                  maximum_window_seconds=1200, actor='fresh.preview@vectorflow.local', scopes=[71001, 72001],
                  commands_before=commands, remaining_commands=planned[len(commands):],
                  restoration_command=normal+up)
    (target / 'window.json').write_text(json.dumps(result, indent=2))
    switched = False
    try:
        switched = True
        (target / 'trial-start.log').write_text(run(normal+['-f', str(overlay_path)]+up))
        result.update(status='TRIAL_READY', trial_ready=ready(), trial_identity=identity(inspect()))
        (target / 'window.json').write_text(json.dumps(result, indent=2))
        print(json.dumps({'status': 'TRIAL_READY', 'run': TRIAL, 'window': str(target)}), flush=True)
        deadline = time.monotonic()+1200
        while time.monotonic() < deadline and not (target / 'restore-now').exists():
            time.sleep(1)
    finally:
        try:
            if switched:
                (target / 'normal-restore.log').write_text(run(normal+up))
                result['normal_ready'] = ready()
                restored = inspect()
                result['normal_after'] = identity(restored)
                result['normal_config_equal'] = operative_config(restored) == operative_config(before)
                result['normal_mounts_equal'] = (sorted(restored['Mounts'], key=lambda m: m['Destination'])
                    == sorted(before['Mounts'], key=lambda m: m['Destination']))
                assert result['normal_config_equal'], 'Normal MTA operative configuration differs'
                assert result['normal_mounts_equal'], 'Temporary mount survived restoration'
                result.update(status='NORMAL_RESTORED', normal_after=identity(restored))
            for path in (wrapper_path, overlay_path):
                assert path.resolve().parent == temporary.resolve()
                path.unlink()
            temporary.rmdir()
            result['temporary_serving_files_removed'] = True
        except Exception as exc:
            result.update(status='RESTORATION_PROOF_FAILED', restoration_error=repr(exc))
            raise
        finally:
            (target / 'window.json').write_text(json.dumps(result, indent=2))
        print(json.dumps({'status': result['status'], 'temporary_serving_files_removed': True}), flush=True)


if __name__ == '__main__':
    main()
