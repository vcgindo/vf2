"""Focused schema and input-boundary checks for typed RRR colour storage."""
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault('VF_SECRET_KEY', 'daily-rrr-storage-unit-test')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.presentation.daily_rrr_colour import OUTPUT_FIELDS
from mta.presentation.daily_rrr_storage import APPROVED_OUTPUTS, VERSION
from development.daily_rrr_storage import _proof_rows, _source_inputs
from mta.runtime.daily_rrr_models import DailyRrrColourReceipt, DailyRrrColourRow


class DailyRrrStorageTests(unittest.TestCase):
    def source_run(self):
        run_id = '17f0eb84-7b6d-40e9-a288-9441a4d7a860'
        return SimpleNamespace(pk=run_id, output_digest=APPROVED_OUTPUTS[run_id])

    def report(self):
        return dict(SKUCode='6120', WhCode='LP001', ParentWhCode='LDC001',
            Req=83, Norm=339, VirtualNorm=339, Stock=254, GIT=2,
            LeftoverParentStock=58, NormReq=83, AllocatedForVirtualNormReq=83,
            ParentPackSize=1, DispatchColor='Green')

    def band(self, **changes):
        row = dict(sku_code='6120', location_code='LP001',
            parent_location_code='LDC001', norm_req_black='0', norm_req_red='0',
            norm_req_yellow='0', norm_req_green='83', order_req_black='0',
            order_req_red='0', order_req_yellow='0', order_req_green='0',
            order_req_blue='0')
        row.update(changes)
        return row

    def calculated(self, **changes):
        values = dict(r1_requirement_band=[self.band()],
            r1_advance_stock_allocation=[], r1_order_route=[], r1_order_bpp=[])
        values.update(changes)
        return [dict(capability=name, rows=rows) for name, rows in values.items()]

    def output(self):
        return dict(BPRFinal=[{'vf_RationedReqReport': [self.report()]}],
            ClosingState=[{'bpr': {'BPRMaster': [
                {'SKUCode': '6120', 'WHCode': 'LDC001'}]}}])

    def test_exact_native_model_shape_and_nullability(self):
        fields = {field.name: field for field in DailyRrrColourRow._meta.fields}
        self.assertEqual(tuple(name for name in OUTPUT_FIELDS if name not in fields), ())
        self.assertEqual(fields['SKUCode'].max_length, 50)
        self.assertEqual(fields['AllocationFor'].max_length, 10)
        self.assertEqual(fields['DispatchColor'].max_length, 10)
        nullable = {'AllocationFor', 'Norm', 'VirtualNorm', 'Stock', 'GIT',
            'LeftoverParentStock', 'Requirement', 'RationedQty',
            'RationedCasePacks', 'DispatchColor'}
        self.assertEqual({name for name in OUTPUT_FIELDS if fields[name].null}, nullable)
        self.assertEqual(DailyRrrColourReceipt._meta.db_table,
                         'fresh_mta_dailyrrrcolourreceipt')
        self.assertEqual(DailyRrrColourRow._meta.db_table,
                         'fresh_mta_dailyrrrcolourrow')

    def test_stage_sources_produce_complete_typed_row_and_digest(self):
        rows, source_digest = _source_inputs(self.source_run(), self.output(), self.calculated())
        self.assertEqual(len(rows), 1)
        self.assertEqual(tuple(rows[0]), OUTPUT_FIELDS)
        self.assertEqual(rows[0]['RationedCasePacks'], 83)
        self.assertEqual(rows[0]['TOGreen_AllocQty'], 83)
        self.assertEqual(len(source_digest), 64)
        self.assertEqual(VERSION, 'daily-rrr-colour-smoke-v1')
        relational = self.output()
        relational['BPRReports'] = relational.pop('BPRFinal')
        self.assertEqual(_source_inputs(self.source_run(), relational, self.calculated()),
                         (rows, source_digest))

    def test_missing_duplicate_or_nonempty_order_capability_is_denied(self):
        calculated = self.calculated()
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            _source_inputs(self.source_run(), self.output(), calculated[:-1])
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            _source_inputs(self.source_run(), self.output(), calculated + [calculated[0]])
        with self.assertRaisesRegex(ValueError, 'non-empty order inputs'):
            _source_inputs(self.source_run(), self.output(),
                self.calculated(r1_order_route=[{'order_id': 'O'}]))
        with self.assertRaisesRegex(ValueError, 'order requirements'):
            _source_inputs(self.source_run(), self.output(),
                self.calculated(r1_requirement_band=[self.band(order_req_red='1')]))

    def test_only_native_case_pack_wire_representation_is_normalized(self):
        rows, _ = _source_inputs(self.source_run(), self.output(), self.calculated())
        proof = dict(rows[0], RationedCasePacks='83')
        self.assertEqual(_proof_rows([proof]), rows)
        with self.assertRaisesRegex(ValueError, 'case-pack representation'):
            _proof_rows([dict(proof, RationedCasePacks='83.0')])


if __name__ == '__main__':
    unittest.main()
