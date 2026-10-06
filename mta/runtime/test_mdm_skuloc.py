"""Migration-enabled master-3 proof against independently captured native rows."""
import gzip
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

from mta.mdm import skuloc
from mta.mdm import skuloc_input, skuloc_tasks, skuloc_reads
from mta.mdm.location_source import install_location
from mta.mdm.skuloc_source import install_skuloc
from mta.mdm.source import install_sku
from mta.mdm.task_reads import TaskDenied
from mta.runtime.mdm_models import (MdmFamilySource, MdmLocationAttributes, MdmSkuAttributes,
    MdmSource, MdmSubTask)
from mta.runtime.mdm_skuloc_models import (MdmSkuLocCurrent, MdmSkuLocHistory,
    MdmSkuLocAddApproved, MdmSkuLocMasterPair, MdmSkuLocModifyApproved,
    MdmSkuLocModifyRequested, MdmSkuLocPair, MdmSkuLocRemoveApproved,
    MdmSkuLocRemoveRequested)


class SkuLocationCurrentPostgresTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root=Path(os.environ['MDM_SKULOC_CAPTURE_DIR'])
        cls.source=install_sku(Path(os.environ['MDM_CAPTURE_DIR']))
        install_location(Path(os.environ['MDM_LOCATION_CAPTURE_DIR']),cls.source)
        install_skuloc(cls.root,cls.source)
        cls.native=json.loads(gzip.decompress((cls.root/'native-current-skuloc.json.gz').read_bytes()))
        cls.native.update(json.loads(gzip.decompress((cls.root/'native-current-actual-actor3.json.gz').read_bytes())))
        products=json.loads((Path(os.environ['MDM_CAPTURE_DIR'])/'native-permissions.json').read_text())['products']['records']
        location_raw=json.loads(gzip.decompress((Path(os.environ['MDM_LOCATION_CAPTURE_DIR'])/'LOCATION_PERMISSION.json.gz').read_bytes()))
        locations=[dict(id=row['id'],**{'level_'+str(i):row['location_heirarchy_'+str(i)] for i in range(1,4)}) for row in location_raw]
        cls.catalogue={'products':{'records':products},'locations':{'records':locations}}

    def test_full_fields_count_order_and_representative_page(self):
        comparisons=[]
        attempt=os.environ.get('MDM_PROOF_ATTEMPT','manual')
        with patch('mta.mdm.skuloc.permission_catalogue',return_value=self.catalogue):
            for name,expected in self.native.items():
                payload=dict(id=3,fields=[{'key':key} for key in skuloc.ALIASES],filters=[],
                    product_permissions=expected['product_permissions'],
                    location_permissions=expected['location_permissions'])
                count=skuloc.read(self.source,payload,count=True)
                actual=skuloc.read(self.source,payload) or []
                payload['paginationParameter']={'pageNumber':1,'recordsPerPage':100}
                page=skuloc.read(self.source,payload) or []
                encode=lambda row:json.dumps(row,sort_keys=True,separators=(',',':'))
                item=dict(profile=name,rows=len(actual),expected_rows=len(expected['rows']),
                    complete_bags=Counter(map(encode,actual))==Counter(map(encode,expected['rows'])),
                    unpaged_exact=actual==expected['rows'],page_exact=page==expected['pages'][0],
                    count_exact=count==str(expected['count']),
                    positions_differ=sum(a!=b for a,b in zip(actual,expected['rows'])))
                comparisons.append(item)
                (self.root/('modern-current-'+attempt+'-'+name+'.json.gz')).write_bytes(
                    gzip.compress(json.dumps({'rows':actual,'page1_100':page},separators=(',',':')).encode(),mtime=0))
        (self.root/('current-comparison-'+attempt+'.json')).write_text(json.dumps(comparisons,indent=2))
        # Human approval call_9QfAPeRqplgZiMfwKfKiZrJE is limited to these
        # unpaged current bags. Paged RANK membership/order remains exact.
        self.assertTrue(all(all(item[key] for key in ('complete_bags','page_exact','count_exact'))
                            for item in comparisons),json.dumps(comparisons))

    def test_pins_and_source_occurrence_counts(self):
        family=MdmFamilySource.objects.get(source=self.source,master_id=3)
        self.assertEqual(family.receipt['NMSAllItems']['rows'],97097)
        self.assertEqual(MdmSkuLocCurrent.objects.filter(source=self.source,owner='Importer').count(),97097)
        self.assertEqual(MdmSkuLocPair.objects.filter(source=self.source,owner='Importer').count(),97097)
        self.assertEqual(MdmSkuLocMasterPair.objects.filter(source=self.source,owner='Importer').count(),97097)
        with self.assertRaises(ValueError): install_skuloc(self.root,self.source)

    def test_configuration_is_exact_captured_order(self):
        self.assertEqual([field['key'] for field in skuloc.configuration('add')[0]['fields']],list(skuloc.ALIASES))
        self.assertEqual(skuloc.DRAFT_ALIASES['spr'],'StockPercentForRat')
        self.assertEqual(skuloc.ALIASES['spr'],'StockPercentForRationing')
        self.assertEqual(skuloc.ALIASES['wc'],'WhCode')


