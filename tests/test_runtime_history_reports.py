from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from mta.application import runtime_history_reports as report
from tests.test_runtime_bor_report import sources, bor

TODAY = date(2026, 6, 17)
FIXTURE = Path(__file__).parent / 'fixtures/runtime_reports_retained_20261019.json'


def history(**changes):
    return dict(dict(ParentWhCode='SUP', ParentWhName='Parent,Name', SKUCode='sku', SKUName='SKU,Name',
        WhCode='P041', WhName=None, IsNormed=True, Req=25, ParentNorm=0,
        RationedReq=30, SupplierDispatchReq=35, DispatchPen=Decimal('20.50'), DispatchColor='Red',
        Dispatch=40, ReportDate=TODAY, Stock=45, GIT=50), **changes)


def efficiency_sources():
    return dict(today=TODAY, rationing_history=[history()], sku_loc_attributes=[dict(
        SKUCode='SKU ', LocCode='p041 ', c9='a,b', c10=None, c12='', c13='x')],
        pick_report=[dict(SKUCode='sku', WhCode='P041', ParentWhCode='sup ', TOR_B=1, TOR_R=2, TOY=3, TOG=4)])


def allocation_sources():
    source = sources()
    return dict(today=TODAY, bor_history=[dict(bor(), ReportDate=TODAY)],
        color_sequence=source['color_sequence'], sku_descriptions=source['sku_descriptions'],
        site_descriptions=source['site_descriptions'], sku_loc_attributes=source['sku_loc_attributes'],
        sku_attributes=source['sku_attributes'], requirements=[dict(SKUCode='SKU ', WhCode='p041', AdvAllocDone=99)],
        remarks=[dict(SKUCode='SKU', WhCode='p041 ', SupplierCode='sup ', Remark='hello,world',
                      RemarkDate=datetime(2026, 6, 17, 12))])


class RuntimeHistoryReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = FIXTURE.read_bytes()
        cls.defs = {r['Id']: r for r in json.loads(cls.raw)}

    def eff(self, inputs=None, identity=2):
        return report.efficiency(self.defs[identity], **(inputs or efficiency_sources()))

    def alloc(self, inputs=None):
        return report.allocation_history(self.defs[8], **(inputs or allocation_sources()))

    def test_pins_exact_sql_not_deployment_id(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), report.SOURCE_FIXTURE_SHA256)
        for identity in (2, 3, 8):
            self.assertEqual(report.query_pin(dict(self.defs[identity], Id=999))['source_id'], identity)
            with self.assertRaises(ValueError): report.query_pin(dict(self.defs[identity], Query=self.defs[identity]['Query'] + ' '))

    def test_complete_efficiency_24_cells_and_numeric_parentnorm_branches(self):
        expected = ('SUP', 'ParentName', 'sku', 'SKUName', 'P041', None, True, 25,
                    'ab', '-', '', 'x', 35, Decimal('20.50'), 'Red', 40, TODAY, 'BOR', 45, 50, 1, 2, 3, 4)
        inputs = efficiency_sources(); before = deepcopy(inputs)
        self.assertEqual(self.eff(inputs), [expected])
        self.assertEqual(inputs, before)
        inputs['rationing_history'][0]['ParentNorm'] = None
        self.assertEqual(self.eff(inputs), [expected])
        inputs['rationing_history'][0]['ParentNorm'] = -1
        self.assertEqual(self.eff(inputs), [])
        self.assertEqual(self.eff(inputs, 3), [expected[:12] + (30,) + expected[13:17] + ('RRR',) + expected[18:]])

    def test_efficiency_date_lower_bound_no_upper_bound_today_stock_bag(self):
        inputs = efficiency_sources()
        inputs['rationing_history'] = [history(ReportDate=TODAY-timedelta(days=45)),
            history(ReportDate=TODAY-timedelta(days=44)), history(ReportDate=TODAY+timedelta(days=1)),
            history(ReportDate=None), history(), history(Stock=100, GIT=200)]
        rows = self.eff(inputs)
        self.assertEqual([r[16] for r in rows], [TODAY-timedelta(days=44)]*2 + [TODAY+timedelta(days=1)]*2 + [TODAY]*4)
        self.assertEqual([(r[18],r[19]) for r in rows], [(45,50),(100,200)]*4)
        inputs['today'] = None
        self.assertEqual(self.eff(inputs), [])

    def test_efficiency_pick_bands_and_all_left_bag_multiplicity(self):
        inputs = efficiency_sources()
        inputs['sku_loc_attributes'] *= 2
        inputs['pick_report'] += [dict(inputs['pick_report'][0], TOR_B=100)]
        expected = self.eff()[0]
        self.assertEqual(self.eff(inputs), [expected, expected[:20]+(100,2,3,4)]*2)
        inputs['pick_report'] = []; inputs['sku_loc_attributes'] = []
        inputs['rationing_history'][0]['ReportDate'] = TODAY-timedelta(days=1)
        self.assertEqual(self.eff(inputs), [expected[:8] + ('-',)*4 + expected[12:16] +
            (TODAY-timedelta(days=1), 'BOR') + (None,)*6])

    def test_complete_allocation_34_cells_and_null_left_bags(self):
        expected = ('sku', 'a "b"\n雪', 'P041', 'Chennai', 'SUP', 'Supplier',
                    1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,'Red',99,
                    '9',None,'hello,world','7','11','','13','3',TODAY)
        self.assertEqual(self.alloc(), [expected])
        self.assertEqual(len(expected), len(report.ALLOCATION_COLUMNS))
        inputs = allocation_sources()
        for name in ('sku_descriptions','site_descriptions','requirements','sku_loc_attributes','sku_attributes','remarks'):
            inputs[name] = []
        self.assertEqual(self.alloc(inputs), [('sku',None,'P041',None,'SUP',None,
            1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,'Red') + (None,)*9 + (TODAY,)])

    def test_allocation_inclusive_window_and_every_duplicate_bag(self):
        inputs = allocation_sources()
        inputs['bor_history'] = [dict(bor(), ReportDate=d) for d in (
            TODAY-timedelta(days=45), TODAY-timedelta(days=44), TODAY, TODAY+timedelta(days=1), None)]
        self.assertEqual([r[-1] for r in self.alloc(inputs)], [TODAY-timedelta(days=44), TODAY])
        for name in ('color_sequence','sku_descriptions','site_descriptions','requirements','sku_loc_attributes','sku_attributes'):
            inputs[name] *= 2
        rows = self.alloc(inputs)
        # Site is joined twice, hence seven independent two-occurrence joins.
        self.assertEqual(len(rows), 2*128)
        self.assertEqual(rows[:128], [self.alloc()[0][:-1]+(TODAY-timedelta(days=44),)]*128)

    def test_latest_remark_pair_partition_precedes_supplier_match(self):
        inputs = allocation_sources()
        inputs['remarks'].append(dict(inputs['remarks'][0], SupplierCode='OTHER', Remark='newer',
                                      RemarkDate=datetime(2026,6,18)))
        self.assertIsNone(self.alloc(inputs)[0][27])
        inputs['remarks'][1]['SupplierCode'] = 'SUP'
        self.assertEqual(self.alloc(inputs)[0][27], 'newer')

    def test_latest_remark_ties_deny_only_distinguishable_projected_results(self):
        inputs = allocation_sources(); inputs['remarks'] *= 2
        self.assertEqual(self.alloc(inputs), self.alloc())
        inputs['remarks'][1] = dict(inputs['remarks'][1], Remark='different')
        with self.assertRaises(report.AmbiguousLatestRemark): self.alloc(inputs)
        inputs['remarks'][1] = dict(inputs['remarks'][0], SupplierCode='OTHER')
        with self.assertRaises(report.AmbiguousLatestRemark): self.alloc(inputs)
        inputs['remarks'] = [dict(r, SupplierCode='OTHER') for r in inputs['remarks']]
        self.assertIsNone(self.alloc(inputs)[0][27])

    def test_missing_columns_typed_dates_and_unsupported_keys_are_explicit(self):
        inputs = efficiency_sources(); del inputs['pick_report'][0]['TOR_B']
        with self.assertRaisesRegex(ValueError, 'columns missing'): self.eff(inputs)
        inputs = efficiency_sources(); inputs['rationing_history'][0]['ParentNorm'] = ''
        with self.assertRaises(ValueError): self.eff(inputs)
        inputs = efficiency_sources(); inputs['rationing_history'][0]['SKUCode'] = 'é'
        with self.assertRaisesRegex(ValueError, 'UNQUALIFIED'): self.eff(inputs)
        inputs = allocation_sources(); inputs['remarks'][0]['RemarkDate'] = TODAY
        with self.assertRaises(ValueError): self.alloc(inputs)
        inputs = allocation_sources(); inputs['bor_history'][0]['ReportDate'] = datetime(2026,6,17)
        with self.assertRaises(ValueError): self.alloc(inputs)

    def test_canonical_nonnull_bit_and_remark_datetime_are_not_defaulted(self):
        # Pinned BTR DDL line588: IsNormed bit NOT NULL. BPR DDL line1934:
        # BORReport_OARemarkDetails.RemarkDate datetime NOT NULL (not the
        # unrelated nullable RemarkDate in the first table of that same file).
        inputs = efficiency_sources(); inputs['rationing_history'][0]['IsNormed'] = None
        with self.assertRaisesRegex(ValueError, 'IsNormed bit'): self.eff(inputs)
        inputs = allocation_sources(); inputs['remarks'][0]['RemarkDate'] = None
        with self.assertRaisesRegex(ValueError, 'typed source date'): self.alloc(inputs)

    def test_latest_pair_prepared_once_and_supplier_results_cached_without_deduping_output(self):
        inputs = allocation_sources()
        inputs['remarks'] += [dict(inputs['remarks'][0], Remark='old', RemarkDate=datetime(2026,1,1))] * 100
        inputs['bor_history'] *= 40
        # CI / trailing-space equivalents share the same query-local cache.
        inputs['bor_history'] += [dict(inputs['bor_history'][0], SKUCode='SKU ', SupplierCode='sup ')] * 20
        with patch.object(report, '_latest_remark_bags', wraps=report._latest_remark_bags) as prepare, \
                patch.object(report, '_remark_for', wraps=report._remark_for) as resolve:
            rows = self.alloc(inputs)
        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(resolve.call_count, 1)
        self.assertEqual(len(rows), 60)
        self.assertEqual([row[27] for row in rows], ['hello,world'] * 60)
        # NULL supplier never SQL-matches even a NULL supplier remark.
        inputs = allocation_sources(); inputs['bor_history'][0]['SupplierCode'] = None
        inputs['remarks'][0]['SupplierCode'] = None
        self.assertIsNone(self.alloc(inputs)[0][27])


if __name__ == '__main__':
    unittest.main()
