from copy import deepcopy
from unittest.mock import patch
import unittest

from mta.application import master_preparation
from mta.application.r1_importer_master import (
    NO_NORM_COLUMNS, PRIOR_TABLES, RAW_COLUMNS, process_importer_master,
)


def raw(sku, wh, parent, *, norm=10, pack=1, parent_name=None):
    row = dict.fromkeys(RAW_COLUMNS)
    row.update(SKUCode=sku, WhCode=wh, ParentWhCode=parent, Norm=norm,
        MinNorm=0, RLT=3, RCP=3, GCP=3, PackSize=pack,
        SKUDescription='Name ' + sku, WHDescription='Name ' + wh,
        ParentDescription=parent_name or 'Name ' + parent,
        SKUIntroDate='2026-10-01')
    return row


def payload(rows, *, day='2026-10-18', settings=None, prior=None,
            import_non_nms=False, raw_non_nms=None, raw_no_norm=None):
    settings = settings or [('NMSActive', 1), ('DBMActive', 1),
                            ('UpdatePWh_RLT_RCP_GCP', 1)]
    return {
        'schema': 'r1-importer-master-input-v1',
        'business_date': day,
        'run_timestamp': day + 'T00:00:00',
        'import_non_nms': import_non_nms,
        'settings': [{'Parameter': name, 'Value': value} for name, value in settings],
        'prior_provenance': {'kind': 'SYNTHETIC_PRIOR_IMPORTER',
                             'identity': 'master-preparation-test',
                             'business_date': '2026-10-17' if day == '2026-10-18'
                                              else '2026-10-18'},
        'prior': deepcopy(prior) if prior is not None else {name: [] for name in PRIOR_TABLES},
        'raw_master': deepcopy(rows),
        'raw_non_nms': deepcopy(raw_non_nms or []),
        'raw_no_norm': deepcopy(raw_no_norm or []),
    }


def changes(*, sku=(), location=(), pair=(), retirement=(), global_change=False):
    pairs = lambda rows: [{'SKUCode': sku, 'WhCode': wh} for sku, wh in rows]
    return {'sku': list(sku), 'location': list(location), 'pair': pairs(pair),
            'retirement': pairs(retirement), 'global': global_change}


