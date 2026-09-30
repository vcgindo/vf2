"""Fresh MTA service: explicit PostgreSQL configuration, no legacy runtime."""
import os

SECRET_KEY = os.environ.get('VF_SECRET_KEY', '')
if not SECRET_KEY:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured('VF_SECRET_KEY is required')
DEBUG = False
ALLOWED_HOSTS = os.environ.get('VF_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
INSTALLED_APPS = ['django.contrib.contenttypes', 'mta.runtime']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware']
ROOT_URLCONF = 'vectorflow.urls'
USE_TZ = True
TIME_ZONE = 'UTC'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.environ.get('VF_DB_NAME', 'freshvcf'),
    'USER': os.environ.get('VF_DB_USER', 'freshvcf'),
    'PASSWORD': os.environ.get('VF_DB_PASSWORD', ''),
    'HOST': os.environ.get('VF_DB_HOST', 'localhost'),
    'PORT': os.environ.get('VF_DB_PORT', '5432'),
    'OPTIONS': {'options': '-c search_path=mta,public'},
    'TEST': {'NAME': 'test_freshvcf'},
}}
