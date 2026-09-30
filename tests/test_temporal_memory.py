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
    def test_calculation_ast_is_unchanged_except_native_name_and_final_return(self):
        tree = ast.parse(inspect.getsource(_calculate_day_native))
        function = tree.body[0]
        self.assertEqual(function.name, '_calculate_day_native')
        self.assertEqual(ast.dump(function.body[-1]), "Return(value=Name(id='result', ctx=Load()))")
        function.name = 'calculate_day'
        function.body[-1] = ast.Return(value=ast.Call(
            func=ast.Name(id='json_value', ctx=ast.Load()),
            args=[ast.Name(id='result', ctx=ast.Load())], keywords=[]))
        self.assertEqual(hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest(),
            '72d7c16d6327a6eaead35cbf0e5bf58ed776d2865423edde592a771fc9feb1f9')

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
