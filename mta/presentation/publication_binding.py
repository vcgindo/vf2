"""Browser publication binding; no selection, session or business-state writer.

Only report reads participate. Installation/MDM metadata and commands retain
their existing contracts. A read-only snapshot survives lazy export iteration.
"""
from contextlib import ExitStack, contextmanager
import json

from django.conf import settings
from django.db import connection, transaction
from django.http import JsonResponse

from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest

HEADER = 'X-VectorFLOW-Publication'
SCOPE_HEADER = 'X-VectorFLOW-Report-Scope'
ENVIRON_HEADER = 'HTTP_X_VECTORFLOW_PUBLICATION'
BOOTSTRAP = '/api/mta/PublicationBinding'

# These are report consumers, not the wider metadata/MDM read-cache allowlist.
REPORTS = frozenset('''GetLastRunDate GetOrderAllocationReportData GetOrderAllocationReportDataCount
GetElephantOrderData GetElephantOrderDataCount GetBPRData GetBPRDataCount
GetAnalyticsData GetExportDataAsync GetRemarkDetails GetPlanningDataGrid
GetPlanningDataCount GetPlanningDataGraph GetPlanningDataGridCount GetPlanningDataCustom
GetInTransitWhereAboutsData GetInTransitWhereAboutsDataCount GetTransporterDetails
GetRemarkDetailsForInTransit GetOpenExpediteRequest GetRemarkDetailsForExpedite
GetResearchInsightData GetHistroricalAvailabilityBPRData GetBTRData GetBTRDataCount
DBMData DBMDataCount RRRData RRRDataCount GetRRROrderAllocationReportData
GetRRRAllocationReportDataCount BORData BORDataCount BORAnalytics
GetBOROrderAllocationReportData GetBOROrderAllocationReportDataCount
getSupplierWiseAllocationReportData getSupplierWiseAllocationReportDataCount
GetBOROARemarkDetails GetBORRemarkDetails DailyDataGraph GetBufferTrendGraphData
DBMNormSuggestionLoc DBMNormSuggestionSKUs DBMNormSuggestionPie DBMNormSuggestionAgeing
ChronicUnavailabilityLoc ChronicUnavailabilitySku ChronicUnavailabilityGridViewData
AvailabilityTrend AvailabilityAgeing ExcessInventorySku ExcessInventoryValue'''.split())


def report_path(path):
    parent, _, name = path.rstrip('/').rpartition('/')
    return ((parent == '/api/mta' and name in REPORTS)
            or parent == '/api/mta/DownloadReports')


def enabled():
    # The retained legacy/non-native interfaces do not claim this guarantee.
    return bool(getattr(settings, 'VF_MTA_NATIVE_PUBLICATION', False))


def identity(admitted):
    """Bound existing owners, including mutable consumer context, not row bags."""
    from mta.presentation import scoped_selection
    from mta.presentation.context import configured_run
    from mta.runtime.models import RunCommand
    from mta.runtime.ancillary_models import RemarkOwner
    from mta.runtime.logistics_models import LogisticsHistoryOwner, TransitLiveGeneration
    from mta.runtime.daily_request_models import DailyRequestOwner
    if scoped_selection.enabled():
        view = scoped_selection.selected()
        run_id, reference = view.run_id, view.read_identity
    else:
        run_id, reference = configured_run().pk, None
    # RunCommand is protected append order; retain the terminal commitment too.
    command = RunCommand.objects.filter(run_id=run_id).order_by('-pk').values(
        'pk', 'digest', 'after_digest', 'state_sealed').first()
    remarks = list(RemarkOwner.objects.order_by('pk').values(
        'family', 'provenance_digest', 'next_ordinal')[:4])
    logistics = list(LogisticsHistoryOwner.objects.order_by('pk').values(
        'name', 'provenance_digest', 'revision', 'next_ordinal')[:2])
    transit = list(TransitLiveGeneration.objects.filter(run_id=run_id).values(
        'source_digest', 'revision'))
    requests = list(DailyRequestOwner.objects.order_by('pk').values(
        'name', 'provenance_digest', 'revision')[:2])
    if len(remarks) > 3 or len(logistics) > 1 or len(requests) > 1:
        raise PublicationUnavailable('publication_binding_owner_population_unqualified')
    return digest(dict(schema='fresh-report-publication-v1', admission=admitted,
        run_id=str(run_id), reference=reference, command=command, remarks=remarks,
        logistics=logistics, transit=transit, requests=requests))


