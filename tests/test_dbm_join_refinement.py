import copy
import importlib.util
from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest

from mta.domain import dbm_suspensions as suspension
from mta.domain.dbm_ingestion import calculate_extended_ocp
from mta.domain.dbm_suspension_history import gather_suspension_history, CONTRIBUTORS

spec=importlib.util.spec_from_file_location('dbm_join_reference',Path(__file__).parent/'fixtures/dbm_join_reference.py')
old=importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
TODAY='2026-06-06'


class JoinDifferentialTests(unittest.TestCase):
    def compare(self,name,new,*args):
        before=copy.deepcopy(args)
        try:expected=getattr(old,name)(*copy.deepcopy(args))
        except Exception as error:
            with self.assertRaises(type(error)) as actual:new(*args)
            self.assertEqual(str(actual.exception),str(error))
        else:
            actual=new(*args)
            self.assertEqual(actual,expected)
            # Retained predecessors remain independent even after a later writer.
            if isinstance(actual,dict):
                actual['DBMMaster'][0]['Norm']=999
                actual['sentinel']['nested'].append('later writer')
            elif actual:actual[0]['ExtendedOCP']=999
        self.assertEqual(args,before)

    def state(self):
        masters=[dict(SKUCode=k,WhCode=w,Norm=norm,RLT=2,OCP=2)
            for k,w,norm in [('01','W',Decimal(9)),('01','W',Decimal(12)),
                             ('1','W',Decimal(9))]]
        daily=[dict(SKUCode=k,WhCode=w,ReportDate=d,Stock=stock,BlueZone=0,
                    Consumption=consumption,Receipts=receipts)
            for k,w in [('01','W'),('1','W'),('absent','W')]
            for d,stock,consumption,receipts in [('2026-06-04',0,2,1),
                ('2026-06-05',0,4,1),(date(2026,6,6),20,4,2),('2026-06-06',0,8,2)]]
        daily.insert(2,copy.deepcopy(daily[2]))
        return dict(DBMMaster=masters,DailyConsumption=daily,
            LastBatchRunTbl=[{'LastRunDate':TODAY+'T00:00:00'}],
            SuspendSpikeTbl=[dict(SKUCode='01',WhCode='W',WaitStartDate='2026-06-04',
                WaitTillDate='2026-06-05',IsRedEnabled=False,IsGreenEnabled=True)]*2,
            SuspendWhitesTbl=[dict(SKUCode='old',WhCode='W',IsRedEnabled=False)],
            SuspendSupplyIssueTbl=[dict(SKUCode='01',WhCode='W',SuspendDate='2026-06-04',
                ReceiptDate=None,IsRedEnabled=False)]*2,
            IntermediateTables=[{'table':'scratch','rows':[{'v':1}]}],sentinel={'nested':[1]})

    def test_suspension_bags_dates_norm_groups_and_nonmutation(self):
        for name in ('apply_white','apply_spike','apply_supply'):
            for variant in range(4):
                state=self.state()
                if variant==1:
                    for row in state['DailyConsumption']:row['Stock']=None;row['Consumption']=None
                if variant==2:state['DailyConsumption']=[]
                if variant==3:state['LastBatchRunTbl'][0]['LastRunDate']=TODAY+'T01:00:00'
                with self.subTest(name=name,variant=variant):self.compare(name,getattr(suspension,name),TODAY,state)

    def test_extended_ocp_order_ties_nulls_and_duplicate_master(self):
        attrs=[dict(SKUCode=k,WhCode=w,ExtendedOCP=0) for k,w in [('01','W'),('1','W')]]
        masters=[dict(**{k:v for k,v in a.items() if k!='ExtendedOCP'},OCP=2,RLT=1) for a in attrs]
        daily=[dict(SKUCode=a['SKUCode'],WhCode=a['WhCode'],ReportDate=d,Stock=0)
               for a in attrs for d in ('2026-06-04','2026-06-05','2026-06-05','2026-06-06')]
        self.compare('calculate_extended_ocp',calculate_extended_ocp,TODAY,attrs,masters,daily)
        daily[2]['Stock']=1
        self.compare('calculate_extended_ocp',calculate_extended_ocp,TODAY,attrs,masters,daily)
        self.compare('calculate_extended_ocp',calculate_extended_ocp,TODAY,attrs,masters+[masters[0]],[])
        masters[0]['OCP']=None
        self.compare('calculate_extended_ocp',calculate_extended_ocp,TODAY,attrs,masters,[])

    def test_history_bag_join_contributors_ambiguity_and_horizon(self):
        state=self.state()
        for table,_,_ in CONTRIBUTORS:state[table]=[]
        member=dict(SKUCode='01',WhCode='W',RedEnabled=False,GreenEnabled=True)
        state['SuspendStockType']=[copy.deepcopy(member),copy.deepcopy(member)]
        state['SuspendConsumptionType']=[copy.deepcopy(member),copy.deepcopy(member)]
        state['SuspendHistory']=[dict(ReportDate=d) for d in ('2026-03-08','2026-03-09',TODAY)]
        state['SuspendWhitesTbl']=[dict(SKUCode='01',WhCode='W',IsRedEnabled=False)]*2
        self.compare('gather_suspension_history',gather_suspension_history,TODAY,state)
        state['SuspendWhitesTbl'].append(dict(SKUCode='01',WhCode='W',IsRedEnabled=True))
        self.compare('gather_suspension_history',gather_suspension_history,TODAY,state)
