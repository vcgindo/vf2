from copy import deepcopy
from datetime import date
from decimal import Decimal
import unittest

from mta.domain.btr_finalization import (
    BPR_SOURCE_FIELDS, COLOURS, DAYS, _colour_age, _count_graph, _import_bpr,
    _latest_norms, _pivot,
)
from mta.domain.btr_rationing_history import COLUMNS, SOURCE_FIELDS, collect
from mta.domain.dbm_daily_cleanup import daily_cleanup
from mta.domain.dbm_ingestion import import_daily_observations
from mta.domain.dbm_suspension_history import CONTRIBUTORS, REASONS, gather_suspension_history
from mta.domain.late_bpr_transfer import update_bpr
from mta.row_sequences import RecordRows


def values(rows):
    return [dict(row) for row in rows]


class StreamedHistoryProducerTests(unittest.TestCase):
    def assert_streamed_equal(self, eager, streamed):
        self.assertIsInstance(streamed, RecordRows)
        self.assertEqual(values(streamed), eager)
        self.assertEqual(values(streamed), eager)  # reiteration keeps the same ordinals

    def test_daily_consumption_replacement_and_cleanup_preserve_bag_order(self):
        opening = [
            dict(SKUCode='A', WhCode='L', Stock=9, Consumption=None, GIT=1,
                 Receipts=0, BlueZone=2, ReportDate='2026-04-07'),
            dict(SKUCode='A', WhCode='L', Stock=8, Consumption=3, GIT=1,
                 Receipts=1, BlueZone=2, ReportDate='2026-04-08'),
            dict(SKUCode='A', WhCode='L', Stock=7, Consumption=3, GIT=1,
                 Receipts=1, BlueZone=2, ReportDate='2026-04-07'),
        ]
        raw = [dict(SKUCode='A', WhCode='L', Stock=6, Consumption=None, GIT=0,
                    Receipts=4, ReportDate='2026-04-08')]
        masters = [dict(SKUCode='A', WhCode='L'), dict(SKUCode='A', WhCode='L')]
        bpr = [dict(SKUCode='A', WHCode='L', BlueZone=5, ReportDate='2026-04-08')]
        args = (raw, masters, bpr, [], [])
        expected = import_daily_observations('2026-04-08', deepcopy(opening), *deepcopy(args))
        source = RecordRows.from_rows(deepcopy(opening))
        actual = import_daily_observations('2026-04-08', source, *deepcopy(args))
        self.assert_streamed_equal(expected, actual)
        self.assertEqual(values(source), opening)

        eager_state = dict(DailyConsumption=deepcopy(expected),
                           LastBatchRunTbl=[{'LastRunDate': '2026-04-08T00:00:00'}])
        streamed_state = dict(DailyConsumption=actual,
                              LastBatchRunTbl=[{'LastRunDate': '2026-04-08T00:00:00'}])
        eager = daily_cleanup('2026-04-08', eager_state, 370)['DailyConsumption']
        streamed = daily_cleanup('2026-04-08', streamed_state, 370)['DailyConsumption']
        self.assert_streamed_equal(eager, streamed)

    def test_suspend_history_preserves_duplicates_nulls_and_input(self):
        def history(sku, report_date, reasons):
            return dict(SKUCode=sku, WhCode='L', RedEnabledStockType=1,
                        GreenEnabledStockType=1, RedEnabledConsumptionType=1,
                        GreenEnabledConsumptionType=1, ReportDate=report_date,
                        **{name: reasons for name in REASONS})
        opening = [
            history('OLD', '2025-01-01', 1), history('A', '2026-04-07', None),
            history('A', '2026-04-07', None), history('DROP', '2026-04-08', 0),
        ]
        state = dict(
            LastBatchRunTbl=[{'LastRunDate': '2026-04-08T00:00:00'}],
            SuspendHistory=deepcopy(opening),
            SuspendStockType=[dict(SKUCode='A', WhCode='L', RedEnabled=1, GreenEnabled=0)],
            SuspendConsumptionType=[dict(SKUCode='A', WhCode='L', RedEnabled=0, GreenEnabled=1)],
        )
        for table, _, _ in CONTRIBUTORS:
            state.setdefault(table, [])
        expected = gather_suspension_history('2026-04-08', deepcopy(state))['SuspendHistory']
        streamed_state = deepcopy(state)
        source = RecordRows.from_rows(opening)
        streamed_state['SuspendHistory'] = source
        actual = gather_suspension_history('2026-04-08', streamed_state)['SuspendHistory']
        self.assert_streamed_equal(expected, actual)
        self.assertEqual(values(source), opening)

    def test_bpr_history_stable_filter_append_matches_eager(self):
        def bpr(report_date, stock):
            row = {name: None for name in BPR_SOURCE_FIELDS}
            row.update(SKUCode='A', WhCode='L', ParentWhCode='P', Norm=10,
                       Stock=stock, GIT=0, VirtualNorm=0)
            row['WHCode'] = row.pop('WhCode')
            row['ReportDate'] = report_date
            return row

        opening = [bpr('2026-04-07', 1), bpr('2026-04-07', 1), bpr('2025-12-01', None)]
        incoming = {name: None for name in BPR_SOURCE_FIELDS}
        incoming.update(SKUCode='A', WhCode='L', ParentWhCode='P', Norm=10,
                        Stock=2, GIT=0, VirtualNorm=0)
        facts = dict(vf_RationedReqReport=[incoming], DBMMaster=[], CWH_List=[], DistributorList=[],
                     LocationAttributeData=[], SiteDescriptionTbl=[], SkuAttributeData=[],
                     SKUDescriptionTbl=[], SkuLocAttributeData=[])
        prior = dict(BPR=deepcopy(opening), LocationAttributeData=[], SiteDescriptionTbl=[],
                     SkuAttributeData=[], SKUDescriptionTbl=[], SkuLocAttributeData=[])
        expected = _import_bpr(date(2026, 4, 8), deepcopy(prior), deepcopy(facts))['BPR']
        streamed_prior = deepcopy(prior)
        source = RecordRows.from_rows(opening)
        streamed_prior['BPR'] = source
        actual = _import_bpr(date(2026, 4, 8), streamed_prior, deepcopy(facts))['BPR']
        self.assert_streamed_equal(expected, actual)
        self.assertEqual(values(source), opening)

    def test_rationing_history_streams_adjacent_update_without_mutating_input(self):
        def target(report_date, dispatch=-1):
            row = {}
            for column in COLUMNS:
                name, kind = column['name'], column['type']
                row[name] = (None if column['nullable'] else
                             'A' if kind == 'nvarchar' else
                             Decimal('1.00') if kind == 'decimal' else
                             False if kind == 'bit' else 1)
            row.update(SKUCode='A', WhCode='L', ParentWhCode='P', GIT=10,
                       Receipts=0, Consumption=0, Dispatch=dispatch,
                       SupplierDispatchReq=None, ReportDate=report_date)
            return row

        opening = [target('2026-04-07'), target('2026-04-07'), target('2025-01-01')]
        report_row = {name: target('2026-04-08', None)[name] for name in SOURCE_FIELDS}
        report_row['GIT'] = 8
        report = [report_row, deepcopy(report_row)]
        daily = [dict(SKUCode='A', WHCode='L', ReportDate='2026-04-08', Receipts=4, Consumption=3)]
        supplier = [dict(SKUCode='A', WHCode='L', DispatchReq=3),
                    dict(SKUCode='A', WHCode='L', DispatchReq=None)]
        expected = collect('2026-04-08', deepcopy(opening), deepcopy(report),
                           deepcopy(daily), deepcopy(supplier), 90)
        source = RecordRows.from_rows(deepcopy(opening))
        actual = collect('2026-04-08', source, deepcopy(report), deepcopy(daily),
                         deepcopy(supplier), 90)
        self.assert_streamed_equal(expected, actual)
        self.assertEqual(values(source), opening)
        self.assertEqual([row['Dispatch'] for row in values(actual)[:2]], [2, 2])
        self.assertEqual([row['SupplierDispatchReq'] for row in values(actual)[2:]], [3, 3])

    def test_late_bpr_blue_zone_update_streams_without_mutating_input(self):
        opening = [
            dict(SKUCode='A', WHCode='L', ReportDate='2026-04-08', BlueZone=1),
            dict(SKUCode='A', WHCode='L', ReportDate='2026-04-08T12:00:00', BlueZone=None),
            dict(SKUCode='A', WHCode='L', ReportDate='2026-04-07', BlueZone=3),
            dict(SKUCode='B', WHCode='L', ReportDate='2026-04-08', BlueZone=4),
        ]
        report = [dict(SKUCode='A', WHCode='L', ResidualSnP=None, NormReq=2,
                       BlueReq=7, Req=8, RationedReq=6, LeftoverParentStock=None)]
        state = dict(BPR_Table=[dict(SKUCode='A', WHCode='L')],
                     BPRDailyConsumption=deepcopy(opening),
                     BPRLastBatchRunTbl=[dict(LastRunDate='2026-04-08T00:00:00')],
                     vf_RationedReqReport=report)
        expected = update_bpr(deepcopy(state))
        source = RecordRows.from_rows(deepcopy(opening))
        streamed_state = deepcopy(state)
        streamed_state['BPRDailyConsumption'] = source
        actual = update_bpr(streamed_state)
        self.assert_streamed_equal(expected['BPRDailyConsumption'],
                                   actual['BPRDailyConsumption'])
        self.assertEqual(values(source), opening)
        self.assertEqual([row['BlueZone'] for row in values(actual['BPRDailyConsumption'])],
                         [7, 7, 3, 4])

    def test_btr_history_folds_match_lists_with_duplicate_null_date_ties(self):
        def history(report_date, **changes):
            row = dict(SKUCode='A', WHCode='L', ParentWhCode='P', ReportDate=report_date,
                       Norm=None, VirtualNorm=4, TechPen=None, EcoPen=2,
                       DispatchPen=3, PhysicalInventoryPen=4, TechColor=None,
                       EcoColor='Red', DispatchColor='Black',
                       PhysicalInventoryColor='White')
            row.update(changes)
            return row

        opening = [history('2026-04-07', TechPen=1, TechColor='Green'),
                   history('2026-04-08'), history('2026-04-08')]
        streamed = RecordRows.from_rows(deepcopy(opening))
        self.assertEqual(_latest_norms(opening, []), _latest_norms(streamed, []))
        for field in ('TechPen', 'TechColor'):
            self.assertEqual(_pivot(opening, date(2026, 4, 8), field),
                             _pivot(streamed, date(2026, 4, 8), field))

        trend = dict(SKUCode='A', WhCode='L', Age=0,
                     **{colour + 'Count': 0 for colour in COLOURS},
                     **{field: None for field in DAYS})
        state = dict(BPR=opening, BufferTrendReport=[deepcopy(trend)],
                     BufferTrendReportEcon=[deepcopy(trend)],
                     BufferTrendDispatch=[deepcopy(trend)],
                     BufferTrendPhysicalInv=[deepcopy(trend)])
        streamed_state = deepcopy(state)
        streamed_state['BPR'] = streamed
        eager_age = _colour_age(date(2026, 4, 8), state, True, 1)
        streamed_age = _colour_age(date(2026, 4, 8), streamed_state, True, 1)
        for table in ('BufferTrendReport', 'BufferTrendReportEcon',
                      'BufferTrendDispatch', 'BufferTrendPhysicalInv'):
            self.assertEqual(streamed_age[table], eager_age[table])
        self.assertEqual(eager_age['BufferTrendReportEcon'][0]['RedCount'], 3)
        eager_graph = _count_graph(state)['BufferTrendGraph']
        streamed_graph = _count_graph(streamed_state)['BufferTrendGraph']
        self.assertEqual(streamed_graph, eager_graph)
        self.assertEqual(eager_graph[-1]['EcoRed'], 2)
        self.assertEqual(eager_graph[-1]['TechWhite'], 0)

        conflicting = opening + [history('2026-04-08', VirtualNorm=5)]
        for rows in (conflicting, RecordRows.from_rows(conflicting)):
            with self.assertRaisesRegex(ValueError, 'latest BTR norm'):
                _latest_norms(rows, [])
        colour_conflict = opening + [history('2026-04-08', EcoColor='Yellow')]
        for rows in (colour_conflict, RecordRows.from_rows(colour_conflict)):
            bad = deepcopy(state)
            bad['BPR'] = rows
            with self.assertRaisesRegex(ValueError, 'conflicting BPR colours'):
                _colour_age(date(2026, 4, 8), bad, True, 1)

    def test_import_bpr_latest_parent_fold_matches_streamed_and_keeps_tie_guard(self):
        def history(parent):
            return dict(SKUCode='A', WHCode='L', ParentWhCode=parent,
                        ReportDate='2026-04-07', Norm=1, VirtualNorm=1)

        def inputs(rows):
            prior = dict(BPR=rows, LocationAttributeData=[], SiteDescriptionTbl=[],
                         SkuAttributeData=[], SKUDescriptionTbl=[], SkuLocAttributeData=[])
            facts = dict(vf_RationedReqReport=[], LocationAttributeData=[],
                         SiteDescriptionTbl=[], SkuAttributeData=[], SKUDescriptionTbl=[],
                         SkuLocAttributeData=[], CWH_List=[], DistributorList=[], DBMMaster=[])
            return prior, facts

        opening = [history('P'), history('P')]
        eager = _import_bpr(date(2026, 4, 8), *inputs(deepcopy(opening)))
        streamed = _import_bpr(date(2026, 4, 8), *inputs(RecordRows.from_rows(opening)))
        self.assertEqual(values(streamed['BPR']), eager['BPR'])
        self.assertEqual(streamed['LocationAttributeData'], eager['LocationAttributeData'])
        conflicting = [history('P'), history(None)]
        for rows in (conflicting, RecordRows.from_rows(conflicting)):
            with self.assertRaisesRegex(ValueError, 'latest BPR parent'):
                _import_bpr(date(2026, 4, 8), *inputs(rows))


if __name__ == '__main__':
    unittest.main()
