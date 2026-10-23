"""Production deployment settings; the native calculation/admission contracts are unchanged."""
from release.configuration import load_secret, database_options, security
load_secret('VF_SECRET_KEY')
load_secret('VF_DB_PASSWORD')
from vectorflow.settings import *  # noqa: E402,F403
DATABASES['default']['OPTIONS'] = database_options(DATABASES['default']['OPTIONS'])
# Keep at most the existing synchronous worker's healthy connection. Every
# request still checks the live snapshot/session; a reconnect invalidates reuse.
DATABASES['default']['CONN_MAX_AGE'] = None
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
security(globals())
