"""Read selection and SQL owner rules; PostgreSQL lifecycle proof runs separately."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import override_settings
from mta.presentation import btr_reporting as reporting
from mta.presentation.context import PermissionCodes, PublicationUnavailable


class ReportingSelectionTests(unittest.TestCase):
    def test_complete_source_identity_and_generation_reject_every_image_change(self):
        from datetime import date
        from mta.serialization import digest
        run = SimpleNamespace(pk=uuid4(), kind='DAILY_CHAIN', business_date=date(2026,7,7),
                              input_digest='input', output_digest='output', production_digest='production')
        metadata = {path: {'image':path, 'count':i, 'fields':[['D1','D1','string']],
                          'rows_digest':'complete-'+str(i)}
                    for i,path in enumerate(reporting.SOURCES.values())}
        with patch.object(reporting, 'image_metadata', side_effect=lambda run,path:metadata[path]) as individual:
            original = reporting.source_identity(run,2)
            self.assertEqual([call.args[1] for call in individual.call_args_list], list(reporting.SOURCES.values()))
            self.assertEqual(original['images'], {role:metadata[path] for role,path in reporting.SOURCES.items()})
            generation = SimpleNamespace(run_id=run.pk, version=2, source_kind=run.kind,
                business_date=run.business_date, source_digest=digest(original))
            with override_settings(VF_BTR_REPORTING_GENERATION=str(uuid4())), \
                    patch.object(reporting.BtrReportingGeneration.objects, 'get', return_value=generation):
                self.assertIs(reporting.selected_generation(run), generation)
                for path in reporting.SOURCES.values():
                    before = metadata[path]
                    for changed in ({'count':999}, {'fields':[['D2','D2','string']]},
                                    {'rows_digest':'same-count-different-values'}):
                        with self.subTest(path=path, change=changed):
                            metadata[path] = before | changed
                            with self.assertRaisesRegex(PublicationUnavailable, 'source_mismatch'):
                                reporting.selected_generation(run)
                    metadata[path] = before
                individual.side_effect = PublicationUnavailable('binding_unavailable')
                with self.assertRaisesRegex(PublicationUnavailable, 'binding_unavailable'):
                    reporting.selected_generation(run)

    def test_ambiguous_sources_and_permission_bags_keep_accepted_reader(self):
        singleton = PermissionCodes({'sku': 1})
        repeated = PermissionCodes({'sku': 2})
        self.assertFalse(reporting.eligible_request(None, singleton, singleton))
        self.assertFalse(reporting.eligible_request(SimpleNamespace(version=reporting.VERSION, eligible=False), singleton, singleton))
        self.assertFalse(reporting.eligible_request(SimpleNamespace(version=reporting.VERSION, eligible=True), repeated, singleton))
        self.assertFalse(reporting.eligible_request(SimpleNamespace(version=reporting.VERSION, eligible=True), singleton, repeated))
        self.assertTrue(reporting.eligible_request(SimpleNamespace(version=reporting.VERSION, eligible=True), singleton, singleton))

    def test_unselected_reader_never_queries_reporting_tables(self):
        with override_settings(VF_BTR_REPORTING_GENERATION=''), patch.object(reporting.BtrReportingGeneration.objects, 'get') as get:
            self.assertIsNone(reporting.selected_generation(object()))
            get.assert_not_called()

    def test_wrong_run_and_unready_generation_fail_closed(self):
        run = SimpleNamespace(pk=uuid4())
        with override_settings(VF_BTR_REPORTING_GENERATION=str(uuid4())):
            with patch.object(reporting.BtrReportingGeneration.objects, 'get', side_effect=reporting.BtrReportingGeneration.DoesNotExist):
                with self.assertRaisesRegex(PublicationUnavailable, 'not_ready'):
                    reporting.selected_generation(run)
            with patch.object(reporting.BtrReportingGeneration.objects, 'get', return_value=SimpleNamespace(run_id=uuid4())):
                with self.assertRaisesRegex(PublicationUnavailable, 'source_mismatch'):
                    reporting.selected_generation(run)

    def test_reference_owner_selection_preserves_parent_inner_join(self):
        parent = ' JOIN la parent ON E."ParentWhCode"=parent."WHCode"'
        result = reporting.reference_from('B."Tags"', parent_join=parent)
        self.assertIn('LEFT JOIN E ON E.vf_ordinal=J.e_ordinal', result)
        self.assertIn('LEFT JOIN B ON B.vf_ordinal=J.b_ordinal', result)
        self.assertTrue(result.endswith(parent))
        self.assertNotIn('JOIN A ', result)
        self.assertNotIn('ORDER BY', result)
