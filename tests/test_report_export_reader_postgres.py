"""Only export-reader qualification; existing owned component, rollback-only."""
import json
import os
import unittest
from time import perf_counter
from unittest.mock import patch
from tests import test_report_export_copy_postgres as fixture


@unittest.skipUnless(os.environ.get('VF_REPORT_EXPORT_READER_PROOF')=='1',
    'Explicit owned export-reader PostgreSQL proof required')
class ReportExportReaderPostgresTests(fixture.ReportExportCopyPostgresTests):
    # Do not inherit/repeat completed writer campaigns.
    test_exact_baseline_types_ragged_empty_duplicates_and_byte_bounds=None
    test_actual_large_representation_and_linear_transport_counts=None
    test_real_guard_denials_mixed_chunks_seal_and_late_failure_rollback=None

    def records(self,headers,cells,*,image='reports/norm0-export/ReportRows'):
        from mta.runtime import relational_state as typed
        typed._save_export_records('report_export_row',typed.EXPORT_ROW_COLUMNS,
            [(self.run.pk,image,*row) for row in headers])
        typed._save_export_records('report_export_cell',typed.EXPORT_CELL_COLUMNS,
            [(self.run.pk,image,*row) for row in cells])

    def test_affected_integrity_empty_ragged_foreign_types_digest_and_version1(self):
        from django.db import transaction,connection
        from mta.runtime import relational_state as typed
        from mta.runtime.models import CalculationRun,DailyReportGeneration
        from mta.serialization import digest,storage
        path='reports/norm0-export/ReportRows'
        null=lambda row,col:(row,col,'null',None,None,None,None)
        integer=lambda row,col,value:(row,col,'int',None,value,None,None)
        cases=[
            ('zero-valid',[],[],[],None),
            ('zero-orphan',[],[null(0,0)],[],'Orphan report cells'),
            ('negative-orphan',[(0,0)],[null(-1,0)],[{'values':[]}],'Orphan report cells'),
            ('upper-orphan',[(0,0)],[null(1,0)],[{'values':[]}],'Orphan report cells'),
            ('interior-header-missing',[(0,0),(2,0)],[null(1,0)],[{'values':[]}]*3,'Report row population drift'),
            ('first-header-missing',[(1,0)],[],[{'values':[]}]*2,'Report row population drift'),
            ('extra-header',[(0,0),(1,0)],[],[{'values':[]}],'Extra report rows'),
            ('missing-cell',[(0,1)],[],[{'values':[None]}],'Report cell population drift'),
            ('extra-cell',[(0,1)],[null(0,0),null(0,1)],[{'values':[None]}],'Extra report cells'),
            ('column-gap',[(0,1)],[null(0,1)],[{'values':[None]}],'Report cell population drift'),
            ('empty-row-has-cell',[(0,0)],[null(0,0)],[{'values':[]}],'Empty report row has cells'),
            ('null-type-conflict',[(0,1)],[(0,0,'null','wrong',None,None,None)],[{'values':[None]}],'Report cell typed columns conflict'),
            ('type-conflict',[(0,1)],[(0,0,'int','wrong',1,None,None)],[{'values':[1]}],'Report cell typed columns conflict'),
            ('value-digest',[(0,1)],[integer(0,0,2)],[{'values':[1]}],'Report projection drift'),
            ('all-empty',[(0,0),(1,0)],[],[{'values':[]},{'values':[]}],None),
            ('zero-extra-header',[(0,0)],[],[],'Extra report rows'),
            ('negative-header',[(-1,0),(0,0)],[],[{'values':[]}],'Report row population drift'),
            ('negative-column',[(0,1)],[null(0,-1)],[{'values':[None]}],'Report cell population drift'),
            ('unknown-tag',[(0,1)],[(0,0,'other',None,None,None,None)],[{'values':[None]}],'Report cell typed columns conflict'),
            ('missing-selected-str',[(0,1)],[(0,0,'str',None,None,None,None)],[{'values':[None]}],'Report cell typed columns conflict'),
            ('missing-selected-int',[(0,1)],[(0,0,'int',None,None,None,None)],[{'values':[None]}],'Report cell typed columns conflict'),
            ('missing-selected-float',[(0,1)],[(0,0,'float',None,None,None,None)],[{'values':[None]}],'Report cell typed columns conflict'),
            ('missing-selected-bool',[(0,1)],[(0,0,'bool',None,None,None,None)],[{'values':[None]}],'Report cell typed columns conflict'),
        ]
        passed=[]
        for name,headers,cells,expected,error in cases:
            with self.subTest(case=name),transaction.atomic():
                self.records(headers,cells)
                meta=dict(version=2,image=path,count=len(expected),digest=digest(expected))
                if error:
                    with self.assertRaisesRegex(ValueError,error):list(typed.iter_export(self.run,meta))
                else:self.assertEqual(list(typed.iter_export(self.run,meta)),expected)
                passed.append(name);transaction.set_rollback(True)
        rows=[{'values':[]},{'values':[None,'',True,False,0,-1,2**63-1,-(2**63),1.25,'Ã©æ¼¢å­—\n\t']},
              {'values':[None]},{'values':[None]},{'values':[]}]
        meta=typed.save_export(self.run,path,rows)
        # Foreign images/runs include ordinals that would fail an unscoped check.
        self.records([], [null(-5,0),null(999,0)],image='reports/norm0-export/ForeignRows')
        foreign=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
            execution_revision='reader-foreign-component-only',input_digest='a'*64,input_payload={},
            status='SUCCEEDED',production_manifest=self.run.production_manifest,production_digest='d'*64)
        DailyReportGeneration.objects.create(run=foreign,source_digest=foreign.production_digest,recipe_digest='c'*64)
        self.owner(str(foreign.pk))
        typed._save_export_records('report_export_cell',typed.EXPORT_CELL_COLUMNS,
            [(foreign.pk,path,-9,0,'null',None,None,None,None)])
        self.owner(str(self.run.pk))
        self.assertEqual(typed.load_export(self.run,meta),storage(rows))
        bad={**meta,'digest':'0'*64}
        with self.assertRaisesRegex(ValueError,'Report projection drift'):list(typed.iter_export(self.run,bad))
        # v1 remains its original cell-only protocol, no v2 header requirement.
        v1path='reports/norm0-export/LegacyRows'
        self.records([], [integer(1,0,7)],image=v1path)
        legacy=dict(version=1,image=v1path,count=2,lengths=[0,1],digest=digest([{'values':[]},{'values':[7]}]))
        self.assertEqual(typed.load_export(self.run,legacy),[{'values':[]},{'values':[7]}])
        print('EXPORT_READER_CASES_PASS '+json.dumps(dict(cases=passed,ragged_duplicates_null_types_digest=True,
            foreign_run_image_excluded=True,version1_unchanged=True)))

    def test_cursor_cleanup_on_full_read_error_and_explicit_early_close(self):
        from django.db import connection
        from mta.runtime import relational_state as typed
        path='reports/norm0-export/ReportRows'
        meta=typed.save_export(self.run,path,[{'values':[0,False,'',None]},{'values':[]}])
        original=connection.chunked_cursor;opened=[]
        def track():
            cursor=original();opened.append(cursor.cursor);return cursor
        with patch.object(connection,'chunked_cursor',side_effect=track):
            stream=typed.iter_export(self.run,meta)
            self.assertEqual(next(stream),{'values':[0,False,'',None]})
            self.assertFalse(opened[-1].closed)
            stream.close();self.assertTrue(opened[-1].closed)
            self.assertEqual(list(typed.iter_export(self.run,meta)),[{'values':[0,False,'',None]},{'values':[]}])
            self.assertTrue(opened[-1].closed)
            with self.assertRaisesRegex(ValueError,'Report projection drift'):
                list(typed.iter_export(self.run,{**meta,'digest':'0'*64}))
            self.assertTrue(opened[-1].closed)
            with self.assertRaisesRegex(ValueError,'Report row population drift'):
                list(typed.iter_export(self.run,{**meta,'count':3}))
            self.assertTrue(opened[-1].closed)
        names=[c.name for c in opened]
        with connection.cursor() as cursor:
            cursor.execute('SELECT name FROM pg_cursors WHERE name=ANY(%s)',[names])
            self.assertEqual(cursor.fetchall(),[])
        print('EXPORT_READER_CLEANUP_PASS full/error/early-close; no retained named cursors')

    def test_observed_new_transaction_rows_stale_estimates_full_values_and_reiteration(self):
        from django.db import connection
        from mta.runtime import relational_state as typed
        from mta.serialization import digest
        from mta.row_sequences import RecordRows
        path='reports/norm0-export/ReportRows'
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('statement_timeout')")
            timeout=cursor.fetchone()[0];self.assertIn(timeout,('5min','300s'))
            cursor.execute("SELECT c.relname,c.reltuples,c.relpages FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='mta_state' AND c.relname IN ('report_export_row','report_export_cell') ORDER BY c.relname")
            estimates=cursor.fetchall()
            self.assertTrue(all(row[1]<1000 for row in estimates),estimates)
        rows=[{'values':[str(i//2),'W',None,True,i-1000,i/8,'',False,'Ã©\n\\']} for i in range(85979)]
        meta=typed.save_export(self.run,path,rows)
        self.records([],[( -3,0,'null',None,None,None,None)],image='reports/norm0-export/ForeignRows')
        from pathlib import Path
        import time
        gate=Path(os.environ['VF_REPORT_EXPORT_READER_GATE'])
        def gate_write(value):
            temporary=gate.with_suffix('.pending');temporary.write_text(json.dumps(value));temporary.replace(gate)
        gate_body=dict(start_epoch=time.time(),deadline_epoch=time.time()+300,complete=False,
            phase='three-full-reader-traversals-and-actual-named-cursor-plan',run=str(self.run.pk))
        gate_write(gate_body)
        start=perf_counter();statement_count=0;captured=[];passes=[]
        def observe(execute,sql,params,many,context):
            nonlocal statement_count
            statement_count+=1
            self.assertNotIn('JOIN',sql.upper());self.assertNotIn('MIN(',sql.upper())
            self.assertIn('UNION ALL',sql.upper())
            named=context['cursor'].cursor
            self.assertIsNotNone(named.name)
            captured.append(dict(sql=sql,params=params,name=named.name,
                scrollable=named.scrollable,withhold=named.withhold))
            return execute(sql,params,many,context)
        with connection.execute_wrapper(observe):
            pass_start=perf_counter()
            loaded=typed.load_export(self.run,meta);self.assertIsInstance(loaded,RecordRows)
            passes.append(perf_counter()-pass_start)
            for turn in range(2):
                pass_start=perf_counter();count=0
                for count,(actual,expected) in enumerate(zip(loaded,rows,strict=True),1):
                    self.assertEqual(actual,expected)
                    self.assertEqual([type(v) for v in actual['values']],[type(v) for v in expected['values']])
                self.assertEqual(count,85979);passes.append(perf_counter()-pass_start)
        self.assertEqual(statement_count,3);self.assertEqual(len(captured),3)
        self.assertTrue(all(not c['withhold'] and c['scrollable']==False for c in captured))
        reader_seconds=perf_counter()-start
        # EXPLAIN the actual named-cursor statement, not a plain SELECT with
        # another startup-cost policy. This required plan capture also runs
        # within the observer's aggregate gate; no statistics/planner changes.
        with connection.cursor() as cursor:
            cursor.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) DECLARE export_reader_plan NO SCROLL CURSOR WITHOUT HOLD FOR '+captured[0]['sql'],captured[0]['params'])
            plan=cursor.fetchone()[0]
            cursor.execute('SELECT name FROM pg_cursors WHERE name=ANY(%s)',[[c['name'] for c in captured]])
            self.assertEqual(cursor.fetchall(),[])
        seconds=perf_counter()-start
        def nodes(node):
            yield node
            for child in node.get('Plans',[]):yield from nodes(child)
        self.assertTrue(all('Join' not in node['Node Type'] for node in nodes(plan[0]['Plan'])))
        self.assertEqual(plan[0]['Plan']['Actual Rows'],859790)
        self.assertEqual(meta['digest'],digest(rows));self.assertLess(seconds,300)
        gate_write({**gate_body,'complete':True,'seconds':seconds,'passes_seconds':passes})
        proof=dict(rows=85979,cells=773811,tagged_records=859790,timeout=timeout,estimates_before=estimates,
            loaded_named_cursor_plan=plan,reader_seconds=reader_seconds,aggregate_gate_seconds=seconds,
            reader_passes=3,passes_seconds=passes,statement_count=statement_count,
            captured_named_cursors=[{k:v for k,v in c.items() if k not in ('sql','params')} for c in captured],
            complete_ordered_values_types_digest=True,reiterable=True,new_uncommitted_rows=True,
            analyze_or_statistics_mutation=False,foreign_image_excluded=True,named_cursors_closed=True)
        if os.environ.get('VF_REPORT_EXPORT_READER_OUTPUT'):
            Path(os.environ['VF_REPORT_EXPORT_READER_OUTPUT']).write_text(json.dumps(proof,indent=2))
        print('EXPORT_READER_OBSERVED_PASS '+json.dumps(proof,sort_keys=True))
