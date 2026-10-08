"""Focused producer mechanics; these tests are not native SQL parity proof."""
from copy import deepcopy
import math
import unittest
from unittest.mock import patch

from mta.evidence import evidence_mode, final_stage

from mta.domain.complete_daily_bpr import (
    post_bpr_calculated_attributes, post_bpr_stages,
    production_order_suggestions, production_suggestion_stages)


def equal(a, b):
    return str(a).rstrip().casefold() == str(b).rstrip().casefold()


def fixture_float(value):
    # Test adapter only; production must qualify its native conversion adapter.
    try:
        return float(value or 0)
    except ValueError:
        return None


def fixture_round(value):
    return float(math.floor(value + .5) if value >= 0 else math.ceil(value - .5))


def post_input():
    return dict(sku_loc_attributes=[{'SKUCode': 's', 'LocCode': 'w', 'c3': 'old'}],
                pick_list_report=[{'SKUCode': 's', 'WhCode': 'w', 'ParentWhCode': 'p',
                                   'RationedReq': 3, 'VirtualNorm': 15, 'Stock': 0,
                                   'GIT': 0, 'ParentPackSize': 4,
                                   'ParentStockForRationing': 19}],
                master_data_raw=[{'SKUCode': 's', 'WhCode': 'w', 'ParentWhCode': 'p',
                                  'SKULocAtt01': 'p', 'SKULocAtt02': '50'}],
                bpr_table=[{'SKUCode': 's', 'WhCode': 'w', 'SKULocAttr3': 'old'}],
                importer_sku_loc_attributes=[{'SKUCode': 's', 'LocCode': 'w', 'c3': 'old'}],
                nms_all_items=[{'SKUCode': 's', 'WhCode': 'w', 'SKULocAtt03': 'old'}],
                intermediate_tables={'scratch': [{'old': 1}]}, equal=equal,
                try_cast_float=fixture_float, round_float=fixture_round,
                float_to_nvarchar=lambda value: format(value, '.6g'))


def production_input():
    return dict(supplier_dispatch_req=[{'SKUCode': 's', 'WHCode': 'w', 'SupplierCode': 'p',
                                       'ReqTopOfRed': 3, 'ReqTopOfYellow': 4, 'ReqTopOfGreen': 5}],
                plants=[{'PlantCode': 'p'}],
                rationed_req_report=[{'SKUCode': 's', 'WhCode': 'w', 'Norm': 10,
                                      'Stock': None, 'GIT': 0}],
                daily_consumption=[{'SKUCode': 's', 'WHCode': 'p', 'ReportDate': '2026-06-06',
                                    'Stock': 4, 'GIT': 1}],
                last_batch_run=[{'LastRunDate': '2026-06-06'}],
                prod_order_suggestions=[{'old': 1}], equal=equal, sort_key=lambda v: v.upper(),
                intermediate_tables={name: [{'old': 1}] for name in (
                    'TempProductionOrderReq', 'TempConsolidatedProdOrderReq', 'PlantStock', 'other')})


