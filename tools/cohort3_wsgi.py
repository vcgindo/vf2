"""Construct nested real gateway and MTA WSGI handlers without a network port."""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tools.cohort3_settings')

import django
django.setup()

from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from api_gateway.inprocess_mta import owned_wsgi_application


INNER_MARKER = 'cohort3.inner_mta'


class Cohort3InnerMtaUrlconfMiddleware:
    """Select the MTA URLConf only for the sealed nested WSGI invocation."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get(INNER_MARKER) is True:
            request.urlconf = 'vectorflow.urls'
        return self.get_response(request)


class _InnerMtaApplication:
    __slots__ = ('handler',)

    def __init__(self):
        self.handler = WSGIHandler()

    def __call__(self, environ, start_response):
        nested = dict(environ)
        nested[INNER_MARKER] = True
        return self.handler(nested, start_response)


def build_application():
    """Admit one explicit owner, then bind its real request-time WSGI guard."""
    current = getattr(settings, 'MTA_INPROCESS_WSGI_APPLICATION', None)
    if current is not None:
        raise RuntimeError('Cohort3 in-process MTA application is already bound')
    if (not getattr(settings, 'VF_COHORT3_OWNED_INPROCESS', False) or
            not settings.VF_MTA_PUBLISHED_RUN or not settings.VF_MTA_PUBLISHED_DIGEST):
        raise RuntimeError('Cohort3 proof requires one explicit selected run and digest')
    # This constructor executes the production startup admission. Its __call__
    # executes require_admission again for every nested /api/mta/ request.
    from mta.presentation.admission import AdmittedApplication
    admitted = AdmittedApplication(_InnerMtaApplication())
    settings.MTA_INPROCESS_WSGI_APPLICATION = owned_wsgi_application(admitted)
    return WSGIHandler()
