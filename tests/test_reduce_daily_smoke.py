import json
import unittest

from parity.temporal_ledger import validate
from tools import reduce_daily_smoke as reducer


class ReduceDailySmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.raw = reducer.SOURCE.read_bytes()
        cls.source = json.loads(cls.raw)
        cls.derived, cls.receipt = reducer.reduce_document(cls.raw)

    @classmethod
    def tearDownClass(cls):
        del cls.derived, cls.receipt, cls.source, cls.raw
        super().tearDownClass()

    def test_registered_source_reduces_to_exact_ordered_pairs_and_valid_ledger(self):
        self.assertEqual(reducer._sha256(self.raw), reducer.SOURCE_SHA256)
        expected = [row for row in self.source['case']['static_day']['raw_master']
                    if (str(row['SKUCode']), str(row['WhCode'])) in set(reducer.TARGET_PAIRS)]
        actual = self.derived['case']['static_day']['raw_master']
        self.assertEqual(actual, expected)
        self.assertEqual([(str(row['SKUCode']), str(row['WhCode'])) for row in actual],
                         list(reducer.TARGET_PAIRS))
        self.assertEqual(validate(self.derived), self.receipt['ledger_validation'])
        expected_facts = [row for row in
            self.source['case']['external_fact_ledger']['daily_reconciliation']
            if (str(row['SKUCode']), str(row['WhCode'])) in set(reducer.TARGET_PAIRS)]
        self.assertEqual(self.derived['case']['external_fact_ledger']['daily_reconciliation'],
                         expected_facts)
        self.assertEqual(self.receipt['ledger_validation']['counts'],
                         {'identities': 10, 'fact_rows': 280, 'shipments': 263})
        self.assertEqual(self.receipt['ledger_validation']['computed_days'], 12)

    def test_values_duplicates_order_and_required_directories_are_only_filtered(self):
        case = self.derived['case']
        self.assertEqual(case['opening']['bpr']['Plants'],
                         self.source['case']['opening']['bpr']['Plants'])
        self.assertEqual(case['opening']['controls']['dbm_settings'],
                         self.source['case']['opening']['controls']['dbm_settings'])
        self.assertEqual(case['opening']['dbm']['ui_ReportConfigurations'],
                         self.source['case']['opening']['dbm']['ui_ReportConfigurations'])
        self.assertEqual([row['WHCode'] for row in case['opening']['dbm']['SiteDescriptionTbl']],
                         [row['WHCode'] for row in
                          self.source['case']['opening']['dbm']['SiteDescriptionTbl']
                          if row['WHCode'] in set(reducer.TARGET_LOCATIONS) | {reducer.EXTERNAL_PARENT}])
        self.assertIn(reducer.EXTERNAL_PARENT,
                      {row['WHCode'] for row in case['opening']['dbm']['SiteDescriptionTbl']})
        for day in case['days']:
            self.assertEqual(len(day['raw_daily']), 10)
        self.assertNotIn('identity_guard', self.derived)
        self.assertNotIn('retained_identity', self.derived)
        self.assertEqual(self.derived['derivative_provenance']['source_sha256'],
                         reducer.SOURCE_SHA256)
        self.assertEqual(self.derived['derivative_provenance']['removed_full_identity_fields'],
                         ['identity_guard', 'retained_identity'])

    def test_unknown_population_fails_instead_of_being_silently_copied(self):
        dbm = self.source['case']['opening']['dbm']
        dbm['UnexpectedPopulation'] = [{'SKUCode': reducer.TARGET_SKU}]
        try:
            with self.assertRaisesRegex(ValueError, 'Unclassified temporal populations'):
                reducer._reduce_case(self.source['case'], {})
        finally:
            del dbm['UnexpectedPopulation']

    def test_cross_pair_command_dependency_fails_instead_of_partial_filter(self):
        command = {
            'after_day': 0, 'cohort': 'test', 'operation': 'APPLY',
            'selected': [list(reducer.TARGET_PAIRS[0]), ['9999', reducer.TARGET_LOCATIONS[0]]],
            'timestamp': '2026-06-06T00:00:00',
        }
        self.source['case']['commands'].append(command)
        try:
            with self.assertRaisesRegex(ValueError, 'Command mixes retained and external pairs'):
                reducer._reduce_case(self.source['case'], {})
        finally:
            self.source['case']['commands'].pop()

    def test_input_bytes_must_match_the_registered_sha(self):
        with self.assertRaisesRegex(ValueError, 'artifact identity differs'):
            reducer.reduce_document(self.raw + b' ')


if __name__ == '__main__':
    unittest.main()
