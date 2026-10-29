"""Private handoff from joint intake to calculation of accepted inputs.

No request field, environment variable or caller-supplied boolean enables this
handoff. The daily producer issues it after dependency-closed preparation;
persisted phase readers restore it from the phase's own accepted metadata.
Explicit standalone validators and diagnostic readers retain their behavior.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

CONTRACT = 'vectorflow-joint-daily-intake-v1'
_ISSUER = object()
_current = ContextVar('accepted_daily_inputs', default=None)
_execution_owner = ContextVar('accepted_daily_execution_owner', default=None)


class _AcceptedInputs:
    __slots__ = ('owner',)

    def __init__(self, issuer, owner):
        if issuer is not _ISSUER:
            raise TypeError('Only daily intake issues accepted inputs')
        self.owner = owner


def _complete(context):
    """Called only after the native gate has produced ReadyBprDay."""
    if context.native_daily:
        context.accepted_inputs = _AcceptedInputs(_ISSUER, context.identity)
        if _execution_owner.get() == context.identity:
            _current.set(context.accepted_inputs)


def _restore(context, metadata):
    if metadata.get('input_admission') == CONTRACT:
        context.accepted_inputs = _AcceptedInputs(_ISSUER, context.identity)


def accepted():
    return type(_current.get()) is _AcceptedInputs


def current():
    """Private writer handoff; callers cannot manufacture an admission."""
    return _current.get()


@contextmanager
def execution(owner):
    """Keep the gate's handoff through calculation and its atomic publication."""
    owner_token = _execution_owner.set(str(owner))
    token = _current.set(None)
    try:
        yield
    finally:
        _current.reset(token)
        _execution_owner.reset(owner_token)


@contextmanager
def consume(context):
    admitted = context.accepted_inputs
    if admitted is not None and (type(admitted) is not _AcceptedInputs
            or admitted.owner != context.identity):
        raise ValueError('Accepted inputs require their private daily owner')
    token = _current.set(admitted)
    try:
        yield
    finally:
        _current.reset(token)


def phase(function):
    @wraps(function)
    def produce(value, *args, **kwargs):
        with consume(value.context):
            return function(value, *args, **kwargs)
    return produce
