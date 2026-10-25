"""Full shipment publication uses its explicit captured Importer settings."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from mta.presentation.daily_sources import _transit_factor, recipe_digest


def factor(value='1.5'):
    return dict(Parameter='SuperDelayFactor', Value=value, Description='Declared test factor')


class DailyTransitSettingsOwnerTests(unittest.TestCase):
    def resolve(self, delivery, current=()):
        with patch('mta.runtime.input_reader.read_input', return_value={'profile': {'delivery': delivery}}) as read:
            result = _transit_factor('run', list(current))
        read.assert_called_once_with('run', components=('profile',))
        return result

    def test_explicit_importer_factor_does_not_require_optional_dbm_projection(self):
        self.assertEqual(self.resolve({'btr_history': {'importer_vf_settings': [factor()]}}), '1.5')

    def test_original_full_current_factor_contract_is_retained_without_capture(self):
        self.assertEqual(self.resolve({}, [factor('2.5')]), '2.5')
        for current in ([], [factor(), factor()]):
            with self.assertRaisesRegex(ValueError, 'Exactly one current'):
                self.resolve({}, current)

    def test_identical_multiple_projections_agree_without_merging_bags(self):
        rows = [factor()]
        delivery = dict(btr_history={'importer_vf_settings': rows},
                        conditional_dbm={'importer_vf_settings': deepcopy(rows)})
        before = deepcopy(delivery)
        self.assertEqual(self.resolve(delivery, rows), '1.5')
        self.assertEqual(delivery, before)

    def test_missing_duplicate_or_null_captured_factor_never_uses_current_as_default(self):
        for rows in ([], [factor(), factor()], [factor(None)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.resolve({'btr_history': {'importer_vf_settings': rows}}, [factor()])

    def test_conflicting_conditional_or_current_projection_is_denied(self):
        explicit = {'btr_history': {'importer_vf_settings': [factor()]}}
        for current in ([factor('2')], [factor(), factor()]):
            with self.assertRaisesRegex(ValueError, 'Current DBM and captured'):
                self.resolve(explicit, current)
        for other in ([factor('2')], [factor(), factor()], [dict(factor(), Description='different')]):
            with self.assertRaisesRegex(ValueError, 'factor declarations differ'):
                self.resolve(dict(explicit, conditional_dbm={'importer_vf_settings': other}))

    def test_captured_sql_identity_preserves_case_and_space_semantics(self):
        row = dict(factor(), Parameter='superdelayfactor ')
        self.assertEqual(self.resolve({'btr_history': {'importer_vf_settings': [row]}}), '1.5')

    def test_malformed_importer_projection_is_denied(self):
        for row in ({'Parameter': 'SuperDelayFactor', 'Value': '1.5'}, dict(factor(), extra='x')):
            with self.assertRaises(ValueError):
                self.resolve({'btr_history': {'importer_vf_settings': [row]}})

    def test_publication_recipe_pins_factor_adapter(self):
        original = recipe_digest()
        with patch('mta.presentation.daily_sources._transit_factor', lambda *args: 'different'):
            self.assertNotEqual(recipe_digest(), original)
