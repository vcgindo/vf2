"""Opt-in, no-port WSGI transport for bounded MTA read proof.

The normal gateway transport remains ``requests.request``.  An owned proof
settings module may explicitly install a sealed WSGI application with
``owned_wsgi_application``; strings and unsealed callables are rejected.
"""
from io import BytesIO, StringIO
import json as json_module
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.http.response import ResponseHeaders
from api_gateway.mta_stream import runtime_report_download


GET_PATHS = frozenset('/api/mta/' + route for route in (
    'GetAllPermmision', 'LocationType', 'SKUDesc', 'WHDesc',
    'GetEnvironmentConfiguration', 'GetAllReports', 'GetUIConfig',
    'GetLastRunDate', 'BORUIConfig', 'BORAnalytics',
    'GetHistroricalAvailabilityBPRData',
))
POST_PATHS = frozenset('/api/mta/' + route for route in (
    'DBMData', 'DBMDataCount', 'RRRData', 'RRRDataCount',
    'GetRRROrderAllocationReportData', 'GetRRRAllocationReportDataCount',
    'GetBPRData', 'GetBPRDataCount', 'GetAnalyticsData', 'GetRemarkDetails',
    'GetBOROrderAllocationReportData', 'GetBOROrderAllocationReportDataCount',
    'GetBOROARemarkDetails', 'BORData', 'BORDataCount',
    'GetBORRemarkDetails', 'GetExportDataAsync',
    'GetPlanningDataGrid', 'GetPlanningDataCount', 'GetPlanningDataGraph',
    'GetPlanningDataGridCount', 'GetPlanningDataCustom',
    'GetBTRData', 'GetBTRDataCount', 'DailyDataGraph',
    'GetBufferTrendGraphData', 'GetResearchInsightData',
    'DBMNormSuggestionLoc', 'DBMNormSuggestionSKUs',
    'DBMNormSuggestionPie', 'DBMNormSuggestionAgeing',
    'ChronicUnavailabilityLoc', 'ChronicUnavailabilitySku',
    'ChronicUnavailabilityGridViewData', 'AvailabilityTrend',
    'AvailabilityAgeing', 'ExcessInventorySku', 'ExcessInventoryValue',
))
DOWNLOAD_PATHS = frozenset('/api/mta/DownloadReports/' + report for report in (
    'LogisticPickListReport', 'LogisticRemainingQtySummary',
    'LogisticRemainingQtyDetails', 'TransportReqSummaryRpt',
))


class InProcessMtaTransportError(ValueError):
    pass


class _OwnedWsgiApplication:
    __slots__ = ('application',)

    def __init__(self, application):
        if not callable(application):
            raise TypeError('MTA in-process WSGI application must be callable')
        self.application = application

    def __call__(self, environ, start_response):
        return self.application(environ, start_response)


def owned_wsgi_application(application):
    """Seal a callable selected directly by an owned Python proof config."""
    return _OwnedWsgiApplication(application)


MDM_WORKFLOW_PATHS = frozenset('/api/mta/' + route for route in (
    'AddMasterData', 'ModifyMasterData', 'PostMasterAfterApproved'))


class _OwnedMdmWorkflowApplication(_OwnedWsgiApplication):
    """Separate capability; never granted by the existing read-proof seal."""
    __slots__ = ('binding',)

    def __init__(self, application, binding):
        super().__init__(application)
        self.binding = binding


def _workflow_binding():
    return (settings.DATABASES['default']['NAME'],
            settings.VF_MDM_SOURCE_DIGEST, str(settings.VF_MTA_PUBLISHED_RUN),
            settings.VF_MTA_PUBLISHED_DIGEST)


def owned_mdm_workflow_application(application, *, run_id, output_digest):
    """Exact isolated approval-day transport; endpoint authentication still applies."""
    if (settings.SETTINGS_MODULE != 'tools.mdm_approval_day_settings'
            or settings.DATABASES['default']['NAME'] != 'fresh_mdm_approval_day_20261010_002'
            or settings.VF_MDM_SOURCE_DIGEST != '39f76f9c718a28e014737e8c856af7d29f1ab5dbdfd2370321a6cb539d010f8e'
            or not run_id or not output_digest
            or str(settings.VF_MTA_PUBLISHED_RUN) != str(run_id)
            or settings.VF_MTA_PUBLISHED_DIGEST != output_digest):
        raise InProcessMtaTransportError('mdm_workflow_owned_binding_required')
    return _OwnedMdmWorkflowApplication(application, _workflow_binding())


