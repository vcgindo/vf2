# DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""Bounded forwarding of large MTA read responses under Django ASGI.

The MTA service owns these JSON/download bodies. The gateway still authenticates
and injects scopes; it must not build a second report object graph to forward it.
Other service and command response adapters retain their existing behavior.
"""
import threading

from asgiref.sync import sync_to_async
from django.http import StreamingHttpResponse


READ_PATHS = frozenset('/api/mta/' + route for route in (
    'RRRData', 'GetBPRData', 'GetBTRData', 'DBMData', 'GetExportDataAsync',
    # Both share the wide native report used by the observed overlapping request.
    # Forwarding safely does not certify these unfinished pages' business flows.
    'ChronicUnavailabilityLoc', 'ChronicUnavailabilitySku',
))
PICK_DOWNLOAD_PATHS = frozenset('/api/mta/DownloadReports/' + key for key in (
    'LogisticPickListReport', 'LogisticRemainingQtySummary',
    'LogisticRemainingQtyDetails', 'TransportReqSummaryRpt',
    'BOR_OrderAllocation',
))
INPUT_ARCHIVE_PATHS = frozenset(('/api/mta/DownloadReports/InputData',))
RUNTIME_REPORT_DOWNLOAD_PATHS = frozenset('/api/mta/DownloadReports/' + name for name in (
    'Spike_Order_Dump', 'TotalReqReport_YYYY-MM-DD',
))
COUNT_PATHS = frozenset('/api/mta/' + route for route in (
    'RRRDataCount', 'GetBPRDataCount', 'GetBTRDataCount', 'DBMDataCount',
))
# Bound requests that previously outlived nginx's existing60-second public wait.
# A report exceeding that window remains unavailable, not a new business result.
UPSTREAM_TIMEOUT = (5, 60)
_END = object()


def runtime_report_download(path):
    """Recognize only the two released native RuntimeReports ReportNames.

    The literal YYYY-MM-DD suffix is part of the captured ReportName, not a
    wildcard. The backend resolves the exact generated file from its receipt.
    """
    return type(path) is str and path in RUNTIME_REPORT_DOWNLOAD_PATHS


def streams_mta_read(request):
    return request.method in ('GET', 'POST') and (request.path in READ_PATHS | PICK_DOWNLOAD_PATHS | INPUT_ARCHIVE_PATHS
        or runtime_report_download(request.path))


def bounded_mta_read(request):
    return request.method in ('GET', 'POST') and (request.path in READ_PATHS | COUNT_PATHS | PICK_DOWNLOAD_PATHS | INPUT_ARCHIVE_PATHS
        or runtime_report_download(request.path))


class UpstreamChunks:
    """Async iteration prevents Django ASGI from materializing a sync iterator."""

    def __init__(self, response):
        self.response = response
        self.chunks = response.iter_content(chunk_size=65536)
        self.closed = False
        self.lock = threading.Lock()

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
        self.response.close()

    def __del__(self):
        # Also release a response discarded before ASGI starts consuming it.
        self.close()

    def __aiter__(self):
        return self

    def _next(self):
        return next(self.chunks, _END)

    async def __anext__(self):
        try:
            while not self.closed:
                chunk = await sync_to_async(self._next, thread_sensitive=False)()
                if chunk is _END:
                    break
                if chunk:
                    return chunk
        except BaseException:
            # close() may wait for a socket read; never block the ASGI loop.
            await sync_to_async(self.close, thread_sensitive=False)()
            raise
        await sync_to_async(self.close, thread_sensitive=False)()
        raise StopAsyncIteration


def streamed_response(request, upstream):
    if not streams_mta_read(request) or upstream.status_code != 200:
        return None
    result = StreamingHttpResponse(
        UpstreamChunks(upstream), status=upstream.status_code,
        content_type=upstream.headers.get('Content-Type', 'application/json'),
    )
    if 'Content-Disposition' in upstream.headers:
        result['Content-Disposition'] = upstream.headers['Content-Disposition']
    # iter_content decodes transport compression: do not forward Content-Length,
    # Content-Encoding or hop-by-hop headers from the upstream transport.
    return result
