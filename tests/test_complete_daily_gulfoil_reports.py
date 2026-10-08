from datetime import date, timedelta
import unittest

from mta.application.complete_daily_gulfoil_reports import transform, csv_bytes, joined_rows, STATIC, PIVOTS
from mta.domain.complete_daily_scalars import ascii_equal


class GulfOilReportTests(unittest.TestCase):
    today = date(2026, 10, 8)

    def row(self, days=0, **changes):
        row = {key: key for key in STATIC}
        row.update(SKUCode='S', WHCode='W', Norm=7, RLT=4,
                   ReportDate=(self.today - timedelta(days=days)).isoformat(),
                   **{key: 'Black' for key in PIVOTS.values()})
        row.update(changes)
        return row

    def test_empty_historical_window_preserves_existing_file(self):
        report = transform([self.row(100)], 'BTR_Tech', host_today=self.today)
        self.assertEqual(report['action'], 'PRESERVE_EXISTING')
        self.assertTrue(report['diagnostic_required'])
        with self.assertRaisesRegex(ValueError, 'Absent report'):
            csv_bytes(report, line_ending='\r\n')

    def test_age_counts_missing_days_but_counts_only_actual_colors(self):
        report = transform([self.row(31, TechColor='Red'), self.row(0)], 'BTR_Tech', host_today=self.today)
        row = report['rows'][0]
        self.assertEqual(row['Age'], 31)
        self.assertEqual(row['BlackCount'], 1)
        self.assertEqual(row['RedCount'], 0)

    def test_latest_static_first_date_tie_and_pivot_first_nonnull(self):
        rows = [self.row(1, Norm=5), self.row(Norm=8, TechColor=None), self.row(Norm=9, TechColor='Red')]
        report = transform(rows, 'BTR_Tech', host_today=self.today)
        self.assertEqual(report['rows'][0]['Norm'], 8)
        self.assertEqual(report['rows'][0]['D90'], 'Red')
        self.assertEqual(report['rows'][0]['Age'], 1)

    def test_grey_virtual_predicate_and_nullable_int_csv_promotion(self):
        rows = [self.row(100, VirtualNorm=None), self.row(Norm=0, VirtualNorm=3)]
        report = transform(rows, 'BTR_OnHand', host_today=self.today)
        self.assertEqual(report['rows'][0]['D90'], 'Black')
        self.assertEqual(report['rows'][0]['VirtualNorm'], 3.0)
        self.assertIn(b',0,3.0,', csv_bytes(report, line_ending='\r\n'))
        rows[-1]['VirtualNorm'] = 0
        self.assertEqual(transform(rows, 'BTR_OnHand', host_today=self.today)['rows'][0]['D90'], 'Grey')

    def test_minimal_csv_quotes_and_null_colors(self):
        row = self.row(WhName=' edge ', ParentWhName='a,b', **{name: None for name in PIVOTS.values()})
        report = transform([row], 'BTR_Tech', host_today=self.today)
        self.assertEqual(report['rows'][0]['Age'], 0)
        raw = csv_bytes(report, line_ending='\r\n')
        self.assertIn(b', edge ,', raw)
        self.assertIn(b',"a,b",', raw)

    def test_native_date_order_required_and_target_diagnostic_condition(self):
        with self.assertRaisesRegex(ValueError, 'ORDER BY'):
            transform([self.row(), self.row(1)], 'BTR_Tech', host_today=self.today)
        report = transform([self.row(SKUCode='21104027051000', WHCode='P023_1002')],
                           'BTR_Tech', host_today=self.today)
        self.assertFalse(report['diagnostic_required'])

    def test_inner_join_preserves_duplicate_occurrences_and_denies_null_keys(self):
        history = self.row(ParentWhCode='P') | dict(VirtualNorm=8)
        sites = [dict(WHCode='W', WHDescription='receiving')]*2 + [dict(WHCode='P', WHDescription=None)]
        params = dict(bpr_history=[history, history | dict(ParentWhCode=None)],
            site_descriptions=sites,
            sku_attributes=[dict(SKUCode='S', SL1=None, SL2='two', SL3='three')],
            location_attributes=[dict(WHCode='W', LL1='one', LL2=None, LL3=None)],
            importer_master=[dict(SKUCode='S', WhCode='W', RLT=4)],
            sku_loc_attributes=[dict(SKUCode='S', LocCode='W', c11='A')]*2,
            equal=ascii_equal)
        rows = joined_rows(**params, report_type='BTR_Tech')
        self.assertEqual(len(rows), 4)
        self.assertNotIn('VirtualNorm', rows[0])
        self.assertIsNone(rows[0]['ParentWhName'])
        self.assertEqual(rows[0]['ABCxFMS'], 'A')
        self.assertEqual(joined_rows(**(params | dict(site_descriptions=[])), report_type='BTR_Tech'), [])


if __name__ == '__main__':
    unittest.main()
