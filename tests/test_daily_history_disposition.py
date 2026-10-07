import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from django.test import override_settings
from mta.presentation.context import PublicationUnavailable
from mta.presentation.daily_history_disposition import guard, VERSION, REASON


class HistoryDispositionTests(unittest.TestCase):
    @override_settings(VF_MTA_GUIDED_EXCESS_DISPOSITION='')
    def test_default_has_no_effect_or_database_access(self):
        with patch('mta.presentation.daily_history_disposition.connection') as db:
            guard(SimpleNamespace(kind='DAILY_CHAIN'), 'excess-sku')
            db.cursor.assert_not_called()

    @override_settings(VF_MTA_GUIDED_EXCESS_DISPOSITION=VERSION,
                       VF_MTA_SYNTHETIC_ROSTER='core-without-bor-v1')
    def test_exact_demo_denies_both_history_routes(self):
        with patch('mta.presentation.daily_history_disposition.connection') as db:
            db.cursor.return_value.__enter__.return_value.fetchone.return_value=('daily_3006',)
            for kind in ('excess-sku','excess-value'):
                with self.assertRaisesRegex(PublicationUnavailable, REASON):
                    guard(SimpleNamespace(kind='DAILY_CHAIN'),kind)
            guard(SimpleNamespace(kind='DAILY_CHAIN'),'availability-trend')

    @override_settings(VF_MTA_GUIDED_EXCESS_DISPOSITION=VERSION,
                       VF_MTA_SYNTHETIC_ROSTER='core-without-bor-v1')
    def test_other_database_and_fixture_cannot_adopt_disposition(self):
        with patch('mta.presentation.daily_history_disposition.connection') as db:
            db.cursor.return_value.__enter__.return_value.fetchone.return_value=('other',)
            with self.assertRaisesRegex(PublicationUnavailable,'owned_database_required'):
                guard(SimpleNamespace(kind='DAILY_CHAIN'),'excess-value')
            with self.assertRaisesRegex(PublicationUnavailable,'scope_mismatch'):
                guard(SimpleNamespace(kind='LEGACY_UI_FIXTURE'),'excess-value')

    @override_settings(VF_MTA_GUIDED_EXCESS_DISPOSITION=VERSION,
                       VF_MTA_SYNTHETIC_ROSTER='')
    def test_default_roster_cannot_adopt_disposition(self):
        with self.assertRaisesRegex(PublicationUnavailable,'scope_mismatch'):
            guard(SimpleNamespace(kind='DAILY_CHAIN'),'excess-sku')
