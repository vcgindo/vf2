"""Real hierarchy projection and scope joins, without commands or state mutation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from django.test import SimpleTestCase, override_settings
from mta.presentation import hierarchy, preacceptance_actions as phase
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


class PreacceptanceHierarchyTests(SimpleTestCase):
    def setUp(self):
        self.directory=TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        root=Path(self.directory.name)
        record=lambda pk,level2=None,level3=None:dict(id=pk,level_1='G',level_2=level2,level_3=level3)
        attribute=lambda code:dict(code=code,level_1='G',level_2=code,level_3='Leaf')
        catalogue=dict(version='block1-permissions-v1',
            products=dict(records=[record(1),record(4,'SKU','Leaf')],attributes=[attribute('SKU')]),
            locations=dict(records=[record(2),record(3,'L2'),record(5,'L1','Leaf'),record(6,'L2','Leaf')],attributes=[attribute('L1'),attribute('L2')]))
        self.run=SimpleNamespace(pk='bound-run',business_date='2026-06-06',output_digest='d'*64)
        def write(name,value):
            path=root/name;path.write_text(json.dumps(value),encoding='utf-8')
            return str(path),hashlib.sha256(path.read_bytes()).hexdigest()
        permissions,permission_sha=write('permissions.json',catalogue)
        manifest=dict(version='fresh-presentation-hierarchy-v1',role='presentation-only-retained-hierarchy',
            allowed_fields=hierarchy.FIELDS,catalogue_sha256=permission_sha,
            catalogue_counts=dict(products=1,locations=2),publications=[dict(run_id='bound-run',business_date='2026-06-06',output_digest='d'*64)])
        path,sha=write('hierarchy.json',manifest)
        self.settings=dict(VF_MTA_PERMISSIONS_FILE=permissions,VF_MTA_PERMISSIONS_SHA256=permission_sha,
            VF_MTA_HIERARCHY_FILE=path,VF_MTA_HIERARCHY_SHA256=sha)
        self.access=dict(product_permissions=[1],location_permissions=[2],permissions_sha256=permission_sha,hierarchy_sha256=sha)
        self.output={'ClosingState':[{'importer':dict(
            SkuAttributeData=[dict(SKUCode='SKU',SL1=None,SL2=None,SL3=None)],
            LocationAttributeData=[dict(WHCode=x,LL1=None,LL2=None,LL3=None) for x in ('L1','L1','L2')])}]}

    def test_approved_projection_scopes_without_mutating_native_rows(self):
        original=deepcopy(self.output);original_digest=digest(self.output)
        with override_settings(**self.settings):
            _,products,locations=phase._access(self.run,self.access,self.output)
            self.assertEqual(products,{'SKU'});self.assertEqual(locations,{'L1','L2'})
            projected=phase._scope_output(self.run,self.output)
            self.assertEqual([r['WHCode'] for r in projected['ClosingState'][0]['importer']['LocationAttributeData']],['L1','L1','L2'])
            restricted={**self.access,'location_permissions':[3]}
            _,_,locations=phase._access(self.run,restricted,self.output)
            self.assertEqual(locations,{'L2'});self.assertNotIn('L1',locations)
        self.assertEqual(self.output,original);self.assertEqual(digest(self.output),original_digest)

    def test_wrong_run_hash_unknown_permission_and_conflicting_native_deny(self):
        with override_settings(**self.settings):
            with self.assertRaisesRegex(hierarchy.HierarchyUnavailable,'scope_mismatch'):
                phase._scope_output(SimpleNamespace(pk='other',business_date=self.run.business_date,output_digest=self.run.output_digest),self.output)
            with self.assertRaisesRegex(PublicationUnavailable,'permission_hierarchy_unavailable'):
                phase._access(self.run,{**self.access,'location_permissions':[999]},self.output)
            changed=deepcopy(self.output);changed['ClosingState'][0]['importer']['SkuAttributeData'][0]['SL1']='Conflict'
            with self.assertRaisesRegex(hierarchy.HierarchyUnavailable,'conflicts'):
                phase._scope_output(self.run,changed)
        with override_settings(**{**self.settings,'VF_MTA_HIERARCHY_SHA256':'0'*64}):
            with self.assertRaisesRegex(hierarchy.HierarchyUnavailable,'hash_mismatch'):
                phase._scope_output(self.run,self.output)

    def test_absent_hierarchy_cannot_bypass_native_null_scope(self):
        with override_settings(**{**self.settings,'VF_MTA_HIERARCHY_FILE':'','VF_MTA_HIERARCHY_SHA256':''}):
            with self.assertRaisesRegex(phase.PreacceptanceDenied,'hierarchy_required'):
                phase._scope_output(self.run,self.output)
