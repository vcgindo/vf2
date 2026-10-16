"""Native reports retain pinned configuration without fixture database tables."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.test import override_settings
from mta.presentation import bor_configuration, boroa_configuration
from mta.presentation.context import PublicationUnavailable


class NativeBuyerConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(override_settings(
            VF_MTA_NATIVE_PUBLICATION=True, VF_MTA_DAILY_PUBLICATION=True,
            VF_MTA_FIXTURE_FILE='', VF_MTA_FIXTURE_SHA256='', VF_MTA_OPERATIONAL_POLICY='',
            VF_MTA_OPERATIONAL_RECEIPT='', VF_MTA_CONSUMPTION_POLICY='', VF_MTA_SYNTHETIC_ROSTER=''))

    def test_pinned_configuration_needs_no_fixture_database(self):
        for module in (bor_configuration, boroa_configuration):
            with self.subTest(module=module.__name__), patch.object(
                    module.connection, 'cursor', side_effect=AssertionError('fixture dependency')):
                value = module.configuration()
                self.assertTrue(value['columns'])
                self.assertTrue(module.ui_columns(value))

    def test_changed_configuration_and_conflicting_mode_are_denied(self):
        for module in (bor_configuration, boroa_configuration):
            with self.subTest(module=module.__name__):
                pin = 'NATIVE_CONFIG_SHA256' if hasattr(module, 'NATIVE_CONFIG_SHA256') else 'CONFIG_SHA256'
                with patch.object(module, pin, '0' * 64):
                    with self.assertRaises(PublicationUnavailable):
                        module.configuration()
                with override_settings(VF_MTA_FIXTURE_FILE='unrelated-fixture'):
                    with self.assertRaisesRegex(PublicationUnavailable, 'mode_conflict'):
                        module.configuration()
