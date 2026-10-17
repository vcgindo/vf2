"""Read-only deployment preflight for the exported Linux-container assembly."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import socket
import subprocess
from urllib.parse import urlsplit


def command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        # Rendered config and subprocess errors may include private operator
        # values. Do not print either. The operator can inspect locally.
        raise ValueError('Read-only command failed: ' + ' '.join(arguments[:2]))
    return result.stdout


def exported_source(root):
    value = json.loads((root / 'release-source.json').read_text(encoding='utf-8'))
    if (value.get('schema') != 'vectorflow-release-source-v1'
            or value.get('default_data_import') is not False
            or not re.fullmatch('[0-9a-f]{40}', value.get('source_commit', ''))):
        raise ValueError('Release source identity is invalid')
    for name, checksum in value['files'].items():
        path = root / name
        if (not path.resolve().is_relative_to(root) or path.is_symlink()
                or hashlib.sha256(path.read_bytes()).hexdigest() != checksum):
            raise ValueError('Exported source file differs: ' + name)
    return value['source_commit']


def inspect(root, env_file, compose_files, image_manifest=None):
    commit = exported_source(root)
    info = json.loads(command(['docker', 'info', '--format', '{{json .}}']))
    if info['OSType'] != 'linux' or info['Architecture'] not in ('x86_64', 'amd64'):
        raise ValueError('This package requires Linux/amd64 Docker containers')
    base = ['docker', 'compose', '--env-file', str(env_file)]
    for path in [root / 'release/compose.yaml', *compose_files]:
        base += ['-f', str(path)]
    rendered = json.loads(command(base + ['--profile', 'install', 'config', '--format', 'json']))
    services = rendered['services']
    if {name for name, value in services.items() if value.get('ports')} != {'frontend'}:
        raise ValueError('Only the application gateway may publish a port')
    front = services['frontend']
    ports = front['ports']
    if len(ports) != 1:
        raise ValueError('Exactly one explicit application gateway port is required')
    binding = ports[0]
    origin = urlsplit(front['environment']['VF_PUBLIC_URL'])
    tls = front['environment']['VF_TLS_MODE']
    if (origin.username or origin.password or origin.query or origin.fragment
            or origin.path not in ('', '/') or not origin.hostname):
        raise ValueError('Public origin must not contain a path or credentials')
    if tls == 'http':
        if origin.scheme != 'http' or origin.hostname not in ('localhost', '127.0.0.1', '::1') \
                or binding.get('host_ip') not in ('127.0.0.1', '::1'):
            raise ValueError('Plain HTTP must be bound to loopback with a matching loopback origin')
    elif tls != 'https' or origin.scheme != 'https':
        raise ValueError('TLS mode and public origin disagree')
    if (origin.port or (443 if tls == 'https' else 80)) != int(binding['published']):
        raise ValueError('Public origin and published gateway port disagree')
    websocket = urlsplit(front['build']['args']['REACT_APP_WS_API_HOST'])
    if (websocket.scheme != ('wss' if tls == 'https' else 'ws')
            or websocket.netloc != origin.netloc):
        raise ValueError('WebSocket and public origins disagree')
    if services['mta']['environment']['VF_DB_NAME'] == services['mto']['environment']['DB_NAME']:
        raise ValueError('MTA and MTO require separate databases')
    for name, value in rendered.get('secrets', {}).items():
        if not value.get('file') or not Path(value['file']).is_file():
            raise ValueError('Required private file is missing: ' + name)
    for name, value in services.items():
        if value.get('restart') != 'no':
            raise ValueError('Unexpected restart policy: ' + name)
    # No automatic network creation, cleanup, subnet substitution or Docker restart.
    selected = rendered.get('networks', {}).get('application', {})
    subnets = [ipaddress.ip_network(row['subnet']) for row in selected.get('ipam', {}).get('config', []) if row.get('subnet')]
    if subnets:
        networks = command(['docker', 'network', 'ls', '-q']).split()
        existing = json.loads(command(['docker', 'network', 'inspect', *networks])) if networks else []
        for network in existing:
            for row in network.get('IPAM', {}).get('Config', []):
                if row.get('Subnet'):
                    other = ipaddress.ip_network(row['Subnet'])
                    if any(subnet.version == other.version and subnet.overlaps(other) for subnet in subnets):
                        raise ValueError('Selected subnet overlaps an existing Docker network; preserve it and choose an approved nonoverlapping subnet')
    host, port = binding.get('host_ip', '0.0.0.0'), int(binding['published'])
    with socket.socket(socket.AF_INET6 if ':' in host else socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError as error:
            raise ValueError('Gateway port is occupied or unavailable; identify its owner before any serving change') from error
    image_ids = []
    if image_manifest:
        record = json.loads(image_manifest.read_text(encoding='utf-8'))
        if record['source_commit'] != commit:
            raise ValueError('Image manifest and exported source commit differ')
        allowed = {item['image_id'] for item in record['images']}
        for image in sorted({value['image'] for value in services.values()}):
            actual = json.loads(command(['docker', 'image', 'inspect', image]))[0]
            if actual['Id'] not in allowed or actual['Os'] != 'linux' or actual['Architecture'] != 'amd64':
                raise ValueError('Loaded image identity/platform differs from the approved delivery')
            image_ids.append(actual['Id'])
    return dict(status='PREFLIGHT_PASS_NO_RESOURCE_CHANGE', source_commit=commit,
                project=rendered['name'], gateway_port=port, docker_platform='linux/amd64',
                image_identity_verified=bool(image_manifest), image_ids=sorted(set(image_ids)),
                qualification='Configuration-only; no installation, readiness, authentication, capacity or business acceptance claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--compose-file', type=Path, action='append', default=[])
    parser.add_argument('--images-manifest', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.root.resolve(), args.env_file.resolve(),
                             [path.resolve() for path in args.compose_file], args.images_manifest), sort_keys=True))


if __name__ == '__main__':
    main()
