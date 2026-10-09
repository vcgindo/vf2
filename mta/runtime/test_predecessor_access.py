"""Parent verification uses its existing binding and restores child settings."""
import hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from django.conf import settings
from django.test import SimpleTestCase,override_settings
from mta.presentation import hierarchy,operational_admission as op


class PredecessorAccessTests(SimpleTestCase):
    def test_two_distinct_bindings_and_denials(self):
        parent=SimpleNamespace(pk='parent',business_date='2026-06-06',output_digest='p'*64)
        child=SimpleNamespace(pk='child',business_date='2026-06-07',output_digest='c'*64,predecessor=parent)
        with TemporaryDirectory() as directory:
            paths={}; hashes={}
            for r in (parent,child):
                path=Path(directory)/(r.pk+'.json')
                value=dict(version='fresh-presentation-hierarchy-v1',role='presentation-only-retained-hierarchy',
                    allowed_fields=hierarchy.FIELDS,catalogue_sha256='catalogue',
                    publications=[dict(run_id=r.pk,business_date=r.business_date,output_digest=r.output_digest)])
                path.write_text(json.dumps(value));paths[r.pk]=str(path);hashes[r.pk]=hashlib.sha256(path.read_bytes()).hexdigest()
            receipt=SimpleNamespace(hierarchy_digest=hashes['parent'],permissions_digest='catalogue')
            with override_settings(VF_MTA_HIERARCHY_FILE=paths['child'],VF_MTA_HIERARCHY_SHA256=hashes['child'],
                VF_MTA_PERMISSIONS_SHA256='catalogue',VF_MTA_PREDECESSOR_HIERARCHY_FILE=paths['parent']), \
                patch('mta.runtime.models.OperationalAcceptance.objects.get',return_value=receipt), \
                patch('mta.presentation.daily_activation.access_manifest',side_effect=hierarchy.selected_manifest):
                with self.assertRaises(hierarchy.HierarchyUnavailable):hierarchy.selected_manifest(parent)
                with op.predecessor_access(child):
                    hierarchy.selected_manifest(parent)
                    with self.assertRaises(hierarchy.HierarchyUnavailable):hierarchy.selected_manifest(child)
                self.assertEqual(settings.VF_MTA_HIERARCHY_SHA256,hashes['child'])
                hierarchy.selected_manifest(child)
                for bad in ('', 'missing', paths['child']):
                    with override_settings(VF_MTA_PREDECESSOR_HIERARCHY_FILE=bad):
                        with self.assertRaises((op.PublicationUnavailable,hierarchy.HierarchyUnavailable)):
                            with op.predecessor_access(child):hierarchy.selected_manifest(parent)
                with override_settings(VF_MTA_PERMISSIONS_SHA256='changed'):
                    with self.assertRaises(op.PublicationUnavailable):
                        with op.predecessor_access(child):pass
                with self.assertRaisesRegex(RuntimeError,'probe'):
                    with op.predecessor_access(child):raise RuntimeError('probe')
                self.assertEqual(settings.VF_MTA_HIERARCHY_SHA256,hashes['child'])
