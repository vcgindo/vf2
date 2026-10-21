"""Full supplier/production and BTR bags, native errors, file-backed histories.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import patch
from mta.application import complete_daily_inputs as supplier
from mta.domain import complete_daily_bpr as production, btr_finalization as btr
from mta.domain.complete_daily_scalars import ascii_equal
from mta.row_sequences import RecordRows
from tests.stage_values import capture_stages

TODAY = date(2026, 6, 6)


def supplier_case(n=1):
    sourcing = [dict(sku_code=str(i), location_code='W', supplier='P') for i in range(n)]
    bor = [dict(case='r1_bor_'+str(i+1), sku=str(i), location='W', supplier='P',
                original_requirement='12', dispatch_requirement='12', to_red='2', to_yellow='3',
                to_green='7', to_blue='0') for i in range(n)]
    masters = [dict(SKUCode=str(i), WHCode='W', ParentWhCode='P') for i in range(n)]
    attrs = [dict(SKUCode=str(i), LocCode='W', **{f'c{j}':None for j in range(1, 16)}) for i in range(n)]
    return dict(sourcing=sourcing, bor=bor, bpr_master=masters, sku_loc_attributes=attrs, equal=ascii_equal)


def production_case(n=1):
    return dict(supplier_dispatch_req=[dict(SKUCode=str(i), WHCode='W', SupplierCode='P'+str(i),
                    ReqTopOfRed=3, ReqTopOfYellow=4, ReqTopOfGreen=5) for i in range(n)],
        plants=[dict(PlantCode='P'+str(i)) for i in range(n)],
        rationed_req_report=[dict(SKUCode=str(i), WhCode='W', Norm=10, Stock=None, GIT=0) for i in range(n)],
        daily_consumption=[dict(SKUCode=str(i), WHCode='P'+str(i), ReportDate='2026-06-06', Stock=4, GIT=1) for i in range(n)],
        last_batch_run=[dict(LastRunDate='2026-06-06')], prod_order_suggestions=[dict(old=1)],
        intermediate_tables={name:[] for name in ('TempProductionOrderReq','TempConsolidatedProdOrderReq','PlantStock')},
        equal=ascii_equal, sort_key=lambda value:value.upper())


def category_case(n=1, depth=3):
    state = dict(BTRSnapshotForUI=[dict(SKUCode=str(i), WhCode='W', TodayColorDispatch='Green',
        AgeDispatch=0, TodayColorPhysicalInv='White', AgePhysicalInv=4) for i in range(n)], BufferTrendPhysicalInv=[])
    facts = dict(SKULocStandardAttributes=[dict(SKUCode=str(i), WhCode='W', Category=None) for i in range(n)],
        MasterData=[dict(SKUCode=str(i), WhCode='W', RLT=2) for i in range(n)],
        DailyConsumption=[dict(SKUCode=str(i), WhCode='W', ReportDate='2026-06-05', Consumption=0)
                          for i in range(n) for _ in range(depth)], GoodsInTransitTransporterMaster=[], Suggestions=[])
    return TODAY, state, facts, dict(up={1}, down={5})


def norm_case(n=1, depth=3, wide=False):
    count = 1 if wide else n
    facts = dict(DBMMaster=[dict(SKUCode=str(i), WhCode='W') for i in range(count)],
        Suggestions=[dict(SKUCode='0' if wide else str(i), WhCode='W', Type=1) for i in range(n)],
        SuggestionsLog=[dict(SKUCode='0' if wide else str(i), WhCode='W', Type=1,
             SuggestionDate='2026-06-04', NewNorm=10) for i in range(n) for _ in range(depth)],
        SuspendHistory=[], NormChangeLogTbl=[])
    return TODAY, {}, facts, dict(up={1}, down={5})


class SupplierBtrScanTests(unittest.TestCase):
    def test_supplier_all_28_fields_duplicate_ordinals_left_join_and_sql_keys(self):
        args = supplier_case();args['bpr_master'] *= 2;args['sku_loc_attributes'] *= 2
        args['bpr_master'][1] = dict(args['bpr_master'][1], SKUCode='0 ', WHCode='w ')
        before = deepcopy(args)
        rows, lineage = supplier.supplier_dispatch(**args)
        expected = dict(SKUCode='0', WHCode='W', SupplierCode='P', OriginalReq=12, DispatchReq=12,
            ReqTopOfRed=2, ReqTopOfYellow=3, ReqTopOfGreen=7, ReqTopOfBlue=0,
            **{f'SKULocAtt{i:02}':None for i in range(1,16)}, CumulativeTOR=2, CumulativeTOY=5,
            CumulativeTOG=12, CumulativeTOB=12)
        self.assertEqual(rows, [expected]*4)
        self.assertEqual(lineage, [dict(output_ordinal=i, calculated_ordinal=0, sourcing_ordinal=0,
            bpr_master_ordinal=i//2, attribute_ordinal=i%2, case='r1_bor_1') for i in range(4)])
        self.assertEqual(args, before)
        args['sku_loc_attributes'] = []
        self.assertEqual([r['attribute_ordinal'] for r in supplier.supplier_dispatch(**args)[1]], [None,None])
        args['bpr_master'].append(dict(SKUCode='0',WHCode='P',ParentWhCode=None))
        self.assertEqual(supplier.supplier_dispatch(**args), ([], []))

    def test_supplier_null_short_circuit_unused_invalid_keys_and_overflow(self):
        args = supplier_case();args['bpr_master'].append(dict(SKUCode=None,WHCode='Q'))
        self.assertEqual(len(supplier.supplier_dispatch(**args)[0]), 1)
        args['bor'][0]['to_red'] = '2147483647'
        with self.assertRaisesRegex(ValueError,'overflows'):supplier.supplier_dispatch(**args)
        args = supplier_case();args['equal'] = lambda a,b:a==b
        self.assertEqual(len(supplier.supplier_dispatch(**args)[0]), 1)

    def test_missing_join_fields_preserve_empty_and_short_circuit_errors(self):
        args=supplier_case();del args['bpr_master'][0]['ParentWhCode']
        with self.assertRaisesRegex(KeyError,'ParentWhCode'):supplier.supplier_dispatch(**args)
        args['bpr_master'][0]['SKUCode']=None
        self.assertEqual(supplier.supplier_dispatch(**args),( [], []))
        args=production_case();del args['supplier_dispatch_req'][0]['SupplierCode']
        with self.assertRaisesRegex(KeyError,'SupplierCode'):production.production_order_suggestions(**args)
        args['plants']=[]
        self.assertEqual(production.production_order_suggestions(**args)['ProdOrderSuggestions'],[])

    def test_production_full_stages_duplicate_joins_and_scalar_conflicts(self):
        args = production_case();before=deepcopy(args)
        stages = dict(capture_stages(production.production_suggestion_stages(**args)))
        self.assertEqual(stages['insert-production-req']['IntermediateTables']['TempProductionOrderReq'],
            [dict(SKUCode='0',WHCode='W',PlantCode='P0',Norm=10,Stock=None,GIT=0,Red=3,Yellow=4,Green=5)])
        expected = dict(SKUCode='0',PlantCode='P0',Red=0,Yellow=2,Green=5,TotalReq=7,EcoColor='Yellow',ReportDate='2026-06-06')
        self.assertEqual(stages['insert-suggestions']['ProdOrderSuggestions'], [expected])
        self.assertEqual(args,before)
        args['plants'] *= 2;args['rationed_req_report'] *= 2
        self.assertEqual(production.production_order_suggestions(**args)['ProdOrderSuggestions'],
            [dict(expected,Red=7,Yellow=16,Green=20,TotalReq=43,EcoColor='Red')])
        args['daily_consumption'].append(dict(args['daily_consumption'][0],Stock=7))
        with self.assertRaisesRegex(ValueError,'SOURCE_ORDER_AMBIGUITY: production plant stock'):
            production.production_order_suggestions(**args)

    def test_production_group_spelling_overflow_and_error_order(self):
        args=production_case();args['supplier_dispatch_req'] *= 2
        args['supplier_dispatch_req'][1]=dict(args['supplier_dispatch_req'][1],SKUCode='0 ')
        with self.assertRaisesRegex(ValueError,'grouped production key representative'):
            production.production_order_suggestions(**args)
        args=production_case();args['supplier_dispatch_req'][0]['ReqTopOfRed']=2**31
        with self.assertRaisesRegex(ValueError,'ARITHMETIC_OVERFLOW'):
            production.production_order_suggestions(**args)

    def test_btr_full_histories_nulls_duplicates_dates_and_source_nonmutation(self):
        args=category_case(2);before=deepcopy(args)
        self.assertEqual(btr._categories(*args)['SKULocStandardAttributes'],
            [dict(SKUCode=str(i),WhCode='W',Category='5') for i in range(2)])
        self.assertEqual(args,before)
        args[2]['DailyConsumption'][0]['Consumption']=None
        self.assertEqual(btr._categories(*args)['SKULocStandardAttributes'][0]['Category'],None)
        args[2]['DailyConsumption'][0]['ReportDate']='bad'
        with self.assertRaises(ValueError):btr._categories(*args)
        args[2]['DailyConsumption'][0]['SKUCode']='unmatched'
        self.assertEqual(btr._categories(*args)['SKULocStandardAttributes'][0]['Category'],'5')
        args=norm_case(2);before=deepcopy(args)
        expected=[dict(SKUCode=str(i),WhCode='W',SuggestionType=1,Suggestion='Increase',
            SuggestionGenerationAge=2,SuggestionDate='2026-06-04') for i in range(2)]
        self.assertEqual(btr._norm_suggestions(*args)['DBMNormSuggestionsData'],expected)
        self.assertEqual(args,before)
        args[2]['SuggestionsLog'].append(dict(args[2]['SuggestionsLog'][0],NewNorm=20))
        with self.assertRaisesRegex(ValueError,'tied SuggestionsLog order'):btr._norm_suggestions(*args)

    def test_actual_file_backed_histories_and_many_key_scaling(self):
        for n in (40,80,160):
            args=supplier_case(n)
            for key in ('bpr_master','sku_loc_attributes'):args[key]=RecordRows.from_rows(args[key])
            with patch.object(supplier,'_join',wraps=supplier._join) as residual:
                self.assertEqual(len(supplier.supplier_dispatch(**args)[0]),n)
                self.assertEqual(residual.call_count,2*n)
            args=production_case(n)
            for key in ('plants','rationed_req_report','daily_consumption'):args[key]=RecordRows.from_rows(args[key])
            with patch.object(production,'_match',wraps=production._match) as residual:
                self.assertEqual(len(production.production_order_suggestions(**args)['ProdOrderSuggestions']),n)
                self.assertEqual(residual.call_count,4*n)
            args=category_case(n)
            args[2]['DailyConsumption']=RecordRows.from_rows(args[2]['DailyConsumption'])
            self.assertTrue(all(row['Category']=='5' for row in btr._categories(*args)['SKULocStandardAttributes']))
            args=norm_case(n);args[2]['SuggestionsLog']=RecordRows.from_rows(args[2]['SuggestionsLog'])
            self.assertEqual(len(btr._norm_suggestions(*args)['DBMNormSuggestionsData']),n)


if __name__ == '__main__':unittest.main()
