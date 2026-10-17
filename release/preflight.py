"""Read-only portable deployment checks. Never install, pull, build or clean up.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import socket
import subprocess
from urllib.parse import urlsplit


def environment(path):
    values = {}
    for number, raw in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('Invalid operator configuration line '+str(number))
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if not key or key in values:
            raise ValueError('Missing or duplicate operator configuration key')
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        values[key] = value
    return values


def configuration(values):
    for key in ('VF_RELEASE', 'VF_PROJECT', 'VF_PUBLIC_URL', 'VF_PUBLIC_WS_URL',
                'VF_CLIENT_CIPHER_KEY', 'VF_SECRETS_DIR'):
        if not values.get(key) or 'REPLACE_' in values[key]:
            raise ValueError(key+' must be explicitly configured before Compose')
    if values.get('MTA_DB_NAME', 'vectorflow_mta') == values.get('MTO_DB_NAME', 'vectorflow_mto'):
        raise ValueError('MTA and MTO database names must differ')
    http, ws = urlsplit(values['VF_PUBLIC_URL']), urlsplit(values['VF_PUBLIC_WS_URL'])
    if (http.scheme not in ('http', 'https') or http.hostname is None
            or http.username or http.password or http.path not in ('', '/') or http.query or http.fragment):
        raise ValueError('Explicit public HTTP(S) origin required')
    expected_ws = 'wss' if http.scheme == 'https' else 'ws'
    if (ws.scheme != expected_ws or ws.netloc != http.netloc or ws.path not in ('', '/')
            or ws.query or ws.fragment):
        raise ValueError('Public HTTP and WebSocket origins must match')
    if http.scheme == 'http' and http.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Plain HTTP requires loopback; external service requires TLS')
    hosts = values.get('VF_ALLOWED_HOSTS', http.hostname).split(',')
    if '*' in hosts:
        raise ValueError('Explicit allowed hosts required')
    port = int(values.get('VF_HTTP_PORT', http.port or (443 if http.scheme == 'https' else 80)))
    if port != (http.port or (443 if http.scheme == 'https' else 80)):
        raise ValueError('Published port and public origin differ')
    secret_root = Path(values['VF_SECRETS_DIR'])
    if not secret_root.is_absolute():
        raise ValueError('VF_SECRETS_DIR must be absolute for portable operator configuration')
    return values.get('VF_BIND_ADDRESS', '127.0.0.1'), port


def source_manifest(root, *, commit=None, source_sha256=None, native_sha256=None):
    from release.mta_packaging import source
    value, _native = source(root, commit=commit, source_sha256=source_sha256,
        native_sha256=native_sha256)
    return value


def non_overlapping_subnet(subnet, networks):
    proposed = ipaddress.ip_network(subnet, strict=True)
    if not proposed.is_private or proposed.prefixlen < 24:
        raise ValueError('Choose a bounded private subnet after reviewing host routes')
    for existing in networks:
        current = ipaddress.ip_network(existing, strict=False)
        if proposed.version == current.version and proposed.overlaps(current):
            raise ValueError('Proposed subnet overlaps an existing Docker network')
    return str(proposed)


def command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True)
    if result.returncode:
        # Compose stderr can include interpolated values; never echo it.
        raise ValueError('Read-only command failed: '+arguments[0]+' '+arguments[1])
    return result.stdout


def inspect(root, env_file, compose_files, *, existing_project=False, subnet=None):
    root, env_file = Path(root).resolve(), Path(env_file).resolve()
    values = environment(env_file)
    bind, port = configuration(values)
    manifest = source_manifest(root, commit=values.get('VF_NATIVE_RELEASE_COMMIT'),
        source_sha256=values.get('VF_SOURCE_MANIFEST_SHA256'),
        native_sha256=values.get('VF_NATIVE_RELEASE_SHA256'))
    if (root/'public-build.json').is_file():
        public = json.loads((root/'public-build.json').read_text(encoding='utf-8'))
        if (public.get('client_cipher_key') != values['VF_CLIENT_CIPHER_KEY']
                or public.get('websocket_origin') != values['VF_PUBLIC_WS_URL']):
            raise ValueError('Operator configuration differs from frozen frontend public build')
    platform = command(['docker', 'info', '--format', '{{.OSType}}/{{.Architecture}}']).strip()
    if platform not in ('linux/amd64', 'linux/x86_64'):
        raise ValueError('Docker Linux/amd64 mode required')
    command(['docker', 'compose', 'version'])
    args = ['docker', 'compose', '--project-name', values['VF_PROJECT'], '--env-file', str(env_file)]
    for name in compose_files or [root/'release/compose.yaml']:
        args += ['-f', str(Path(name).resolve())]
    rendered = json.loads(command(args+['config', '--format', 'json']))
    missing = []
    for name, secret in rendered.get('secrets', {}).items():
        if 'file' in secret and not Path(secret['file']).is_file():
            missing.append(name)
    if missing:
        raise ValueError('Required secret files missing: '+','.join(sorted(missing)))
    images = {}
    for name, service in rendered['services'].items():
        if service.get('image'):
            images[name] = command(['docker', 'image', 'inspect', service['image'],
                '--format', '{{.Id}}']).strip()
    if (root/'runtime-images.json').is_file():
        pinned = json.loads((root/'runtime-images.json').read_text(encoding='utf-8'))['services']
        if any(name in pinned and value != pinned[name]['image_id'] for name, value in images.items()):
            raise ValueError('Selected runtime image differs from delivered pinned image manifest')
    ids = command(['docker', 'ps', '-aq', '--filter',
        'label=com.docker.compose.project='+values['VF_PROJECT']]).split()
    containers = json.loads(command(['docker', 'inspect', *ids])) if ids else []
    owns_port = any(any(str(p.get('HostPort')) == str(port) and p.get('HostIp') == bind
        for mappings in row.get('NetworkSettings', {}).get('Ports', {}).values()
        for p in (mappings or [])) for row in containers)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((bind, port))
            port_status = 'available'
        except OSError:
            if not (existing_project and owns_port):
                raise ValueError('Gateway port is occupied; this is not Docker address-pool exhaustion')
            port_status = 'occupied by explicitly allowed existing project'
    checked_subnet = None
    if subnet:
        network_ids = command(['docker', 'network', 'ls', '-q']).split()
        networks = json.loads(command(['docker', 'network', 'inspect', *network_ids])) if network_ids else []
        checked_subnet = non_overlapping_subnet(subnet, [c['Subnet'] for n in networks
            for c in (n.get('IPAM', {}).get('Config') or []) if c.get('Subnet')])
    return dict(status='READ_ONLY_DEPLOYMENT_PREFLIGHT_PASS', source_commit=manifest['source_commit'],
        source_files=len(manifest['files']), platform=platform, images=images,
        gateway_port_status=port_status, checked_new_subnet=checked_subnet,
        qualification='No resource creation/pull/build/start/install. A new subnet also requires host-route review; '
            'a passed read-only preflight does not authorize deployment, initialization or data execution. '
            'Enforce private operator ACLs; this check does not certify Windows ACLs or licence entitlement.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--compose-file', type=Path, action='append')
    parser.add_argument('--allow-existing-project', action='store_true')
    parser.add_argument('--network-subnet')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.source_root, args.env_file, args.compose_file,
            existing_project=args.allow_existing_project, subnet=args.network_subnet), sort_keys=True))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, 'Preflight refused: '+str(exc)+'\n')
