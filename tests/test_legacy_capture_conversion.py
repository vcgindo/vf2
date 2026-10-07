import json
import math
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import IntEnum

from parity.adapters.legacy.temporal_day import _plain
from parity.adapters.legacy.temporal_support import _json


class CaptureConversionTests(unittest.TestCase):
    def test_matches_original_wire_types_keys_order_and_duplicates(self):
        class Code(IntEnum):
            FIRST = 1
        shared = {'amount': Decimal('1.2300'), 'day': date(2026, 6, 6),
                  'at': datetime(2026, 6, 6, 1, 2, 3, 400, tzinfo=timezone.utc),
                  'null': None, 'flag': False, 'tuple': (1, 'x', True)}
        value = {'rows': [shared, shared], 'keys': {None: 1, 'null': 2, 3: 'n',
                 False: 'b', 1.5: 'f', Code.FIRST: 'e'}, 'unicode': '\u00e9\u0000\ud800'}
        expected = json.loads(json.dumps(value, default=_json))
        actual = _plain(value)
        self.assertEqual(actual, expected)
        self.assertEqual(list(actual['keys']), list(expected['keys']))
        self.assertIsNot(actual['rows'][0], actual['rows'][1])
        self.assertIsInstance(actual['rows'][0]['amount'], str)
        self.assertIsInstance(actual['rows'][0]['tuple'], list)

    def test_nonfinite_numbers_and_unsupported_values(self):
        result = _plain([float('nan'), float('inf'), float('-inf')])
        self.assertTrue(math.isnan(result[0]))
        self.assertEqual(result[1:], [float('inf'), float('-inf')])
        for value in ({('x',): 1}, {'x': object()}, {1, 2}):
            with self.assertRaises(TypeError):_plain(value)
        cycle = []; cycle.append(cycle)
        with self.assertRaises(ValueError):_plain(cycle)

    def test_no_encoded_whole_result(self):
        from unittest.mock import patch
        with patch('parity.adapters.legacy.temporal_day.json.dumps', side_effect=AssertionError):
            self.assertEqual(_plain({'rows': [{'value': Decimal('2.0')}] * 1000}),
                             {'rows': [{'value': '2.0'}] * 1000})
