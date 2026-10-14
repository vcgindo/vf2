"""Explicit native upload-audit initialization policy admission."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


FIELDS = frozenset(('horizon', 'timezone', 'client_folder'))


def validate_policy(profile):
    """Return the validated policy, or None when the profile omits it."""
    if 'native_upload_audit' not in profile:
        return None
    policy = profile['native_upload_audit']
    if not isinstance(policy, dict) or set(policy) != FIELDS:
        raise ValueError('Native upload audit policy fields differ')
    horizon = policy['horizon']
    if type(horizon) is not int or horizon < 0:
        raise ValueError('Native upload audit horizon must be a nonnegative integer')
    timezone = policy['timezone']
    if type(timezone) is not str:
        raise ValueError('Native upload audit timezone must be an IANA name')
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('Native upload audit timezone must be an IANA name') from None
    client_folder = policy['client_folder']
    if client_folder is not None and (type(client_folder) is not str
                                      or not client_folder.strip()):
        raise ValueError('Native upload audit client folder must be null or nonblank text')
    return policy
