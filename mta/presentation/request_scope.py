"""Bounded reuse of successful immutable metadata checks within one read request.

Nothing survives the request. Each subsequent request rechecks live selection,
permissions, source files and database receipts. Offline callers stay uncached.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_current = ContextVar('presentation_read_request', default=None)
_metadata = ContextVar('presentation_metadata_operation', default=None)
_remark_validation = ContextVar('presentation_remark_validation', default=False)
_validation = ContextVar('presentation_validation_reads', default=None)


@contextmanager
def remark_validation():
    """Opt in only after the remark writer holds its source/run/journal locks."""
    from django.db import connection
    if (not connection.in_atomic_block or _remark_validation.get()
            or _current.get() is not None or _metadata.get() is not None):
        raise ValueError('Remark validation requires its own locked transaction')
    token = _remark_validation.set(True)
    try:
        yield
    finally:
        _remark_validation.reset(token)


@contextmanager
def validation_reads():
    """One pure metadata traversal; its cache cannot survive a producer call."""
    if not _remark_validation.get() or _validation.get() is not None:
        yield
        return
    from django.db import connection
    if not connection.in_atomic_block:
        raise ValueError('Remark validation transaction ended')
    def read_only(execute, sql, params, many, context):
        # These finite metadata readers issue SELECTs, including fixed invoker
        # read helpers. Producer SQL, DDL, role changes and nested transactions
        # belong outside this phase and must never inherit a read cache.
        words = sql.lstrip().split(None, 1) if isinstance(sql, str) else []
        if not words or words[0].upper() != 'SELECT':
            raise ValueError('SQL write or control statement inside remark validation')
        if ';' in sql:
            import sqlparse
            statements = sqlparse.parse(sql)
            if (len(statements) != 1 or statements[0].get_type() != 'SELECT'
                    or any(token.ttype in sqlparse.tokens.Keyword.DML and token.value.upper() != 'SELECT'
                        for token in statements[0].flatten())):
                raise ValueError('Multiple or modifying statements inside remark validation')
        return execute(sql, params, many, context)
    token = _validation.set({})
    try:
        with connection.execute_wrapper(read_only):
            yield
    finally:
        _validation.reset(token)


def validated_read(function):
    @wraps(function)
    def read(*args, **kwargs):
        with validation_reads():
            return function(*args, **kwargs)
    return read


def in_validation_reads():
    return _validation.get() is not None


@contextmanager
def metadata_operation():
    """Fresh read-only startup pass; never enables HTTP/cross-request reuse."""
    token = _metadata.set({})
    try:
        yield
    finally:
        _metadata.reset(token)


def in_read_request():
    return _current.get() is not None

# Explicit read-only routes, including POST-based report and MDM queries.
# Action, MDM, layout and remark writes never enter this scope.
READ_ROUTES = frozenset((
    'readyz',
    'GetAllPermmision', 'LocationType', 'GetEnvironmentConfiguration', 'SKUDesc', 'WHDesc',
    'GetAllReports', 'GetUIConfig', 'GetLastRunDate', 'GetState',
    'GetBPRData', 'GetBPRDataCount', 'GetAnalyticsData', 'GetExportDataAsync', 'GetRemarkDetails',
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
    'LogisticRemainingQtyDetails', 'TransportReqSummaryRpt', 'InputData',
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
    if type(value) in (str, int, bool, float, bytes, type(None)):
        return (type(value), value)
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
            cache = _metadata.get()
        physical = None
        if cache is None and _validation.get() is not None:
            from django.db import connection
            physical = connection.connection
            if physical is not None and not physical.closed:
                cache = _validation.get()
        if cache is None:
            return function(*args, **kwargs)
        key = (function, physical, tuple(_argument(value) for value in args),
               tuple(sorted((name, _argument(value)) for name, value in kwargs.items())))
        if key not in cache:
            # Failed validation is never cached; exceptions propagate normally.
            value = function(*args, **kwargs)
            if len(cache) < 128:
                cache[key] = value
            return value
        return cache[key]
    return read


def once_per_metadata_operation(function):
    """Only startup's guarded immutable reads, never HTTP or writer reuse."""
    cached = once_per_request(function)
    @wraps(function)
    def read(*args, **kwargs):
        if _metadata.get() is None or kwargs.get('reading') is False:
            return function(*args, **kwargs)
        return cached(*args, **kwargs)
    return read
