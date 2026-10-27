"""Authentication gateway deployment settings; preserve RSA database-password handling."""
import os
from release.configuration import load_secret, secret, public_url, database_options, security, email_settings, auth_site_key_cache
load_secret('SECRET_KEY')
# Existing browser-password cipher key is public client configuration, not a signing secret.
os.environ['SECRET_KEY_FOR_PASSWORD'] = secret('CLIENT_CIPHER_KEY')
os.environ['BASE_CLIENT_URL'] = public_url()[0]
from apps.settings import *  # noqa: E402,F403
from django.conf import global_settings
_site_key_cache = auth_site_key_cache()
if _site_key_cache is not None:
    CACHES = {**globals().get('CACHES', global_settings.CACHES), 'site_identity': _site_key_cache}
    AUTH_SITE_KEY_CACHE_ALIAS = 'site_identity'
globals().update(email_settings())
DATABASES['default']['OPTIONS'] = database_options({'options': '-c search_path=identity'})
security(globals())
