"""Offline selector/stream proof; entitlement tests live in api_gateway.tests."""
import json
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from api_gateway.mta_stream import (RUNTIME_REPORT_DOWNLOAD_PATHS, runtime_report_download,
    streams_mta_read, bounded_mta_read, streamed_response)


class RuntimeReportDownloadSelectorsTests(SimpleTestCase):
    def test_selectors_equal_retained_native_report_names_not_generated_filenames(self):
        retained = json.loads((Path(__file__).resolve().parents[2] /
            'tests/fixtures/runtime_reports_retained_20261019.json').read_bytes())
        reports = {row['Id']:row for row in retained}
        self.assertEqual(RUNTIME_REPORT_DOWNLOAD_PATHS, frozenset(
            '/api/mta/DownloadReports/'+reports[key]['ReportName'] for key in (2,3,4,5,6,7,8,10)))
        self.assertEqual(reports[7]['FileName'], 'Spiker_Order_Dump')
        self.assertTrue(reports[7]['Compression'])
        self.assertEqual(reports[10]['FileName'], '%TotalReqReport%')
        self.assertFalse(reports[10]['Compression'])

    def test_only_eight_exact_native_selectors_acquire_transport_authority(self):
        for route in RUNTIME_REPORT_DOWNLOAD_PATHS:
            for method in ('GET','POST'):
                request = SimpleNamespace(path=route, method=method)
                self.assertTrue(streams_mta_read(request))
                self.assertTrue(bounded_mta_read(request))
            self.assertFalse(streams_mta_read(SimpleNamespace(path=route, method='DELETE')))
        for name in ('Spiker_Order_Dump.zip', 'Spike_Order_Dump.zip', 'spike_order_dump',
                     'TotalReqReport_2026-10-26', 'TotalReqReport_2026-02-30',
                     'TotalReqReport_2026-10-26.csv', 'TotalReqReport_YYYY-MM-DD.csv',
                     '../Spike_Order_Dump', 'download/Spike_Order_Dump',
                     '%53pike_Order_Dump', 'Spike_Order_Dump/', 'ForeignReport'):
            route = '/api/mta/DownloadReports/'+name
            request = SimpleNamespace(path=route, method='GET')
            with self.subTest(name=name):
                self.assertFalse(runtime_report_download(route))
                self.assertFalse(streams_mta_read(request))
                self.assertFalse(bounded_mta_read(request))
        for name in ('LogisticPickListReport','BOR_OrderAllocation'):
            self.assertTrue(streams_mta_read(SimpleNamespace(
                path='/api/mta/DownloadReports/'+name, method='GET')))
        self.assertFalse(streams_mta_read(SimpleNamespace(
            path='/api/mto/DownloadReports/Spike_Order_Dump', method='GET')))

    async def test_accepted_file_bytes_and_headers_stream_without_buffering(self):
        class Upstream:
            status_code = 200
            headers = {'Content-Type':'application/zip',
                'Content-Disposition':'attachment; filename="Spiker_Order_Dump.zip"'}
            closed = False

            def iter_content(self, chunk_size):
                yield b'zip'
                yield b'bytes'

            def close(self):
                self.closed = True

        upstream = Upstream()
        response = streamed_response(SimpleNamespace(
            path='/api/mta/DownloadReports/Spike_Order_Dump', method='GET'), upstream)
        self.assertEqual(response['Content-Disposition'], upstream.headers['Content-Disposition'])
        self.assertEqual(b''.join([part async for part in response]), b'zipbytes')
        self.assertTrue(upstream.closed)
