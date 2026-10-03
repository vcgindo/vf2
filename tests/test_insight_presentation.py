"""Focused insight wire/aggregation tests, not replacement parity fixtures."""
import unittest
from mta.presentation.insight_response import scalar_json_rows,chronic_grid_payload,insight_payload
from mta.presentation import insights


class InsightTest(unittest.TestCase):
    def test_chronic_chart_post_scalar_empty_list(self):
        for kind in ('chronic-loc', 'chronic-sku'):
            self.assertEqual(insight_payload([], kind), [])
        for kind in ('loc', 'sku', 'pie', 'ageing', 'availability-trend', 'availability-ageing'):
            self.assertIsNone(insight_payload([], kind))

    def test_scalar_json_null_and_positive_identity(self):
        self.assertIsNone(scalar_json_rows([]))
        rows=[dict(count=0),dict(count=0)]
        self.assertIs(scalar_json_rows(rows),rows)

    def test_chronic_grid_numeric_wire_and_null_omission_preserve_duplicates(self):
        row=dict(SKUCode='337',WHCode='AG515802',skucode='337',skudesc=None,
            PhysicalInventoryPen='100.00',PipelineInventoryPen='66.67',RLT=3)
        result=chronic_grid_payload([row,row])
        expected=dict(skucode='337',PhysicalInventoryPen=100.0,PipelineInventoryPen=66.67,RLT=3)
        self.assertEqual(result,[expected,expected])
        self.assertEqual(row['PhysicalInventoryPen'],'100.00')
        self.assertIsNone(chronic_grid_payload([]))

    def test_availability_denominator_excludes_null_not_nonblack_colours(self):
        rows=[dict(ReportDate='2026-06-17',LocationType=None,PhysicalInventoryColor=colour)
            for colour in ('Black','White','Green',None)]
        self.assertEqual(insights.availability_trend(rows),[dict(week='2026-06-17',percentage=66)])

    def test_ageing_uses_snapshot_multiplicity_and_threshold(self):
        pair=dict(SKUCode='337',WhCode='AG515802')
        rows=[dict(pair,ReportDate='2026-06-17',PhysicalInventoryColor='Black')]
        snapshots=[dict(pair,AgePhysicalInv=4),dict(pair,AgePhysicalInv=4)]
        self.assertEqual(insights.availability_ageing(rows,snapshots,4),
            [dict(date='2026-06-17',black=2,red=0,white=0)])
        self.assertEqual(insights.availability_ageing(rows,snapshots,5),[])


if __name__=='__main__': unittest.main()
