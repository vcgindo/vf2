"""Authentication gateway deployment settings; preserve RSA database-password handling."""
import os
from release.configuration import load_secret, secret, public_url, database_options, security, email_settings
load_secret('SECRET_KEY')
# Existing browser-password cipher key is public client configuration, not a signing secret.
os.environ['SECRET_KEY_FOR_PASSWORD'] = secret('CLIENT_CIPHER_KEY')
os.environ['BASE_CLIENT_URL'] = public_url()[0]
from apps.settings import *  # noqa: E402,F403
globals().update(email_settings())
DATABASES['default']['OPTIONS'] = database_options({'options': '-c search_path=identity'})
security(globals())
