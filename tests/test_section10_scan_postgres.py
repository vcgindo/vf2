"""Small positive producer SQL round trips, separate from the native day proof.

These rollback-only component runs are never accepted business openings/days.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from datetime import date
import os
import unittest


@unittest.skipUnless(os.environ.get('VF_SECTION10_POSTGRES_PROOF')=='1','Owned Section10 PostgreSQL proof required')
class ScanProducerPostgresTests(unittest.TestCase):
    def test_nonempty_changed_families_exact_typed_roundtrips_and_rollback(self):
        from django.db import connection,transaction
        from mta.runtime.models import CalculationRun
        from mta.runtime import relational_state as typed
        from mta.serialization import digest,storage
        from tests.test_dbm_report_scan_indexes import cases as report_cases
        from tests.test_dbm_state_scan_indexes import DbmStateScanIndexTests as State
        from tests.test_supplier_btr_scan_indexes import supplier_case,production_case,category_case,norm_case
        from mta.application import complete_daily_inputs as supplier
        from mta.domain import (complete_daily_bpr as production,btr_finalization as btr,
            dbm_ingestion,dbm_suspensions,dbm_norm1_advisory)
        from mta.row_sequences import RecordRows
        self.assertEqual(connection.settings_dict['NAME'],'vf_section9_fifth_proof_20261021')
        today=date(2026,6,6)
        components=[]
        for label,module,function,args in report_cases(2):
            value=function(*args)
            table={'D4-discard':'DiscardedSuggestions','D4-report':'SuggestionsLog',
                'D6':'DBMDelistingOfNormsWithHits','D7':'PhaseOutRecommendation',
                'D8-data':'Norm0Norm1Norm2Report','D8-detail':'Norm0_1_2ReportDetails',
                'D9':'NormAcceptanceTbl'}.get(label)
            if label=='D4-discard':
                args[1]['Suggestions'][0]['NewNorm']=2
                value=function(*args)
            if table:components.append((label,'closing/dbm/'+table,value[table]))
            else:
                self.assertEqual(len(value['ReportRows']),2)
                print('SECTION10_D10_FULL_REPORT_VALUES_PASS '+digest(value['ReportRows']))
        rows=[dict(SKUCode='S',WhCode='W')]*2
        components.extend([
            ('D1','closing/dbm/SuspendCustomSKUTbl',dbm_ingestion.import_exclusions(rows,RecordRows.from_rows(rows))),
            ('D2','closing/dbm/SuspendNewSKUTbl',dbm_suspensions.suspend_introductions(today,State.introduction_state(streamed=True))['SuspendNewSKUTbl']),
            ('D3-forced','closing/dbm/SuspendNormsForceChangedTbl',dbm_suspensions.apply_forced_norm_stock(today,State.forced_state(streamed=True))['SuspendNormsForceChangedTbl']),
            ('D3-accepted-create','closing/dbm/SuspendAcceptedNormsStockType',dbm_suspensions.suspend_accepted_norm_stock(today,State.accepted_state(streamed=True))['SuspendAcceptedNormsStockType']),
            ('D3-accepted-update','closing/dbm/SuspendAcceptedNormsStockType',dbm_suspensions.apply_accepted_norm_stock(today,State.accepted_state(streamed=True))['SuspendAcceptedNormsStockType']),
            ('D5','closing/dbm/Norm1IncreaseSuggestions',dbm_norm1_advisory.norm1_advisory(today,State.advisory_state(streamed=True))['Norm1IncreaseSuggestions']),
            ('S1-S3','closing/complete/SupplierDispatchReq',supplier.supplier_dispatch(**supplier_case(2))[0]),
            ('S4','closing/complete/ProdOrderSuggestions',production.production_order_suggestions(**production_case(2))['ProdOrderSuggestions']),
            ('B1','closing/btr/SKULocStandardAttributes',btr._categories(*category_case(2))['SKULocStandardAttributes']),
            ('B2','closing/btr/DBMNormSuggestionsData',btr._norm_suggestions(*norm_case(2))['DBMNormSuggestionsData'])])
        count=CalculationRun.objects.count()
        for label,path,rows in components:
            rows=list(rows);self.assertTrue(rows,label+' must be positive')
            with transaction.atomic():
                run=CalculationRun.objects.create(kind='COMPONENT_PROOF',business_date=today,
                    execution_revision='section10-scan-rollback-'+label,input_digest=digest(rows),
                    input_payload={},status='RUNNING')
                meta=typed.save_image(run,path,path,RecordRows.from_rows(rows))
                self.assertEqual(typed.load_image(run,meta),storage(rows),label)
                self.assertEqual(meta['count'],len(rows))
                self.assertEqual(meta['digest'],digest(rows))
                print('SECTION10_TYPED_PRODUCER_PASS '+label+' rows='+str(len(rows))+' digest='+meta['digest'])
                transaction.set_rollback(True)
            self.assertFalse(CalculationRun.objects.filter(pk=run.pk).exists())
        self.assertEqual(CalculationRun.objects.count(),count)
        print('SECTION10_ALL_CHANGED_FAMILIES_TYPED_ROUNDTRIP_PASS component headers and rows rolled back; accepted native day unchanged')


if __name__=='__main__':unittest.main()
