"""No native execution: pinned source and finite proof-boundary checks."""
import unittest
from unittest.mock import patch
from parity.verify_complete_daily_fullkit import (
    source_preflight, statement, fixture_cases, code_pins, STATEMENTS)


class FullkitQualificationTests(unittest.TestCase):
    def test_source_preflight_binds_all_three_bats_and_exact_payloads(self):
        self.assertEqual(len(source_preflight()),3)
        self.assertEqual(statement('initial_files'),
            'update CriticalFiles set [Exists]=0, [ResolvedPath]=NULL,[ResolvedFileName]=NULL')
        self.assertIn("CONVERT(Date,'2026-06-06')",statement('initial_date'))
        self.assertIn("[Type]='GoAheadFiles'",statement('missing_files',file_type='GoAheadFiles'))
        self.assertFalse(statement('post_count').startswith('EXIT('))

    def test_unregistered_or_changed_inline_payload_is_denied(self):
        with patch.dict(STATEMENTS, {'initial_flag':(STATEMENTS['initial_flag'][0],'select 99')}):
            with self.assertRaisesRegex(ValueError,'Exact native inline SQL absent'):
                source_preflight()
        with self.assertRaisesRegex(ValueError,'Undeclared fixture file type'):
            statement('missing_files',file_type="DataFiles';DROP TABLE x")
        with self.assertRaisesRegex(ValueError,'Undeclared fixture date'):
            statement('post_count',run_date='2026-06-08')

    def test_valid_nulls_and_duplicate_quirk_have_explicit_fixture_coverage(self):
        cases=fixture_cases()
        self.assertEqual(len(cases),4)
        for case in cases:
            for row in case['settings']:
                self.assertIsNotNone(row['Parameter']); self.assertIsNotNone(row['Value'])
            for row in case['files']:
                self.assertIsNotNone(row['Type']); self.assertIsNotNone(row['Exists'])
        self.assertIsNone(cases[0]['files'][1]['ResolvedPath'])
        self.assertFalse(cases[0]['files'][0]['Exists'])
        self.assertTrue(cases[0]['files'][1]['Exists'])
        self.assertEqual(cases[1]['settings'][0],cases[1]['settings'][1])
        self.assertEqual(len(cases[2]['settings']),3)
        self.assertEqual(cases[3]['settings'],[])

    def test_code_pins_cover_harness_and_actual_pure_producer(self):
        pins=code_pins()
        self.assertIn('mta/domain/complete_daily_fullkit.py',pins)
        self.assertIn('parity/verify_complete_daily_fullkit.py',pins)
        self.assertTrue(all(len(value)==64 for value in pins.values()))


if __name__=='__main__':
    unittest.main()
