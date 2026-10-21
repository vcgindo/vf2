"""Independent canonical expression/assignment witnesses, not a large replay.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from decimal import Decimal
import os
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','section9-unit-only-no-serving')
import django
django.setup()

from mta.domain.r1_requirement_bands import RequirementBandInput,calculate_requirement_bands,_stored_threshold
from mta.application.operational_bor import _int
from mta.row_sequences import RecordRows
from mta.temporal.chain import native_rows


def band(location='C',parent='P',norm='10',stock='0',pso='4',threshold='33.00'):
    return RequirementBandInput(sku_code='A',location_code=location,parent_location_code=parent,
        norm=Decimal(norm),stock=Decimal(stock),goods_in_transit=Decimal(0),pso=Decimal(pso),
        pso_threshold_percent=Decimal(threshold),due_direct_spike=Decimal(0),due_routed_spike=Decimal(0))


class Section9ArithmeticTests(unittest.TestCase):
    def test_canonical_ceiling_precedes_black_band_and_real_native_source(self):
        from mta.application.production_order_sources import produce
        native={}
        value=calculate_requirement_bands((band(),),reference_parent_keys=frozenset({('A','P')}),source_rows=native)[0]
        self.assertEqual((value['rel_pso'],value['norm_black_band'],value['norm_req_black']),('1','5','5'))
        self.assertEqual(native[('A','C')]['RelPSO'],'1')
        for field,value in native[('A','C')].items():
            if field not in ('SKUCode','WhCode','ParentWhCode'):_int(value)
        calculated={name:[] for name in ('r1_order_route','r1_order_bpp','r1_advance_stock_allocation',
            'r1_git_advance_allocation','r1_stock_balance')}
        calculated['r1_order_allocation_bands']=list(native.values())
        self.assertEqual(produce(today='2026-04-08',calculated=calculated,orders=[],dbm_master=[],
            attributes=[],daily_consumption=[]),[])

    def test_zero_equal_below_integral_fractional_and_zero_norm(self):
        for norm,pso,pct,expected in [('10','0','33','0'),('100','33','33','0'),('10','3','33','0'),
                ('10','4','30','1'),('10','4','33','1'),('0','4','66.67','4')]:
            with self.subTest(norm=norm,pso=pso,pct=pct):
                row=calculate_requirement_bands((band(norm=norm,pso=pso,threshold=pct),),
                    reference_parent_keys=frozenset({('A','P')}))[0]
                self.assertEqual(Decimal(row['rel_pso']),Decimal(expected))

    def test_fractional_pso_generated_bands_reach_positive_native_parent_allocation(self):
        from mta.application.production_order_sources import produce
        native={}
        calculate_requirement_bands((band(),),reference_parent_keys=frozenset({('A','P')}),source_rows=native)
        calculated=dict(r1_order_route=[dict(order_key=1,order_id='O1',child_location_code='C',
            location_code='P',due_date='2026-04-08')],r1_order_bpp=[dict(order_key=1,order_id='O1',
            sku_code='A',source_location_code='P',destination_location_code='C',bpp='100',colour='black')],
            r1_advance_stock_allocation=[],r1_git_advance_allocation=[],
            r1_stock_balance=[dict(sku_code='A',location_code='C',stock_for_rationing='0'),
                dict(sku_code='A',location_code='P',stock_for_rationing='20')],
            r1_order_allocation_bands=list(native.values()))
        orders=[dict(SKUCode='A',WhCode='C',OrderKey=1,DueDate='2026-04-08',Qty=4,
            CustomerOrderId='O1',IsSpike=1,CustomerExpectedDate=None)]
        actual=produce(today='2026-04-08',calculated=calculated,orders=orders,
            dbm_master=[dict(SKUCode='A',WhCode='C',ParentWhCode='P',Norm=10,RLT=1)],
            attributes=[dict(SKUCode='A',LocCode='P',PackSize=1)],
            daily_consumption=[dict(SKUCode='A',WHCode='C',Stock=0,GIT=0,ReportDate='2026-04-08'),
                dict(SKUCode='A',WHCode='P',Stock=20,GIT=0,ReportDate='2026-04-08')])
        self.assertEqual(actual,[dict(SKUCode='A',DestWhCode='C',SrcWhCode='P',OrderKey=1,
            DueDate='2026-04-08',CustomerOrderId='O1',IsSpike=1,Qty=4,OrderWiseAllocatedQty=4,
            BPP=Decimal('100.00'),OrderColor='Black',DueDateAtDest=None,PackSizeWiseAllocatedQty=4)])

    def test_threshold_assignment_before_child_cnr_netoff(self):
        rows=(band('P',None,'3',pso='0',threshold='33.33'),
              band('C','P','3',stock='1',pso='0',threshold='0'))
        before=deepcopy(rows)
        values={r['location_code']:r for r in calculate_requirement_bands(rows)}
        self.assertEqual(values['C']['norm_req_green'],'1')
        self.assertEqual(values['P']['rel_cnr_green'],'0')
        self.assertEqual(values['P']['norm_green_band'],'1')
        self.assertEqual(rows,before)

    def test_decimal13_3_half_up_edges_maximum_and_rounding_overflow(self):
        for raw,expected in [('0.9999','1.000'),('0.0004','0.000'),('0.0005','0.001'),
                ('0.0006','0.001'),('1.234','1.234'),('0','0.000'),
                ('9999999999.9994','9999999999.999')]:
            self.assertEqual(str(_stored_threshold(Decimal(raw))),expected)
        for raw in ('9999999999.9995','10000000000'):
            with self.assertRaisesRegex(ValueError,'decimal\\(13,3\\)'):_stored_threshold(Decimal(raw))

    def test_all_four_sequential_cnr_colours_high_override_not_capped(self):
        # Two child rows independently yield Green11, Yellow11, Red9, Black1.
        for remaining,expected in [('0',(11,11,9,1)),('11.5',(0,11,9,1)),
                ('22.5',(0,0,9,1)),('31.5',(0,0,0,1)),('32.5',(0,0,0,0))]:
            with self.subTest(remaining=remaining):
                rows=(band('P',None,'1',pso='0',threshold=str(Decimal(remaining)*100)),
                    band('C1','P','3',pso='0',threshold='0'),
                    band('C2','P','30',stock='1',pso='0',threshold='0'))
                parent=next(r for r in calculate_requirement_bands(rows) if r['location_code']=='P')
                self.assertEqual(tuple(int(parent['rel_cnr_'+c]) for c in ('green','yellow','red','black')),expected)

    def test_native_int_input_and_relevant_pso_overflow(self):
        for kwargs in ({'norm':'2147483648'},{'pso':'2147483648'}):
            with self.assertRaisesRegex(ValueError,'native SQL int'):
                calculate_requirement_bands((band(**kwargs),),reference_parent_keys=frozenset({('A','P')}))

    def test_alias_is_exact_required_fields_nullable_and_immutable(self):
        rows=[dict(SKUCode='A',WhCode='C',NewNorm=None)]
        before=deepcopy(rows)
        for source in (rows,RecordRows.from_rows(rows)):
            self.assertEqual(native_rows(source,('SKUCode','WHCode','NewNorm')),
                [dict(SKUCode='A',WHCode='C',NewNorm=None)])
            for missing in ('OldNorm','NormChangeDate','NormChangeReason'):
                with self.assertRaisesRegex(ValueError,'Missing native control field '+missing):
                    native_rows(source,('SKUCode','WHCode',missing))
        self.assertEqual(rows,before)
        self.assertEqual(native_rows([],('SKUCode','WHCode')),[])
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            native_rows([dict(WhCode='C',WHCode='D')],('WHCode',))
        self.assertEqual(native_rows([dict(WhCode='C',WHCode='C')],('WHCode',)),[{'WHCode':'C'}])


if __name__=='__main__':unittest.main()
