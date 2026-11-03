"""Exact independent witnesses plus unchanged production history owners."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import unittest

from mta.domain.dbm_ingestion import import_daily_observations, import_orders
from mta.domain.dbm_daily_cleanup import daily_cleanup
from mta.domain.dbm_order_summary import update_order_summary
from mta.domain.dbm_postrules import generate_reports, discard_suggestions
from mta.domain.dbm_suspension_history import gather_suspension_history, CONTRIBUTORS, REASONS
from mta.runtime.dated_history_delta import changes, fields, supports_descriptor, Fact, Removal, Counts, Occurrence
from mta.serialization import storage


TODAY = '2026-04-10'


def row(table, stamp=TODAY, **values):
    result = dict.fromkeys(fields('closing/dbm/'+table), 0)
    result.update(SKUCode='sku ', WhCode='w')
    if table == 'OrderData':
        result.update(OrderID='O', OrderDate='2026-04-01')
    field = {'OrderData': 'ImportDate', 'OrderDataSummary': 'ImportDate',
             'SuggestionsLog': 'SuggestionDate', 'DiscardedSuggestions': 'SuggestionDate',
             'SpikeReport': 'SuspendFromDate'}.get(table, 'ReportDate')
    result[field] = stamp
    if table == 'SpikeReport':
        result['SuspendTillDate'] = '2026-04-20'
    if table == 'SuspendHistory':
        result.update({k: True for k in result if k.startswith(('RedEnabled','GreenEnabled'))})
    result.update(values)
    return result


def reconstruct(before, events, position=0):
    # Independent occurrence ledger, with no date/retention policy in this oracle.
    output = {Occurrence(position, n): storage(deepcopy(r)) for n, r in enumerate(before)}
    for event in events:
        if isinstance(event, Removal):
            del output[event.occurrence]
        elif isinstance(event, Fact):
            assert event.occurrence not in output
            output[event.occurrence] = event.values
    return list(output.values())


class DatedHistoryDeltaTests(unittest.TestCase):
    def classify(self, table, before, after, *, horizon=None, today=TODAY, position=1, prior_position=0):
        prior = ((Occurrence(prior_position, n), r) for n, r in enumerate(before))
        return list(changes(prior, iter(after), family='closing/dbm/'+table,
                            today=today, position=position, horizon=horizon))

    def test_empty_and_duplicate_first_facts_for_all_seven_families(self):
        for table in ('DailyConsumption','OrderData','OrderDataSummary','SuggestionsLog',
                      'DiscardedSuggestions','SpikeReport','SuspendHistory'):
            with self.subTest(table=table):
                horizon = 30 if table == 'DailyConsumption' else None
                self.assertEqual(self.classify(table, [], [], horizon=horizon), [Counts(0,0,0,0,0)])
                rows = [row(table), row(table)]
                events = self.classify(table, [], rows, horizon=horizon)
                self.assertEqual([e.occurrence for e in events[:-1]], [Occurrence(1,0),Occurrence(1,1)])
                self.assertEqual(reconstruct([],events),rows)

    def test_actual_daily_owner_multiplicity_blues_exclusion_and_final_cutoff(self):
        before = [row('DailyConsumption','2026-03-11'),row('DailyConsumption','2026-03-12'),
                  row('DailyConsumption',None),row('DailyConsumption'),row('DailyConsumption','2026-04-20')]
        frozen = deepcopy(before)
        masters = [dict(SKUCode='SKU',WhCode='W'),dict(SKUCode='SKU',WhCode='W')]
        incoming = [row('DailyConsumption',Consumption=3,Stock=4),row('DailyConsumption',WhCode='excluded')]
        blue = [dict(SKUCode='SKU',WhCode='W',ReportDate=TODAY,BlueZone=7)]
        consumed = import_daily_observations(TODAY,before,incoming,masters,blue,
            [dict(WhCode='excluded',ReportDate=TODAY,TransactedItemCount=0)],[])
        after = daily_cleanup(TODAY,{'DailyConsumption':consumed,'LastBatchRunTbl':[{'LastRunDate':TODAY+'T00:00:00'}]},30)['DailyConsumption']
        events = self.classify('DailyConsumption',before,after,horizon=30)
        self.assertEqual(events[-1],Counts(5,3,2,2,5))
        self.assertEqual(reconstruct(before,events),after)
        self.assertEqual([e.values['BlueZone'] for e in events if isinstance(e,Fact)],[7,7])
        self.assertEqual(before,frozen)

    def test_zero_negative_horizon_does_not_reintroduce_current_rows(self):
        for horizon in (0,-1):
            before=[row('DailyConsumption',None),row('DailyConsumption','2026-04-20')]
            after=daily_cleanup(TODAY,{'DailyConsumption':before+[row('DailyConsumption')],
                'LastBatchRunTbl':[{'LastRunDate':TODAY+'T00:00:00'}]},horizon)['DailyConsumption']
            events=self.classify('DailyConsumption',before,after,horizon=horizon)
            self.assertEqual(events,[Counts(2,2,0,0,2)])
            self.assertEqual(reconstruct(before,events),after)

    def test_actual_orders_replace_today_preserve_null_future_and_raw_keys(self):
        before=[row('OrderData',None),row('OrderData'),row('OrderData','2026-04-20',SKUCode='SKU')]
        raw=[row('OrderData',OrderQuantity=2)]*2
        after=import_orders(TODAY,before,raw)
        events=self.classify('OrderData',before,after)
        self.assertEqual(events[-1],Counts(3,2,2,1,4))
        self.assertEqual(reconstruct(before,events),after)

    def test_actual_summary_includes_ninetieth_day_and_duplicate_new_rows(self):
        before=[row('OrderDataSummary','2026-01-09'),row('OrderDataSummary','2026-01-10'),row('OrderDataSummary')]
        current={k:v for k,v in row('OrderDataSummary',NodeConsumption=5).items() if k!='ImportDate'}
        after=update_order_summary(TODAY,{'OrderDataSummary':before,'OrderRuleSummary':[current,current]})['OrderDataSummary']
        events=self.classify('OrderDataSummary',before,after)
        self.assertEqual(events[-1],Counts(3,1,2,2,3))
        self.assertEqual(reconstruct(before,events),after)

    def test_actual_suspension_strict_cutoff_and_duplicate_cartesian_rows(self):
        before=[row('SuspendHistory','2026-01-09'),row('SuspendHistory','2026-01-10'),row('SuspendHistory','2026-01-11')]
        current=dict(SKUCode='sku ',WhCode='w',RedEnabled=True,GreenEnabled=False)
        state={'SuspendHistory':before,'LastBatchRunTbl':[{'LastRunDate':TODAY+'T00:00:00'}],
               'SuspendStockType':[current,current],'SuspendConsumptionType':[current,current],
               **{table:[] for table,_,_ in CONTRIBUTORS}}
        after=gather_suspension_history(TODAY,state)['SuspendHistory']
        events=self.classify('SuspendHistory',before,after)
        self.assertEqual(events[-1],Counts(3,1,4,2,5))
        self.assertEqual(reconstruct(before,events),after)

    def test_actual_suggestion_discard_spike_history_owners(self):
        master=dict(SKUCode='sku ',WhCode='w',Norm=10,MinNorm=5)
        suggestion=dict(SKUCode='sku ',WhCode='w',Type=1,NewNorm=8)
        state={'DBMMaster':[master,master],'Suggestions':[suggestion,suggestion],
               'LastBatchRunTbl':[{'LastRunDate':TODAY+'T00:00:00'}],
               'SuggestionsLog':[row('SuggestionsLog',None),row('SuggestionsLog')],
               'SpikeReport':[row('SpikeReport','2026-04-01'),row('SpikeReport')],
               'SuspendSpikeTbl':[dict(SKUCode='sku ',WhCode='w',WaitStartDate=TODAY,WaitTillDate='2026-04-20')]*2}
        after=generate_reports(TODAY,state)
        for table,inserted in [('SuggestionsLog',4),('SpikeReport',2)]:
            events=self.classify(table,state[table],after[table])
            self.assertEqual(events[-1],Counts(2,1,inserted,1,inserted+1))
            self.assertEqual(reconstruct(state[table],events),after[table])
        state.update(DiscardedSuggestions=[row('DiscardedSuggestions',None),row('DiscardedSuggestions')],
                     Suggestions=[dict(suggestion,NewNorm=3)]*2)
        discarded=discard_suggestions(TODAY,state)['DiscardedSuggestions']
        events=self.classify('DiscardedSuggestions',state['DiscardedSuggestions'],discarded)
        self.assertEqual(events[-1],Counts(2,1,2,1,3))
        self.assertEqual(reconstruct(state['DiscardedSuggestions'],events),discarded)

    def test_own_successor_has_no_retained_payload_events_and_old_image_unchanged(self):
        first=[row('OrderData'),row('OrderData')]
        saved=deepcopy(first)
        second=import_orders('2026-04-11',first,[row('OrderData','2026-04-11')])
        events=self.classify('OrderData',first,second,today='2026-04-11',position=2,prior_position=1)
        self.assertEqual(events,[Fact(Occurrence(2,0),second[-1]),Counts(2,2,1,0,3)])
        self.assertEqual(reconstruct(first,events,position=1),second)
        self.assertEqual(first,saved)

    def test_retained_value_type_null_spelling_order_and_shape_cannot_change(self):
        before=[row('OrderData','2026-04-09',OrderQuantity=1),row('OrderData','2026-04-08',OrderQuantity=2)]
        variants=[list(reversed(before)),before[:1],
                  [dict(before[0],OrderQuantity=True),before[1]],
                  [dict(before[0],OrderQuantity=None),before[1]],
                  [dict(before[0],SKUCode='SKU'),before[1]],
                  [dict(before[0],extra=0),before[1]]]
        for after in variants:
            with self.subTest(after=after),self.assertRaises(ValueError):
                self.classify('OrderData',before,after)

    def test_storage_wire_dates_and_decimal_text_are_not_normalized_for_matching(self):
        before=[row('OrderData',date(2026,4,9),OrderQuantity=Decimal('1.00'))]
        after=[row('OrderData','2026-04-09',OrderQuantity='1.00')]
        self.assertEqual(self.classify('OrderData',before,after),[Counts(1,1,0,0,1)])
        with self.assertRaises(ValueError):
            self.classify('OrderData',before,[dict(after[0],OrderQuantity='1.0')])

    def test_postrule_literal_date_comparison_is_not_ingestion_date_parsing(self):
        before=[row('SuggestionsLog','20260410')]
        state={'DBMMaster':[],'Suggestions':[],'SuggestionsLog':before,'SpikeReport':[],
               'SuspendSpikeTbl':[],'LastBatchRunTbl':[{'LastRunDate':TODAY+'T00:00:00'}]}
        after=generate_reports(TODAY,state)['SuggestionsLog']
        self.assertEqual(self.classify('SuggestionsLog',before,after),[Counts(1,1,0,0,1)])

    def test_retained_signed_zero_bytes_cannot_change(self):
        before=[row('OrderData','2026-04-09',OrderQuantity=-0.0)]
        self.assertEqual(self.classify('OrderData',before,before),[Counts(1,1,0,0,1)])
        with self.assertRaises(ValueError):
            self.classify('OrderData',before,[dict(before[0],OrderQuantity=0.0)])

    def test_old_subset_and_case_mapped_descriptors_require_old_image_path(self):
        family='closing/dbm/OrderData'
        descriptor=[[f,f,'str'] for f in fields(family)]
        self.assertTrue(supports_descriptor(family,descriptor,1))
        self.assertTrue(supports_descriptor(family,list(reversed(descriptor)),1))
        self.assertTrue(supports_descriptor(family,[],0))
        self.assertFalse(supports_descriptor(family,[],1))
        self.assertFalse(supports_descriptor(family,descriptor[:-1],1))
        self.assertFalse(supports_descriptor(family,[['orderid','OrderID','str']]+descriptor[1:],1))

    def test_late_bad_fact_never_emits_completion_and_inputs_are_one_pass(self):
        def one_pass(rows):
            yield from rows
        before=[row('OrderData','2026-04-09')]
        events=changes(one_pass([(Occurrence(0,0),before[0])]),
            one_pass(before+[row('OrderData'),row('OrderData','2026-04-11')]),
            family='closing/dbm/OrderData',today=TODAY,position=1)
        self.assertIsInstance(next(events),Fact)
        with self.assertRaises(ValueError):next(events)

    def test_unqualified_family_owner_horizon_and_null_contracts_refuse(self):
        for options in ({'family':'closing/dbm/DBMMaster'}, {'position':True},
                        {'horizon':30}, {'today':None}):
            args=dict(family='closing/dbm/OrderData',today=TODAY,position=1);args.update(options)
            with self.subTest(options=options),self.assertRaises(ValueError):list(changes([],[],**args))
        for horizon in (None,True,-2147483648,'30'):
            with self.subTest(horizon=horizon),self.assertRaises(ValueError):
                self.classify('DailyConsumption',[],[],horizon=horizon)
        for occurrence in (Occurrence(1,0),Occurrence(2,0)):
            with self.assertRaises(ValueError):
                list(changes([(occurrence,row('OrderData','2026-04-09'))],[],
                    family='closing/dbm/OrderData',today=TODAY,position=1))
        for table in ('OrderDataSummary','SuspendHistory'):
            with self.subTest(table=table),self.assertRaises(ValueError):
                self.classify(table,[row(table,None)],[row(table,None)])


if __name__=='__main__':unittest.main()
