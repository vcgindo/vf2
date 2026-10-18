"""Reset API contracts on an owned PostgreSQL with rollback-only fixture accounts.

Run with VF_RESET_CONTRACT_TEST=1 inside the auth environment. Local SMTP only,
no external mail, real-user reset, persisted fixture user or production schema change.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import contextmanager
from email import message_from_bytes
import os
import smtplib
import socketserver
import threading
import unittest
from unittest.mock import patch
import uuid


class SMTPHandler(socketserver.StreamRequestHandler):
    def reply(self, text):
        self.wfile.write(text.encode('ascii') + b'\r\n')
        self.wfile.flush()

    def handle(self):
        self.request.settimeout(5)
        self.reply('220 localhost test SMTP')
        while line := self.rfile.readline():
            command = line.split(None, 1)[0].upper()
            if command in (b'EHLO', b'HELO', b'MAIL', b'RSET', b'NOOP'):
                self.reply('250 OK')
            elif command == b'RCPT':
                self.reply('550 test rejection' if self.server.reject else '250 OK')
            elif command == b'DATA':
                self.reply('354 send message')
                body = []
                while (line := self.rfile.readline()) not in (b'.\r\n', b''):
                    body.append(line[1:] if line.startswith(b'..') else line)
                self.server.messages.append(b''.join(body))
                self.reply('250 accepted')
            elif command == b'QUIT':
                self.reply('221 bye')
                return
            else:
                self.reply('502 unsupported')


@contextmanager
def local_smtp(reject=False):
    with socketserver.ThreadingTCPServer(('127.0.0.1', 0), SMTPHandler) as server:
        server.reject, server.messages = reject, []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=5)


@unittest.skipUnless(os.environ.get('VF_RESET_CONTRACT_TEST') == '1', 'Requires owned PostgreSQL auth environment')
class PasswordResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.auth_settings')
        import django
        django.setup()

    def setUp(self):
        from django.db import transaction
        from api.models import User
        from django.test import override_settings
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        self.addCleanup(self.rollback)
        suffix = uuid.uuid4().hex
        self.admin = User.all_objects.create_superuser(
            email='admin-' + suffix + '@example.invalid', name='ResetAdmin', tc=True,
            password='FixtureOnly!19')
        self.target = User.all_objects.create_user(
            email='target-' + suffix + '@example.invalid', name='ResetTarget', tc=True,
            password='FixtureOnly!19')
        self.before = self.target.password
        self.settings = override_settings(EMAIL_BACKEND='api.common.mail_config.CustomEmailBackend',
            EMAIL_HOST='127.0.0.1', EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='',
            EMAIL_USE_TLS=False, EMAIL_USE_SSL=False, EMAIL_TIMEOUT=2,
            DEFAULT_FROM_EMAIL='sender@example.invalid')
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.environment = patch.dict(os.environ, EMAIL_FROM='sender@example.invalid', EMAIL_NAME='VectorFLOW test')
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def rollback(self):
        from django.db import transaction
        transaction.set_rollback(True)
        self.atomic.__exit__(None, None, None)

    def request(self, actor=None, target=None):
        from api.view.auth import UserResetPWDView
        from rest_framework.test import APIRequestFactory, force_authenticate
        request = APIRequestFactory().post('/api/user/reset-pwd/' + str(self.target.pk), {}, format='json')
        force_authenticate(request, user=actor or self.admin)
        response = UserResetPWDView.as_view()(request, uid=target or self.target.pk)
        response.render()  # Catches the original tuple/Response/ContentNotRendered failure.
        return response

    def assert_unchanged(self):
        self.target.refresh_from_db()
        self.assertEqual(self.target.password, self.before)

    def test_missing_smtp_is_useful_400_without_generating_or_changing_password(self):
        from django.test import override_settings
        from api.models import User
        with override_settings(EMAIL_HOST=''), patch.object(User.all_objects, 'make_random_password') as generate:
            response = self.request()
        self.assertEqual(response.status_code, 400)
        self.assertIn('SMTP', str(response.data))
        generate.assert_not_called()
        self.assert_unchanged()

    def test_rejected_email_returns_renderable_400_and_preserves_password(self):
        from django.test import override_settings
        with local_smtp(reject=True) as server, override_settings(EMAIL_PORT=server.server_address[1]):
            response = self.request()
            self.assertEqual(server.messages, [])
        self.assertEqual(response.status_code, 400)
        self.assert_unchanged()

    def test_smtp_acceptance_sends_real_mime_and_updates_only_fixture_password(self):
        from django.test import override_settings
        from api.models import User
        with local_smtp() as server, override_settings(EMAIL_PORT=server.server_address[1]), \
                patch.object(User.all_objects, 'make_random_password', return_value='ResetFixture!29'):
            response = self.request()
            self.assertEqual(len(server.messages), 1)
            message = message_from_bytes(server.messages[0])
            self.assertEqual(message['To'], self.target.email)
            self.assertIn('sender@example.invalid', message['From'])
            self.assertEqual(message.get_content_type(), 'multipart/alternative')
        self.assertEqual(response.status_code, 200)
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password('ResetFixture!29'))
        self.assertEqual(self.target.role_id.count(), 0)

    def test_timeout_or_authentication_failure_returns_400_and_preserves_password(self):
        for error in (TimeoutError('test timeout'), smtplib.SMTPAuthenticationError(535, b'test denied')):
            with self.subTest(error=type(error).__name__), \
                    patch('api.common.mail_config.CustomEmailBackend.open', side_effect=error):
                self.assertEqual(self.request().status_code, 400)
                self.assert_unchanged()

    def test_zero_accepted_messages_is_not_success(self):
        with patch('api.services.Util.send_html_email', return_value=0):
            self.assertEqual(self.request().status_code, 400)
        self.assert_unchanged()

    def test_non_admin_and_missing_user_remain_denied(self):
        self.assertEqual(self.request(actor=self.target).status_code, 403)
        self.assertEqual(self.request(target=2147483647).status_code, 400)
        self.assert_unchanged()

    def test_transport_uses_django_starttls_and_implicit_ssl(self):
        from api.common.mail_config import CustomEmailBackend
        from django.test import override_settings
        for tls, ssl, transport in ((True, False, 'SMTP'), (False, True, 'SMTP_SSL')):
            with self.subTest(transport=transport), override_settings(EMAIL_USE_TLS=tls, EMAIL_USE_SSL=ssl), \
                    patch('django.core.mail.backends.smtp.smtplib.' + transport) as connect:
                with CustomEmailBackend(host='smtp.example.invalid', port=587 if tls else 465,
                                        username='test-user', password='test-only', timeout=2):
                    pass
                connect.assert_called_once()
                connect.return_value.login.assert_called_once_with('test-user', 'test-only')
                self.assertEqual(connect.return_value.starttls.call_count, int(tls))


if __name__ == '__main__':
    unittest.main(verbosity=2)
