import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import requests
from django.core.handlers.asgi import ASGIHandler
from django.test import SimpleTestCase

from api_gateway.mta_stream import streamed_response, streams_mta_read


class Upstream:
    status_code = 200
    headers = {'Content-Type': 'application/json', 'Content-Encoding': 'gzip',
               'Content-Length': '123'}

    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.close_count = 0

    def iter_content(self, chunk_size):
        assert chunk_size == 65536
        return self.chunks

    def close(self):
        self.close_count += 1

    @property
    def text(self):
        raise AssertionError('Do not decode body')

    @property
    def content(self):
        raise AssertionError('Do not buffer body')

    def json(self):
        raise AssertionError('Do not parse body')


class MtaStreamTests(SimpleTestCase):
    def request(self, path='/api/mta/RRRData', method='POST'):
        return SimpleNamespace(path=path, method=method)

    async def test_exact_bytes_async_iteration_and_close(self):
        upstream = Upstream([b'{"data":[', b'', b'1,1,null', b']}', b''])
        response = streamed_response(self.request(), upstream)
        self.assertTrue(response.is_async)
        self.assertEqual(b''.join([part async for part in response]), b'{"data":[1,1,null]}')
        self.assertNotIn('Content-Encoding', response)
        self.assertNotIn('Content-Length', response)
        response.close()
        self.assertEqual(upstream.close_count, 1)

    async def test_download_bytes_and_headers(self):
        upstream = Upstream([b'column\r\n', b'"a,b"\r\n'])
        upstream.headers = {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename="report.csv"'}
        response = streamed_response(self.request('/api/mta/GetExportDataAsync'), upstream)
        self.assertEqual(response['Content-Disposition'], upstream.headers['Content-Disposition'])
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertEqual(b''.join([part async for part in response]), b'column\r\n"a,b"\r\n')

    def test_errors_commands_and_other_services_are_not_adapted(self):
        for path in ('/api/mto/GetBTRData', '/api/mta/ApplyNorm', '/api/mta/v1/runs'):
            self.assertFalse(streams_mta_read(self.request(path)))
        for status in (400, 403, 404, 500):
            upstream = Upstream([]); upstream.status_code = status
            self.assertIsNone(streamed_response(self.request(), upstream))

    def test_pre_header_timeout_is_504_for_get_and_post(self):
        from api_gateway.views import API_GATEWAY_VIEW
        interceptor = MagicMock()
        interceptor.return_value.forward.side_effect = requests.ReadTimeout('upstream wait')
        with patch('api_gateway.views.service_map', {'mta': {'interceptor': interceptor}}):
            for route in ('/api/mta/RRRData', '/api/mta/GetBTRDataCount'):
                for method in ('GET', 'POST'):
                    response = getattr(API_GATEWAY_VIEW(), method.lower())(self.request(route, method))
                    self.assertEqual(response.status_code, 504)
                    self.assertIn(b'"error": "Failed to forward request"', response.content)

    def test_get_missing_download_closes_upstream_and_keeps_404(self):
        from api_gateway.views import API_GATEWAY_VIEW
        upstream = Upstream([])
        upstream.status_code = 404
        upstream.headers = {'Content-Disposition': 'attachment; filename="missing.csv"'}
        with patch.object(API_GATEWAY_VIEW, '_forward', return_value=upstream):
            response = API_GATEWAY_VIEW().get(self.request('/api/mta/GetExportDataAsync', 'GET'))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b'')
        self.assertEqual(upstream.close_count, 1)

    async def test_iteration_failure_closes_upstream(self):
        def fail():
            yield b'first'
            raise requests.exceptions.ReadTimeout('bounded read failed')
        upstream = Upstream(fail())
        response = streamed_response(self.request(), upstream)
        with self.assertRaises(requests.exceptions.ReadTimeout):
            _ = [part async for part in response]
        self.assertEqual(upstream.close_count, 1)

    async def test_asgi_first_chunk_before_completion_and_disconnect_cleanup(self):
        release = threading.Event()
        def chunks():
            yield b'first'
            release.wait(3)
            yield b'last'
        upstream = Upstream(chunks())
        original_close = upstream.close
        def close():
            original_close(); release.set()
        upstream.close = close
        response = streamed_response(self.request(), upstream)
        first = asyncio.Event()
        disconnect = asyncio.Event()
        sent = []
        initial = True
        async def receive():
            nonlocal initial
            if initial:
                initial = False
                return {'type': 'http.request', 'body': b'', 'more_body': False}
            await disconnect.wait()
            return {'type': 'http.disconnect'}
        async def send(message):
            sent.append(message)
            if message.get('body') == b'first':
                first.set()
        handler = ASGIHandler()
        scope = dict(type='http', method='POST', path='/api/mta/RRRData', headers=[],
                     query_string=b'', server=('localhost',80), scheme='http', http_version='1.1')
        with patch.object(handler, 'get_response_async', AsyncMock(return_value=response)):
            task = asyncio.create_task(handler(scope, receive, send))
            try:
                await asyncio.wait_for(first.wait(), 2)
                self.assertFalse(release.is_set(), 'Whole body was buffered before sending')
                disconnect.set()
                await asyncio.wait_for(task, 2)
                self.assertEqual(upstream.close_count, 1)
            finally:
                release.set()
                if not task.done():
                    task.cancel()


class ReadinessTests(SimpleTestCase):
    def test_failed_mta_dependency_is_not_reported_ready(self):
        from apps.urls import readyz
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
        with patch('apps.urls.connection', connection), \
             patch('apps.urls.requests.get', side_effect=requests.ConnectionError):
            response = readyz(None)
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'"mta": false', response.content)
