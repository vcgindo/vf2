"""Retained order facts survive current-hierarchy changes as in CalculateRoute.sql.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import unittest

from mta.application.r1_input import prepare_r1_current_day
from mta.domain.r1_current_day import (
    RouteNode, route_established_spike_order, route_new_spike_order,
)
from mta.planning.engine import calculate_current_day
from mta.domain.validation import RuleBlocked


def physical(location, parent, rlt):
    return RouteNode(location, True, Decimal(100), Decimal(20), parent, rlt)


def terminal(location='supplier'):
    return RouteNode(location, False, None, None, None, None)


class EstablishedOrderRouteTests(unittest.TestCase):
    def route(self, nodes, *, first='retired', due=date(2026, 4, 8), source='leaf'):
        return route_established_spike_order(
            order_id='order', sku_code='SKU', source_location_code=source,
            first_servicing_location_code=first, due_date=due, nodes=nodes)

    def test_existing_on_path_first_service_still_stops_there(self):
        nodes = (physical('leaf', 'parent', 2), physical('parent', 'supplier', 3), terminal())
        result = self.route(nodes, first='parent')
        self.assertEqual(result.first_servicing_location_code, 'parent')
        self.assertEqual(result.due_date, date(2026, 4, 8))
        self.assertEqual(result.route, (
            dict(location_code='leaf', child_location_code=None, due_date='2026-04-08'),
            dict(location_code='parent', child_location_code='leaf', due_date='2026-04-06')))
        self.assertEqual(len(self.route(nodes, first='leaf').route), 1)

    def test_retired_first_service_uses_current_path_and_retains_historical_fields(self):
        nodes = (physical('leaf', 'parent', 2), physical('parent', 'supplier', 3), terminal())
        before = deepcopy(nodes)
        result = self.route(nodes)
        self.assertEqual(result.first_servicing_location_code, 'retired')
        self.assertEqual(result.due_date, date(2026, 4, 8))
        self.assertEqual(result.route[-1], dict(
            location_code='supplier', child_location_code='parent', due_date='2026-04-03'))
        changed = self.route((replace(nodes[0], rlt_to_parent_days=4), *nodes[1:]))
        self.assertEqual(changed.due_date, result.due_date)
        self.assertEqual(changed.route[-1]['due_date'], '2026-04-01')
        zero_edge = self.route((replace(nodes[0], rlt_to_parent_days=0), *nodes[1:]))
        self.assertEqual(zero_edge.route[-1]['due_date'], '2026-04-05')
        self.assertEqual(nodes, before)

    def test_first_service_still_exists_on_another_branch(self):
        nodes = (physical('leaf', 'parent', 2), physical('parent', 'supplier', 3),
                 physical('old-branch', 'supplier', 7), terminal())
        result = self.route(nodes, first='old-branch')
        self.assertEqual(result.first_servicing_location_code, 'old-branch')
        self.assertEqual([r['location_code'] for r in result.route], ['leaf', 'parent', 'supplier'])

    def test_historical_first_service_uses_selected_sql_comparison_without_rewriting_it(self):
        nodes = (physical('leaf', 'parent', 2), physical('parent', 'supplier', 3), terminal())
        for historical in ('parent', 'PARENT', 'parent '):
            with self.subTest(first=historical):
                result = self.route(nodes, first=historical)
                self.assertEqual([r['location_code'] for r in result.route], ['leaf', 'parent'])
                self.assertEqual(result.first_servicing_location_code, historical)
                self.assertEqual(result.route[-1]['due_date'], '2026-04-06')

    def test_actual_obsolete_location_examples_keep_exact_backward_dates(self):
        for first, source, due, nodes, expected in (
            ('0000_Discontinued', 'P035_1002', date(2026, 3, 11),
             (physical('P035_1002', 'CDC2', 10), physical('CDC2', 'P001', 48),
              physical('P001', 'P001_Prod', 1), terminal('P001_Prod')),
             ['2026-03-11', '2026-03-01', '2026-01-12', '2026-01-11']),
            ('0000_Discontinued', 'CDC1', date(2026, 2, 26),
             (physical('CDC1', 'CDC2', 13), physical('CDC2', 'P001', 48),
              physical('P001', 'P001_Prod', 1), terminal('P001_Prod')),
             ['2026-02-26', '2026-02-13', '2025-12-27', '2025-12-26']),
            ('0000_HighInventory', 'P001', date(2026, 3, 13),
             (physical('P001', 'P001_Prod', 1), terminal('P001_Prod')),
             ['2026-03-13', '2026-03-12']),
        ):
            with self.subTest(first=first, source=source):
                result = self.route(nodes, first=first, source=source, due=due)
                self.assertEqual([r['due_date'] for r in result.route], expected)
                self.assertEqual(result.first_servicing_location_code, first)
                self.assertEqual(result.due_date, due)

    def test_retained_off_path_fixture_reaches_requirement_and_report_producers(self):
        path = Path(__file__).resolve().parents[1] / 'mta/fixtures/r1_boundary_historical_service_off_path.json'
        raw = json.loads(path.read_text(encoding='utf-8'))
        before = deepcopy(raw)
        prepared = prepare_r1_current_day(raw)
        self.assertEqual([r['location_code'] for r in prepared.routes],
                         ['R1-C', 'R1-Q', 'R1-GP', 'R1-SUP'])
        self.assertEqual([r['due_date'] for r in prepared.routes],
                         ['2026-01-21', '2026-01-19', '2026-01-16', '2026-01-10'])
        self.assertTrue(all(r['first_servicing_location_code'] == 'R1-P' for r in prepared.routes))
        due = {r['location_code']: Decimal(r['routed_due_spike']) for r in prepared.track_a['nodes']}
        self.assertEqual(due, {'R1-C': Decimal(0), 'R1-GP': Decimal(50),
                               'R1-P': Decimal(0), 'R1-Q': Decimal(0)})
        output = calculate_current_day(raw)
        self.assertEqual(len(output['r1_order_route']), 4)
        self.assertTrue(output['r1_requirement'])
        self.assertIn('r1_bor', output)
        self.assertIn('r1_pick_list', output)
        self.assertEqual(raw, before)

    def test_new_spike_still_selects_its_own_first_service_and_due_date(self):
        nodes = (physical('leaf', 'parent', 2), physical('parent', 'supplier', 3), terminal())
        result = route_new_spike_order(business_date=date(2026, 4, 8), order_id='new',
            sku_code='SKU', source_location_code='leaf', quantity=Decimal(30),
            customer_expected_date=None, nodes=nodes)
        self.assertEqual(result.first_servicing_location_code, 'supplier')
        self.assertEqual(result.due_date, date(2026, 4, 13))

    def test_invalid_graphs_and_missing_historical_identity_are_not_waived(self):
        for nodes in (
            (physical('leaf', 'supplier', 1), physical('leaf', 'supplier', 1), terminal()),
            (physical('leaf', 'leaf', 1),),
            (physical('leaf', 'missing', 1),),
            (physical('leaf', 'supplier', -1), terminal()),
            (physical('leaf', None, None),),
            (terminal(),),
        ):
            with self.subTest(nodes=nodes), self.assertRaises(ValueError):
                self.route(nodes)
        with self.assertRaises(ValueError):
            self.route((physical('leaf', 'supplier', 1), terminal()), first='')

    def test_established_route_source_depth_boundary_is_explicit(self):
        nodes = tuple(physical(f'L{i}', f'L{i + 1}', 0) for i in range(100)) + (terminal('L100'),)
        self.assertEqual(len(self.route(nodes, source='L0', first='L99').route), 100)
        with self.assertRaisesRegex(RuleBlocked, 'R1_ROUTE_SOURCE_LIMIT'):
            self.route(nodes, source='L0', first='retired')

    def test_new_route_cannot_silently_exceed_the_same_source_limit(self):
        nodes = tuple(physical(f'L{i}', f'L{i + 1}', 0) for i in range(100)) + (terminal('L100'),)
        kwargs = dict(business_date=date(2026, 4, 8), order_id='new', sku_code='SKU',
                      source_location_code='L0', quantity=Decimal(30), customer_expected_date=None)
        with self.assertRaisesRegex(RuleBlocked, 'R1_ROUTE_SOURCE_LIMIT'):
            route_new_spike_order(**kwargs, nodes=nodes)
        at_boundary = nodes[:99] + (terminal('L99'),)
        self.assertEqual(len(route_new_spike_order(**kwargs, nodes=at_boundary).route), 100)


if __name__ == '__main__':
    unittest.main()
