"""Bounded operational timings, never a business input or retained trace.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import logging
import sys
from time import perf_counter, process_time

_owner = ContextVar('daily_stage_owner', default=None)
_logger = logging.getLogger(__name__)


@contextmanager
def operation(owner):
    token = _owner.set(str(owner))
    try:
        yield
    finally:
        _owner.reset(token)


def _emit(name, event, **values):
    if _owner.get() is None:
        return
    # Fixed scalar metadata only: no state graph, row payload or per-truck log.
    if sys.platform != 'win32':
        import resource
        values['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
    _logger.warning('daily_stage %s', json.dumps(dict(owner=_owner.get(),
        stage=name, event=event, **values), sort_keys=True))


def summary(name, **counts):
    """One scalar summary per stage; never a row or truck event stream."""
    _emit(name, 'summary', **counts)


@contextmanager
def stage(name, **counts):
    wall, cpu = perf_counter(), process_time()
    _emit(name, 'begin', **counts)
    try:
        yield
    except BaseException as error:
        _emit(name, 'failure', seconds=perf_counter()-wall,
            cpu_seconds=process_time()-cpu, error_type=type(error).__name__)
        raise
    else:
        _emit(name, 'end', seconds=perf_counter()-wall,
            cpu_seconds=process_time()-cpu)
