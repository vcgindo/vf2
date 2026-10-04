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
    def test_ambiguous_sources_and_permission_bags_keep_accepted_reader(self):
        singleton = PermissionCodes({'sku': 1})
        repeated = PermissionCodes({'sku': 2})
        self.assertFalse(reporting.eligible_request(None, singleton, singleton))
        self.assertFalse(reporting.eligible_request(SimpleNamespace(eligible=False), singleton, singleton))
        self.assertFalse(reporting.eligible_request(SimpleNamespace(eligible=True), repeated, singleton))
        self.assertFalse(reporting.eligible_request(SimpleNamespace(eligible=True), singleton, repeated))
        self.assertTrue(reporting.eligible_request(SimpleNamespace(eligible=True), singleton, singleton))

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
