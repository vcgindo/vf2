"""Boundary guards; report values are proved separately against SQL/.NET."""
import unittest
from mta.presentation.buffer_trends_sql import GraphFilters, read_graph
from mta.presentation.context import PublicationUnavailable


class BufferTrendsBoundaryTest(unittest.TestCase):
    def test_custom_only_preserves_deployed_call_gate(self):
        payload = {'filters': {'customAttributeFilter': {'filters': [
            dict(attributeName='skulocattr999', operator='equalto', value='x')]}}}
        self.assertEqual(GraphFilters(payload).compile(), 'TRUE')
        payload['filters']['productFilter'] = {'filters': []}
        with self.assertRaisesRegex(PublicationUnavailable, 'missing column c999'):
            GraphFilters(payload).compile()

    def test_deployed_missing_age_alias_is_not_repaired(self):
        with self.assertRaisesRegex(PublicationUnavailable, 'no btd alias'):
            GraphFilters({'filters': {'colorFilter': {'filters': [dict(
                attributeName='red', type='colorage', operator='greaterthan', value='1')]}}}).compile()

    def test_horizon_rejects_columns_outside_persisted_history(self):
        for days in (0, -1, 91):
            with self.assertRaisesRegex(ValueError, 'outside retained columns'):
                read_graph(None, {'days': days})

    def test_filter_value_remains_a_bound_parameter(self):
        marker = "337'; DROP TABLE anything;--"
        query = GraphFilters({'filters': {'productFilter': {'filters': [
            dict(attributeName='sku', value=marker)]}}})
        sql = query.compile()
        self.assertNotIn(marker, sql)
        self.assertEqual(query.params, [marker])
