"""Independent positional witnesses for retained RuntimeReports 4/5/6 SQL."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import unittest

from mta.application import runtime_bor_report as report
from mta.row_sequences import RecordRows

FIXTURE = Path(__file__).parent / 'fixtures/runtime_reports_retained_20261019.json'


def bor(**changes):
    row = dict(SKUCode='sku', WhCode='P041', SupplierCode='SUP', DispatchColor='Red',
               Norm=1, Stock=2, VirtualNorm=3, GIT=4, ParentLeftoverStock=5,
               Requirement=6, Req_TOB=7, Req_TOR=8, Req_TOY=9, Req_TOG=10,
               Req_TOBlue=11, DispatchQty=12, Dispatch_TOB=13, Dispatch_TOR=14,
               Dispatch_TOY=15, Dispatch_TOG=16, Dispatch_ToBlue=17,
               OrderBlackUnsatisfiedPercentage=Decimal('10.25'),
               OrderRedUnsatisfiedPercentage=Decimal('20.25'),
               OrderYellowUnsatisfiedPercentage=Decimal('30.25'),
               OrderGreenUnsatisfiedPercentage=Decimal('40.25'), DispatchPen=Decimal('50.25'))
    return dict(row, **changes)


def sources():
    return dict(bor_with_order_allocation=[bor()], color_sequence=[dict(Color='Red', SequenceNo=2)],
                sku_descriptions=[dict(SKUCode='SKU ', SKUDescription='a,"b"\n雪')],
                site_descriptions=[dict(WHCode='p041 ', WHDescription='Chennai'),
                                   dict(WHCode='sup ', WHDescription='Supplier')],
                sku_loc_attributes=[dict(SKUCode='SKU', LocCode='p041 ', c9='9', c10=None,
                                        c12='', c13='13', c11='11', c7='7')],
                sku_attributes=[dict(SKUCode='SKU', c3='3')])


class RuntimeBorReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = FIXTURE.read_bytes()
        cls.definitions = {row['Id']: row for row in json.loads(cls.raw) if row['Id'] in (4, 5, 6)}

    def project(self, inputs=None, identity=4):
        return report.project(self.definitions[identity], **(inputs or sources()))

    def test_exact_captured_source_and_query_pins_not_deployment_ids(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), report.SOURCE_FIXTURE_SHA256)
        for identity in (4, 5, 6):
            definition = dict(self.definitions[identity], Id=900 + identity)
            self.assertEqual(report.query_pin(definition)['source_id'], identity)
            self.assertEqual(report.project(definition, **sources()), self.project(identity=identity))
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                report.query_pin(dict(definition, Query=definition['Query'] + ' '))

    def test_complete_independently_derived_31_cells_and_no_input_mutation(self):
        inputs = sources(); before = deepcopy(inputs)
        expected = ('sku', '"a,"b"\n雪"', 'P041', '"Chennai"', 'SUP', '"Supplier"',
                    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
                    'Red', '9', '-', '', '13', '3', '11', '7')
        self.assertEqual(self.project(inputs), [expected])
        self.assertEqual(len(expected), len(report.COLUMNS))
        self.assertEqual(inputs, before)

    def test_all_six_join_bags_expand_duplicates_in_supplied_occurrence_order(self):
        inputs = sources()
        inputs['color_sequence'] *= 2
        inputs['sku_descriptions'] = [dict(SKUCode='sku', SKUDescription='one'),
                                      dict(SKUCode='SKU ', SKUDescription='two')]
        inputs['site_descriptions'] = [dict(WHCode='P041', WHDescription='L1'),
                                      dict(WHCode='P041', WHDescription='L2'),
                                      dict(WHCode='SUP', WHDescription='S1'),
                                      dict(WHCode='SUP', WHDescription='S2')]
        inputs['sku_loc_attributes'] *= 2
        inputs['sku_attributes'] = [dict(SKUCode='sku', c3='A'), dict(SKUCode='sku', c3='B')]
        expected = []
        # Independent explicit full row, not a call to the projection helpers.
        for _colour in (0, 1):
            for sku in ('"one"', '"two"'):
                for loc in ('"L1"', '"L2"'):
                    for supplier in ('"S1"', '"S2"'):
                        for _pair in (0, 1):
                            for unit in ('A', 'B'):
                                expected.append(('sku', sku, 'P041', loc, 'SUP', supplier,
                                    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
                                    'Red', '9', '-', '', '13', unit, '11', '7'))
        self.assertEqual(self.project(inputs), expected)
        inputs['bor_with_order_allocation'] *= 2
        self.assertEqual(self.project(inputs), expected + expected)

    def test_missing_and_null_left_joins_remain_null_except_four_isnull_cells(self):
        inputs = sources()
        for name in ('sku_descriptions', 'site_descriptions', 'sku_loc_attributes', 'sku_attributes'):
            inputs[name] = []
        expected = ('sku', None, 'P041', None, 'SUP', None,
                    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
                    'Red', '-', '-', '-', '-', None, None, None)
        self.assertEqual(self.project(inputs), [expected])
        inputs['sku_descriptions'] = [dict(SKUCode='sku', SKUDescription=None)]
        inputs['site_descriptions'] = [dict(WHCode='P041', WHDescription=None)]
        self.assertEqual(self.project(inputs), [expected])
        inputs['bor_with_order_allocation'][0]['SKUCode'] = None
        inputs['sku_descriptions'] = [dict(SKUCode=None, SKUDescription='must not join')]
        self.assertEqual(self.project(inputs)[0][1], None)

    def test_inner_colour_join_filters_and_null_never_matches_null(self):
        inputs = sources()
        inputs['bor_with_order_allocation'] += [bor(DispatchColor='unmatched'), bor(DispatchColor=None)]
        inputs['color_sequence'] += [dict(Color=None, SequenceNo=0)]
        self.assertEqual(len(self.project(inputs)), 1)
        inputs['color_sequence'] = []
        self.assertEqual(self.project(inputs), [])

    def test_site_filters_use_native_case_and_space_matching(self):
        inputs = sources()
        inputs['bor_with_order_allocation'] = [bor(WhCode='p001 '), bor(WhCode='p041 '),
                                               bor(WhCode='OTHER'), bor(WhCode=None)]
        self.assertEqual([r[2] for r in self.project(inputs)], ['p001 ', 'p041 ', 'OTHER', None])
        self.assertEqual([r[2] for r in self.project(inputs, 5)], ['p041 '])
        self.assertEqual([r[2] for r in self.project(inputs, 6)], ['p001 '])

    def test_every_native_order_key_null_position_and_stable_tie(self):
        inputs = sources()
        inputs['color_sequence'] = [dict(Color='Red', SequenceNo=2),
                                    dict(Color='NULLSEQ', SequenceNo=None)]
        rows = [bor(SKUCode='base'), bor(SKUCode='tie'), bor(SKUCode='null-sequence', DispatchColor='NULLSEQ')]
        for field, name in (('DispatchPen', 'pen'), ('OrderGreenUnsatisfiedPercentage', 'green'),
                            ('OrderYellowUnsatisfiedPercentage', 'yellow'),
                            ('OrderRedUnsatisfiedPercentage', 'red'),
                            ('OrderBlackUnsatisfiedPercentage', 'black')):
            rows.append(bor(SKUCode=name, **{field: Decimal('100.00')}))
            rows.append(bor(SKUCode='null-' + name, **{field: None}))
        inputs['bor_with_order_allocation'] = rows
        self.assertEqual([r[0] for r in self.project(inputs)],
            ['null-sequence', 'black', 'red', 'yellow', 'green', 'pen', 'base', 'tie',
             'null-pen', 'null-green', 'null-yellow', 'null-red', 'null-black'])
        self.assertIn('unqualified', report.TIE_POLICY)

    def test_typed_sources_missing_population_columns_and_unsupported_domains(self):
        for source, field, value in (('bor_with_order_allocation', 'SKUCode', 'café'),
                ('sku_attributes', 'SKUCode', 42), ('bor_with_order_allocation', 'Norm', '1'),
                ('bor_with_order_allocation', 'DispatchPen', float('nan')),
                ('bor_with_order_allocation', 'Stock', True), ('color_sequence', 'SequenceNo', '2')):
            with self.subTest(source=source, field=field):
                inputs = sources(); inputs[source][0][field] = value
                with self.assertRaises(ValueError): self.project(inputs)
        inputs = sources(); del inputs['sku_loc_attributes'][0]['c7']
        with self.assertRaisesRegex(ValueError, 'columns missing'): self.project(inputs)
        inputs = sources(); inputs['sku_attributes'] = None
        with self.assertRaisesRegex(ValueError, 'population'): self.project(inputs)
        inputs = sources()
        inputs['bor_with_order_allocation'] = RecordRows(1, lambda: iter([bor()]))
        self.assertEqual(self.project(inputs), self.project())


if __name__ == '__main__':
    unittest.main()
