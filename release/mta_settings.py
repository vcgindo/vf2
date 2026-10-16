"""Production deployment settings; the native calculation/admission contracts are unchanged."""
from release.configuration import load_secret, database_options, security
load_secret('VF_SECRET_KEY')
load_secret('VF_DB_PASSWORD')
from vectorflow.settings import *  # noqa: E402,F403
DATABASES['default']['OPTIONS'] = database_options(DATABASES['default']['OPTIONS'])
security(globals())
