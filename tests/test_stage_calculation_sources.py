"""Real native producer-to-consumer boundary, without persisted scope claims."""
from copy import deepcopy
import unittest

from tests import test_h3_daily_integration as coupled
from mta.application.stage_calculation_sources import capture, capture_bpr
from mta.application.operational_capture import CAPTURE_POLICY, capture_rows
from mta.presentation.fulfillment import routes_for_orders
from mta.presentation.pick_storage import selected_bands
from mta.presentation.production_reports import current
from mta.serialization import digest


class CalculationSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frame = coupled.frame()
        cls.profile = frame['profile']
        prior = deepcopy(frame['opening']['state'])
        cls.opening = dict(supplier=deepcopy(prior['supplier']),
            production_report_policy=dict(bor_history_horizon=90, rrr_history_horizon=90))
        day = coupled.supplied_day('2037-04-10')['day']
        frozen = coupled.captured(prior, 'WithDestLoc')
        day.update(raw_master=coupled.compose(frozen, coupled.nms_master_raw(prior),
                    last_run_date='2037-04-09'), exclusions=[],
            supplier_feeds=coupled.complete_feeds(frozen, prior),
            production_report_policy=cls.opening['production_report_policy'])
        coupled.replace_working_inputs(frozen, prior, day, None)
        cls.phase_inputs = deepcopy((prior, day, cls.profile))
        cls.output = coupled.calculate_day(prior, '2037-04-09', day, cls.profile,
            'scoped-consumer-component',
            lambda source, **owned: (coupled.calculate_current_day(
                source, defer_pick=True, **owned), 'scoped-consumer-component'),
            native_daily=True)

    def test_real_bpr_cut_has_all_terminal_calculation_consumers_without_dbm_btr(self):
        from mta.application.native_output_contracts import native_assignments
        from mta.application import production_output_policy
        from mta.temporal import chain
        prior, day, profile = deepcopy(self.phase_inputs)
        profile['operational_sources'] = CAPTURE_POLICY
        with native_assignments(True):
            prepared = chain.prepare_day(prior, '2037-04-09', day, profile,
                'scoped-consumer-component',
                lambda source, **owned: (coupled.calculate_current_day(
                    source, defer_pick=True, **owned), 'scoped-consumer-component'),
                native_daily=True)
            bpr = chain.produce_bpr(prepared)
            expanded = dict(self.opening,
                production_report_schema=production_output_policy.SOURCE_SCHEMA,
                production_report_policy=dict(self.opening['production_report_policy'],
                    output_contract=production_output_policy.contract()))
            for opening in (self.opening, expanded):
                with self.subTest(schema=opening.get('production_report_schema')):
                    actual = capture_bpr(bpr, opening)
                    self.assertEqual(actual, capture(self.output, profile, opening))
                    self.assertTrue(actual.operational['requirement_bands'])
                    if opening is expanded:
                        self.assertTrue(actual.production_reports['SupplierDispatchReq'])
        self.assertNotIn('dbm-imported', bpr.completed_boundaries)
        self.assertNotIn('btr-insights', bpr.completed_boundaries)
        bpr.context.native_daily = False
        with self.assertRaisesRegex(ValueError, 'native BPR phase'):
            capture_bpr(bpr, self.opening)

    def test_all_actual_consumers_match_existing_publication_projections(self):
        output = deepcopy(self.output)
        before = deepcopy(output)
        profile = dict(self.profile, operational_sources=CAPTURE_POLICY)
        actual = capture(output, profile, self.opening)
        calculated = output['CalculationOutputs']
        self.assertEqual(actual.calculation_digest, digest(calculated))
        self.assertEqual(actual.pick_bands, selected_bands(calculated))
        self.assertEqual(actual.routes, routes_for_orders(calculated,
            output['ClosingState'][0]['orders']['SpikeOrderData']))
        self.assertEqual(actual.operational, capture_rows(calculated))
        self.assertEqual(actual.production_reports, current(output, self.opening))
        self.assertTrue(actual.pick_bands)
        self.assertTrue(actual.routes)
        self.assertTrue(actual.production_reports['AllocatedOrders'])
        self.assertEqual(output, before)
        bags = [actual.pick_bands, actual.routes, *actual.operational.values(),
                *actual.production_reports.values()]
        self.assertTrue(all(not isinstance(value, (dict, list, tuple))
            for rows in bags for row in rows for value in row.values()))

    def test_absent_opt_ins_are_not_invented_empty_populations(self):
        profile = dict(self.profile)
        profile.pop('operational_sources', None)
        actual = capture(self.output, profile, {})
        self.assertIsNone(actual.operational)
        self.assertIsNone(actual.production_reports)
        with self.assertRaisesRegex(ValueError, 'Unsupported operational'):
            capture(self.output, dict(profile, operational_sources='unknown'), {})

    def test_missing_or_duplicate_required_capabilities_keep_original_errors(self):
        for capability in ('r1_ration_bifurcation', 'r1_order_route',
                           'r1_requirement_band', 'r1_allocated_orders'):
            for duplicate in (False, True):
                output = deepcopy(self.output)
                source = next(r for r in output['CalculationOutputs']
                              if r['capability'] == capability)
                if duplicate:
                    output['CalculationOutputs'].append(deepcopy(source))
                else:
                    output['CalculationOutputs'].remove(source)
                with self.subTest(capability=capability, duplicate=duplicate), \
                        self.assertRaises(ValueError):
                    capture(output, dict(self.profile, operational_sources=CAPTURE_POLICY),
                            self.opening)

    def test_duplicate_occurrences_and_original_calculation_identity_survive(self):
        output = deepcopy(self.output)
        for capability in ('r1_ration_bifurcation', 'r1_order_route'):
            rows = next(r['rows'] for r in output['CalculationOutputs']
                        if r['capability'] == capability)
            rows.insert(1, deepcopy(rows[0]))
        actual = capture(output, self.profile, self.opening)
        self.assertEqual(actual.pick_bands[0], actual.pick_bands[1])
        self.assertEqual(actual.routes[0], actual.routes[1])
        self.assertEqual(actual.calculation_digest, digest(output['CalculationOutputs']))
        self.assertNotEqual(actual.calculation_digest, digest(self.output['CalculationOutputs']))

    def test_other_report_boundaries_are_not_reinterpreted_as_native_sources(self):
        output = dict(self.output)
        output.pop('_ReportBoundary')
        with self.assertRaisesRegex(ValueError, 'native report boundary'):
            capture(output, self.profile, self.opening)


if __name__ == '__main__':
    unittest.main()
