"""Focused PostgreSQL behavior for the pinned Location family."""
import gzip
import json
import os
from pathlib import Path
from collections import Counter
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import TestCase

from mta.mdm import location, location_input, location_reads, location_tasks
from mta.mdm.location_source import install_location
from mta.runtime.mdm_models import (MdmSource, MdmTask, MdmSubTask,
    MdmLocationAttributes, MdmLocationDescription, MdmLocationRequested,
    MdmLocationHistory, MdmLocationApproved, MdmLocationUse)


class LocationWorkflowTests(TestCase):
    def setUp(self):
        self.source=MdmSource.objects.create(digest='a'*64,dll_digest=
            '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346',
            database_name='owned-test',receipt={})
        self.requester={'id':3,'name':'Requester'}
        self.reviewer={'id':2,'name':'Reviewer','location_id':[1]}
        self.catalogue={'locations':{'records':[dict(id=1,level_1='Type',
            level_2='Business',level_3='Zone')]}}
        for module in (location,location_tasks,location_reads):
            mocked=patch.object(module,'permission_catalogue',return_value=self.catalogue)
            mocked.start(); self.addCleanup(mocked.stop)
        for ordinal,code in enumerate(('LOC-BASE','LOC-DIRECT','LOC-PARENT','LOC-DELETE'),1):
            MdmLocationAttributes.objects.create(source=self.source,owner='Importer',
                ordinal=ordinal,WHCode=code,LocationType='Warehouse',
                LogisticsLocation='Yes',LL1='Type',LL2='Business',LL3='Zone',c1='old')
            MdmLocationDescription.objects.create(source=self.source,owner='Importer',
                ordinal=ordinal,WHCode=code,WHDescription=code+' description')
        MdmLocationUse.objects.create(source=self.source,use_kind='direct',ordinal=1,
                                      WHCode='LOC-DIRECT')
        MdmLocationUse.objects.create(source=self.source,use_kind='parent',ordinal=1,
                                      WHCode='LOC-PARENT')

    def row(self,code,description=None):
        return dict(wc=code,wd=description or code+' new',l='Yes',lc='Warehouse',
            c1='new',LL1='Type',LL2='Business',LL3='Zone')

    def submit(self,action,rows,task_id='',overwrite=False):
        payload=dict(id=2,taskId=task_id,isOverwrite=overwrite,data=rows,
            location_permissions=[1],all_users=[self.reviewer])
        stamp=datetime(2026,10,6,18,0,0,tzinfo=ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE))
        with patch.object(location_tasks,'now',return_value=stamp):
            return location_tasks.submit(self.source,payload,self.requester,action)

    def test_current_scope_configuration_and_delete_guard_categories(self):
        config=location.configuration('remove')[0]
        self.assertEqual((config['id'],config['name'],len(config['fields'])),('2','Location',24))
        payload=dict(id=2,location_permissions=[1],fields=[{'key':'wc'},{'key':'wd'}],
                     paginationParameter={'pageNumber':1,'recordsPerPage':100})
        self.assertEqual(len(location.read(self.source,payload)),4)
        response=self.submit(3,[dict(wc=code,LL1='Type',LL2='Business',LL3='Zone')
            for code in ('LOC-DIRECT','LOC-PARENT','LOC-DELETE','MISSING')])
        self.assertEqual([row['errorType'] for row in response['error']],
            ['Either You are UnAuthorized Location Code or Location Code Does not Exist',
             "You can't remove these Location Codes as they are already existing in SKULocation Combination",
             "You can't remove these Location Codes as they are already existing in SKULocation Combination as Parent Location Code"])
        self.assertEqual(MdmLocationRequested.objects.get().WHCode,'LOC-DELETE')

    def test_modify_approval_stages_delayed_input_without_current_publication(self):
        task_id=self.submit(2,[self.row('LOC-BASE')])['taskId']
        location_tasks.approve(self.source,dict(taskId=task_id,
            location_permissions=[1],data=[dict(wc='LOC-BASE',status='3',comments='approved')]),self.reviewer)
        self.assertEqual(MdmLocationApproved.objects.get().WHDescription,'LOC-BASE new')
        self.assertEqual(MdmLocationDescription.objects.get(owner='Importer',
            WHCode='LOC-BASE').WHDescription,'LOC-BASE description')
        self.assertEqual(MdmSubTask.objects.get().TaskStatus,'2')
        self.assertEqual(MdmTask.objects.get().TaskStatus,'1')
        revision=location_input.select_revision(self.source)
        columns=['SKUCode','WhCode','WHDescription','LocationType','LogisticsLocation',
            *('LL'+str(i) for i in range(1,6)),*('LocAtt%02d'%i for i in range(1,16))]
        raw=[dict.fromkeys(columns)|dict(SKUCode='SKU',WhCode='LOC-BASE',WHDescription='old')]
        result=location_input.consumer_input(revision,raw,columns,nms_active=True)
        self.assertEqual((result[0]['WHDescription'],result[0]['LocAtt01']),('LOC-BASE new','new'))

    def test_current_duplicate_attribute_occurrence_multiplies_cte_and_outer_join(self):
        MdmLocationDescription.objects.create(source=self.source,owner='Importer',ordinal=9,
            WHCode='DUP',WHDescription='duplicate')
        for ordinal,value in ((9,'one'),(10,'two')):
            MdmLocationAttributes.objects.create(source=self.source,owner='Importer',ordinal=ordinal,
                WHCode='DUP',LL1='Type',LL2='Business',LL3='Zone',c1=value)
        payload=dict(id=2,location_permissions=[1],fields=[{'key':'wc'},{'key':'c1'}])
        self.assertEqual(location.read(self.source,payload,count=True),'8')
        self.assertEqual(len(location.read(self.source,payload)),8)

    def test_decision_scope_denial_precedes_mutation(self):
        task_id=self.submit(2,[self.row('LOC-BASE')])['taskId']
        with self.assertRaises(location_reads.TaskDenied):
            location_tasks.approve(self.source,dict(taskId=task_id,
                location_permissions=[],data=[dict(wc='LOC-BASE',status='3',comments='denied')]),
                self.reviewer)
        self.assertFalse(MdmLocationRequested.objects.get().Approved)
        self.assertIsNone(MdmLocationHistory.objects.get().Status)
        self.assertFalse(MdmLocationApproved.objects.exists())

    def test_append_and_delete_are_requester_owned(self):
        task_id=self.submit(1,[self.row('LOC-ADD')])['taskId']
        self.submit(1,[self.row('LOC-ADD-2')],task_id=task_id)
        self.assertEqual(MdmLocationRequested.objects.count(),2)
        with self.assertRaises(location_reads.TaskDenied):
            location_tasks.delete(self.source,task_id,self.reviewer)
        location_tasks.delete(self.source,task_id,self.requester)
        self.assertFalse(MdmLocationRequested.objects.exists())
        self.assertFalse(MdmLocationHistory.objects.exists())

    def test_modify_review_keeps_native_json_text_and_correlated_duplicates(self):
        task_id=self.submit(2,[self.row('LOC-BASE')])['taskId']
        history=MdmLocationHistory.objects.get(TaskId=task_id)
        history.pk=None
        history.Status='4'
        history.ApproverId='999'
        history.save()
        result=location_reads.details(self.source,dict(taskId=task_id,
            location_permissions=[1]),self.reviewer)[0]['data']
        self.assertEqual(len(result),1)
        self.assertEqual(json.loads(result[0]['new'])['wc'],'LOC-BASE')
        # Correlated old JSON keeps both source occurrences, including one
        # excluded by the outer pending/reviewer predicate.
        old=json.loads('['+result[0]['old']+']')
        self.assertEqual(len(old),2)
        self.assertEqual(old[0],old[1])
        self.assertEqual(old[0]['c1'],'old')
        self.assertEqual(json.loads(result[0]['new'])['c1'],'new')
        MdmLocationHistory.objects.filter(TaskId=task_id).update(ApprovedBy=2)
        downloaded=location_reads.details(self.source,dict(taskId=task_id,approverId=2),
            self.requester,download=True)[0]['data'][0]
        self.assertEqual(json.loads('['+downloaded['old']+']')[0],json.loads(downloaded['new']))


