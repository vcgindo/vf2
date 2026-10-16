"""Install only retained application/permission/feature metadata into a NEW identity schema."""
import json
import os
from pathlib import Path


def install():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','release.auth_settings')
    import django
    django.setup()
    from django.db import transaction, connection
    from api.models import ApplicationMaster, Permission, FeatureMaster, UserserviceConfig, User
    value=json.loads(Path(__file__).with_name('identity_catalogue.json').read_text(encoding='utf-8'))
    if value['schema']!='vectorflow-identity-catalogue-v1':
        raise ValueError('Identity catalogue version differs')
    with transaction.atomic():
        # This command is not an update/reset of an existing installation.
        if any(model.objects.exists() for model in (ApplicationMaster,Permission,FeatureMaster,UserserviceConfig)) or User.all_objects.exists():
            raise ValueError('Identity catalogue installation requires empty metadata/users; overwrite prohibited')
        ApplicationMaster.objects.bulk_create([ApplicationMaster(**row) for row in value['applications']])
        Permission.objects.bulk_create([Permission(**row) for row in value['permissions']])
        FeatureMaster.objects.bulk_create([FeatureMaster(**row) for row in value['features']])
        UserserviceConfig.objects.bulk_create([UserserviceConfig(**row) for row in value['configuration']])
    connection.close()
    return dict(status='IDENTITY_CATALOGUE_INSTALLED_NO_USER_PASSWORD_OR_SCOPE_CREATED',
        applications=len(value['applications']),permissions=len(value['permissions']),features=len(value['features']))


if __name__=='__main__':
    print(json.dumps(install(),sort_keys=True))
