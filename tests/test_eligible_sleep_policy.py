from copy import deepcopy
import unittest
from parity.temporal_policy import commands_for_day, ELIGIBLE_SLEEP_POLICY


class EligibleSleepPolicyTests(unittest.TestCase):
    def test_new_policy_uses_only_own_suggestions_and_preserves_strict_default(self):
        case = dict(days=[{'business_date':'2026-06-06'}],commands=[dict(after_day=0,
            operation='SLEEP', selected=[['a','one'],['b','two']],
            timestamp='2026-06-06T12:00:00+05:30')])
        suggestions = [{'SKUCode':'a','WhCode':'one'},{'SKUCode':'c','WhCode':'three'}]
        with self.assertRaisesRegex(ValueError, 'lacks unique own suggestions'):
            commands_for_day(case,0,suggestions)
        new = {**deepcopy(case),'profile':{'synthetic_action_policy':ELIGIBLE_SLEEP_POLICY}}
        commands = commands_for_day(new,0,suggestions)
        self.assertEqual([(c['operation'],c['selected']) for c in commands],
                         [('SLEEP',[['a','one']]),('APPLY',[['c','three']])])
        self.assertEqual(commands_for_day(new,0,[]),[])
        self.assertNotIn('profile',case)

    def test_overlapping_eligible_sleep_still_fails(self):
        event = dict(after_day=0,operation='SLEEP',selected=[['a','one']],
                     timestamp='2026-06-06T12:00:00+05:30')
        case = dict(days=[{'business_date':'2026-06-06'}],commands=[event,event],
                    profile={'synthetic_action_policy':ELIGIBLE_SLEEP_POLICY})
        with self.assertRaisesRegex(ValueError,'unique own suggestions'):
            commands_for_day(case,0,[{'SKUCode':'a','WhCode':'one'}])
