"""Generate new secrets once and route only the declared subset to each service.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import json
import os
from pathlib import Path

from release.prepare_secrets import prepare


ROUTES = {
    'postgres': ('postgres_admin_password',),
    'mta-runtime': ('mta_secret', 'mta_runtime_password'),
    'mta-installer': ('mta_secret', 'mta_installer_password'),
    'auth-runtime': ('auth_secret', 'auth_runtime_password_enc', 'auth_private_key', 'auth_public_key'),
    'auth-installer': ('auth_secret', 'auth_installer_password_enc', 'auth_private_key', 'auth_public_key'),
    'mto-runtime': ('mto_secret', 'mto_runtime_password'),
    'mto-installer': ('mto_secret', 'mto_installer_password'),
    'provision': ('postgres_admin_password', 'mta_secret', 'mta_installer_password', 'mta_runtime_password',
                  'mto_installer_password', 'mto_runtime_password', 'auth_installer_password', 'auth_runtime_password'),
}


def ensure(root=Path('/secrets')):
    root = Path(root)
    private, marker = root / 'private/source', root / 'private/ready.json'
    if marker.exists():
        pins = json.loads(marker.read_text())
        if (set(pins) != set().union(*ROUTES.values())
                or set(pins) != {str(p.relative_to(private)) for p in private.iterdir() if p.is_file()}):
            raise ValueError('Existing private secret roster differs; no regeneration')
        for name, pin in pins.items():
            if hashlib.sha256((private / name).read_bytes()).hexdigest() != pin:
                raise ValueError('Existing secret differs; no replacement')
        for service, names in ROUTES.items():
            target = root / service
            if {p.name for p in target.iterdir()} != set(names):
                raise ValueError('Existing service secret roster differs')
            if any((target / name).read_bytes() != (private / name).read_bytes() for name in names):
                raise ValueError('Existing routed secret differs; no replacement')
        return {'status': 'EXISTING_SECRETS_VERIFIED_UNCHANGED'}
    if private.exists() or any(any((root / service).iterdir()) for service in ROUTES):
        raise ValueError('Partial/existing secret state; stop and reconcile, never rotate')
    prepare(private)
    for service, names in ROUTES.items():
        for name in names:
            target = root / service / name
            with target.open('xb') as stream:
                stream.write((private / name).read_bytes())
            target.chmod(0o444)
    pins = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in private.iterdir()}
    marker.write_text(json.dumps(pins, sort_keys=True) + '\n')
    marker.chmod(0o400)
    return {'status': 'NEW_PRIVATE_SECRETS_ROUTED', 'services': sorted(ROUTES)}


if __name__ == '__main__':
    os.chown('/receipts', 10001, 10001)
    Path('/receipts').chmod(0o700)
    print(json.dumps(ensure(), sort_keys=True))