class WsgiResponse:
    """Small requests-compatible response over a real WSGI response iterable."""
    def __init__(self, status, headers, iterable, url):
        self.status_code = int(status.split(' ', 1)[0])
        self.headers = ResponseHeaders(dict(headers))
        self.url = url
        self._iterable = iter(iterable)
        self._close_target = iterable
        self._content = None
        self._closed = False

    def close(self):
        if self._closed:
            return
        self._closed = True
        close = getattr(self._close_target, 'close', None)
        if close:
            close()

    def iter_content(self, chunk_size=1, **_kwargs):
        if self._content is not None:
            source = (self._content,)
        else:
            source = self._iterable
        try:
            for chunk in source:
                if not isinstance(chunk, bytes):
                    raise TypeError('WSGI application yielded a non-bytes response chunk')
                for offset in range(0, len(chunk), chunk_size):
                    part = chunk[offset:offset + chunk_size]
                    if part:
                        yield part
        finally:
            if self._content is None:
                self.close()

    @property
    def content(self):
        if self._content is None:
            self._content = b''.join(self.iter_content(chunk_size=65536))
        return self._content

    @property
    def text(self):
        content_type = self.headers.get('Content-Type', '')
        charset = 'utf-8'
        for item in content_type.split(';')[1:]:
            if item.strip().lower().startswith('charset='):
                charset = item.split('=', 1)[1].strip()
        return self.content.decode(charset, errors='replace')

    def json(self):
        return json_module.loads(self.text)


def _query_string(parsed, params):
    values = parsed.query
    if params:
        extra = params.urlencode() if hasattr(params, 'urlencode') else urlencode(params, doseq=True)
        values = '&'.join(value for value in (values, extra) if value)
    return values


def _validate_target(method, url, base_url, *, workflow=False):
    if method not in ('GET', 'POST'):
        raise InProcessMtaTransportError('mta_inprocess_method_denied')
    parsed, base = urlsplit(url), urlsplit(base_url)
    if (parsed.scheme, parsed.netloc) != (base.scheme, base.netloc) or parsed.fragment:
        raise InProcessMtaTransportError('mta_inprocess_target_denied')
    allowed = GET_PATHS | DOWNLOAD_PATHS if method == 'GET' else POST_PATHS
    if workflow:
        allowed = MDM_WORKFLOW_PATHS if method == 'POST' else frozenset()
    if parsed.path not in allowed and not (not workflow and method == 'GET'
            and runtime_report_download(parsed.path)):
        raise InProcessMtaTransportError('mta_inprocess_path_denied')
    return parsed


def _wsgi_request(application, *, method, url, base_url, headers=None, params=None,
                  json=None, data=None, files=None, **_ignored):
    method = str(method).upper()
    parsed = _validate_target(method, url, base_url,
        workflow=isinstance(application, _OwnedMdmWorkflowApplication))
    if files or data is not None:
        raise InProcessMtaTransportError('mta_inprocess_json_reads_only')
    body = b'' if json is None else json_module.dumps(
        json, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    supplied = ResponseHeaders(headers or {})
    environ = {
        'REQUEST_METHOD': method,
        'SCRIPT_NAME': '',
        'PATH_INFO': parsed.path,
        'QUERY_STRING': _query_string(parsed, params),
        'SERVER_NAME': parsed.hostname or 'localhost',
        'SERVER_PORT': str(parsed.port or (443 if parsed.scheme == 'https' else 80)),
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': parsed.scheme,
        'wsgi.input': BytesIO(body),
        'wsgi.errors': StringIO(),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'CONTENT_LENGTH': str(len(body)),
    }
    for name, value in supplied.items():
        key = name.upper().replace('-', '_')
        if key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            environ[key] = str(value)
        else:
            environ['HTTP_' + key] = str(value)
    environ.setdefault('HTTP_HOST', parsed.netloc)
    captured = {}

    def start_response(status, response_headers, exc_info=None):
        if exc_info:
            raise exc_info[1].with_traceback(exc_info[2])
        captured['status'] = status
        captured['headers'] = response_headers

    iterable = application(environ, start_response)
    if 'status' not in captured:
        close = getattr(iterable, 'close', None)
        if close:
            close()
        raise InProcessMtaTransportError('mta_inprocess_invalid_wsgi_response')
    return WsgiResponse(captured['status'], captured['headers'], iterable, url)


def request(*, base_url, **kwargs):
    """Use the sealed WSGI application only when proof settings opt in."""
    application = getattr(settings, 'MTA_INPROCESS_WSGI_APPLICATION', None)
    if application is None:
        import requests
        return requests.request(**kwargs)
    if not isinstance(application, _OwnedWsgiApplication):
        raise InProcessMtaTransportError('mta_inprocess_application_not_owned')
    if isinstance(application, _OwnedMdmWorkflowApplication) and application.binding != _workflow_binding():
        raise InProcessMtaTransportError('mdm_workflow_owned_binding_changed')
    return _wsgi_request(application, base_url=base_url, **kwargs)
