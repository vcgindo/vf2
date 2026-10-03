"""Guided source ownership regressions; SQL comparison remains a separate gate."""
import os
import unittest
import json
from unittest.mock import patch
from datetime import date
from types import SimpleNamespace

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-test-only-not-a-serving-secret')
import django
django.setup()

from mta.presentation.context import PublicationUnavailable
from mta.presentation.insight_filters import InsightPredicate
from mta.presentation.insights import availability_ageing
from django.test import RequestFactory


def group(attribute, value, operator='equalto'):
    return {'filters': [dict(attributeName=attribute, value=value, operator=operator)]}


class InsightFilterTests(unittest.TestCase):
    def test_excess_date_overflow_uses_processor_error_envelope(self):
        from mta.presentation.views import insight_data
        context = SimpleNamespace(state={'LocationAttributeData': []}, business_date=date(2026, 6, 17))
        request = RequestFactory().post('/api/mta/ExcessInventoryValue',
            json.dumps({'horison': 2147483647, 'filters': {}}), content_type='application/json')
        with patch('mta.presentation.views.identity', return_value={'id': 'unit-test'}), \
             patch('mta.presentation.insight_read.insight_context', return_value=context):
            response = insight_data(request, kind='excess-value')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.content)['status'], 500)
        self.assertIsNone(json.loads(response.content)['data'])

    def test_invalid_sql_http_envelope_is_distinct_from_missing_publication(self):
        from mta.presentation.views import endpoint
        from mta.presentation.insight_filters import InsightFilterUnavailable
        request = RequestFactory().post('/api/mta/AvailabilityTrend', '{}', content_type='application/json')
        for error, expected in ((InsightFilterUnavailable('invalid SQL'), 500),
                                (PublicationUnavailable('missing image'), 503)):
            @endpoint('POST')
            def failed(request, payload):
                raise error
            with patch('mta.presentation.views.identity', return_value={'id': 'unit-test'}):
                response = failed(request)
            self.assertEqual(response.status_code, expected)
            if expected == 500:
                self.assertEqual(json.loads(response.content), dict(recordCount=None, data=None,
                    status=500, msg=None, errorCount=None, error=None, conflictErrorCount=None,
                    conflictError=None))

    def predicate(self, filters, kind='availability-trend', locations=()):
        payload = {'filters': filters} if kind.startswith('availability-') or kind == 'chronic-grid' else filters
        return InsightPredicate(payload, locations, kind=kind)

    def test_custom_only_does_not_activate_commons(self):
        row = {'_sku': {'c1': 'kept'}}
        filters = {'customAttributeFilter': group('skuattr1', 'excluded')}
        self.assertEqual(self.predicate(filters).select([row]), [row])
        filters['productFilter'] = {'filters': []}
        self.assertEqual(self.predicate(filters).select([row]), [])

    def test_hierarchy_or_within_attribute_and_between_attributes(self):
        filters = {'productFilter': {'filters': [
            *group('p2', 'First')['filters'], *group('p2', 'Second')['filters'],
            *group('p3', 'Leaf')['filters']]}}
        rows = [{'_sku': {'SL2': 'Second', 'SL3': 'Leaf'}},
                {'_sku': {'SL2': 'First', 'SL3': 'Other'}}]
        self.assertEqual(self.predicate(filters).select(rows), rows[:1])

    def test_norm_is_valid_in_trend_but_ambiguous_with_snapshot(self):
        filters = {'availabilityFilter': group('norm', '300', 'greaterthan')}
        row = {'_a': {'Norm': 301}, 'Norm': 0}
        self.assertEqual(self.predicate(filters).select([row]), [row])
        with self.assertRaisesRegex(PublicationUnavailable, 'ambiguous column norm'):
            self.predicate(filters, 'availability-ageing')

    def test_invalid_color_name_rejected_before_population_iteration(self):
        with self.assertRaisesRegex(PublicationUnavailable, 'missing column pic'):
            self.predicate({'availabilityFilter': group('pic', 'Black')})

    def test_dbm_parent_uses_master_and_preserves_parent_join_duplicates(self):
        locations = [{'WHCode': 'P', 'LocationType': 'LDC'}] * 2
        predicate = self.predicate({'supplyChainFilter': group('forChildren', 'LDC')},
                                   'pie', locations)
        row = {'_a': {'ParentWhCode': 'wrong'}, '_master': {'ParentWhCode': 'P'}}
        self.assertEqual(predicate.select([row]), [row, row])

    def test_ageing_predicate_observes_each_snapshot_and_preserves_bag(self):
        row = dict(SKUCode='S', WhCode='L', ReportDate='2026-06-17', PhysicalInventoryColor='Black')
        snapshots = [dict(SKUCode='S', WhCode='L', AgePhysicalInv=4)] * 2
        seen = []
        def predicate(joined):
            seen.append(joined['_snapshot'])
            return 2
        self.assertEqual(availability_ageing([row], snapshots, 4, predicate=predicate),
                         [dict(date='2026-06-17', black=4, red=0, white=0)])
        self.assertEqual(seen, snapshots)
        self.assertEqual(availability_ageing([row], snapshots, 4, predicate=lambda _: 0), [])


if __name__ == '__main__':
    unittest.main()
