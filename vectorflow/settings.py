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
MTA_TRUSTED_GATEWAY_HEADER = os.environ.get('MTA_TRUSTED_GATEWAY_HEADER', 'X-VectorFLOW-Identity')
VF_MDM_SOURCE_DIGEST = os.environ.get('VF_MDM_SOURCE_DIGEST', '')
VF_MTA_DAILY_PUBLICATION = os.environ.get('VF_MTA_DAILY_PUBLICATION', '') == '1'
VF_MTA_CONSUMPTION_POLICY = os.environ.get('VF_MTA_CONSUMPTION_POLICY', '')
VF_MTA_OPERATIONAL_POLICY = os.environ.get('VF_MTA_OPERATIONAL_POLICY', '')
VF_MTA_OPERATIONAL_RECEIPT = os.environ.get('VF_MTA_OPERATIONAL_RECEIPT', '')
VF_MTA_PLANNING_EXTENSION = os.environ.get('VF_MTA_PLANNING_EXTENSION', '')
VF_MTA_RRR_COLOUR_EXTENSION = os.environ.get('VF_MTA_RRR_COLOUR_EXTENSION', '')
VF_MTA_GUIDED_EXCESS_DISPOSITION = os.environ.get('VF_MTA_GUIDED_EXCESS_DISPOSITION', '')
VF_MTA_SYNTHETIC_ROSTER = os.environ.get('VF_MTA_SYNTHETIC_ROSTER', '')
VF_MTA_ALLOW_UNSELECTED_STARTUP = os.environ.get('VF_MTA_ALLOW_UNSELECTED_STARTUP', '') == '1'
VF_MTA_PUBLISHED_RUN = os.environ.get('VF_MTA_PUBLISHED_RUN', '')
VF_MTA_PUBLISHED_DIGEST = os.environ.get('VF_MTA_PUBLISHED_DIGEST', '')
VF_MTA_FIXTURE_FILE = os.environ.get('VF_MTA_FIXTURE_FILE', '')
VF_MTA_FIXTURE_SHA256 = os.environ.get('VF_MTA_FIXTURE_SHA256', '')
VF_BTR_REPORTING_GENERATION = os.environ.get('VF_BTR_REPORTING_GENERATION', '')
VF_BPR_PREPARED = os.environ.get('VF_BPR_PREPARED', '') == '1'
VF_GUIDED_PREPARED = os.environ.get('VF_GUIDED_PREPARED', '') == '1'
VF_RRR_PREPARED = os.environ.get('VF_RRR_PREPARED', '') == '1'
VF_HISTORY_REPORTS_PREPARED = os.environ.get('VF_HISTORY_REPORTS_PREPARED', '') == '1'
VF_RESEARCH_AVAILABILITY_PREPARED = os.environ.get('VF_RESEARCH_AVAILABILITY_PREPARED', '') == '1'
if VF_BTR_REPORTING_GENERATION:
    LOGGING = {'version': 1, 'disable_existing_loggers': False,
        'handlers': {'btr_console': {'class': 'logging.StreamHandler'}},
        'loggers': {'mta.presentation.btr_sql': {
            'handlers': ['btr_console'], 'level': 'INFO', 'propagate': False}}}
VF_MTA_PERMISSIONS_FILE = os.environ.get('VF_MTA_PERMISSIONS_FILE', '')
VF_MTA_PERMISSIONS_SHA256 = os.environ.get('VF_MTA_PERMISSIONS_SHA256', '')
VF_MTA_HIERARCHY_FILE = os.environ.get('VF_MTA_HIERARCHY_FILE', '')
VF_MTA_HIERARCHY_SHA256 = os.environ.get('VF_MTA_HIERARCHY_SHA256', '')
VF_MTA_PREDECESSOR_HIERARCHY_FILE = os.environ.get('VF_MTA_PREDECESSOR_HIERARCHY_FILE', '')
VF_MTA_TERMINAL_FILE = os.environ.get('VF_MTA_TERMINAL_FILE', '')
VF_MTA_TERMINAL_SHA256 = os.environ.get('VF_MTA_TERMINAL_SHA256', '')
VF_MTA_EXCESS_HISTORY_FILE = os.environ.get('VF_MTA_EXCESS_HISTORY_FILE', '')
VF_MTA_EXCESS_HISTORY_SHA256 = os.environ.get('VF_MTA_EXCESS_HISTORY_SHA256', '')
VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY = os.environ.get('VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY') == '1'
VF_MTA_ACTIONS_ENABLED = os.environ.get('VF_MTA_ACTIONS_ENABLED', '0') == '1'
VF_MTA_FORCE_HISTORY_FIXTURE = os.environ.get('VF_MTA_FORCE_HISTORY_FIXTURE', '')
VF_MTA_ACTION_TIME_ZONE = os.environ.get('VF_MTA_ACTION_TIME_ZONE', 'Asia/Kolkata')
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
    'OPTIONS': {'options': '-c search_path=mta,public', 'connect_timeout': 5},
    'TEST': {'NAME': 'test_freshvcf'},
}}

VF_MTA_PREACCEPTANCE_FILE = os.environ.get('VF_MTA_PREACCEPTANCE_FILE', '')
VF_MTA_PREACCEPTANCE_SHA256 = os.environ.get('VF_MTA_PREACCEPTANCE_SHA256', '')
