"""Pure focused fixture and native action-component checks for the H3 proof."""
from copy import deepcopy
from types import SimpleNamespace
import os
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'h3-native-actions-pure-proof')
import django
django.setup()

from mta.domain.dbm_rules import too_much_in_green
from mta.domain.dbm_suspension_history import CONTRIBUTORS, gather_suspension_history
from mta.domain.dbm_suspensions import apply_sleep
from mta.domain.elephant_orders import apply_due_dates
from mta.mdm.initialization_contract import decode
from mta.runtime.production_preflight import Requirements, closing_shape
from mta.serialization import digest, storage
from mta.temporal.actions import apply_command
from tests.initialization_input_fixture import encoded
from tests.production_h3_fixture import CHILD
from tests.test_h3_daily_integration import coupled
from tests.native_action_fixture import TARGET, operator_input


def rule5_state():
    master = dict(SKUCode=TARGET[0], WhCode=TARGET[1], Norm=36, GCP=3, RLT=3)
    return dict(DBMMaster=[master], Suggestions=[], IntermediateTables=[],
        SuspendStockType=[dict(SKUCode=TARGET[0], WhCode=TARGET[1],
            RedEnabled=True, GreenEnabled=True, RedResumeDate='2037-04-10',
            GreenResumeDate='2037-04-10')],
        DailyConsumption=[dict(SKUCode=TARGET[0], WhCode=TARGET[1], Stock=30,
            BlueZone=0, ReportDate=day) for day in
            ('2037-04-10', '2037-04-11', '2037-04-12')],
        LastBatchRunTbl=[dict(LastRunDate='2037-04-12T00:00:00')])


