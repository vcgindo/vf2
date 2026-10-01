"""Expedite unit boundaries, not a substitute synthetic acceptance artifact."""
from copy import deepcopy
import unittest
from mta.presentation.expedite import produce,potential_loss
from mta.presentation.expedite_views import counts
from mta.presentation.permissions import PermissionCodes


class ExpediteTest(unittest.TestCase):
    def setUp(self):
        self.row=dict(SKUCode='337',WhCode='AG515802',ParentWhCode='LP001',PhysicalInventoryPen='100.00',
            PhysicalInventoryColor='Black',DispatchPen='100.00',DispatchColor='Black',RationedReq=7,
            Req=8,Norm=220,VirtualNorm=220,Stock=0,GIT=0)
        self.master=dict(SKUCode='337',WhCode='AG515802',Norm=220,RLT=4)
        self.standard=dict(SKUCode='337',WhCode='AG515802',Price='1.000')
        self.age=dict(SKUCode='337',WhCode='AG515802',BRAge=12,BRAgeRedCount=0,BRAgeBlackCount=12)
        self.parent=dict(SKUCode='337',WhCode='LP001',Stock=50,DispatchColor='Green')

    def produce(self,**kw):
        args=dict(pick=[self.row],masters=[self.master],standards=[self.standard],rationed=[self.parent],ages=[self.age])
        args.update(kw); return produce(**args)

    def test_projection_and_existing_age_values_no_mutation(self):
        before=deepcopy((self.row,self.master,self.standard,self.parent,self.age))
        row=self.produce()[0]
        self.assertEqual((row['StockAtParent'],row['ParentPipelineInventoryColor'],row['BRAge']),(50,'Green',12))
        self.assertEqual((row['IsParent'],row['IsReceiving']),(False,True))
        self.assertEqual((self.row,self.master,self.standard,self.parent,self.age),before)

    def test_left_join_and_multiplicity(self):
        self.assertEqual(len(self.produce(pick=[self.row]*2,masters=[self.master]*3,standards=[self.standard]*2)),12)
        self.assertEqual(self.produce(standards=[])[0]['PotentialLossPerDay'],0)
        self.assertIsNone(self.produce(rationed=[])[0]['StockAtParent'])
        self.assertEqual(potential_loss(0,None,'9.000'),0)
        self.assertIsNone(potential_loss(-1,1,'9.000'))
        self.assertEqual(potential_loss(2,1,'1.000'),1)

    def test_predicates_membership_and_ambiguous_update_never_invented(self):
        for changed in (dict(self.row,ParentWhCode=None),dict(self.row,ParentWhCode='AG515802'),dict(self.row,DispatchColor='Green')):
            self.assertEqual(self.produce(pick=[changed],ages=[]),[])
        with self.assertRaisesRegex(ValueError,'ageing state'): self.produce(ages=[])
        with self.assertRaisesRegex(ValueError,'ambiguous parent'):
            self.produce(rationed=[self.parent,dict(self.parent,Stock=51)])
        with self.assertRaisesRegex(ValueError,'ambiguous age'):
            self.produce(ages=[self.age,dict(self.age,BRAge=13)])

    def test_counts_direction_permission_and_join_multiplicity(self):
        imp=dict(SKUDescriptionTbl=[dict(SKUCode='337')]*2,
            SiteDescriptionTbl=[dict(WHCode='AG515802'),dict(WHCode='LP001')],
            SkuAttributeData=[dict(SKUCode='337')],LocationAttributeData=[dict(WHCode='AG515802')],
            SkuLocAttributeData=[dict(SKUCode='337',LocCode='AG515802')]*3)
        output={'ClosingState':[dict(importer=imp,dbm=dict(SKULocStandardAttributes=[self.standard]))]}
        rows=self.produce()+[dict(self.produce()[0],RationedQty=0)]
        values=counts(output,rows,'parent',products=PermissionCodes({'337':2}),locations={'AG515802'})
        self.assertEqual(values,dict(expediteDispatches=12,createAvailabilityAtParent=12))
        self.assertEqual(counts(output,rows,'child',products=None,locations={'AG515802'}),
                         dict(expediteDispatches=0,createAvailabilityAtParent=0))
        self.assertEqual(counts(output,rows,'child',products=None,locations={'LP001'})['expediteDispatches'],6)


if __name__=='__main__': unittest.main()
