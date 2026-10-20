"""Ordered join bags and bounded lookup work at the producer boundaries."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from mta.application.r1_importer_master import NO_NORM_COLUMNS, _distinct, _join, _join_index, _key, process_importer_master
from mta.application.r1_daily_entry import native_auxiliary_stock_balances
from mta.application.r1_supplier_input import process_supplier_validation, STAGES, RAW_TABLES
from tests import test_production_csv_diagnostics as csv_fixtures
from tests import test_temporal_active_population as temporal_fixtures


class CountingRows(list):
    def __iter__(self):
        for row in super().__iter__():
            self.visits += 1
            yield row

    visits = 0


class IndexedProducerJoinTests(unittest.TestCase):
    def test_sql_index_matches_nested_join_with_nulls_spelling_and_duplicates(self):
        rows = [dict(SKUCode=s, WhCode=w, ordinal=i) for i, (s, w) in enumerate([
            ('s ', 'L'), (None, 'L'), ('S', 'l '), ('s ', 'L'), ('S', None), ('X', 'L')])]
        index = _join_index(rows)
        for source in rows:
            expected = [r for r in rows if _join(source, r)]
            actual = index.get(_key(source), [])
            self.assertEqual(actual, expected)
            self.assertTrue(all(a is b for a, b in zip(actual, expected)))

    def test_master_overlap_retains_each_matching_occurrence(self):
        payload = csv_fixtures.master_payload()
        no_norm = {f: payload['raw_master'][0][f] for f in NO_NORM_COLUMNS}
        payload['raw_no_norm'] = [no_norm, dict(no_norm)]
        result = process_importer_master(payload)
        self.assertEqual(result['outcome'], 'EARLY_RETURN')
        self.assertEqual([r['ReasonCode'] for r in result['rejects_added']], [20, 20])
        self.assertEqual(result['tables']['NoNormMasterRaw'], [])

    def test_supplier_parent_bag_keeps_duplicates_until_existing_distinct(self):
        payload = csv_fixtures.master_payload()
        master = process_importer_master(payload)
        master['tables']['MasterData'] *= 2
        master['tables']['MasterData'].append(dict(master['tables']['MasterData'][0], WhCode='OTHER'))
        raw = dict(SOBDataRaw=[], MOQDataRaw2=[], MOQDataRaw1=[dict(
            SKUCode='csv-1 ', SupplierCode='csv-p ', SupplierDescription='Parent', MOQ=7)])
        joined = []
        def observed_distinct(rows, fields):
            if fields == RAW_TABLES['MOQDataRaw2']:
                joined.extend(dict(r) for r in rows)
            return _distinct(rows, fields)
        with patch('mta.application.r1_supplier_input._distinct', side_effect=observed_distinct):
            result = process_supplier_validation(raw, master, payload['settings'], payload['run_timestamp'])
        tables = result[STAGES[-1]]['tables']
        self.assertEqual([r['WHCode'] for r in joined], ['CSV-W', 'CSV-W', 'OTHER'])
        self.assertEqual([r['WHCode'] for r in tables['MOQDataRaw2']], ['CSV-W', 'OTHER'])

    def test_auxiliary_index_preserves_duplicate_null_and_ambiguity_rules(self):
        day = '2026-10-18'
        daily = [dict(SKUCode=s, WHCode='L', Stock=12, ReportDate=day)
                 for s in ('s ', None, 's ')]
        attrs = [dict(SKUCode=s, LocCode='l ', StockPercentForRationing=25)
                 for s in ('S', None, 'S')]
        result = native_auxiliary_stock_balances(daily, [], attrs, day, 1)
        # This adapter's existing Python tuple match includes NULL identities.
        self.assertEqual([r['reserved_stock'] for r in result], ['9', '9', '9'])
        self.assertEqual([r['sku_code'] for r in result], ['s ', None, 's '])
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            native_auxiliary_stock_balances(daily, [], attrs + [dict(attrs[0], StockPercentForRationing=None)], day, 1)
        with self.assertRaisesRegex(ValueError, 'NULL reservation'):
            native_auxiliary_stock_balances(daily[:1], [], [dict(attrs[0], StockPercentForRationing=None)], day, 1)

    def test_auxiliary_large_population_reads_attributes_once(self):
        day = '2026-10-18'
        daily = [dict(SKUCode=str(i), WHCode='L', Stock=12, ReportDate=day) for i in range(1000)]
        attrs = CountingRows(dict(SKUCode=str(i), LocCode='L', StockPercentForRationing=25) for i in range(1000))
        result = native_auxiliary_stock_balances(daily, [], attrs, day, 1)
        self.assertEqual(len(result), 1000)
        self.assertEqual(attrs.visits, 1000)
        self.assertTrue(all(r['reserved_stock'] == '9' for r in result))

    def test_calculation_adapter_reads_processed_population_once(self):
        fixture = temporal_fixtures.ActivePopulationTest()
        profile, importer, processed = fixture.inputs(('A', 'B'))
        expected = fixture.run_adapter(profile, importer, processed)
        rows = CountingRows(processed + [dict(processed[0], SKUCode=str(i)) for i in range(1000)])
        self.assertEqual(fixture.run_adapter(profile, importer, rows), expected)
        self.assertEqual(rows.visits, len(rows))

    def test_route_indexes_keep_allocation_order_and_ignore_unrelated_routes(self):
        from mta.application.r1_calculation import calculate_r1_requirements
        from mta.application.r1_input import prepare_r1_current_day
        from tests.test_production_order_identity import payload, feed
        raw = payload([feed('Z', 25), feed('A', 35)])
        prepared = prepare_r1_current_day(raw)
        expected = calculate_r1_requirements(prepared, raw)
        unrelated = [dict(prepared.routes[0], sku_code='OTHER'+str(i),
                          location_code='OTHER', child_location_code='ELSEWHERE') for i in range(1000)]
        routes = CountingRows(list(prepared.routes) + unrelated)
        actual = calculate_r1_requirements(replace(prepared, routes=routes), raw)
        self.assertEqual(actual, expected)
        self.assertLessEqual(routes.visits, len(routes) * (len(set(r['wh_level'] for r in prepared.additional_master)) + 2))


if __name__ == '__main__':
    unittest.main()
