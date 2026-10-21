"""Persisted-row ownership at the native daily entry; no database or daily run.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import unittest

from mta.row_sequences import RecordRows
from mta.temporal.chain import entry_inputs


def typed(value):
    if isinstance(value,dict):
        return [(key,typed(item)) for key,item in value.items()]
    if isinstance(value,(list,RecordRows)):
        return ['rows',[typed(item) for item in value]]
    if isinstance(value,tuple):
        return ['tuple',[typed(item) for item in value]]
    return [type(value).__name__,repr(value)]


class EntryRowOwnershipTests(unittest.TestCase):
    def test_bit_adapter_has_lazy_owned_generation_and_exact_non_bit_values(self):
        from datetime import date
        from decimal import Decimal
        rows=[dict(Approved=True,NonNMS=False,Event_Type=None,Count=1,
                   Quantity=Decimal('1.00'),Date=date(2026,4,7),Name=' A ')]*2
        def prepare(source):
            prior=dict(importer_settings=[],importer={'T':source},bpr={})
            return entry_inputs(prior,'2026-04-07',dict(business_date='2026-04-08',
                raw_master=[],raw_non_nms=[],raw_no_norm=[],raw_daily=[]),
                dict(import_non_nms=True,daily={}),'entry-proof')[0]['prior']['T']
        expected=prepare(deepcopy(rows))
        spool=RecordRows.from_rows(rows)
        before=typed(spool)
        actual=prepare(spool)
        self.assertIsInstance(actual,RecordRows)
        self.assertFalse(hasattr(actual,'_data'))  # lazy, no second spool/list
        self.assertEqual(typed(actual),typed(expected))
        self.assertEqual(typed(actual),typed(expected))
        self.assertEqual(typed(actual[1]),typed(expected[1]))
        self.assertEqual(typed(spool),before)
        self.assertIs(type(actual[0]['Approved']),int)
        self.assertIs(type(spool[0]['Approved']),bool)
        with self.assertRaisesRegex(TypeError,'Immutable'):
            actual[0]['Approved']=0
        nested=[dict(Approved=True,extra={'flag':False,'items':[1,None]})]
        converted=prepare(nested)
        converted[0]['extra']['items'].append(2)
        self.assertEqual(nested[0]['extra']['items'],[1,None])
        self.assertIs(converted[0]['extra']['flag'],False)

    def test_complete_spooled_entry_equals_eager_and_keeps_original_generations(self):
        from tests.test_h3_inactive_mode import inactive_frame,inactive_day
        from tests.test_production_daily_contract import encoded_day
        from mta.runtime.production_daily import working_day,decode
        from mta.temporal.chain import calculate_day
        from mta.planning.engine import calculate_current_day
        frame=inactive_frame()
        day=working_day(decode(*encoded_day(inactive_day('2037-04-10',root=True))),frame['profile'])
        prior=frame['opening']['state']
        for row in prior['importer']['SkuLocAttributeData']:
            row['NonNMS']=bool(row['NonNMS'])
        def calculate(source,**owned):
            return calculate_current_day(source,defer_pick=True,**owned),'owned-entry-proof'
        expected=calculate_day(deepcopy(prior),'2037-04-09',deepcopy(day),
            frame['profile'],'owned-entry-proof',calculate,native_daily=True)
        persisted=deepcopy(prior)
        for name,rows in persisted['importer'].items():
            persisted['importer'][name]=RecordRows.from_rows(rows)
        for section,names in (('bpr',('DailyConsumption',)),
                ('dbm',('DailyConsumption','SuspendHistory','OrderDataSummary','SuggestionsLog')),
                ('btr',('BPR','RationingHistory'))):
            for name in names:
                if name in persisted[section]:
                    persisted[section][name]=RecordRows.from_rows(persisted[section][name])
        frozen_day=deepcopy(day)
        frozen_day['raw_daily']=RecordRows.from_rows(frozen_day['raw_daily'])
        before=typed(persisted),typed(frozen_day)
        actual=calculate_day(persisted,'2037-04-09',frozen_day,frame['profile'],
            'owned-entry-proof',calculate,native_daily=True)
        self.assertEqual(typed(actual),typed(expected))
        self.assertEqual((typed(persisted),typed(frozen_day)),before)

    def test_importer_rejection_is_identical_for_spooled_rows(self):
        from tests.test_h3_inactive_mode import inactive_frame,inactive_day
        from mta.application.r1_importer_master import validate_master_input
        frame=inactive_frame();prior=frame['opening']['state']
        day=inactive_day('2037-04-10',root=True)['day']
        # This tests the unchanged row/NULL validator, beyond the adapter.
        payload,_=entry_inputs(prior,'2037-04-09',day,frame['profile'],'owned-entry-proof')
        for field,bad in (('Norm',None),('Norm','not-a-number')):
            with self.subTest(value=bad):
                eager=deepcopy(payload)
                eager['prior']['MasterData'][0][field]=bad
                with self.assertRaises(ValueError) as expected:
                    validate_master_input(eager)
                spooled=deepcopy(eager)
                spooled['prior']['MasterData']=RecordRows.from_rows(spooled['prior']['MasterData'])
                with self.assertRaises(type(expected.exception)) as actual:
                    validate_master_input(spooled)
                self.assertEqual(str(actual.exception),str(expected.exception))
        payload['prior']['MasterData']=iter(payload['prior']['MasterData'])
        with self.assertRaisesRegex(ValueError,'list or immutable record rows'):
            validate_master_input(payload)
