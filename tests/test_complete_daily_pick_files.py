"""Pure required Pick file projections, with explicit native stage fixtures."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import unittest

from mta.application import complete_daily_pick_files as files


def logistic(**overrides):
    row = dict(ParentWHCode='P', WHCode='W', LogisticLocation='L', TruckCount=1,
        VehicleName='V', TransportLoadType='Full', DispatchColor='Black', SKUCode='S',
        ColorWiseAlloction=2, TotalWeight=Decimal('1.250'), TotalVolume=Decimal('2.000'),
        IsTruckFormed=True)
    row.update(overrides)
    return row


def remaining(**overrides):
    row = dict(ParentWHCode='P', WHCode='W', LogisticLocation='L', DispatchColor='Black',
        SKUCode='S', ColorWiseAlloction=2, TotalWeight=Decimal('1.250'), TotalVolume=Decimal('2.000'))
    row.update(overrides)
    return row


class PickFileTests(unittest.TestCase):
    def test_logistic_distinct_metadata_groups_qty_without_colour(self):
        rows = [logistic(), logistic(), logistic(DispatchColor='Red', ColorWiseAlloction=3)]
        before = deepcopy(rows)
        report = files.logistic_pick_list_report(rows)
        data = report['resultsets'][1]
        self.assertEqual(len(data['rows']), 2)
        self.assertEqual([row[6] for row in data['rows']], ['Black', 'Red'])
        self.assertTrue(all(row[8:] == (7, Decimal('3.750'), Decimal('6.000')) for row in data['rows']))
        self.assertEqual(report['transient_rows'][0]['SumOfPikedQty'], 7)
        self.assertEqual(data['fields'][3], 'Vehicle Counter')
        self.assertEqual(rows, before)

    def test_null_update_keys_leave_all_payload_null(self):
        for field in files.LOGISTIC_GROUP:
            report = files.logistic_pick_list_report([logistic(**{field: None})])
            self.assertEqual(report['resultsets'][1]['rows'][0][8:], (None, None, None))
        for field in files.DETAIL_GROUP:
            report = files.remaining_quantity_details_report([remaining(**{field: None})])
            self.assertEqual(report['resultsets'][1]['rows'][0][5:], (None, None, None))

    def test_null_metadata_not_in_update_keys_still_gets_totals(self):
        report = files.logistic_pick_list_report([logistic(VehicleName=None, DispatchColor=None)])
        self.assertEqual(report['resultsets'][1]['rows'][0][8:], (2, Decimal('1.250'), Decimal('2.000')))

    def test_isnull_logistic_qty_and_plain_sum_details_are_different(self):
        row = dict(ColorWiseAlloction=None, TotalWeight=None, TotalVolume=None)
        picked = files.logistic_pick_list_report([logistic(**row)])['resultsets'][1]['rows'][0]
        leftover = files.remaining_quantity_details_report([remaining(**row)])['resultsets'][1]['rows'][0]
        self.assertEqual(picked[8:], (0, Decimal('0.000'), Decimal('0.000')))
        self.assertEqual(leftover[5:], (None, Decimal('0.000'), Decimal('0.000')))

    def test_details_distinct_colours_receive_same_group_total(self):
        rows = [remaining(), remaining(), remaining(DispatchColor='Red', ColorWiseAlloction=3)]
        data = files.remaining_quantity_details_report(rows)['resultsets'][1]
        self.assertEqual(len(data['rows']), 2)
        self.assertTrue(all(row[5:] == (7, Decimal('3.750'), Decimal('6.000')) for row in data['rows']))
        self.assertEqual(data['fields'][-1], 'RemainingTotalVol')

    def test_summary_groups_nulls_and_promotes_decimal_sum(self):
        rows = [remaining(ParentWHCode=None), remaining(ParentWHCode=None, WHCode='W2',
            SKUCode='S2', TotalWeight=None)]
        data = files.remaining_quantity_summary_report(rows)['resultsets'][1]
        self.assertEqual(data['rows'], [(None, 'L', Decimal('1.250'), Decimal('4.000'))])
        self.assertEqual(data['types'][-2:], ('decimal(38,3)', 'decimal(38,3)'))

    def test_transport_counts_false_but_not_null_and_not_distinct_trucks(self):
        data = files.transport_requirement_summary_report([
            logistic(), logistic(), logistic(IsTruckFormed=False), logistic(IsTruckFormed=None),
            logistic(VehicleName=None, IsTruckFormed=None)])['resultsets'][1]
        self.assertEqual(data['rows'], [('P', 'L', 'V', 'Full', 3), ('P', 'L', None, 'Full', 0)])
        self.assertEqual(data['fields'][-1], '')

    def test_headers_are_separate_unnamed_sets_and_empty_data_is_explicit(self):
        reports = files.project_reports(logistic_pick_list=[], pick_list_data_for_truck_formation=[])
        for key, report in reports.items():
            header, data = report['resultsets']
            self.assertEqual(header['fields'], ('',) * len(header['rows'][0]))
            self.assertEqual(data['rows'], [])
            self.assertEqual(len(header['rows'][0]), len(data['fields']))
            self.assertEqual(report['scratch_truncate_before'], key in ('logistic', 'remaining_details'))
            self.assertEqual(report['script_marker'] is not None, key in ('logistic', 'remaining_details'))
        self.assertEqual(reports['logistic']['resultsets'][0]['rows'][0][7], 'SKUCode')
        self.assertEqual(reports['remaining_details']['resultsets'][0]['rows'][0][4], 'SKU Code')
        with self.assertRaises(ValueError):
            files.project_reports(logistic_pick_list=None, pick_list_data_for_truck_formation=[])

    def test_no_sort_tie_break_or_input_mutation(self):
        rows = [logistic(SKUCode='Z'), logistic(SKUCode='A')]
        before = deepcopy(rows)
        data = files.logistic_pick_list_report(rows)['resultsets'][1]['rows']
        self.assertEqual([r[7] for r in data], ['Z', 'A'])
        self.assertEqual(rows, before)

    def test_exact_native_type_scale_and_visible_unqualified_domains(self):
        for override in (dict(TotalWeight=1.25), dict(TotalWeight=Decimal('1.25')),
                         dict(ColorWiseAlloction=True)):
            with self.assertRaises(files.UnqualifiedPickFileInput):
                files.logistic_pick_list_report([logistic(**override)])
        with self.assertRaises(files.UnqualifiedPickFileInput):
            files.logistic_pick_list_report([logistic(), logistic(SKUCode='s ')])
        with self.assertRaises(ValueError):
            files.logistic_pick_list_report([logistic(SKUCode='é')])
        with self.assertRaises(files.UnqualifiedPickFileInput):
            files.logistic_pick_list_report([logistic(ColorWiseAlloction=2**31-1), logistic()])
        with self.assertRaises(files.UnqualifiedPickFileInput):
            files.transport_requirement_summary_report([logistic(IsTruckFormed=1)])

    def test_signed_native_quantities_are_not_repaired(self):
        data = files.remaining_quantity_details_report([remaining(ColorWiseAlloction=-2,
            TotalWeight=Decimal('-1.250'))])['resultsets'][1]['rows']
        self.assertEqual(data[0][5:], (-2, Decimal('-1.250'), Decimal('2.000')))

    def test_source_pins_and_literal_headers_match_registered_canonical_sources(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / 'baseline/manifest.json').read_text())
        registered = {r['path']: r['sha256'] for r in manifest['engine_sources']}
        source = Path('F:/VFlow_Local/local-runtime/mta-engine')
        reports = files.project_reports(logistic_pick_list=[], pick_list_data_for_truck_formation=[])
        for key, (relative, pin) in files.SOURCES.items():
            path = source / relative
            self.assertEqual(registered[path.as_posix()], pin)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), pin)
            text = path.read_text(encoding='cp1252')
            for literal in reports[key]['resultsets'][0]['rows'][0]:
                self.assertIn("'" + literal + "'", text)


if __name__ == '__main__':
    unittest.main()
