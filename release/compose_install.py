"""Finish one fresh blank installation with system metadata and an operator-owned admin.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import getpass
import json
import os
from pathlib import Path


def install():
    from release.install_identity import install as install_catalogue
    expected = json.loads(Path('/opt/vectorflow/release.json').read_text())
    database = json.loads(Path('/receipts/database.json').read_text())
    if database['status'] != 'BLANK_DATABASES_SCHEMA_GRANTS_VERIFIED' or database['source_commit'] != expected['source_commit']:
        raise ValueError('Missing matching blank database installation')
    # Identity installer refuses existing metadata/users; do this BEFORE creating an account.
    email = os.environ.get('VF_ADMIN_EMAIL') or input('New administrator email: ').strip()
    name = os.environ.get('VF_ADMIN_NAME') or input('New administrator name: ').strip()
    password = os.environ.get('VF_ADMIN_PASSWORD') or getpass.getpass('New administrator password: ')
    if not os.environ.get('VF_ADMIN_PASSWORD') and password != getpass.getpass('Confirm password: '):
        raise ValueError('Passwords differ')
    if not email or not name or not password:
        raise ValueError('Explicit new administrator identity and password required')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.auth_settings')
    import django
    django.setup()
    from django.contrib.auth.password_validation import validate_password
    from django.core.validators import validate_email
    from django.db import connection
    from api.models import User
    validate_email(email)
    validate_password(password, User(email=email, name=name))
    install_catalogue()
    user = User.all_objects.create_superuser(email=email, name=name, tc=True, password=password)
    assert user.is_admin and user.is_active and user.check_password(password)
    from common.data_scopes import ADMIN_DATA_ACCESS_POLICY
    result = dict(status='BLANK_INSTALLATION_COMPLETE', source_commit=expected['source_commit'],
                  administrator_email=user.email, administrator_data_access=ADMIN_DATA_ACCESS_POLICY,
                  sample_loaded=False, daily_runs=0, business_registration=False)
    with Path('/receipts/install.json').open('x') as stream:
        json.dump(result, stream, sort_keys=True)
    connection.close()
    return result


if __name__ == '__main__':
    print(json.dumps(install(), sort_keys=True))
