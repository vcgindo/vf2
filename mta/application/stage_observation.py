"""Bounded operational timings, never a business input or retained trace.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import contextmanager, nullcontext, ExitStack
from contextvars import ContextVar
from functools import wraps
from inspect import signature
import json
import logging
import sys
from time import perf_counter, process_time, time

_owner = ContextVar('daily_stage_owner', default=None)
_stages = ContextVar('daily_stage_path', default=())
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
    # Observers must never replace a business result/exception if a log sink fails.
    try:
        stack = _stages.get()
        path = stack if stack and stack[-1][0] == name else (*stack, (name, _owner.get()))
        if sys.platform != 'win32':
            import resource
            values['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
        _logger.warning('daily_stage %s', json.dumps(dict(owner=_owner.get(),
            stage=name, event=event, stage_path='/'.join(part[0] for part in path),
            parent_stage=path[-2][0] if len(path) > 1 else None,
            parent_owner=path[-2][1] if len(path) > 1 else None,
            observed_at_unix=time(), timing='inclusive', **values), sort_keys=True))
    except Exception:
        pass


def summary(name, **counts):
    """One scalar summary per stage; never a row or truck event stream."""
    _emit(name, 'summary', **counts)


@contextmanager
def stage(name, **counts):
    wall, cpu = perf_counter(), process_time()
    token = _stages.set((*_stages.get(), (name, _owner.get())))
    try:
        _emit(name, 'begin', **counts)
        try:
            yield
        except BaseException as error:
            _emit(name, 'failure', seconds=perf_counter()-wall,
                cpu_seconds=process_time()-cpu, error_type=type(error).__name__, **counts)
            raise
        else:
            _emit(name, 'end', seconds=perf_counter()-wall,
                cpu_seconds=process_time()-cpu, **counts)
    finally:
        _stages.reset(token)


def observed(name, *, owner_parameter=None):
    """Install an owner at an entry point; nested calls keep existing custody."""
    def decorate(function):
        parameters = signature(function)
        @wraps(function)
        def call(*args, **kwargs):
            owner = name
            if _owner.get() is None and owner_parameter is not None:
                try:
                    owner = name + ':' + str(parameters.bind_partial(*args, **kwargs).arguments.get(owner_parameter, 'unknown'))[:80]
                except Exception:
                    pass  # The function retains its own argument/type failures.
            with (operation(owner) if _owner.get() is None else nullcontext()), stage(name):
                return function(*args, **kwargs)
        return call
    return decorate


@contextmanager
def observe_exit(context, name):
    """Time an existing context's exit, without changing its transaction policy.

    Enter the timing last, then let the original context commit/rollback before
    closing the timer. body_failed distinguishes an earlier rejection from an
    exit failure; the original context retains exception/suppression ownership.
    """
    with ExitStack() as observer:
        with context:
            failed = True
            try:
                yield
                failed = False
            finally:
                observer.enter_context(stage(name, body_failed=failed))


def stock_rejection(*, sku_code, location_code, business_date, match_count, reason, identity):
    """One bounded rejected key, never matched rows or arbitrary exception text."""
    def text(value):
        return str(value)[:80] if isinstance(value, (str, int)) else None
    try:
        _emit('current_physical_stock', 'rejection', sku_code=text(sku_code),
            location_code=text(location_code), business_date=text(business_date),
            match_count=match_count, reason=reason, identity=text(identity))
    except Exception:
        pass
