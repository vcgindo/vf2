"""Exact scope of the approved supplier text availability contract."""
from copy import deepcopy
import unittest

from mta.application import operational_bor as native
from mta.application import production_output_policy as policy


def core():
    return {field['name']: ('S' if field['sql_type'].startswith('nvarchar')
                            else '0.00' if field['sql_type'].startswith('decimal') else 0)
            for field in native.NATIVE_SCHEMAS['BORWithOrderAllocation']}


class ApprovedOutputPolicyTests(unittest.TestCase):
    def test_only_precise_text_roster_is_nullable_and_known_values_survive(self):
        row = core()
        row['SKULocAtt04'] = 'known source value'
        row['SKULocAtt15'] = ''
        frozen = deepcopy(row)
        result = policy.bor_oa([row, row], policy.contract())
        self.assertEqual(row, frozen)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['SKULocAtt04'], 'known source value')
        self.assertEqual(result[0]['SKULocAtt15'], '')
        self.assertTrue(all(result[0][name] is None for name in policy.ATTRIBUTES
                            if name not in ('SKULocAtt04', 'SKULocAtt15')))
        self.assertEqual(len(result[0]), 41)
        for mutate in (lambda x: x.pop('Norm'), lambda x: x.update(Norm=None),
                       lambda x: x.update(SKULocAtt16=None),
                       lambda x: x.update(SKULocAtt01=3),
                       lambda x: x.update(SKULocAtt01='😀' * 26)):
            bad = deepcopy(row)
            mutate(bad)
            with self.assertRaises(ValueError):
                policy.bor_oa([bad], policy.contract())

    def test_policy_requires_exact_version_and_roster(self):
        for key in ('schema', 'normal_bor', 'boroa_text'):
            bad = policy.contract()
            bad.pop(key)
            with self.assertRaises(ValueError):
                policy.bor_oa([], bad)

    def test_own_history_preserves_text_and_original_retention_order(self):
        row = core()
        row['SKULocAtt04'] = 'retained'
        old = policy.bor_oa([row], policy.contract())[0]
        previous = [dict(old, ReportDate='2037-04-08'),
                    dict(old, ReportDate='2037-04-09'),
                    dict(old, ReportDate='2037-04-09')]
        result = policy.bor_oa_history(opening=previous, current=[core()],
            business_date='2037-04-10', horizon=2, policy=policy.contract())
        self.assertEqual([r['ReportDate'] for r in result], ['2037-04-09'] * 2 + ['2037-04-10'])
        self.assertEqual([r['SKULocAtt04'] for r in result], ['retained', 'retained', None])
        self.assertEqual(len(result[0]), 42)
        with self.assertRaises(ValueError):
            policy.bor_oa_history(opening=[dict(core(), ReportDate='2037-04-09')],
                current=[], business_date='2037-04-10', horizon=2, policy=policy.contract())
