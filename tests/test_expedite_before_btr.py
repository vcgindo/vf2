"""Explicit CollectDataToExpediteDispatches expectations before BTR ageing."""
from copy import deepcopy
import unittest

from mta.presentation.expedite import AGE_FIELDS,produce,produce_before_btr
from tests import test_expedite_presentation as fixtures


class BeforeBtrTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.ExpediteTest();fixture.setUp()
        self.pick=fixture.row;self.master=fixture.master;self.standard=fixture.standard
        self.parent=fixture.parent;self.age=fixture.age

    def project(self,**changes):
        args=dict(pick=[self.pick],masters=[self.master],standards=[self.standard],rationed=[self.parent])
        args.update(changes)
        return produce_before_btr(**args)

    def test_complete_row_has_sql_insert_null_ages_and_parent_update(self):
        before=deepcopy((self.pick,self.master,self.standard,self.parent))
        self.assertEqual(self.project(),[dict(
            SKUCode='337',WhCode='AG515802',ParentWhCode='LP001',PhysicalInventoryPen='100.00',
            PhysicalInventoryColor='Black',PipelineInventoryPen='100.00',PipelineInventoryColor='Black',
            RationedQty=7,Req=8,StockAtParent=50,ParentPipelineInventoryColor='Green',RLT=4,
            BRAge=None,BRAgeRedCount=None,BRAgeBlackCount=None,Norm=220,VirtualNorm=220,Stock=0,GIT=0,
            PotentialLossPerDay=0,IsParent=False,IsReceiving=True)])
        self.assertEqual((self.pick,self.master,self.standard,self.parent),before)

    def test_bag_joins_missing_left_join_and_predicates(self):
        rows=self.project(pick=[self.pick]*2,masters=[self.master]*3,standards=[self.standard]*2)
        self.assertEqual(len(rows),12)
        self.assertEqual(rows,[self.project()[0]]*12)
        missing=self.project(standards=[],rationed=[])[0]
        self.assertEqual(missing['PotentialLossPerDay'],0)
        self.assertIsNone(missing['StockAtParent'])
        self.assertIsNone(missing['ParentPipelineInventoryColor'])
        for changed in (dict(self.pick,ParentWhCode=None),dict(self.pick,ParentWhCode='AG515802'),
                        dict(self.pick,WhCode=None),dict(self.pick,DispatchColor='Green')):
            self.assertEqual(self.project(pick=[changed]),[])
        with self.assertRaisesRegex(ValueError,'ambiguous parent'):
            self.project(rationed=[self.parent,dict(self.parent,Stock=51)])
        with self.assertRaisesRegex(ValueError,'NOT NULL PipelineInventoryPen'):
            self.project(pick=[dict(self.pick,DispatchPen=None)])

    def test_current_population_is_parent_uses_its_actual_rows(self):
        parent_pick=dict(self.pick,WhCode='LP001',ParentWhCode='TOP')
        rows=self.project(pick=[self.pick,parent_pick],masters=[self.master,dict(self.master,WhCode='LP001')])
        self.assertEqual([row['IsParent'] for row in rows],[False,True])
        self.assertTrue(all(row[field] is None for row in rows for field in AGE_FIELDS))

    def test_full_retains_accepted_age_requirement_and_all_other_cells(self):
        args=dict(pick=[self.pick],masters=[self.master],standards=[self.standard],rationed=[self.parent])
        full=produce(**args,ages=[self.age]);partial=self.project()
        self.assertEqual([{k:v for k,v in row.items() if k not in AGE_FIELDS} for row in full],
                         [{k:v for k,v in row.items() if k not in AGE_FIELDS} for row in partial])
        self.assertEqual([full[0][field] for field in AGE_FIELDS],[12,0,12])
        with self.assertRaisesRegex(ValueError,'ageing state'):produce(**args,ages=[])
        with self.assertRaisesRegex(ValueError,'ambiguous age'):
            produce(**args,ages=[self.age,dict(self.age,BRAge=13)])
        with self.assertRaisesRegex(ValueError,'membership differs'):
            produce(**args,ages=[self.age,dict(self.age,WhCode='UNOWNED')])


if __name__=='__main__':unittest.main()
