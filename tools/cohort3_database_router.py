"""Keep Cohort3 identity models in their owned schema and MTA models in mta."""


IDENTITY_APPS = frozenset(('api', 'auth', 'contenttypes'))


class Cohort3DatabaseRouter:
    def db_for_read(self, model, **hints):
        return 'identity' if model._meta.app_label in IDENTITY_APPS else 'default'

    def db_for_write(self, model, **hints):
        return 'identity' if model._meta.app_label in IDENTITY_APPS else 'default'

    def allow_relation(self, obj1, obj2, **hints):
        left = self.db_for_read(obj1.__class__)
        right = self.db_for_read(obj2.__class__)
        return left == right

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in IDENTITY_APPS:
            return db == 'identity'
        return db == 'default'
