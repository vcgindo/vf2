"""Post-DBM record contracts, native values and ordered bag access paths."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'post-dbm-contract-only')
import django
django.setup()

from copy import deepcopy
from datetime import date, datetime
from unittest.mock import patch
import unittest

from mta.row_sequences import RecordRows
from mta.serialization import digest, storage
from mta.application import daily_transit, operational_bor, operational_capture, production_rrr
from mta.presentation import production_reports, daily_transit as transit_storage
from mta.mdm import master_owners
from mta.runtime import mdm_models
from mta.application.row_bag_lookup import AsciiBagLookup
from mta.domain.complete_daily_scalars import ascii_equal
from tests.test_operational_bor import bor_row, rrr_row, requirement, rationed
from tests import test_production_rrr as rrr_fixture
from tests import test_daily_transit as transit_fixture
from tests.test_operational_capture import calculated


class PostDbmContracts(unittest.TestCase):
    def test_source_recipe_binds_new_lookup_and_norm_rrr_dependencies(self):
        import inspect
        from mta.application import row_bag_lookup
        from mta.presentation import daily_rrr_colour
        original=inspect.getsource
        before=production_reports.recipe_digest()
        for module in (row_bag_lookup,daily_rrr_colour):
            with self.subTest(module=module.__name__),patch.object(inspect,'getsource',
                    side_effect=lambda value: original(value)+'\n# changed dependency' if value is module else original(value)):
                self.assertNotEqual(production_reports.recipe_digest(),before)

    def test_transit_actual_spools_keep_nulls_negative_quantities_and_duplicate_joins(self):
        fixture=transit_fixture.DailyTransitTests()
        raw=[fixture.raw(), fixture.raw(InTransitQty=-3), fixture.raw(SKUCode=None)]
        standards=[dict(SKUCode='A', WhCode='L1', SLT=2), dict(SKUCode='A', WhCode='L1', SLT=None)]
        expected=daily_transit.validate_goods_in_transit(raw, standards, date(2026,6,6), datetime(2026,6,6))
        actual=daily_transit.validate_goods_in_transit(RecordRows.from_rows(raw),
            RecordRows.from_rows(standards),date(2026,6,6),datetime(2026,6,6))
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual['rows']),4)
        self.assertEqual([r['InTransitQty'] for r in actual['rows']], [5,5,-3,-3])
        self.assertEqual(transit_storage._decoded(RecordRows.from_rows([]), daily_transit.RAW_FIELDS), [])

    def test_large_predecessor_histories_keep_exact_cutoffs_order_and_duplicates(self):
        for make, writer, current_key in ((bor_row,operational_bor.collect_bor_order_allocation_history,'current_bor'),
                                         (rrr_row,operational_bor.collect_rrr_order_allocation_history,'current_rrr')):
            opening=[dict(make(),ReportDate='2026-06-05') for _ in range(10001)]
            opening.extend([dict(make(),ReportDate='2026-03-08'),dict(make(),ReportDate='2026-06-06')])
            args=dict(opening_history=opening,business_date='2026-06-06',horizon=90,**{current_key:[make()]})
            expected=writer(**args)
            actual=writer(**dict(args,opening_history=RecordRows.from_rows(opening)))
            self.assertEqual(actual,expected)
            self.assertEqual(len(actual),10002)
            self.assertEqual(actual[-1]['ReportDate'],'2026-06-06')
            self.assertTrue(all(r['ReportDate']=='2026-06-05' for r in actual[:-1]))

    def test_live_capabilities_keep_list_contract_and_supplier_projection_accepts_spools(self):
        rows=rrr_fixture.ProductionRrrTests().inputs()
        expected=production_rrr.produce(**rows)
        self.assertTrue(expected)
        with self.assertRaises(ValueError):
            production_rrr.produce(**{k:RecordRows.from_rows(v) for k,v in rows.items()})
        value=[dict(SKUCode='S', WHCode='W', SupplierCode='P', SOB=100.0)]*2
        self.assertEqual(production_reports._project({'SOBData':RecordRows.from_rows(value)},
            'SOBData',operational_bor.SOB_FIELDS),value)
        source=calculated()
        expected=operational_capture.capture_rows(source)
        for item in source:item['rows']=RecordRows.from_rows(item['rows'])
        with self.assertRaises(ValueError):operational_capture.capture_rows(source)

    def test_master_projection_closed_protocol_and_scalar_validation_remain_strict(self):
        from mta.runtime.mdm_models import MdmSkuDescription
        fields=master_owners.business_fields(MdmSkuDescription)
        row={f.name:None if f.null else 'S' for f in fields}
        expected=master_owners.typed(MdmSkuDescription,[row,row],strict=True)
        self.assertEqual(len(expected),2)
        with self.assertRaises(ValueError):master_owners.typed(MdmSkuDescription,RecordRows.from_rows([row,row]),strict=True)
        for bad in (None, tuple([row]), iter([row])):
            with self.assertRaises(ValueError):master_owners.typed(MdmSkuDescription,bad)
        with self.assertRaises(ValueError):master_owners.typed(MdmSkuDescription,[dict(row,Unexpected=1)])

    def test_post_commit_master_projection_adapts_only_selected_spools(self):
        from mta.mdm import daily_current, location_projection
        from tests.test_h3_daily_integration import frame, coupled
        source=frame()
        output,_=coupled(source['profile'],deepcopy(source['opening']['state']),'2037-04-09','2037-04-10')
        closing=output['ClosingState'][0]
        expected=daily_current._partition_identity(daily_current.closing_owners(closing,version=location_projection.VERSION))
        copy=deepcopy(closing)
        for section in ('importer','dbm','btr','consumer_context'):
            for name, rows in copy[section].items():
                if isinstance(rows,list) and all(isinstance(row,dict) and
                        all(not isinstance(value,(dict,list,tuple,RecordRows)) for value in row.values()) for row in rows):
                    copy[section][name]=RecordRows.from_rows(rows)
        class Unrelated(dict):
            def items(self):raise AssertionError('Unrelated histories traversed')
        copy['unrelated']=Unrelated()
        actual=daily_current.closing_owners(copy,version=location_projection.VERSION)
        self.assertEqual(daily_current._partition_identity(actual),expected)
        self.assertIsInstance(copy['importer']['MasterData'],RecordRows)

    def test_ordered_lookup_keeps_case_space_null_duplicates_and_fallback(self):
        rows=[dict(SKU='s ',WH='W',N=1),dict(SKU='S',WH='w ',N=2),dict(SKU=None,WH='W',N=3)]
        index=AsciiBagLookup(rows,('SKU','WH'),ascii_equal)
        self.assertEqual([r['N'] for r in index.candidates(dict(SKU='S',WH='w'),('SKU','WH'))],[1,2])
        self.assertEqual(list(index.candidates(dict(SKU=None,WH='W'),('SKU','WH'))),[])
        index.add(dict(SKU='S',WH='W',N=4))
        self.assertEqual([r['N'] for r in index.candidates(dict(SKU='S',WH='W'),('SKU','WH'))],[1,2,4])
        self.assertIs(AsciiBagLookup(rows,('SKU','WH'),lambda a,b:a==b).candidates(rows[0],('SKU','WH')),rows)
        invalid=rows+[dict(SKU='é',WH='W',N=5)]
        self.assertIs(AsciiBagLookup(invalid,('SKU','WH'),ascii_equal).candidates(rows[0],('SKU','WH')),invalid)

    def test_bor_fast_path_preserves_full_values_and_linear_candidate_work(self):
        from mta.application import operational_bor as bor
        counts=[]
        for n in (50,100):
            args=dict(bpr_master=[dict(SKUCode=str(i),WHCode='W',ParentWhCode='P') for i in range(n)],
                sob_data=[dict(SKUCode=str(i),WHCode='W',SupplierCode='P',SOB=100.0) for i in range(n)],
                moq_data=[],requirements=[requirement(SKUCode=str(i)) for i in range(n)],
                rationed_report=[rationed(SKUCode=str(i)) for i in range(n)],bpr_table=[],equal=ascii_equal)
            before=digest(args | {'equal':'ascii_equal'})
            with patch.object(bor,'_join',wraps=bor._join) as join:
                rows=bor.collect_bor_order_allocation(**args);counts.append(join.call_count)
            self.assertEqual(len(rows),n)
            self.assertEqual(rows,[bor_row(SKUCode=str(i),DispatchQty=15,Dispatch_ToBlue=5) for i in range(n)])
            self.assertEqual(digest(args | {'equal':'ascii_equal'}),before)
        self.assertEqual(counts[1],2*counts[0])

    def test_bor_index_and_original_scan_agree_on_duplicate_null_and_ambiguous_bags(self):
        for change in ('duplicates','null','ambiguous'):
            args=dict(bpr_master=[dict(SKUCode='S',WHCode='W',ParentWhCode='P')],
                sob_data=[dict(SKUCode='s ',WHCode='w ',SupplierCode='p ',SOB=100.0)],moq_data=[],
                requirements=[requirement()],rationed_report=[rationed()],bpr_table=[])
            if change=='duplicates':args['requirements']*=2;args['rationed_report']*=2
            elif change=='null':args['requirements'][0]['NormReqBlack']=None
            else:args['requirements'].append(requirement(OrderReqBlack=2))
            def outcome(equal):
                try:return storage(operational_bor.collect_bor_order_allocation(**args,equal=equal))
                except ValueError as error:return type(error).__name__,str(error)
            with self.subTest(change=change):
                self.assertEqual(outcome(ascii_equal),outcome(lambda a,b:ascii_equal(a,b)))
