"""Two-connection guard component proof, never an accepted operational day.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import os,threading,time,unittest


@unittest.skipUnless(os.environ.get('VF_REPORT_GUARD_PROOF')=='1','Owned Section11 SQL guard proof required')
class ReportGuardConcurrencyTests(unittest.TestCase):
    def test_late_append_waits_for_seal_and_is_denied_without_fk_deadlock(self):
        import psycopg
        from django.db import connection,transaction
        from django.utils import timezone
        from mta.runtime.models import CalculationRun,DailyReportGeneration
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        # Unaccepted header with no capture/opening: only the SQL guard contract.
        run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
            execution_revision='guard-seal-concurrency-component-only',input_digest='a'*64,
            input_payload={},status='SUCCEEDED',production_manifest={'version':3},production_digest='b'*64)
        generation=DailyReportGeneration.objects.create(run=run,source_digest=run.production_digest,recipe_digest='c'*64)
        params=connection.get_connection_params();params['application_name']='guard_report_append_race'
        result=[];started=threading.Event()
        def append():
            try:
                with psycopg.connect(**params) as other,other.cursor() as cursor:
                    cursor.execute("SET LOCAL statement_timeout='10s'")
                    cursor.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(run.pk)])
                    started.set()
                    cursor.execute('INSERT INTO mta_state.btr_btrsnapshotforui (vf_run_id,vf_image,vf_ordinal) VALUES (%s,%s,991)',
                        [run.pk,'closing/btr/BTRSnapshotForUI'])
                result.append('unexpected-append')
            except Exception as error:result.append(str(error))
        thread=threading.Thread(target=append,daemon=True)
        try:
            with transaction.atomic():
                generation=DailyReportGeneration.objects.select_for_update().get(pk=generation.pk)
                thread.start();self.assertTrue(started.wait(3))
                waiting=False
                for _ in range(60):
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='guard_report_append_race' AND wait_event_type='Lock')")
                        waiting=cursor.fetchone()[0]
                    if waiting:break
                    time.sleep(.05)
                self.assertTrue(waiting,'Appended row must wait after its run FK check, before seal')
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(run.pk)])
                generation.metadata={'component_guard_probe':True};generation.digest=digest(generation.metadata)
                generation.status='READY';generation.sealed_at=timezone.now()
                generation.save(update_fields=['metadata','digest','status','sealed_at'])
        finally:thread.join(12)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(result),1)
        self.assertIn('Derived v3 generation is absent, drifted or sealed',result[0])
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM mta_state.btr_btrsnapshotforui WHERE vf_run_id=%s',[run.pk])
            self.assertEqual(cursor.fetchone()[0],0)
        generation.refresh_from_db();self.assertEqual(generation.status,'READY')
        self.assertFalse(run.checkpoints.exists());self.assertFalse(hasattr(run,'mdm_input_capture'))
        print('GUARD_REPORT_CONCURRENT_APPEND_PASS waited on generation; READY recheck denied/no FK deadlock; retained metadata-only run='+str(run.pk))


    def test_btr_row_lock_acl_and_sealed_append(self):
        import psycopg
        from django.db import connection,transaction,DatabaseError
        from django.utils import timezone
        from mta.runtime.models import CalculationRun,BtrReportingGeneration,BtrJoinReference
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
            execution_revision='guard-btr-concurrency-component-only',input_digest='a'*64,
            input_payload={},status='SUCCEEDED',production_manifest={'version':3},production_digest='b'*64)
        generation=BtrReportingGeneration.objects.create(run=run,source_digest='b'*64,source_kind=run.kind,business_date=run.business_date)
        params=connection.get_connection_params();params['application_name']='guard_btr_append_race'
        result=[];started=threading.Event()
        def append():
            try:
                with psycopg.connect(**params) as other,other.cursor() as c:
                    c.execute("SET LOCAL statement_timeout='10s'")
                    started.set()
                    c.execute("INSERT INTO mta.fresh_mta_btrjoinreference (generation_id,branch,export,a_ordinal) VALUES(%s,'tech',false,0)",[generation.pk])
                result.append('unexpected-append')
            except Exception as error:result.append(str(error))
        thread=threading.Thread(target=append,daemon=True)
        try:
            with transaction.atomic():
                generation=BtrReportingGeneration.objects.select_for_update().get(pk=generation.pk)
                thread.start();self.assertTrue(started.wait(3));waiting=False
                for _ in range(60):
                    with connection.cursor() as c:
                        c.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='guard_btr_append_race' AND wait_event_type='Lock')")
                        waiting=c.fetchone()[0]
                    if waiting:break
                    time.sleep(.05)
                self.assertTrue(waiting)
                generation.status='READY';generation.rows_digest=digest([]);generation.completed_at=timezone.now()
                generation.save(update_fields=['status','rows_digest','completed_at'])
        finally:thread.join(12)
        self.assertFalse(thread.is_alive());self.assertEqual(len(result),1)
        self.assertIn('BTR references require a private BUILDING generation',result[0])
        self.assertFalse(BtrJoinReference.objects.filter(generation=generation).exists())
        with self.assertRaises(DatabaseError),transaction.atomic():
            with connection.cursor() as c:
                c.execute('SET LOCAL ROLE vectorflow_mta_runtime')
                c.execute("INSERT INTO mta.fresh_mta_btrjoinreference (generation_id,branch,export,a_ordinal) VALUES(%s,'tech',false,0)",[generation.pk])
        with self.assertRaisesRegex(DatabaseError,'cannot be truncated'),transaction.atomic():
            with connection.cursor() as c:c.execute('TRUNCATE mta.fresh_mta_btrjoinreference')
        print('GUARD_BTR_CONCURRENT_APPEND_PASS FOR SHARE waits, seal denial/runtime ACL/TRUNCATE preserved; retained metadata-only run='+str(run.pk))


if __name__=='__main__':unittest.main()
