"""Daily graph SQL qualification; no engine execution or accepted-day creation."""
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_DAILY_GRAPH_SELECTIVE_PROOF')=='1',
                     'Explicit owned graph PostgreSQL proof required')
class DailyGraphSelectivePostgresTests(unittest.TestCase):
    def test_native_and_large_graph_values_raw_keys_dates_scopes_and_null_failure(self):
        from django.db import connection,transaction
        from django.test import override_settings
        from mta.runtime.models import CalculationRun
        from mta.runtime import relational_state as typed,temporal
        from mta.presentation import dbm_read,daily_history
        from mta.presentation.selective import image_rows
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        with connection.cursor() as cursor:
            cursor.execute("SELECT oid,shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(cursor.fetchone(),(1598463,'owned terminal SMALL takeover thread01a16058 20261022; not working/serving'))
        count=CalculationRun.objects.count();observed=[]

        def compare(run,pair,*,expect_failure=False):
            with patch.object(dbm_read,'selected_run',return_value=run), \
                    patch.object(dbm_read.hierarchy,'selected_manifest',return_value=None):
                broad=dbm_read.dbm_context(history=True)
                with patch.object(dbm_read,'_selected_rows',wraps=dbm_read._selected_rows) as queries:
                    narrow=dbm_read.dbm_context(history=True,pair=pair)
                if expect_failure:
                    for context in (broad,narrow):
                        with self.assertRaises(TypeError):daily_history.daily_graph(context.dbm,*pair)
                else:
                    expected=daily_history.daily_graph(broad.dbm,*pair)
                    actual=daily_history.daily_graph(narrow.dbm,*pair)
                    self.assertEqual(actual,expected);self.assertEqual(digest(actual),digest(expected))
                for name,field,value in (('SkuAttributeData','SKUCode',pair[0]),
                                         ('LocationAttributeData','WHCode',pair[1])):
                    self.assertEqual(narrow.output['ClosingState'][0]['importer'][name],
                        [r for r in broad.output['ClosingState'][0]['importer'][name] if r[field]==value])
                for name,rows in narrow.dbm.items():
                    if name in ('LastBatchRunTbl','ReasonCodes'):continue
                    self.assertTrue(all(dbm_read_row_key(r)==pair for r in rows))
                observed.append(dict(kind=run.kind,pair=pair,
                    transferred={k:len(v) for k,v in narrow.dbm.items()},selected_queries=len(queries.call_args_list),
                    expected_failure=expect_failure))
                return broad,narrow

        def dbm_read_row_key(row):
            return row['SKUCode'],row.get('WhCode',row.get('WHCode',row.get('LocCode')))

        with override_settings(VF_MTA_DAILY_PUBLICATION=True),transaction.atomic(), \
                patch.object(temporal,'execute_day',side_effect=AssertionError('No daily execution')), \
                patch.object(temporal,'calculate_day',side_effect=AssertionError('No calculation')):
            native=CalculationRun.objects.get(pk='331a821a-853e-49c0-8f61-42c90fc6b1ce',status='SUCCEEDED')
            masters=image_rows(native,'closing/dbm/DBMMaster')
            self.assertTrue(masters)
            native_before=digest(native.production_manifest)
            for row in masters[:2]:compare(native,dbm_read_row_key(row))
            # Explicit rollback-only component inputs. The header is not a
            # native accepted run and has no capture, attempt or opening.
            run=CalculationRun.objects.create(kind='COMPONENT_PROOF',business_date='2037-05-01',
                execution_revision='daily-graph-selective-component',input_digest='a'*64,
                input_payload={},status='RUNNING')
            pair={'SKUCode':'SKU','WhCode':'W'}
            daily=dict(pair,ReportDate='2037-04-10',Stock=1,GIT=2,Consumption=3,Receipts=4,BlueZone=None)
            suspend=dict(pair,ReportDate='2037-04-10',RedReasonStockType=1,GreenReasonStockType=2,
                RedReasonConsumptionType=3,GreenReasonConsumptionType=4)
            unrelated=[dict(daily,SKUCode='other'+str(i)) for i in range(10001)]
            change=dict(SKUCode='SKU',WHCode='W',NormChangeDate='2037-04-10',OldNorm=1,NewNorm=2,NormChangeReason=1)
            suggestion=dict(pair,SuggestionDate='2037-04-10',OldNorm=1,NewNorm=2,Type=999)
            states=dict(LastBatchRunTbl=[{'LastRunDate':'2037-04-10T00:00:00'}],
                DailyConsumption=unrelated+[daily,deepcopy(daily),dict(daily,ReportDate='2037-04-09'),
                    dict(daily,ReportDate='2037-01-09'),dict(daily,SKUCode='sku'),dict(daily,WhCode='W ')],
                SuspendHistory=[suspend,deepcopy(suspend),deepcopy(suspend),
                    dict(suspend,ReportDate='2037-04-08'),dict(suspend,ReportDate='2037-01-09')],
                NormChangeLogTbl=[change,dict(change,NormChangeDate='2020-01-01'),
                    dict(change,NormChangeReason=999)],
                SuggestionsLog=[suggestion,dict(suggestion,SuggestionDate='2037-01-09')],
                DBMMaster=[dict(pair,Norm=5,MinNorm=1,RLT=2,RCP=3,GCP=4,ParentWhCode='PARENT')],
                SuspendStockType=[dict(pair,RedResumeDate=None,GreenResumeDate='2037-04-10')]*2,
                SuspendConsumptionType=[dict(pair,RedResumeDate='2037-04-09',GreenResumeDate=None)]*2,
                ReasonCodes=[{'Id':1,'Reason':'retained '},{'Id':1,'Reason':'duplicate '},{'Id':2,'Reason':None}])
            importer=dict(SkuAttributeData=[dict(SKUCode='SKU',SL1='P',SL2='L',SL3='Leaf')]*2+
                [dict(SKUCode='sku',SL1='P',SL2='L',SL3='Leaf')],
                LocationAttributeData=[dict(WHCode='W',LL1='L',LL2='L',LL3='Leaf'),
                    dict(WHCode='PARENT',LL1='L',LL2='L',LL3='Leaf'),
                    dict(WHCode='W ',LL1=None,LL2=None,LL3=None)])
            images={}
            for owner,tables in (('dbm',states),('importer',importer)):
                for name,rows in tables.items():
                    path='closing/'+owner+'/'+name
                    images[path]=typed.save_image(run,path,path,rows)
            run.production_manifest={'version':2,'images':images}
            broad,narrow=compare(run,('SKU','W'))
            self.assertGreater(len(broad.dbm['DailyConsumption']),10000)
            self.assertEqual(len(narrow.dbm['DailyConsumption']),3)
            self.assertEqual(len(narrow.dbm['NormChangeLogTbl']),3) # old history must remain
            graph=daily_history.daily_graph(narrow.dbm,'SKU','W')[0]
            self.assertEqual(len(graph['StockData']),8);self.assertEqual(len(graph['MonitoringData']),4)
            self.assertEqual(len(graph['NormChangeHistoryData']),4)
            self.assertEqual(graph['RunDate'],'2037-04-10T00:00:00')
            for pair_value in (('sku','W'),('SKU','W '),('missing','W')):compare(run,pair_value)
            # A selected NULL date must still fail, rather than vanish in SQL.
            with transaction.atomic():
                meta=images['closing/dbm/DailyConsumption']
                with connection.cursor() as cursor:
                    cursor.execute('UPDATE '+typed.table_sql(meta['table'])+' SET "ReportDate"=NULL '
                        'WHERE vf_run_id=%s AND vf_image=%s AND vf_ordinal=10001',[run.pk,meta['image']])
                # This is a declared invalid input component, with a matching
                # manifest digest so the projection failure itself is tested.
                invalid=[dict(r,ReportDate=None) if i==10001 else r for i,r in enumerate(states['DailyConsumption'])]
                meta['digest']=digest(invalid)
                compare(run,('SKU','W'),expect_failure=True)
                transaction.set_rollback(True)
            native.refresh_from_db();self.assertEqual(digest(native.production_manifest),native_before)
            self.assertFalse(run.checkpoints.exists());self.assertFalse(hasattr(run,'mdm_input_capture'))
            transaction.set_rollback(True)
        self.assertEqual(CalculationRun.objects.count(),count)
        print('DAILY_GRAPH_SELECTIVE_PASS '+json.dumps(observed,sort_keys=True))
