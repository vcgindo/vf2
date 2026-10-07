"""Evidence policy belongs to one synchronous engine invocation, never global state."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy

_mode = ContextVar('daily_evidence_mode', default='validation')


def validating():
    return _mode.get() == 'validation'


@contextmanager
def evidence_mode(mode):
    if mode not in ('production', 'validation'):
        raise ValueError('Evidence mode must be production or validation')
    token = _mode.set(mode)
    try:
        yield
    finally:
        _mode.reset(token)


def snapshot(value):
    """Validation owns a snapshot; production consumes the yielded working value.

    Production callers must consume with final_stage, or copy only a required
    report before advancing a mutating producer. Never accumulate live snapshots.
    """
    return deepcopy(value) if validating() else value


def final_stage(iterator):
    if validating():
        return list(iterator)
    last = None
    for last in iterator:
        pass
    return [] if last is None else [last]
