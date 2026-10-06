"""Migration-enabled SKU proof using independently captured native full rows."""
import gzip
import json
import os
from collections import Counter
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from unittest.mock import patch

from django.db import DatabaseError, transaction
from django.test import TestCase
from django.conf import settings

from mta.mdm import drafts, sku
from mta.mdm.source import install_sku
from mta.runtime.mdm_models import MdmSource, MdmSkuAttributes, MdmSkuDescription, MdmDraft, MdmDraftSku
from mta.runtime.mdm_models import (MdmTask, MdmSubTask, MdmSkuRequested,
    MdmSkuHistory, MdmSkuApproved, MdmSkuUse, MdmSkuUploadLog)
from mta.mdm import tasks, task_reads, sku_input


class SkuMasterPostgresTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Path(os.environ['MDM_CAPTURE_DIR'])
        cls.installed = install_sku(cls.root)
        cls.native = json.loads(gzip.decompress((cls.root/'native-current-002.json.gz').read_bytes()))
        cls.permissions = json.loads((cls.root/'native-permissions.json').read_text())

    def test_full_scoped_rows_and_count(self):
        with patch('mta.mdm.sku.permission_catalogue', return_value=self.permissions):
            for name, expected in self.native.items():
                with self.subTest(actor=name):
                    payload = dict(id=1, name='SKU', fields=[{'key': k} for k in sku.ALIASES],
                        filters=[], product_permissions=expected['permissions'])
                    self.assertEqual(sku.read(self.installed, payload, count=True), str(expected['count']))
                    actual = sku.read(self.installed, payload)
                    encode = lambda row: json.dumps(row,sort_keys=True,separators=(',',':'))
                    diagnostic = dict(actor=name, exact_order=actual==expected['rows'],
                        complete_bags=Counter(map(encode,actual))==Counter(map(encode,expected['rows'])),
                        rows=len(actual), position_differences=sum(a!=b for a,b in zip(actual,expected['rows'])))
                    (self.root/('unpaged-'+name+'-comparison.json')).write_text(json.dumps(diagnostic,indent=2))
                    (self.root/('unpaged-'+name+'-modern.json.gz')).write_bytes(gzip.compress(json.dumps(actual,separators=(',',':')).encode(),mtime=0))
                    # Human-approved only for SKU unpaged current reads; strict
                    # failure evidence and all exact page assertions are retained.
                    self.assertEqual(Counter(map(encode,actual)),Counter(map(encode,expected['rows'])))

    def test_every_page_against_native_row_number_query(self):
        with patch('mta.mdm.sku.permission_catalogue', return_value=self.permissions):
            for name, expected in self.native.items():
                payload = dict(id=1, name='SKU', fields=[{'key': k} for k in sku.ALIASES],
                    filters=[], product_permissions=expected['permissions'])
                for page, rows in enumerate(expected['pages'],1):
                    with self.subTest(actor=name,page=page):
                        payload['paginationParameter'] = dict(pageNumber=page,recordsPerPage=100)
                        self.assertEqual(sku.read(self.installed,payload),rows)

    def test_duplicate_and_missing_description_join_grains(self):
        original = MdmSkuAttributes.objects.filter(source=self.installed,owner='Importer').exclude(SL1=None).first()
        attributes = {f.name: getattr(original, f.name) for f in MdmSkuAttributes._meta.fields if f.name not in ('id','source')}
        hierarchy = {'products': {'records': [dict(id=999, **{'level_'+str(i): getattr(original,'SL'+str(i)) for i in range(1,4)})]}}
        payload = dict(id=1, name='SKU', fields=[{'key':'sc'}, {'key':'sd'}],
            filters=[dict(attributeName='sc',op='=',value=original.SKUCode)], product_permissions=[999])
        with patch('mta.mdm.sku.permission_catalogue', return_value=hierarchy):
            before = sku.read(self.installed, payload)
            before_count = int(sku.read(self.installed, payload, count=True))
            self.assertEqual(len(before), 1)
            MdmSkuAttributes.objects.create(source=self.installed, **attributes)
            self.assertEqual(sku.read(self.installed, payload), before * 4)
            self.assertEqual(int(sku.read(self.installed, payload, count=True)), before_count + 1)
            MdmSkuDescription.objects.filter(source=self.installed, SKUCode=original.SKUCode).delete()
            self.assertEqual(sku.read(self.installed, payload), [{'sc':original.SKUCode}] * 4)
            self.assertEqual(sku.read(self.installed, payload, count=True), '0')

    def test_source_is_install_once_and_transactional(self):
        with self.assertRaises(ValueError):
            install_sku(self.root)
        self.assertEqual(MdmSource.objects.count(), 1)
        self.assertEqual(MdmSkuAttributes.objects.filter(owner='Importer').count(), 2189)

    def test_draft_text_rows_pages_ownership_append_modify_delete(self):
        actor, other = {'id':3}, {'id':2}
        payload = dict(actionType=2, instanceName='SKU', searchKey='SKU', draftId='',
            draftData=[dict(masterId=1, status='Validation', gridState='[]', dataMaster=[
                dict(sc='MDM-%03d'%i, sd="Owner's row", ec='invalid number', error=None, warning='Check') for i in range(103)])])
        created = drafts.write(self.installed, payload, actor)
        identifier = created['data']
        paging = {'pageNumber':2,'recordsPerPage':100}
        read = drafts.details(self.installed, identifier, actor, paging)
        self.assertEqual(read[0]['DataMaster'], [dict(sc='MDM-%03d'%i,sd='Owner"s row',ec='invalid number',warning='Check') for i in range(100,103)])
        with patch('mta.presentation.mdm_views.source', return_value=self.installed), \
                patch('mta.presentation.fixture.enabled', return_value=False):
            response = self.client.post('/api/mta/draft/' + identifier,
                json.dumps(paging), content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY='{"id":3}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'], read)
        self.assertEqual(json.loads(drafts.count(self.installed, identifier, actor)), [{'masterid':1,'recordCount':103}])
        for action in (lambda: drafts.count(self.installed,identifier,other),
                lambda: drafts.details(self.installed,identifier,other,paging),
                lambda: drafts.write(self.installed,{**payload,'draftId':identifier},other)):
            with self.assertRaises(drafts.DraftDenied): action()
        self.assertEqual(drafts.delete(self.installed,identifier,other)['status'],304)
        self.assertEqual(drafts.write(self.installed,{**payload,'draftId':identifier},other,modify=True)['status'],304)
        payload['draftId'] = identifier
        payload['draftData'][0]['dataMaster'] = [{'sc':'appended'}]
        drafts.write(self.installed,payload,actor)
        self.assertEqual(MdmDraftSku.objects.get(RowId=104).SKUCode,'appended')
        payload['actionType'] = 1
        drafts.write(self.installed,payload,actor,modify=True)
        self.assertEqual(MdmDraft.objects.get().ActionType,2)
        self.assertEqual(MdmDraftSku.objects.get().RowId,1)
        self.assertEqual(drafts.delete(self.installed,identifier,actor)['status'],200)
        self.assertFalse(MdmDraftSku.objects.exists())
        self.assertFalse(MdmDraft.objects.exists())

    def test_empty_append_retains_native_null_row_id_failure(self):
        payload = dict(actionType=1,instanceName='SKU',searchKey='SKU',draftData=[
            dict(masterId=1,status='Draft',gridState='[]',dataMaster=[])])
        created = drafts.write(self.installed,payload,{'id':3})
        payload['draftId'] = created['data']
        payload['draftData'][0]['dataMaster'] = [{'sc':'failure'}]
        with self.assertRaises(DatabaseError), transaction.atomic():
            drafts.write(self.installed,payload,{'id':3})
        self.assertTrue(MdmDraft.objects.exists())
        self.assertFalse(MdmDraftSku.objects.exists())


