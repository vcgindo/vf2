"""Complete cell/bag projections; native runtime files remain unqualified."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import unittest

from mta.application import runtime_demand_reports as reports
from mta.row_sequences import RecordRows


def definition(identity):
    values = json.loads((Path(__file__).parent / 'fixtures/runtime_reports_retained_20261019.json').read_bytes())
    return next(row for row in values if row['Id'] == identity)


def rationed():
    # Explicit source field names and distinct values make ordinal mistakes visible.
    return dict(SKUCode='S', SKUName='SKU, name', WhCode='L', WhName='Loc, name',
        Norm=4, VirtualNorm=5, VirtualNodeNorm=6, SpikeThreshold=Decimal('7.00'),
        PSOThreshold=Decimal('8.00'), Stock=9, GIT=10, StockForRationing=11,
        StockForReqCalc=12, TechPen=Decimal('13.00'), TechColor='Red',
        EcoPen=Decimal('15.00'), EcoColor='Green', DispatchPen=Decimal('17.00'),
        DispatchColor='Black', DispatchColorSequence=19, ParentWhCode='P', ParentNorm=25,
        TechPenParent=Decimal('26.00'), TechColorParent='Blue',
        EcoPenParent=Decimal('28.00'), EcoColorParent='Yellow', Req=30,
        AllocatedForVirtualNormReq=31, AllocatedForNormReq=32, AllocatedForSnPReq=33,
        AllocatedForDirectOrders=34, RationedReq=35, PackSize=36,
        RationedCasePacks=37, LeftoverParentStock=38, LeftoverStock=39,
        ParentPackSize=40, IsNormed=1, DirectSpikeOverdue=42, SpikeOverdueAtParent=43,
        PSO=44, RelPSOAndCNR=45, ResidualChildrenSnP=46, SnPToNetOff=47,
        SnPNettedOff=48, ResidualSnP=49, EcoStockForNormReq=50, NormReq=51,
        BlueReq=52, AvgSiblingsNorm=53, AvgChildrenNorm=54,
        ParentStockForNormRationing=55, ParentStockForSnPRationing=56,
        ParentStockForRationing=57, StockPercentageForRationing=58,
        NormPercentReservation=59, ParentStockPercentageForRationing=60,
        ParentNormPercentReservation=61)


def attributes(prefix, **keys):
    return dict(keys, **{'c' + str(n): prefix + str(n) for n in range(1, 16)})


def sources():
    return dict(rationed_report=[rationed()], supplier_dispatch=[],
        site_descriptions=[dict(WHCode='P', WHDescription='Parent, name')],
        sku_loc_attributes=[attributes('C', SKUCode='S', LocCode='L')],
        sku_attributes=[attributes('D', SKUCode='S')],
        location_attributes=[attributes('E', WHCode='L')])


class RuntimeDemandReportTests(unittest.TestCase):
    def test_complete_total_requirement_tuple_preserves_all_107_positions(self):
        original = sources(); before = deepcopy(original)
        actual = list(reports.total_requirements(definition(10), **original))
        expected = ('S', 'SKU name', 'L', 'Loc name', 4, 5, 6, Decimal('7.00'),
            Decimal('8.00'), 9, 10, 11, 12, Decimal('13.00'), 'Red', Decimal('15.00'),
            'Green', Decimal('17.00'), 'Black', 19, None, None, None, 'P', 'Parent name', 25,
            Decimal('26.00'), 'Blue', Decimal('28.00'), 'Yellow', 30, 31, 32, 33, 34,
            35, 36, 37, 38, 39, 40, 1, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52,
            53, 54, 55, 56, 57, 58, 59, 60, 61) + tuple(
                prefix + str(n) for prefix in ('C', 'D', 'E') for n in range(1, 16))
        self.assertEqual(actual, [expected])
        self.assertEqual(len(expected), 107)
        self.assertEqual(original, before)

    def test_supplier_left_bag_overrides_and_required_attribute_bags_do_not_collapse(self):
        value = sources()
        value['supplier_dispatch'] = [
            dict(SKUCode='s ', WHCode='l ', SupplierCode='Q', OriginalReq=0, DispatchReq=2,
                 ReqTopOfRed=70, ReqTopOfYellow=71, ReqTopOfGreen=72),
            dict(SKUCode='S', WHCode='L', SupplierCode=None, OriginalReq=None, DispatchReq=None,
                 ReqTopOfRed=None, ReqTopOfYellow=0, ReqTopOfGreen=73)]
        value['site_descriptions'] += [dict(WHCode='q ', WHDescription='Q,first'),
                                       dict(WHCode='Q', WHDescription='Q,second')]
        value['sku_loc_attributes'].append(attributes('Z', SKUCode='s ', LocCode='l '))
        value['sku_attributes'] *= 2
        actual = list(reports.total_requirements(definition(10), **value))
        self.assertEqual(len(actual), 12)  # (two Q descriptions + one P) * 2 pairs * 2 SKUs
        self.assertEqual([r[20:23] for r in actual], [(70, 71, 72)] * 8 + [(None, 0, 73)] * 4)
        self.assertEqual([(r[23], r[24], r[30], r[35], r[62]) for r in actual],
            [(parent, name, req, rationed, attr) for parent, name, req, rationed in
             [('Q', 'Qfirst', 0, 2), ('Q', 'Qsecond', 0, 2), ('P', 'Parent name', 30, 35)]
             for attr in ('C1', 'Z1') for duplicate in range(2)])
        for key in ('sku_loc_attributes', 'sku_attributes', 'location_attributes'):
            missing = dict(value, **{key: []})
            self.assertEqual(list(reports.total_requirements(definition(10), **missing)), [])

    def test_null_and_empty_supplier_parent_remain_distinct_and_null_keys_do_not_join(self):
        value = sources()
        value['rationed_report'][0].update(SKUName=None, WhName=None)
        value['supplier_dispatch'] = [dict(SKUCode='S', WHCode='L', SupplierCode='',
            OriginalReq=None, DispatchReq=None, ReqTopOfRed=None, ReqTopOfYellow=None, ReqTopOfGreen=None)]
        actual = list(reports.total_requirements(definition(10), **value))[0]
        self.assertEqual((actual[1], actual[3], actual[23], actual[24]), ('', '', '', ''))
        value['rationed_report'][0]['SKUCode'] = None
        value['sku_attributes'][0]['SKUCode'] = None
        value['sku_loc_attributes'][0]['SKUCode'] = None
        self.assertEqual(list(reports.total_requirements(definition(10), **value)), [])

    def test_spike_complete_projection_preserves_duplicates_types_and_input_order(self):
        row = dict(OrderKey=7, CustomerOrderId='A,"order', PartId=2, IsSpike=True,
            IsElephant=False, OriginalQty=9, Qty=3, SKUCode='S', WhCode='L',
            CustomerExpectedDate=date(2026, 10, 26), FirstServicingWhCode=None,
            DueDate=date(2026, 10, 27), IntroDate=None)
        expected = (7, 'A,"order', 2, True, False, 9, 3, 'S', 'L', None, date(2026, 10, 27), None)
        row2 = dict(row, OrderKey=1)
        value = RecordRows(3, lambda: iter([row, row, row2]))
        self.assertEqual(list(reports.spike_orders(dict(definition(7), Id=99), spike_order_data=value)),
                         [expected, expected, (1, *expected[1:])])

    def test_unordered_projection_streams_persisted_rows_without_list_only_assumption(self):
        value = sources(); reads = []
        def rows():
            for i in range(10001):
                reads.append(i)
                yield rationed()
        value['rationed_report'] = RecordRows(10001, rows)
        stream = reports.total_requirements(definition(10), **value)
        self.assertEqual(reads, [])
        next(stream)
        self.assertEqual(reads, [0])
        stream.close()

    def test_changed_queries_missing_sources_columns_and_unqualified_join_keys_deny(self):
        for function, identity, arguments in (
                (reports.total_requirements, 10, sources()),
                (reports.spike_orders, 7, dict(spike_order_data=[]))):
            with self.assertRaises(ValueError):
                function(dict(definition(identity), Query='SELECT different'), **arguments)
        with self.assertRaises(ValueError):
            reports.spike_orders(definition(7), spike_order_data=None)
        with self.assertRaises(ValueError):
            list(reports.spike_orders(definition(7), spike_order_data=[{}]))
        value = sources(); del value['rationed_report'][0]['Stock']
        with self.assertRaises(ValueError):
            list(reports.total_requirements(definition(10), **value))
        value = sources(); del value['sku_loc_attributes'][0]['c15']
        with self.assertRaises(ValueError):
            reports.total_requirements(definition(10), **value)
        value = sources(); value['rationed_report'][0]['SKUCode'] = '\u00e9'
        with self.assertRaisesRegex(ValueError, 'SCALAR_DOMAIN'):
            list(reports.total_requirements(definition(10), **value))

    def test_unqualified_band_columns_belong_to_supplier_native_schema(self):
        root = Path(__file__).parents[1]
        native = json.loads((root / 'baseline/production-state-schema.json').read_text())
        rationed_columns = dict(native['tables']['BPR/vf_RationedReqReport'])
        complete = json.loads((root / 'mta/config/initialization_storage_v1.json').read_text())
        supplier_columns = dict(complete['tables']['complete/BPR/SupplierDispatchReq'])
        self.assertTrue(set(rationed()) <= rationed_columns.keys())
        self.assertTrue(set(reports.RATIONED_FIELDS) <= rationed_columns.keys())
        for name in reports.SUPPLIER_BANDS:
            self.assertNotIn(name, rationed_columns)
            self.assertEqual(supplier_columns[name], 'int')
