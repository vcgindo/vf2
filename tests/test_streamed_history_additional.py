from copy import deepcopy
from datetime import datetime
import unittest

from mta.application.r1_daily_entry import generated_bpr_daily_state
from mta.application.r1_daily_input import STAGES, _typed_rows, process_daily_validation
from mta.domain.complete_daily_completion import prune_bpr_history
from mta.domain.dbm_order_summary import update_order_summary
from mta.domain.dbm_postrules import discard_suggestions, generate_reports
from mta.domain.ordinal_lookup import OrdinalLookup
from mta.row_sequences import RecordRows
from tests.test_native_daily_modules import PRIOR, TODAY, fixture


def values(rows):
    return [dict(row) for row in rows]


class AdditionalStreamedHistoryTests(unittest.TestCase):
    def assert_rows_equal(self, expected, actual):
        self.assertIsInstance(actual, RecordRows)
        self.assertEqual(values(actual), expected)
        self.assertEqual(values(actual), expected)

    def test_complete_connected_day_matches_eager_state(self):
        from tests.test_h3_inactive_mode import inactive_frame,inactive_day
        from tests.test_production_daily_contract import encoded_day
        from mta.runtime.production_daily import working_day,decode
        from mta.temporal.chain import calculate_day
        from mta.planning.engine import calculate_current_day
        from mta.serialization import digest
        frame=inactive_frame()
        day=working_day(decode(*encoded_day(inactive_day('2037-04-10',root=True))),frame['profile'])
        def calculate(source,**owned):
            return calculate_current_day(source,defer_pick=True,**owned),'streamed-component'
        prior=frame['opening']['state']
        expected=calculate_day(deepcopy(prior),'2037-04-09',deepcopy(day),
            frame['profile'],'streamed-component',calculate,native_daily=True)
        streamed=deepcopy(prior)
        for section,names in (
            ('bpr',('DailyConsumption',)),
            ('dbm',('DailyConsumption','SuspendHistory','OrderDataSummary','SuggestionsLog')),
            ('btr',('BPR','RationingHistory'))):
            for name in names:
                if name in streamed[section]:streamed[section][name]=RecordRows.from_rows(streamed[section][name])
        actual=calculate_day(streamed,'2037-04-09',deepcopy(day),frame['profile'],
            'streamed-component',calculate,native_daily=True)
        self.assertEqual(digest(actual),digest(expected))
        self.assertIsInstance(actual['ClosingState'][0]['bpr']['DailyConsumption'],RecordRows)

    def test_typed_prior_history_validates_before_lazy_projection(self):
        fields = ('SKUCode', 'WHCode', 'Stock', 'ReportDate')
        source = RecordRows.from_rows([
            dict(SKUCode='A', WHCode='L', Stock=None, ReportDate=PRIOR),
            dict(SKUCode='A', WHCode='L', Stock=3, ReportDate=PRIOR),
        ])
        result = _typed_rows(source, fields, ('Stock',))
        self.assert_rows_equal(values(source), result)
        invalid = RecordRows.from_rows([dict(SKUCode='A', WHCode='L', Stock='3', ReportDate=PRIOR)])
        with self.assertRaisesRegex(ValueError, 'numeric value'):
            _typed_rows(invalid, fields, ('Stock',))

    def test_daily_carry_preserves_normalized_duplicate_history_and_output(self):
        value, master = fixture(3)
        value['raw_daily_data'] = [row for row in value['raw_daily_data'] if row['WhCode'] != 'W']
        duplicate = dict(value['prior_bpr']['DailyConsumption'][0], SKUCode='s ', WHCode='w ')
        value['prior_bpr']['DailyConsumption'].append(duplicate)
        expected = process_daily_validation(deepcopy(value), deepcopy(master), TODAY,
            TODAY+'T00:00:00')[STAGES[-1]]['tables']
        streamed = deepcopy(value)
        opening = deepcopy(streamed['prior_bpr']['DailyConsumption'])
        streamed['prior_bpr']['DailyConsumption'] = RecordRows.from_rows(opening)
        actual = process_daily_validation(streamed, deepcopy(master), TODAY,
            TODAY+'T00:00:00')[STAGES[-1]]['tables']
        self.assertEqual(actual, expected)
        self.assertEqual(values(streamed['prior_bpr']['DailyConsumption']), opening)
        self.assertEqual([row['Stock'] for row in actual['DailyDataProcessed']
                          if row['WhCode'] == 'W'], [42])

    def test_generated_bpr_daily_history_stable_filter_append(self):
        opening = [
            dict(SKUCode='A', WHCode='L', Stock=None, Consumption=1, GIT=2,
                 Receipts=3, PSO=4, BlueZone=5, ReportDate=PRIOR),
            dict(SKUCode='A', WHCode='L', Stock=8, Consumption=1, GIT=2,
                 Receipts=3, PSO=4, BlueZone=5, ReportDate=TODAY),
            dict(SKUCode='A', WHCode='L', Stock=None, Consumption=1, GIT=2,
                 Receipts=3, PSO=4, BlueZone=5, ReportDate=PRIOR),
        ]
        processed = [dict(SKUCode='A', WhCode='L', Stock=9, Consumption=2,
                          GIT=1, Receipts=0, PSO=0, ReportDate=TODAY)]
        stages = {STAGES[-1]: {'tables': {'DailyDataProcessed': processed}}}
        def payload(rows):
            return {'raw_master_entry': {'business_date': TODAY},
                    'raw_daily_entry': {'prior_bpr': {'DailyConsumption': rows}}}
        expected = generated_bpr_daily_state(payload(deepcopy(opening)), stages)
        actual = generated_bpr_daily_state(payload(RecordRows.from_rows(opening)), stages)
        self.assert_rows_equal(expected, actual)

    def test_order_and_postrule_histories_match_eager_bags(self):
        summary = [
            dict(SKUCode='A', WhCode='L', NodeOrderCount=1, CummOrderCount=2,
                 NodeConsumption=3, ImportDate='2026-01-01'),
            dict(SKUCode='A', WhCode='L', NodeOrderCount=4, CummOrderCount=5,
                 NodeConsumption=6, ImportDate='2026-04-07'),
            dict(SKUCode='A', WhCode='L', NodeOrderCount=4, CummOrderCount=5,
                 NodeConsumption=6, ImportDate='2026-04-07'),
        ]
        state = dict(OrderDataSummary=deepcopy(summary), OrderRuleSummary=[
            dict(SKUCode='A', WhCode='L', NodeOrderCount=7,
                 CummOrderCount=8, NodeConsumption=9)])
        expected = update_order_summary(TODAY, deepcopy(state))['OrderDataSummary']
        state['OrderDataSummary'] = RecordRows.from_rows(summary)
        self.assert_rows_equal(expected, update_order_summary(TODAY, state)['OrderDataSummary'])

        histories = dict(
            DiscardedSuggestions=[dict(SKUCode='A', WhCode='L', SuggestionType=2,
                SuggestionDate='2026-04-07', DiscardCode=4)],
            SuggestionsLog=[dict(SKUCode='A', WhCode='L', Type=2, OldNorm=4,
                NewNorm=5, SuggestionDate='2026-04-07')]*2,
            SpikeReport=[dict(SKUCode='A', WhCode='L', SuspendFromDate='2026-04-07',
                SuspendTillDate=None)],
        )
        base = dict(**deepcopy(histories), LastBatchRunTbl=[{'LastRunDate': TODAY+'T00:00:00'}],
            Suggestions=[dict(SKUCode='A', WhCode='L', Type=2, NewNorm=5)],
            DBMMaster=[dict(SKUCode='A', WhCode='L', Norm=4, MinNorm=1)],
            SuspendSpikeTbl=[dict(SKUCode='A', WhCode='L', WaitStartDate=TODAY,
                                  WaitTillDate=None)])
        eager_discard = discard_suggestions(TODAY, deepcopy(base))
        eager_reports = generate_reports(TODAY, deepcopy(base))
        streamed = deepcopy(base)
        for name in histories:
            streamed[name] = RecordRows.from_rows(histories[name])
        actual_discard = discard_suggestions(TODAY, streamed)
        actual_reports = generate_reports(TODAY, streamed)
        self.assert_rows_equal(eager_discard['DiscardedSuggestions'], actual_discard['DiscardedSuggestions'])
        self.assert_rows_equal(eager_reports['SuggestionsLog'], actual_reports['SuggestionsLog'])
        self.assert_rows_equal(eager_reports['SpikeReport'], actual_reports['SpikeReport'])

    def test_completion_prunes_each_history_without_materializing(self):
        data = {'DailyConsumption': [{'ReportDate': '2026-03-08'}, {'ReportDate': '2026-03-09'}]}
        for table, field in (('BPRReport_RemarkDetails', 'RemarkDate'),
                             ('OpenExpeditRequestRemarksHistory', 'RemarkDate'),
                             ('InTransitWhereAboutsRemarks', 'RemarksDate')):
            data[table] = [{field: '2026-03-08T00:00:00'},
                           {field: '2026-03-08T00:00:00.003'}, {field: None}, {field: None}]
        expected = prune_bpr_history(deepcopy(data), [{'LastRunDate': datetime(2026, 6, 6)}],
                                     consumption_days=90, remark_days=90)
        streamed = {name: RecordRows.from_rows(rows) for name, rows in data.items()}
        actual = prune_bpr_history(streamed, [{'LastRunDate': datetime(2026, 6, 6)}],
                                   consumption_days=90, remark_days=90)
        for name in data:
            self.assert_rows_equal(expected[name], actual[name])

    def test_ordinal_lookup_caches_record_source_and_custom_normalized_key(self):
        calls = []
        source = [dict(SKUCode='A ', WHCode='l', value=1),
                  dict(SKUCode='a', WHCode='L ', value=2),
                  dict(SKUCode=None, WHCode='L', value=3)]
        rows = RecordRows(len(source), lambda: (calls.append('scan') or iter(deepcopy(source))))
        key = lambda row: (None if row['SKUCode'] is None else row['SKUCode'].rstrip().upper(),
                           row['WHCode'].rstrip().upper())
        with OrdinalLookup(rows, key=key) as lookup:
            self.assertEqual([row['value'] for row in lookup.matching(rows, ('A', 'L'))], [1, 2])
            self.assertEqual([row['value'] for row in lookup.matching(rows, (None, 'L'))], [3])
            self.assertIs(rows.ordinal_source(), rows.ordinal_source())
        self.assertEqual(calls, ['scan'])


if __name__ == '__main__':
    unittest.main()
