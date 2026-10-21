"""Complete ordered report bags, scalar failures and generation-owned lookups.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import patch
from mta.domain import (dbm_postrules as post, dbm_delisting as delist,
    dbm_phase_recommendation as phase, dbm_norm012 as norm,
    dbm_auto_acceptance as auto, dbm_norm_change_history as change)
from mta.domain.ordinal_lookup import OrderedIndex
from mta.row_sequences import RecordRows

TODAY = date(2026, 6, 6)


def attrs(**key):return dict(**key, **{f'c{i}':None for i in range(1,16)})


def state(n=1, depth=3):
    return dict(LastBatchRunTbl=[dict(LastRunDate=TODAY.isoformat()+'T00:00:00')],
        DBMMaster=[dict(SKUCode=str(i),WhCode='W',ParentWhCode='P',Norm=10,MinNorm=5,
                        OCP=4,MinOrderCount=5) for i in range(n)],
        Suggestions=[dict(SKUCode=str(i),WhCode='W',Type=1,NewNorm=12) for i in range(n)],
        SuggestionsLog=[], DiscardedSuggestions=[], SpikeReport=[],SuspendSpikeTbl=[],
        SKULocStandardAttributes=[dict(SKUCode=str(i),WhCode='W',ExtendedOCP=3) for i in range(n)],
        DailyConsumption=[dict(SKUCode=str(i),WhCode='W',ReportDate=TODAY.isoformat(),
            Consumption=0,Stock=1) for i in range(n) for _ in range(depth)],
        VFSettings=[dict(Parameter='DBMDelistingDataPointPercent',Value='0')],
        SKUDescriptionTbl=[dict(SKUCode=str(i),SKUDescription='Item, '+str(i)) for i in range(n)],
        SiteDescriptionTbl=[dict(WHCode='W',WHDescription='Warehouse, W')],
        SkuAttributeData=[attrs(SKUCode=str(i)) for i in range(n)],
        LocationAttributeData=[attrs(WHCode='W')],
        SkuLocAttributeData=[attrs(SKUCode=str(i),LocCode='W') for i in range(n)],
        PhaseInTbl=[],PhaseOutTbl=[],PhaseOutRecommendation=[],IntermediateTables=[],
        Norm0Norm1Norm2Report=[],Norm0_1_2ReportDetails=[],
        NormChangeLogTbl=[dict(SKUCode=str(i),WHCode='W',OldNorm=10,NewNorm=12,
            NormChangeDate=TODAY.isoformat(),NormChangeReason=1) for i in range(n)],
        ReasonCodes=[dict(Id=1,Reason='Native reason')])


def cases(n=1,depth=3):
    value=state(n,depth)
    delisting=deepcopy(value);delisting['Suggestions']=[]
    normstate=deepcopy(value)
    for row in normstate['DBMMaster']:row['Norm']=0
    for row in normstate['DailyConsumption']:row['Consumption']=2
    detail=norm.data_stage(TODAY,normstate,0,30)
    return [('D4-discard',post,post.discard_suggestions,(TODAY,value)),
        ('D4-report',post,post.generate_reports,(TODAY,value)),
        ('D6',delist,delist.delisting_recommendation,(TODAY,delisting)),
        ('D7',phase,phase.phase_recommendation,(TODAY,value,30,27)),
        ('D8-data',norm,norm.data_stage,(TODAY,normstate,0,30)),
        ('D8-detail',norm,norm.detail_stage,(detail,)),
        ('D9',auto,auto.automatic_acceptance,(TODAY,value)),
        ('D10',change,change.norm_change_history,(TODAY,value,7))]


class CaptureIndex(OrderedIndex):
    instances=[]
    enabled_override=True
    def __init__(self,*args,**kwargs):
        kwargs['enabled']=self.enabled_override
        super().__init__(*args,**kwargs)
        self.instances.append(self)


class DbmReportScanTests(unittest.TestCase):
    def equal_modes(self,module,function,args):
        before=deepcopy(args)
        with patch.object(module,'OrderedIndex',CaptureIndex):
            CaptureIndex.enabled_override=False
            expected=function(*deepcopy(args))
            CaptureIndex.enabled_override=True;CaptureIndex.instances=[]
            actual=function(*args)
        self.assertEqual(actual,expected)
        self.assertEqual(args,before)
        self.assertTrue(all(index._closed and index.owner is None for index in CaptureIndex.instances))
        return actual,list(CaptureIndex.instances)

    def test_complete_outputs_lists_and_real_file_backed_dimensions_histories(self):
        for name,module,function,args in cases(2):
            for streamed in (False,True):
                current=deepcopy(args)
                if streamed:
                    value=next(value for value in current if isinstance(value,dict))
                    for table in ('DailyConsumption','SKUDescriptionTbl','SiteDescriptionTbl',
                                  'SkuAttributeData','LocationAttributeData','SkuLocAttributeData',
                                  'NormChangeLogTbl'):
                        if table in value:value[table]=RecordRows.from_rows(value[table])
                with self.subTest(name=name,streamed=streamed):self.equal_modes(module,function,current)

    def test_independent_native_expected_projections(self):
        value=state(1,3)
        self.assertEqual(auto.automatic_acceptance(TODAY,value)['NormAcceptanceTbl'],
            [dict(SKUCode='0',WhCode='W',AcceptanceDate='2026-06-06',OldNorm=10,NewNorm=12)])
        self.assertEqual(list(post.generate_reports(TODAY,value)['SuggestionsLog']),
            [dict(SKUCode='0',WhCode='W',Type=1,OldNorm=10,NewNorm=12,SuggestionDate='2026-06-06')])
        value['Suggestions'][0]['NewNorm']=2
        discarded=post.discard_suggestions(TODAY,value)
        self.assertEqual(discarded['Suggestions'],[])
        self.assertEqual(list(discarded['DiscardedSuggestions']),[dict(SKUCode='0',WhCode='W',
            SuggestionType=1,SuggestionDate='2026-06-06',DiscardCode=4)])
        value['Suggestions']=[]
        self.assertEqual(delist.delisting_recommendation(TODAY,value)['DBMDelistingOfNormsWithHits'],
            [dict(SKUCode='0',SKUDescription='Item, 0',WhCode='W',WHDescription='Warehouse, W',
                Norm=10,OCP=3,MinOrderCount=5,ConsumptionCount=0,TotalConsumption=0,ConsumptionOcurrences='')])
        result=phase.phase_recommendation(TODAY,value,30,27)['PhaseOutRecommendation']
        self.assertEqual(len(result),1);self.assertEqual(len(result[0]),53)
        # Three same-day current-stock occurrences multiply three observations.
        self.assertEqual([result[0][k] for k in phase.FIELDS[:8]],['0','Item 0','W','Warehouse W',9,0,10,1])
        self.assertEqual(change.norm_change_history(TODAY,value,7)['ReportRows'],
            [dict(values=['0','Item  0','W','Warehouse  W',10,12,'2026-06-06','Native reason'])])

    def test_duplicate_cartesian_bags_spelling_nulls_and_conflicting_parent(self):
        value=state(1,3);value['DBMMaster']*=2;value['SKUDescriptionTbl']*=2
        value['SiteDescriptionTbl']*=2;value['ReasonCodes']*=2
        self.assertEqual(len(auto.automatic_acceptance(TODAY,value)['NormAcceptanceTbl']),2)
        self.assertEqual(len(change.norm_change_history(TODAY,value,7)['ReportRows']),8)
        value['Suggestions'][0]['SKUCode']='0 '
        self.assertEqual(len(auto.automatic_acceptance(TODAY,value)['NormAcceptanceTbl']),2)
        value['Suggestions'][0]['SKUCode']=None
        self.assertEqual(auto.automatic_acceptance(TODAY,value)['NormAcceptanceTbl'],[])
        value=state(1,1);value['DBMMaster'][0]['Norm']=0
        data=norm.data_stage(TODAY,value,0,30)
        data['SkuAttributeData']*=2;data['SkuLocAttributeData']*=2
        self.assertEqual(len(norm.detail_stage(data)['Norm0_1_2ReportDetails']),4)
        data['DBMMaster'] += [dict(SKUCode='0',WhCode='P',Norm=4),dict(SKUCode='0',WhCode='P',Norm=5)]
        with self.assertRaisesRegex(norm.AmbiguousReport,'Conflicting parent Norm'):norm.detail_stage(data)

    def test_date_validation_eligibility_and_empty_candidates_keep_error_precedence(self):
        value=state(2,1);value['DailyConsumption'].append(dict(SKUCode='other',WhCode='W',ReportDate='bad'))
        with self.assertRaises(ValueError):phase.phase_recommendation(TODAY,value,30,29)
        for master in value['DBMMaster']:master['Norm']=0
        self.assertEqual(phase.phase_recommendation(TODAY,value,30,29)['PhaseOutRecommendation'],[])
        value=state();value['DBMMaster']=[];value['Suggestions']=[dict(Type=1)]
        self.assertEqual(auto.automatic_acceptance(TODAY,value)['NormAcceptanceTbl'],[])
        value=state();value['Suggestions'][0]['NewNorm']=2**31
        with self.assertRaisesRegex(ValueError,'signed32'):auto.automatic_acceptance(TODAY,value)
        value=state();value['DailyConsumption'][0]['Consumption']=2
        value['DailyConsumption'][1]['Consumption']=3
        value['Suggestions']=[]
        with self.assertRaisesRegex(ValueError,'unordered STRING_AGG'):delist.delisting_recommendation(TODAY,value)
        value=state();del value['Suggestions'][0]['SKUCode']
        with self.assertRaisesRegex(KeyError,'SKUCode'):auto.automatic_acceptance(TODAY,value)
        value=state();value['Suggestions']=[];value['DBMMaster']=[{}]
        self.assertEqual(post.generate_reports(TODAY,value)['SuggestionsLog'],[])

    def test_per_family_n_2n_4n_candidate_counts(self):
        metrics={}
        for n in (8,16,32):
            for name,module,function,args in cases(n):
                with self.subTest(name=name,n=n):
                    _,indexes=self.equal_modes(module,function,args)
                    measured=tuple(sum(getattr(i,k) for i in indexes) for k in ('indexed_rows','probes','candidate_rows'))
                    metrics[name,n]=measured
                    self.assertLessEqual(measured[2],12*n)
        for name,_,_,_ in cases():
            for a,b in ((8,16),(16,32)):
                # D7 retains a first full validation pass; later indexed probes
                # have exact candidate count 11*n-6 (not a zero-intercept line).
                self.assertTrue(all(y<=2*x+6 for x,y in zip(metrics[name,a],metrics[name,b])))


if __name__=='__main__':unittest.main()
