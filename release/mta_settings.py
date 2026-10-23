"""Production deployment settings; the native calculation/admission contracts are unchanged."""
from release.configuration import load_secret, database_options, security
load_secret('VF_SECRET_KEY')
load_secret('VF_DB_PASSWORD')
from vectorflow.settings import *  # noqa: E402,F403
DATABASES['default']['OPTIONS'] = database_options(DATABASES['default']['OPTIONS'])
# Keep at most the existing worker's connection, with health checks and a finite
# lifetime. Reconnecting safely invalidates its native identity memo.
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
security(globals())
