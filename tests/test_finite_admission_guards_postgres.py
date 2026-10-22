"""Direct finite SQL guard proof using disposable metadata, never business facts.

Replica mode is limited to explicit fixture setup; all assertions exercise the
installed guards with normal replication and independent PostgreSQL sessions.
"""
import os
from datetime import date
import threading
import time
from uuid import uuid4

from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.serialization import digest
from tests.test_ingestion_ownership_postgres import IngestionPostgresTests,RUNTIME


class FiniteAdmissionGuardsPostgresTests(IngestionPostgresTests):
    proof_database='vf_btr_terminal_admission_20261022' if os.environ.get('VF_CAPTURED_TERMINAL_PROOF')=='1' else 'vf_admission_guards_20261022'

    def rollback(self):
        if self.atomic is not None:super().rollback()

    def test_exact_finite_sql_guards_and_competing_creation(self):
        from mta.runtime.models import CalculationRun
        from mta.runtime.daily_feed_models import DailyFeedAttempt
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from mta.runtime.report_generation_models import DailyReportGeneration,DailyReportOrderRouteSource
        from mta.runtime import captured_input as ci
        from mta.runtime.input_v3 import _live_identity
        import psycopg
        from psycopg.types.json import Jsonb

        runs=[];captures=[];attempts=[]
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL session_replication_role=replica')
        for index in range(7):
            run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=date(2026,4,8),
                execution_revision='metadata-prefix-'+str(index),evidence_mode='production',
                input_digest='6'*64,input_payload={},status='RUNNING' if index==6 else 'FAILED')
            capture=MdmDailyInputCapture.objects.create(run=run,source=self.source,
                origin=captures[-1] if captures else None,request_digest='a'*64,revision_digest='b'*64,
                sku_revision_digest='c'*64,location_revision_digest='d'*64,skuloc_revision_digest='e'*64,
                sql_digest='f'*64,nms_active=False)
            attempt=DailyFeedAttempt.objects.create(initialization=self.owner,business_date=run.business_date,
                batch_id='metadata-frozen',request_key=digest(str(index)),batch_digest='7'*64,
                binding_digest='8'*64,input_sha256='9'*64,run=run,status=run.status,phase='CALCULATE',
                archive_path='/metadata/'+str(index),certification=self.cert,master_revision=self.revision,
                accepted_facts={'metadata_only':True} if index==0 else {})
            if index==0:
                run.input_payload={'schema':'fresh-daily-input-manifest-v3','content_digest':run.input_digest}
            else:
                run.input_payload=dict(schema=ci.SCHEMA if index==1 else ci.SECOND,
                    identity=_live_identity(run,reading=False) if run.status=='RUNNING' else
                        dict(database_name=self.proof_database,database_oid=self.body['database_oid'],
                             source_digest=self.source.digest,owner_kind='run',owner_id=str(run.pk)),
                    origin_run_id=str(runs[-1].pk),origin_manifest_digest=runs[-1].input_manifest_digest,
                    content_digest=run.input_digest,images={})
                if index>1:run.input_payload.update(physical_origin_run_id=str(runs[0].pk),
                    physical_origin_manifest_digest=runs[0].input_manifest_digest)
            run.input_manifest_digest=digest(run.input_payload)
            run.save(update_fields=['input_payload','input_manifest_digest'])
            runs.append(run);captures.append(capture);attempts.append(attempt)
        leaf=runs[-1];parent=attempts[-1]
        child=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=leaf.business_date,
            execution_revision='native-finite-'+self.release['source_commit'],evidence_mode='production',
            input_digest=leaf.input_digest,input_payload={},status='RUNNING')
        cap=MdmDailyInputCapture.objects.create(run=child,source=self.source,origin=captures[-1],
            request_digest='a'*64,revision_digest='b'*64,sku_revision_digest='c'*64,
            location_revision_digest='d'*64,skuloc_revision_digest='e'*64,sql_digest='f'*64,nms_active=False)
        with connection.cursor() as cursor:cursor.execute('SET LOCAL session_replication_role=origin')
        physical,rows,prefix=ci.finite_prefix(leaf)
        child.input_payload=ci.finite_manifest(child,leaf,expected_prefix_digest=prefix,
            packaged_source=self.release['source_commit'])
        child.input_manifest_digest=digest(child.input_payload)
        child.save(update_fields=['input_payload','input_manifest_digest'])
        final=os.environ.get('VF_CAPTURED_FINAL_PROOF')=='1'
        retry=os.environ.get('VF_CAPTURED_RETRY_PROOF')=='1' or final
        terminal=os.environ.get('VF_CAPTURED_TERMINAL_PROOF')=='1' or retry
        if terminal:
            first={field.attname:getattr(parent,field.attname) for field in parent._meta.concrete_fields
                if field.name not in ('id','attempt_id','created_at','updated_at')}
            first.update(run_id=child.pk,recovery_origin_id=parent.pk,request_key=digest('stopped-finite'),
                archive_path='/metadata/stopped-finite',status='RUNNING',phase='CALCULATE',accepted_facts={},prepared_context={},error={})
            parent=DailyFeedAttempt.objects.create(**first)
            leaf=child
            with connection.cursor() as cursor:cursor.execute('SET LOCAL session_replication_role=replica')
            child=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=leaf.business_date,
                execution_revision='native-terminal-'+self.release['source_commit'],evidence_mode='production',
                input_digest=leaf.input_digest,input_payload={},status='RUNNING')
            cap=MdmDailyInputCapture.objects.create(run=child,source=self.source,origin=cap,
                request_digest='a'*64,revision_digest='b'*64,sku_revision_digest='c'*64,
                location_revision_digest='d'*64,skuloc_revision_digest='e'*64,sql_digest='f'*64,nms_active=False)
            with connection.cursor() as cursor:cursor.execute('SET LOCAL session_replication_role=origin')
            physical,rows,prefix=ci.terminal_prefix(leaf)
            child.input_payload=ci.terminal_manifest(child,leaf,expected_prefix_digest=prefix,
                packaged_source=self.release['source_commit'])
            child.input_manifest_digest=digest(child.input_payload)
            child.save(update_fields=['input_payload','input_manifest_digest'])
        if retry:
            values={field.attname:getattr(parent,field.attname) for field in parent._meta.concrete_fields
                    if field.name not in ('id','attempt_id','created_at','updated_at')}
            values.update(run_id=child.pk,recovery_origin_id=parent.pk,request_key=digest('failed-terminal'),
                archive_path='/metadata/failed-terminal',status='RUNNING',phase='CALCULATE',accepted_facts={},prepared_context={},error={})
            parent=DailyFeedAttempt.objects.create(**values)
            child.status='FAILED';child.save(update_fields=['status'])
            parent.status='FAILED';parent.save(update_fields=['status'])
            leaf=child
            with connection.cursor() as cursor:cursor.execute('SET LOCAL session_replication_role=replica')
            child=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=leaf.business_date,
                execution_revision='native-terminal-retry-'+self.release['source_commit'],evidence_mode='production',
                input_digest=leaf.input_digest,input_payload={},status='RUNNING')
            cap=MdmDailyInputCapture.objects.create(run=child,source=self.source,origin=cap,
                request_digest='a'*64,revision_digest='b'*64,sku_revision_digest='c'*64,
                location_revision_digest='d'*64,skuloc_revision_digest='e'*64,sql_digest='f'*64,nms_active=False)
            with connection.cursor() as cursor:cursor.execute('SET LOCAL session_replication_role=origin')
            physical,rows,prefix=ci.retry_prefix(leaf)
            child.input_payload=ci.terminal_manifest(child,leaf,expected_prefix_digest=prefix,
                packaged_source=self.release['source_commit'],retry=True)
            child.input_manifest_digest=digest(child.input_payload)
            child.save(update_fields=['input_payload','input_manifest_digest'])
        if final:
            values={field.attname:getattr(parent,field.attname) for field in parent._meta.concrete_fields
                    if field.name not in ('id','attempt_id','created_at','updated_at')}
            values.update(run_id=child.pk,recovery_origin_id=parent.pk,request_key=digest('failed-v5'),
                archive_path='/metadata/failed-v5',status='RUNNING',phase='CALCULATE',accepted_facts={},prepared_context={},error={})
            parent=DailyFeedAttempt.objects.create(**values)
            child.status='FAILED';child.save(update_fields=['status'])
            parent.status='FAILED';parent.save(update_fields=['status'])
            leaf=child
            with connection.cursor() as cursor:cursor.execute('SET LOCAL session_replication_role=replica')
            child=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=leaf.business_date,
                execution_revision='native-final-attempt-'+self.release['source_commit'],evidence_mode='production',
                input_digest=leaf.input_digest,input_payload={},status='RUNNING')
            cap=MdmDailyInputCapture.objects.create(run=child,source=self.source,origin=cap,
                request_digest='a'*64,revision_digest='b'*64,sku_revision_digest='c'*64,
                location_revision_digest='d'*64,skuloc_revision_digest='e'*64,sql_digest='f'*64,nms_active=False)
            with connection.cursor() as cursor:cursor.execute('SET LOCAL session_replication_role=origin')
            physical,rows,prefix=ci.final_prefix(leaf)
            child.input_payload=ci.terminal_manifest(child,leaf,expected_prefix_digest=prefix,
                packaged_source=self.release['source_commit'],additional=True)
            child.input_manifest_digest=digest(child.input_payload)
            child.save(update_fields=['input_payload','input_manifest_digest'])
        prefix_reader=ci.final_prefix if final else ci.retry_prefix if retry else ci.terminal_prefix if terminal else ci.finite_prefix
        self.atomic.__exit__(None,None,None);self.atomic=None
        original_rows=digest(rows)
        def values(**changes):
            result={field.attname:getattr(parent,field.attname) for field in parent._meta.concrete_fields
                    if field.name not in ('id','attempt_id','created_at','updated_at')}
            result.update(run_id=child.pk,recovery_origin_id=parent.pk,request_key=digest(str(uuid4())),
                archive_path='/metadata/finite-'+str(uuid4()),status='RUNNING',phase='CALCULATE',
                accepted_facts={},prepared_context={},error={})
            result.update(changes)
            return result
        def reject(**changes):
            with self.assertRaises(DatabaseError),transaction.atomic():
                DailyFeedAttempt.objects.create(**values(**changes))
        # Ordinary attempt uniqueness remains exactly active for NULL origins.
        reject(recovery_origin_id=None)
        for changes in (dict(business_date=date(2026,4,9)),dict(initialization_id=uuid4()),
                dict(recovery_origin_id=attempts[0].pk),dict(recovery_origin_id=parent.pk,id=parent.pk),
                dict(input_sha256='0'*64),dict(certification_id=None),dict(master_revision_id=None)):
            with self.subTest(changes=changes):reject(**changes)
        # Independently mutate the actual child manifest. Rehashing its own
        # checksum cannot authenticate a false original-prefix or physical pin.
        for field,value in (('prefix_digest','0'*64),('physical_origin_run_id',str(uuid4())),
                ('physical_origin_manifest_digest','0'*64),('origin_run_id',str(child.pk)),
                ('packaged_source','0'*40)):
            with self.subTest(field=field),transaction.atomic():
                bad=dict(child.input_payload,**{field:value})
                CalculationRun.objects.filter(pk=child.pk).update(input_payload=bad,input_manifest_digest=digest(bad))
                reject()
                transaction.set_rollback(True)
        # Cyclic and shortened metadata are explicit scratch fixtures, not an
        # attempted production mutation or a reader-only mock.
        for origin in (leaf.pk,None):
            with self.subTest(origin=origin),transaction.atomic(),connection.cursor() as cursor:
                cursor.execute('SET LOCAL session_replication_role=replica')
                MdmDailyInputCapture.objects.filter(pk=leaf.pk).update(origin_id=origin)
                cursor.execute('SET LOCAL session_replication_role=origin')
                reject()
                transaction.set_rollback(True)
        for model,fields in ((DailyReportGeneration,dict(source_digest='0'*64,recipe_digest='0'*64)),
                (DailyReportOrderRouteSource,dict(ordinal=1,OrderKey=1,SrcWhCode=None,DestWhCode=None,DueDate=None))):
            with self.subTest(model=model.__name__),transaction.atomic(),connection.cursor() as cursor:
                cursor.execute('SET LOCAL session_replication_role=replica')
                model.objects.create(run=leaf,**fields)
                cursor.execute('SET LOCAL session_replication_role=origin')
                reject()
                transaction.set_rollback(True)
        # Same immutable prefix has the same digest under independent runtime
        # READ ONLY transactions despite different caller timezone/date styles.
        options=connection.settings_dict
        params=dict(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
                    user=options['USER'],password=options['PASSWORD'])
        with connection.cursor() as cursor:
            cursor.execute('GRANT EXECUTE ON FUNCTION mta.'+('final' if final else 'retry' if retry else 'terminal' if terminal else 'finite')+'_capture_prefix_digest(uuid) TO '+RUNTIME)
        for zone,style in (('Asia/Kolkata','SQL, DMY'),('America/New_York','German, DMY')):
            with psycopg.connect(**params) as runtime:
                runtime.execute('SET TRANSACTION READ ONLY')
                runtime.execute('SET LOCAL ROLE '+RUNTIME)
                runtime.execute("SELECT set_config('TimeZone',%s,true),set_config('DateStyle',%s,true)",[zone,style])
                actual=runtime.execute('SELECT mta.'+('final' if final else 'retry' if retry else 'terminal' if terminal else 'finite')+'_capture_prefix_digest(%s)',[leaf.pk]).fetchone()[0]
                self.assertEqual(actual,prefix)
        # Two genuine INSERTs enter the new guard. The second waits on the
        # parent's row lock, then loses to the committed first child's identity.
        insert=values();insert.update(attempt_id=uuid4(),created_at=timezone.now(),updated_at=timezone.now())
        columns=list(insert)
        sql='INSERT INTO mta.fresh_mta_dailyfeedattempt ('+','.join(columns)+') VALUES ('+','.join(['%s']*len(columns))+') RETURNING id'
        def adapt(data):return [Jsonb(data[key]) if isinstance(data[key],(dict,list)) else data[key] for key in columns]
        outcome=[];started=threading.Event()
        competitor=psycopg.connect(**params)
        loser_values=dict(insert,attempt_id=uuid4(),request_key=digest(str(uuid4())),archive_path='/metadata/race-loser')
        def competing_insert():
            try:
                competitor.execute("SET LOCAL lock_timeout='8s'")
                started.set()
                competitor.execute(sql,adapt(loser_values));competitor.commit()
                outcome.append('unexpected-success')
            except psycopg.Error as error:
                competitor.rollback();outcome.append(error.sqlstate)
        try:
            with psycopg.connect(**params) as first:
                winner_id=first.execute(sql,adapt(insert)).fetchone()[0]
                thread=threading.Thread(target=competing_insert,daemon=True);thread.start()
                self.assertTrue(started.wait(2))
                blocked=False;deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=%s",[competitor.info.backend_pid])
                        blocked=cursor.fetchone()==(True,)
                    if blocked:break
                    time.sleep(.02)
                self.assertTrue(blocked,'Second real INSERT must wait on the canonical parent lock')
                first.commit()
            thread.join(10);self.assertFalse(thread.is_alive())
            self.assertEqual(outcome,['23505'])
        finally:
            competitor.close()
        winner=DailyFeedAttempt.objects.get(pk=winner_id)
        self.assertEqual(winner.recovery_origin_id,parent.pk)
        self.assertEqual(ci.origin(child).pk,physical.pk)
        self.assertEqual(digest(prefix_reader(leaf)[1]),original_rows)
        # Every committed finite child, including a failed one, consumes the
        # origin forever. No eighth owner or mutable replacement is admitted.
        reject()
        reject(recovery_origin_id=winner.pk)
        for model,pk,changes in ((DailyFeedAttempt,winner.pk,dict(recovery_origin_id=None)),
                (DailyFeedAttempt,winner.pk,dict(input_sha256='0'*64)),
                (DailyFeedAttempt,winner.pk,dict(status='PUBLISHED')),
                (DailyFeedAttempt,winner.pk,dict(status='FAILED')),
                (DailyFeedAttempt,parent.pk,dict(status='FAILED')),
                (CalculationRun,leaf.pk,dict(status='FAILED')),
                (MdmDailyInputCapture,leaf.pk,dict(status='CONSUMED'))):
            with self.subTest(model=model.__name__,changes=changes),self.assertRaises(DatabaseError),transaction.atomic():
                model.objects.filter(pk=pk).update(**changes)
        with transaction.atomic():
            CalculationRun.objects.filter(pk=child.pk).update(status='FAILED')
            DailyFeedAttempt.objects.filter(pk=winner.pk).update(status='FAILED')
            with self.assertRaises(DatabaseError),transaction.atomic():
                DailyFeedAttempt.objects.filter(pk=winner.pk).update(status='RUNNING')
            transaction.set_rollback(True)
        # A genuine canonical two-capture sibling must fail even before either
        # competing attempt can claim the unique origin/date owner.
        with transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('SET LOCAL session_replication_role=replica')
            sibling=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=leaf.business_date,
                execution_revision='metadata-adversarial-sibling',input_digest=leaf.input_digest,
                input_payload={},status='RUNNING')
            copied={field.attname:getattr(cap,field.attname) for field in cap._meta.concrete_fields
                    if field.name not in ('run','captured_at')}
            MdmDailyInputCapture.objects.create(run=sibling,**copied)
            cursor.execute('SET LOCAL session_replication_role=origin')
            reject(run_id=sibling.pk)
            transaction.set_rollback(True)
        print(('FINAL_DIRECT_SQL_GUARDS_PASS' if final else 'TERMINAL_DIRECT_SQL_GUARDS_PASS' if terminal else 'FINITE_DIRECT_SQL_GUARDS_PASS')+' metadata-only exact-prefix UTC runtime-read ordinaryduplicate foreigncycle sibling childparent immutable lifecycle competingINSERT')
