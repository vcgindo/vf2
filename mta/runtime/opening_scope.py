"""Operation-local reuse of sealed opening material, never live MDM state.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_current = ContextVar('native_immutable_opening', default=None)
_ISSUER = object()


class _Operation:
    def __init__(self):
        self.cache = {}
        self.handles = set()


class CertifiedOpeningHandle:
    """Unforgeable operation-local proof of an already certified admission."""
    def __init__(self, issuer, identity, metadata):
        if issuer is not _ISSUER:
            raise ValueError('Certified opening handle issuer differs')
        self.identity = identity
        self.metadata = metadata


@contextmanager
def opening_scope():
    if _current.get() is not None:
        yield
        return
    token = _current.set(_Operation())
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


def sealed_identity(owner):
    """Bind prepared immutable material to the complete refreshed DB seal."""
    from django.db import connections
    alias = getattr(getattr(owner, '_state', None), 'db', None) or 'default'
    database = connections[alias].settings_dict
    return (alias, database.get('HOST'), database.get('PORT'), database.get('NAME'),
            owner.pk, owner.source_id, owner.input_digest, owner.input_manifest_digest,
            owner.receipt_digest, owner.configuration_digest, owner.recipe_sha256,
            owner.implementation_digest, owner.input_sha256)


def immutable(owner, name, build):
    """Only sealed rows/derived facts; source, queues and admissions stay live.

    A refreshed seal or database identity cannot borrow an earlier value.
    Callers must not mutate the shared opening; calculation already copies its
    own working state. Nothing is retained beyond the operation/capture phase.
    """
    operation = _current.get()
    if operation is None:
        return build()
    cache = operation.cache
    key = (name, *sealed_identity(owner))
    if key not in cache:
        # Store only successful results, and only a bounded number of openings.
        value = build()
        if len(cache) < 64:
            cache[key] = value
        return value
    return cache[key]


def release_opening():
    """Drop capture-only material before allocating the calculation graph."""
    operation = _current.get()
    if operation is not None:
        operation.cache.clear()


def certify_opening(owner, metadata):
    """Install a validated private handle in the current preparation operation."""
    operation = _current.get()
    if operation is None or not isinstance(metadata, tuple):
        raise ValueError('Certified opening handle requires an active operation')
    identity = sealed_identity(owner)
    exact = [handle for handle in operation.handles if handle.identity == identity]
    if exact:
        if len(exact) == 1 and exact[0].metadata == metadata:
            return exact[0]
        raise ValueError('Certified opening handle metadata differs')
    if any(handle.identity[:6] == identity[:6] for handle in operation.handles):
        raise ValueError('Certified opening handle is stale')
    handle = CertifiedOpeningHandle(_ISSUER, identity, metadata)
    operation.handles.add(handle)
    return handle


def require_certified_opening(owner, handle):
    operation = _current.get()
    if (operation is None or not isinstance(handle, CertifiedOpeningHandle)
            or handle not in operation.handles or handle.identity != sealed_identity(owner)):
        raise ValueError('Certified opening handle is absent or stale')
    return handle.metadata


def current_certified_opening(owner):
    """Return this operation's exact handle; reject a matching stale seal."""
    operation = _current.get()
    if operation is None:
        return None
    identity = sealed_identity(owner)
    exact = [handle for handle in operation.handles if handle.identity == identity]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError('Duplicate certified opening handles')
    # Database alias/name plus initialization/source identify the same owner;
    # any remaining difference is a refreshed seal and must fail closed.
    prefix = identity[:4]
    owner_key = identity[4:6]
    if any(handle.identity[:4] == prefix and handle.identity[4:6] == owner_key
           for handle in operation.handles):
        raise ValueError('Certified opening handle is stale')
    return None