class SkuLocationWorkflowPostgresTests(TestCase):
    def setUp(self):
        self.source=MdmSource.objects.create(digest='3'*64,database_name='owned-test',
            dll_digest='0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346',receipt={})
        self.catalogue={'products':{'records':[
            {'id':1,'level_1':'P','level_2':'A','level_3':'X'},
            {'id':2,'level_1':'P','level_2':'B','level_3':'Y'}]},
            'locations':{'records':[
            {'id':10,'level_1':'L','level_2':'A','level_3':'X'},
            {'id':11,'level_1':'L','level_2':'B','level_3':'Y'}]}}
        MdmSkuAttributes.objects.create(source=self.source,owner='Importer',ordinal=1,
            SKUCode='S1',SL1='P',SL2='A',SL3='X')
        MdmLocationAttributes.objects.create(source=self.source,owner='Importer',ordinal=1,
            WHCode='W1',LL1='L',LL2='A',LL3='X')
        MdmSkuLocPair.objects.create(source=self.source,owner='Importer',ordinal=1,
            SKUCode='S1',LocCode='W1',PackSize=1,StockPercentForRationing=100,
            NormPercentReservation=0,NonNMS=False)
        MdmSkuLocMasterPair.objects.create(source=self.source,owner='Importer',ordinal=1,
            SKUCode='S1',WhCode='W1',Norm=10,MinNorm=2,RLT=1,RCP=1,GCP=1,ParentWhCode='P1')
        MdmSkuLocCurrent.objects.create(source=self.source,owner='Importer',ordinal=1,
            SKUCode='S1',WhCode='W1',Norm=10,MinNorm=2,RLT=1,RCP=1,GCP=1,
            ParentWhCode='P1',SKUIntroDate='2026-10-06',SKUDescription='SKU',
            WHDescription='WH',ParentDescription='Parent',PackSize=1,
            StockPercentForRationing=100,NormPercentReservation=0,DBMActive=True)
        self.requester={'id':3,'name':'Requester'}
        self.reviewer={'id':2,'name':'Reviewer','product_id':[1],'location_id':[10]}
        patcher=patch.object(skuloc_tasks,'permission_catalogue',return_value=self.catalogue)
        patcher.start();self.addCleanup(patcher.stop)

    def test_assigned_reviewer_must_have_both_pair_scopes_before_mutation(self):
        submitted=skuloc_tasks.submit(self.source,dict(id=3,taskId='',isOverwrite=False,
            data=[{'sc':'S1','wc':'W1','mn':'3'}],product_permissions=[1],
            location_permissions=[10],all_users=[self.reviewer]),self.requester,2)
        task_id=submitted['taskId']
        decision=dict(taskId=task_id,data=[{'sc':'S1','wc':'W1','status':'3','comments':'proof'}],
            product_permissions=[1],location_permissions=[11])
        with self.assertRaises(TaskDenied):
            skuloc_tasks.approve(self.source,decision,self.reviewer)
        self.assertIsNone(MdmSkuLocHistory.objects.get(TaskId=task_id).Status)
        self.assertFalse(MdmSkuLocModifyApproved.objects.exists())
        decision['location_permissions']=[10]
        skuloc_tasks.approve(self.source,decision,self.reviewer)
        self.assertEqual(MdmSkuLocHistory.objects.get(TaskId=task_id).Status,'3')
        self.assertTrue(MdmSkuLocModifyRequested.objects.get(TaskId=task_id).Approved)
        self.assertEqual(MdmSkuLocModifyApproved.objects.get().MinNorm,3)
        self.assertEqual(MdmSubTask.objects.get(TaskID=task_id).TaskStatus,'2')
        revision=skuloc_input.select_revision(self.source)
        columns=['SKUCode','WhCode','ParentWhCode','Norm','MinNorm','RLT','RCP','GCP','OCP',
            'PackSize','SpikeThreshold','PSOThreshold','FGRMFlag','StockPercentForRationing',
            'NormPercentReservation','MinOrderCount',*('SKULocAtt%02d'%i for i in range(1,16))]
        base={name:None for name in columns};base.update(SKUCode='S1',WhCode='W1',ParentWhCode='P1',
            Norm=10,MinNorm=2,RLT=1,RCP=1,GCP=1,PackSize=1,SpikeThreshold=5,PSOThreshold=6,
            StockPercentForRationing=100,NormPercentReservation=0)
        mapped=skuloc_input.consumer_input(revision,[base],columns,nms_active=True,last_run_date='2026-10-06')
        self.assertEqual(mapped[0]['MinNorm'],3)
        self.assertIsNone(mapped[0]['SpikeThreshold'])
        self.assertIsNone(mapped[0]['PSOThreshold'])

    def test_modify_review_text_and_native_download_old_projection(self):
        submitted=skuloc_tasks.submit(self.source,dict(id=3,taskId='',isOverwrite=False,
            data=[{'sc':'S1','wc':'W1','mn':'3','c1':''}],product_permissions=[1],
            location_permissions=[10],all_users=[self.reviewer]),self.requester,2)
        task_id=submitted['taskId']
        with patch.object(skuloc_reads,'permission_catalogue',return_value=self.catalogue):
            reviewed=skuloc_reads.details(self.source,dict(taskId=task_id,
                product_permissions=[1],location_permissions=[10]),self.reviewer)[0]['data'][0]
        self.assertEqual(json.loads(reviewed['new']),{'sc':'S1','wc':'W1','mn':'3','c1':''})
        self.assertEqual(json.loads(reviewed['old']),{'sc':'S1','wc':'W1','mn':'2','c1':''})
        MdmSkuLocHistory.objects.filter(TaskId=task_id).update(ApprovedBy=2,Status='3')
        downloaded=skuloc_reads.details(self.source,dict(taskId=task_id,approverId=2),
            self.requester,download=True)[0]['data'][0]
        self.assertEqual(json.loads(downloaded['old']),json.loads(downloaded['new']))
        self.assertEqual(json.loads(downloaded['new'])['mn'],3)

    def test_configured_add_approval_retry_keeps_one_deferred_input(self):
        MdmLocationAttributes.objects.create(source=self.source,owner='Importer',ordinal=2,
            WHCode='W-NEW',LL1='L',LL2='A',LL3='X')
        aliases=[alias for alias,row in skuloc.FIELDS.items() if row['IsAdd']]
        values={'sc':'S1','wc':'W-NEW','pwc':'P1','n':'10','npr':'5','mn':'2','rlt':'3',
            'rcp':'4','gcp':'5','ocp':'6','moc':'1','ps':'7','st':'1.25','pt':'2.25',
            'frf':'FG','da':'yes','c1':'one','c2':'two','c4':'four','c7':'seven','c11':'eleven'}
        self.assertEqual(set(aliases),set(values))
        result=skuloc_tasks.submit(self.source,dict(id=3,taskId='',isOverwrite=False,
            data=[{alias:values[alias] for alias in aliases}],product_permissions=[1],
            location_permissions=[10],all_users=[self.reviewer]),self.requester,1)
        decision=dict(taskId=result['taskId'],data=[{'sc':'S1','wc':'W-NEW','status':'3','comments':'proof'}],
            product_permissions=[1],location_permissions=[10])
        skuloc_tasks.approve(self.source,decision,self.reviewer)
        skuloc_tasks.approve(self.source,decision,self.reviewer)
        self.assertEqual(MdmSkuLocAddApproved.objects.filter(source=self.source,SKUCode='S1',WhCode='W-NEW').count(),1)
        staged=MdmSkuLocAddApproved.objects.get(source=self.source,SKUCode='S1',WhCode='W-NEW')
        self.assertEqual((staged.StockPercentForRat,staged.NormPercentReservation),(100,5))
        self.assertFalse(MdmSkuLocCurrent.objects.filter(source=self.source,SKUCode='S1',WhCode='W-NEW').exists())
        columns=['SKUCode','WhCode','ParentWhCode','Norm','MinNorm','RLT','RCP','GCP','OCP',
            'PackSize','SpikeThreshold','PSOThreshold','FGRMFlag','StockPercentForRationing',
            'NormPercentReservation','MinOrderCount',*('SKULocAtt%02d'%i for i in range(1,16))]
        base={name:None for name in columns};base.update(SKUCode='S1',WhCode='W1',Norm=10,
            MinNorm=2,RLT=1,RCP=1,GCP=1,PackSize=1,StockPercentForRationing=100,
            NormPercentReservation=0)
        mapped=skuloc_input.consumer_input(skuloc_input.select_revision(self.source),[base],columns,
            nms_active=True,last_run_date='2026-10-06')
        added=[row for row in mapped if row['SKUCode']=='S1' and row['WhCode']=='W-NEW']
        self.assertEqual(len(added),1)
        self.assertEqual((added[0]['Norm'],added[0]['NormPercentReservation']),(10,5))

    def test_remove_cross_pair_flaw_and_exact_remove_are_deferred(self):
        for ordinal,code in enumerate(('S2','S3'),2):
            MdmSkuAttributes.objects.create(source=self.source,owner='Importer',ordinal=ordinal,
                SKUCode=code,SL1='P',SL2='A',SL3='X')
        for ordinal,code in enumerate(('W2','W3'),2):
            MdmLocationAttributes.objects.create(source=self.source,owner='Importer',ordinal=ordinal,
                WHCode=code,LL1='L',LL2='A',LL3='X')
        for ordinal,(sku_code,wh_code) in enumerate((('S2','W3'),('S3','W2')),2):
            MdmSkuLocPair.objects.create(source=self.source,owner='Importer',ordinal=ordinal,
                SKUCode=sku_code,LocCode=wh_code,PackSize=1,StockPercentForRationing=100,
                NormPercentReservation=0,NonNMS=False)
        task_stamps=[datetime(2026,10,6,12,0,0),datetime(2026,10,6,12,0,1)]
        with patch.object(skuloc_tasks,'now',side_effect=task_stamps):
            cross=skuloc_tasks.submit(self.source,dict(id=3,taskId='',data=[{'sc':'S2','wc':'W2'}],
                product_permissions=[1],location_permissions=[10],all_users=[self.reviewer]),self.requester,3)
            exact=skuloc_tasks.submit(self.source,dict(id=3,taskId='',data=[{'sc':'S1','wc':'W1'}],
                product_permissions=[1],location_permissions=[10],all_users=[self.reviewer]),self.requester,3)
        self.assertEqual(cross['errorCount'],'0')
        self.assertTrue(MdmSkuLocRemoveRequested.objects.filter(TaskId=cross['taskId'],SKUCode='S2',WhCode='W2').exists())
        self.assertFalse(MdmSkuLocHistory.objects.filter(TaskId=cross['taskId']).exists())
        self.assertFalse(MdmSkuLocRemoveApproved.objects.filter(source=self.source,SKUCode='S2',WhCode='W2').exists())
        skuloc_tasks.approve(self.source,dict(taskId=exact['taskId'],
            data=[{'sc':'S1','wc':'W1','status':'3','comments':'proof'}],
            product_permissions=[1],location_permissions=[10]),self.reviewer)
        self.assertTrue(MdmSkuLocRemoveApproved.objects.filter(source=self.source,SKUCode='S1',WhCode='W1').exists())
        self.assertTrue(MdmSkuLocCurrent.objects.filter(source=self.source,SKUCode='S1',WhCode='W1').exists())