class ChangedMasterPreparationTests(unittest.TestCase):
    def setUp(self):
        self.rows = [raw('S1', 'W1', 'P1'), raw('S2', 'W2', 'P2')]
        self.root = process_importer_master(payload(self.rows))
        self.prior_raw = self.root['tables']['MasterDataRaw']
        self.prior = {name: self.root['tables'][name] for name in PRIOR_TABLES}

    def successor(self, rows=None, **overrides):
        return payload(rows or self.prior_raw, day='2026-10-19', prior=self.prior,
                       **overrides)

    def assert_full_exact(self, value, change, mode):
        expected = process_importer_master(value)
        with patch.object(master_preparation, 'process_importer_master',
                          wraps=process_importer_master) as producer:
            actual = master_preparation.prepare_changed(value, self.prior_raw, change)
        self.assertEqual(actual['eligibility']['mode'], mode)
        self.assertEqual(actual['result'], expected)
        return actual, producer

    def test_changed_sku_runs_one_complete_component_without_accepted_copy(self):
        rows = deepcopy(self.prior_raw)
        next(row for row in rows if row['SKUCode'] == 'S1')['PackSize'] = 4
        value = self.successor(rows)
        expected = process_importer_master(value)
        with patch.object(master_preparation, 'process_importer_master',
                          wraps=process_importer_master) as producer:
            actual = master_preparation.prepare_changed(
                value, self.prior_raw, changes(sku=('s1 ',)))
        self.assertEqual(producer.call_count, 1)
        self.assertEqual(len(producer.call_args.args[0]['raw_master']), 1)
        self.assertEqual(actual['eligibility']['mode'], 'SCOPED')
        self.assertEqual(actual['work'], {
            'producer_calls': 1, 'producer_rows': 1,
            'affected_skus': 1, 'affected_locations': 2,
            'prior_rows': 2, 'current_rows': 2,
        })
        self.assertNotIn('accepted', actual)
        self.assertNotIn('operational', actual)
        self.assertEqual(actual['result'], expected)

    def test_parent_closure_and_complete_catalogue_use_one_full_call(self):
        rows = [raw('S1', 'W1', 'P'), raw('S2', 'W2', 'P')]
        root = process_importer_master(payload(rows))
        prior = {name: root['tables'][name] for name in PRIOR_TABLES}
        changed_rows = deepcopy(root['tables']['MasterDataRaw'])
        for row in changed_rows:
            row['ParentDescription'] = 'New Parent'
        value = payload(changed_rows, day='2026-10-19', prior=prior)
        expected = process_importer_master(value)
        with patch.object(master_preparation, 'process_importer_master',
                          wraps=process_importer_master) as producer:
            actual = master_preparation.prepare_changed(
                value, root['tables']['MasterDataRaw'], changes(location=('p ',)))
        self.assertEqual(producer.call_count, 1)
        self.assertEqual(actual['eligibility']['mode'], 'FULL_CLOSURE')
        self.assertEqual(actual['work']['affected_skus'], 2)
        self.assertEqual(actual['result'], expected)

    def test_unreported_raw_change_is_an_explicit_full_fallback(self):
        rows = deepcopy(self.prior_raw)
        next(row for row in rows if row['SKUCode'] == 'S2')['PackSize'] = 9
        actual, producer = self.assert_full_exact(
            self.successor(rows), changes(sku=('S1',)), 'FULL_UNREPORTED')
        self.assertEqual(producer.call_count, 1)
        self.assertFalse(actual['eligibility']['qualified'])

    def test_retirement_within_nonempty_component_is_scoped_and_exact(self):
        rows = [raw('S1', 'W1', 'P1'), raw('S1', 'W1B', 'P1'),
                raw('S2', 'W2', 'P2')]
        root = process_importer_master(payload(rows))
        prior = {name: root['tables'][name] for name in PRIOR_TABLES}
        changed_rows = [row for row in root['tables']['MasterDataRaw']
                        if not (row['SKUCode'] == 'S1' and row['WhCode'] == 'W1B')]
        value = payload(changed_rows, day='2026-10-19', prior=prior)
        expected = process_importer_master(value)
        actual = master_preparation.prepare_changed(
            value, root['tables']['MasterDataRaw'],
            changes(retirement=(('S1', 'W1B'),)))
        self.assertEqual(actual['eligibility']['mode'], 'SCOPED')
        self.assertEqual(actual['result'], expected)
        self.assertEqual([(row['SKUCode'], row['WhCode'])
                          for row in actual['result']['retired_events_added']],
                         [('S1', 'W1B')])

    def test_complete_retirement_and_partial_rejection_fall_back_exactly(self):
        retired_rows = [row for row in self.prior_raw if row['SKUCode'] != 'S1']
        retired, producer = self.assert_full_exact(
            self.successor(retired_rows),
            changes(retirement=(('S1', 'W1'),)), 'FULL_EMPTY_CLOSURE')
        self.assertEqual(producer.call_count, 1)
        self.assertEqual(retired['work']['affected_skus'], 1)

        duplicate = deepcopy(self.prior_raw)
        duplicate.append(deepcopy(next(row for row in duplicate
                                       if row['SKUCode'] == 'S1')))
        rejected, producer = self.assert_full_exact(
            self.successor(duplicate), changes(sku=('S1',)), 'FULL_EARLY_RETURN')
        self.assertEqual(producer.call_count, 2)
        self.assertEqual(rejected['result']['rejects_added'][0]['ReasonCode'], 1)

    def test_global_non_nms_no_norm_and_date_sensitive_cases_are_full(self):
        global_result, producer = self.assert_full_exact(
            self.successor(), changes(global_change=True), 'FULL_GLOBAL')
        self.assertEqual(producer.call_count, 1)
        self.assertEqual(global_result['work']['producer_calls'], 1)

        non_nms = self.successor(import_non_nms=True,
                                 raw_non_nms=[raw('S3', 'W3', 'P3')])
        _, producer = self.assert_full_exact(
            non_nms, changes(sku=('S3',)), 'FULL_NON_NMS')
        self.assertEqual(producer.call_count, 1)

        overlap = {name: self.prior_raw[0][name] for name in NO_NORM_COLUMNS}
        _, producer = self.assert_full_exact(
            self.successor(raw_no_norm=[overlap]),
            changes(sku=('S1',)), 'FULL_NO_NORM')
        self.assertEqual(producer.call_count, 1)

        dated = deepcopy(self.prior_raw)
        next(row for row in dated if row['SKUCode'] == 'S1')['SKUIntroDate'] = None
        _, producer = self.assert_full_exact(
            self.successor(dated), changes(sku=('S1',)), 'FULL_DATE')
        self.assertEqual(producer.call_count, 1)

    def test_changed_only_api_never_treats_an_empty_queue_as_unchanged(self):
        actual, producer = self.assert_full_exact(
            self.successor(), changes(), 'FULL_UNQUALIFIED')
        self.assertEqual(producer.call_count, 1)
        self.assertEqual(actual['work']['producer_rows'], len(self.prior_raw))

    def test_orphan_location_metadata_is_scoped_by_sql_location_key(self):
        orphan = raw('PLACEHOLDER', 'W9', 'P9')
        orphan['SKUCode'] = None
        orphan['SKUDescription'] = None
        rows = self.rows + [orphan]
        root = process_importer_master(payload(rows))
        prior = {name: root['tables'][name] for name in PRIOR_TABLES}
        changed_rows = deepcopy(root['tables']['MasterDataRaw'])
        next(row for row in changed_rows
             if row['SKUCode'] is None and row['WhCode'] == 'W9')['WHDescription'] = 'Renamed W9'
        value = payload(changed_rows, day='2026-10-19', prior=prior)
        expected = process_importer_master(value)
        with patch.object(master_preparation, 'process_importer_master',
                          wraps=process_importer_master) as producer:
            actual = master_preparation.prepare_changed(
                value, root['tables']['MasterDataRaw'], changes(location=('w9 ',)))
        self.assertEqual(producer.call_count, 1)
        self.assertEqual(len(producer.call_args.args[0]['raw_master']), 1)
        self.assertEqual(actual['eligibility']['mode'], 'SCOPED')
        self.assertEqual(actual['work']['affected_skus'], 0)
        self.assertEqual(actual['result'], expected)


if __name__ == '__main__':
    unittest.main()
