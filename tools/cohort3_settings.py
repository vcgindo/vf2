"""Combined, no-port Cohort3 proof settings; never a serving configuration."""
from copy import deepcopy
from datetime import timedelta

from vectorflow.settings import *  # noqa: F401,F403 - retain the accepted MTA settings


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'api',
    'mta.runtime',
]
AUTH_USER_MODEL = 'api.User'
ROOT_URLCONF = 'tools.cohort3_gateway_urls'
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'tools.cohort3_wsgi.Cohort3InnerMtaUrlconfMiddleware',
]
DATABASES['identity'] = deepcopy(DATABASES['default'])
DATABASES['identity']['OPTIONS'] = {
    **DATABASES['identity'].get('OPTIONS', {}),
    'options': '-c search_path=cohort3_identity,public',
}
DATABASES['identity']['TEST'] = {'NAME': 'test_freshvcf_cohort3_identity'}
DATABASE_ROUTERS = ['tools.cohort3_database_router.Cohort3DatabaseRouter']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('apps.authentication.CookieJWTAuthentication',),
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
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                      'LOCATION': 'cohort3-auth-proof'}}

# Installed only by tools.cohort3_wsgi after Django has initialized. A string or
# ordinary callable is rejected by the transport seam.
MTA_INPROCESS_WSGI_APPLICATION = None
VF_COHORT3_OWNED_INPROCESS = True
