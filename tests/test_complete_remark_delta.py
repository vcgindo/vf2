"""Exact terminal remark expiry, independent of live comment/action owners."""
from copy import deepcopy
from datetime import date,datetime,time,timedelta
import unittest

from mta.domain.complete_daily_completion import prune_bpr_history
from mta.runtime.dated_history_delta import (
    COMPLETE_REMARKS,FAMILIES,fields,changes,Counts,Removal,Occurrence,family_enabled,source_table)

TODAY='2026-07-10'


def row(family,stamp):
    value=dict.fromkeys(fields(family))
    value.update(SKUCode='raw sku ',**{FAMILIES[family][0]:stamp})
    return value


class CompleteRemarkDeltaTests(unittest.TestCase):
    def test_original_pruner_all_horizons_null_cutoff_time_and_duplicates(self):
        for horizon in (-2,0,1,30):
            cutoff=datetime.combine(date.fromisoformat(TODAY)-timedelta(days=horizon),time())
            stamps=[None,(cutoff-timedelta(microseconds=1)).isoformat(),cutoff.isoformat(),
                    (cutoff+timedelta(microseconds=1)).isoformat(),
                    (cutoff+timedelta(microseconds=1)).isoformat(),'2027-01-01T00:00:00']
            source={'DailyConsumption':[]}
            source.update({f.rsplit('/',1)[1]:[row(f,t) for t in stamps] for f in COMPLETE_REMARKS})
            saved=deepcopy(source)
            actual=prune_bpr_history(source,[{'LastRunDate':TODAY}],consumption_days=1,remark_days=horizon)
            for f in COMPLETE_REMARKS:
                name=f.rsplit('/',1)[1];before=source[name];after=actual[name]
                self.assertEqual(after,[before[i] for i in (0,3,4,5)])
                events=list(changes(((Occurrence(0,i),v) for i,v in enumerate(before)),after,
                    family=f,today=TODAY,position=1,horizon=horizon))
                self.assertEqual(events,[Removal(Occurrence(0,1)),Removal(Occurrence(0,2)),Counts(6,4,0,2,4)])
                self.assertEqual(source_table(f),'complete/BPR/'+name)
            self.assertEqual(source,saved)

    def test_append_change_reorder_and_missing_frozen_horizon_refuse(self):
        for f in COMPLETE_REMARKS:
            before=[row(f,None),row(f,'2026-07-10T10:00:00')]
            for after in (before+[row(f,'2026-07-10T11:00:00')],list(reversed(before)),before[:1],
                          [dict(before[0],SKUCode='changed'),before[1]]):
                with self.subTest(family=f),self.assertRaises(ValueError):
                    list(changes(((Occurrence(0,i),r) for i,r in enumerate(before)),after,
                        family=f,today=TODAY,position=1,horizon=30))
            for horizon in (None,True,'30',2147483648):
                with self.subTest(horizon=horizon),self.assertRaises(ValueError):
                    list(changes([],[],family=f,today=TODAY,position=1,horizon=horizon))

    def test_optional_family_requires_actual_finalization_policy(self):
        for f in COMPLETE_REMARKS:
            self.assertFalse(family_enabled(f,{}))
            self.assertTrue(family_enabled(f,{'complete_daily':{
                'policy':'generic-finalization-v1','consumption_days':1,'remark_days':0}}))
            with self.assertRaises(ValueError):family_enabled(f,{'complete_daily':{}})
        self.assertTrue(family_enabled('closing/orders/SpikeOrderClosureHistory',{}))


if __name__=='__main__':unittest.main()
