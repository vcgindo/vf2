from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import unittest

from mta.serialization import digest, storage


class CanonicalDigestTest(unittest.TestCase):
    def test_streamed_digest_preserves_existing_bytes(self):
        shared = {'quantity': Decimal('12.3400'), 'nullable': None, 'flag': True}
        values = [None, {}, [], (1, 'x'), -0.0, 1e-12,
                  {'z': [shared, shared], 'a': (date(2026, 6, 6),
                   datetime(2026, 6, 6, 12, tzinfo=timezone.utc)),
                   'text': 'Product \u00e9 \u20b9 \U0001f600 " \\ \n'}]
        for value in values:
            old = hashlib.sha256(json.dumps(storage(value), sort_keys=True,
                separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            self.assertEqual(digest(value), old)

    def test_nonfinite_and_unsupported_values_still_fail_closed(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError):
                digest({'value': value})
        with self.assertRaises(TypeError):
            digest({'value': object()})
