"""Configured same-day DBM report predicates, independent of trial horizons."""
import copy
from datetime import date
import unittest
from unittest.mock import patch

from mta.domain.dbm_norm_change_report import norm_change_report
from mta.domain.dbm_norm_change_history import norm_change_history


class ReportHorizonTests(unittest.TestCase):
    def state(self):
        def change(day, reason=1, sku='Sku', wh='Loc'):
            return dict(SKUCode=sku,WHCode=wh,OldNorm=8,NewNorm=12,
                NormChangeDate=day,NormChangeReason=reason)
        return dict(LastBatchRunTbl=[dict(LastRunDate='2037-04-10T00:00:00')],
            NormChangeLogTbl=[change('2037-04-10'),change('2037-04-09'),
                change('2037-03-12'),change('2037-03-11'),change(None),change('2037-04-10',None)],
            ReasonCodes=[dict(Id=1,Reason='Increase'),dict(Id=1,Reason=None)],
            SKUDescriptionTbl=[dict(SKUCode='SKU ',SKUDescription='One, two'),dict(SKUCode='Sku',SKUDescription=None)],
            SiteDescriptionTbl=[dict(WHCode='loc',WHDescription='Here, there')])

    def test_export_horizons_keep_inclusive_cutoff_and_duplicate_reason_join(self):
        state=self.state();before=copy.deepcopy(state)
        for horizon,days in ((1,['2037-04-10']),(2,['2037-04-10','2037-04-09']),
                (30,['2037-04-10','2037-04-09','2037-03-12']),
                (31,['2037-04-10','2037-04-09','2037-03-12','2037-03-11'])):
            with self.subTest(horizon=horizon):
                rows=norm_change_report('2037-04-10',state,horizon)['ReportRows']
                self.assertEqual([row['values'][4] for row in rows],[day for day in days for _ in range(2)])
                self.assertEqual([row['values'][-1] for row in rows],['"Increase"',None]*len(days))
        self.assertEqual(state,before)

    def test_history_horizons_keep_exclusive_cutoff_nulls_and_join_multiplicity(self):
        state=self.state();before=copy.deepcopy(state)
        for horizon,days in ((1,['2037-04-10']),(7,['2037-04-10','2037-04-09']),
                (30,['2037-04-10','2037-04-09','2037-03-12'])):
            with self.subTest(horizon=horizon):
                rows=norm_change_history(date(2037,4,10),state,horizon)['ReportRows']
                expected=[day for day in days for _ in range(4)]
                # NULL reason still appears in history with a nonmatching left join.
                expected.insert(4,'2037-04-10');expected.insert(5,'2037-04-10')
                self.assertEqual([row['values'][6] for row in rows],expected)
                self.assertEqual(rows[0]['values'][1:4],['One  two','Loc','Here  there'])
                self.assertIsNone(rows[2]['values'][1])
        self.assertEqual(state,before)

    def test_null_join_keys_do_not_match_null_description_or_reason_keys(self):
        state=self.state()
        state['NormChangeLogTbl']=[dict(SKUCode=None,WHCode=None,OldNorm=None,NewNorm=None,
            NormChangeDate='2037-04-10',NormChangeReason=None)]
        state['SKUDescriptionTbl']=[dict(SKUCode=None,SKUDescription='Not a match')]
        state['SiteDescriptionTbl']=[dict(WHCode=None,WHDescription='Not a match')]
        state['ReasonCodes']=[dict(Id=None,Reason='Not a match')]
        self.assertEqual(norm_change_report('2037-04-10',state,30)['ReportRows'],[])
        self.assertEqual(norm_change_history('2037-04-10',state,30)['ReportRows'],[
            {'values':[None,None,None,None,None,None,'2037-04-10',None]}])

    def test_zero_negative_future_horizons_and_reason_filter_are_not_defaulted(self):
        state=self.state();row=copy.deepcopy(state['NormChangeLogTbl'][0])
        row['NormChangeDate']='2037-04-11';state['NormChangeLogTbl'].append(row)
        row=copy.deepcopy(row);row['NormChangeReason']=100;state['NormChangeLogTbl'].append(row)
        self.assertEqual(len(norm_change_report('2037-04-10',state,0)['ReportRows']),2)
        self.assertEqual(norm_change_report('2037-04-10',state,-1)['ReportRows'],[])
        self.assertEqual(len(norm_change_history('2037-04-10',state,0)['ReportRows']),6)
        self.assertEqual(norm_change_history('2037-04-10',state,-1)['ReportRows'],[])

    def test_invalid_horizons_dates_and_bounds_fail_without_changing_input(self):
        state=self.state();before=copy.deepcopy(state)
        for producer in (norm_change_report,norm_change_history):
            for horizon in (None,True,'30',2**31,-(2**31),2**31-1):
                with self.subTest(producer=producer,horizon=horizon),self.assertRaises(ValueError):
                    producer('2037-04-10',state,horizon)
            wrong=copy.deepcopy(state);wrong['LastBatchRunTbl'].append(wrong['LastBatchRunTbl'][0])
            with self.assertRaises(ValueError):producer('2037-04-10',wrong,30)
        self.assertEqual(state,before)

    def test_actual_selected_dispatch_consumes_configured_horizons(self):
        from mta.domain import dbm_selected_chain as chain
        config=dict(AutoDBMActive=0,PhaseOutRecommendation30Days=0,PhaseOutRecommendation60Days=0,
            PhaseOutRecommendation90Days=0,DBMNormChangeReportHorizon=30,NormChangeLogHorizon=30,
            ActivateNormChangeLogReport=1,GatherSuspensionHistory=0,DailyConsumptionHorizonDBM=370)
        state=self.state();state['DBMSettingsTbl']=[]
        names=('update_order_summary','norm1_advisory','gather_suspension_history','daily_cleanup')
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.object(chain,'connected_stages',return_value=[('ingestion',state)]))
            stack.enter_context(patch.object(chain,'postrule_stages',side_effect=lambda today,current:[]))
            stack.enter_context(patch.object(chain,'selected_norm012_stages',return_value=[]))
            for name in names:stack.enter_context(patch.object(chain,name,side_effect=lambda *args:args[1]))
            stages=dict(chain.selected_stages('2037-04-10',state,{},config))
        self.assertEqual(stages['norm-change-export']['ReportRows'],norm_change_report('2037-04-10',state,30)['ReportRows'])
        self.assertEqual(stages['norm-change-history']['ReportRows'],norm_change_history('2037-04-10',state,30)['ReportRows'])
