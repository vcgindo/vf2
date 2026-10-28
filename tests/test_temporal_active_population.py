"""Current-master membership at the calculation adapter boundary."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from mta.temporal.chain import calculation_source, MASTER_SOURCE_MAP


class ActivePopulationTest(unittest.TestCase):
    def inputs(self, active=('A',)):
        profile = {'calculation': {'skus': [], 'locations': [],
            'logistics': {'items': []},
            'stock_openings': [dict(sku_code=s, location_code='L', stock=99,
                stock_percent_reservation=None, norm_percent_reservation=None) for s in ('B','A','A')],
            'policies': [dict(sku_code=s, location_code='L', policy={
                'spike_override': 99, 'pso_override': 99}) for s in ('B','A','A')]}}
        masters = []
        for sku in active:
            row = {field: None for field in MASTER_SOURCE_MAP.values()}
            row[MASTER_SOURCE_MAP['sku_code']] = sku
            row[MASTER_SOURCE_MAP['location_code']] = 'L'
            masters.append(row)
        importer = dict(MasterData=masters, LocationAttributeData=[],
            SkuAttributeData=[dict(SKUCode=s, ElephantOrderCapping=None) for s in ('A','B')],
            SkuLocAttributeData=[dict(SKUCode=s, LocCode='L', PackSize=2,
                StockPercentForRationing=None, NormPercentReservation=3,
                SpikeThreshold=None, PSOThreshold=7) for s in active])
        processed = [dict(SKUCode=s, WhCode='L', ReportDate='2026-07-04',
                          Stock=11, GIT=0) for s in active]
        return profile, importer, processed

    def run_adapter(self, profile, importer, processed):
        return calculation_source('2026-07-04', '2026-07-03', profile,
            importer, [], processed, [], [], 'focused-active-population')

    def test_remove_preserves_duplicate_order_values_and_input(self):
        args = self.inputs()
        before = deepcopy(args)
        value = self.run_adapter(*args)
        self.assertEqual([r['sku_code'] for r in value['stock_openings']], ['A','A'])
        self.assertEqual([r['sku_code'] for r in value['policies']], ['A','A'])
        self.assertEqual(value['stock_openings'][0], dict(sku_code='A', location_code='L',
            stock=11, stock_percent_reservation=None, norm_percent_reservation=3))
        self.assertEqual(value['policies'][0]['policy'], dict(spike_override=None, pso_override=7))
        self.assertEqual(args, before)

    def test_restore_reuses_supplied_template_in_original_order(self):
        value = self.run_adapter(*self.inputs(('A','B')))
        for name in ('stock_openings','policies'):
            self.assertEqual([r['sku_code'] for r in value[name]], ['B','A','A'])

    def test_current_missing_or_duplicate_stock_still_denied(self):
        profile, importer, processed = self.inputs()
        for rows in ([], processed * 2):
            with self.assertRaisesRegex(ValueError, 'Missing/ambiguous current physical stock'):
                self.run_adapter(profile, importer, rows)

    def test_stock_failure_logs_only_first_bounded_key_and_exact_reason(self):
        from mta.application import stage_observation as observation
        for reason, count in (('missing',0),('duplicate',2),('null',1)):
            profile, importer, processed = self.inputs()
            rows = [] if count==0 else processed*count
            if reason=='null': rows[0]['Stock']=None
            before = deepcopy((profile,importer,rows))
            with patch.object(observation._logger,'warning') as logger, observation.operation('test-run'):
                with self.assertRaisesRegex(ValueError,
                        '^Missing/ambiguous current physical stock reaches calculation; no substituted input$'):
                    self.run_adapter(profile,importer,rows)
            diagnostic = [json.loads(call.args[1]) for call in logger.call_args_list
                          if json.loads(call.args[1])['event']=='rejection']
            self.assertEqual(len(diagnostic),1)
            self.assertEqual({k:diagnostic[0][k] for k in
                ('sku_code','location_code','business_date','match_count','reason','owner')},
                dict(sku_code='A',location_code='L',business_date='2026-07-04',
                     match_count=count,reason=reason,owner='test-run'))
            self.assertNotIn('Stock',json.dumps(diagnostic))
            self.assertEqual((profile,importer,rows),before)

    def test_current_missing_attributes_still_denied(self):
        profile, importer, processed = self.inputs()
        importer['SkuLocAttributeData'] = []
        with self.assertRaises(KeyError):
            self.run_adapter(profile, importer, processed)

    def test_missing_templates_are_not_manufactured(self):
        profile, importer, processed = self.inputs()
        profile['calculation']['stock_openings'] = []
        profile['calculation']['policies'] = []
        value = self.run_adapter(profile, importer, processed)
        self.assertEqual(value['stock_openings'], [])
        self.assertEqual(value['policies'], [])
        # R1 admission owns the ensuing missing-policy/stock closure denial.
