"""Staging-only source isolation, ownership and finite edge coverage checks."""
import ast
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch
from parity.verify_complete_daily_gulfoil_reports import (
    extract_functions, fixtures, code_pins, guard_options, OWNER, OUTPUT_ROOT, FUNCTIONS, SOURCE)
from mta.application.complete_daily_gulfoil_reports import TARGET


class GulfOilQualificationTests(unittest.TestCase):
    def test_only_three_function_definitions_are_compiled(self):
        code,roster=extract_functions()
        self.assertEqual([r['name'] for r in roster],list(FUNCTIONS))
        self.assertNotIn('DBConnect',code.co_names)
        self.assertNotIn('main',code.co_names)
        # Top-level canonical source remains unexecuted, including its call.
        self.assertEqual(code.co_names,FUNCTIONS)

    def test_declared_edges_preserve_native_date_order_and_tie_sequence(self):
        cases=dict(fixtures(date(2026,10,8)))
        self.assertEqual(cases['empty'],[])
        rows=cases['mixed']
        self.assertEqual([r['ReportDate'] for r in rows],sorted(r['ReportDate'] for r in rows))
        current=[r for r in rows if r['SKUCode']=='S' and r['ReportDate'].date()==date(2026,10,8)]
        self.assertEqual([r['Norm'] for r in current],[8,9])
        self.assertIsNone(current[0]['TechColor'])
        self.assertEqual(current[1]['TechColor'],'Red')
        self.assertTrue(any(r['VirtualNorm'] is None and r['SKUCode']=='OUTSIDE' for r in rows))
        self.assertTrue(any('\n' in r['ParentWhName'] for r in rows))
        self.assertTrue(any(r['SKUCode']=='AGE' for r in rows))
        self.assertEqual((cases['target-present'][0]['SKUCode'],cases['target-present'][0]['WHCode']),TARGET)

    def test_guard_refuses_unowned_output_or_overwrite(self):
        with self.assertRaisesRegex(ValueError,'approved owned'):
            guard_options('other',OUTPUT_ROOT/'proof.json')
        with self.assertRaisesRegex(ValueError,'Owned JSON'):
            guard_options(OWNER,Path('F:/freshvcf/proof.json'))
        with patch.object(Path,'exists',return_value=True):
            with self.assertRaises(FileExistsError):
                guard_options(OWNER,OUTPUT_ROOT/'proof.json')

    def test_actual_module_and_harness_hashes_recorded(self):
        pins=code_pins()
        self.assertEqual(len(pins),2)
        self.assertTrue(all(len(value)==64 for value in pins.values()))


if __name__=='__main__':
    unittest.main()
