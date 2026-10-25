from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.application.production_source_inputs import SCHEMA
from mta.application.stage_calculation_sources import CalculationSources
from mta.runtime import scope_bpr_histories as history
from tests.test_operational_bor import bor_row, rrr_row


class ScopeBprHistoryTests(unittest.TestCase):
    def fixture(self):
        values = dict(BORWithOrderAllocation=[bor_row(), bor_row()],
            RRR_OrderAllocation=[rrr_row(), rrr_row()], AllocatedOrders=[], BOROARequirement=[])
        prior = {history.NAMES[0]: [dict(bor_row(), ReportDate=d) for d in
            ('2026-10-22', '2026-10-23', '2026-10-23', '2026-10-24')],
            history.NAMES[1]: [dict(rrr_row(), ReportDate=d) for d in
            ('2026-10-22', '2026-10-23', '2026-10-23', '2026-10-24')]}
        return values, prior, dict(bor_history_horizon=2, rrr_history_horizon=2)

    def test_canonical_cutoff_replaces_today_and_preserves_duplicates_nulls_order(self):
        values, prior, policy = self.fixture()
        before = deepcopy((values, prior, policy))
        result = history.project(values, prior, business_date='2026-10-24', policy=policy, source_schema=SCHEMA)
        for current, name in zip(('BORWithOrderAllocation', 'RRR_OrderAllocation'), history.NAMES):
            self.assertEqual(result[name], prior[name][1:3] +
                [dict(row, ReportDate='2026-10-24') for row in values[current]])
        self.assertEqual((values, prior, policy), before)
        self.assertEqual(result['AllocatedOrders'], values['AllocatedOrders'])

    def test_missing_or_already_completed_history_is_not_defaulted(self):
        values, prior, policy = self.fixture()
        for changed in ({}, {history.NAMES[0]: []}):
            with self.assertRaises(ValueError):
                history.project(values, changed, business_date='2026-10-24', policy=policy, source_schema=SCHEMA)
        for changed in ({}, {'bor_history_horizon': 2}):
            with self.assertRaises(ValueError):
                history.project(values, prior, business_date='2026-10-24', policy=changed, source_schema=SCHEMA)
        with self.assertRaisesRegex(ValueError, 'once'):
            history.project(dict(values, **{history.NAMES[0]: []}), prior,
                business_date='2026-10-24', policy=policy, source_schema=SCHEMA)

    def test_complete_sources_uses_exact_predecessor_and_does_not_write(self):
        values, prior, policy = self.fixture()
        sources = CalculationSources('a'*64, [], [], None, values)
        parent = SimpleNamespace(status='SUCCEEDED', business_date=date(2026,10,23))
        run = SimpleNamespace(predecessor_id='parent', predecessor=parent, business_date=date(2026,10,24))
        opening = dict(production_report_opening=None, production_report_policy=policy, production_report_schema=SCHEMA)
        with patch('mta.runtime.production_report_storage.read', side_effect=lambda p,n: prior[n]) as read:
            completed = history.complete_sources(run, sources, opening)
            self.assertEqual([call.args for call in read.call_args_list], [(parent,n) for n in history.NAMES])
        self.assertIsNot(completed, sources)
        self.assertEqual(sources.production_reports, values)
        self.assertEqual(len(completed.production_reports[history.NAMES[0]]), 4)
        with patch('mta.runtime.production_report_storage.read', side_effect=ValueError('history unavailable')):
            with self.assertRaisesRegex(ValueError, 'history unavailable'):
                history.complete_sources(run, sources, opening)

    def test_initial_and_successor_openings_cannot_be_substituted(self):
        values, prior, policy = self.fixture()
        sources = CalculationSources('a'*64, [], [], None, values)
        run = SimpleNamespace(predecessor_id=None, business_date=date(2026,10,24))
        opening = dict(production_report_opening=prior, production_report_policy=policy, production_report_schema=SCHEMA)
        with self.assertRaisesRegex(ValueError, 'fresh'):
            history.complete_sources(run, sources, opening)
        opening['production_report_opening'] = {n: [] for n in history.NAMES}
        result = history.complete_sources(run, sources, opening)
        self.assertEqual(len(result.production_reports[history.NAMES[0]]), 2)
        run.predecessor_id = 'parent'
        with self.assertRaisesRegex(ValueError, 'own persisted'):
            history.complete_sources(run, sources, opening)

    def test_expanded_history_preserves_declared_text(self):
        from mta.application import production_output_policy as expanded
        values, prior, policy = self.fixture()
        contract = expanded.contract()
        values['BORWithOrderAllocation'] = expanded.bor_oa(
            [dict(row, SKULocAtt01='retained text') for row in values['BORWithOrderAllocation']], contract)
        prior[history.NAMES[0]] = []
        result = history.project(values, prior, business_date='2026-10-24',
            policy=dict(policy, output_contract=contract), source_schema=expanded.SOURCE_SCHEMA)
        self.assertEqual([row['SKULocAtt01'] for row in result[history.NAMES[0]]], ['retained text']*2)


if __name__ == '__main__':
    unittest.main()
