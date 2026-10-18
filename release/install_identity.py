"""Install retained identity metadata; repair only missing canonical roles/links.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import argparse
import json
import os
from pathlib import Path


def catalogue():
    value = json.loads(Path(__file__).with_name('identity_catalogue.json').read_text(encoding='utf-8'))
    if value['schema'] != 'vectorflow-identity-catalogue-v1':
        raise ValueError('Identity catalogue version differs')
    names = [row['name'] for row in value['roles']]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate canonical role')
    applications = {row['application_id'] for row in value['applications']}
    if any(row['application_id'] not in applications for row in value['roles']):
        raise ValueError('Canonical role application differs')
    for key, field, rows in (('role_permissions', 'url', 'permissions'),
                             ('role_features', 'feature', 'features')):
        valid = {row[field] for row in value[rows]}
        if set(value[key]) - set(names) or any(set(links) - valid for links in value[key].values()):
            raise ValueError('Unresolved canonical role link: ' + key)
    return value


def _setup():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','release.auth_settings')
    import django
    django.setup()


def _roles(value):
    from api.models import Roles, Permission, FeatureMaster
    permissions = {row.url: row for row in Permission.objects.all()}
    features = {row.feature: row for row in FeatureMaster.objects.all()}
    created = permission_links = feature_links = 0
    for definition in value['roles']:
        role, new = Roles.objects.get_or_create(name=definition['name'], defaults={
            key: val for key, val in definition.items() if key != 'name'})
        if any(getattr(role, key) != val for key, val in definition.items()):
            raise ValueError('Existing role differs; no overwrite: ' + role.name)
        wanted_permissions = set(value['role_permissions'].get(role.name, []))
        wanted_features = set(value['role_features'].get(role.name, []))
        old_permissions = set(role.permission_id.values_list('url', flat=True))
        old_features = set(role.feature_id.values_list('feature', flat=True))
        if old_permissions - wanted_permissions or old_features - wanted_features:
            raise ValueError('Existing role links differ; no overwrite: ' + role.name)
        role.permission_id.add(*(permissions[url] for url in sorted(wanted_permissions - old_permissions)))
        role.feature_id.add(*(features[name] for name in sorted(wanted_features - old_features)))
        created += int(new)
        permission_links += len(wanted_permissions - old_permissions)
        feature_links += len(wanted_features - old_features)
    return dict(roles_created=created, permission_links_created=permission_links,
                feature_links_created=feature_links)


def install():
    _setup()
    from django.db import transaction, connection
    from api.models import ApplicationMaster, Permission, FeatureMaster, UserserviceConfig, User, Roles
    value = catalogue()
    with transaction.atomic():
        # This command is not an update/reset of an existing installation.
        if any(model.objects.exists() for model in (ApplicationMaster,Permission,FeatureMaster,UserserviceConfig,Roles)) or User.all_objects.exists():
            raise ValueError('Identity catalogue installation requires empty metadata/users; overwrite prohibited')
        ApplicationMaster.objects.bulk_create([ApplicationMaster(**row) for row in value['applications']])
        Permission.objects.bulk_create([Permission(**row) for row in value['permissions']])
        FeatureMaster.objects.bulk_create([FeatureMaster(**row) for row in value['features']])
        UserserviceConfig.objects.bulk_create([UserserviceConfig(**row) for row in value['configuration']])
        roles = _roles(value)
    connection.close()
    return dict(status='IDENTITY_CATALOGUE_INSTALLED_NO_USER_PASSWORD_OR_SCOPE_CREATED',
        applications=len(value['applications']),permissions=len(value['permissions']),features=len(value['features']), **roles)


def repair_missing_roles():
    """Add missing retained metadata only; never create users or assign grants."""
    _setup()
    from django.db import transaction, connection
    from api.models import ApplicationMaster, Permission, FeatureMaster
    value = catalogue()
    with transaction.atomic():
        # Lock the installed application rows to serialize this repair.
        list(ApplicationMaster.objects.select_for_update().order_by('pk'))
        for model, rows, key in ((ApplicationMaster, 'applications', 'application_id'),
                                 (Permission, 'permissions', 'url'),
                                 (FeatureMaster, 'features', 'feature')):
            for definition in value[rows]:
                row = model.objects.get(**{key: definition[key]})
                if any(getattr(row, field) != expected for field, expected in definition.items()):
                    raise ValueError('Installed metadata differs; no repair: ' + rows)
        roles = _roles(value)
    connection.close()
    return dict(status='CANONICAL_ROLES_VERIFIED_NO_USER_OR_SCOPE_ASSIGNMENT', **roles)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repair-missing-roles', action='store_true')
    args = parser.parse_args()
    print(json.dumps(repair_missing_roles() if args.repair_missing_roles else install(), sort_keys=True))
