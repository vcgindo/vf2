"""Production policy admission must agree with the native calculation consumers.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'policy-contract-unit-only')
import django
django.setup()

from mta.application.r1_additional_master import validate_policy_rows
from mta.application.r1_phase_in import collect_phase_in, phase_start_percent
from mta.domain.demand import ThresholdPolicy, classify_spike
from mta.domain.validation import percent
from mta.mdm.initialization_contract import scalar_configuration
from mta.runtime import production_preflight as preflight
from mta.serialization import digest
from tests.initialization_input_fixture import encoded
from tests.production_daily_fixture import initialized_input
from tests.test_h3_daily_integration import coupled, frame


def policy(**changes):
    return dict(spike_high='33.33', spike_low='100.00', pso_high='66.67',
                pso_low='0', spike_override='1000000.00', pso_override='33.00', **changes)


class PolicyContractIntegrityTests(unittest.TestCase):
    def test_large_demand_multiplier_classification_and_both_norm_branches(self):
        value = ThresholdPolicy.from_mapping(policy())
        self.assertEqual(value.thresholds(Decimal(2)), (Decimal('1000000.00'), Decimal('33.00')))
        self.assertEqual(value.thresholds(Decimal(3)), (Decimal('1000000.00'), Decimal('33.00')))
        self.assertFalse(classify_spike(Decimal(30000), Decimal(3), value))
        self.assertTrue(classify_spike(Decimal(30001), Decimal(3), value))
        defaults = policy(); defaults.update(spike_override=None, pso_override=None)
        value = ThresholdPolicy.from_mapping(defaults)
        self.assertEqual(value.thresholds(Decimal(2)), (Decimal('100.00'), Decimal(0)))
        self.assertEqual(value.thresholds(Decimal(3)), (Decimal('33.33'), Decimal('66.67')))
        with self.assertRaises(ValueError):
            percent(Decimal(101))  # True bounded percentages retain their contract.

    def test_invalid_thresholds_are_denied_by_both_consumers_and_early_admission(self):
        for invalid in ('-1', 'NaN', 'Infinity', 'bad-number', '100000000000000',
                        '0.0000001', True, 1.1, None):
            with self.subTest(value=invalid):
                row = dict(sku_code='SKU', location_code='LOC', policy=policy())
                row['policy']['spike_high'] = invalid
                with self.assertRaises(ValueError):
                    ThresholdPolicy.from_mapping(row['policy'])
                profile = initialized_input()['configuration']
                profile['calculation']['policies'] = [row]
                with self.assertRaises(ValueError):
                    scalar_configuration(profile)
                requirements = preflight.Requirements('day')
                preflight.configuration(requirements, profile, None)
                self.assertTrue(any(item['path'].endswith('/policies') for item in requirements.issues))

    def test_four_default_raw_policy_and_null_override_keep_values_and_order(self):
        rows = [dict(sku_code='SKU', location_code=loc, policy=policy()) for loc in ('B', 'A')]
        rows[0]['policy'] = {key: value for key, value in rows[0]['policy'].items()
                             if not key.endswith('_override')}
        rows[1]['policy'].update(spike_override=None, pso_override=None)
        before = deepcopy(rows)
        validate_policy_rows(rows)
        self.assertEqual(rows, before)
        with self.assertRaises(ValueError):
            ThresholdPolicy.from_mapping(rows[0]['policy'])  # Runtime still needs resolved overrides.
        for invalid in (rows + [deepcopy(rows[0])], deepcopy(rows)):
            if len(invalid) == 2:
                invalid[1]['policy']['spike_low'] = '99'
            with self.assertRaises(ValueError):
                validate_policy_rows(invalid)

    def test_phase_decimal_text_matches_float_for_an_active_row_without_mutation(self):
        state = dict(phase_in_requests=[], phase_in_norms=[], phase_map=[dict(
            PhaseOutSKUCode='OLD', WhCode='L', PhaseInSKUCode='NEW', PhaseOutSKUOrigNorm=10)],
            phase_in=[dict(SKUCode='NEW', WhCode='L', PhaseOutSKUOrigNorm=10, TargetNorm=10,
                OldNorm=0, NewNorm=0, PhaseInStartDate='2026-04-07', LastProcessedDate='2026-04-07')],
            dbm_master=[dict(SKUCode='OLD', WhCode='L', Norm=0)], importer_master=[], phase_out=[])
        before = deepcopy(state)
        text = collect_phase_in(state, '2026-04-08', from_ui=True, start_percent='66.67')
        numeric = collect_phase_in(state, '2026-04-08', from_ui=True, start_percent=66.67)
        self.assertEqual(text, numeric)
        self.assertEqual(text['phase_in'][0]['NewNorm'], 10)
        self.assertEqual(state, before)
        for invalid in (-1, 101, True, 'NaN', 'Infinity', 'bad-number'):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                phase_start_percent(invalid)

    def test_phase_invalid_configuration_is_denied_before_the_daily_producer(self):
        for invalid in ('-1', '101', 'NaN', True):
            profile = initialized_input()['configuration']
            profile['delivery']['controls']['start_percent'] = invalid
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                scalar_configuration(profile)
            requirements = preflight.Requirements('day')
            preflight.configuration(requirements, profile, None)
            self.assertTrue(any(item['path'].endswith('/start_percent') for item in requirements.issues))

    def test_approved_description_diagnostic_uses_the_same_importer_domain(self):
        for character in ('\u00a0', '\u00ae', '\u2013', '\u03a9'):
            value = initialized_input()
            value['masters']['importer']['SKUDescriptionTbl'][0]['SKUDescription'] = 'Original' + character
            raw, sha, arguments = encoded(value)
            with patch('django.db.backends.utils.CursorWrapper.execute', side_effect=AssertionError('No SQL')):
                report = preflight.initialization(raw, sha, **arguments)
            issues = [item for item in report['issues'] if item['code'] == 'MASTER_TEXT_DOMAIN_UNQUALIFIED'
                      and item['path'].endswith('/SKUDescription')]
            self.assertEqual(bool(issues), character == '\u03a9')

    def test_supported_complete_native_outputs_are_unchanged_for_both_moq_formats(self):
        expected = {'WithDestLoc': '92f8110fd6e75bb7d6025972ae508db9b7f05af9857fe9e59109ca89c13a7127',
                    'WithoutDestLoc': '467f7e2d68646dd2c95579eb341ff672ce9a209ad686b817396972536d7504ff'}
        for fmt, checksum in expected.items():
            value = frame(fmt)
            with self.subTest(fmt=fmt), patch('django.db.backends.utils.CursorWrapper.execute', side_effect=AssertionError('No SQL')):
                result, _ = coupled(value['profile'], value['opening']['state'], '2037-04-09', '2037-04-10', fmt=fmt)
            self.assertEqual(digest(result), checksum)

    def test_large_multiplier_reaches_complete_native_flow_and_track_a_consumer(self):
        value = frame(); profile = value['profile']; prior = value['opening']['state']
        for row in profile['calculation']['policies']:
            row['policy'] = policy()
        for row in prior['importer']['SkuLocAttributeData']:
            row.update(SpikeThreshold=1000000.0, PSOThreshold=33.0)
        profile['delivery']['controls']['start_percent'] = '66.67'
        before = digest(prior)
        with patch('django.db.backends.utils.CursorWrapper.execute', side_effect=AssertionError('No SQL')):
            result, _ = coupled(profile, prior, '2037-04-09', '2037-04-10')
        self.assertEqual(digest(prior), before)
        closing = result['ClosingState'][0]
        for family, name in (('bpr', 'DailyConsumption'), ('dbm', 'DBMMaster'),
                             ('complete', 'LogisticPickList'), ('btr', 'RationingHistory')):
            self.assertTrue(closing[family][name], (family, name))


if __name__ == '__main__':
    unittest.main()
