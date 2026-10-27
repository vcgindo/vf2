"""Focused daily-identity arbitration; native Redis/refresh proof is separate."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import importlib.util
from pathlib import Path
import threading
from unittest.mock import patch

from django.core.cache import caches
from django.test import SimpleTestCase, override_settings

spec = importlib.util.spec_from_file_location('tested_site_keys', Path(__file__).resolve().parents[1] /
    'user-service/api_gateway/site_keys.py')
site_keys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_keys)


@override_settings(CACHES={
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'unit-permissions'},
    'site_identity': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'unit-site'},
}, AUTH_SITE_KEY_CACHE_ALIAS='site_identity')
class SiteKeyTests(SimpleTestCase):
    def setUp(self):
        caches['default'].clear()
        caches['site_identity'].clear()

    def test_same_day_reuses_site_owner_without_touching_permission_cache(self):
        caches['default'].set('site_key_2026-10-27', 'unrelated-permission-cache-value')
        with patch.object(site_keys, 'datetime') as clock:
            clock.utcnow.return_value = datetime(2026, 10, 27, 12)
            first = site_keys.get_site_key()
            self.assertEqual(site_keys.get_site_key(), first)
        self.assertEqual(len(first), 32)
        self.assertNotEqual(first, 'unrelated-permission-cache-value')
        self.assertEqual(caches['default'].get('site_key_2026-10-27'), 'unrelated-permission-cache-value')

    def test_concurrent_first_read_returns_the_atomic_winner(self):
        barrier = threading.Barrier(2)
        def generate(_):
            identity = threading.get_ident()
            barrier.wait(timeout=5)
            return str(identity)
        with patch.object(site_keys.secrets, 'token_hex', side_effect=generate), ThreadPoolExecutor(2) as pool:
            jobs = [pool.submit(site_keys.get_site_key) for _ in range(2)]
            values = [job.result(timeout=10) for job in jobs]
        self.assertEqual(values[0], values[1])

    def test_utc_day_rollover_still_changes_identity(self):
        with patch.object(site_keys, 'datetime') as clock:
            clock.utcnow.return_value = datetime(2026, 10, 27, 23, 59, 59)
            first = site_keys.get_site_key()
            clock.utcnow.return_value = datetime(2026, 10, 28)
            second = site_keys.get_site_key()
        self.assertNotEqual(first, second)
        self.assertEqual(caches['site_identity'].get('site_key_2026-10-27'), first)

    def test_owner_failure_does_not_choose_a_local_fallback(self):
        with patch.object(caches['site_identity'], 'get_or_set', side_effect=ConnectionError('unit outage')), \
                patch.object(site_keys.secrets, 'token_hex') as random_key:
            with self.assertRaises(ConnectionError):
                site_keys.get_site_key()
            random_key.assert_not_called()

    def test_legacy_unconfigured_alias_remains_default(self):
        with override_settings(AUTH_SITE_KEY_CACHE_ALIAS='default'), patch.object(site_keys, 'datetime') as clock:
            clock.utcnow.return_value = datetime(2026, 10, 27)
            first = site_keys.get_site_key()
        self.assertEqual(caches['default'].get('site_key_2026-10-27'), first)
        self.assertIsNone(caches['site_identity'].get('site_key_2026-10-27'))
