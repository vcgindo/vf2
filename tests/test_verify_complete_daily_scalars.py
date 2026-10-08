"""Focused scalar proof mechanics; no SQL or business-day invocation."""
import unittest

from parity.verify_complete_daily_scalars import (
    ScalarProof, cell, code_pins, edge_corpus, read_only, registered_domain)


class Cursor:
    description = [('Value',)]
    def __init__(self, value):
        self.value = value
    def fetchall(self):
        return [(self.value,)]


class ReadOnlyDouble:
    def __init__(self):
        self.calls = []
    def execute(self, sql, parameters):
        read_only(sql)
        self.calls.append((sql, parameters))
        return Cursor(parameters[0])


class ScalarProofHelperTests(unittest.TestCase):
    def test_mutation_queries_are_rejected_before_execution(self):
        for sql in ('UPDATE dbo.X SET V=1', 'SELECT * INTO dbo.X FROM dbo.Y',
                    'SELECT 1; DELETE FROM dbo.X', 'EXEC dbo.proc'):
            with self.assertRaisesRegex(ValueError, 'read-only'):
                read_only(sql)
        self.assertEqual(read_only('SELECT ROUND(CAST(? AS FLOAT),0)'), 'SELECT ROUND(CAST(? AS FLOAT),0)')

    def test_probe_cache_retains_signed_zero_and_typed_results(self):
        raw = ReadOnlyDouble()
        receipt = dict(queries=[], comparisons=[])
        proof = ScalarProof(raw, receipt)
        proof.compare('float', 'positive', 'SELECT ?', [0.0], lambda: 0.0)
        proof.compare('float', 'negative', 'SELECT ?', [-0.0], lambda: -0.0)
        proof.compare('float', 'positive-again', 'SELECT ?', [0.0], lambda: 0.0)
        self.assertEqual(len(raw.calls), 2)
        self.assertNotEqual(cell(0.0), cell(-0.0))
        self.assertNotEqual(cell(False), cell(0))

    def test_first_mismatch_retains_native_and_modern_cells(self):
        receipt = dict(queries=[], comparisons=[])
        proof = ScalarProof(ReadOnlyDouble(), receipt)
        with self.assertRaisesRegex(ValueError, 'First exact scalar mismatch'):
            proof.compare('float', 'fixture', 'SELECT ?', [1.0], lambda: 2.0)
        self.assertEqual(len(receipt['comparisons']), 1)
        self.assertEqual(receipt['comparisons'][0]['native'], cell(1.0))
        self.assertEqual(receipt['comparisons'][0]['modern'], cell(2.0))

    def test_python_failure_retains_exact_probe_and_error(self):
        receipt = dict(queries=[], comparisons=[])
        proof = ScalarProof(ReadOnlyDouble(), receipt)
        def fail():
            raise ValueError('unsupported input')
        with self.assertRaisesRegex(ValueError, 'First Python scalar failure'):
            proof.compare('parser', 'fixture', 'SELECT ?', ['x'], fail)
        self.assertEqual(receipt['comparisons'][0]['native'], ['text', 'x'])
        self.assertEqual(receipt['comparisons'][0]['modern_error']['message'], 'unsupported input')

    def test_registered_domain_preserves_all_actual_keys_and_null_raw_rows(self):
        domain = registered_domain()
        self.assertEqual(len(domain['sku_keys']), 200)
        self.assertEqual(len(domain['location_keys']), 20)
        self.assertEqual(len(domain['all_keys']), 220)
        self.assertEqual(len(domain['raw_percentages']), 1240)
        self.assertEqual(len(domain['actual_business_dates']), 21)
        self.assertTrue(all(r['SKULocAtt02'] is None for r in domain['raw_percentages']))
        self.assertEqual([r['ordinal'] for r in domain['raw_percentages']], list(range(1240)))

    def test_edge_corpus_keeps_midpoints_exponents_and_datetime_ticks(self):
        corpus = edge_corpus()
        for number in (123456.5, 123454.5, 1.234565, 999999.5, -2.5, .00009999995):
            self.assertIn(number, corpus['floats'])
        for value in ('invalid', '1e309', '1e-308'):
            self.assertIn(value, corpus['casts'])
        for value in ('2026-06-06T00:00:00.001', '2026-06-06T23:59:59.999'):
            self.assertIn(value, corpus['date_texts'])

    def test_hash_roster_binds_scalar_module_and_harness(self):
        pins = code_pins()
        self.assertIn('mta/domain/complete_daily_scalars.py', pins)
        self.assertIn('parity/verify_complete_daily_scalars.py', pins)
        self.assertTrue(all(len(value) == 64 for value in pins.values()))


if __name__ == '__main__':
    unittest.main()
