"""Deterministic WSGI binding proof; no database or serving mutation."""
from contextlib import ExitStack, contextmanager
import json
import os
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import SimpleTestCase, override_settings
from mta.presentation import publication_binding as binding
from django.http import JsonResponse
from django.urls import path

urlpatterns = [path('api/mta/PublicationBinding', binding.bootstrap_view),
               path('api/mta/RRRData', lambda request: JsonResponse({'rows': []}))]


@override_settings(VF_MTA_NATIVE_PUBLICATION=True)
class PublicationBindingTests(SimpleTestCase):
    @property
    def token(self):
        return binding.scoped_identity(self.publication, self.gateway)

    @token.setter
    def token(self, publication):
        self.publication = publication

    def setUp(self):
        self.active = False
        self.events = []
        self.gateway = {'id': 7, 'report_scope_digest': 'c' * 64}
        self.token = 'a' * 64
        @contextmanager
        def snapshot():
            self.active = True
            self.events.append('open')
            try:
                yield
            finally:
                self.active = False
                self.events.append('close')
        owner = patch.object(binding, 'snapshot', snapshot)
        owner.start()
        self.addCleanup(owner.stop)
        owner = patch.object(binding, 'identity', side_effect=lambda admitted: self.publication)
        owner.start()
        self.addCleanup(owner.stop)
        self.date_body = {'status': 200, 'data': [{'formatted': '19 Oct 2026', 'rawDate': '2026-10-19'}]}
        from mta.presentation.views import last_run_date
        self.real_date_reader = last_run_date
        def date_response(request=None, *args):
            self.assertTrue(self.active)
            return JsonResponse(self.date_body)
        owner = patch('mta.presentation.views.last_run_date', side_effect=date_response)
        self.date_reader = owner.start()
        self.addCleanup(owner.stop)
        def admitted():
            from mta.presentation.request_scope import in_read_request
            self.assertTrue(self.active)
            self.assertTrue(in_read_request())
            return 'admitted'
        owner = patch('mta.presentation.admission.require_admission', side_effect=admitted)
        self.admission_reader = owner.start()
        self.addCleanup(owner.stop)

    def call(self, path, claim=None, application=None, consume=True, authenticated=True, gateway=None, method='GET'):
        from django.test import RequestFactory
        from django.http import JsonResponse
        headers = {'HTTP_X_VECTORFLOW_IDENTITY': json.dumps({'id': (gateway or self.gateway)['id']})} if authenticated else {}
        if authenticated:
            headers['HTTP_X_VECTORFLOW_REPORT_SCOPE'] = (gateway or self.gateway).get('report_scope_digest', '')
        if claim is not None:
            headers[binding.ENVIRON_HEADER] = claim
        request = getattr(RequestFactory(), method.lower())(path, **headers)
        request.META['vectorflow.admitted_publication'] = 'admitted'
        downstream = application or Mock(side_effect=lambda request: binding.bootstrap_view(request)
            if path == binding.BOOTSTRAP else JsonResponse({'rows': 'result'}))
        response = binding.PublicationBindingMiddleware(downstream)(request)
        if consume and response.streaming:
            body = b''.join(response.streaming_content)
            response.close()
        else:
            body = response.content if consume else response
        return response.status_code, body, downstream

    def test_bootstrap_then_count_cutover_data_and_paging_export_reject(self):
        status, body, _ = self.call(binding.BOOTSTRAP)
        self.assertEqual(json.loads(body)['binding'], self.token)
        self.assertEqual(json.loads(body)['date_response'], self.date_body)
        self.assertEqual(self.call('/api/mta/RRRDataCount', self.token)[0], 200)
        old = self.token
        self.token = 'b' * 64
        for route in ('RRRData', 'GetBTRData', 'GetPlanningDataGraph', 'GetExportDataAsync'):
            status, body, downstream = self.call('/api/mta/' + route, old)
            self.assertEqual(status, 409)
            self.assertEqual(json.loads(body)['error'], 'publication_binding_missing_or_stale')
            downstream.assert_not_called()

    def test_missing_binding_denied_and_metadata_mdm_action_paths_unchanged(self):
        status, _, downstream = self.call('/api/mta/GetBTRData')
        self.assertEqual(status, 409)
        downstream.assert_not_called()
        for route in ('GetState', 'GetMasterData', 'GetCount', 'DBMApplySelectedNorms', 'AddRemark'):
            self.assertEqual(self.call('/api/mta/' + route)[0], 200)

    def test_explicit_acquisition_returns_owner_date_in_same_snapshot_only_for_reads(self):
        value = json.loads(self.call(binding.BOOTSTRAP)[1])
        self.assertTrue(value['report_acquisition'])
        response = self.call('/api/mta/GetBTRData', binding.ACQUIRE, consume=False)[1]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response[binding.HEADER], self.token)
        self.assertEqual(json.loads(response[binding.DATE_HEADER]), self.date_body)
        self.assertEqual(response['Cache-Control'], 'no-store')
        for route in ('GetExportDataAsync', 'DownloadReports/LogisticPickListReport'):
            status, _, downstream = self.call('/api/mta/' + route, binding.ACQUIRE)
            self.assertEqual(status, 409)
            downstream.assert_not_called()
        for claim in (None, '', 'ACQUIRE', 'random'):
            self.assertEqual(self.call('/api/mta/GetBTRData', claim)[0], 409)

    def test_scoped_cannot_advertise_or_accept_fast_acquisition(self):
        with patch('mta.presentation.scoped_selection.enabled', return_value=True):
            value = json.loads(self.call(binding.BOOTSTRAP)[1])
            self.assertFalse(value['report_acquisition'])
            self.assertEqual(self.call('/api/mta/GetBTRData', binding.ACQUIRE)[0], 409)

    def test_acquisition_date_failure_precedes_body_and_error_response_has_no_date(self):
        self.date_reader.side_effect = lambda *args: JsonResponse({'error': 'missing'}, status=503)
        status, _, downstream = self.call('/api/mta/GetBTRData', binding.ACQUIRE)
        self.assertEqual(status, 503)
        downstream.assert_not_called()
        self.date_reader.side_effect = lambda *args: JsonResponse(self.date_body)
        response = self.call('/api/mta/GetBTRData', binding.ACQUIRE,
            application=lambda request: JsonResponse({'error': 'denied'}, status=403), consume=False)[1]
        self.assertNotIn(binding.DATE_HEADER, response)

    def test_date_failure_cannot_publish_a_successful_binding_envelope(self):
        self.date_reader.side_effect = lambda *args: JsonResponse({'error': 'date unavailable'}, status=503)
        status, body, _ = self.call(binding.BOOTSTRAP)
        self.assertEqual(status, 503)
        self.assertNotIn('binding', json.loads(body))

    def test_admission_failure_rejects_even_a_supplied_preflight_identity(self):
        from mta.presentation.context import PublicationUnavailable
        self.admission_reader.side_effect = PublicationUnavailable('changed selection')
        status, body, downstream = self.call('/api/mta/RRRData', self.token)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)['error'], 'publication_binding_unavailable')
        downstream.assert_not_called()
        self.assertEqual(self.events, ['open', 'close'])

    def test_new_bootstrap_uses_current_date_and_same_snapshot(self):
        first = json.loads(self.call(binding.BOOTSTRAP)[1])
        self.token = 'b' * 64
        self.date_body = {'status': 200, 'data': [{'formatted': '20 Oct 2026', 'rawDate': '2026-10-20'}]}
        second = json.loads(self.call(binding.BOOTSTRAP)[1])
        self.assertNotEqual(first['binding'], second['binding'])
        self.assertEqual(second['date_response'], self.date_body)
        self.assertEqual(first['date_response']['data'][0]['rawDate'], '2026-10-19')

    def test_bootstrap_reuses_actual_full_and_scoped_date_envelope(self):
        from datetime import date
        for scoped, expected in ((False, date(2026, 10, 19)), (True, date(2026, 10, 20))):
            run = SimpleNamespace(business_date=expected)
            with patch('mta.presentation.views.last_run_date', self.real_date_reader), \
                    patch('mta.presentation.scoped_selection.enabled', return_value=scoped), \
                    patch('mta.presentation.scoped_selection.selected', return_value=SimpleNamespace(run=run)), \
                    patch('mta.presentation.views.selected_run', return_value=run):
                status, body, _ = self.call(binding.BOOTSTRAP)
            self.assertEqual(status, 200)
            value = json.loads(body)['date_response']
            self.assertEqual(value['data'], [{'formatted': expected.strftime('%d %b %Y'), 'rawDate': expected.isoformat()}])
            self.assertEqual(value['status'], 200)
            self.assertIsNone(value['recordCount'])

    def test_actual_full_date_core_supports_post_acquisition_without_changing_get_endpoint_method(self):
        from datetime import date
        from django.test import RequestFactory
        with patch('mta.presentation.views.last_run_date', self.real_date_reader), \
                patch('mta.presentation.views.selected_run', return_value=SimpleNamespace(business_date=date(2026,10,19))):
            response = self.call('/api/mta/GetBTRData', binding.ACQUIRE, consume=False, method='POST')[1]
            self.assertEqual(response.status_code,200)
            self.assertEqual(json.loads(response[binding.DATE_HEADER])['data'],self.date_body['data'])
            self.assertEqual(self.real_date_reader(RequestFactory().post('/api/mta/GetLastRunDate')).status_code,405)

    def test_report_date_cannot_succeed_with_old_count_binding_after_cutover(self):
        old = json.loads(self.call(binding.BOOTSTRAP)[1])['binding']
        self.assertEqual(self.call('/api/mta/GetLastRunDate', old)[0], 200)
        self.token = 'b' * 64
        status, _, downstream = self.call('/api/mta/GetLastRunDate', old)
        self.assertEqual(status, 409)
        downstream.assert_not_called()
        fresh = json.loads(self.call(binding.BOOTSTRAP)[1])['binding']
        self.assertEqual(self.call('/api/mta/GetLastRunDate', fresh)[0], 200)

    def test_actor_or_effective_scope_change_cannot_reuse_count_binding(self):
        old = json.loads(self.call(binding.BOOTSTRAP)[1])['binding']
        self.assertEqual(self.call('/api/mta/RRRDataCount', old)[0], 200)
        for gateway in ({'id': 8, 'report_scope_digest': 'c' * 64},
                        {'id': 7, 'report_scope_digest': 'd' * 64}):
            for report in ('RRRData', 'GetBTRData', 'GetPlanningDataGraph', 'GetExportDataAsync'):
                status, _, downstream = self.call('/api/mta/' + report, old, gateway=gateway)
                self.assertEqual(status, 409)
                downstream.assert_not_called()
            fresh = json.loads(self.call(binding.BOOTSTRAP, gateway=gateway)[1])['binding']
            self.assertNotEqual(old, fresh)
            self.assertEqual(self.call('/api/mta/RRRData', fresh, gateway=gateway)[0], 200)

    def test_missing_gateway_scope_fails_closed_without_reading_body_claim(self):
        from django.test import RequestFactory
        request = RequestFactory().post('/api/mta/RRRData',
            {'report_scope_digest': 'c' * 64}, content_type='application/json',
            HTTP_X_VECTORFLOW_IDENTITY=json.dumps({'id': 7, 'report_scope_digest': 'c' * 64}),
            HTTP_X_VECTORFLOW_PUBLICATION=self.token)
        request.META['vectorflow.admitted_publication'] = 'admitted'
        downstream = Mock()
        response = binding.PublicationBindingMiddleware(downstream)(request)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('_body', request.__dict__)
        downstream.assert_not_called()

    def test_bootstrap_requires_trusted_identity_and_normal_get_method(self):
        status, _, downstream = self.call(binding.BOOTSTRAP, authenticated=False)
        self.assertEqual(status, 403)
        downstream.assert_not_called()
        from django.test import RequestFactory
        request = RequestFactory().post(binding.BOOTSTRAP)
        request._publication_binding = self.token
        self.assertEqual(binding.bootstrap_view(request).status_code, 405)

    @override_settings(ROOT_URLCONF=__name__, ALLOWED_HOSTS=['testserver'])
    def test_real_django_wsgi_bootstrap_auth_and_request_scope_cleanup(self):
        from django.core.handlers.wsgi import WSGIHandler
        from django.test import RequestFactory
        from mta.presentation import admission
        from mta.presentation.request_scope import in_read_request
        application = admission.AdmittedApplication.__new__(admission.AdmittedApplication)
        application.application = WSGIHandler()
        with patch('mta.presentation.installation_metadata.publication_configured', return_value=True):
            for authenticated, expected in ((False, '403 Forbidden'), (True, '200 OK')):
                self.admission_reader.reset_mock()
                request = RequestFactory().get(binding.BOOTSTRAP,
                    **({'HTTP_X_VECTORFLOW_IDENTITY': json.dumps({'id': self.gateway['id']}),
                        'HTTP_X_VECTORFLOW_REPORT_SCOPE': self.gateway['report_scope_digest']} if authenticated else {}))
                start = Mock()
                response = application(request.environ, start)
                body = b''.join(response)
                response.close()
                self.assertEqual(start.call_args.args[0], expected, body)
                self.assertFalse(self.active)
                self.assertFalse(in_read_request())
                self.assertEqual(self.admission_reader.call_count, int(authenticated))

    @override_settings(ROOT_URLCONF=__name__, ALLOWED_HOSTS=['testserver'])
    def test_scoped_wsgi_retains_its_owned_preflight_before_report_snapshot(self):
        from django.core.handlers.wsgi import WSGIHandler
        from django.test import RequestFactory
        from mta.presentation import admission, scoped_selection
        app = admission.AdmittedApplication.__new__(admission.AdmittedApplication)
        app.application = WSGIHandler()
        def preflight():
            self.assertFalse(self.active)
            return 'scoped-admitted'
        self.admission_reader.side_effect = preflight
        for schema in ('fresh-selected-bpr-v1', scoped_selection.DBM_SCHEMA):
            with override_settings(VF_MTA_PHASE_SELECTION={'schema': schema}), \
                    patch.object(scoped_selection, 'enabled', return_value=True), \
                    patch('django.db.connection.get_autocommit', return_value=True), \
                    patch('mta.presentation.installation_metadata.publication_configured', return_value=True):
                for route in (binding.BOOTSTRAP, '/api/mta/RRRData'):
                    self.admission_reader.reset_mock()
                    request = RequestFactory().get(route,
                        HTTP_X_VECTORFLOW_IDENTITY=json.dumps({'id': self.gateway['id']}),
                        HTTP_X_VECTORFLOW_REPORT_SCOPE=self.gateway['report_scope_digest'],
                        HTTP_X_VECTORFLOW_PUBLICATION=self.token)
                    start = Mock()
                    response = app(request.environ, start)
                    body = b''.join(response); response.close()
                    self.assertEqual(start.call_args.args[0], '200 OK', body)
                    self.admission_reader.assert_called_once_with()
                    self.assertFalse(self.active)

    def test_bootstrap_metadata_reuse_ends_at_each_request(self):
        from mta.presentation.request_scope import once_per_request, in_read_request
        reader = Mock(return_value='metadata')
        cached = once_per_request(reader)
        def downstream(request):
            self.assertTrue(in_read_request())
            self.assertEqual(cached(), cached())
            return binding.bootstrap_view(request)
        for _ in range(2):
            self.assertEqual(self.call(binding.BOOTSTRAP, application=downstream)[0], 200)
            self.assertFalse(in_read_request())
        self.assertEqual(reader.call_count, 2)

    def test_lazy_export_scope_and_snapshot_survive_until_exhaustion(self):
        from django.http import StreamingHttpResponse
        from mta.presentation.request_scope import in_read_request
        def export(request):
            self.assertTrue(self.active)
            self.assertTrue(in_read_request())
            def chunks():
                self.assertTrue(self.active)
                self.assertTrue(in_read_request())
                yield b'header\n'
                self.assertTrue(self.active)
                yield b'row\n'
            return StreamingHttpResponse(chunks(), content_type='text/csv')
        status, response, _ = self.call('/api/mta/GetExportDataAsync', self.token, export, consume=False)
        self.assertEqual(status, 200)
        self.assertTrue(self.active)
        self.assertEqual(response[binding.HEADER], self.token)
        self.assertEqual(b''.join(response.streaming_content), b'header\nrow\n')
        response.close()
        self.assertFalse(self.active)
        self.assertFalse(in_read_request())
        self.assertEqual(self.events, ['open', 'close'])

    def test_btr_export_disconnect_closes_rows_before_the_pinned_transaction(self):
        from django.http import StreamingHttpResponse
        from mta.presentation.btr_sql import export_chunks
        events = []
        def rows():
            try:
                for value in (1,2):
                    events.append(('read',self.active))
                    yield {'x':value}
            finally:
                events.append(('cursor closed',self.active))
        for consumed in (0,1,2):
            events.clear()
            def downstream(request):
                return StreamingHttpResponse(export_chunks(rows(), [('X','x')]))
            _, response, _ = self.call('/api/mta/GetExportDataAsync', self.token, downstream, consume=False)
            stream = iter(response.streaming_content)
            for _ in range(consumed):
                next(stream)
            response.close()
            self.assertFalse(self.active)
            self.assertEqual(events,[('read',True),('cursor closed',True)] if consumed==2 else [])

    def test_disconnect_before_first_chunk_and_iterator_error_close_once(self):
        from django.http import StreamingHttpResponse
        for fail in (False, True):
            def application(request):
                def chunks():
                    yield b'first'
                    raise RuntimeError('export interrupted')
                return StreamingHttpResponse(chunks())
            _, response, _ = self.call('/api/mta/GetExportDataAsync', self.token, application, consume=False)
            if fail:
                iterator = iter(response.streaming_content)
                self.assertEqual(next(iterator), b'first')
                with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                    next(iterator)
            response.close()
            self.assertFalse(self.active)
            response.close()
        self.assertEqual(self.events, ['open', 'close', 'open', 'close'])

    def test_primed_csv_export_closes_cursor_before_the_snapshot(self):
        from mta.presentation.rrr_export import csv_response
        for consume_header in (False, True):
            events = []

            def rows():
                try:
                    yield {'x': 1}
                    yield {'x': 2}
                finally:
                    events.append(self.active)

            def downstream(request):
                from mta.presentation.bpr_prepared import _primed_export
                return csv_response(_primed_export(rows()), lambda: [('X', 'x')])

            _, response, _ = self.call('/api/mta/GetExportDataAsync', self.token, downstream, consume=False)
            if consume_header:
                self.assertEqual(next(iter(response.streaming_content)), b'X\r\n')
            response.close()
            response.close()
            self.assertEqual(events, [True])
            self.assertFalse(self.active)

    @override_settings(VF_MTA_NATIVE_PUBLICATION=False)
    def test_legacy_bootstrap_explicit_and_existing_reads_unchanged(self):
        _, body, _ = self.call(binding.BOOTSTRAP)
        self.assertEqual(json.loads(body), {'mode': 'legacy', 'binding': None})
        self.assertEqual(self.call('/api/mta/RRRData')[0], 200)
        self.assertEqual(self.events, [])

    @override_settings(VF_MTA_NATIVE_PUBLICATION=False)
    def test_non_native_reports_preserve_unauthenticated_method_precedence(self):
        from django.test import RequestFactory
        from django.http import JsonResponse
        request = RequestFactory().delete('/api/mta/RRRData')
        original = JsonResponse({'error': 'method_not_allowed'}, status=405)
        downstream = Mock(return_value=original)
        with patch('mta.presentation.views.identity', side_effect=AssertionError('New auth must not run')):
            response = binding.PublicationBindingMiddleware(downstream)(request)
        self.assertIs(response, original)
        downstream.assert_called_once_with(request)
        self.assertEqual(self.events, [])
        status, _, downstream = self.call(binding.BOOTSTRAP, authenticated=False)
        self.assertEqual(status, 403)
        downstream.assert_not_called()