def scoped_identity(publication, gateway):
    """The gateway commits its effective scope; the browser cannot select it."""
    scope = gateway.get('report_scope_digest')
    if (not isinstance(scope, str) or len(scope) != 64
            or any(char not in '0123456789abcdef' for char in scope)):
        raise PublicationUnavailable('publication_binding_gateway_scope_required')
    return digest(dict(schema='fresh-scoped-report-publication-v1', publication=publication,
                       actor=gateway['id'], report_scope_digest=scope))


@contextmanager
def snapshot():
    if connection.vendor != 'postgresql' or connection.in_atomic_block:
        raise PublicationUnavailable('publication_binding_snapshot_unavailable')
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        yield


def bootstrap_view(request):
    """Routed normally through Django; the middleware validates trusted identity."""
    if request.method != 'GET':
        return JsonResponse({'error': 'method_not_allowed'}, status=405)
    if not hasattr(request, '_publication_binding'):
        return JsonResponse({'error': 'publication_binding_not_admitted'}, status=503)
    value = {'mode': 'native' if enabled() else 'legacy',
             'binding': request._publication_binding}
    if enabled():
        # Reuse the normal Full/scoped date reader inside this same admitted
        # snapshot. The client need not make another admission round trip just
        # to label the count/grid reads bound by this response.
        from mta.presentation.views import last_run_date
        date_response = last_run_date(request)
        if date_response.status_code != 200:
            raise PublicationUnavailable('publication_date_unavailable')
        value['date_response'] = json.loads(date_response.content)
    response = JsonResponse(value)
    response['Cache-Control'] = 'no-store'
    return response


class PublicationBindingMiddleware:
    """Enter after request_started; leave before request_finished closes DBs."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        bootstrap = request.path == BOOTSTRAP
        if not bootstrap and not report_path(request.path):
            return self.get_response(request)
        # Existing non-native report handlers own method/auth error precedence.
        # Only the new bootstrap endpoint adds an authenticated legacy response.
        if not bootstrap and not enabled():
            return self.get_response(request)
        from mta.presentation.views import identity as gateway_identity
        gateway = gateway_identity(request)
        if gateway is None:
            return JsonResponse({'error': 'gateway_identity_required'}, status=403)
        if not enabled():
            request._publication_binding = None
            return self.get_response(request)
        stack = ExitStack()
        try:
            stack.enter_context(snapshot())
            from mta.presentation.request_scope import read_request
            # WSGI admission's outer scope ends when it returns the iterable.
            # Own a fresh scope here, including the entire lazy report body.
            stack.enter_context(read_request(request.path, fresh=True))
            from mta.presentation import scoped_selection
            # Full admission and consumer validation share one snapshot/cache.
            # Certified scoped readiness retains its existing owned preflight.
            admitted = (request.META.get('vectorflow.admitted_publication')
                        if scoped_selection.enabled() else None)
            if admitted is None:
                from mta.presentation.admission import require_admission
                admitted = require_admission()
            token = scoped_identity(identity(admitted), {
                'id': gateway['id'], 'report_scope_digest': request.headers.get(SCOPE_HEADER)})
            request._publication_binding = token
            if not bootstrap and request.headers.get(HEADER) != token:
                response = JsonResponse({'error': 'publication_binding_missing_or_stale'}, status=409)
                response['Cache-Control'] = 'no-store'
            else:
                response = self.get_response(request)
                if not bootstrap:
                    response[HEADER] = token
            if not response.streaming:
                stack.close()
                return response
            original = iter(response.streaming_content)
            closed = False
            def close():
                nonlocal closed
                if closed:
                    return
                closed = True
                try:
                    closer = getattr(original, 'close', None)
                    if closer:
                        closer()
                finally:
                    stack.close()
            def chunks():
                try:
                    yield from original
                finally:
                    close()
            response.streaming_content = chunks()
            # Response.close executes these before request_finished. This also
            # covers a disconnect before the generator's first next().
            response._resource_closers.insert(0, close)
            return response
        except Exception:
            stack.close()
            return JsonResponse({'error': 'publication_binding_unavailable'}, status=503)
        except BaseException:
            stack.close()
            raise
