"""Focused report contracts; these are not acceptance-artifact replacements."""
from copy import deepcopy
import unittest
from mta.presentation.pick_post import produce
from mta.presentation.expedite_charts import queries,response
from mta.presentation.permissions import PermissionCodes


class PickPostTest(unittest.TestCase):
    def setUp(self):
        self.row=dict(SKUCode='337',WhCode='AG515802',ParentWhCode='LP001',VirtualNorm=220,
            StockForReqCalc=0,GIT=0,RationedReq=7,Norm=220,BlueReq=0)

    def test_typed_projection_duplicates_and_self_null_without_mutation(self):
        rows=[self.row,self.row,dict(self.row,ParentWhCode='AG515802')]; before=deepcopy(rows)
        result=produce(rows)
        self.assertEqual(result[0],result[1]); self.assertEqual(result[0]['PostPipelineInventoryPen'],'96.82')
        self.assertEqual(result[0]['PostPipelineInventoryColor'],'Red')
        self.assertIsNone(result[2]['PostPipelineInventoryPen']); self.assertEqual(rows,before)

    def test_source_thresholds_blue_grey_and_negative_norm(self):
        for changes,pen,colour in ((dict(VirtualNorm=3,Norm=3,RationedReq=1),'66.67','Red'),
            (dict(StockForReqCalc=221,RationedReq=0,BlueReq=2),'-0.45','Blue'),
            (dict(VirtualNorm=0,Norm=0,RationedReq=0),'-99999999.00','Grey'),
            (dict(VirtualNorm=-100,Norm=-100,RationedReq=0),'-100.00','White')):
            result=produce([dict(self.row,**changes)])[0]
            self.assertEqual((result['PostPipelineInventoryPen'],result['PostPipelineInventoryColor']),(pen,colour))

    def test_conflicting_update_is_not_given_invented_winner(self):
        with self.assertRaisesRegex(ValueError,'conflicting'):
            produce([self.row,dict(self.row,RationedReq=8)])


class ExpediteChartsTest(unittest.TestCase):
    def setUp(self):
        self.row=dict(SKUCode='337',WhCode='AG515802',ParentWhCode='LP001',RationedQty=7,
            PipelineInventoryColor='Black',PipelineInventoryPen='100.00',BRAge=12,BRAgeRedCount=3,
            BRAgeBlackCount=9,IsParent=1,IsReceiving=1)
        self.pick=dict(SKUCode='337',WhCode='AG515802',ParentWhCode='LP001',DispatchColor='Black',PostPipelineInventoryColor='Red')
        self.output={'ClosingState':[dict(importer=dict(
            SiteDescriptionTbl=[dict(WHCode=c,WHDescription=c) for c in ('AG515802','LP001')],
            LocationAttributeData=[dict(WHCode=c,LogisticsLocation='L',**{f'LL{i}':None for i in range(1,6)}) for c in ('AG515802','LP001')]),
            bpr=dict(BPRMaster=[dict(SKUCode='337',WHCode='LP001',ParentWhCode='LP001')]))]}

    def test_permissions_and_joins_precede_window_distinct(self):
        imp=self.output['ClosingState'][0]['importer']; imp['LocationAttributeData']*=2
        values=queries(self.output,[self.row],[self.pick],'parent',products=PermissionCodes({'337':2}),locations=None)
        self.assertEqual(values['critical'][0]['counts'],4)
        self.assertEqual(len(values['receiving']),1); self.assertEqual(values['receiving'][0]['ParentwiseCount'],4)

    def test_parent_prepost_cross_sku_join_and_child_scope(self):
        other=dict(self.pick,SKUCode='338',WhCode='LP001',ParentWhCode='AG515802')
        rows=[self.pick,other,other]
        result=queries(self.output,[self.row],rows,'parent',products={'337'},locations={'AG515802'})
        self.assertEqual(result['pre_post'][0]['BlackCount'],2)
        child=queries(self.output,[self.row],rows,'child',products={'337'},locations={'LP001'})
        self.assertEqual(child['receiving'],[]); self.assertEqual(child['pre_post'][0]['BlackCount'],0)

    def test_response_keeps_source_bug_and_age_not_binary_count(self):
        tables=queries(self.output,[dict(self.row,RationedQty=0)],[self.pick],'parent',products=None,locations=None)
        result=response(tables,'parent')['data']
        receiving=result['expediteDispatches']['maxPipelineInvBlackRedSKUWithRationedQuantityAvailableAtParentuiconfig']
        self.assertIsNone(receiving['data'][0]['LogisticsLocation'])
        nil=result['createAvailabilityAtParent']['maxEcoBlackRedWithNilRationedStockForRecievingLocations']['data'][0]
        self.assertEqual((nil['RedCount'],nil['BlackCount']),('3','9'))
        self.assertEqual(receiving['uiconfig'][0]['colPosition'],0)

    def test_unordered_label_conflict_is_flagged_not_repaired(self):
        tables=queries(self.output,[self.row],[self.pick],'parent',products=None,locations=None)
        tables['critical'].append(dict(tables['critical'][0],LogisticsLocation='Other'))
        with self.assertRaisesRegex(ValueError,'unordered'): response(tables,'parent')
