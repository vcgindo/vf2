from copy import deepcopy
from unittest.mock import patch
import os
import unittest

os.environ.setdefault('VF_SECRET_KEY', 'master-compatibility-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.application.master_compatibility import unchanged_plan
from mta.application.r1_importer_master import (
    MASTER_COLUMNS, PRIOR_TABLES, RAW_COLUMNS, process_importer_master,
)
from mta.mdm import daily_input
from mta.row_sequences import RecordRows
from mta.serialization import digest
from tests.test_mdm_daily_input import snapshot


DAY = '2026-10-19'


def nms_item():
    row = dict.fromkeys(RAW_COLUMNS)
    row.update(SKUCode='s1 ', WhCode='w1 ', ParentWhCode='p ', Norm=17,
        MinNorm=0, RLT=3, RCP=3, GCP=3, OCP=None, MinOrderCount=None,
        SKUIntroDate='2026-10-01', ElephantOrderCapping=None,
        Weight=None, Volume=None)
    return row


def unchanged_snapshot():
    value = snapshot()
    value['rows']['sku']['descriptions'] = [
        {'id': 1, 'SKUCode': 's1 ', 'SKUDescription': 'Latest SKU  '},
        {'id': 2, 'SKUCode': 'ORPHAN-SKU', 'SKUDescription': 'Orphan SKU'}]
    value['rows']['location']['descriptions'] = [
        {'id': 1, 'WHCode': 'w1 ', 'WHDescription': 'Latest Location'},
        {'id': 2, 'WHCode': 'p ', 'WHDescription': 'Parent Only'},
        {'id': 3, 'WHCode': 'ORPHAN-LOC', 'WHDescription': 'Orphan Location'},
        {'id': 4, 'WHCode': 'ORPHAN-LOC', 'WHDescription': 'Orphan Location'}]
    sku_attr = {'id': 1, 'SKUCode': 'S1'}
    for name in daily_input.SKU_FIELDS:
        if name != 'SKUDescription':
            sku_attr[name] = None
    sku_attr['SL1'] = 'Category'
    value['rows']['sku']['attributes'] = [sku_attr]
    loc_attr = {'id': 1, 'WHCode': 'W1'}
    for name in daily_input.LOCATION_FIELDS:
        if name != 'WHDescription':
            loc_attr[name] = None
    loc_attr['LL1'] = 'Region'
    value['rows']['location']['attributes'] = [loc_attr]
    pair = {'id': 1, 'SKUCode': 'S1', 'LocCode': 'W1'}
    for name in daily_input.PAIR_ATTRIBUTES:
        pair[name] = None
    pair.update(PackSize=6, StockPercentForRationing=75,
                NormPercentReservation=0)
    value['rows']['skuloc']['attributes'] = [pair]
    value['revision_digest'] = digest({k: v for k, v in value.items()
                                       if k != 'revision_digest'})
    return value


def full_raw(value, items):
    prior = {'consumer_context': {'NMSAllItems': deepcopy(items)}}
    return daily_input.compose(value, daily_input.nms_master_raw(prior),
                               last_run_date=DAY)


def full_canonical(value, items):
    raw = full_raw(value, items)
    payload = {'schema': 'r1-importer-master-input-v1', 'business_date': DAY,
        'run_timestamp': DAY + 'T00:00:00', 'import_non_nms': False,
        'settings': [{'Parameter': 'NMSActive', 'Value': 1},
                     {'Parameter': 'DBMActive', 'Value': 1},
                     {'Parameter': 'UpdatePWh_RLT_RCP_GCP', 'Value': 1}],
        'prior_provenance': {'kind': 'SYNTHETIC_PRIOR_IMPORTER',
            'identity': 'lazy-master-compatibility', 'business_date': '2026-10-18'},
        'prior': {name: [] for name in PRIOR_TABLES}, 'raw_master': raw,
        'raw_non_nms': [], 'raw_no_norm': []}
    return process_importer_master(payload)['tables']['MasterDataRaw']


class MasterCompatibilityTests(unittest.TestCase):
    def test_raw_view_exactly_matches_full_composition_with_orphans_and_overlays(self):
        value, items = unchanged_snapshot(), [nms_item()]
        expected = full_raw(value, items)
        with patch.object(daily_input, 'nms_master_raw', side_effect=AssertionError), \
                patch.object(daily_input, 'compose', side_effect=AssertionError), \
                patch('mta.application.r1_importer_master.process_importer_master',
                      side_effect=AssertionError):
            plan = unchanged_plan(value, items, DAY)
            actual = list(plan.raw)
        self.assertIsInstance(plan.raw, RecordRows)
        self.assertEqual(actual, expected)
        self.assertEqual(list(plan.view()), expected)
        self.assertEqual(plan.counts, {'nms': 1, 'metadata': 4, 'total': 5})
        self.assertEqual(actual[0]['Norm'], 17)
        self.assertEqual(actual[0]['ParentDescription'], 'Parent Only')
        self.assertEqual(sum(row['WhCode'] == 'ORPHAN-LOC' for row in actual), 2)

    def test_canonical_view_matches_full_producer_order_padding_and_current_date(self):
        value, items = unchanged_snapshot(), [nms_item()]
        expected = full_canonical(value, items)
        plan = unchanged_plan(value, items, DAY)
        actual = list(plan.canonical)
        self.assertEqual(actual, expected)
        self.assertEqual(list(plan.view(canonical=True)), expected)
        self.assertEqual(list(plan.canonical), expected)
        orphan = next(row for row in actual if row['SKUCode'] == 'ORPHAN-SKU')
        self.assertEqual(orphan['SKUIntroDate'], DAY)
        self.assertEqual(next(row for row in actual if row['SKUCode'] == 's1 ')['SKUDescription'],
                         'Latest SKU')
        with self.assertRaises(TypeError):
            plan.canonical[0]['Norm'] = 999

    def test_case_trailing_null_and_duplicate_occurrences_remain_exact(self):
        value, items = unchanged_snapshot(), [nms_item(), deepcopy(nms_item())]
        items[1]['SKUCode'] = None
        items[1]['WhCode'] = None
        items[1]['ParentWhCode'] = None
        items[1]['Norm'] = None
        raw = full_raw(value, items)
        plan = unchanged_plan(value, items, DAY)
        self.assertEqual(list(plan.raw), raw)
        self.assertEqual(list(plan.canonical), full_canonical(value, items))

    def test_reuse_preserves_latest_operational_norm_and_complete_canonical_tables(self):
        from mta.application.persistent_master import MasterReuse
        value=unchanged_snapshot()
        initial=full_raw(value,[nms_item()])
        def payload(rows,prior,day):
            return dict(schema='r1-importer-master-input-v1',business_date=day,
                run_timestamp=day+'T00:00:00',import_non_nms=False,
                settings=[{'Parameter':n,'Value':1} for n in
                    ('NMSActive','DBMActive','UpdatePWh_RLT_RCP_GCP')],
                prior_provenance=dict(kind='SYNTHETIC_PRIOR_IMPORTER',identity='norm-reuse-proof',
                    business_date='2026-10-17'),prior=deepcopy(prior),raw_master=rows,
                raw_non_nms=[],raw_no_norm=[])
        first=process_importer_master(payload(initial,{name:[] for name in PRIOR_TABLES},'2026-10-18'))
        importer={name:first['tables'][name] for name in PRIOR_TABLES}
        for row in importer['MasterData']:row['Norm']=31
        nms=[deepcopy(next(row for row in first['tables']['MasterDataRaw']
            if row['SKUCode'] is not None and row['WhCode'] is not None))]
        nms[0]['Norm']=17
        prior=dict(importer=importer,importer_settings=payload([],{},DAY)['settings'],
            consumer_context={'NMSAllItems':nms})
        expected=process_importer_master(payload(full_raw(value,nms),importer,DAY))
        with patch('mta.application.r1_importer_master.process_importer_master',side_effect=AssertionError):
            actual=MasterReuse(prior,value,DAY).result
        self.assertEqual(digest(actual),digest(expected))
        self.assertEqual(actual['tables']['MasterData'][0]['Norm'],31)
        self.assertEqual(next(row['Norm'] for row in actual['tables']['MasterDataRaw']
            if row['SKUCode'] is not None and row['WhCode'] is not None),17)

    def test_inactive_or_approved_changes_are_explicitly_denied(self):
        inactive = unchanged_snapshot()
        inactive['nms_active'] = False
        inactive['revision_digest'] = digest({k: v for k, v in inactive.items()
                                              if k != 'revision_digest'})
        with self.assertRaisesRegex(ValueError, 'active NMS'):
            unchanged_plan(inactive, [nms_item()], DAY)
        changed = unchanged_snapshot()
        changed['rows']['sku']['approved'] = [{'Approved': True}]
        changed['revision_digest'] = digest({k: v for k, v in changed.items()
                                             if k != 'revision_digest'})
        with self.assertRaisesRegex(ValueError, 'approved family changes'):
            unchanged_plan(changed, [nms_item()], DAY)

    def test_nullable_operational_norm_retains_canonical_rejection(self):
        from mta.application.persistent_master import CONTRACT, select
        value=unchanged_snapshot()
        profile={'import_non_nms':False}
        day={'business_date':DAY,'raw_non_nms':[],'raw_no_norm':[]}
        cut=(3,4,0,0,0)
        previous=dict(contract=CONTRACT,qualified=True,
            configuration_digest=digest(profile),master_cut=[3,4])
        item=nms_item();item['Norm']=None
        with patch('mta.application.persistent_master.MasterReuse',side_effect=AssertionError):
            self.assertIsNone(select({'consumer_context':{'NMSAllItems':[item]}},
                profile,day,value,previous,cut))
        # Fallback remains the existing producer's decision, not a new default.
        payload=dict(schema='r1-importer-master-input-v1',business_date=DAY,
            run_timestamp=DAY+'T00:00:00',import_non_nms=False,
            settings=[{'Parameter':n,'Value':1} for n in
                ('NMSActive','DBMActive','UpdatePWh_RLT_RCP_GCP')],
            prior_provenance=dict(kind='SYNTHETIC_PRIOR_IMPORTER',identity='null-norm-proof',
                business_date='2026-10-18'),prior={name:[] for name in PRIOR_TABLES},
            raw_master=full_raw(value,[item]),raw_non_nms=[],raw_no_norm=[])
        result=process_importer_master(payload)
        self.assertNotEqual(result['outcome'],'APPLIED')


if __name__ == '__main__':
    unittest.main()
