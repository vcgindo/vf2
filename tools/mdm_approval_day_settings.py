"""Isolated no-listener authentication settings for the approved MDM exercise."""
from copy import deepcopy
from tools.cohort6_settings import *  # noqa: F401,F403 - unchanged login contract

DATABASES = deepcopy(DATABASES)
DATABASES['default']['OPTIONS']['options'] = (
    '-c search_path=mta,public -c role=fresh_mdm_day_owner_002')
DATABASES['identity'] = deepcopy(DATABASES['default'])
DATABASES['identity']['OPTIONS']['options'] = (
    '-c search_path=mdm_day_identity,public -c role=fresh_mdm_day_owner_002')
DATABASES['identity']['TEST'] = {'NAME': 'test_fresh_mdm_day_identity'}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                      'LOCATION': 'mdm-day-offline-actions'}}
