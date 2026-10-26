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
_admission_preflight = ContextVar('presentation_admission_preflight', default=False)


@contextmanager
def admission_preflight(*, enabled):
    """Allow certified metadata reuse only before the HTTP handler is entered.

    This creates no request/graph cache and grants no permission to reuse checks
    inside an action transaction. Offline and startup callers do not enter it.
    """
    if not enabled:
        yield
        return
    from django.db import connection
    if connection.in_atomic_block or not connection.get_autocommit():
        yield
        return
    token = _admission_preflight.set(True)
    try:
        yield
    finally:
        _admission_preflight.reset(token)


def in_admission_preflight():
    return _admission_preflight.get()


@contextmanager
def remark_validation():
    """Opt in only after the remark writer holds its source/run/journal locks."""
    from django.db import connection
    if (not connection.in_atomic_block or _remark_validation.get()
            or _current.get() is not None or _metadata.get() is not None
            or _admission_preflight.get()):
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


def metadata_guard_check(verify, cursor):
    """Reuse one successful catalogue check only under an unchanged live stamp.

    Startup crosses transaction boundaries. Its ordinary metadata dictionary
    alone cannot certify that a later catalogue/session is still the same.
    Writer transactions and non-default connections retain full verification.
    """
    cache = _metadata.get()
    database = getattr(cursor, 'db', None)
    physical = getattr(database, 'connection', None)
    if cache is None or physical is None or physical.closed:
        return verify(cursor)
    from django.db import connection, connections, DEFAULT_DB_ALIAS
    if database is not connections[DEFAULT_DB_ALIAS]:
        return verify(cursor)
    from mta.presentation.identity_reuse import stamp
    before = stamp()
    if before is None or connection.connection is not physical:
        return verify(cursor)
    key = (metadata_guard_check, verify, database, physical, before)
    if key in cache:
        return cache[key]
    value = verify(cursor)
    if stamp() == before and connection.connection is physical and len(cache) < 128:
        cache[key] = value
    return value


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
    'GetInTransitWhereAboutsData', 'GetInTransitWhereAboutsDataCount',
    'GetTransporterDetails', 'GetRemarkDetailsForInTransit',
    'GetOpenExpediteRequest', 'GetRemarkDetailsForExpedite',
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
    'BOR_OrderAllocation',
    'Spike_Order_Dump', 'TotalReqReport_YYYY-MM-DD',
    'DailyDataUnavailabilityReport','InvalidDataReport','NMSAddNewSKULoc','NMSModifySKULoc',
    'NMSRemoveSKULoc','NMSLocMaster','NMSSKUMaster','NMSSOBMaster','NMSMOQMaster','ForceNormChangeUpload',
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
        # A producer may call an already declared immutable reader between
        # writes. Give that traversal the same SELECT-only scope as an
        # explicitly validated reader, then discard it before returning.
        if (_remark_validation.get() and _validation.get() is None
                and _current.get() is None and _metadata.get() is None):
            with validation_reads():
                return read(*args, **kwargs)
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
