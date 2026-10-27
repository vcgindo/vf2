"""Daily site identity, shared only when the deployment explicitly configures it."""
import secrets
from datetime import datetime

from django.conf import settings
from django.core.cache import caches


def get_site_key():
    cache_key = f"site_key_{datetime.utcnow().strftime('%Y-%m-%d')}"
    owner = caches[getattr(settings, 'AUTH_SITE_KEY_CACHE_ALIAS', 'default')]
    # get_or_set uses atomic add and rereads the winner. A cache failure must
    # propagate: choosing a worker-local replacement would invalidate sessions.
    return owner.get_or_set(cache_key, lambda: secrets.token_hex(16), timeout=60 * 60 * 25)
