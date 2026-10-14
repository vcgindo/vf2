"""Small rollback-only PostgreSQL cases; no retained business dataset or replay."""
from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from unittest.mock import patch

from django.db import connection, DatabaseError, transaction
from django.test import TestCase

from mta.mdm import location_tasks as tasks
from mta.mdm.location_publication import publication_statement
from mta.runtime.initialization_models import ProductionInitialization
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.mdm_models import (MdmSource, MdmTask, MdmSubTask,
    MdmLocationAttributes, MdmLocationDescription, MdmLocationRequested, MdmLocationHistory,
    MdmLocationApproved, MdmLocationUploadLog, MdmSkuDescription)
from mta.runtime.models import CalculationRun


def setting(name, value):
    with connection.cursor() as cursor:
        cursor.execute('SELECT set_config(%s,%s,true)', [name, str(value)])


class NativeLocationAddTests(TestCase):
    def setUp(self):
        self.source = MdmSource.objects.create(digest='e'*64,
            database_name='rollback-component-only', dll_digest='d'*64,
            receipt={'schema':'fresh-production-mdm-source-v1'})
        identity = uuid.uuid4()
        setting('fresh.production_initialization', identity)
        self.initialization = ProductionInitialization.objects.create(id=identity,
            source=self.source, opening_identity=str(identity), opening_date=date(2026,7,1),
            input_sha256='e'*64, recipe_sha256='e'*64, configuration_digest='e'*64,
            implementation_digest='e'*64, input_digest='e'*64)
        setting('fresh.mdm_current_bootstrap', self.source.pk)
        for owner in ('Importer','BPR','BTR','DBM'):
            ordinal = 4 if owner=='BTR' else 199
            MdmLocationAttributes.objects.create(source=self.source, owner=owner,
                ordinal=ordinal, WHCode='Existing')
            MdmLocationDescription.objects.create(source=self.source, owner=owner,
                ordinal=ordinal, WHCode='Existing', WHDescription='Existing description')
        self.initialization.input_manifest_digest = 'e'*64
        self.initialization.receipt_digest = 'e'*64
        self.initialization.save(update_fields=['input_manifest_digest','receipt_digest'])
        setting('fresh.production_initialization','')
        setting('fresh.mdm_current_bootstrap','')
        self.catalogue = {'locations':{'records':[
            dict(id=1,level_1='P',level_2='A',level_3='X')]}}
        for module in ('mta.mdm.location_tasks','mta.mdm.task_reads'):
            patcher=patch(module+'.permission_catalogue',return_value=self.catalogue)
            patcher.start(); self.addCleanup(patcher.stop)
        self.requester={'id':2,'name':'Requester'}
        self.reviewer={'id':3,'name':'Reviewer','location_id':[1]}
        self.stamp=datetime(2026,7,3,8,1,15,tzinfo=timezone.utc)

    def submit(self):
        data={'wc':'LP002','wd':'Retained location','LL1':'P','LL2':'A','LL3':'X'}
        with patch.object(tasks,'now',return_value=self.stamp):
            result=tasks.submit(self.source,dict(id=2,taskId='',data=[data],
                location_permissions=[1],all_users=[self.reviewer]),self.requester,1)
        self.assertEqual(result['errorCount'],'0')
        return MdmTask.objects.get(source=self.source,TaskID=result['taskId'])

    def approve(self, task):
        return tasks.approve(self.source,dict(taskId=task.TaskID,
            data=[dict(wc='LP002',status='3',comments='component')],
            location_permissions=[1]),self.reviewer)

    def backed_queue(self):
        task=self.submit()
        MdmLocationRequested.objects.filter(source=self.source).update(Approved=True)
        MdmLocationHistory.objects.filter(source=self.source).update(Status='3',ApprovedBy=3)
        tasks.update_approved_queue(self.source,task.TaskID)
        return task

    def row(self, **changes):
        values=dict(source=self.source,owner='Importer',ordinal=200,WHCode='LP002',
            LL1='P',LL2='A',LL3='X')
        values.update(changes)
        return MdmLocationAttributes(**values)

    def denied(self, operation):
        with self.assertRaises(DatabaseError), transaction.atomic():
            operation()

    def test_real_submit_approve_exact_eight_rows_and_completion(self):
        task=self.submit()
        self.approve(task)
        for owner in ('Importer','BPR','BTR','DBM'):
            ordinal=5 if owner=='BTR' else 200
            row=MdmLocationAttributes.objects.get(source=self.source,owner=owner,WHCode='LP002')
            actual={f.name:getattr(row,f.name) for f in row._meta.fields if f.name not in ('id','source')}
            expected={name:None for name in ('LogisticsLocation','LocationType','LL4','LL5',*('c'+str(i) for i in range(1,16)))}
            expected.update(owner=owner,ordinal=ordinal,WHCode='LP002',
                LL1='P',LL2='A',LL3='X')
            self.assertEqual(actual,expected)
            desc=MdmLocationDescription.objects.get(source=self.source,owner=owner,WHCode='LP002')
            self.assertEqual((desc.ordinal,desc.WHDescription),(ordinal,'Retained location'))
        task.refresh_from_db(); self.assertEqual(task.TaskStatus,'7')
        sub=MdmSubTask.objects.get(source=self.source)
        self.assertEqual(sub.TaskStatus,'4'); self.assertTrue(sub.DBUpdatedDate)
        self.assertEqual(list(MdmLocationUploadLog.objects.filter(source=self.source)
            .order_by('pk').values_list('ActionId',flat=True)),[5,3])
        self.assertFalse(MdmLocationApproved.objects.filter(source=self.source).exists())
        with connection.cursor() as c:
            c.execute("SELECT current_setting('fresh.location_add_task',true), current_setting('fresh.location_add_source',true)")
            self.assertEqual(c.fetchone(),('',''))

    def test_marker_free_and_incorrect_values_owner_ordinal_denied(self):
        task=self.backed_queue()
        self.denied(lambda:self.row().save())
        for changes in ({'WHCode':'UNBACKED'},{'owner':'Other'},{'ordinal':201},
                        {'LogisticsLocation':'wrong'},{'c4':'unexpected'},{'LL1':'wrong'}):
            with self.subTest(changes=changes):
                with publication_statement(self.source,task):
                    self.denied(lambda:self.row(**changes).save())

    def test_wrong_invocation_and_missing_approval_backing_denied(self):
        task=self.backed_queue()
        for field,value in (('MasterId','1'),('Actiontype',2),('source_id',None)):
            with self.subTest(field=field), transaction.atomic():
                if field=='source_id':
                    other=MdmSource.objects.create(digest='f'*64,database_name='other',dll_digest='d'*64,receipt={})
                    value=other.pk
                MdmTask.objects.filter(pk=task.pk).update(**{field:value})
                with publication_statement(self.source,task):
                    self.denied(lambda:self.row().save())
                transaction.set_rollback(True)
        for model,field,value in ((MdmLocationRequested,'Approved',False),
                                  (MdmLocationHistory,'Status','4')):
            with self.subTest(model=model.__name__), transaction.atomic():
                model.objects.filter(source=self.source).update(**{field:value})
                with publication_statement(self.source,task):
                    self.denied(lambda:self.row().save())
                transaction.set_rollback(True)
        MdmLocationApproved.objects.filter(source=self.source).delete()
        with publication_statement(self.source,task):
            self.denied(lambda:self.row().save())

    def test_add_marker_never_authorizes_update_delete_truncate_or_sku(self):
        task=self.backed_queue()
        with publication_statement(self.source,task):
            self.denied(lambda:MdmLocationAttributes.objects.filter(source=self.source).update(c4='bad'))
            self.denied(lambda:MdmLocationAttributes.objects.filter(source=self.source).delete())
            def truncate():
                with connection.cursor() as c:
                    c.execute('TRUNCATE mta.fresh_mta_mdmlocationattributes')
            self.denied(truncate)
            self.denied(lambda:MdmSkuDescription.objects.create(source=self.source,
                owner='Importer',ordinal=1,SKUCode='5328',SKUDescription='Unauthorized'))

    def test_duplicate_queue_occurrences_and_other_task_global_queue(self):
        task=self.backed_queue()
        first=MdmLocationApproved.objects.get(source=self.source)
        first.pk=None; first.WHDescription='Second occurrence'; first.LL1='Different'; first.save()
        # Canonical global queue includes other approved tasks irrespective of
        # ActionType; the invocation task still supplies the selected columns.
        values=dict(WHCode='OTHER',WHDescription='Other approved task',LL1='P',LL2='A',LL3='X')
        MdmLocationRequested.objects.create(source=self.source,TaskId='other',ActionType=0,Approved=True,Reverted=False,**values)
        MdmLocationHistory.objects.create(source=self.source,TaskId='other',Status='3',**values)
        MdmLocationApproved.objects.create(source=self.source,ActionType=0,Approved=True,Reverted=False,**values)
        tasks.publish_add(self.source,task)
        for owner in ('Importer','BPR','BTR','DBM'):
            start=5 if owner=='BTR' else 200
            self.assertEqual(list(MdmLocationAttributes.objects.filter(source=self.source,owner=owner)
                .exclude(WHCode='Existing').order_by('ordinal').values_list('ordinal','WHCode','LL1')),
                [(start,'LP002','P'),(start+1,'LP002','Different'),(start+2,'OTHER','P')])
            self.assertEqual(list(MdmLocationDescription.objects.filter(source=self.source,owner=owner)
                .exclude(WHCode='Existing').order_by('ordinal').values_list('WHDescription',flat=True)),
                ['Retained location','Second occurrence','Other approved task'])
        # A second publication excludes all normalized existing occurrences.
        before=MdmLocationAttributes.objects.filter(source=self.source).count()
        tasks.publish_add(self.source,task)
        self.assertEqual(MdmLocationAttributes.objects.filter(source=self.source).count(),before)

    def test_existing_normalized_identity_excluded(self):
        task=self.backed_queue()
        MdmLocationApproved.objects.filter(source=self.source).update(WHCode='EXISTING  ')
        tasks.publish_add(self.source,task)
        self.assertEqual(MdmLocationAttributes.objects.filter(source=self.source).count(),4)
        self.assertEqual(MdmLocationDescription.objects.filter(source=self.source).count(),4)

    def test_later_statement_failure_preserves_earlier_effect_and_native_completion(self):
        task=self.submit()
        original=MdmLocationDescription.objects.bulk_create
        def fail_bpr(rows, **kwargs):
            if rows and rows[0].owner=='BPR':
                raise DatabaseError('bounded injected second-owner description failure')
            return original(rows,**kwargs)
        with patch.object(MdmLocationDescription.objects,'bulk_create',side_effect=fail_bpr):
            with self.assertLogs('mta.mdm.location_tasks',level='ERROR'):
                self.approve(task)
        self.assertEqual(set(MdmLocationAttributes.objects.filter(source=self.source,WHCode='LP002')
            .values_list('owner',flat=True)),{'Importer','BPR'})
        self.assertEqual(list(MdmLocationDescription.objects.filter(source=self.source,WHCode='LP002')
            .values_list('owner',flat=True)),['Importer'])
        task.refresh_from_db(); self.assertEqual(task.TaskStatus,'7')
        self.assertEqual(MdmSubTask.objects.get(source=self.source).TaskStatus,'4')
        self.assertFalse(MdmLocationApproved.objects.filter(source=self.source).exists())
        self.assertEqual(MdmLocationUploadLog.objects.filter(source=self.source).count(),2)

    def test_normal_consumed_day_guards_still_require_exact_run_markers(self):
        run=CalculationRun.objects.create(input_digest='e'*64,execution_revision='component',
            kind='DAILY_CHAIN',business_date=date(2026,7,3),input_payload={},status='RUNNING')
        capture=MdmDailyInputCapture.objects.create(run=run,source=self.source,
            request_digest='e'*64,revision_digest='e'*64,sku_revision_digest='e'*64,
            location_revision_digest='e'*64,skuloc_revision_digest='e'*64,sql_digest='e'*64,
            nms_active=False,status='CAPTURED')
        self.denied(lambda:self.row(WHCode='daily').save())
        setting('fresh.mdm_current_run',run.pk)
        setting('fresh.mdm_consuming_run',uuid.uuid4())
        self.denied(lambda:self.row(WHCode='daily').save())
        setting('fresh.mdm_consuming_run',run.pk)
        self.denied(lambda:self.row(WHCode='daily').save())
        capture.status='CONSUMED'; capture.consumed_at=self.stamp
        capture.save(update_fields=['status','consumed_at'])
        self.row(WHCode='daily').save()
        MdmLocationAttributes.objects.filter(source=self.source,WHCode='daily').delete()
        run.status='SUCCEEDED'; run.save(update_fields=['status'])
        self.denied(lambda:self.row(WHCode='daily').save())

    def test_sealed_bootstrap_stays_denied(self):
        setting('fresh.mdm_current_bootstrap',self.source.pk)
        setting('fresh.production_initialization',self.initialization.pk)
        self.denied(lambda:self.row().save())

    def test_publication_holds_capture_lock_through_all_eight_statements(self):
        import psycopg
        from mta.mdm import location_publication
        from contextlib import contextmanager
        task=self.backed_queue()
        statements=[]
        with psycopg.connect(**connection.get_connection_params(),autocommit=True) as other:
            @contextmanager
            def observed(source, current_task):
                with other.cursor() as cursor:
                    cursor.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0))',
                        ['fresh-mdm-supplier:'+str(source.pk)])
                    self.assertFalse(cursor.fetchone()[0])
                statements.append(current_task.pk)
                with publication_statement(source,current_task):
                    yield
            with patch.object(location_publication,'publication_statement',observed):
                tasks.publish_add(self.source,task)
            self.assertEqual(statements,[task.pk]*8)
            # In this rollback-only test the outer TestCase owns the xact lock.
            # Also prove the inverse: a pre-existing second-connection owner
            # excludes the database trigger's native branch.
            other_id=self.source.pk+1000000
            with other.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',
                    ['fresh-mdm-supplier:'+str(other_id)])
            def lock():
                with connection.cursor() as cursor:
                    cursor.execute('SELECT mta.lock_native_location_add(%s)',[other_id])
            self.denied(lock)
            with other.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',
                    ['fresh-mdm-supplier:'+str(other_id)])
            lock()