class PostBPRTests(unittest.TestCase):
    def test_production_validation_modes_equal_without_diagnostic_deepcopy(self):
        inputs = post_input()
        inputs['sku_loc_attributes'] *= 2
        inputs['pick_list_report'][0]['VirtualNorm'] = None
        with evidence_mode('validation'):
            validation = final_stage(post_bpr_stages(**inputs))
        with evidence_mode('production'), patch('mta.evidence.deepcopy', side_effect=AssertionError('diagnostic copy')):
            production = final_stage(post_bpr_stages(**inputs))
            final = post_bpr_calculated_attributes(**inputs)
        self.assertEqual(len(production), 1)
        self.assertGreater(len(validation), 1)
        self.assertEqual(production[-1], validation[-1])
        self.assertEqual(final, validation[-1][1])

    def test_statement_order_propagation_multiplicity_and_no_mutation(self):
        inputs = post_input()
        inputs['sku_loc_attributes'] *= 2
        original = deepcopy(inputs['sku_loc_attributes'])
        stages = dict(post_bpr_stages(**inputs))
        self.assertEqual(stages['rationed-c3']['SkuLocAttributeData'][0]['c3'], '3')
        result = stages['truncate-intermediate-after']
        self.assertEqual([r['c3'] for r in result['SkuLocAttributeData']], ['8', '8'])
        self.assertEqual(result['BPR_Table'][0]['SKULocAttr3'], '8')
        self.assertEqual(result['ImporterSkuLocAttributeData'][0]['c3'], '8')
        self.assertEqual(result['NMSAllItems'][0]['SKULocAtt03'], '8')
        self.assertEqual(result['IntermediateTables'], {'scratch': []})
        self.assertEqual(inputs['sku_loc_attributes'], original)
        self.assertEqual(inputs['bpr_table'][0]['SKULocAttr3'], 'old')

    def test_cap_up_down_and_parent_floor(self):
        for stock, expected in ((9, '8'), (7, '4'), (2, '0'), (-1, '-4')):
            inputs = post_input()
            inputs['pick_list_report'][0]['ParentStockForRationing'] = stock
            self.assertEqual(post_bpr_calculated_attributes(**inputs)['SkuLocAttributeData'][0]['c3'], expected)

    def test_null_arithmetic_reaches_else_cap_and_null_pack_remains_null(self):
        inputs = post_input()
        inputs['pick_list_report'][0]['VirtualNorm'] = None
        self.assertEqual(post_bpr_calculated_attributes(**inputs)['SkuLocAttributeData'][0]['c3'], '16')
        inputs['pick_list_report'][0]['ParentPackSize'] = None
        self.assertIsNone(post_bpr_calculated_attributes(**inputs)['SkuLocAttributeData'][0]['c3'])

    def test_try_cast_failure_clamp_and_raw_match_null_exclusion(self):
        inputs = post_input()
        inputs['master_data_raw'][0]['SKULocAtt02'] = 'invalid'
        inputs['pick_list_report'][0]['Stock'] = 10
        self.assertEqual(post_bpr_calculated_attributes(**inputs)['SkuLocAttributeData'][0]['c3'], '0')
        inputs['master_data_raw'][0]['SKULocAtt01'] = None
        self.assertEqual(post_bpr_calculated_attributes(**inputs)['SkuLocAttributeData'][0]['c3'], '3')

    def test_self_rows_and_unmatched_rows_are_retained(self):
        inputs = post_input()
        inputs['pick_list_report'][0]['ParentWhCode'] = 'W '
        inputs['sku_loc_attributes'].append({'SKUCode': None, 'LocCode': 'w', 'c3': None})
        result = post_bpr_calculated_attributes(**inputs)
        self.assertEqual(result['SkuLocAttributeData'][0]['c3'], 'old')
        self.assertIsNone(result['SkuLocAttributeData'][1]['c3'])

    def test_conflicting_update_sources_and_divide_zero_are_not_repaired(self):
        inputs = post_input()
        inputs['pick_list_report'].append(inputs['pick_list_report'][0] | {'RationedReq': 99})
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            post_bpr_calculated_attributes(**inputs)
        inputs = post_input()
        inputs['master_data_raw'].append(inputs['master_data_raw'][0] | {'SKULocAtt02': '100'})
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            post_bpr_calculated_attributes(**inputs)
        inputs = post_input()
        inputs['pick_list_report'][0]['ParentPackSize'] = 0
        with self.assertRaisesRegex(ValueError, 'DIVIDE_BY_ZERO'):
            post_bpr_calculated_attributes(**inputs)


