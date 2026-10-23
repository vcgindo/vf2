"""Bounded reuse of successful immutable metadata checks within one read request.

Nothing survives the request. Each subsequent request rechecks live selection,
permissions, source files and database receipts. Offline callers stay uncached.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_current = ContextVar('presentation_read_request', default=None)


def in_read_request():
    return _current.get() is not None

# Explicit read-only routes, including POST-based report and MDM queries.
# Action, MDM, layout and remark writes never enter this scope.
READ_ROUTES = frozenset((
    'readyz',
    'GetAllPermmision', 'LocationType', 'GetEnvironmentConfiguration',
    'GetAllReports', 'GetUIConfig', 'GetLastRunDate', 'GetState',
    'GetBPRData', 'GetBPRDataCount', 'GetAnalyticsData', 'GetExportDataAsync',
    'GetPlanningDataGrid', 'GetPlanningDataCount', 'GetPlanningDataGraph',
    'GetPlanningDataGridCount', 'GetPlanningDataCustom',
    'GetResearchInsightData', 'GetHistroricalAvailabilityBPRData',
    'GetMasterUIConfiguration', 'GetCount', 'GetMasterData', 'GetSeasonalityDetails',
    'GetBTRData', 'GetBTRDataCount', 'DBMData', 'DBMDataCount',
    'RRRData', 'RRRDataCount', 'GetRRROrderAllocationReportData',
    'GetRRRAllocationReportDataCount', 'BORUIConfig', 'BORData', 'BORDataCount',
    'BORAnalytics', 'GetBOROrderAllocationReportData',
    'GetBOROrderAllocationReportDataCount', 'getSupplierWiseAllocationReportData',
    'getSupplierWiseAllocationReportDataCount',
    'DailyDataGraph', 'GetBufferTrendGraphData',
    'DBMNormSuggestionLoc', 'DBMNormSuggestionSKUs', 'DBMNormSuggestionPie',
    'DBMNormSuggestionAgeing', 'ChronicUnavailabilityLoc',
    'ChronicUnavailabilitySku', 'ChronicUnavailabilityGridViewData',
    'AvailabilityTrend', 'AvailabilityAgeing', 'ExcessInventorySku',
    'ExcessInventoryValue',
))

# Match the dynamic URL's parent as well as its finite report name. A bare
# basename must not accidentally opt an unrelated endpoint into read reuse.
PICK_READ_ROUTES = frozenset((
    'LogisticPickListReport', 'LogisticRemainingQtySummary',
    'LogisticRemainingQtyDetails', 'TransportReqSummaryRpt',
))


def _read_route(path):
    parent, _, name = path.rstrip('/').rpartition('/')
    return (name in READ_ROUTES or
            (parent.rsplit('/', 1)[-1] == 'DownloadReports' and name in PICK_READ_ROUTES))


@contextmanager
def read_request(path):
    if not _read_route(path) or _current.get() is not None:
        yield
        return
    token = _current.set({})
    try:
        yield
    finally:
        _current.reset(token)


def _argument(value):
    if hasattr(value, '_meta') and hasattr(value, 'pk'):
        return (type(value), value.pk, *(getattr(value, field, None) for field in
                ('kind', 'status', 'input_digest', 'input_manifest_digest', 'output_digest', 'production_digest',
                 'digest', 'implementation_digest', 'receipt_digest')))
    return value


def once_per_request(function):
    @wraps(function)
    def read(*args, **kwargs):
        cache = _current.get()
        if cache is None:
            return function(*args, **kwargs)
        key = (function, tuple(_argument(value) for value in args),
               tuple(sorted((name, _argument(value)) for name, value in kwargs.items())))
        if key not in cache:
            # Failed validation is never cached; exceptions propagate normally.
            value = function(*args, **kwargs)
            if len(cache) < 128:
                cache[key] = value
            return value
        return cache[key]
    return read
