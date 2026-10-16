"""External deployment configuration, independent of Django/application imports."""
import os
from pathlib import Path
from urllib.parse import urlsplit


def secret(name, *, required=True):
    value = os.environ.get(name)
    filename = os.environ.get(name + '_FILE')
    if value is not None and filename:
        raise ValueError(name + ': supply a value or a file, not both')
    if filename:
        value = Path(filename).read_text(encoding='utf-8').rstrip('\r\n')
    if required and not value:
        raise ValueError(name + ' or ' + name + '_FILE is required')
    return value or ''


def load_secret(name):
    os.environ[name] = secret(name)
    os.environ.pop(name + '_FILE', None)


def integer(name, default, *, minimum=1, maximum=65535):
    value = int(os.environ.get(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(name + ': outside supported range')
    return value


def public_url():
    value = os.environ.get('VF_PUBLIC_URL', '').rstrip('/')
    url = urlsplit(value)
    if (url.scheme not in ('http', 'https') or not url.hostname or url.username
            or url.password or url.path not in ('', '/') or url.query or url.fragment):
        raise ValueError('VF_PUBLIC_URL must be an explicit HTTP(S) origin')
    if url.scheme == 'http' and url.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('Plain HTTP is supported only on loopback; use TLS for external deployment')
    return value, url


def database_options(options=None):
    value = dict(options or {})
    mode = os.environ.get('DB_SSLMODE', 'disable')
    if mode not in ('disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'):
        raise ValueError('DB_SSLMODE is invalid')
    value.update(sslmode=mode, connect_timeout=integer('DB_CONNECT_TIMEOUT', 5, maximum=300))
    for env, key in [('DB_SSLROOTCERT', 'sslrootcert'), ('DB_SSLCERT', 'sslcert'), ('DB_SSLKEY', 'sslkey')]:
        if os.environ.get(env):
            value[key] = os.environ[env]
    return value


def security(namespace):
    origin, parsed = public_url()
    hosts = [h.strip() for h in os.environ.get('VF_ALLOWED_HOSTS', parsed.hostname).split(',') if h.strip()]
    if '*' in hosts or not hosts:
        raise ValueError('VF_ALLOWED_HOSTS requires explicit hosts')
    secure = parsed.scheme == 'https'
    namespace.update(DEBUG=False, ALLOWED_HOSTS=hosts,
        CSRF_TRUSTED_ORIGINS=[origin], CORS_ALLOWED_ORIGINS=[origin], CORS_ALLOW_ALL_ORIGINS=False,
        SESSION_COOKIE_SECURE=secure, CSRF_COOKIE_SECURE=secure,
        SESSION_COOKIE_SAMESITE='Strict', CSRF_COOKIE_SAMESITE='Strict',
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
        SECURE_HSTS_SECONDS=31536000 if secure else 0,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=secure, SECURE_HSTS_PRELOAD=False,
        LOGGING={'version': 1, 'disable_existing_loggers': False,
            'handlers': {'console': {'class': 'logging.StreamHandler'}},
            'root': {'handlers': ['console'], 'level': os.environ.get('LOG_LEVEL', 'INFO')}})
