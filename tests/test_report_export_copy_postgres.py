"""Export transport qualification on the explicitly owned PostgreSQL fixture.

Rollback-only components; no calculation, operational day or serving change.
"""
import json
import os
import types
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_REPORT_EXPORT_COPY_PROOF')=='1',
                     'Explicit owned report-export PostgreSQL proof required')
class ReportExportCopyPostgresTests(unittest.TestCase):
    def setUp(self):
        from django.db import connection, transaction
        from mta.runtime.models import CalculationRun, DailyReportGeneration
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        with connection.cursor() as cursor:
            cursor.execute("SELECT oid,shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(cursor.fetchone(),(1598463,'owned terminal SMALL takeover thread01a16058 20261022; not working/serving'))
            cursor.execute("SELECT count(*) FROM pg_trigger WHERE tgname IN ('v3_report_insert','ingestion_watch_insert') AND tgrelid IN ('mta_state.report_export_row'::regclass,'mta_state.report_export_cell'::regclass) AND tgenabled='O'")
            self.assertEqual(cursor.fetchone()[0],4)
        self.before=CalculationRun.objects.count()
        self.atomic=transaction.atomic();self.atomic.__enter__()
        self.addCleanup(self.rollback)
        self.run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
            execution_revision='report-export-copy-component-only',input_digest='a'*64,
            input_payload={},status='SUCCEEDED',production_manifest={'version':3,
                'reports':[{'stage':'norm0-export','deferred':{}}]},production_digest='b'*64)
        self.generation=DailyReportGeneration.objects.create(run=self.run,
            source_digest=self.run.production_digest,recipe_digest='c'*64)
        self.owner(str(self.run.pk))

    def rollback(self):
        from django.db import transaction
        from mta.runtime.models import CalculationRun
        transaction.set_rollback(True);self.atomic.__exit__(None,None,None)
        self.assertEqual(CalculationRun.objects.count(),self.before)

    def owner(self,value):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.report_generation',%s,true)",[value])

    def populations(self):
        from django.db import connection
        with connection.cursor() as cursor:
            counts=[]
            for table in ('report_export_row','report_export_cell'):
                cursor.execute('SELECT count(*) FROM mta_state.'+table+' WHERE vf_run_id=%s',[self.run.pk])
                counts.append(cursor.fetchone()[0])
            return tuple(counts)

    def test_exact_baseline_types_ragged_empty_duplicates_and_byte_bounds(self):
        from django.db import transaction
        from mta.runtime import relational_state as typed
        from mta.serialization import digest,storage
        baseline=types.ModuleType('pinned_export_baseline')
        baseline.__file__=typed.__file__
        source=Path(os.environ['VF_REPORT_EXPORT_BASELINE']).read_text()
        import hashlib
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),os.environ['VF_REPORT_EXPORT_BASELINE_SHA256'])
        exec(compile(source,'pinned_export_baseline','exec'),baseline.__dict__)
        rows=[{'values':[]},{'values':[None,'',True,False,0,1,-1,0.0,-1e-200]},
            {'values':['é漢字\n\t\\"',-(2**63),2**63-1,Decimal('1.2300'),
                       date(2026,4,8),datetime(2026,4,8,1,2,3),1.25,-1e200]}]
        rows+=rows[:2]
        path='reports/norm0-export/ReportRows'
        signed_results={}
        for label,writer in (('baseline',baseline),('candidate',typed)):
            with transaction.atomic():
                signed=[{'values':[-0.0]}];seen=[]
                signed_meta=writer.save_export(self.run,path,signed)
                try:
                    seen.extend(writer.iter_export(self.run,signed_meta))
                except ValueError as error:
                    self.assertIn('Report projection drift',str(error))
                    self.assertEqual(digest(seen),digest([{'values':[0.0]}]))
                    signed_results[label]='positive-zero-readback-rejected'
                else:
                    self.assertEqual(digest(seen),digest(signed))
                    signed_results[label]='negative-zero-exact'
                transaction.set_rollback(True)
        self.assertEqual(signed_results['baseline'],'positive-zero-readback-rejected')
        with transaction.atomic():
            original=baseline.save_export(self.run,path,rows)
            original_values=[]
            try:
                original_values.extend(baseline.iter_export(self.run,original))
            except ValueError:
                self.assertEqual(digest(original_values),digest(storage(rows)),
                    'Pinned baseline roundtrip differs: expected='+repr(storage(rows))+' actual='+repr(original_values))
                raise
            transaction.set_rollback(True)
        self.assertEqual(self.populations(),(0,0))
        meta=typed.save_export(self.run,path,rows)
        actual=list(typed.iter_export(self.run,meta))
        self.assertEqual(meta,original);self.assertEqual(actual,original_values)
        self.assertEqual(digest(actual),digest(storage(rows)))
        self.assertEqual([[type(v) for v in r['values']] for r in actual],
                         [[type(v) for v in r['values']] for r in original_values])
        # Force byte-bounded chunks and a valid scalar larger than the budget;
        # no new value-size rejection may be introduced by the transport.
        lengths=[];real_summary=typed.summary
        def observe(name,**values):
            if name=='report_export_transport':lengths.append(values)
            real_summary(name,**values)
        # Use the already admitted second image of this same source stage.
        wide=[{'values':['x'*700000]},{'values':['é'*700000]},{'values':[]}]
        with patch.object(typed,'summary',side_effect=observe):
            wide_meta=typed.save_export(self.run,'reports/norm0-export/ReportHeader',wide)
        self.assertEqual(list(typed.iter_export(self.run,wide_meta)),wide)
        self.assertEqual(lengths[-1]['statements'],2)
        self.assertEqual(lengths[-1]['max_chunk_records'],1)
        print('EXPORT_COPY_BASELINE_PASS exact metadata/types/NULL/Unicode/ragged/zero-cell/duplicate/oversized-scalar signed-zero='+json.dumps(signed_results))

    def test_actual_large_representation_and_linear_transport_counts(self):
        from django.db import transaction
        from mta.runtime import relational_state as typed
        from mta.row_sequences import RecordRows
        from mta.serialization import digest
        observed=[];real_summary=typed.summary
        def observe(name,**values):
            if name=='report_export_transport':observed.append(values)
            real_summary(name,**values)
        proof=[]
        for count in (1000,2000,4000,85979):
            rows=[{'values':[str(i//2),'W',None,True,i-1000,i/8,'',False,'é\n\\']} for i in range(count)]
            start=perf_counter()
            with transaction.atomic(),patch.object(typed,'summary',side_effect=observe):
                meta=typed.save_export(self.run,'reports/norm0-export/ReportRows',rows)
                loaded=typed.load_export(self.run,meta)
                if count>10000:self.assertIsInstance(loaded,RecordRows)
                self.assertEqual(digest(list(loaded)),digest(rows))
                self.assertEqual(meta['digest'],digest(rows))
                row_stats,cell_stats=observed[-2:]
                self.assertEqual(row_stats['records'],count)
                self.assertEqual(cell_stats['records'],count*9)
                self.assertEqual(row_stats['statements'],(count+499)//500)
                self.assertEqual(cell_stats['statements'],(count*9+499)//500)
                for stats in (row_stats,cell_stats):
                    self.assertLessEqual(stats['max_chunk_records'],500)
                    self.assertLessEqual(stats['max_chunk_estimated_bytes'],1024*1024)
                proof.append(dict(rows=count,cells=count*9,seconds=perf_counter()-start,
                    row_transport=row_stats,cell_transport=cell_stats))
                transaction.set_rollback(True)
            self.assertEqual(self.populations(),(0,0))
        print('EXPORT_COPY_SCALE_PASS '+json.dumps(proof,sort_keys=True))

    def test_real_guard_denials_mixed_chunks_seal_and_late_failure_rollback(self):
        from django.db import connection,transaction,DatabaseError
        from django.utils import timezone
        from mta.runtime import relational_state as typed
        from mta.runtime.models import CalculationRun
        from mta.serialization import digest
        path='reports/norm0-export/ReportRows'
        self.owner('')
        with self.assertRaisesRegex(DatabaseError,'owning append generation'),transaction.atomic():
            typed.save_export(self.run,path,[{'values':[1]}])
        self.assertEqual(self.populations(),(0,0));self.owner(str(self.run.pk))
        foreign=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
            execution_revision='report-export-foreign-component-only',input_digest='a'*64,input_payload={},
            status='SUCCEEDED',production_manifest=self.run.production_manifest,production_digest='d'*64)
        for owner,image in ((foreign.pk,path),(self.run.pk,'reports/unadmitted/ReportRows')):
            with self.assertRaisesRegex(DatabaseError,'owner/path differs'),transaction.atomic():
                typed._save_export_records('report_export_row',typed.EXPORT_ROW_COLUMNS,
                    [(self.run.pk,path,0,0),(owner,image,1,0)])
            self.assertEqual(self.populations(),(0,0))
        # The second cell COPY fails after the first 500 cells succeeded.
        # Save_export shares its caller's outer transaction, including lengths.
        bad=[{'values':[i]} for i in range(501)];bad[-1]['values']=[2**63]
        with self.assertRaises(DatabaseError),transaction.atomic():
            typed.save_export(self.run,path,bad)
        self.assertEqual(self.populations(),(0,0))
        good=typed.save_export(self.run,path,[{'values':[None,1]}])
        self.generation.metadata={'component':True};self.generation.digest=digest(self.generation.metadata)
        self.generation.status='READY';self.generation.sealed_at=timezone.now()
        self.generation.save(update_fields=['metadata','digest','status','sealed_at'])
        with self.assertRaisesRegex(DatabaseError,'absent, drifted or sealed'),transaction.atomic():
            typed._save_export_records('report_export_row',typed.EXPORT_ROW_COLUMNS,[(self.run.pk,path,2,0)])
        with self.assertRaisesRegex(DatabaseError,'owning append generation'),transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('UPDATE mta_state.report_export_cell SET integer_value=2 WHERE vf_run_id=%s',[self.run.pk])
        self.assertEqual(list(typed.iter_export(self.run,good)),[{'values':[None,1]}])
        print('EXPORT_COPY_GUARDS_PASS missing-owner/mixed-foreign-owner/path/sealed-append/update/late-COPY-full-rollback')
