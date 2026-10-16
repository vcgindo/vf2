"""Direct-port MTO deployment settings; retain its separate database and contract."""
from release.configuration import load_secret, database_options, security
load_secret('SECRET_KEY')
load_secret('DB_PASSWORD')
from MTO_API.settings import *  # noqa: E402,F403
DATABASES['default']['OPTIONS'] = database_options({'options': '-c search_path=mto'})
security(globals())
