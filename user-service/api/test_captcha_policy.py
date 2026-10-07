import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch
from rest_framework.test import APIRequestFactory
from api.view import captcha_policy as policy


class CaptchaPolicyTests(TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'VF_LOCAL_FIXTURE_CAPTCHA_EXEMPTION': '1',
            'VF_LOCAL_INSTANCE': policy.INSTANCE, 'BASE_CLIENT_URL': policy.ORIGIN})
        self.env.start(); self.addCleanup(self.env.stop)
        self.db = patch.object(policy, 'connection'); self.connection = self.db.start()
        self.addCleanup(self.db.stop)
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.cursor.fetchone.return_value = ('daily_3006', 'identity')
        self.users = patch.object(policy, 'User'); self.user = self.users.start()
        self.addCleanup(self.users.stop)
        self.user.all_objects.filter.return_value.exists.return_value = True

    def request(self, email='stage2.broad@vectorflow.local', origin=policy.ORIGIN, host='localhost'):
        return SimpleNamespace(data={'email': email}, headers={'Origin': origin},
                               get_host=lambda: host)

    def test_only_exact_active_fixture_pairs(self):
        for email, pk in policy.FIXTURES.items():
            self.assertTrue(policy.exempt(self.request(email)))
            self.user.all_objects.filter.assert_called_with(pk=pk, email=email,
                is_active=True, is_admin=False, is_deleted=False)
        self.user.all_objects.filter.return_value.exists.return_value = False
        self.assertFalse(policy.exempt(self.request()))

    def test_configuration_and_request_denials(self):
        for key in ('VF_LOCAL_FIXTURE_CAPTCHA_EXEMPTION', 'VF_LOCAL_INSTANCE', 'BASE_CLIENT_URL'):
            for value in ('', '0', 'wrong'):
                with patch.dict(os.environ, {key: value}):
                    self.assertFalse(policy.exempt(self.request()))
        for origin in ('', None, 'http://localhost:3005', 'http://evil.test:3006'):
            self.assertFalse(policy.exempt(self.request(origin=origin)))
        for host in ('localhost:3005', 'localhost:3006', 'evil.test', ''):
            self.assertFalse(policy.exempt(self.request(host=host)))
        for email in (None, [], {}, 'other@example.test', 'STAGE2.BROAD@vectorflow.local'):
            self.assertFalse(policy.exempt(self.request(email)))

    def test_database_schema_and_dependency_denials(self):
        for identity in (('preview', 'identity'), ('daily_3006', 'public'), None):
            self.cursor.fetchone.return_value = identity
            self.assertFalse(policy.exempt(self.request()))
        self.connection.cursor.side_effect = RuntimeError('offline')
        self.assertFalse(policy.exempt(self.request()))

    def test_generic_uncached_response_even_for_malformed_body(self):
        factory = APIRequestFactory()
        for data, format in (({'email': 'other'}, 'json'), ([], 'json')):
            request = factory.post('/api/user/captcha-policy/', data, format=format,
                HTTP_HOST='localhost', HTTP_ORIGIN=policy.ORIGIN)
            response = policy.FixtureCaptchaPolicyView.as_view()(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {'exempt': False})
            self.assertEqual(response['Cache-Control'], 'no-store, private')
