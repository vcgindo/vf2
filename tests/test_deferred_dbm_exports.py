"""Deferred exports preserve original complete cell values and source bags.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import unittest
from copy import deepcopy
from mta.domain.deferred_dbm_exports import defer,render,SOURCES
from mta.domain.dbm_norm_change_report import norm_change_report
from mta.domain.dbm_norm_change_history import norm_change_history
from mta.domain.dbm_norm012 import export_stage
from mta.row_sequences import RecordRows
from mta.serialization import storage


class DeferredExportTests(unittest.TestCase):
    def test_norm_change_and_history_match_complete_original_cells_and_order(self):
        state=dict(LastBatchRunTbl=[dict(LastRunDate='2026-04-08T00:00:00')],
            NormChangeLogTbl=[dict(SKUCode='337',WHCode='W',NewNorm=2,OldNorm=None,NormChangeDate='2026-04-08',NormChangeReason=1)]*2,
            ReasonCodes=[dict(Id=1,Reason='reason'),dict(Id=1,Reason=None)],
            SKUDescriptionTbl=[dict(SKUCode='337',SKUDescription='Name,one'),dict(SKUCode='337',SKUDescription=None)],
            SiteDescriptionTbl=[dict(WHCode='W',WHDescription='WH,name')])
        for kind,producer,horizon in (('norm-change',norm_change_report,1),('norm-history',norm_change_history,7)):
            before=deepcopy(state)
            expected=producer('2026-04-08',state,horizon,_owned=True)
            captured=defer('2026-04-08',state,kind,horizon=horizon)
            self.assertNotIn('ReportRows',captured)
            for spooled in (False,True):
                sources={name:RecordRows.from_rows(state[name]) if spooled else state[name] for name in SOURCES[kind]}
                result=render('2026-04-08',captured['_DeferredExport'],sources)
                self.assertEqual(storage(result),storage({name:expected[name] for name in ('ReportHeader','ReportRows')}))
            self.assertEqual(state,before)

    def test_norm012_preserves_quotes_nulls_and_duplicate_cells(self):
        names=['SKUCode','SKUName','WHCode','WhName','ParentWhCode','ParentNorm','NumOfDaysSold','TotalSale','Occurances']
        config=[dict(ReportName='Norm_0_1_2Report',Visible=True,Col_Position=i,Col_Code=n,Header=n) for i,n in enumerate(names)]
        row=dict(SKUCode='337',SKUName='Name,"quoted"',WhCode='W',WhName=None,ParentWhCode='P',ParentNorm=1,NumOfDaysSold=2,TotalSale=3,Occurances='[07/04/26 - 3]')
        state=dict(ui_ReportConfigurations=config,Norm0_1_2ReportDetails=[row,dict(row)])
        before=deepcopy(state);captured=defer('2026-04-08',state,'norm012')
        for spooled in (False,True):
            sources={name:RecordRows.from_rows(state[name]) if spooled else state[name] for name in SOURCES['norm012']}
            expected=export_stage(state)
            self.assertEqual(render('2026-04-08',captured['_DeferredExport'],sources),{name:expected[name] for name in ('ReportHeader','ReportRows')})
        self.assertEqual(state,before)

    def test_bad_config_and_cutoff_reject_at_original_operational_boundary(self):
        with self.assertRaises(ValueError):defer('2026-04-08',dict(ui_ReportConfigurations=[]),'norm012')
        with self.assertRaises(ValueError):defer('2026-04-08',dict(LastBatchRunTbl=[]),'norm-change',horizon=1)


if __name__=='__main__':unittest.main()
