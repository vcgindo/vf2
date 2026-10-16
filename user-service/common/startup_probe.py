"""Opt-in local timing only; never stores tokens, identities, queries or bodies."""
from contextvars import ContextVar
from functools import wraps
import json
import logging
import os
import re
import time

_trace = ContextVar('startup_probe', default=None)
logger = logging.getLogger(__name__)


def observed(name):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            trace = _trace.get()
            if trace is None:
                return function(*args, **kwargs)
            start = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                trace['timings'][name] = trace['timings'].get(name, 0) + (time.perf_counter() - start) * 1000
        return call
    return decorate


def permission_request(name, *args, **kwargs):
    import requests
    trace = _trace.get()
    if trace is not None:
        kwargs['headers'] = {**kwargs.get('headers', {}), 'X-VF-Probe-ID': trace['id']}
    return observed(name)(requests.request)(*args, **kwargs)


class StartupProbeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        probe_id = request.META.get('HTTP_X_VF_PROBE_ID', '')
        if (os.environ.get('VF_STARTUP_PROBE') != '1'
                or not (request.path == '/api/user/profile/' or request.path.startswith('/api/mta/'))
                or not re.fullmatch(r'[a-f0-9]{32}-[0-9]{1,6}', probe_id)):
            return self.get_response(request)
        from django.db import connection
        trace = dict(id=probe_id, path=request.path, started_ms=time.time() * 1000,
                     timings={}, sql_count=0)
        token = _trace.set(trace)
        start = time.perf_counter()

        def sql(execute, query, params, many, context):
            before = time.perf_counter()
            try:
                return execute(query, params, many, context)
            finally:
                trace['sql_count'] += 1
                trace['timings']['sql'] = trace['timings'].get('sql', 0) + (time.perf_counter() - before) * 1000
        try:
            with connection.execute_wrapper(sql):
                response = self.get_response(request)
            trace['timings']['server'] = (time.perf_counter() - start) * 1000
            trace['status'] = response.status_code
            response['X-VF-Probe-ID'] = probe_id
            response['Server-Timing'] = ', '.join(f'{key};dur={value:.3f}' for key, value in trace['timings'].items())
            return response
        finally:
            trace['finished_ms'] = time.time() * 1000
            _trace.reset(token)
            logger.warning('VF_STARTUP %s', json.dumps(trace, sort_keys=True))
