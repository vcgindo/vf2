"""Daily intake selects persisted predecessor metadata without replaying days."""
from datetime import date
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.runtime.day_opening import latest_predecessor
from mta.runtime.daily_feed import predecessor


class DayOpeningTests(unittest.TestCase):
    def test_no_candidate_has_no_predecessor(self):
        self.assertIsNone(latest_predecessor([]))

    def test_latest_persisted_date_survives_a_calendar_gap(self):
        older = SimpleNamespace(business_date=date(2026, 10, 18))
        latest = SimpleNamespace(business_date=date(2026, 10, 21))
        self.assertIs(latest_predecessor([older, latest]), latest)
        self.assertIs(latest_predecessor([latest, older]), latest)

    def test_duplicate_latest_date_rejects_instead_of_breaking_tie(self):
        older = SimpleNamespace(business_date=date(2026, 10, 18))
        latest = SimpleNamespace(business_date=date(2026, 10, 21))
        duplicate = SimpleNamespace(business_date=latest.business_date)
        with self.assertRaisesRegex(ValueError, 'unique.*latest'):
            latest_predecessor([latest, older, duplicate])

    def test_duplicate_older_date_does_not_make_latest_ambiguous(self):
        older = SimpleNamespace(business_date=date(2026, 10, 18))
        latest = SimpleNamespace(business_date=date(2026, 10, 21))
        self.assertIs(latest_predecessor([older, older, latest]), latest)

    def query(self, rows):
        manager = Mock()
        ordered = manager.filter.return_value.order_by.return_value
        ordered.__getitem__ = Mock(return_value=rows)
        return manager, ordered

    def test_first_and_any_other_date_without_predecessor_return_none(self):
        owner = SimpleNamespace(source=object(), opening_date=date(2026, 10, 17))
        for business_date in ('2026-10-18', '2026-10-30', '2026-10-16'):
            with self.subTest(business_date=business_date):
                manager, ordered = self.query([])
                with patch('mta.runtime.daily_feed.CalculationRun.objects', manager):
                    self.assertIsNone(predecessor(owner, business_date))
                manager.filter.assert_called_once_with(
                    kind='DAILY_CHAIN', status='SUCCEEDED',
                    business_date__lt=date.fromisoformat(business_date),
                    mdm_input_capture__source=owner.source)
                manager.filter.return_value.order_by.assert_called_once_with('-business_date')
                ordered.__getitem__.assert_called_once_with(slice(None, 2))

    def test_adapter_selects_prior_persisted_run_using_only_metadata(self):
        # These objects deliberately expose no calculations, history or outputs.
        owner = SimpleNamespace(source=object())
        latest = SimpleNamespace(business_date=date(2026, 10, 21))
        older = SimpleNamespace(business_date=date(2026, 10, 18))
        manager, _ = self.query([latest, older])
        with patch('mta.runtime.daily_feed.CalculationRun.objects', manager), \
                patch('mta.planning.engine.calculate_current_day') as calculate, \
                patch('mta.runtime.services.read_outputs') as read_outputs, \
                patch('mta.application.daily_finalization.verify_successor') as verify_successor:
            self.assertIs(predecessor(owner, '2026-10-30'), latest)
        calculate.assert_not_called()
        read_outputs.assert_not_called()
        verify_successor.assert_not_called()
        manager.filter.assert_called_once_with(
            kind='DAILY_CHAIN', status='SUCCEEDED', business_date__lt=date(2026, 10, 30),
            mdm_input_capture__source=owner.source)

    def test_adapter_rejects_same_latest_date_ambiguity(self):
        owner = SimpleNamespace(source=object())
        manager, _ = self.query([
            SimpleNamespace(business_date=date(2026, 10, 21)),
            SimpleNamespace(business_date=date(2026, 10, 21))])
        with patch('mta.runtime.daily_feed.CalculationRun.objects', manager):
            with self.assertRaisesRegex(ValueError, 'unique.*latest'):
                predecessor(owner, '2026-10-30')
