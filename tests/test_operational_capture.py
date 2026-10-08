from copy import deepcopy
import unittest
from mta.application.operational_capture import BAND_MAP, capture_rows


def calculated():
    band = {field: str(index) if index >= 3 else ('SKU', 'WH', 'PARENT')[index]
            for index, (_, field) in enumerate(BAND_MAP)}
    return [dict(capability='r1_requirement_band', rows=[band, deepcopy(band)]),
            dict(capability='r1_advance_stock_allocation', rows=[
                dict(sku_code='SKU', source_location_code='WH', allocated_quantity='3',
                     allocation_type='advance-stock')])]


class OperationalCaptureTests(unittest.TestCase):
    def test_copies_every_quantity_and_duplicate(self):
        original = calculated()
        expected = deepcopy(original)
        result = capture_rows(original)
        self.assertEqual(original, expected)
        self.assertEqual(len(result['requirement_bands']), 2)
        self.assertEqual(result['requirement_bands'][0], result['requirement_bands'][1])
        for index, (field, _) in enumerate(BAND_MAP):
            self.assertEqual(result['requirement_bands'][0][field],
                             index if index >= 3 else ('SKU', 'WH', 'PARENT')[index])
        self.assertEqual(result['advance_stock_allocations'], [
            dict(sku_code='SKU', source_location_code='WH', allocated_quantity=3)])

    def test_empty_requires_explicit_capabilities(self):
        value = calculated()
        for item in value:
            item['rows'] = []
        self.assertEqual(capture_rows(value), dict(requirement_bands=[], advance_stock_allocations=[]))
        with self.assertRaises(ValueError):
            capture_rows(value[:1])
        with self.assertRaises(ValueError):
            capture_rows(value + value[:1])

    def test_no_git_substitution_or_quantity_rounding(self):
        value = calculated()
        value[1]['rows'][0]['allocation_type'] = 'advance-git'
        with self.assertRaises(ValueError):
            capture_rows(value)
        value = calculated()
        value[0]['rows'][0]['order_req_red'] = '1.5'
        with self.assertRaises(ValueError):
            capture_rows(value)

    def test_nullable_values_and_source_roster(self):
        value = calculated()
        value[0]['rows'][0].update(parent_location_code=None, norm_req_red=None)
        result = capture_rows(value)
        self.assertIsNone(result['requirement_bands'][0]['ParentWhCode'])
        self.assertIsNone(result['requirement_bands'][0]['NormReqRed'])
        del value[0]['rows'][0]['order_green_band']
        with self.assertRaises(ValueError):
            capture_rows(value)