class SkuWorkflowPostgresTests(TestCase):
    """Owned rows, independently retained request fixtures, no serving writes."""
    def setUp(self):
        self.root = Path(os.environ['MDM_CAPTURE_DIR'])/'native-workflow'
        self.fixture = json.loads((self.root/'request-fixture.json').read_text())
        self.source = MdmSource.objects.create(digest='a'*64,database_name='owned-test',
            dll_digest='0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346',receipt={})
        self.actor=self.fixture['actors']['requester']
        self.reviewer=self.fixture['actors']['reviewer']
        permission=self.fixture['permission']
        catalogue={'products':{'records':[dict(id=permission['id'],**{
            'level_'+str(i):permission['product_hierarchy_'+str(i)] for i in range(1,4)})]}}
        for module in (tasks,task_reads):
            patcher=patch.object(module,'permission_catalogue',return_value=catalogue)
            patcher.start(); self.addCleanup(patcher.stop)
        for owner in ('Importer','BPR','BTR','DBM'):
            for ordinal,raw in enumerate(self.fixture['initial_rows'],1):
                row={k:v for k,v in raw.items() if k not in ('locations','SKUDescription')}
                MdmSkuAttributes.objects.create(source=self.source,owner=owner,ordinal=ordinal,**row)
                MdmSkuDescription.objects.create(source=self.source,owner=owner,ordinal=ordinal,
                    SKUCode=raw['SKUCode'],SKUDescription=raw['SKUDescription'])
        MdmSkuUse.objects.create(source=self.source,ordinal=1,SKUCode='MDM-LINKED')

    def submit(self,name,action,second=0,actor=None,task_id=''):
        rows=[{alias: str(row[field]) if row[field] is not None else ''
            for field in self.fixture['taskColumnList'].split(',')
            for alias,target in sku.ALIASES.items() if target==field}
            for row in self.fixture['submissions'][name]]
        payload=dict(id=1,taskId=task_id,isOverwrite=False,data=rows,
            product_permissions=[4],all_users=[self.reviewer])
        stamp=datetime(2026,10,6,18,0,second,tzinfo=ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE))
        with patch.object(tasks,'now',return_value=stamp):
            return tasks.submit(self.source,payload,actor or self.actor,action)

    def decide(self,task_id,code,status='3',actor=None,permissions=None):
        return tasks.approve(self.source,dict(taskId=task_id,
            data=[dict(sc=code,status=status,comments='proof')],
            product_permissions=[4] if permissions is None else permissions),actor or self.reviewer)

    def test_modify_and_delete_leave_current_master_and_pin_future_input(self):
        modify=self.submit('modify',2)['taskId']
        remove=self.submit('delete',3,second=1)['taskId']
        initial=sku_input.select_revision(self.source)
        self.decide(modify,'MDM-BASE')
        self.decide(remove,'MDM-DELETE')
        self.assertEqual(MdmTask.objects.get(TaskID=modify).Actiontype,2)
        self.assertEqual(MdmSkuRequested.objects.get(TaskId=modify).ActionType,1)
        self.assertEqual(MdmSkuRequested.objects.get(TaskId=remove).ActionType,0)
        self.assertEqual(list(MdmSubTask.objects.order_by('id').values_list('TaskStatus',flat=True)),['2','2'])
        self.assertEqual(list(MdmTask.objects.order_by('id').values_list('TaskStatus',flat=True)),['1','1'])
        self.assertEqual(MdmSkuDescription.objects.get(owner='Importer',SKUCode='MDM-BASE').SKUDescription,'Base SKU')
        revision=sku_input.select_revision(self.source)
        self.assertNotEqual(initial.digest,revision.digest)
        with self.assertRaises(ValueError): sku_input.select_revision(self.source,initial.digest)
        self.assertEqual(sku_input.select_revision(self.source,revision.digest).digest,revision.digest)
        columns=['SKUCode','SKUDescription','LocationCode','Quantity',
            *[n for n in sku.ALIASES.values() if n not in ('SKUCode','SKUDescription') and not n.startswith('c')],
            *['SKUAtt%02d'%i for i in range(1,16)]]
        raw=[dict.fromkeys(columns)|dict(SKUCode=code,LocationCode=loc,Quantity=7)
            for code,loc in [('MDM-BASE','LOC-1'),('MDM-BASE','LOC-2'),('MDM-DELETE','LOC-1')]]
        self.assertEqual(sku_input.consumer_input(revision,raw,columns,nms_active=False),raw)
        result=sku_input.consumer_input(revision,raw,columns,nms_active=True)
        self.assertEqual([r['SKUCode'] for r in result],['MDM-BASE','MDM-BASE','MDM-LINKED'])
        for row in result[:2]:
            self.assertEqual((row['SKUDescription'],row['Weight'],row['SKUAtt01'],row['Quantity']),
                ('Base Modified',Decimal('3.333'),'modified',7))
        self.assertEqual([r['LocationCode'] for r in result],['LOC-1','LOC-2',None])
        self.assertEqual(MdmSkuApproved.objects.count(),2)
        with self.assertRaises(TypeError): revision.approved[0]['SKUCode']='mutated'

    def test_actor_guards_prevent_partial_writes(self):
        task_id=self.submit('modify',2)['taskId']
        with self.assertRaises(task_reads.TaskDenied): self.decide(task_id,'MDM-BASE',actor=self.actor)
        with self.assertRaises(task_reads.TaskDenied): self.decide(task_id,'MDM-BASE',permissions=[])
        with self.assertRaises(task_reads.TaskDenied): tasks.approve(self.source,
            dict(taskId=task_id,data=[dict(status='3',comments='invalid')],product_permissions=[4]),self.actor)
        with self.assertRaises(task_reads.TaskDenied): self.submit('provided',1,actor=self.reviewer,task_id=task_id)
        with self.assertRaises(task_reads.TaskDenied): tasks.delete(self.source,task_id,self.reviewer)
        with self.assertRaises(task_reads.TaskDenied): task_reads.details(self.source,
            dict(taskId=task_id,approverId='2'),dict(id='999'),download=True)
        with self.assertRaises(task_reads.TaskDenied): task_reads.history(self.source,
            dict(masterId=1,skuCode='MDM-BASE',product_permissions=[]),self.actor)
        self.assertIsNone(MdmSkuHistory.objects.get().Status)
        self.assertFalse(MdmSkuRequested.objects.get().Approved)
        self.assertEqual(MdmSkuApproved.objects.count(),0)
        self.assertEqual(MdmTask.objects.count(),1)

    def test_partial_add_publishes_only_approved_rows_and_retains_request_history(self):
        task_id=self.submit('add',1)['taskId']
        self.decide(task_id,'MDM-ADD-A')
        self.assertEqual(MdmTask.objects.get().TaskStatus,'7')
        self.assertEqual(MdmSubTask.objects.get().TaskStatus,'5')
        self.assertEqual(MdmSkuRequested.objects.count(),2)
        self.assertEqual(MdmSkuHistory.objects.count(),2)
        self.assertEqual(MdmSkuApproved.objects.count(),0)
        for owner in ('Importer','BPR','BTR','DBM'):
            added=MdmSkuAttributes.objects.get(owner=owner,SKUCode='MDM-ADD-A')
            self.assertEqual((added.Weight,added.c1,added.SL1),(Decimal('1.111'),'A','FG'))
            self.assertEqual(MdmSkuDescription.objects.get(owner=owner,SKUCode='MDM-ADD-A').SKUDescription,'Added A')
            self.assertFalse(MdmSkuAttributes.objects.filter(owner=owner,SKUCode='MDM-ADD-B').exists())
        self.assertEqual(task_reads.pending_rows(self.source,self.reviewer),[])
        self.assertEqual(task_reads.count(self.source,task_id,self.reviewer),2)
        # Completed parent/subtask does not forbid the assigned reviewer's later
        # decision on its still-pending second history occurrence.
        self.decide(task_id,'MDM-ADD-B','4')
        self.assertEqual(list(MdmSkuHistory.objects.order_by('SKUCode').values_list('Status',flat=True)),['3','4'])
        self.assertFalse(MdmSkuDescription.objects.filter(SKUCode='MDM-ADD-B').exists())
        downloaded=task_reads.details(self.source,dict(taskId=task_id,approverId='2'),self.actor,download=True)
        self.assertEqual([r['Status'] for r in downloaded[0]['data']],
            ['Request approved','Request approval reverted/ Rejected'])
        tasks.delete(self.source,task_id,self.actor)
        self.assertFalse(MdmSkuRequested.objects.exists())
        self.assertTrue(MdmSkuAttributes.objects.filter(SKUCode='MDM-ADD-A').exists())

    def test_supplied_delete_id_and_conflict_duplicate_grain(self):
        task_id=self.submit('modify',2)['taskId']
        # Both pending histories identify one conflicting code, while DISTINCT
        # old task projections and first incoming row determine the details.
        prior=MdmSkuHistory.objects.get()
        prior.pk=None; prior.save()
        self.fixture['submissions']['modify']*=2
        response=self.submit('modify',2,second=1)
        self.assertEqual(response['conflictErrorCount'],'2')
        self.assertEqual(len(response['conflictError']),1)
        self.assertEqual(len(response['conflictError'][0]['conflictdetails']),1)
        self.assertEqual(MdmSkuRequested.objects.count(),1)
        response=self.submit('delete',3,second=2,task_id=task_id)
        self.assertEqual(response['taskId'],task_id)
        self.assertEqual(MdmTask.objects.count(),1)
        self.assertEqual(MdmSubTask.objects.count(),1)
        self.assertEqual(MdmSkuRequested.objects.get(SKUCode='MDM-DELETE').TaskId,task_id)

    def test_status_uses_native_formatted_date_order(self):
        first=self.submit('modify',2)['taskId']
        second=self.submit('delete',3,second=1)['taskId']
        zone=ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)
        MdmTask.objects.filter(TaskID=first).update(PendingSince=datetime(2026,9,30,8,tzinfo=zone))
        MdmTask.objects.filter(TaskID=second).update(PendingSince=datetime(2026,10,1,8,tzinfo=zone))
        self.assertEqual([r['TaskID'] for r in task_reads.status_rows(self.source,self.actor)],[second,first])
        self.assertEqual([r['TaskID'] for r in task_reads.pending_rows(self.source,self.reviewer)],[first,second])

    def test_history_selector_preserves_midnight_window_and_current_scope(self):
        task_id=self.submit('modify',2)['taskId']
        zone=ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)
        stamp=datetime(2026,10,6,18,tzinfo=zone)
        payload=dict(masterId=1,product_permissions=[4],location_permissions=[])
        with patch.object(task_reads,'database_now',return_value=stamp):
            self.assertEqual(task_reads.history_skus(self.source,payload),[])
            MdmTask.objects.filter(TaskID=task_id).update(PendingSince=stamp.replace(hour=0))
            duplicate=MdmSkuHistory.objects.get(); duplicate.pk=None; duplicate.save()
            self.assertEqual(task_reads.history_skus(self.source,payload),[{'SKUCode':'MDM-BASE'}])
            self.assertEqual(task_reads.history_skus(self.source,{**payload,'product_permissions':[]}),[])
            MdmTask.objects.filter(TaskID=task_id).update(PendingSince=datetime(2026,7,7,tzinfo=zone))
            self.assertEqual(task_reads.history_skus(self.source,payload),[])

    def test_database_clock_matches_native_datetime_rounding_and_rollover(self):
        from mta.mdm.clock import database_now
        zone=ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)
        # Independently checked with CAST(datetime2(6) AS datetime), style121.
        for micros,suffix in ((0,'59.000000'),(1000,'59.000000'),(2000,'59.003000'),
            (5000,'59.007000'),(8000,'59.007000'),(998000,'59.997000'),(999000,'00.000000')):
            raw=datetime(2026,10,6,23,59,59,micros,tzinfo=zone)
            with patch('mta.mdm.clock.connection.cursor') as cursor:
                cursor.return_value.__enter__.return_value.fetchone.return_value=(raw,)
                actual=database_now()
            self.assertEqual(actual.strftime('%S.%f'),suffix)
            self.assertEqual(actual.day,7 if micros==999000 else 6)

    def test_native_sql_conversion_failure_keeps_success_envelope_without_rows(self):
        with self.assertLogs('mta.mdm.tasks',level='ERROR'):
            response=self.submit('invalid_numeric',1)
        self.assertEqual(response['status'],200)
        self.assertEqual(response['errorCount'],'0')
        for model in (MdmTask,MdmSubTask,MdmSkuRequested,MdmSkuHistory):
            self.assertEqual(model.objects.count(),0)

    def test_exact_native_partial_add_full_relational_state(self):
        root=self.root.parent/'native-workflow-review-002'
        partial=json.loads((root/'after-partial.json').read_text())
        final=json.loads((root/'after-final.json').read_text())
        zone=ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)
        # Native approval proof declares its seed separately from submission.
        # Reproduce that identical seed, never use native outputs as production state.
        for model in (MdmSkuAttributes,MdmSkuDescription):
            model.objects.filter(source=self.source).delete()
        for raw in final['#Requested']:
            if raw['TaskId']=='ADD':
                MdmSkuRequested.objects.create(source=self.source,**{**raw,'Approved':False,'Reverted':False})
        for raw in final['#History']:
            if raw['TaskId']=='ADD':
                MdmSkuHistory.objects.create(source=self.source,**{**raw,'Status':None,'Comments':None,'ApprovedBy':None})
        task=next(r for r in partial['#TaskStatus'] if r['TaskID']=='ADD')
        MdmTask.objects.create(source=self.source,**{**task,'TaskStatus':'1',
            'PendingSince':datetime.fromisoformat(task['PendingSince']).replace(tzinfo=zone)})
        sub=next(r for r in partial['#SubTask'] if r['TaskID']=='ADD')
        MdmSubTask.objects.create(source=self.source,**{**sub,'TaskStatus':'1',
            'ApprovedOrRejectedDate':None,'DBUpdatedDate':None})
        def encoded(row):
            result={}
            for field in row._meta.fields:
                if field.name in ('id','source','owner','ordinal'): continue
                val=getattr(row,field.name)
                if isinstance(val,Decimal): val=format(val,'f')
                if isinstance(val,datetime): val=val.astimezone(zone).replace(tzinfo=None).isoformat()
                result[field.name]=val
            return result
        def compare(expected,label):
            actual={}
            for table,model,key in (('#Requested',MdmSkuRequested,'TaskId'),
                ('#History',MdmSkuHistory,'TaskId'),('#TaskStatus',MdmTask,'TaskID'),
                ('#SubTask',MdmSubTask,'TaskID')):
                actual[table]=[encoded(r) for r in model.objects.filter(source=self.source,**{key:'ADD'}).order_by('SKUCode' if table in ('#Requested','#History') else key)]
                self.assertEqual(actual[table],[r for r in expected[table] if r[key]=='ADD'],table)
            actual['#Queue']=[encoded(r) for r in MdmSkuApproved.objects.filter(source=self.source)]
            self.assertEqual(actual['#Queue'],[r for r in expected['#Queue'] if r['SKUCode'].startswith('MDM-ADD')])
            for owner in ('Importer','BPR','BTR','DBM'):
                for suffix,model in (('Attr',MdmSkuAttributes),('Desc',MdmSkuDescription)):
                    table='#'+owner+suffix
                    actual[table]=[encoded(r) for r in model.objects.filter(source=self.source,owner=owner).order_by('SKUCode')]
                    self.assertEqual(actual[table],expected[table],table)
            actual['#Audit']=[encoded(r) for r in MdmSkuUploadLog.objects.filter(source=self.source).order_by('SKUCode')]
            self.assertEqual(actual['#Audit'],[r for r in expected['#Audit'] if r['SKUCode'].startswith('MDM-ADD')])
            (root/('modern-'+label+'.json')).write_text(json.dumps(actual,indent=2))
        for code,status,comment,expected,label in (
            ('MDM-ADD-A','3','approve first',partial,'partial'),
            ('MDM-ADD-B','4','reject second',final,'final')):
            audit=next(r for r in expected['#Audit'] if r['SKUCode']==code)
            stamp=datetime.fromisoformat(audit['ActionTimeStamp']).replace(tzinfo=zone)
            with patch.object(tasks,'database_now',return_value=stamp):
                tasks.approve(self.source,dict(taskId='ADD',product_permissions=[4],
                    data=[dict(sc=code,status=status,comments=comment)]),self.reviewer)
            compare(expected,label)
