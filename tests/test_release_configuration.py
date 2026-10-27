import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from release.configuration import database_options, integer, load_secret, public_url, secret, security, email_settings, auth_site_key_cache


class ReleaseConfigurationTests(unittest.TestCase):
    def test_site_identity_cache_requires_both_explicit_owner_and_location(self):
        self.assertIsNone(auth_site_key_cache())
        for values in ({'VF_AUTH_SITE_CACHE_URL': 'redis://redis:6379/0'},
                       {'VF_AUTH_SITE_KEY_NAMESPACE': 'owned-auth'},
                       {'VF_AUTH_SITE_CACHE_URL': 'https://redis/0', 'VF_AUTH_SITE_KEY_NAMESPACE': 'owned-auth'},
                       {'VF_AUTH_SITE_CACHE_URL': 'redis://redis/0', 'VF_AUTH_SITE_KEY_NAMESPACE': '*'},
                       {'VF_AUTH_SITE_CACHE_URL': 'redis://redis', 'VF_AUTH_SITE_KEY_NAMESPACE': 'owned-auth'},
                       {'VF_AUTH_SITE_CACHE_URL': 'redis://redis:99999/0', 'VF_AUTH_SITE_KEY_NAMESPACE': 'owned-auth'}):
            with self.subTest(values=values), patch.dict(os.environ, values, clear=True):
                with self.assertRaises(ValueError):
                    auth_site_key_cache()

    def test_site_identity_configuration_is_separate_and_accepts_secret_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cache-url'
            path.write_text('rediss://redis.example.invalid:6379/0\n')
            os.environ.update(VF_AUTH_SITE_CACHE_URL_FILE=str(path), VF_AUTH_SITE_KEY_NAMESPACE='owned-auth:one')
            configured = auth_site_key_cache()
        self.assertEqual(configured['BACKEND'], 'django.core.cache.backends.redis.RedisCache')
        self.assertEqual(configured['LOCATION'], 'rediss://redis.example.invalid:6379/0')
        self.assertEqual(configured['KEY_PREFIX'], 'vectorflow:site-key:owned-auth:one')
        self.assertEqual(configured['OPTIONS'], {'socket_connect_timeout': 5, 'socket_timeout': 5})

    def test_optional_smtp_and_explicit_starttls_or_ssl(self):
        self.assertEqual(email_settings()['EMAIL_HOST'], '')
        os.environ.update(EMAIL_HOST='smtp.example.invalid', EMAIL_FROM='sender@example.invalid',
                          EMAIL_USER='sender', EMAIL_PASS='test-only', EMAIL_PORT='587')
        config = email_settings()
        self.assertTrue(config['EMAIL_USE_TLS'])
        self.assertFalse(config['EMAIL_USE_SSL'])
        self.assertEqual(config['EMAIL_TIMEOUT'], 15)
        self.assertEqual(config['EMAIL_HOST_PASSWORD'], 'test-only')
        os.environ.update(EMAIL_USE_TLS='false', EMAIL_USE_SSL='true', EMAIL_PORT='465')
        config = email_settings()
        self.assertFalse(config['EMAIL_USE_TLS'])
        self.assertTrue(config['EMAIL_USE_SSL'])
        self.assertEqual(config['EMAIL_PORT'], 465)

    def test_smtp_rejects_invalid_transport_incomplete_credentials_and_missing_sender(self):
        for updates in ({'EMAIL_USE_SSL':'true'}, {'EMAIL_USE_TLS':'maybe'},
                        {'EMAIL_PORT':'70000'}, {'EMAIL_TIMEOUT':'0'},
                        {'EMAIL_USER':'sender'}, {'EMAIL_HOST':'smtp.example.invalid'}):
            with self.subTest(updates=updates), patch.dict(os.environ, updates):
                with self.assertRaises(ValueError):
                    email_settings()

    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_secret_files_do_not_accept_a_conflicting_environment_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'password'
            path.write_text('non-serving-unit-test-value\n', encoding='utf-8')
            os.environ['PASSWORD_FILE'] = str(path)
            self.assertEqual(secret('PASSWORD'), 'non-serving-unit-test-value')
            os.environ['PASSWORD'] = 'other'
            with self.assertRaisesRegex(ValueError, 'not both'):
                secret('PASSWORD')

    def test_loading_secret_is_repeatable_and_missing_secrets_have_no_default(self):
        with self.assertRaisesRegex(ValueError, 'required'):
            secret('PASSWORD')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'password'
            path.write_text('non-serving-unit-test-value', encoding='utf-8')
            os.environ['PASSWORD_FILE'] = str(path)
            load_secret('PASSWORD')
            load_secret('PASSWORD')
            self.assertEqual(os.environ['PASSWORD'], 'non-serving-unit-test-value')

    def test_external_cleartext_origins_and_urls_containing_credentials_or_paths_are_rejected(self):
        for value in ['http://example.com', 'https://user:password@example.com',
                      'https://example.com/application', 'https://example.com?token=value']:
            with self.subTest(value=value):
                os.environ['VF_PUBLIC_URL'] = value
                with self.assertRaises(ValueError):
                    public_url()

    def test_https_origin_drives_host_csrf_cookie_and_proxy_settings(self):
        os.environ['VF_PUBLIC_URL'] = 'https://vectorflow.example:8443'
        result = {}
        security(result)
        self.assertEqual(result['ALLOWED_HOSTS'], ['vectorflow.example'])
        self.assertEqual(result['CSRF_TRUSTED_ORIGINS'], ['https://vectorflow.example:8443'])
        self.assertTrue(result['SESSION_COOKIE_SECURE'])
        self.assertFalse(result['CORS_ALLOW_ALL_ORIGINS'])
        self.assertEqual(result['SECURE_PROXY_SSL_HEADER'], ('HTTP_X_FORWARDED_PROTO', 'https'))

    def test_loopback_http_is_explicit_and_wildcard_hosts_are_rejected(self):
        os.environ['VF_PUBLIC_URL'] = 'http://127.0.0.1:3006'
        result = {}
        security(result)
        self.assertFalse(result['SESSION_COOKIE_SECURE'])
        self.assertEqual(result['SECURE_HSTS_SECONDS'], 0)
        os.environ['VF_ALLOWED_HOSTS'] = '*'
        with self.assertRaises(ValueError):
            security({})

    def test_database_tls_options_retain_schema_and_validate_timeout(self):
        os.environ.update(DB_SSLMODE='verify-full', DB_SSLROOTCERT='/run/certs/ca.crt', DB_CONNECT_TIMEOUT='12')
        self.assertEqual(database_options({'options': '-c search_path=mta,public'}),
            {'options': '-c search_path=mta,public', 'sslmode': 'verify-full',
             'sslrootcert': '/run/certs/ca.crt', 'connect_timeout': 12})
        os.environ['DB_SSLMODE'] = 'unknown'
        with self.assertRaises(ValueError):
            database_options()
        os.environ['DB_CONNECT_TIMEOUT'] = '0'
        with self.assertRaises(ValueError):
            integer('DB_CONNECT_TIMEOUT', 5)
