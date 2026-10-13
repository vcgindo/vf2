"""Enabled module intake and literal missing-data branches, no business day."""
from copy import deepcopy
import os
import unittest
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','daily-modules-unit-only')
import django
django.setup()
from mta.application.r1_daily_input import process_daily_validation,FLAGS,DAILY_COLUMNS,STAGES
from mta.application.r1_daily_entry import native_auxiliary_stock_balances

TODAY='2026-01-15';PRIOR='2026-01-14'


def row(wh,**overrides):
    return dict(SKUCode='S',WhCode=wh,Stock=5,Consumption=2,GIT=3,Receipts=1,PSO=0,ReportDate=TODAY,**overrides)


def fixture(mode=1):
    pairs=[dict(SKUCode='S',WhCode=w) for w in ('W','W2','D','V','X')]
    master={'tables':dict(MasterData=pairs,RejectedMaster=[],
        SiteDescriptionTbl=[dict(WHCode=w,WHDescription=w) for w in ('W','W2','D','V','X')])}
    prior=dict(BPRMaster=[],Plants=[],NoNormMaster=[],DailyConsumption=[
        dict(SKUCode='S',WHCode='W',Stock=42,Consumption=0,GIT=0,Receipts=0,PSO=0,BlueZone=0,ReportDate=PRIOR)],
        opening_provenance=dict(kind='SYNTHETIC_PRIOR_BPR_DAILY',identity='own-module-boundary',business_date=PRIOR))
    value=dict(schema='r1-daily-input-v1',raw_daily_data=[row(w) for w in ('W','W2','D','V','X')],
        prior_bpr=prior,settings=[dict(Parameter='MissingDailyDataHandling',Value=str(mode))],vf_settings=[],
        shell_flags=dict.fromkeys(FLAGS,1),distributor_codes=['D'],vendor_codes=['V'],vector_dms_codes=['X'],
        module_sources=dict(distributor_norms=[dict(SKUCode='S',WhCode='D')],vendor_master=[dict(SKUCode='S',WhCode='V')]))
    return value,master


def run(value,master):
    return process_daily_validation(value,master,TODAY,TODAY+'T00:00:00')[STAGES[-1]]['tables']


