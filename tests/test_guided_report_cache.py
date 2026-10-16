"""Focused contracts of the restored bounded, process-local report cache."""
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from mta.presentation.report_cache import ReportReadCache


class ReportCacheTests(unittest.TestCase):
    def test_concurrent_identical_reads_compute_once(self):
        cache = ReportReadCache()
        start = threading.Barrier(3)
        entered, release = threading.Event(), threading.Event()
        calls = []

        def compute():
            calls.append(1)
            entered.set()
            if not release.wait(3):
                raise AssertionError('test reader did not release')
            return b'complete response'

        def request():
            start.wait(3)
            return cache.get_or_compute('same identity and payload', compute)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(request) for _ in range(2)]
            start.wait(3)
            self.assertTrue(entered.wait(3))
            release.set()
            self.assertEqual([result.result(3) for result in results],
                             [b'complete response'] * 2)
        self.assertEqual(calls, [1])

    def test_expiration_and_storage_bounds_do_not_reuse_evicted_data(self):
        cache = ReportReadCache(max_bytes=5, max_entries=2, ttl=3)
        with patch('mta.presentation.report_cache.time.monotonic', return_value=1):
            self.assertEqual(cache.get_or_compute('a', lambda: b'aaa'), b'aaa')
            self.assertEqual(cache.get_or_compute('b', lambda: b'bbb'), b'bbb')
            self.assertEqual(cache.get_or_compute('a', lambda: b'new'), b'new')
        with patch('mta.presentation.report_cache.time.monotonic', return_value=5):
            self.assertEqual(cache.get_or_compute('a', lambda: b'fresh'), b'fresh')
        with patch('mta.presentation.report_cache.time.monotonic', return_value=6):
            self.assertEqual(cache.get_or_compute('large', lambda: b'oversized'), b'oversized')
            self.assertEqual(cache.get_or_compute('large', lambda: b'other'), b'other')

    def test_failure_and_uncacheable_response_allow_a_later_read(self):
        cache = ReportReadCache()
        with self.assertRaisesRegex(ValueError, 'denied'):
            cache.get_or_compute('key', lambda: (_ for _ in ()).throw(ValueError('denied')))
        self.assertIsNone(cache.get_or_compute('key', lambda: None))
        self.assertEqual(cache.get_or_compute('key', lambda: b'allowed'), b'allowed')


if __name__ == '__main__':
    unittest.main()
