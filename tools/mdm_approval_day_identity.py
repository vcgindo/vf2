"""Install only the pinned S4 identity copy in its new private schema."""
import hashlib
import json

DATABASE = 'fresh_mdm_approval_day_20261010_002'
OWNER = 'fresh_mdm_day_owner_002'
SCHEMA = 'mdm_day_identity'
PAYLOAD_SHA = 'c67b10dfb26bcf5c0de485d50376abf020a64e1abb5f97090d999185aaf24ef9'
ACTORS = {2: 'nms.sob.moq.requester@vectorflow.local',
          3: 'nms.sob.moq.approver@vectorflow.local'}
PRODUCTS = {(2, 2, 71001), (3, 2, 71001), (3, 2, 71002)}
LOCATIONS = {(2, 2, 72001), (3, 2, 72001), (3, 2, 72003)}
MODELS = ('applicationmaster', 'user', 'roles', 'permission',
          'user_application_product_permission', 'user_application_location_permission',
          'user_application_data_permission', 'userserviceconfig', 'ads_config')


def validate(raw):
    if hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA:
        raise ValueError('Exact approved NMS identity export required')
    rows = json.loads(raw)
    keys = [(r['model'], r['pk']) for r in rows]
    if len(keys) != len(set(keys)) or any(k[0] not in {'api.' + m for m in MODELS} for k in keys):
        raise ValueError('Identity model/occurrence roster differs')
    users = {r['pk']: r['fields'] for r in rows if r['model'] == 'api.user'}
    if ({pk: r['email'] for pk, r in users.items()} != ACTORS
            or any(not r['is_active'] or r['is_admin'] or r['is_deleted'] for r in users.values())):
        raise ValueError('Exact active non-admin NMS actors required')
    for model, field, expected in (
        ('user_application_product_permission', 'productfilter_id', PRODUCTS),
        ('user_application_location_permission', 'locationfilter_id', LOCATIONS)):
        actual = {(r['fields']['user_id'], r['fields']['application_id'], r['fields'][field])
                  for r in rows if r['model'] == 'api.' + model}
        if actual != expected:
            raise ValueError('Existing NMS membership differs')
    return rows


def install(raw, *, resume_empty_schema=False):
    from django.apps import apps
    from django.core import serializers
    from django.core.management import call_command
    from django.core.management.color import no_style
    from django.db import connections, transaction
    from mta.mdm.owned_namespace import verify_binding
    from mta.runtime.mdm_models import MdmSource
    source_rows = validate(raw)
    verify_binding(MdmSource.objects.get().receipt)
    for alias in ('default', 'identity'):
        with connections[alias].cursor() as cursor:
            cursor.execute('SELECT current_database(), current_user')
            if cursor.fetchone() != (DATABASE, OWNER):
                raise ValueError('NMS identity destination ownership differs')
    with connections['identity'].cursor() as cursor:
        cursor.execute('SELECT to_regnamespace(%s)', [SCHEMA])
        exists = cursor.fetchone()[0] is not None
        if exists and not resume_empty_schema:
            raise ValueError('Identity schema exists; overwrite is prohibited')
        if not exists:
            cursor.execute('CREATE SCHEMA mdm_day_identity AUTHORIZATION fresh_mdm_day_owner_002')
    for app in ('contenttypes', 'auth', 'api'):
        call_command('migrate', app, database='identity', interactive=False, verbosity=0)
    objects = list(serializers.deserialize('json', raw.decode()))
    model_types = [apps.get_model('api', name) for name in MODELS]
    with transaction.atomic(using='identity'):
        if any(model._base_manager.using('identity').exists() for model in model_types):
            raise ValueError('Fresh identity migration unexpectedly installed source objects')
        for item in objects:
            item.save(using='identity')
        with connections['identity'].cursor() as cursor:
            for statement in connections['identity'].ops.sequence_reset_sql(no_style(), model_types):
                cursor.execute(statement)
        # Django's JSON serializer truncates datetime microseconds to milliseconds.
        # Read typed fields directly so exact source precision remains mandatory.
        actual = []
        for row in source_rows:
            model = apps.get_model(row['model'])
            obj = model._base_manager.using('identity').get(pk=row['pk'])
            fields = {}
            for name in row['fields']:
                field = model._meta.get_field(name)
                fields[name] = (list(getattr(obj, name).values_list('pk', flat=True))
                                if field.many_to_many else getattr(obj, field.attname))
            actual.append({'model': row['model'], 'pk': obj.pk, 'fields': fields})
        if sum(model._base_manager.using('identity').count() for model in model_types) != len(source_rows):
            raise ValueError('Complete imported identity roster differs')
        def normalized(rows):
            result = []
            for row in rows:
                model = apps.get_model(row['model'])
                fields = {}
                for name, value in row['fields'].items():
                    field = model._meta.get_field(name)
                    fields[name] = sorted(value) if field.many_to_many else field.to_python(value)
                result.append((row['model'], row['pk'], fields))
            return sorted(result, key=lambda r: (r[0], str(r[1])))
        if normalized(actual) != normalized(source_rows):
            raise ValueError('Complete imported identity readback differs')
    return {'actors': ACTORS, 'payload_sha256': PAYLOAD_SHA, 'schema': SCHEMA,
            'source_mutations': 0, 'new_grants': 0, 'credential_changes': 0}
