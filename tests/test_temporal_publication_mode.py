"""Daily sources are explicit input; prepared serving work remains separate."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
import unittest
from django.test import override_settings
from mta.runtime.temporal import daily_sources_enabled


class DailySourceModeTests(unittest.TestCase):
    @override_settings(VF_MTA_DAILY_PUBLICATION=True)
    def test_explicit_disabled_profile_cannot_inherit_serving_mode(self):
        self.assertFalse(daily_sources_enabled({'daily_publication':False}))
        self.assertTrue(daily_sources_enabled({}))

    @override_settings(VF_MTA_DAILY_PUBLICATION=False)
    def test_explicit_sources_work_without_serving_flag(self):
        self.assertTrue(daily_sources_enabled({'daily_publication':True}))
        self.assertFalse(daily_sources_enabled({}))

    def test_ambiguous_configuration_is_rejected(self):
        for value in ('false', 'true', 0, 1, None):
            with self.assertRaisesRegex(ValueError, 'explicit boolean'):
                daily_sources_enabled({'daily_publication':value})
