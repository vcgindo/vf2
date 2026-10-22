"""Affected two-function SQL/migration proof on the existing owned component DB."""
import json
import os
import random
import unittest
from importlib import import_module
from time import perf_counter
from uuid import uuid4
from django.db import connection,transaction,DatabaseError
from mta.serialization import digest

migration=import_module('mta.runtime.migrations.0168_report_guard_owner_sets')


@unittest.skipUnless(os.environ.get('VF_REPORT_GUARD_PROOF')=='1','Explicit existing-owned guard proof required')
class ReportGuardOwnerSetsPostgresTests(unittest.TestCase):
    def setUp(self):
        from mta.runtime.models import CalculationRun,DailyReportGeneration
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        with connection.cursor() as c:
            c.execute("SELECT oid,shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(c.fetchone(),(1598463,'owned terminal SMALL takeover thread01a16058 20261022; not working/serving'))
        self.before=CalculationRun.objects.count()
        self.atomic=transaction.atomic();self.atomic.__enter__();self.addCleanup(self.rollback)
        rng=random.Random(168)
        manifest=dict(version=3,reports=[dict(stage='norm0-export',deferred={})],padding=''.join(rng.choices('abcdef0123456789',k=134952)))
        self.run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
            execution_revision='report-guard-component-only',input_digest='a'*64,input_payload={},
            status='SUCCEEDED',production_manifest=manifest,production_digest='b'*64)
        self.report=DailyReportGeneration.objects.create(run=self.run,source_digest='b'*64,recipe_digest='c'*64)
        with connection.cursor() as c:c.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(self.run.pk)])

    def rollback(self):
        from mta.runtime.models import CalculationRun
        transaction.set_rollback(True);self.atomic.__exit__(None,None,None)
        self.assertEqual(CalculationRun.objects.count(),self.before)

    def epochs(self):
        with connection.cursor() as c:
            c.execute('SELECT initialization_id,master_epoch,configuration_epoch,fact_epoch,operational_epoch,action_epoch FROM mta.fresh_mta_ingestionrevisionstate ORDER BY initialization_id')
            return c.fetchall()

    def generation(self,run=None,version=1):
        from mta.runtime.models import BtrReportingGeneration
        run=run or self.run
        return BtrReportingGeneration.objects.create(run=run,version=version,source_digest=digest(str(uuid4())),
            source_kind=run.kind,business_date=run.business_date)

    def test_baseline_candidate_owner_verdicts_revision_effects_and_exact_reverse(self):
        from mta.runtime.models import CalculationRun,BtrJoinReference
        from release.advance_ingestion import catalogue,catalogue_delta
        with connection.cursor() as c:
            # The runner migrated forward normally. Reverse and forward are
            # tested inside this rollback-only transaction, including exact
            # predecessor rejection and unchanged function identity/ACL.
            c.execute(migration.REVERSE);baseline_catalogue=catalogue(c)
            c.execute(migration.FORWARD);candidate_catalogue=catalogue(c)
            delta=catalogue_delta(baseline_catalogue,candidate_catalogue)
            self.assertEqual(set(delta),{'functions:mta.ingestion_watch()','functions:mta.guard_v3_derived_report_rows()'})
            for change in delta.values():
                self.assertEqual({k:v for k,v in change['before'].items() if k!='body'},
                                 {k:v for k,v in change['after'].items() if k!='body'})
            if os.environ.get('VF_REPORT_GUARD_DELTA'):
                from pathlib import Path
                Path(os.environ['VF_REPORT_GUARD_DELTA']).write_text(json.dumps(delta,indent=2))
            with self.assertRaisesRegex(DatabaseError,'Exact predecessor report guard required'),transaction.atomic():
                c.execute(migration.FORWARD)
            c.execute('CREATE TEMP TABLE guard_probe(run_id uuid,generation_id uuid,vf_run_id uuid,vf_image text) ON COMMIT DROP')
        valid=self.generation()
        v2=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',execution_revision='guard-v2',input_digest='a'*64,input_payload={},status='SUCCEEDED',production_manifest={'version':2})
        v2gen=self.generation(v2)
        bad=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',execution_revision='guard-running',input_digest='a'*64,input_payload={},status='RUNNING',production_manifest={'version':3})
        invalid=self.generation(bad)
        samples=[[],[(self.run.pk,valid.pk,self.run.pk,'reports/norm0-export/ReportRows')],
            [(v2.pk,v2gen.pk,v2.pk,'reports/norm0-export/ReportRows')],
            [(bad.pk,invalid.pk,bad.pk,'reports/norm0-export/ReportRows')],
            [(None,None,None,None)],[(uuid4(),uuid4(),uuid4(),'foreign')],
            [(self.run.pk,valid.pk,self.run.pk,'foreign')],
            [(self.run.pk,valid.pk,self.run.pk,'reports/norm0-export/ReportRows'),(None,None,None,None)],
            [(self.run.pk,valid.pk,self.run.pk,'closing/btr/BufferTrendReport')]]
        paths=[('run_id','','N.run_id','LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.run_id','TRUE'),
            ('generation_id','LEFT JOIN mta.fresh_mta_btrreportinggeneration P ON P.id=N.generation_id','P.run_id',
             'LEFT JOIN mta.fresh_mta_btrreportinggeneration P ON P.id=N.generation_id LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=P.run_id','TRUE'),
            ('vf_run_id,vf_image','','N.vf_run_id','LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.vf_run_id',"N.vf_image='closing/btr/BufferTrendReport'"),
            ('vf_run_id,vf_image','','N.vf_run_id','LEFT JOIN mta.fresh_mta_calculationrun R ON R.id=N.vf_run_id',"EXISTS(SELECT 1 FROM jsonb_array_elements(R.production_manifest->'reports') S WHERE S ? 'deferred' AND N.vf_image IN ('reports/'||(S->>'stage')||'/ReportHeader','reports/'||(S->>'stage')||'/ReportRows'))")]
        verdicts=0
        with connection.cursor() as c:
            for rows in samples:
                c.execute('DELETE FROM guard_probe')
                if rows:c.executemany('INSERT INTO guard_probe VALUES(%s,%s,%s,%s)',rows+rows)
                for keys,parent,resolve,join,path in paths:
                    old='SELECT NOT EXISTS(SELECT 1 FROM guard_probe N '+join+" WHERE R.id IS NULL OR R.kind<>'DAILY_CHAIN' OR R.status<>'SUCCEEDED' OR R.production_manifest->>'version' IS DISTINCT FROM '3' OR NOT ("+path+'))'
                    c.execute(old);expected=c.fetchone()[0]
                    c.execute(migration._query(parent,path,keys,resolve).replace('{changes}','guard_probe'));self.assertEqual(c.fetchone()[0],expected);verdicts+=1
                    if 'generation_id' not in keys:
                        for qualify in (False,True):
                            old=('SELECT NOT EXISTS(SELECT 1 FROM guard_probe N '+join+" WHERE R.id IS DISTINCT FROM %s OR R.status<>'SUCCEEDED' OR NOT ("+path+'))') if qualify else ('SELECT EXISTS(SELECT 1 FROM guard_probe N '+join+" WHERE R.production_manifest->>'version'='3' AND ("+path+'))')
                            c.execute(old,[self.run.pk] if qualify else None);expected=c.fetchone()[0]
                            query=migration._query(parent,path,keys,resolve,derived=True,qualified=qualify).replace('{changes}','guard_probe').replace('$1','%s')
                            c.execute(query,[self.run.pk] if qualify else None);self.assertEqual(c.fetchone()[0],expected);verdicts+=1
        effects=[]
        # Compare actual trigger verdicts AND revision deltas on valid native
        # versus old-v2 child writes, including old/new UPDATE classification.
        for label,sql in (('baseline',migration.REVERSE),('candidate',None)):
            with transaction.atomic():
                if sql:
                    with connection.cursor() as c:c.execute(sql)
                before=self.epochs();ref=BtrJoinReference.objects.create(generation=valid,branch='tech',export=False,a_ordinal=0)
                self.assertEqual(self.epochs(),before)
                BtrJoinReference.objects.filter(pk=ref.pk).update(a_ordinal=1);self.assertEqual(self.epochs(),before)
                BtrJoinReference.objects.filter(pk=ref.pk).update(a_ordinal=1);self.assertEqual(self.epochs(),before)
                BtrJoinReference.objects.filter(pk=ref.pk).update(generation=v2gen)
                after=self.epochs();effects.append([(b[0],*[y-x for x,y in zip(b[1:],a[1:])]) for b,a in zip(before,after)])
                self.assertTrue(all(e[-2]==1 for e in effects[-1]))
                transaction.set_rollback(True)
        self.assertEqual(effects[0],effects[1])
        print('REPORT_GUARD_EQUIVALENCE_PASS '+json.dumps(dict(verdicts=verdicts,revision_effects_equal=True,delta_keys=sorted(delta))))

    def test_large_btr_live_triggers_display_summary_and_guard_denials(self):
        from mta.runtime.models import BtrJoinReference,BtrPresentationRow
        from mta.runtime.planning_summary_models import PlanningSummaryReceipt,PlanningSummaryContribution
        ref=self.generation();display=self.generation(version=2)
        before=self.epochs()
        query="INSERT INTO mta.fresh_mta_btrjoinreference (generation_id,branch,export,a_ordinal) SELECT %s,'tech',false,I FROM generate_series(0,97096) I"
        started=perf_counter()
        with connection.cursor() as c:
            c.execute("SET LOCAL statement_timeout='60s'")
            c.execute('SELECT octet_length(production_manifest::text),pg_column_size(production_manifest) FROM mta.fresh_mta_calculationrun WHERE id=%s',[self.run.pk]);manifest=c.fetchone()
            self.assertGreaterEqual(manifest[0],135000)
            c.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+query,[ref.pk]);plan=c.fetchone()[0]
        seconds=perf_counter()-started;self.assertLess(seconds,60)
        self.assertEqual(BtrJoinReference.objects.filter(generation=ref).count(),97097)
        self.assertEqual(list(BtrJoinReference.objects.filter(generation=ref).order_by('a_ordinal').values_list('a_ordinal',flat=True)),list(range(97097)))
        self.assertEqual(self.epochs(),before)
        # Exercise the wide display-row shape under its actual row guards,
        # using ordinary model defaults plus explicit text/array values.
        values={}
        for f in BtrPresentationRow._meta.concrete_fields:
            if f.name in ('id','generation','branch','a_ordinal'):continue
            if f.null:values[f.attname]=None
            elif f.get_internal_type()=='TextField':values[f.attname]=''
            elif f.get_internal_type()=='ArrayField':values[f.attname]=[]
        BtrPresentationRow.objects.bulk_create([BtrPresentationRow(generation=display,branch='tech',a_ordinal=i,**values) for i in range(128)])
        receipt=PlanningSummaryReceipt.objects.create(run=self.run,source_digest='d'*64,generation_digest='e'*64,recipe_digest='f'*64,business_date=self.run.business_date)
        with connection.cursor() as c:c.execute("SELECT set_config('fresh.planning_summary_build',%s,true)",[str(receipt.pk)])
        PlanningSummaryContribution.objects.bulk_create([PlanningSummaryContribution(receipt=receipt,ordinal=i,metric='git_parent',product_key='SKU',location_key='W',equality_profile='raw',occurrence_count=1) for i in range(128)])
        self.assertEqual(self.epochs(),before)
        from mta.runtime import relational_state as typed
        meta=typed.save_export(self.run,'reports/norm0-export/ReportRows',[{'values':[None,1,False]},{'values':[]}])
        self.assertEqual(list(typed.iter_export(self.run,meta)),[{'values':[None,1,False]},{'values':[]}])
        self.assertEqual(self.epochs(),before)
        with self.assertRaisesRegex(DatabaseError,'owner/path differs'),transaction.atomic():
            typed._save_export_records('report_export_row',typed.EXPORT_ROW_COLUMNS,[(self.run.pk,'reports/foreign/ReportRows',0,0),(self.run.pk,'reports/norm0-export/ReportRows',2,0)])
        with self.assertRaisesRegex(DatabaseError,'owning append generation'),transaction.atomic():
            with connection.cursor() as c:c.execute('UPDATE mta_state.report_export_row SET column_count=column_count+1 WHERE vf_run_id=%s',[self.run.pk])
        proof=dict(reference_rows=97097,display_rows=128,summary_contributions=128,manifest_bytes=manifest,insert_seconds=seconds,actual_insert_plan_and_triggers=plan,revision_epochs_unchanged=True)
        if os.environ.get('VF_REPORT_GUARD_LARGE'):
            from pathlib import Path
            Path(os.environ['VF_REPORT_GUARD_LARGE']).write_text(json.dumps(proof,indent=2))
        print('REPORT_GUARD_LARGE_PASS '+json.dumps(proof,sort_keys=True))
