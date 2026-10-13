"""Small rollback-only PostgreSQL cases; no retained business dataset or replay."""
from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from unittest.mock import patch

from django.db import connection, DatabaseError, transaction
from django.test import TestCase

from mta.mdm import tasks
from mta.mdm.sku_publication import publication_statement
from mta.runtime.initialization_models import ProductionInitialization
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.mdm_models import (MdmSource, MdmTask, MdmSubTask,
    MdmSkuAttributes, MdmSkuDescription, MdmSkuRequested, MdmSkuHistory,
    MdmSkuApproved, MdmSkuUploadLog, MdmLocationDescription)
from mta.runtime.models import CalculationRun


def setting(name, value):
    with connection.cursor() as cursor:
        cursor.execute('SELECT set_config(%s,%s,true)', [name, str(value)])


class NativeSkuAddTests(TestCase):
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
            MdmSkuAttributes.objects.create(source=self.source, owner=owner,
                ordinal=ordinal, SKUCode='Existing')
            MdmSkuDescription.objects.create(source=self.source, owner=owner,
                ordinal=ordinal, SKUCode='Existing', SKUDescription='Existing description')
        self.initialization.input_manifest_digest = 'e'*64
        self.initialization.receipt_digest = 'e'*64
        self.initialization.save(update_fields=['input_manifest_digest','receipt_digest'])
        setting('fresh.production_initialization','')
        setting('fresh.mdm_current_bootstrap','')
        self.catalogue = {'products':{'records':[
            dict(id=1,level_1='P',level_2='A',level_3='X')]}}
        for module in ('mta.mdm.tasks','mta.mdm.task_reads'):
            patcher=patch(module+'.permission_catalogue',return_value=self.catalogue)
            patcher.start(); self.addCleanup(patcher.stop)
        self.requester={'id':2,'name':'Requester'}
        self.reviewer={'id':3,'name':'Reviewer','product_id':[1]}
        self.stamp=datetime(2026,7,3,8,1,15,tzinfo=timezone.utc)

    def submit(self):
        data={'sc':'5328','sd':'Retained SKU','wt':'2.000','SL1':'P','SL2':'A','SL3':'X'}
        with patch.object(tasks,'now',return_value=self.stamp):
            result=tasks.submit(self.source,dict(id=1,taskId='',data=[data],
                product_permissions=[1],all_users=[self.reviewer]),self.requester,1)
        self.assertEqual(result['errorCount'],'0')
        return MdmTask.objects.get(source=self.source,TaskID=result['taskId'])

    def approve(self, task):
        return tasks.approve(self.source,dict(taskId=task.TaskID,
            data=[dict(sc='5328',status='3',comments='component')],
            product_permissions=[1]),self.reviewer)

    def backed_queue(self):
        task=self.submit()
        MdmSkuRequested.objects.filter(source=self.source).update(Approved=True)
        MdmSkuHistory.objects.filter(source=self.source).update(Status='3',ApprovedBy=3)
        tasks.update_approved_queue(self.source,task.TaskID)
        return task

    def row(self, **changes):
        values=dict(source=self.source,owner='Importer',ordinal=200,SKUCode='5328',
            Weight=Decimal('2.000'),SL1='P',SL2='A',SL3='X')
        values.update(changes)
        return MdmSkuAttributes(**values)

    def denied(self, operation):
        with self.assertRaises(DatabaseError), transaction.atomic():
            operation()

    def test_real_submit_approve_exact_eight_rows_and_completion(self):
        task=self.submit()
        self.approve(task)
        for owner in ('Importer','BPR','BTR','DBM'):
            ordinal=5 if owner=='BTR' else 200
            row=MdmSkuAttributes.objects.get(source=self.source,owner=owner,SKUCode='5328')
            actual={f.name:getattr(row,f.name) for f in row._meta.fields if f.name not in ('id','source')}
            expected={name:None for name in ('ElephantOrderCapping','Volume',
                'SL4','SL5',*('c'+str(i) for i in range(1,16)))}
            expected.update(owner=owner,ordinal=ordinal,SKUCode='5328',Weight=Decimal('2.000'),
                SL1='P',SL2='A',SL3='X')
            self.assertEqual(actual,expected)
            desc=MdmSkuDescription.objects.get(source=self.source,owner=owner,SKUCode='5328')
            self.assertEqual((desc.ordinal,desc.SKUDescription),(ordinal,'Retained SKU'))
        task.refresh_from_db(); self.assertEqual(task.TaskStatus,'7')
        sub=MdmSubTask.objects.get(source=self.source)
        self.assertEqual(sub.TaskStatus,'4'); self.assertTrue(sub.DBUpdatedDate)
        self.assertEqual(list(MdmSkuUploadLog.objects.filter(source=self.source)
            .order_by('pk').values_list('ActionId',flat=True)),[5,3])
        self.assertFalse(MdmSkuApproved.objects.filter(source=self.source).exists())
        with connection.cursor() as c:
            c.execute("SELECT current_setting('fresh.sku_add_task',true), current_setting('fresh.sku_add_source',true)")
            self.assertEqual(c.fetchone(),('',''))

    def test_marker_free_and_incorrect_values_owner_ordinal_denied(self):
        task=self.backed_queue()
        self.denied(lambda:self.row().save())
        for changes in ({'SKUCode':'UNBACKED'},{'owner':'Other'},{'ordinal':201},
                        {'Weight':Decimal('9')},{'Volume':Decimal('1')},{'SL1':'wrong'}):
            with self.subTest(changes=changes):
                with publication_statement(self.source,task):
                    self.denied(lambda:self.row(**changes).save())

    def test_wrong_invocation_and_missing_approval_backing_denied(self):
        task=self.backed_queue()
        for field,value in (('MasterId','2'),('Actiontype',2),('source_id',None)):
            with self.subTest(field=field), transaction.atomic():
                if field=='source_id':
                    other=MdmSource.objects.create(digest='f'*64,database_name='other',dll_digest='d'*64,receipt={})
                    value=other.pk
                MdmTask.objects.filter(pk=task.pk).update(**{field:value})
                with publication_statement(self.source,task):
                    self.denied(lambda:self.row().save())
                transaction.set_rollback(True)
        for model,field,value in ((MdmSkuRequested,'Approved',False),
                                  (MdmSkuHistory,'Status','4')):
            with self.subTest(model=model.__name__), transaction.atomic():
                model.objects.filter(source=self.source).update(**{field:value})
                with publication_statement(self.source,task):
                    self.denied(lambda:self.row().save())
                transaction.set_rollback(True)
        MdmSkuApproved.objects.filter(source=self.source).delete()
        with publication_statement(self.source,task):
            self.denied(lambda:self.row().save())

    def test_add_marker_never_authorizes_update_delete_truncate_or_location(self):
        task=self.backed_queue()
        with publication_statement(self.source,task):
            self.denied(lambda:MdmSkuAttributes.objects.filter(source=self.source).update(Weight=1))
            self.denied(lambda:MdmSkuAttributes.objects.filter(source=self.source).delete())
            def truncate():
                with connection.cursor() as c:
                    c.execute('TRUNCATE mta.fresh_mta_mdmskuattributes')
            self.denied(truncate)
            self.denied(lambda:MdmLocationDescription.objects.create(source=self.source,
                owner='Importer',ordinal=1,WHCode='LP002',WHDescription='Unauthorized'))

    def test_duplicate_queue_occurrences_and_other_task_global_queue(self):
        task=self.backed_queue()
        first=MdmSkuApproved.objects.get(source=self.source)
        first.pk=None; first.SKUDescription='Second occurrence'; first.Weight=Decimal('3.000'); first.save()
        # Canonical global queue includes other approved tasks irrespective of
        # ActionType; the invocation task still supplies the selected columns.
        values=dict(SKUCode='OTHER',SKUDescription='Other approved task',Weight=Decimal('4'),SL1='P',SL2='A',SL3='X')
        MdmSkuRequested.objects.create(source=self.source,TaskId='other',ActionType=0,Approved=True,Reverted=False,**values)
        MdmSkuHistory.objects.create(source=self.source,TaskId='other',Status='3',**values)
        MdmSkuApproved.objects.create(source=self.source,ActionType=0,Approved=True,Reverted=False,**values)
        tasks.publish_add(self.source,task)
        for owner in ('Importer','BPR','BTR','DBM'):
            start=5 if owner=='BTR' else 200
            self.assertEqual(list(MdmSkuAttributes.objects.filter(source=self.source,owner=owner)
                .exclude(SKUCode='Existing').order_by('ordinal').values_list('ordinal','SKUCode','Weight')),
                [(start,'5328',Decimal('2')),(start+1,'5328',Decimal('3')),(start+2,'OTHER',Decimal('4'))])
            self.assertEqual(list(MdmSkuDescription.objects.filter(source=self.source,owner=owner)
                .exclude(SKUCode='Existing').order_by('ordinal').values_list('SKUDescription',flat=True)),
                ['Retained SKU','Second occurrence','Other approved task'])
        # A second publication excludes all normalized existing occurrences.
        before=MdmSkuAttributes.objects.filter(source=self.source).count()
        tasks.publish_add(self.source,task)
        self.assertEqual(MdmSkuAttributes.objects.filter(source=self.source).count(),before)

    def test_existing_normalized_identity_excluded(self):
        task=self.backed_queue()
        MdmSkuApproved.objects.filter(source=self.source).update(SKUCode='EXISTING  ')
        tasks.publish_add(self.source,task)
        self.assertEqual(MdmSkuAttributes.objects.filter(source=self.source).count(),4)
        self.assertEqual(MdmSkuDescription.objects.filter(source=self.source).count(),4)

    def test_later_statement_failure_preserves_earlier_effect_and_native_completion(self):
        task=self.submit()
        original=MdmSkuDescription.objects.bulk_create
        def fail_bpr(rows, **kwargs):
            if rows and rows[0].owner=='BPR':
                raise DatabaseError('bounded injected second-owner description failure')
            return original(rows,**kwargs)
        with patch.object(MdmSkuDescription.objects,'bulk_create',side_effect=fail_bpr):
            with self.assertLogs('mta.mdm.tasks',level='ERROR'):
                self.approve(task)
        self.assertEqual(set(MdmSkuAttributes.objects.filter(source=self.source,SKUCode='5328')
            .values_list('owner',flat=True)),{'Importer','BPR'})
        self.assertEqual(list(MdmSkuDescription.objects.filter(source=self.source,SKUCode='5328')
            .values_list('owner',flat=True)),['Importer'])
        task.refresh_from_db(); self.assertEqual(task.TaskStatus,'7')
        self.assertEqual(MdmSubTask.objects.get(source=self.source).TaskStatus,'4')
        self.assertFalse(MdmSkuApproved.objects.filter(source=self.source).exists())
        self.assertEqual(MdmSkuUploadLog.objects.filter(source=self.source).count(),2)

    def test_normal_consumed_day_guards_still_require_exact_run_markers(self):
        run=CalculationRun.objects.create(input_digest='e'*64,execution_revision='component',
            kind='DAILY_CHAIN',business_date=date(2026,7,3),input_payload={},status='RUNNING')
        capture=MdmDailyInputCapture.objects.create(run=run,source=self.source,
            request_digest='e'*64,revision_digest='e'*64,sku_revision_digest='e'*64,
            location_revision_digest='e'*64,skuloc_revision_digest='e'*64,sql_digest='e'*64,
            nms_active=False,status='CAPTURED')
        self.denied(lambda:self.row(SKUCode='daily').save())
        setting('fresh.mdm_current_run',run.pk)
        setting('fresh.mdm_consuming_run',uuid.uuid4())
        self.denied(lambda:self.row(SKUCode='daily').save())
        setting('fresh.mdm_consuming_run',run.pk)
        self.denied(lambda:self.row(SKUCode='daily').save())
        capture.status='CONSUMED'; capture.consumed_at=self.stamp
        capture.save(update_fields=['status','consumed_at'])
        self.row(SKUCode='daily').save()
        MdmSkuAttributes.objects.filter(source=self.source,SKUCode='daily').delete()
        run.status='SUCCEEDED'; run.save(update_fields=['status'])
        self.denied(lambda:self.row(SKUCode='daily').save())

    def test_sealed_bootstrap_stays_denied(self):
        setting('fresh.mdm_current_bootstrap',self.source.pk)
        setting('fresh.production_initialization',self.initialization.pk)
        self.denied(lambda:self.row().save())

    def test_publication_holds_capture_lock_through_all_eight_statements(self):
        import psycopg
        from mta.mdm import sku_publication
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
            with patch.object(sku_publication,'publication_statement',observed):
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
                    cursor.execute('SELECT mta.lock_native_sku_add(%s)',[other_id])
            self.denied(lock)
            with other.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',
                    ['fresh-mdm-supplier:'+str(other_id)])
            lock()
