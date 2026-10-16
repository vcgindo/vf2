import os
import unittest
from unittest.mock import patch
from django.test import RequestFactory
from django.http import JsonResponse
from common.startup_probe import StartupProbeMiddleware, observed, _trace, permission_request


class StartupProbeTests(unittest.TestCase):
    def request(self, value='a' * 32 + '-1'):
        return RequestFactory().get('/api/user/profile/', HTTP_X_VF_PROBE_ID=value)

    def test_disabled_and_invalid_ids_do_not_change_response(self):
        for flag, value in [('0', 'a' * 32 + '-1'), ('1', 'invalid')]:
            with patch.dict(os.environ, VF_STARTUP_PROBE=flag):
                response = StartupProbeMiddleware(lambda request: JsonResponse({'detail': 'denied'}, status=401))(self.request(value))
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.content, b'{"detail": "denied"}')
                self.assertNotIn('Server-Timing', response)
                self.assertIsNone(_trace.get())

    def test_enabled_does_not_turn_denial_into_success(self):
        @observed('jwt_user')
        def denied(request):
            return JsonResponse({'detail': 'denied'}, status=401)
        with patch.dict(os.environ, VF_STARTUP_PROBE='1'):
            response = StartupProbeMiddleware(denied)(self.request())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.content, b'{"detail": "denied"}')
        self.assertEqual(response['X-VF-Probe-ID'], 'a' * 32 + '-1')
        self.assertIn('jwt_user;dur=', response['Server-Timing'])
        self.assertIsNone(_trace.get())

    def test_exception_propagates_and_context_is_cleared(self):
        @observed('jwt_user')
        def broken(request):
            raise ValueError('original exception')
        with patch.dict(os.environ, VF_STARTUP_PROBE='1'), self.assertRaisesRegex(ValueError, 'original exception'):
            StartupProbeMiddleware(broken)(self.request())
        self.assertIsNone(_trace.get())

    def test_permission_call_is_once_and_unmodified_when_disabled(self):
        with patch('requests.request', return_value='original') as request:
            self.assertEqual(permission_request('permission_mta', method='GET', url='http://mta/example'), 'original')
        request.assert_called_once_with(method='GET', url='http://mta/example')

    def test_correlated_child_keeps_headers_and_propagates_failure(self):
        token = _trace.set({'id': 'b' * 32 + '-2', 'timings': {}})
        try:
            with patch('requests.request', side_effect=ValueError('upstream')) as request:
                with self.assertRaisesRegex(ValueError, 'upstream'):
                    permission_request('permission_mta', method='GET', url='http://mta/example', headers={'Existing': 'kept'})
                self.assertEqual(request.call_args.kwargs['headers'], {'Existing': 'kept', 'X-VF-Probe-ID': 'b' * 32 + '-2'})
                self.assertIn('permission_mta', _trace.get()['timings'])
        finally:
            _trace.reset(token)
