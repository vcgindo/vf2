import unittest
from parity.temporal import differences, fingerprint, command_membership


class TemporalComparisonTest(unittest.TestCase):
    def test_bags_preserve_duplicates_and_types(self):
        left = [{'v': 1}, {'v': None}, {'v': 1}]
        self.assertEqual(fingerprint(left), fingerprint(list(reversed(left))))
        self.assertEqual(differences(left, list(reversed(left))), [])
        for right in (left[:2], [{'v': '1'}, {'v': None}, {'v': 1}],
                      [{'v': True}, {'v': None}, {'v': 1}]):
            self.assertNotEqual(fingerprint(left), fingerprint(right))
            self.assertTrue(differences(left, right))

    def test_action_projection_uses_latest_log_and_reason_without_weakening_rows(self):
        suggestion = dict(SKUCode='337', WhCode='AG515802', NewNorm=294, Type=1)
        state = dict(Suggestions=[suggestion],
                     SuggestionsLog=[dict(suggestion, OldNorm=200, SuggestionDate='2026-06-05'),
                                     dict(suggestion, OldNorm=220, SuggestionDate='2026-06-06')],
                     ReasonCodes=[dict(Id=1, Reason='retained-reason')])
        self.assertEqual(command_membership(state, {('337','AG515802')}), [dict(
            suggestion, OldNorm=220, SuggestionDate='2026-06-06', Reason='retained-reason')])
        state['SuggestionsLog'].append(dict(suggestion, OldNorm=221, SuggestionDate='2026-06-06'))
        with self.assertRaisesRegex(ValueError, 'ambiguous latest logs'):
            command_membership(state, {('337','AG515802')})

    def test_ordered_scalar_arrays_and_all_fields_remain_strict(self):
        for left, right in (([1, 2], [2, 1]), ({'a': 1}, {'a': 1, 'b': None}),
                            ({'a': 1}, {'a': '1'}), (None, 0)):
            self.assertNotEqual(fingerprint(left), fingerprint(right))
            self.assertTrue(differences(left, right))
