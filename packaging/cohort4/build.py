"""Build one pinned CLI package and verify its retained application source."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def output(*args):
    return subprocess.check_output(args, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not args.tag.startswith('freshvcf-cohort4:') or '@' in args.tag:
        raise ValueError('Use an explicit freshvcf-cohort4:* local tag')
    destination = args.output.resolve()
    if destination.is_relative_to(ROOT) or destination.exists():
        raise ValueError('Choose a new external package directory')
    lock = json.loads((HERE / 'runtime-lock.json').read_text(encoding='utf-8'))
    base = json.loads(output('docker', 'image', 'inspect', lock['base_tag']))[0]
    if base['Id'] != lock['base_image_id'] or base['Architecture'] != 'amd64':
        raise ValueError('Pinned base image differs')
    donor = json.loads(output('docker', 'image', 'inspect', lock['tool_dependency_tag']))[0]
    if donor['Id'] != lock['tool_dependency_image_id']:
        raise ValueError('Pinned operational library donor differs')
    subprocess.run(['git', 'diff', '--exit-code', lock['application_commit'], '--',
                    *lock['application_roots']], cwd=ROOT, check=True)
    destination.mkdir(parents=True)
    manifest = []
    for line in output('git', 'ls-tree', '-r', '--name-only', lock['application_commit'],
                       '--', *lock['application_roots']).decode().splitlines():
        raw = output('git', 'show', lock['application_commit'] + ':' + line)
        normalized = Path(line).suffix in ('.py', '.json', '.md', '.txt', '.sql', '.ps1')
        if line in ('baseline/cohort3-consumption-v1.json', 'baseline/cohort3-hierarchy-v1.json'):
            normalized = False  # approved exact byte pins
        if normalized:
            raw = raw.replace(b'\r\n', b'\n')
        target = line.replace('user-service/api_gateway/', 'api_gateway/', 1)
        manifest.append(dict(path='/app/' + target, normalize_newlines=normalized,
                             sha256=hashlib.sha256(raw).hexdigest()))
    (destination / 'source-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    subprocess.run(['docker', 'build', '--pull=false', '--no-cache', '-t', args.tag,
                    str(HERE)], check=True)
    image_id = json.loads(output('docker', 'image', 'inspect', args.tag))[0]['Id']
    code = """import hashlib,json,importlib.metadata as m,subprocess
from pathlib import Path
rows=json.loads(Path('/source.json').read_text())
for row in rows:
 raw=Path(row['path']).read_bytes()
 if row['normalize_newlines']: raw=raw.replace(b'\\r\\n',b'\\n')
 assert hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
import django,rest_framework,rest_framework_simplejwt,psycopg,psycopg2,Crypto,requests
names=['Django','djangorestframework','djangorestframework-simplejwt','psycopg','psycopg2-binary','pycryptodome','requests']
print(json.dumps(dict(source_files=len(rows),dependencies={n:m.version(n) for n in names},pg_dump=subprocess.check_output(['pg_dump','--version'],text=True).strip(),pg_restore=subprocess.check_output(['pg_restore','--version'],text=True).strip())))
"""
    audit = json.loads(output('docker', 'run', '--rm', '--network', 'none', '--memory', '4g',
        '--cpus', '2', '--restart', 'no', '--entrypoint', 'python', '--mount',
        'type=bind,source=' + (destination / 'source-manifest.json').as_posix() + ',target=/source.json,readonly',
        image_id, '-c', code))
    receipt = dict(status='PINNED_PACKAGE_SOURCE_IMPORT_PASS', image=image_id,
        tag=args.tag, base_image=base['Id'], application_commit=lock['application_commit'],
        source_manifest_sha256=hashlib.sha256((destination / 'source-manifest.json').read_bytes()).hexdigest(),
        package_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()},
        **audit)
    (destination / 'package.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
