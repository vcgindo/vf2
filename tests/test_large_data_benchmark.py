import hashlib
import unittest

from tools.large_data_benchmark import next_row


class SyntheticBenchmarkFactsTest(unittest.TestCase):
    def row(self, **changes):
        return dict(SKUCode='000337',WhCode='DP01',Stock=30,Consumption=9,
                    Receipts=5,GIT=None,PSO=0,ReportDate='2026-04-07',**changes)

    def test_conservation_without_changing_source(self):
        source=self.row()
        actual=next_row(source)
        self.assertEqual(actual['Stock'],26)
        self.assertEqual(actual['ReportDate'],'2026-04-08')
        self.assertEqual(source['Stock'],30)
        self.assertEqual(actual['SKUCode'],'000337')
        self.assertIsNone(actual['GIT'])

    def test_consumption_cannot_exceed_available_stock(self):
        source=self.row();source.update(Stock=3,Consumption=100,Receipts=2)
        actual=next_row(source)
        self.assertEqual((actual['Consumption'],actual['Stock']),(5,0))

    def test_unknown_stock_and_absent_flows_stay_null(self):
        source=self.row();source.update(Stock=None,Consumption=None,Receipts=None)
        actual=next_row(source)
        for name in ('Stock','Consumption','Receipts','GIT'):
            self.assertIsNone(actual[name])

    def test_missing_flow_cells_are_preserved_in_known_stock_balance(self):
        source=self.row();source.update(Consumption=None,Receipts=None)
        actual=next_row(source)
        self.assertEqual(actual['Stock'],30)
        self.assertIsNone(actual['Consumption'])
        self.assertIsNone(actual['Receipts'])


class ApprovedLegacyVariantTest(unittest.TestCase):
    path = 'Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql'

    def setUp(self):
        self.original = b'original SQL'
        self.variant = b'approved corrected SQL'
        self.pin = hashlib.sha256(self.original).hexdigest()
        self.approval = dict(decision='APPROVE_ISOLATED_LEGACY_CORRECTION_AND_ONE_RERUN',
            canonical_sha256=self.pin, proposed_sha256=hashlib.sha256(self.variant).hexdigest())

    def validate(self, raw, *, path=None, original=None, approval=None):
        from tools.large_data_legacy_sqlcmd import validate_source
        return validate_source(raw, original or self.original, self.pin, path or self.path, approval)

    def test_unchanged_canonical_bytes_need_no_exception(self):
        self.assertFalse(self.validate(self.original))

    def test_only_exact_approved_variant_is_accepted(self):
        self.assertTrue(self.validate(self.variant, approval=self.approval))
        for variant in (b'unapproved SQL', self.variant+b' extra edit'):
            with self.assertRaises(ValueError):
                self.validate(variant, approval=self.approval)

    def test_approval_does_not_apply_to_another_producer(self):
        with self.assertRaises(ValueError):
            self.validate(self.variant, path='Scripts/DBM/Calculate.sql', approval=self.approval)

    def test_unapproved_variant_and_changed_original_pin_are_denied(self):
        with self.assertRaises(ValueError):
            self.validate(self.variant)
        with self.assertRaises(ValueError):
            self.validate(self.variant, original=b'changed canonical SQL', approval=self.approval)

    def test_native_unicode_error_result_is_readable_with_or_without_bom(self):
        from tools.large_data_legacy_sqlcmd import decode_output
        text = 'ERROR ErrorNumber ErrorSeverity\r\nArithmetic overflow'
        for encoding in ('utf-8', 'utf-16', 'utf-16-le'):
            self.assertEqual(decode_output(text.encode(encoding)), text)


if __name__=='__main__':
    unittest.main()
