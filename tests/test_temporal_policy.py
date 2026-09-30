import unittest

from parity.temporal_policy import commands_for_day


class TrialPolicyTest(unittest.TestCase):
    def case(self):
        return dict(days=[dict(business_date='2026-06-06'),dict(business_date='2026-06-07')],
                    commands=[dict(after_day=0,operation='SLEEP',selected=[['337','AG515802']],
                                   timestamp='2026-06-06T12:00:00+05:30')])

    def test_sleep_event_then_apply_all_other_own_suggestions(self):
        actions=commands_for_day(self.case(),0,[dict(SKUCode='337',WhCode='AG515802'),
                                                dict(SKUCode='6119',WhCode='MT0513')])
        self.assertEqual([a['operation'] for a in actions],['SLEEP','APPLY'])
        self.assertEqual(actions[1]['selected'],[['6119','MT0513']])

    def test_next_day_uses_new_computed_membership_not_previous_selection(self):
        actions=commands_for_day(self.case(),1,[dict(SKUCode='7081',WHCode='PPI000604')])
        self.assertEqual(actions[0]['selected'],[['7081','PPI000604']])

    def test_no_suggestions_means_no_invented_action(self):
        self.assertEqual(commands_for_day(self.case(),1,[]),[])

    def test_missing_sleep_selection_cannot_silently_disappear(self):
        with self.assertRaisesRegex(ValueError,'lacks unique'):commands_for_day(self.case(),0,[])

    def test_sleep_clock_must_match_trial_day(self):
        value=self.case();value['commands'][0]['timestamp']='2026-06-07T12:00:00+05:30'
        with self.assertRaisesRegex(ValueError,'SQL DATE'):
            commands_for_day(value,0,[dict(SKUCode='337',WhCode='AG515802')])

    def test_duplicate_suggestions_are_not_resolved_by_trial(self):
        row=dict(SKUCode='337',WhCode='AG515802')
        with self.assertRaisesRegex(ValueError,'exactly one'):commands_for_day(self.case(),0,[row,row])
