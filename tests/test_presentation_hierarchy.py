"""Presentation-only metadata guards; these unit tests are not parity receipts."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import override_settings
from mta.presentation import hierarchy
from mta.presentation.context import Publication, scope


class HierarchyTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((Path(__file__).resolve().parents[1]/'baseline/presentation-hierarchy-v1.json').read_text())
        self.catalogue = {
            kind: dict(attributes=[dict(code=code, level_1='Root', level_2='Group', level_3='Leaf')],
                       records=[dict(id=1, level_1='Root', level_2=None, level_3=None),
                                dict(id=2, level_1='Root', level_2='Group', level_3='Leaf')])
            for kind, code in [('products', '337'), ('locations', 'AG515802')]}
        self.manifest['catalogue_counts'] = dict(products=1, locations=1)
        self.state = dict(SkuAttributeData=[dict(SKUCode='337', SL1=None, SL2=None, SL3=None, c1='existing')],
                          LocationAttributeData=[dict(WHCode='AG515802', LL1=None, LL2=None, LL3=None)],
                          Suggestions=[dict(SKUCode='337', NewNorm=220)])

    def test_only_six_fields_change_without_mutating_native_or_calculated_rows(self):
        before = deepcopy(self.state)
        output = dict(DBMFinal=[self.state], BTRFinal=[self.state], ClosingState=[dict(importer=self.state)])
        projected, dbm = hierarchy.project(output, self.state, self.catalogue, self.manifest)
        self.assertEqual(self.state, before)
        self.assertEqual(dbm['SkuAttributeData'][0]['c1'], 'existing')
        self.assertIs(dbm['Suggestions'], self.state['Suggestions'])
        self.assertIsNot(dbm['SkuAttributeData'][0], self.state['SkuAttributeData'][0])
        self.assertEqual(projected['BTRFinal'][0]['SkuAttributeData'][0]['SL1'], 'Root')
        self.assertIs(Publication(None, projected, dbm, output).storage_output, output)

    def test_canonical_null_denial_remains_without_opt_in(self):
        payload = dict(product_permissions=[1], location_permissions=[1])
        with patch('mta.presentation.context.permission_catalogue', return_value=self.catalogue):
            self.assertEqual(scope(payload, attributes=self.state), (set(), set()))
            enriched = hierarchy.project_attributes(self.state, self.catalogue, self.manifest)
            self.assertEqual(scope(payload, attributes=enriched), ({'337'}, {'AG515802'}))
            self.assertEqual(scope({**payload, 'product_permissions': []}, attributes=enriched)[0], set())

    def test_duplicate_native_occurrences_keep_permission_multiplicity(self):
        self.state['SkuAttributeData'] *= 2
        enriched = hierarchy.project_attributes(self.state, self.catalogue, self.manifest)
        self.assertEqual(len(enriched['SkuAttributeData']), 2)
        with patch('mta.presentation.context.permission_catalogue', return_value=self.catalogue):
            products, _ = scope(dict(product_permissions=[1], location_permissions=[1]), attributes=enriched)
            self.assertEqual(products.multiplicities['337'], 2)

    def test_unknown_entity_conflicting_native_and_duplicate_catalogue_fail_closed(self):
        for variant in ('unknown', 'conflict', 'duplicate'):
            state, catalogue = deepcopy(self.state), deepcopy(self.catalogue)
            if variant == 'unknown': state['SkuAttributeData'][0]['SKUCode'] = 'unregistered'
            elif variant == 'conflict': state['SkuAttributeData'][0]['SL1'] = 'another hierarchy'
            else: catalogue['products']['attributes'] *= 2
            with self.subTest(variant=variant), self.assertRaises(hierarchy.HierarchyUnavailable):
                hierarchy.project_attributes(state, catalogue, self.manifest)

    def test_manifest_exact_hash_run_date_digest_and_allowed_fields(self):
        binding = self.manifest['publications'][0]
        run = SimpleNamespace(pk=binding['run_id'], business_date=date.fromisoformat(binding['business_date']),
                              output_digest=binding['output_digest'])
        raw = json.dumps(self.manifest).encode()
        with override_settings(VF_MTA_HIERARCHY_FILE='approved.json',
                VF_MTA_HIERARCHY_SHA256=hashlib.sha256(raw).hexdigest(),
                VF_MTA_PERMISSIONS_SHA256=self.manifest['catalogue_sha256']), \
                patch.object(Path, 'read_bytes', return_value=raw):
            self.assertEqual(hierarchy.selected_manifest(run), self.manifest)
            for field, value in [('pk', 'different'), ('business_date', date(2026,6,16)), ('output_digest', 'different')]:
                changed = SimpleNamespace(**{**vars(run), field: value})
                with self.subTest(field=field), self.assertRaises(hierarchy.HierarchyUnavailable):
                    hierarchy.selected_manifest(changed)
            with override_settings(VF_MTA_HIERARCHY_SHA256='wrong'), self.assertRaises(hierarchy.HierarchyUnavailable):
                hierarchy.selected_manifest(run)
            self.manifest['allowed_fields']['products'].append('Weight')
            wrong = json.dumps(self.manifest).encode()
            with patch.object(Path, 'read_bytes', return_value=wrong), \
                    override_settings(VF_MTA_HIERARCHY_SHA256=hashlib.sha256(wrong).hexdigest()), \
                    self.assertRaises(hierarchy.HierarchyUnavailable):
                hierarchy.selected_manifest(run)

    def test_absent_supplement_leaves_native_objects_unchanged(self):
        with override_settings(VF_MTA_HIERARCHY_FILE='', VF_MTA_HIERARCHY_SHA256=''):
            self.assertIsNone(hierarchy.selected_manifest(None))
        output, dbm = hierarchy.project(self.state, self.state, {}, None)
        self.assertIs(output, self.state)
        self.assertIs(dbm, self.state)


if __name__ == '__main__': unittest.main()
