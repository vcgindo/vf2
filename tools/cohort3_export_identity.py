"""Read the current owned 3006 two-actor contract into an explicit private file."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

try:
    from tools.daily_stack_auth import EXPORT as RETAINED_EXPORT
except ModuleNotFoundError:  # Direct ``python tools/cohort3_export_identity.py``.
    from daily_stack_auth import EXPORT as RETAINED_EXPORT


SOURCE = 'freshvcf-daily3006-user-service-1'
GUARD = r'''
from django.db import connection
with connection.cursor() as cursor:
 cursor.execute('SELECT current_database(),current_schema()')
 assert cursor.fetchone()==('daily_3006','identity')
 cursor.execute('SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY')
 cursor.execute('SHOW default_transaction_read_only')
 assert cursor.fetchone()==('on',)
'''


def export_script():
    marker = "import django;django.setup()\n"
    if RETAINED_EXPORT.count(marker) != 1:
        raise ValueError('Retained identity export setup boundary changed')
    return RETAINED_EXPORT.replace(marker, marker + GUARD, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-container', default=SOURCE)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    repository = Path(__file__).resolve().parents[1]
    if output.is_relative_to(repository):
        raise ValueError('Identity export must remain outside the Git checkout')
    if output.exists():
        raise ValueError('Refusing to replace an existing private identity export')
    result = subprocess.run(
        ['docker', 'exec', '-i', args.source_container, 'python', '-'],
        input=export_script(), text=True, encoding='utf-8', capture_output=True)
    if result.returncode:
        raise RuntimeError('Read-only current3006 identity export failed: ' + result.stderr[-1000:])
    raw = result.stdout.encode('utf-8')
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError('Retained identity export is not a serialized object list')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'status': 'CURRENT_3006_IDENTITY_EXPORTED_PRIVATE',
                      'sha256': hashlib.sha256(raw).hexdigest(),
                      'bytes': len(raw), 'output': str(output)}))


if __name__ == '__main__':
    main()