class H3NativeActionComponents(unittest.TestCase):
    def test_operator_input_has_only_declared_action_profile_delta(self):
        value = operator_input()
        self.assertEqual(value['configuration']['delivery']['batch']['AutoDBMActive'], 0)
        reason = [dict(Id=5, Reason='Supplied rule 5')]
        self.assertEqual(value['opening']['state']['dbm']['ReasonCodes'], reason)
        self.assertEqual(value['opening']['state']['controls']['reason_codes'], reason)
        self.assertEqual(value['recipe']['version'], 'supplied-h3-native-actions-v1')
        self.assertEqual(value['opening']['identity'],
                         'SUPPLIED-H3-NATIVE-ACTIONS-WithDestLoc')
        state = value['opening']['state']['dbm']
        self.assertEqual(state['Suggestions'], [])
        self.assertEqual(state['NormAcceptanceTbl'], [])

    def test_actual_rule5_and_apply_overlay_match_database_expectation(self):
        calculated = too_much_in_green('2037-04-12', rule5_state())
        suggestion = dict(SKUCode=TARGET[0], WhCode=TARGET[1], Type=5, NewNorm=24)
        self.assertEqual(calculated['Suggestions'], [suggestion])
        calculated['NormAcceptanceTbl'] = []
        applied = apply_command(calculated, 'APPLY', [TARGET],
                                '2037-04-12T12:00:00+05:30')
        self.assertEqual(applied['Suggestions'], [suggestion])
        self.assertEqual(applied['NormAcceptanceTbl'], [dict(SKUCode=TARGET[0],
            WhCode=TARGET[1], AcceptanceDate='2037-04-12', OldNorm=36, NewNorm=24)])

    def test_unmatched_native_selection_is_the_existing_no_op(self):
        calculated = too_much_in_green('2037-04-12', rule5_state())
        calculated.update(NormAcceptanceTbl=[], NormsInSleepModeTbl=[])
        for action in ('APPLY', 'SLEEP'):
            self.assertEqual(apply_command(calculated, action, [('ABSENT', 'ABSENT')],
                '2037-04-12T12:00:00+05:30'), calculated)

    def test_actual_sleep_overlay_next_day_wait_and_history_bits(self):
        calculated = too_much_in_green('2037-04-12', rule5_state())
        calculated.update(NormsInSleepModeTbl=[], SuspendNormsInSleepModeTbl=[])
        slept = apply_command(calculated, 'SLEEP', [TARGET],
                              '2037-04-12T12:00:00+05:30')
        slept['LastBatchRunTbl'] = [dict(LastRunDate='2037-04-13T00:00:00')]
        successor = apply_sleep('2037-04-13', slept)
        expected = dict(SKUCode=TARGET[0], WhCode=TARGET[1], IsRedEnabled=False,
            IsGreenEnabled=False, WaitStartDate='2037-04-12',
            WaitTillDate='2037-04-15', WaitForReceipts=False)
        self.assertEqual(successor['Suggestions'], [])
        self.assertEqual(successor['NormsInSleepModeTbl'], [])
        self.assertEqual(successor['SuspendNormsInSleepModeTbl'], [expected])

        history = deepcopy(successor)
        history.update(SuspendHistory=[],
            SuspendStockType=[dict(SKUCode=TARGET[0], WhCode=TARGET[1],
                RedEnabled=False, GreenEnabled=False)],
            SuspendConsumptionType=[dict(SKUCode=TARGET[0], WhCode=TARGET[1],
                RedEnabled=False, GreenEnabled=False)])
        for table, _, _ in CONTRIBUTORS:
            history.setdefault(table, [])
        result = gather_suspension_history('2037-04-13', history)['SuspendHistory']
        self.assertEqual(len(result), 1)
        for field in ('RedReasonStockType', 'GreenReasonStockType',
                      'RedReasonConsumptionType', 'GreenReasonConsumptionType'):
            self.assertEqual(result[0][field], 2)

    def test_operator_input_actual_four_day_coupled_apply_and_sleep(self):
        """Exercise the same producers/captures before either PostgreSQL proof."""
        for action in ('APPLY', 'SLEEP'):
            with self.subTest(action=action):
                supplied = operator_input()
                raw, sha, args = encoded(supplied)
                frame = decode(raw, sha, **args)[1]
                profile = frame['profile']
                opening = frame['opening']['state']

                root_result, _ = coupled(profile, opening, '2037-04-09', '2037-04-10',
                                         positive=False)
                root = storage(root_result['ClosingState'][0])
                root['orders'] = apply_due_dates(root['orders'], [dict(OrderID=order_id,
                    SKUCode=TARGET[0], WhCode=CHILD, DueDate='2037-04-14')
                    for order_id in ('ELEPHANT-Z', 'ELEPHANT-A')])
                root_parent = SimpleNamespace(pk='h3-actions-root-'+action.lower(),
                                              output_digest=digest(root))

                april11_result, capture11 = coupled(profile, root, '2037-04-10',
                    '2037-04-11', parent=root_parent, positive=True)
                april11 = storage(april11_result['ClosingState'][0])
                self.assertTrue(capture11['force']['rows'])
                self.assertTrue(capture11['season']['rows'])
                self.assertTrue(capture11['phase_controls']['phase_requests'])
                self.assertTrue(capture11['supplier']['queues']['NMSSOB'])
                self.assertEqual(april11['orders']['ElephantOrders'], [])
                self.assertTrue(all(row['DueDate'] == '2037-04-14'
                    for row in april11['orders']['SpikeOrderData']
                    if row['CustomerOrderId'] in ('ELEPHANT-Z', 'ELEPHANT-A')))
                april11_parent = SimpleNamespace(pk='h3-actions-april11-'+action.lower(),
                                                 output_digest=digest(april11))

                april12_result, capture12 = coupled(profile, april11, '2037-04-11',
                    '2037-04-12', parent=april11_parent, positive=False, stop=True)
                april12 = storage(april12_result['ClosingState'][0])
                self.assertTrue(capture12['stop_pipo']['rows'])
                suggestion = dict(SKUCode=TARGET[0], WhCode=TARGET[1], Type=5,
                                  NewNorm=24)
                self.assertEqual(april12['dbm']['Suggestions'], [suggestion])
                self.assertEqual(april12['dbm']['ReasonCodes'],
                                 [dict(Id=5, Reason='Supplied rule 5')])
                self.assertEqual(next(row['Norm'] for row in april12['dbm']['DBMMaster']
                    if (row['SKUCode'], row['WhCode']) == TARGET), 36)
                requirements = Requirements('day')
                closing_shape(requirements, april12)
                self.assertEqual(requirements.issues, [])

                acted = deepcopy(april12)
                acted['dbm'] = storage(apply_command(acted['dbm'], action, [TARGET],
                    '2037-04-12T12:00:00+05:30'))
                action_parent = SimpleNamespace(pk='h3-actions-april12-'+action.lower(),
                                                output_digest=digest(april12))
                april13_result, capture13 = coupled(profile, acted, '2037-04-12',
                    '2037-04-13', parent=action_parent, positive=False)
                self.assertEqual(capture13['force']['rows'], [])
                self.assertEqual(capture13['stop_pipo']['rows'], [])
                final = storage(april13_result['ClosingState'][0])
                requirements = Requirements('day')
                closing_shape(requirements, final)
                self.assertEqual(requirements.issues, [])
                self.assertEqual(final['dbm']['Suggestions'], [])
                self.assertEqual([row for row in final['dbm']['SuggestionsLog']
                    if (row['SKUCode'], row['WhCode']) == TARGET], [dict(
                        SKUCode=TARGET[0], WhCode=TARGET[1], Type=5, OldNorm=36,
                        NewNorm=24, SuggestionDate='2037-04-12')])
                if action == 'APPLY':
                    self.assertEqual(final['dbm']['NormAcceptanceTbl'], [])
                    self.assertEqual(next(row['Norm'] for row in final['dbm']['DBMMaster']
                        if (row['SKUCode'], row['WhCode']) == TARGET), 24)
                    self.assertEqual([row for row in final['dbm']['NormChangeLogTbl']
                        if (row['SKUCode'], row['WHCode']) == TARGET], [dict(
                            SKUCode=TARGET[0], WHCode=TARGET[1], OldNorm=36, NewNorm=24,
                            NormChangeDate='2037-04-13', NormChangeReason=5)])
                else:
                    self.assertEqual(final['dbm']['NormsInSleepModeTbl'], [])
                    self.assertEqual(next(row['Norm'] for row in final['dbm']['DBMMaster']
                        if (row['SKUCode'], row['WhCode']) == TARGET), 36)
                    self.assertEqual([row for row in final['dbm']['SuspendNormsInSleepModeTbl']
                        if (row['SKUCode'], row['WhCode']) == TARGET], [dict(
                            SKUCode=TARGET[0], WhCode=TARGET[1], IsRedEnabled=False,
                            IsGreenEnabled=False, WaitStartDate='2037-04-12',
                            WaitTillDate='2037-04-15', WaitForReceipts=False)])
                    history = [row for row in final['dbm']['SuspendHistory']
                        if (row['SKUCode'], row['WhCode'], row['ReportDate']) ==
                           (TARGET[0], TARGET[1], '2037-04-13')]
                    self.assertEqual(len(history), 1)
                    for field in ('RedReasonStockType', 'GreenReasonStockType',
                                  'RedReasonConsumptionType', 'GreenReasonConsumptionType'):
                        self.assertEqual(history[0][field], 2)


if __name__ == '__main__':
    unittest.main()