class SnapshotContractTests(unittest.TestCase):
    def test_real_snapshot_uses_postgres_repeatable_read_read_only(self):
        with patch.object(binding, 'connection') as connection, patch.object(binding.transaction, 'atomic') as atomic:
            connection.vendor = 'postgresql'
            connection.in_atomic_block = False
            connection.needs_rollback = False
            connection.connection.closed = False
            with binding.snapshot():
                connection.in_atomic_block = True
                self.assertIs(binding.snapshot_identity()[0], connection.connection)
                with patch.object(connection, 'connection'):
                    self.assertIsNone(binding.snapshot_identity())
                atomic.return_value.__enter__.assert_called_once()
                connection.cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
                    'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            atomic.return_value.__exit__.assert_called_once()
            self.assertIsNone(binding.snapshot_identity())

    def test_nested_or_non_postgres_snapshot_fails_closed(self):
        with patch.object(binding, 'connection') as connection:
            for vendor, nested in (('sqlite', False), ('postgresql', True)):
                connection.vendor, connection.in_atomic_block = vendor, nested
                with self.assertRaisesRegex(ValueError, 'snapshot_unavailable'):
                    with binding.snapshot():
                        self.fail('unsupported snapshot entered')


class BindingIdentityTests(unittest.TestCase):
    def test_frontend_and_backend_share_the_same_finite_report_transport_boundary(self):
        from pathlib import Path
        import re
        source = (Path(__file__).resolve().parents[1] / 'frontend/src/config/mta-publication-binding.ts').read_text()
        names = re.search(r'const reportNames = new Set\(`([^`]+)`', source).group(1).split()
        self.assertEqual(set(names), binding.REPORTS)

    def test_action_and_remark_revisions_change_identity_under_same_publication(self):
        from mta.runtime.models import RunCommand
        from mta.runtime.ancillary_models import RemarkOwner
        from mta.runtime.logistics_models import LogisticsHistoryOwner, TransitLiveGeneration
        from mta.runtime.daily_request_models import DailyRequestOwner
        with ExitStack() as stack:
            stack.enter_context(patch('mta.presentation.scoped_selection.enabled', return_value=False))
            stack.enter_context(patch('mta.presentation.context.configured_run', return_value=SimpleNamespace(pk='run')))
            managers = [stack.enter_context(patch.object(model, 'objects')) for model in (
                RunCommand, RemarkOwner, LogisticsHistoryOwner, TransitLiveGeneration, DailyRequestOwner)]
            terminal = managers[0].filter.return_value.order_by.return_value.values.return_value
            terminal.first.return_value = None
            managers[1].order_by.return_value.values.return_value = []
            managers[2].order_by.return_value.values.return_value = []
            managers[3].filter.return_value.values.return_value = []
            managers[4].order_by.return_value.values.return_value = []
            before = binding.identity('admitted')
            terminal.first.return_value = dict(pk=1, digest='action', after_digest='state', state_sealed=True)
            action = binding.identity('admitted')
            self.assertNotEqual(before, action)
            managers[1].order_by.return_value.values.return_value = [dict(
                family='BPR', provenance_digest='source', next_ordinal=1)]
            self.assertNotEqual(action, binding.identity('admitted'))
            self.assertEqual(binding.identity('admitted'), binding.identity('admitted'))
