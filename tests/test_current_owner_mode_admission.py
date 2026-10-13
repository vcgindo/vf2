"""Inactive current publication belongs only to exact native source admission."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','current-owner-mode-unit-only')
import django
django.setup()
from mta.mdm import daily_current
from mta.mdm.daily_source import SCHEMA as LEGACY_SCHEMA
from mta.mdm.initialization_contract import SOURCE_SCHEMA
from mta.application.daily_finalization import ACTIVE_POLICY, POLICY
from mta.runtime.mdm_daily_models import MdmDailyInputCapture


class CurrentOwnerModeAdmissionTests(unittest.TestCase):
    def verify_mode(self,schema,active,policy,allowed):
        run=SimpleNamespace(pk='owned-run',kind='DAILY_CHAIN',predecessor_id=None)
        source=SimpleNamespace(receipt={'schema':schema})
        capture=SimpleNamespace(run=run,run_id=run.pk,nms_active=active)
        query=Mock();query.select_related.return_value=[capture]
        with patch.object(MdmDailyInputCapture.objects,'filter',return_value=query), \
                patch('mta.runtime.validation_storage.read_input',return_value={
                    'profile':{'complete_daily':{'policy':policy}}}), \
                patch('mta.runtime.services.read_outputs',return_value={'ClosingState':[{'owned':'closing'}]}) as read, \
                patch.object(daily_current,'verify_current') as verify, \
                patch.object(daily_current,'identity',return_value=['full-owner-identity']):
            if allowed:
                self.assertEqual(daily_current.verify_published(run,source),['full-owner-identity'])
                verify.assert_called_once_with(source,{'owned':'closing'})
            else:
                with self.assertRaisesRegex(ValueError,'unavailable|mode differs'):
                    daily_current.verify_published(run,source)
                verify.assert_not_called()
                read.assert_not_called()

    def test_legacy_active_allowed_and_inactive_denied(self):
        self.verify_mode(LEGACY_SCHEMA,True,ACTIVE_POLICY,True)
        self.verify_mode(LEGACY_SCHEMA,False,POLICY,False)

    def test_exact_native_schema_allows_both_matching_modes(self):
        self.verify_mode(SOURCE_SCHEMA,True,ACTIVE_POLICY,True)
        self.verify_mode(SOURCE_SCHEMA,False,POLICY,True)

    def test_near_native_schema_does_not_grant_inactive_admission(self):
        for schema in (None,SOURCE_SCHEMA+'-other','unknown'):
            with self.subTest(schema=schema):self.verify_mode(schema,False,POLICY,False)

    def test_frozen_policy_mismatches_denied_for_both_source_kinds(self):
        for schema in (LEGACY_SCHEMA,SOURCE_SCHEMA):
            for active,policy in ((True,POLICY),(False,ACTIVE_POLICY),(True,'unknown'),(False,'unknown')):
                with self.subTest(schema=schema,active=active,policy=policy):
                    self.verify_mode(schema,active,policy,False)
