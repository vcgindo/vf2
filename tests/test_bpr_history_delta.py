"""BPR's own import/update/prune owners, independent of DBM retention."""
from copy import deepcopy
import unittest

from mta.application.r1_daily_entry import generated_bpr_daily_state, STAGES
from mta.domain.late_bpr_transfer import update_bpr, FIELD_MAP
from mta.domain.complete_daily_completion import prune_bpr_history
from mta.runtime.dated_history_delta import changes, fields, Counts, Fact, Occurrence, source_table
from tests.test_dated_history_delta import reconstruct


FAMILY='closing/bpr/DailyConsumption'
TODAY='2026-04-10'


def row(stamp=TODAY, **values):
    result=dict.fromkeys(fields(FAMILY),0)
    result.update(SKUCode='sku ',WHCode='wh',ReportDate=stamp)
    result.update(values)
    return result


def produced(before, *, horizon, today=TODAY):
    incoming=[{('WhCode' if k=='WHCode' else k):v for k,v in row(today,Consumption=3).items() if k!='BlueZone'}]*2
    incoming.append(dict(incoming[0],ReportDate='2026-01-01'))
    imported=generated_bpr_daily_state(
        {'raw_master_entry':{'business_date':today},'raw_daily_entry':{'prior_bpr':{'DailyConsumption':before}}},
        {STAGES[-1]:{'tables':{'DailyDataProcessed':incoming}}})
    report=dict.fromkeys(FIELD_MAP.values(),1)
    report.update(SKUCode='SKU',WhCode='WH',BlueReq=7)
    updated=update_bpr(dict(BPRLastBatchRunTbl=[{'LastRunDate':today+'T00:00:00'}],
                           BPR_Table=[],BPRDailyConsumption=imported,vf_RationedReqReport=[report]))['BPRDailyConsumption']
    if horizon is None:
        return updated
    return prune_bpr_history(dict(DailyConsumption=updated,BPRReport_RemarkDetails=[],
        OpenExpeditRequestRemarksHistory=[],InTransitWhereAboutsRemarks=[]),
        [{'LastRunDate':today}],consumption_days=horizon,remark_days=1)['DailyConsumption']


class BprHistoryDeltaTests(unittest.TestCase):
    def classify(self,before,after,horizon,*,today=TODAY):
        return list(changes(((Occurrence(0,n),r) for n,r in enumerate(before)),iter(after),
            family=FAMILY,today=today,position=1,horizon=horizon))

    def test_actual_owners_cutoff_null_future_duplicates_and_bluezone(self):
        before=[row('2026-03-11'),row('2026-03-12'),row('2026-03-12'),row(None),row(),row('2026-04-20')]
        saved=deepcopy(before)
        after=produced(before,horizon=30)
        events=self.classify(before,after,30)
        self.assertEqual(events[-1],Counts(6,4,2,2,6))
        self.assertEqual(reconstruct(before,events),after)
        self.assertEqual([e.values['BlueZone'] for e in events if isinstance(e,Fact)],[7,7])
        self.assertEqual(before,saved)

    def test_independent_zero_negative_one_and_absent_finalization(self):
        before=[row('2026-01-01'),row('2026-04-09'),row(None),row('2026-04-20'),row()]
        for horizon in (None,0,-1,1,30):
            with self.subTest(horizon=horizon):
                after=produced(before,horizon=horizon)
                events=self.classify(before,after,horizon)
                self.assertEqual(reconstruct(before,events),after)
                self.assertEqual(events[-1].inserted,0 if horizon in (0,-1) else 2)
        # Unlike DBM cleanup, this producer imposes no 1753 timestamp bound.
        after=produced([row('1752-01-01')],horizon=2,today='1752-01-02')
        self.assertEqual(reconstruct([row('1752-01-01')],self.classify(
            [row('1752-01-01')],after,2,today='1752-01-02')),after)

    def test_own_successor_keeps_old_values_order_and_emits_only_new_facts(self):
        first=produced([],horizon=30)
        second=produced(first,horizon=30,today='2026-04-11')
        events=self.classify(first,second,30,today='2026-04-11')
        self.assertEqual(events[-1],Counts(2,2,2,0,4))
        self.assertEqual(reconstruct(first,events),second)
        self.assertEqual(second[:2],first)

    def test_wrong_history_family_or_retention_cannot_be_silently_used(self):
        self.assertEqual(source_table(FAMILY),'BPR/DailyConsumption')
        self.assertIn('WHCode',fields(FAMILY));self.assertNotIn('WhCode',fields(FAMILY))
        before=[row('2026-04-05')]
        after=produced(before,horizon=30)
        with self.assertRaises(ValueError):self.classify(before,after,1)
        with self.assertRaises(ValueError):
            list(changes([],after,family='closing/dbm/DailyConsumption',today=TODAY,position=1,horizon=30))

    def test_retained_mutation_and_bad_late_fact_refuse(self):
        before=[row('2026-04-09',Consumption=3)]
        for after in ([dict(before[0],Consumption=4)],[dict(before[0],Consumption=True)],
                      before+[row('2026-04-11')]):
            with self.subTest(after=after),self.assertRaises(ValueError):self.classify(before,after,30)
        for horizon in (True,'30',2147483648):
            with self.subTest(horizon=horizon),self.assertRaises(ValueError):self.classify([],[],horizon)


if __name__=='__main__':unittest.main()
