"""April retained requests are admitted only for their exact sealed fixture."""
import os
import json
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
        self.source=json.loads(subject.SOURCE.read_bytes())
        self.run=SimpleNamespace(pk=self.source['run_id'],kind='LEGACY_UI_FIXTURE',business_date='2026-04-07')

    def test_exact_source_passes_but_drift_is_denied(self):
        with patch.object(subject.fixture,'binding',return_value=(self.run,self.source['fixture_source_digest'])) as binding, \
                patch.object(subject.fixture,'policy',return_value={'manifest_sha256':self.source['manifest_sha256']}):
            self.assertEqual(subject.empty_requests(self.run),[])
            binding.return_value=(self.run,'changed')
            with self.assertRaisesRegex(PublicationUnavailable,'wrong_fixture'):subject.empty_requests(self.run)

    def test_other_day_or_kind_does_not_inherit_empty_source(self):
        with patch.object(subject.fixture,'binding',return_value=(self.run,self.source['fixture_source_digest'])):
            for kind,day in [('DAILY_CHAIN','2026-04-07'),('LEGACY_UI_FIXTURE','2026-06-17')]:
                with self.assertRaisesRegex(PublicationUnavailable,'wrong_fixture'):
                    subject.empty_requests(SimpleNamespace(pk=self.run.pk,kind=kind,business_date=day))

    def test_changed_or_missing_source_denied(self):
        with patch.object(subject.fixture,'binding',return_value=(self.run,self.source['fixture_source_digest'])), \
                patch.object(subject,'SOURCE') as source:
            source.read_bytes.return_value=b'{}'
            with self.assertRaisesRegex(PublicationUnavailable,'missing_or_changed'):subject.empty_requests(self.run)
            source.read_bytes.side_effect=FileNotFoundError()
            with self.assertRaisesRegex(PublicationUnavailable,'missing_or_changed'):subject.empty_requests(self.run)

    def test_fixture_child_route_preserves_norm_denial_and_uses_prepared_reader(self):
        from mta.presentation import expedite_read
        with patch.object(expedite_read,'selected_run',return_value=self.run), \
                patch.object(expedite_read,'expedite_context') as context, \
                patch('mta.presentation.planning_expedite_sql.child_grid',return_value={'data':'prepared'}) as reader:
            self.assertEqual(expedite_read.child_grid({'filters':{}}),{'data':'prepared'})
            context.assert_not_called()
            with self.assertRaisesRegex(PublicationUnavailable,'norm_filter_contract_unverified'):
                expedite_read.child_grid({'filters':{'availabilityFilter':{'filters':[{'attributeName':'norm'}]}}})
            self.assertEqual(reader.call_count,1)
