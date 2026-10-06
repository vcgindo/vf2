import os
import unittest

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.application.r1_importer_master import RAW_COLUMNS
from mta.mdm.daily_input import (SCHEMA, SQL_DIGEST, CONSUMER_ORDER,
                                 apply_refresh_setting, capture_configuration, compose,
                                 compose_pair_exclusions)
from mta.serialization import digest


def blank(**values):
    return {**dict.fromkeys(RAW_COLUMNS), **values}


def approved_sku(code, action):
    return {'id': 1, 'SKUCode': code, 'SKUDescription': code + '-description',
        'ElephantOrderCapping': None, 'Weight': None, 'Volume': None,
        **{'SL%d' % i: None for i in range(1, 6)},
        **{'c%d' % i: None for i in range(1, 16)},
        'ActionType': action, 'Approved': True, 'Reverted': False}


def approved_location(code, action, pk=1):
    return {'id': pk, 'WHCode': code, 'WHDescription': code + '-description',
        'LocationType': None, 'LogisticsLocation': None,
        **{'LL%d' % i: None for i in range(1, 6)},
        **{'c%d' % i: None for i in range(1, 16)},
        'ActionType': action, 'Approved': True, 'Reverted': False}


def pair_add(sku, location):
    values = {'id': 1, 'SKUCode': sku, 'WhCode': location,
        'ParentWhCode': 'PARENT', 'Norm': 10, 'MinNorm': 5, 'RLT': 2,
        'RCP': 1, 'GCP': 1, 'OCP': 0, 'PackSize': 4,
        'SpikeThreshold': '1.00', 'PSOThreshold': '2.00', 'FGRMFlag': None,
        'DBMActive': True, 'StockPercentForRat': 100,
        'NormPercentReservation': 0, 'MinOrderCount': 1, 'Approved': True}
    values.update({'SKULocAtt%02d' % i: None for i in range(1, 16)})
    return values


def snapshot(*, sku=(), location=(), additions=(), modifications=(), removals=(),
             exclusions=(), active=True):
    rows = {'sku': {'attributes': [], 'descriptions': [], 'approved': list(sku)},
        'location': {'attributes': [], 'descriptions': [], 'approved': list(location)},
        'skuloc': {'attributes': [], 'additions': list(additions),
                   'modifications': list(modifications), 'removals': list(removals)}}
    result = {'schema': SCHEMA, 'source_id': 1, 'source_digest': 's' * 64,
        'sql_digest': SQL_DIGEST, 'nms_active': active,
        'consumer_order': list(CONSUMER_ORDER), 'revision_digests': {},
        'rows': rows,
        'pair_exclusion_opening': {'digest': digest(list(exclusions)),
            'row_count': len(exclusions), 'rows': list(exclusions)},
        'pair_exclusions_post_nms': list(exclusions),
        'pair_exclusions': list(exclusions),
        'occurrences': [], 'tasks': []}
    result['revision_digest'] = digest(result)
    return result


