"""External deployment configuration, independent of Django/application imports."""
import os
import re
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


def auth_site_key_cache():
    """An explicit site-owned namespace; never reuse the permission cache."""
    location = secret('VF_AUTH_SITE_CACHE_URL', required=False)
    namespace = os.environ.get('VF_AUTH_SITE_KEY_NAMESPACE', '')
    if not location and not namespace:
        return None  # Retained unconfigured installations keep their old boundary.
    if not location or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:._-]{0,127}', namespace):
        raise ValueError('Supply both VF_AUTH_SITE_CACHE_URL and an explicit VF_AUTH_SITE_KEY_NAMESPACE')
    url = urlsplit(location)
    if (url.scheme not in ('redis', 'rediss') or not url.hostname
            or not re.fullmatch(r'/[0-9]+', url.path) or url.query or url.fragment):
        raise ValueError('VF_AUTH_SITE_CACHE_URL must identify one Redis database')
    try:
        port = url.port
    except ValueError:
        raise ValueError('VF_AUTH_SITE_CACHE_URL has an invalid port') from None
    if port is not None and not 1 <= port <= 65535:
        raise ValueError('VF_AUTH_SITE_CACHE_URL has an invalid port')
    return dict(BACKEND='django.core.cache.backends.redis.RedisCache', LOCATION=location,
                KEY_PREFIX='vectorflow:site-key:' + namespace,
                OPTIONS=dict(socket_connect_timeout=5, socket_timeout=5))


def integer(name, default, *, minimum=1, maximum=65535):
    value = int(os.environ.get(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(name + ': outside supported range')
    return value


def email_settings():
    """Optional SMTP, shared by the auth runtime and installer; never build secrets."""
    def flag(name, default):
        value = os.environ.get(name, default).lower()
        if value not in ('true', 'false', '1', '0'):
            raise ValueError(name + ': use true or false')
        return value in ('true', '1')

    host = os.environ.get('EMAIL_HOST', '').strip()
    sender = os.environ.get('EMAIL_FROM', '').strip()
    username = os.environ.get('EMAIL_USER', '')
    password = os.environ.get('EMAIL_PASS', '')
    tls, ssl = flag('EMAIL_USE_TLS', 'true'), flag('EMAIL_USE_SSL', 'false')
    if tls and ssl:
        raise ValueError('Enable EMAIL_USE_TLS or EMAIL_USE_SSL, not both')
    if host and not sender:
        raise ValueError('EMAIL_FROM is required when EMAIL_HOST is configured')
    if bool(username) != bool(password):
        raise ValueError('Supply both EMAIL_USER and EMAIL_PASS, or neither for an authorized relay')
    return dict(EMAIL_HOST=host, EMAIL_PORT=integer('EMAIL_PORT', 587),
        EMAIL_HOST_USER=username, EMAIL_HOST_PASSWORD=password,
        EMAIL_USE_TLS=tls, EMAIL_USE_SSL=ssl,
        EMAIL_TIMEOUT=integer('EMAIL_TIMEOUT', 15, maximum=120),
        DEFAULT_FROM_EMAIL=sender)


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
    role = os.environ.get('DB_SESSION_ROLE')
    if role:
        import re
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', role):
            raise ValueError('DB_SESSION_ROLE requires a PostgreSQL identifier')
        value['options'] = (value.get('options', '') + ' -c role=' + role).strip()
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
