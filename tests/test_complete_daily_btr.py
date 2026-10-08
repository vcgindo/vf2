"""Focused PostBTR mechanics; native SQL differential proof remains required."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import unittest
from unittest.mock import patch

from mta.evidence import evidence_mode, final_stage

from mta.domain.complete_daily_btr import (
    post_btr_calculated_attributes, post_btr_stages, _penetration)


def equal(a, b):
    # Deliberately only a fixture adapter, not a qualified native collation.
    return str(a).rstrip(' ').upper() == str(b).rstrip(' ').upper()


TODAY = date(2026, 6, 6)


def attrs(location='rm', flag='RM'):
    return {'SKUCode': 's', 'LocCode': location, 'FGRMFlag': flag,
            'c9': 'old9', 'c10': 'old10', 'c12': 'old12', 'c13': 'old13'}


def trend(location='rm', ending=('Black',)):
    row = {'SKUCode': 's', 'WhCode': location}
    row.update({f'D{i}': 'Green' for i in range(61, 91)})
    row.update({f'D{i}': color for i, color in zip(range(91 - len(ending), 91), ending)})
    return row


def history_row(when, location='p', tech='Black', eco='Black'):
    return {'CurrentNodeSKU': 's', 'CurrentNodeWhCode': location,
            'ChildNodeSKU': 's', 'ChildNodeWhCode': 'c',
            'CurrentNodeStock': 0, 'CurrentNodeGIT': 0,
            'ChildStock': 0, 'ChildGIT': 0, 'ChildVN': 10,
            'CurrentNodeNorm': 10, 'TechPen': Decimal('100.000'),
            'EcoPen': Decimal('100.000'), 'TechColor': tech, 'EcoColor': eco,
            'ReportDate': when.isoformat()}


def inputs():
    calendars = [{f'D{i}': (TODAY - timedelta(days=90 - i)).isoformat()
                  for i in range(61, 91)}]
    return dict(buffer_trend_report=[trend(ending=('Black', 'Red'))],
                buffer_trend_report_econ=[trend(ending=('Black', 'Black'))],
                buffer_trend_dates=calendars,
                last_batch_run=[{'LastRunDate': TODAY.isoformat() + 'T00:00:00'}],
                sku_loc_attributes=[attrs()], location_attributes=[], req_calculation=[],
                importer_sku_loc_attributes=[attrs()], fg_trend_data=[],
                bor_with_order_allocation=[], bpr_table=[{'SKUCode': 's', 'WhCode': 'rm'}],
                bpr_sku_loc_attributes=[attrs()],
                supplier_dispatch_req=[{'SKUCode': 's', 'WHCode': 'rm'}],
                dbm_sku_loc_attributes=[attrs()], nms_all_items=[{'SKUCode': 's', 'WHCode': 'rm'}],
                intermediate_tables={'GulfOil_TechColorData': [{'old': 1}], 'other': [{'old': 2}]},
                equal=equal)


def fg_inputs():
    result = inputs()
    result.update(buffer_trend_report=[], buffer_trend_report_econ=[],
                  sku_loc_attributes=[attrs('p', 'FG')],
                  importer_sku_loc_attributes=[attrs('p', 'FG')],
                  location_attributes=[{'WHCode': 'p', 'c1': 'c'}],
                  req_calculation=[{'SKUCode': 's', 'WhCode': 'p', 'ParentWhCode': 'p',
                                    'Stock': 0, 'GIT': 0, 'Norm': 10, 'VirtualNorm': 10},
                                   {'SKUCode': 's', 'WhCode': 'c', 'ParentWhCode': 'p',
                                    'Stock': 0, 'GIT': 0, 'Norm': 10, 'VirtualNorm': 10}],
                  fg_trend_data=[history_row(TODAY - timedelta(days=i)) for i in (1, 2)],
                  bpr_table=[{'SKUCode': 's', 'WhCode': 'p'}],
                  bpr_sku_loc_attributes=[attrs('p', 'FG')],
                  supplier_dispatch_req=[{'SKUCode': 's', 'WhCode': 'p'}],
                  dbm_sku_loc_attributes=[attrs('p', 'FG')],
                  nms_all_items=[{'SKUCode': 's', 'WhCode': 'p'}])
    return result


class RMTests(unittest.TestCase):
    def test_rm_fields_and_six_propagations_preserve_inputs(self):
        data = inputs()
        opening = deepcopy(data)
        out = post_btr_calculated_attributes(**data)
        self.assertEqual([out['SkuLocAttributeData'][0][f] for f in ('c9', 'c10', 'c12', 'c13')],
                         ['2', '2', '0', '2'])
        for table in ('BPRSkuLocAttributeData', 'DBMSkuLocAttributeData', 'ImporterSkuLocAttributeData'):
            self.assertEqual([out[table][0][f] for f in ('c9', 'c10', 'c12', 'c13')], ['2', '2', '0', '2'])
        self.assertEqual(out['BPR_Table'][0]['SKULocAttr12'], '0')
        self.assertEqual(out['SupplierDispatchReq'][0]['SKULocAtt09'], '2')
        self.assertEqual(out['NMSAllItems'][0]['SKULocAtt13'], '2')
        self.assertEqual(out['IntermediateTables'], {'GulfOil_TechColorData': [], 'other': []})
        self.assertEqual(data, opening)

    def test_three_simultaneous_na_to_zero_passes_not_prior_color_copy(self):
        data = inputs()
        data['buffer_trend_report'] = [trend(ending=('Black', None, None, None, None, 'Black'))]
        stages = dict(post_btr_stages(**data))
        def colors(stage):
            return [r['TechColor'] for r in stages[stage]['IntermediateTables']['GulfOil_TechColorData']][-6:]
        self.assertEqual(colors('rm-tech-fill-1'), ['Black', '0', 'NA', 'NA', 'NA', 'Black'])
        self.assertEqual(colors('rm-tech-fill-3'), ['Black', '0', '0', '0', 'NA', 'Black'])
        self.assertEqual(stages['rm-tech-update-c12']['SkuLocAttributeData'][0]['c12'], '1')
        data['buffer_trend_report'] = [trend(ending=('Black', None, None, None, 'Black'))]
        self.assertEqual(post_btr_calculated_attributes(**data)['SkuLocAttributeData'][0]['c12'], '2')

    def test_rm_has_no_flag_filter_and_unselected_attributes_remain(self):
        data = inputs()
        data['sku_loc_attributes'][0]['FGRMFlag'] = 'FG'
        data['sku_loc_attributes'].append(attrs('absent'))
        data['buffer_trend_report'] *= 2
        self.assertEqual(post_btr_calculated_attributes(**data)['SkuLocAttributeData'][0]['c13'], '2')
        self.assertEqual(post_btr_calculated_attributes(**data)['SkuLocAttributeData'][1]['c13'], 'old13')

    def test_distinct_keeps_different_colors_and_inclusive_change_date(self):
        data = inputs()
        data['buffer_trend_report'] = [trend(ending=('Black',)), trend(ending=('Red',))]
        # Both colours occur today; SQL uses >= latest non-Black date, so Black
        # at the change date contributes even though this is not a timeline.
        self.assertEqual(post_btr_calculated_attributes(**data)['SkuLocAttributeData'][0]['c12'], '1')
        data['buffer_trend_report'].append(trend(ending=('black',)))
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            post_btr_calculated_attributes(**data)

    def test_rm_cross_apply_retains_null_calendar(self):
        data = inputs()
        data['buffer_trend_dates'][0]['D61'] = None
        stages = dict(post_btr_stages(**data))
        self.assertIsNone(stages['rm-tech-insert-colors']['IntermediateTables']['GulfOil_TechColorData'][0]['ReportDate'])


class FGTests(unittest.TestCase):
    def test_production_validation_modes_equal_without_diagnostic_deepcopy(self):
        data = fg_inputs()
        data['location_attributes'] *= 2
        data['sku_loc_attributes'] *= 2
        data['req_calculation'][1]['VirtualNorm'] = None
        data['buffer_trend_report'] = [trend('p', ending=('Black', None, 'Black'))]
        with evidence_mode('validation'):
            validation = final_stage(post_btr_stages(**data))
        with evidence_mode('production'), patch('mta.evidence.deepcopy', side_effect=AssertionError('diagnostic copy')):
            production = final_stage(post_btr_stages(**data))
            final = post_btr_calculated_attributes(**data)
        self.assertEqual(len(production), 1)
        self.assertGreater(len(validation), 1)
        self.assertEqual(production[-1], validation[-1])
        self.assertEqual(final, validation[-1][1])
        stages = dict(validation)
        scratch = stages['rm-tech-fill-1']['IntermediateTables']['GulfOil_TechColorData']
        self.assertEqual(scratch[-2]['TechColor'], '0')
        self.assertEqual(len(stages['fg-insert-today']['FGTrendData']), 4)
        self.assertIsNone(stages['fg-update-penetration']['FGTrendData'][-1]['TechPen'])

    def test_today_rebuild_retention_decimal_and_history_independence(self):
        data = fg_inputs()
        data['fg_trend_data'].extend([history_row(TODAY, tech='White'),
                                     history_row(TODAY - timedelta(days=30)),
                                     history_row(TODAY - timedelta(days=31))])
        old = deepcopy(data['fg_trend_data'])
        out = post_btr_calculated_attributes(**data)
        history = out['FGTrendData']
        self.assertEqual(len(history), 4)
        new = [r for r in history if r['ReportDate'] == TODAY.isoformat()]
        self.assertEqual(len(new), 1)
        self.assertEqual((new[0]['TechPen'], new[0]['EcoPen']), (Decimal('100.000'), Decimal('100.000')))
        self.assertEqual(new[0]['TechColor'], 'Black')
        self.assertIn((TODAY - timedelta(days=30)).isoformat(), [r['ReportDate'] for r in history])
        self.assertEqual(data['fg_trend_data'], old)
        self.assertEqual(out['SkuLocAttributeData'][0]['c12'], '3')

    def test_fg_insert_multiplicity_but_grid_distinct(self):
        data = fg_inputs()
        data['location_attributes'] *= 2
        data['importer_sku_loc_attributes'] *= 2
        data['sku_loc_attributes'] *= 2
        stages = dict(post_btr_stages(**data))
        today = [r for r in stages['fg-insert-today']['FGTrendData'] if r['ReportDate'] == TODAY.isoformat()]
        self.assertEqual(len(today), 4)
        grid = stages['fg-tech-insert-colors']['IntermediateTables']['GulfOil_TechColorData']
        self.assertEqual(len(grid), 30)
        self.assertEqual([r['c12'] for r in stages['truncate-intermediate-after']['SkuLocAttributeData']], ['3', '3'])

    def test_bor_null_missing_red_and_conflicting_join(self):
        data = fg_inputs()
        self.assertEqual(post_btr_calculated_attributes(**data)['SkuLocAttributeData'][0]['c12'], '3')
        data['bor_with_order_allocation'] = [{'SKUCode': 's', 'WhCode': 'p', 'DispatchColor': None}]
        self.assertEqual(post_btr_calculated_attributes(**data)['SkuLocAttributeData'][0]['c12'], '3')
        data['bor_with_order_allocation'][0]['DispatchColor'] = 'Red'
        out = post_btr_calculated_attributes(**data)['SkuLocAttributeData'][0]
        self.assertEqual((out['c12'], out['c13'], out['c9'], out['c10']), ('0', '3', '0', '3'))
        data['bor_with_order_allocation'].append({'SKUCode': 's', 'WhCode': 'p', 'DispatchColor': 'Black'})
        with self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            post_btr_calculated_attributes(**data)

    def test_retained_historical_pair_overwritten_without_current_selection(self):
        data = fg_inputs()
        data['req_calculation'] = []
        out = post_btr_calculated_attributes(**data)['SkuLocAttributeData'][0]
        self.assertEqual([out[f] for f in ('c9', 'c10', 'c12', 'c13')], ['0'] * 4)

    def test_zero_or_null_denominator_white_and_economic_divergence(self):
        data = fg_inputs()
        data['req_calculation'][0]['GIT'] = 10
        today = post_btr_calculated_attributes(**data)['FGTrendData'][-1]
        self.assertEqual((today['TechPen'], today['EcoPen'], today['TechColor'], today['EcoColor']),
                         (Decimal('100.000'), Decimal('50.000'), 'Black', 'Yellow'))
        data['req_calculation'][0]['Norm'] = -10
        today = post_btr_calculated_attributes(**data)['FGTrendData'][-1]
        self.assertIsNone(today['TechPen'])
        self.assertEqual(today['TechColor'], 'White')
        data['req_calculation'][1]['VirtualNorm'] = None
        today = post_btr_calculated_attributes(**data)['FGTrendData'][-1]
        self.assertIsNone(today['TechPen'])
        self.assertEqual(today['TechColor'], 'White')

    def test_unpivot_drops_null_and_scalar_rejects_multiple_even_equal(self):
        data = fg_inputs()
        data['buffer_trend_dates'][0]['D61'] = None
        stages = dict(post_btr_stages(**data))
        self.assertEqual(len(stages['fg-tech-insert-colors']['IntermediateTables']['GulfOil_TechColorData']), 29)
        data['last_batch_run'] *= 2
        with self.assertRaisesRegex(ValueError, 'SCALAR_SUBQUERY_MULTIPLE_ROWS'):
            post_btr_calculated_attributes(**data)

    def test_decimal_rounding_and_int_denominator_overflow(self):
        row = history_row(TODAY)
        row.update(ChildVN=2, CurrentNodeNorm=1, ChildStock=1)
        self.assertEqual(_penetration(row, False), Decimal('66.667'))
        row.update(ChildVN=2147483647, CurrentNodeNorm=1)
        with self.assertRaisesRegex(ValueError, 'ARITHMETIC_OVERFLOW'):
            _penetration(row, False)
        row.update(ChildVN=1, CurrentNodeNorm=0, ChildStock=-2147483648)
        with self.assertRaisesRegex(ValueError, 'ARITHMETIC_OVERFLOW'):
            _penetration(row, False)


if __name__ == '__main__':
    unittest.main()
