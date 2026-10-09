"""Combined no-listener settings for the owned Cohort6 action phase."""
from copy import deepcopy
from datetime import timedelta

from vectorflow.settings import *  # noqa: F401,F403 - retain Fresh MTA settings


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'api',
    'mta.runtime',
]
AUTH_USER_MODEL = 'api.User'
AUTHENTICATION_BACKENDS = [
    'api.common.authentication_backends.CustomModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]
ROOT_URLCONF = 'vectorflow.urls'
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware']
# The dedicated issuer is NOINHERIT. PostgreSQL itself checks its membership
# before assuming this exact isolated owner; no serving setting consumes it.
DATABASES['default']['OPTIONS']['options'] += ' -c role=fresh_cohort6_owner_001'
DATABASES['identity'] = deepcopy(DATABASES['default'])
DATABASES['identity']['OPTIONS'] = {
    **DATABASES['identity'].get('OPTIONS', {}),
    'options': '-c search_path=cohort6_identity,public -c role=fresh_cohort6_owner_001',
}
DATABASES['identity']['TEST'] = {'NAME': 'test_freshvcf_cohort6_identity'}
DATABASE_ROUTERS = ['tools.cohort3_database_router.Cohort3DatabaseRouter']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.authentication.CookieJWTAuthentication',
    ),
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE':
        'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'AUTH_TOKEN_CLASSES': ('api_gateway.tokens.SiteScopedAccessToken',),
}
CACHES = {'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'cohort6-offline-actions',
}}

# The action phase calls Python APIs directly. It never installs a gateway
# transport or starts a serving application.
MTA_INPROCESS_WSGI_APPLICATION = None