class ProductionTests(unittest.TestCase):
    def test_colors_are_owned_by_supplier_not_rationed_report(self):
        inputs = production_input()
        without_report_colors = production_order_suggestions(**inputs)
        inputs['rationed_req_report'][0].update(ReqTopOfRed=999, ReqTopOfYellow=None, ReqTopOfGreen=-999)
        self.assertEqual(production_order_suggestions(**inputs), without_report_colors)
        stages = dict(production_suggestion_stages(**inputs))
        inserted = stages['insert-production-req']['IntermediateTables']['TempProductionOrderReq'][0]
        self.assertEqual((inserted['Red'], inserted['Yellow'], inserted['Green']), (3, 4, 5))
        self.assertEqual((inserted['Norm'], inserted['Stock'], inserted['GIT']), (10, None, 0))

    def test_production_validation_modes_equal_with_required_business_scratch(self):
        inputs = production_input()
        inputs['supplier_dispatch_req'] *= 2
        inputs['plants'] *= 2
        inputs['daily_consumption'][0]['Stock'] = None
        with evidence_mode('validation'):
            validation = final_stage(production_suggestion_stages(**inputs))
        with evidence_mode('production'), patch('mta.evidence.deepcopy', side_effect=AssertionError('diagnostic copy')):
            production = final_stage(production_suggestion_stages(**inputs))
            final = production_order_suggestions(**inputs)
        self.assertEqual(len(production), 1)
        self.assertGreater(len(validation), 1)
        self.assertEqual(production[-1], validation[-1])
        self.assertEqual(final, validation[-1][1])
        stages = dict(validation)
        self.assertEqual(len(stages['insert-production-req']['IntermediateTables']['TempProductionOrderReq']), 4)
        self.assertEqual(len(stages['insert-plant-stock']['IntermediateTables']['PlantStock']), 2)
        self.assertEqual(stages['insert-plant-stock']['IntermediateTables']['PlantStock'][0]['Stock'], 0)

    def test_sequential_netting_and_original_inputs(self):
        inputs = production_input()
        original = deepcopy(inputs)
        stages = dict(production_suggestion_stages(**inputs))
        red = stages['net-red']['IntermediateTables']['TempConsolidatedProdOrderReq'][0]
        self.assertEqual((red['Red'], red['RemPlantEcoStk'], red['EcoColor']), (0, 2, 'Red'))
        result = stages['truncate-intermediate-after']
        self.assertEqual(result['ProdOrderSuggestions'], [dict(SKUCode='s', PlantCode='p', Red=0,
            Yellow=2, Green=5, TotalReq=7, EcoColor='Yellow', ReportDate='2026-06-06')])
        self.assertTrue(all(rows == [] for rows in result['IntermediateTables'].values()))
        self.assertEqual(inputs, original)

    def test_multiplicative_join_rows_are_summed_not_deduplicated(self):
        inputs = production_input()
        inputs['supplier_dispatch_req'] *= 2
        inputs['plants'] *= 2
        stages = dict(production_suggestion_stages(**inputs))
        self.assertEqual(len(stages['insert-production-req']['IntermediateTables']['TempProductionOrderReq']), 4)
        row = stages['truncate-intermediate-after']['ProdOrderSuggestions'][0]
        self.assertEqual((row['Red'], row['Yellow'], row['Green'], row['TotalReq']), (7, 16, 20, 43))

    def test_green_netting_and_full_stock_removes_suggestion(self):
        inputs = production_input()
        inputs['daily_consumption'][0]['Stock'] = 7
        row = production_order_suggestions(**inputs)['ProdOrderSuggestions'][0]
        self.assertEqual((row['Green'], row['EcoColor']), (4, 'Green'))
        inputs['daily_consumption'][0]['Stock'] = 20
        self.assertEqual(production_order_suggestions(**inputs)['ProdOrderSuggestions'], [])

    def test_missing_plant_stock_leaves_initial_zero_and_null_stock_is_zero(self):
        inputs = production_input()
        inputs['daily_consumption'] = []
        self.assertEqual(production_order_suggestions(**inputs)['ProdOrderSuggestions'][0]['TotalReq'], 12)
        inputs['daily_consumption'] = production_input()['daily_consumption']
        inputs['daily_consumption'][0]['Stock'] = None
        self.assertEqual(production_order_suggestions(**inputs)['ProdOrderSuggestions'][0]['TotalReq'], 11)

    def test_null_constraint_overflow_and_unordered_sources(self):
        inputs = production_input()
        inputs['supplier_dispatch_req'][0]['ReqTopOfRed'] = None
        with self.assertRaisesRegex(ValueError, 'NONNULL_CONSTRAINT'):
            production_order_suggestions(**inputs)
        inputs = production_input()
        inputs['supplier_dispatch_req'][0]['ReqTopOfRed'] = 2147483647
        with self.assertRaisesRegex(ValueError, 'ARITHMETIC_OVERFLOW'):
            production_order_suggestions(**inputs)
        inputs = production_input()
        inputs['last_batch_run'].append({'LastRunDate': '2026-06-07'})
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            production_order_suggestions(**inputs)
        inputs = production_input()
        inputs['daily_consumption'].append(inputs['daily_consumption'][0] | {'Stock': 9})
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            production_order_suggestions(**inputs)

    def test_date_cast_and_empty_top1_only_fail_when_inserting_required_date(self):
        inputs = production_input()
        inputs['last_batch_run'][0]['LastRunDate'] = '2026-06-06T17:30:00'
        inputs['last_batch_run'].append({'LastRunDate': '2026-06-06T01:00:00'})
        self.assertEqual(production_order_suggestions(**inputs)['ProdOrderSuggestions'][0]['ReportDate'], '2026-06-06')
        inputs['last_batch_run'] = []
        with self.assertRaisesRegex(ValueError, 'NONNULL_CONSTRAINT'):
            production_order_suggestions(**inputs)
        inputs['supplier_dispatch_req'] = []
        self.assertEqual(production_order_suggestions(**inputs)['ProdOrderSuggestions'], [])


if __name__ == '__main__':
    unittest.main()
