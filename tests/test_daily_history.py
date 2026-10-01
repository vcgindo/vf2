"""Graph consumer protocol probes, not new synthetic acceptance data."""
from copy import deepcopy
import unittest
from mta.presentation.daily_history import daily_graph,POPULATIONS


class DailyHistoryTest(unittest.TestCase):
    def setUp(self):
        self.identity=dict(SKUCode='337',WhCode='AG515802')
        self.state={n:[] for n in ('DailyConsumption','SuspendHistory','NormChangeLogTbl','DBMMaster',
            'SuspendStockType','SuspendConsumptionType','SuggestionsLog','ReasonCodes')}
        self.state['LastBatchRunTbl']=[dict(LastRunDate='2026-06-17')]

    def test_full_join_duplicate_multiplicity_nulls_and_order(self):
        consumption=dict(self.identity,ReportDate='2026-06-17',Stock=1,GIT=2,Consumption=3,Receipts=4,BlueZone=5)
        suspended=dict(self.identity,ReportDate='2026-06-17',RedReasonStockType=1,GreenReasonStockType=2,
            RedReasonConsumptionType=3,GreenReasonConsumptionType=4)
        self.state['DailyConsumption']=[consumption]*2+[dict(consumption,ReportDate='2026-06-15')]
        self.state['SuspendHistory']=[suspended]*3+[dict(suspended,ReportDate='2026-06-16')]
        before=deepcopy(self.state); values=daily_graph(self.state,'337','AG515802')[0]['StockData']
        self.assertEqual(len(values),8); self.assertEqual(values[0]['dt'],'2026-06-15')
        self.assertIsNone(values[0]['rrs']); self.assertIsNone(values[1]['stk'])
        self.assertEqual(self.state,before)

    def test_horizon_and_history_reason_joins_remain_distinct(self):
        self.state['ReasonCodes']=[dict(Id=1,Reason='Retained reason')]*2
        self.state['NormChangeLogTbl']=[dict(self.identity,NormChangeDate='2020-01-01',OldNorm=1,NewNorm=2,NormChangeReason=1)]
        self.state['SuggestionsLog']=[dict(self.identity,SuggestionDate='2026-06-17',OldNorm=1,NewNorm=2,Type=9)]
        result=daily_graph(self.state,'337','AG515802')[0]
        self.assertIsNone(result['NormData']); self.assertEqual(len(result['NormChangeHistoryData']),2)
        self.assertIsNone(result['SuggestionHistoryData'][0]['rsn'])

    def test_empty_nested_sections_are_sql_null_not_empty_arrays(self):
        before=deepcopy(self.state); result=daily_graph(self.state,'337','AG515802')[0]
        self.assertTrue(all(result[n] is None for n in POPULATIONS))
        self.assertEqual(result['RunDate'],'2026-06-17'); self.assertEqual(result['horizonValue'],90)
        self.assertEqual(before,self.state)
