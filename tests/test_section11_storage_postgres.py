"""Production COPY on typed tables with actual large-row reader representation.

Rollback-only components, never native day executions or operational openings.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import os,unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_SECTION11_SQL_GUARDS')=='1','Owned Section11 SQL proof required')
class Section11StoragePostgresTests(unittest.TestCase):
    def test_production_copy_full_spool_readonly_reader_and_late_rollback(self):
        from django.db import connection,transaction,DatabaseError
        from mta.runtime.models import CalculationRun
        from mta.runtime import relational_state as typed
        from mta.row_sequences import RecordRows
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'],'vf_section9_contracts_20261021')
        before=CalculationRun.objects.count()
        rows=[dict(SKUCode='S'+str(i//2),WHCode='W',Stock=i%11-3,Consumption=0,
            GIT=i%3,Receipts=0,PSO=0,BlueZone=None,ReportDate='2037-04-10') for i in range(10001)]
        with transaction.atomic():
            run=CalculationRun.objects.create(kind='COMPONENT_PROOF',business_date='2037-04-10',
                execution_revision='section11-copy-spool-component',input_digest=digest(rows),input_payload={},status='RUNNING')
            meta=typed.save_image(run,'copy/component','copy/component',RecordRows.from_rows(rows),table='BPR/DailyConsumption')
            loaded=typed.load_image(run,meta)
            self.assertIsInstance(loaded,RecordRows);self.assertTrue(hasattr(loaded,'_data'))
            self.assertEqual(list(loaded),rows)
            with patch.dict(os.environ):
                os.environ.pop('VF_WORK_ROOT',None)
                readonly=typed.load_image(run,meta)
                self.assertIsInstance(readonly,RecordRows);self.assertEqual(list(readonly),rows)
            with self.assertRaises(DatabaseError),transaction.atomic():
                typed.save_image(run,meta['image'],'copy/component',rows,table='BPR/DailyConsumption')
            self.assertEqual(list(typed.iter_image(run,meta)),rows)
            # Same wire type throughout passes the complete describe scan;
            # only the last row fails db_value after 10,000 COPY writes.
            bad=[dict(row,Stock=float(row['Stock'])) for row in rows];bad[-1]['Stock']=1.5
            with self.assertRaises(ValueError),transaction.atomic():
                typed.save_image(run,'copy/fail-late','copy/fail-late',bad,table='BPR/DailyConsumption')
            with connection.cursor() as cursor:
                cursor.execute('SELECT count(*) FROM mta_state.bpr_dailyconsumption WHERE vf_run_id=%s AND vf_image=%s',[run.pk,'copy/fail-late'])
                self.assertEqual(cursor.fetchone()[0],0)
            transaction.set_rollback(True)
        self.assertEqual(CalculationRun.objects.count(),before)
        print('SECTION11_PRODUCTION_COPY_PASS 10001 full values/NULL/duplicate keys/ordinals real spool/read-only factory/late error/duplicate rejection/outer rollback')

    def test_version_two_derived_table_keeps_original_revision_contract(self):
        from django.db import connection,transaction
        from mta.runtime.models import CalculationRun,ProductionInitialization
        from mta.runtime.accepted_daily import epochs
        from mta.runtime import relational_state as typed
        owner=ProductionInitialization.objects.get()
        with transaction.atomic():
            run=CalculationRun.objects.create(kind='COMPONENT_PROOF',business_date='2037-04-10',
                execution_revision='section11-v2-compatibility-component',input_digest='d'*64,input_payload={},
                status='RUNNING',production_manifest={'version':2})
            meta=typed.save_image(run,'closing/btr/BufferTrendPhysicalInv','closing/btr/BufferTrendPhysicalInv',
                [dict(SKUCode='S',WhCode='W',Norm=None)])
            self.assertEqual(typed.load_image(run,meta),[dict(SKUCode='S',WhCode='W',Norm=None)])
            cut=epochs(owner.pk)
            with connection.cursor() as cursor:
                cursor.execute('UPDATE mta_state.btr_buffertrendphysicalinv SET "Norm"=1 WHERE vf_run_id=%s',[run.pk])
            changed=epochs(owner.pk)
            self.assertEqual(changed[:3],cut[:3]);self.assertEqual(changed[3],cut[3]+1)
            self.assertEqual(changed[4],cut[4])
            with self.assertRaisesRegex(ValueError,'value/type/multiplicity drift'):
                typed.load_image(run,meta)
            transaction.set_rollback(True)
        self.assertFalse(CalculationRun.objects.filter(pk=run.pk).exists())
        print('SECTION11_V2_FALLTHROUGH_PASS old typed values/NULL/order read; old write invalidates; tampering detected; rollback retained')


if __name__=='__main__':unittest.main()
