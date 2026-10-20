"""Operation-local reuse of sealed opening material, never live MDM state.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_current = ContextVar('native_immutable_opening', default=None)


@contextmanager
def opening_scope():
    if _current.get() is not None:
        yield
        return
    token = _current.set({})
    try:
        yield
    finally:
        _current.reset(token)


def opening_operation(function):
    @wraps(function)
    def run(*args, **kwargs):
        with opening_scope():
            return function(*args, **kwargs)
    return run


def immutable(owner, name, build):
    """Only sealed rows/derived facts; source, queues and admissions stay live.

    A refreshed seal or database identity cannot borrow an earlier value.
    Callers must not mutate the shared opening; calculation already copies its
    own working state. Nothing is retained beyond the operation/capture phase.
    """
    cache = _current.get()
    if cache is None:
        return build()
    from django.db import connections
    alias = getattr(getattr(owner, '_state', None), 'db', None) or 'default'
    database = connections[alias].settings_dict
    key = (name, alias, database.get('HOST'), database.get('PORT'), database.get('NAME'),
           owner.pk, owner.source_id, owner.input_digest, owner.input_manifest_digest,
           owner.receipt_digest, owner.configuration_digest, owner.recipe_sha256,
           owner.implementation_digest, owner.input_sha256)
    if key not in cache:
        # Store only successful results, and only a bounded number of openings.
        value = build()
        if len(cache) < 64:
            cache[key] = value
        return value
    return cache[key]


def release_opening():
    """Drop capture-only material before allocating the calculation graph."""
    cache = _current.get()
    if cache is not None:
        cache.clear()
