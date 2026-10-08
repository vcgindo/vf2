"""No SQL: ownership and lossless full-cell qualification helper checks."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import re
from unittest.mock import patch
import unittest

from parity.verify_complete_daily_producers import (
    OWNER, OUTPUT_ROOT, SOURCE, FixtureSQL, compare_rows, fixture_cases, guard_options,
    implementation_pins, preflight_fixture_suite)


class QualificationHelperTests(unittest.TestCase):
    def test_standalone_completion_adapters_never_probe_sql(self):
        from mta.domain import complete_daily_scalars as scalars
        from parity.verify_complete_daily_completion import callbacks, implementation_pins as completion_pins
        from parity.verify_complete_daily_producers import NATIVE_COLLATION
        class NoNativeProbes:
            def execute(self, *args):
                raise AssertionError('Modern adapters must not execute native SQL')
        class Schema:
            def schema(self, role, table):
                fields = ['ScriptName', 'ModuleName'] if table == 'ScriptExecutedFlag' else ['Parameter']
                return [dict(name=field, collation=NATIVE_COLLATION) for field in fields]
        probes = []
        self.assertEqual(callbacks(NoNativeProbes(), Schema(), probes),
                         (scalars.ascii_equal, scalars.parse_datetime, scalars.datetime_to_nvarchar))
        self.assertEqual(probes, [])
        self.assertIn('parity/verify_complete_daily_completion.py', completion_pins())
        self.assertIn('mta/domain/complete_daily_scalars.py', completion_pins())

    def test_context_rejects_unqualified_language_or_collation(self):
        from parity.verify_complete_daily_producers import native_context, NATIVE_COLLATION
        class Raw:
            def execute(self, *args):
                return self
            def fetchone(self):
                return ('British', NATIVE_COLLATION)
        class Isolation:
            MAPPING = {}
        with self.assertRaisesRegex(ValueError, 'language/collation'):
            native_context(Raw(), Isolation())

    def test_preflight_rejects_later_null_before_any_loader_mutation(self):
        columns = [dict(name='DispatchColor', type_name='nvarchar', nullable=False,
                        identity=False, computed=False, max_length=20, precision=0, scale=0)]
        class ReadOnlySchema:
            def schema(self, role, table):
                if table == 'GulfOil_TechColorData':
                    return [dict(columns[0], name=name, nullable=True, max_length=100,
                                 type_name='date' if name == 'ReportDate' else 'nvarchar')
                            for name in ('ReportDate', 'SKUCode', 'WhCode', 'TechColor')]
                return columns
            def fill(self, column):
                return None, 'explicit unused NULL'
            def load(self, *args):
                raise AssertionError('preflight must never mutate')
        cases = [('later-case', 'BPR', 'canonical.sql',
                  {('BPR', 'BORWithOrderAllocation'): [dict(DispatchColor=None)]})]
        report = preflight_fixture_suite(ReadOnlySchema(), cases)
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(any('NOT NULL' in e['failure'] for e in report['errors']))
        cases[0][3][('BPR', 'BORWithOrderAllocation')] = []
        # Empty population still validates its schema; it cannot insert NULL.
        report = preflight_fixture_suite(ReadOnlySchema(), cases)
        self.assertEqual(report['status'], 'PASS')
        self.assertTrue(any(p['table'] == 'BORWithOrderAllocation' and p['rows'] == []
                            for p in report['populations']))

    def test_missing_bor_row_exercises_null_join_without_impossible_stored_null(self):
        declared = fixture_cases()[2][3]
        bor = declared[('BPR', 'BORWithOrderAllocation')]
        self.assertFalse(any(r['SKUCode'] == 'FG' for r in bor))
        self.assertTrue(all(r['DispatchColor'] is not None for r in bor))
        source = (SOURCE / 'Scripts/DBCreation/BPR_DBCreation.sql').read_text(encoding='cp1252')
        match = re.search(r'CREATE TABLE \[dbo\]\.\[BORWithOrderAllocation\]\((.*?)\)\s*ON', source, re.S)
        self.assertRegex(match[1], r'\[DispatchColor\].*NOT NULL')

    def test_receipt_pins_bind_actual_modern_modules_and_harness(self):
        pins = implementation_pins()
        self.assertIn('mta/domain/complete_daily_bpr.py', pins)
        self.assertIn('mta/domain/complete_daily_scalars.py', pins)
        self.assertIn('mta/domain/complete_daily_btr.py', pins)
        self.assertIn('parity/verify_complete_daily_producers.py', pins)
        self.assertTrue(all(re.fullmatch('[0-9a-f]{64}', digest) for digest in pins.values()))

    def test_production_color_fixture_uses_actual_owner_columns(self):
        source = (SOURCE / 'Scripts/DBCreation/BPR_DBCreation.sql').read_text(encoding='cp1252')
        declared = fixture_cases()[1][3]
        for table in ('SupplierDispatchReq', 'vf_RationedReqReport'):
            match = re.search(r'CREATE TABLE \[dbo\]\.\[' + table + r'\]\((.*?)\)\s*ON', source, re.S)
            self.assertIsNotNone(match)
            columns = {name.casefold() for name in re.findall(r'^\s*\[([^]]+)\]', match[1], re.M)}
            for row in declared[('BPR', table)]:
                self.assertLessEqual({name.casefold() for name in row}, columns)
        colors = {'ReqTopOfRed', 'ReqTopOfYellow', 'ReqTopOfGreen'}
        self.assertTrue(colors <= set(declared[('BPR', 'SupplierDispatchReq')][0]))
        self.assertTrue(colors.isdisjoint(declared[('BPR', 'vf_RationedReqReport')][0]))

    def test_exact_owner_output_boundary_and_overwrite_denial(self):
        with self.assertRaisesRegex(ValueError, 'explicitly approved'):
            guard_options('complete-daily-production-001', OUTPUT_ROOT / 'test.json')
        with self.assertRaisesRegex(ValueError, 'approved evidence directory'):
            guard_options(OWNER, Path('F:/freshvcf/test.json'))
        with patch.object(Path, 'exists', return_value=True):
            with self.assertRaises(FileExistsError):
                guard_options(OWNER, OUTPUT_ROOT / 'test.json')

    def test_typed_multiset_retains_null_duplicates_and_full_fields(self):
        columns = [dict(name='SKUCode', type_name='nvarchar'), dict(name='Qty', type_name='int'),
                   dict(name='ReportDate', type_name='date')]
        rows = [dict(SKUCode='S', Qty=None, ReportDate=date(2026, 6, 6))] * 2
        modern = [dict(SKUCode='S', Qty=None, ReportDate='2026-06-06')] * 2
        report = compare_rows(rows, modern, columns)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['native_duplicates'][0]['count'], 2)
        self.assertEqual(compare_rows(rows, modern[:1], columns)['status'], 'FAIL')
        wrong = [dict(SKUCode='S', Qty=0, ReportDate='2026-06-06')] * 2
        self.assertEqual(compare_rows(rows, wrong, columns)['status'], 'FAIL')
        wrong = [dict(SKUCode='s', Qty=None, ReportDate='2026-06-06')] * 2
        self.assertEqual(compare_rows(rows, wrong, columns)['status'], 'FAIL')
        with self.assertRaisesRegex(ValueError, 'column roster'):
            compare_rows(rows, [dict(SKUCode='S', Qty=None)], columns)

    def test_values_types_and_decimal_scales_are_not_relaxed(self):
        columns = [dict(name='Qty', type_name='decimal')]
        self.assertEqual(compare_rows([dict(Qty=Decimal('1.000'))], [dict(Qty=1)], columns)['status'], 'FAIL')
        self.assertEqual(compare_rows([dict(Qty=Decimal('1.000'))], [dict(Qty=Decimal('1.00'))], columns)['status'], 'FAIL')

    def test_declared_cases_cover_native_null_duplicate_cap_and_history(self):
        cases = fixture_cases()
        self.assertEqual(len(cases), 3)
        post = cases[0][3]
        self.assertTrue(any(r['ParentPackSize'] is None for r in post[('BPR', 'vf_PickListReport')]))
        self.assertTrue(any(r['ParentStockForRationing'] == 2 for r in post[('BPR', 'vf_PickListReport')]))
        production = cases[1][3]
        self.assertEqual(len(production[('BPR', 'Plants')]), 2)
        self.assertIsNone(production[('BPR', 'DailyConsumption')][0]['Stock'])
        btr = cases[2][3]
        self.assertTrue(btr[('Interface', 'FGTrendData')])
        self.assertTrue(any(r['SKUCode'] == 'FGROUND' for r in btr[('BPR', 'vf_ReqCalculation')]))


if __name__ == '__main__':
    unittest.main()
