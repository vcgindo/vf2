"""Persisted-row ownership at the native daily entry; no database or daily run.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import unittest

from mta.row_sequences import RecordRows
from mta.temporal.chain import entry_inputs


def typed(value):
    if isinstance(value,dict):
        return [(key,typed(item)) for key,item in value.items()]
    if isinstance(value,(list,RecordRows)):
        return ['rows',[typed(item) for item in value]]
    if isinstance(value,tuple):
        return ['tuple',[typed(item) for item in value]]
    return [type(value).__name__,repr(value)]


def persisted_input(raw,*,large_configuration=False):
    """Use the real typed writer/reader, exercising every flat-row branch.

    Paths are the complete >10,000-row flat populations in the retained native
    capture and referenced initialization manifests, including BATCH inputs.
    Small fixture rows exercise those same branches without duplicating facts.
    Bounded metadata (for example ScriptExecutedFlag) remains a mutable list.
    """
    from types import SimpleNamespace
    from mta.runtime import input_storage
    from mta.serialization import digest
    from tests.test_input_storage_v3 import MemoryImages, run_identity, table
    owner=SimpleNamespace(pk='2cbe5b35-68cc-4aad-a06e-dbb968311f1c',
        input_digest=digest(raw),kind='DAILY_CHAIN')
    images=MemoryImages()
    owner.input_payload=input_storage.save_input(owner,raw,version=3,
        image_writer=images.write,table_selector=table,identity_resolver=run_identity)
    owner.input_manifest_digest=digest(owner.input_payload)
    result=input_storage.read_input(owner,image_reader=images.read,identity_resolver=run_identity)
    paths=set('''profile/calculation/logistics/items profile/calculation/policies
        profile/calculation/stock_openings opening/state/bpr/BPRMaster
        opening/state/btr/SKULocStandardAttributes opening/state/consumer_context/NMSAllItems
        opening/state/controls/dbm_master opening/state/controls/importer_master
        opening/state/controls/suspend_order_type opening/state/dbm/DBMMaster
        opening/state/dbm/SKULocStandardAttributes opening/state/dbm/SkuLocAttributeData
        opening/state/dbm/SuspendConsumptionType opening/state/dbm/SuspendOrderType
        opening/state/dbm/SuspendStockType opening/state/importer/MasterData
        opening/state/importer/SkuLocAttributeData opening/state/orders/SpikeOrderData
        day/raw_master day/raw_daily day/order_feed mdm_input/rows/skuloc/attributes'''.split())
    if large_configuration:
        paths.update('''profile/calculation/skus profile/calculation/locations
            profile/calculation/replenishment_exclusions profile/calculation/logistics/vehicles
            profile/calculation/logistics/location_vehicles'''.split())
    def immutable(value,path=''):
        if isinstance(value,dict):return {k:immutable(v,path+'/'+k if path else k) for k,v in value.items()}
        if not isinstance(value,list):return value
        if path in paths:
            assert all(isinstance(row,dict) and not list(input_storage.leaves(
                input_storage.shape(row),'list')) for row in value)
            return RecordRows(len(value),lambda:(deepcopy(row) for row in value))
        return [immutable(row,path+'/'+str(i)) for i,row in enumerate(value)]
    return immutable(result)


class EntryRowOwnershipTests(unittest.TestCase):
    def test_active_native_entry_with_spooled_external_master_and_daily_feeds(self):
        self.check_active_native_entry()

    def test_nonempty_current_suspensions_keep_full_persisted_shape_contract(self):
        self.check_active_native_entry(with_flags=True)

    def check_active_native_entry(self,*,with_flags=False):
        from tests.test_h3_daily_integration import frame,captured
        from tests.production_h3_fixture import supplied_day
        from mta.mdm.daily_input import compose,nms_master_raw
        from mta.mdm.supplier_capture import complete_feeds
        from mta.mdm.integration_source import replace_working_inputs
        from mta.temporal.chain import calculate_day
        from mta.planning.engine import calculate_current_day
        f=frame();prior=f['opening']['state']
        if with_flags:
            # Nonempty current state is necessary to exercise mutation; an
            # empty immutable collection only proves the collection protocol.
            for name in ('SuspendStockType','SuspendConsumptionType','SuspendOrderType'):
                prior['dbm'][name]=[dict(SKUCode=m['SKUCode'],WhCode=m['WhCode'],
                    RedEnabled=True,GreenEnabled=True,RedResumeDate=m['SKUIntroDate'],
                    GreenResumeDate=m['SKUIntroDate'],
                    **({'SuggestionStartDate':None} if name=='SuspendOrderType' else {}))
                    for m in prior['dbm']['DBMMaster']]
        for row in prior['importer']['SkuLocAttributeData']:
            row['NonNMS']=bool(row['NonNMS'])
        def compute(spooled,*,bad_policy=False,large_configuration=False):
            working=deepcopy(prior)
            frozen=captured(working,'WithDestLoc')
            day=supplied_day('2037-04-10')['day']
            day.update(raw_master=compose(frozen,nms_master_raw(working),last_run_date='2037-04-09'),
                exclusions=[],supplier_feeds=complete_feeds(frozen,working))
            replace_working_inputs(frozen,working,day,None)
            profile=deepcopy(f['profile'])
            if bad_policy:
                profile['calculation']['policies'][0]['policy']['pso_high']='not-a-number'
            raw=dict(opening=dict(state=deepcopy(prior)),day=day,profile=profile,mdm_input=frozen)
            if spooled:
                raw=persisted_input(raw,large_configuration=large_configuration)
                self.assertIsInstance(raw['profile']['calculation']['stock_openings'],RecordRows)
                self.assertIsInstance(raw['profile']['calculation']['policies'],RecordRows)
                self.assertIsInstance(raw['mdm_input']['rows']['skuloc']['attributes'],RecordRows)
            before=typed(raw)
            working=deepcopy(raw['opening']['state']);day=deepcopy(raw['day']);profile=raw['profile']
            from mta.runtime.captured_recovery import _restore_working
            _restore_working(raw['mdm_input'],working,day,None)
            calculation_before=typed(working),typed(day),typed(profile)
            def calculate(source,**owned):
                return calculate_current_day(source,defer_pick=True,**owned),'active-entry-proof'
            try:
                actual=calculate_day(working,'2037-04-09',day,profile,
                    'active-entry-proof',calculate,native_daily=True)
            finally:
                self.assertEqual((typed(working),typed(day),typed(profile)),calculation_before)
                self.assertEqual(typed(raw),before)
            return actual
        from mta.serialization import digest
        expected=compute(False);before=typed(expected)
        actual=compute(True)
        self.assertEqual(typed(actual),before)
        self.assertEqual(digest(actual),digest(expected))
        self.assertEqual(typed(expected),before)
        self.assertEqual(typed(compute(True,large_configuration=True)),before)
        from decimal import InvalidOperation
        with self.assertRaises(InvalidOperation) as eager:
            compute(False,bad_policy=True)
        with self.assertRaises(type(eager.exception)) as persisted:
            compute(True,bad_policy=True)
        self.assertEqual(str(persisted.exception),str(eager.exception))

    def test_nonempty_spooled_nms_and_non_nms_raw_use_same_canonical_producer(self):
        import json
        from pathlib import Path
        from mta.application.r1_importer_master import process_importer_master
        payload=json.loads((Path(__file__).parents[1]/'mta/fixtures/r1_importer_master_base.json').read_text())
        payload['raw_non_nms']=[payload['raw_master'].pop()]
        payload['import_non_nms']=True
        expected=process_importer_master(deepcopy(payload))
        self.assertEqual(expected['outcome'],'APPLIED')
        spooled=deepcopy(payload)
        for name,rows in spooled['prior'].items():
            spooled['prior'][name]=RecordRows.from_rows(rows)
        for name in ('raw_master','raw_non_nms'):
            self.assertTrue(spooled[name])
            spooled[name]=RecordRows.from_rows(spooled[name])
        before=typed(spooled)
        self.assertEqual(typed(process_importer_master(spooled)),typed(expected))
        self.assertEqual(typed(spooled),before)

    def test_bit_adapter_has_lazy_owned_generation_and_exact_non_bit_values(self):
        from datetime import date
        from decimal import Decimal
        rows=[dict(Approved=True,NonNMS=False,Event_Type=None,Count=1,
                   Quantity=Decimal('1.00'),Date=date(2026,4,7),Name=' A ')]*2
        def prepare(source):
            prior=dict(importer_settings=[],importer={'T':source},bpr={})
            return entry_inputs(prior,'2026-04-07',dict(business_date='2026-04-08',
                raw_master=[],raw_non_nms=[],raw_no_norm=[],raw_daily=[]),
                dict(import_non_nms=True,daily={}),'entry-proof')[0]['prior']['T']
        expected=prepare(deepcopy(rows))
        spool=RecordRows.from_rows(rows)
        before=typed(spool)
        actual=prepare(spool)
        self.assertIsInstance(actual,RecordRows)
        self.assertFalse(hasattr(actual,'_data'))  # lazy, no second spool/list
        self.assertEqual(typed(actual),typed(expected))
        self.assertEqual(typed(actual),typed(expected))
        self.assertEqual(typed(actual[1]),typed(expected[1]))
        self.assertEqual(typed(spool),before)
        self.assertIs(type(actual[0]['Approved']),int)
        self.assertIs(type(spool[0]['Approved']),bool)
        with self.assertRaisesRegex(TypeError,'Immutable'):
            actual[0]['Approved']=0
        nested=[dict(Approved=True,extra={'flag':False,'items':[1,None]})]
        converted=prepare(nested)
        converted[0]['extra']['items'].append(2)
        self.assertEqual(nested[0]['extra']['items'],[1,None])
        self.assertIs(converted[0]['extra']['flag'],False)

    def test_complete_spooled_entry_equals_eager_and_keeps_original_generations(self):
        from tests.test_h3_inactive_mode import inactive_frame,inactive_day
        from tests.test_production_daily_contract import encoded_day
        from mta.runtime.production_daily import working_day,decode
        from mta.temporal.chain import calculate_day
        from mta.planning.engine import calculate_current_day
        frame=inactive_frame()
        day=working_day(decode(*encoded_day(inactive_day('2037-04-10',root=True))),frame['profile'])
        prior=frame['opening']['state']
        for row in prior['importer']['SkuLocAttributeData']:
            row['NonNMS']=bool(row['NonNMS'])
        def calculate(source,**owned):
            return calculate_current_day(source,defer_pick=True,**owned),'owned-entry-proof'
        expected=calculate_day(deepcopy(prior),'2037-04-09',deepcopy(day),
            frame['profile'],'owned-entry-proof',calculate,native_daily=True)
        raw=persisted_input(dict(opening=dict(state=prior),day=day,profile=frame['profile']))
        before=typed(raw)
        actual=calculate_day(raw['opening']['state'],'2037-04-09',raw['day'],raw['profile'],
            'owned-entry-proof',calculate,native_daily=True)
        self.assertEqual(typed(actual),typed(expected))
        from mta.serialization import digest
        self.assertEqual(digest(actual),digest(expected))
        self.assertEqual(typed(raw),before)

    def test_importer_rejection_is_identical_for_spooled_rows(self):
        from tests.test_h3_inactive_mode import inactive_frame,inactive_day
        from mta.application.r1_importer_master import validate_master_input
        frame=inactive_frame();prior=frame['opening']['state']
        day=inactive_day('2037-04-10',root=True)['day']
        # This tests the unchanged row/NULL validator, beyond the adapter.
        payload,_=entry_inputs(prior,'2037-04-09',day,frame['profile'],'owned-entry-proof')
        for field,bad in (('Norm',None),('Norm','not-a-number')):
            with self.subTest(value=bad):
                eager=deepcopy(payload)
                eager['prior']['MasterData'][0][field]=bad
                with self.assertRaises(ValueError) as expected:
                    validate_master_input(eager)
                spooled=deepcopy(eager)
                spooled['prior']['MasterData']=RecordRows.from_rows(spooled['prior']['MasterData'])
                with self.assertRaises(type(expected.exception)) as actual:
                    validate_master_input(spooled)
                self.assertEqual(str(actual.exception),str(expected.exception))
        payload['prior']['MasterData']=iter(payload['prior']['MasterData'])
        with self.assertRaisesRegex(ValueError,'list or immutable record rows'):
            validate_master_input(payload)
