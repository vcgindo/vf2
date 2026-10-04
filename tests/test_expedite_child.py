"""Child contract branches distinct from the parent consumer."""
from datetime import date
import unittest
from mta.presentation.expedite_child import child_rows
from mta.presentation.permissions import PermissionCodes


class ChildGridTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(SKUCode='S', WhCode='W', ParentWhCode='P', Norm=10,
            VirtualNorm=10, Stock=0, GIT=0, PhysicalInventoryPen='100.00',
            PhysicalInventoryColor='Black', PipelineInventoryPen='100.00',
            PipelineInventoryColor='Red', Req=10, RationedQty=5, BRAge=2,
            ParentPipelineInventoryColor=None, RLT=3)
        self.imp = {name: [] for name in ('SKUDescriptionTbl', 'SiteDescriptionTbl',
            'SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData')}

    def read(self, **changes):
        args = dict(rows=[self.row], importer=self.imp, standards=[], products=None,
                    locations=None, paging=(1, 20), business_date=date(2026, 6, 17), requests=[], transit=[])
        args.update(changes)
        return child_rows(**args)

    def test_parent_scope_nulls_numeric_values_and_batch_eta(self):
        self.assertEqual(self.read(locations={'W'})['expediteDispatches'], [])
        row = self.read(locations={'P'})['expediteDispatches'][0]
        self.assertEqual((row['rn'], row['pip'], row['rtq']), (1, 100.0, 5))
        self.assertIsNone(row['sd'])
        self.assertIsNone(row['remark'])
        self.assertEqual(row['eta'], '2026-06-20T00:00:00')
        self.assertEqual(row['intransit'], '[]')
        self.assertIn('sl5', row)

    def test_availability_requires_inner_metadata_but_not_red_black(self):
        self.row.update(RationedQty=0, PipelineInventoryColor='Green')
        self.assertEqual(self.read()['createAvailabilityAtParent'], [])
        self.imp.update(SKUDescriptionTbl=[dict(SKUCode='S', SKUDescription='desc')],
            SiteDescriptionTbl=[dict(WHCode='W', WHDescription='child')],
            SkuAttributeData=[dict(SKUCode='S')], LocationAttributeData=[dict(WHCode='W')],
            SkuLocAttributeData=[dict(SKUCode='S', LocCode='W')])
        values = self.read(standards=[dict(SKUCode='S', WhCode='W')])['createAvailabilityAtParent']
        self.assertEqual(len(values), 1)
        self.assertIsNone(values[0]['pl'])

    def test_null_age_last_paging_and_permission_multiplicity(self):
        values = self.read(rows=[dict(self.row, BRAge=None, SKUCode='Z'), self.row], paging=None)['expediteDispatches']
        self.assertEqual([r['sc'] for r in values], ['S', 'Z'])
        values = self.read(products=PermissionCodes({'S': 3}), paging=(2, 2))['expediteDispatches']
        self.assertEqual([r['rn'] for r in values], [3])

    def test_unknown_history_and_ambiguous_ties_are_not_hidden(self):
        for field in ('requests', 'transit'):
            with self.assertRaisesRegex(ValueError, 'approved_empty'):
                self.read(**{field: None})
        self.imp['SKUDescriptionTbl'] = [dict(SKUCode='S', SKUDescription=x) for x in ('a', 'b')]
        with self.assertRaisesRegex(ValueError, 'ambiguous_row_number'):
            self.read()

    def test_preview_history_requires_opt_in_and_exact_publication(self):
        import os
        from types import SimpleNamespace
        from unittest.mock import patch
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'unit-test-only-not-a-serving-secret')
        import django
        django.setup()
        from django.test import override_settings
        from mta.presentation.context import PublicationUnavailable
        from mta.presentation.expedite_read import child_grid
        run = SimpleNamespace(pk='ac1612c8-0e49-4155-83c3-f59f41422293',
            business_date=date(2026, 6, 17),
            output_digest='bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d')
        with patch('mta.presentation.expedite_read.expedite_context', return_value=SimpleNamespace(run=run)), \
                patch('mta.presentation.expedite_read.selected_run', return_value=run):
            with override_settings(VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY=False):
                with self.assertRaisesRegex(PublicationUnavailable, 'history_not_admitted'):
                    child_grid({})
            for field, changed in (('pk', 'another-run'), ('business_date', date(2026, 6, 18)),
                                   ('output_digest', 'changed')):
                old = getattr(run, field)
                setattr(run, field, changed)
                with override_settings(VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY=True):
                    with self.assertRaisesRegex(PublicationUnavailable, 'history_not_admitted'):
                        child_grid({})
                setattr(run, field, old)


if __name__ == '__main__':
    unittest.main()