class DailyModuleTests(unittest.TestCase):
    def test_native_auxiliary_stock_uses_actual_nonmaster_daily_owner_and_attribute_rule(self):
        daily=[dict(SKUCode='S',WHCode='ROOT',Stock=11,ReportDate=TODAY)]
        attrs=[dict(SKUCode='S',LocCode='ROOT',StockPercentForRationing=25)]
        for kind,reserved,rationing in ((0,'0','11'),(1,'8','3'),(2,'0','11')):
            actual=native_auxiliary_stock_balances(daily,[],attrs,TODAY,kind)
            self.assertEqual(actual,(dict(sku_code='S',location_code='ROOT',stock_for_requirement='11',
                stock_for_rationing=rationing,reserved_stock=reserved),))
        self.assertEqual(len(native_auxiliary_stock_balances(daily*2,[],attrs,TODAY,1)),2)
        for rows,attributes in (([daily[0],dict(daily[0],Stock=12)],attrs),
            (daily,[attrs[0],dict(attrs[0],StockPercentForRationing=50)]),
            ([dict(daily[0],Stock=None)],attrs)):
            with self.assertRaises(ValueError):native_auxiliary_stock_balances(rows,[],attributes,TODAY,1)
        for stock,percent in ((2**31-1,0),(0,-2**31),(2**31-1,99)):
            rows=[dict(daily[0],Stock=stock)];attributes=[dict(attrs[0],StockPercentForRationing=percent)]
            if percent==99:
                self.assertEqual(native_auxiliary_stock_balances(rows,[],attributes,TODAY,1)[0]['reserved_stock'],str((2**31-1)//100))
            else:
                with self.assertRaisesRegex(ValueError,'intermediate overflow'):
                    native_auxiliary_stock_balances(rows,[],attributes,TODAY,1)

    def test_native_connected_calculation_keeps_positive_nonmaster_module_stock_without_master_seed(self):
        from tests.test_production_order_identity import payload,state,calculate
        from mta.application.r1_input import calculation_order_rows
        from mta.planning.engine import calculate_current_day
        raw=payload([]);raw.pop('order_input');closing=calculate(state(),[])
        raw['schema']='r1-current-day-input-v3'
        raw['stock_configuration']=dict(reservation_type=0,reservation_for_rationing_only=True)
        raw['orders']=calculation_order_rows(closing)
        fact=dict(SKUCode='R1SKU',WHCode='MODULE',Stock=31,ReportDate=TODAY)
        output=calculate_current_day(raw,defer_pick=True,_owned_order_closing=closing,
            _owned_daily_stock=dict(daily_consumption=[fact],attributes=[]))
        self.assertIn(dict(sku_code='R1SKU',location_code='MODULE',stock_for_requirement='31',
            stock_for_rationing='31',reserved_stock='0'),output['r1_stock_balance'])
        self.assertFalse(any(r['location_code']=='MODULE' for r in output['r1_additional_master']))

    def test_all_three_enabled_use_actual_master_join_and_preserve_complete_values(self):
        value,master=fixture();before=deepcopy((value,master))
        result=run(value,master)
        expected=[row(w) for w in ('W','W2','D','V','X')]
        self.assertEqual(sorted(result['DailyDataProcessed'],key=lambda r:r['WhCode']),sorted(expected,key=lambda r:r['WhCode']))
        self.assertEqual(result['RejectedMaster'],[])
        self.assertEqual((value,master),before)

    def test_active_module_null_stock_is_never_carried_or_zero_substituted(self):
        for mode in (1,2,3):
            value,master=fixture(mode)
            for raw in value['raw_daily_data']:
                if raw['WhCode'] in ('D','V','X'):raw['Stock']=None
            rows=run(value,master)['DailyDataProcessed']
            self.assertEqual({r['WhCode'] for r in rows},{'W','W2'})

    def test_modes_carry_only_own_yesterday_and_zero_only_nonmodule_targets(self):
        for mode,expected in ((1,None),(2,0),(3,42)):
            value,master=fixture(mode);value['raw_daily_data']=[r for r in value['raw_daily_data'] if r['WhCode']!='W']
            rows=run(value,master)['DailyDataProcessed']
            self.assertEqual({r['WhCode']:r['Stock'] for r in rows}.get('W'),expected)
            self.assertTrue({'D','V','X'}<={r['WhCode'] for r in rows})

    def test_module_only_data_cannot_authorize_normal_carry_or_zero(self):
        for mode in (2,3):
            value,master=fixture(mode);value['raw_daily_data']=[r for r in value['raw_daily_data'] if r['WhCode'] in ('D','V','X')]
            result=run(value,master)
            self.assertEqual({r['WhCode'] for r in result['DailyDataProcessed']},{'D','V','X'})
            self.assertEqual([r['ReasonCode'] for r in result['RejectedMaster']],[13])

    def test_distributor_dms_duplicate_rejection_removes_entire_union_subset(self):
        value,master=fixture();value['raw_daily_data'].append(dict(row('D'),Stock=8))
        result=run(value,master)
        self.assertEqual([r['ReasonCode'] for r in result['RejectedMaster']],[14])
        self.assertEqual({r['WhCode'] for r in result['DailyDataProcessed']},{'W','W2','V'})

    def test_vendor_directory_join_multiplicity_is_not_silently_deduplicated(self):
        value,master=fixture();value['vendor_codes']*=2
        result=run(value,master)
        self.assertEqual([r['ReasonCode'] for r in result['RejectedMaster']],[15])
        self.assertNotIn('V',{r['WhCode'] for r in result['DailyDataProcessed']})

    def test_non_distributor_rejection_retains_source_asymmetric_dms_rule(self):
        value,master=fixture();value['raw_daily_data'].append(dict(row('W'),Stock=8))
        result=run(value,master)
        self.assertEqual([r['ReasonCode'] for r in result['RejectedMaster']],[6])
        self.assertEqual({r['WhCode'] for r in result['DailyDataProcessed']},{'D'})
        self.assertIn('Non-Distributor/Non-Vendor',result['RejectedMaster'][0]['ReasonDescription'])

    def test_join_bags_and_enabled_empty_or_ineligible_pairs_are_preserved(self):
        value,master=fixture();value['module_sources']['distributor_norms']*=2;value['vector_dms_codes']*=2
        rows=run(value,master)['DailyDataProcessed']
        self.assertEqual([r for r in rows if r['WhCode']=='D'],[row('D'),row('D')])
        self.assertEqual([r for r in rows if r['WhCode']=='X'],[row('X'),row('X')])
        value,master=fixture();value['module_sources']['distributor_norms']=[dict(SKUCode='OTHER',WhCode='D')]
        self.assertNotIn('D',{r['WhCode'] for r in run(value,master)['DailyDataProcessed']})

    def test_inactive_explicit_projection_preserves_selected_behavior(self):
        value,master=fixture();value['shell_flags']=dict.fromkeys(FLAGS,0)
        source=deepcopy(value);del source['module_sources']
        self.assertEqual(run(source,master),run(value,master))

    def test_enabled_source_presence_and_flag_types_deny_before_mutation(self):
        for change in ('missing','flag','shape'):
            value,master=fixture()
            if change=='missing':del value['module_sources']
            elif change=='flag':value['shell_flags'][FLAGS[0]]=True
            else:value['module_sources']['vendor_master'][0]['Qty']=5
            before=deepcopy(value)
            with self.assertRaises(ValueError):run(value,master)
            self.assertEqual(value,before)

    def test_native_initialization_and_capture_keep_explicit_typed_module_owners(self):
        from tests.production_daily_fixture import initialized_input,SKU,CHILD
        from tests.initialization_input_fixture import encoded
        from mta.mdm.initialization_contract import decode
        from mta.runtime.production_preflight import initialization
        from mta.runtime.production_daily import input_table
        from mta.runtime.input_storage import Rows
        from mta.mdm.initialization_rows import select
        value=initialized_input();value['configuration']['daily'].update(shell_flags=dict.fromkeys(FLAGS,1),
            module_sources=dict(distributor_norms=[dict(SKUCode=SKU,WhCode=CHILD)],vendor_master=[]))
        raw,sha,args=encoded(value);frame=decode(raw,sha,**args)[1]
        self.assertEqual(frame['profile']['daily']['module_sources'],value['configuration']['daily']['module_sources'])
        report=initialization(raw,sha,**args)
        self.assertTrue(report['stage_eligibility']['installation'],report['issues'])
        self.assertFalse(report['production_ready'])
        self.assertFalse(any(r['code']=='MODULE_UNSUPPORTED' for r in report['issues']))
        for name in ('distributor_norms','vendor_master'):
            path='input/profile/daily/module_sources/'+name+'/values'
            rows=frame['profile']['daily']['module_sources'][name]
            self.assertEqual(input_table(rows[0] if rows else (),path,rows),'Intermediate/SKULoc_DailyData')
        settings=[dict(Parameter='CaptureDispatchExecutionEfficiency',Value='1',Description='typed owner')]
        sequence=Rows(1,lambda:iter(settings))
        self.assertEqual(select(settings[0],'input/profile/delivery/btr_history/importer_vf_settings/values',sequence),'Importer/VFSettings')


if __name__=='__main__':unittest.main()
