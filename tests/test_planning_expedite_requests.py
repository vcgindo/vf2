"""Current daily request source routing never falls back to a retained empty bag."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation import planning_expedite_requests as subject
from mta.presentation.context import PublicationUnavailable


class RequestAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.run=SimpleNamespace(pk='daily',kind='DAILY_CHAIN',business_date='2037-04-10')

    def test_daily_source_keeps_nonempty_and_explicit_empty_populations(self):
        from mta.presentation.daily_requests import FIELDS
        row=dict.fromkeys(FIELDS);row['Request']='captured'
        with patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch('mta.presentation.selective.image_rows',return_value=[row]) as image, \
                patch.object(subject,'SOURCE') as retained:
            self.assertEqual(subject.empty_requests(self.run),[row])
            image.assert_called_once_with(self.run,'sources/planning/OpenExpediteRequests')
            image.return_value=[]
            self.assertEqual(subject.empty_requests(self.run),[])
            retained.read_bytes.assert_not_called()

    def test_unsupported_branch_does_not_inherit_april_empty_source(self):
        with patch('mta.presentation.daily_preparation.production_branch',return_value=False), \
                patch('mta.presentation.selective.image_rows') as image,patch.object(subject,'SOURCE') as retained:
            for kind,day in [('DAILY_CHAIN','2026-04-07'),('LEGACY_UI_FIXTURE','2026-06-17')]:
                with self.assertRaisesRegex(PublicationUnavailable,'removed_historical_mode'):
                    subject.empty_requests(SimpleNamespace(pk=self.run.pk,kind=kind,business_date=day))
            image.assert_not_called();retained.read_bytes.assert_not_called()

    def test_missing_or_changed_daily_image_is_not_replaced_with_empty(self):
        with patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch('mta.presentation.selective.image_rows',side_effect=PublicationUnavailable('daily_image_missing_or_changed')), \
                patch.object(subject,'SOURCE') as retained:
            with self.assertRaisesRegex(PublicationUnavailable,'daily_image_missing_or_changed'):subject.empty_requests(self.run)
            retained.read_bytes.assert_not_called()

    def test_daily_child_route_preserves_norm_denial_and_uses_prepared_reader(self):
        from mta.presentation import expedite_read
        with patch.object(expedite_read,'selected_run',return_value=self.run), \
                patch('mta.presentation.daily_preparation.production_branch',return_value=True), \
                patch.object(expedite_read,'expedite_context') as context, \
                patch('mta.presentation.planning_expedite_sql.child_grid',return_value={'data':'prepared'}) as reader:
            self.assertEqual(expedite_read.child_grid({'filters':{}}),{'data':'prepared'})
            context.assert_not_called()
            with self.assertRaisesRegex(PublicationUnavailable,'norm_filter_contract_unverified'):
                expedite_read.child_grid({'filters':{'availabilityFilter':{'filters':[{'attributeName':'norm'}]}}})
            self.assertEqual(reader.call_count,1)

    def test_unqualified_dynamic_attribute_branch_is_still_denied(self):
        from mta.presentation import expedite_read
        with patch('mta.presentation.legacy_ui.BPR_UI_CONFIG',new=[dict(Visible=True,Col_Code='attr1')]), \
                patch('mta.presentation.planning_expedite_sql.child_grid') as reader:
            with self.assertRaisesRegex(PublicationUnavailable,'dynamic_attributes_not_connected'):
                expedite_read.child_grid(dict(filters={}))
            reader.assert_not_called()