class LocationCapturedCurrentTests(TestCase):
    """Complete qualified native rows and pages, without a legacy connection."""
    @classmethod
    def setUpTestData(cls):
        cls.root=Path(os.environ['MDM_LOCATION_CAPTURE_DIR'])
        cls.source=MdmSource.objects.create(digest='b'*64,dll_digest=
            '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346',
            database_name='owned-captured-test',receipt={})
        install_location(cls.root,cls.source)
        permissions=json.loads(gzip.decompress((cls.root/'LOCATION_PERMISSION.json.gz').read_bytes()))
        cls.catalogue={'locations':{'records':[dict(id=row['id'],
            level_1=row['location_heirarchy_1'],level_2=row['location_heirarchy_2'],
            level_3=row['location_heirarchy_3']) for row in permissions]}}
        cls.native=json.loads(gzip.decompress((cls.root/'native-current-location-exact-v2.json.gz').read_bytes()))

    def test_complete_native_current_counts_order_and_pages(self):
        fields=[{'key':alias} for alias in location.ALIASES]
        comparisons=[]
        attempt=os.environ.get('MDM_PROOF_ATTEMPT','manual')
        with patch.object(location,'permission_catalogue',return_value=self.catalogue):
            for name,case in self.native.items():
                payload=dict(id=2,location_permissions=case['permission_ids'],fields=fields)
                actual=location.read(self.source,payload) or []
                expected=case['unpaged']
                count=location.read(self.source,payload,count=True)
                paged=location.read(self.source,{**payload,
                    'paginationParameter':{'pageNumber':1,'recordsPerPage':100}}) or []
                page_expected=case['page1_100']
                encode=lambda row:json.dumps(row,sort_keys=True,separators=(',',':'))
                item=dict(profile=name,rows=len(actual),expected_rows=len(expected),
                    complete_bags=Counter(map(encode,actual))==Counter(map(encode,expected)),
                    unpaged_exact=actual==expected,page_exact=paged==page_expected,
                    count_exact=count==str(case['count']),
                    positions_differ=sum(a!=b for a,b in zip(actual,expected)))
                comparisons.append(item)
                (self.root/('modern-current-'+attempt+'-'+name+'.json.gz')).write_bytes(
                    gzip.compress(json.dumps({'rows':actual,'page1_100':paged},separators=(',',':')).encode(),mtime=0))
        (self.root/('current-comparison-'+attempt+'.json')).write_text(json.dumps(comparisons,indent=2))
        # Human approval call_9QfAPeRqplgZiMfwKfKiZrJE: only unpaged current
        # order is qualified; every field, occurrence and page remains strict.
        self.assertTrue(all(all(item[key] for key in ('complete_bags','page_exact','count_exact'))
                            for item in comparisons),json.dumps(comparisons))
