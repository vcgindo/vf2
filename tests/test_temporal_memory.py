"""Memory-boundary equivalence; these values are not replacement parity inputs."""
import ast
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import inspect
import json
import unittest
from unittest.mock import patch

from mta.temporal.chain import calculate_day, _calculate_day_native, json_value


class TemporalMemoryTest(unittest.TestCase):
    def test_production_avoids_normalization_and_diagnostic_copy(self):
        from mta.evidence import evidence_mode, snapshot, final_stage, validating
        row={'quantity':Decimal('1.2500')}
        with evidence_mode('production'):
            with patch('mta.temporal.chain._calculate_day_native', return_value={'ClosingState':[row]}), \
                 patch('mta.temporal.chain.json_value',side_effect=AssertionError('diagnostic normalization')), \
                 patch('mta.evidence.deepcopy',side_effect=AssertionError('diagnostic copy')):
                result=calculate_day(None,None,None,None,None,None,None)
                self.assertIs(result['ClosingState'][0],row)
                self.assertIs(snapshot(row),row)
                self.assertEqual(final_stage(iter([1,2,3])),[3])
        self.assertTrue(validating())
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with evidence_mode('production'):raise RuntimeError('injected')
        self.assertTrue(validating())

    def test_checkpoint_conversion_matches_whole_graph_without_mutating_shared_rows(self):
        shared = {'quantity': Decimal('12.3400'), 'null': None, 'flag': True,
                  'day': date(2026, 6, 17), 'at': datetime(2026, 6, 17, tzinfo=timezone.utc),
                  'tuple': (1, '1', False, -0.0), 'text': 'Product é ₹'}
        original = deepcopy(shared)
        raw = {'ClosingState': [shared, shared], 'DBMStages': [shared],
               'Empty': [], 'MajorBoundaries': [{'state': shared}], 'Lineage': []}
        expected = json_value(raw)
        arguments = ({'prior': True}, '2026-06-16', {'day': True}, {'profile': True},
                     'same-run', object(), {'same-exception': True})
        with patch('mta.temporal.chain._calculate_day_native', return_value=raw) as calculate:
            actual = calculate_day(*arguments)
        calculate.assert_called_once_with(*arguments)
        self.assertEqual(actual, expected)
        self.assertEqual(json.dumps(actual, separators=(',', ':')),
                         json.dumps(expected, separators=(',', ':')))
        self.assertEqual(shared, original)
        self.assertIsNot(actual['ClosingState'][0], actual['ClosingState'][1])
        self.assertIsNot(actual['ClosingState'][0], actual['DBMStages'][0])
        self.assertEqual(list(actual), list(expected))


if __name__ == '__main__':
    unittest.main()