class DailyMdmCompositionTests(unittest.TestCase):
    def test_capture_configuration_requires_exact_scalar_settings(self):
        settings = [{'Parameter': 'NMSActive', 'Value': '0'},
                    {'Parameter': 'TaskStatusLogHorizon', 'Value': '7'}]
        self.assertEqual(capture_configuration(settings), (False, 7))
        self.assertEqual(capture_configuration([*settings,
            {'Parameter': 'NMSActive', 'Value': '0'}]), (False, 7))
        self.assertEqual(capture_configuration(settings[1:]), (False, 7))
        with self.assertRaisesRegex(ValueError, 'NMSActive count'):
            capture_configuration([settings[1],
                {'Parameter': 'NMSActive', 'Value': '1'},
                {'Parameter': 'NMSActive', 'Value': '1'}])
        with self.assertRaisesRegex(ValueError, 'TaskStatusLogHorizon'):
            capture_configuration(settings[:1])
        self.assertEqual(capture_configuration([
            {'Parameter': 'TaskStatusLogHorizon', 'Value': '-1'}]), (False, -1))

    def test_active_capture_sets_native_parent_refresh_marker(self):
        settings = [
            {'Parameter': 'NMSActive', 'Value': '1'},
            {'Parameter': 'DBMActive', 'Value': '1'},
            {'Parameter': 'UpdatePWh_RLT_RCP_GCP', 'Value': '0'}]
        apply_refresh_setting(settings, {'nms_active': True})
        marker = [row for row in settings
                  if row['Parameter'] == 'UpdatePWh_RLT_RCP_GCP']
        self.assertEqual(marker, [{'Parameter': 'UpdatePWh_RLT_RCP_GCP', 'Value': '1'}])

    def test_pair_add_precedes_sku_delete(self):
        result = compose(snapshot(sku=[approved_sku('NEW', 0)],
            additions=[pair_add('NEW', 'LOC')]), [], last_run_date='2026-10-05')
        self.assertEqual(result, [])

    def test_pair_add_precedes_location_delete(self):
        result = compose(snapshot(location=[approved_location('LOC', 0)],
            additions=[pair_add('NEW', 'LOC')]), [], last_run_date='2026-10-05')
        self.assertEqual(result, [])

    def test_new_pair_dbm_off_updates_pair_exclusions(self):
        added = pair_add('NEW', 'LOC'); added['DBMActive'] = False
        result = compose_pair_exclusions(snapshot(additions=[added]), [])
        self.assertEqual(result['pair_exclusions'],
                         [{'SKUCode': 'NEW', 'WhCode': 'LOC'}])

    def test_existing_pair_discards_dbm_off_add_before_exclusion_tail(self):
        existing = blank(SKUCode='EXISTING', WhCode='LOC')
        added = pair_add('EXISTING', 'LOC'); added['DBMActive'] = False
        result = compose_pair_exclusions(snapshot(additions=[added]), [existing])
        self.assertEqual(result['pair_exclusions'], [])

    def test_modification_off_adds_and_on_removes_pair(self):
        off = pair_add('EXISTING', 'LOC'); off['DBMActive'] = False
        added = compose_pair_exclusions(snapshot(modifications=[off]), [])
        self.assertEqual(added['pair_exclusions'],
                         [{'SKUCode': 'EXISTING', 'WhCode': 'LOC'}])
        on = pair_add('EXISTING', 'LOC'); on['DBMActive'] = True
        removed = compose_pair_exclusions(snapshot(modifications=[on],
            exclusions=[{'SKUCode': 'EXISTING', 'WhCode': 'LOC'}]), [])
        self.assertEqual(removed['pair_exclusions'], [])

    def test_post_nms_duplicates_are_evidence_then_validation_distincts(self):
        first = pair_add('NEW', 'LOC'); first['DBMActive'] = False
        second = dict(first); second['id'] = 2
        result = compose_pair_exclusions(snapshot(additions=[first, second]), [])
        self.assertEqual(len(result['pair_exclusions_post_nms']), 2)
        self.assertEqual(result['pair_exclusions'],
                         [{'SKUCode': 'NEW', 'WhCode': 'LOC'}])

    def test_partial_null_rejects_whole_validated_exclusion_bag(self):
        modified = pair_add(None, 'LOC'); modified['DBMActive'] = False
        result = compose_pair_exclusions(snapshot(modifications=[modified],
            exclusions=[{'SKUCode': 'KEEP', 'WhCode': 'LOC'}]), [])
        self.assertEqual(result['pair_exclusions_post_nms'], [
            {'SKUCode': 'KEEP', 'WhCode': 'LOC'},
            {'SKUCode': None, 'WhCode': 'LOC'}])
        self.assertEqual(result['pair_exclusions'], [])

    def test_location_add_statement_preserves_duplicate_occurrences(self):
        result = compose(snapshot(location=[approved_location('LOC', 1, 1),
            approved_location('LOC', 1, 2)]), [], last_run_date='2026-10-05')
        self.assertEqual(len(result), 2)
        self.assertEqual([row['WhCode'] for row in result], ['LOC', 'LOC'])

    def test_location_description_statement_preserves_duplicate_occurrences(self):
        value = snapshot()
        value['rows']['location']['descriptions'] = [
            {'id': 1, 'WHCode': 'LOC', 'WHDescription': 'Location'},
            {'id': 2, 'WHCode': 'LOC', 'WHDescription': 'Location'}]
        value['revision_digest'] = digest({k: v for k, v in value.items()
                                           if k != 'revision_digest'})
        result = compose(value, [], last_run_date='2026-10-05')
        self.assertEqual(len(result), 2)

    def test_inactive_does_not_rewrite_input(self):
        source = [blank(SKUCode='BASE', WhCode='LOC')]
        self.assertEqual(compose(snapshot(active=False), source,
                                 last_run_date='2026-10-05'), source)

    def test_complete_master_schema_is_required_when_active(self):
        with self.assertRaisesRegex(ValueError, 'complete MasterDataRaw'):
            compose(snapshot(), [{'SKUCode': 'BASE'}], last_run_date='2026-10-05')

    def test_native_unknown_location_and_parent_descriptions_are_nd(self):
        result = compose(snapshot(), [blank(SKUCode='BASE', WhCode='LOC',
            ParentWhCode='UNKNOWN')], last_run_date='2026-10-05')
        self.assertEqual(result[0]['WHDescription'], 'ND')
        self.assertEqual(result[0]['ParentDescription'], 'ND')


if __name__ == '__main__':
    unittest.main()
