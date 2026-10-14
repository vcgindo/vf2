import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.mdm.initialization_contract import scalar_configuration
from mta.mdm.native_audit_policy import validate_policy


POLICY = {
    'horizon': 7,
    'timezone': 'Asia/Kolkata',
    'client_folder': None,
}


def profile():
    return {
        'calculation': {
            'skus': [], 'locations': [], 'stock_openings': [], 'policies': [],
            'logistics': {'items': [], 'vehicles': [], 'location_vehicles': []},
            'stock_configuration': {'reservation_type': 0,
                                    'reservation_for_rationing_only': False},
            'allocation': {'advance_stock_threshold_percent': 0},
            'replenishment_exclusions': [],
        },
        'force_flags': {'from_ui': True, 'ignore_master_norm': False,
                        'nms_active': True},
        'delivery': {
            'site_code': 'SITE',
            'batch': dict.fromkeys((
                'AutoDBMActive', 'DBMNormChangeReportHorizon',
                'NormChangeLogHorizon', 'GatherSuspensionHistory',
                'ActivateNormChangeLogReport', 'DailyConsumptionHorizonDBM',
                'PhaseOutRecommendation30Days', 'PhaseOutRecommendation60Days',
                'PhaseOutRecommendation90Days', 'ActivateNorm0Report30Days',
                'ActivateNorm0Report60Days', 'ActivateNorm0Report90Days',
                'ActivateNorm1Report30Days', 'ActivateNorm2Report30Days'), 0),
            'controls': {'from_ui': True, 'start_percent': 0,
                         'history_horizon': 0},
            'btr_settings': {
                'CaptureDispatchExecutionEfficiency': 0,
                'GenerateColorAgeingReport': 0,
                'BRAgeColorTolerance': 0,
                'CARNoColorToleranceDuration': 0,
                'NormSuggestion_Upward': 'Upward',
                'NormSuggestion_Downward': 'Downward',
            },
        },
        'daily_publication_config': {'bpr_remark_horizon': 0},
        'daily': {
            'settings': [{'Parameter': 'MissingDailyDataHandling', 'Value': '1'}],
            'vf_settings': [{'Parameter': 'GenerateBPRForMissingInventoryLoc',
                             'Value': '0'}],
        },
    }


class NativeAuditPolicyTests(unittest.TestCase):
    def assert_scalar_configuration(self, value):
        with patch('mta.domain.dbm_phase_recommendation.configuration'), \
                patch('mta.domain.btr_finalization._selected_settings'):
            scalar_configuration(value)

    def test_absent_policy_remains_absent_and_profile_key_is_admitted(self):
        self.assertIsNone(validate_policy({}))
        contract = json.loads((Path(__file__).resolve().parents[1] /
            'mta/config/initialization_storage_v1.json').read_text())
        self.assertIn('native_upload_audit', contract['allowed_profile_keys'])

    def test_scalar_configuration_preserves_profiles_without_policy(self):
        self.assert_scalar_configuration(profile())

    def test_scalar_configuration_admits_and_checks_canonical_policy(self):
        value = profile()
        value['native_upload_audit'] = POLICY.copy()
        self.assert_scalar_configuration(value)
        value['native_upload_audit']['timezone'] = 'Not/A_Zone'
        with self.assertRaisesRegex(ValueError, 'IANA name'):
            self.assert_scalar_configuration(value)

    def test_canonical_policy_accepts_explicit_null_client_folder(self):
        profile = {'native_upload_audit': POLICY.copy()}
        self.assertIs(validate_policy(profile), profile['native_upload_audit'])

    def test_policy_requires_exact_fields(self):
        for policy in (
                {name: value for name, value in POLICY.items() if name != 'horizon'},
                {**POLICY, 'extra': 'denied'}):
            with self.subTest(policy=policy), self.assertRaisesRegex(
                    ValueError, 'policy fields differ'):
                validate_policy({'native_upload_audit': policy})

    def test_horizon_requires_nonnegative_integer_and_denies_bool(self):
        for value in (-1, True, False, 7.0, '7', None):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, 'nonnegative integer'):
                validate_policy({'native_upload_audit': {**POLICY, 'horizon': value}})
        self.assertEqual(validate_policy({'native_upload_audit': {**POLICY, 'horizon': 0}})
                         ['horizon'], 0)

    def test_timezone_requires_valid_iana_string(self):
        for value in ('', 'Not/A_Zone', 5, None):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, 'IANA name'):
                validate_policy({'native_upload_audit': {**POLICY, 'timezone': value}})

    def test_client_folder_accepts_null_or_nonblank_string_only(self):
        for value in ('', '   ', 5, False, [], {}):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, 'null or nonblank text'):
                validate_policy({'native_upload_audit': {**POLICY,
                    'client_folder': value}})
        value = 'C:/VectorFLOW/Client'
        self.assertEqual(validate_policy({'native_upload_audit': {**POLICY,
            'client_folder': value}})['client_folder'], value)

    def test_policy_itself_must_be_an_object(self):
        for value in (None, [], 'policy'):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, 'policy fields differ'):
                validate_policy({'native_upload_audit': value})


if __name__ == '__main__':
    unittest.main()
