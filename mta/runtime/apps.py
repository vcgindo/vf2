from django.apps import AppConfig


def ensure_mta_schema(sender, using, **kwargs):
    # The standalone service uses a named schema. Django's freshly created
    # test database does not run the container initialization SQL, so this
    # permanent initialization must precede its first model migration as well.
    from django.db import connections
    with connections[using].cursor() as cursor:
        cursor.execute('CREATE SCHEMA IF NOT EXISTS mta')


class RuntimeConfig(AppConfig):
    name = 'mta.runtime'
    label = 'fresh_mta'

    def ready(self):
        from django.db.models.signals import pre_migrate
        pre_migrate.connect(ensure_mta_schema, sender=self, dispatch_uid='fresh_mta_schema')
