"""Exact connector-configuration carry, with no changes to canonical state."""
from copy import deepcopy
from contextlib import nullcontext
from datetime import date
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.mdm.daily_input import SCHEMA, SQL_DIGEST
from mta.runtime.mdm_configuration import capture_configuration_for_day
from mta.serialization import digest


class MdmConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.settings = [{'Parameter':'NMSActive','Value':'0'}]
        self.source = SimpleNamespace(pk=1, digest='source')
        self.snapshot = dict(schema=SCHEMA,source_id=1,source_digest='source',
            sql_digest=SQL_DIGEST,nms_active=True,configuration=dict(
                task_status_log_horizon=7,nms_data_history_horizon=15))
        self.snapshot['revision_digest'] = digest(self.snapshot)
        self.capture = SimpleNamespace(status='CONSUMED',source_id=1,
            sql_digest=SQL_DIGEST,nms_active=True,
            revision_digest=self.snapshot['revision_digest'])
        self.parent = SimpleNamespace(status='SUCCEEDED',kind='DAILY_CHAIN',
                                      mdm_input_capture=self.capture)

    def resolve(self, settings=None):
        with patch('mta.runtime.validation_storage.read_input',
                   return_value={'mdm_input':self.snapshot}):
            return capture_configuration_for_day(self.settings if settings is None else settings,
                predecessor=self.parent,source=self.source)

    def test_exact_carry_keeps_current_nms_flag_and_canonical_state_unchanged(self):
        before = deepcopy(self.settings)
        self.assertEqual(self.resolve(),(False,7))
        self.assertEqual(self.settings,before)

    def test_root_requires_explicit_setting(self):
        with self.assertRaisesRegex(ValueError,'exact TaskStatusLogHorizon'):
            capture_configuration_for_day(self.settings)

    def test_current_setting_is_authoritative_and_duplicates_malformed_fail(self):
        current = self.settings+[{'Parameter':'TaskStatusLogHorizon','Value':'9'}]
        self.assertEqual(self.resolve(current),(False,9))
        with self.assertRaises(ValueError): self.resolve(current+[current[-1]])
        with self.assertRaises(ValueError):
            self.resolve(self.settings+[{'Parameter':'TaskStatusLogHorizon','Value':'bad'}])

    def test_absent_unconsumed_wrong_source_or_failed_predecessor_fail(self):
        for obj,field,value in [(self.parent,'mdm_input_capture',None),
                (self.capture,'status','CAPTURED'),(self.capture,'source_id',2),
                (self.parent,'status','FAILED')]:
            before=getattr(obj,field); setattr(obj,field,value)
            with self.assertRaisesRegex(ValueError,'consumed same-source'): self.resolve()
            setattr(obj,field,before)

    def test_frozen_configuration_drift_and_wrong_types_fail(self):
        self.snapshot['configuration']['task_status_log_horizon']=8
        with self.assertRaisesRegex(ValueError,'integrity differs'): self.resolve()
        self.snapshot['configuration']['task_status_log_horizon']=True
        self.snapshot.pop('revision_digest')
        self.snapshot['revision_digest']=digest(self.snapshot)
        self.capture.revision_digest=self.snapshot['revision_digest']
        with self.assertRaisesRegex(ValueError,'exact frozen horizons'): self.resolve()

    def test_successor_retry_resolves_origin_source_before_configuration(self):
        from mta.runtime.temporal import execute_day
        self.parent.pk='parent'
        self.parent.business_date=date(2026,6,6)
        self.parent.output_digest='output'
        self.parent.input_payload={'profile':{'delivery':{'site_code':'test'}}}
        origin=SimpleNamespace(source_id=1)
        def resolver(settings, *, predecessor, source):
            self.assertEqual(settings,self.settings)
            self.assertIs(predecessor,self.parent)
            self.assertIs(source,self.source)
            raise RuntimeError('verified successor retry configuration source')
        with patch('mta.runtime.temporal.transaction.get_autocommit',return_value=True), \
                patch('mta.runtime.temporal.transaction.atomic',return_value=nullcontext()), \
                patch('mta.runtime.temporal.connection.cursor'), \
                patch('mta.runtime.temporal.settings.VF_MTA_DAILY_PUBLICATION',False), \
                patch('mta.runtime.temporal.CalculationRun.objects') as runs, \
                patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects') as captures, \
                patch('mta.runtime.mdm_models.MdmSource.objects') as sources, \
                patch('mta.runtime.temporal.read_outputs',return_value={
                    'ClosingState':[{'importer_settings':self.settings,'dbm':{}}]}), \
                patch('mta.runtime.temporal.command_state',return_value=({},[])), \
                patch('mta.runtime.mdm_configuration.capture_configuration_for_day',side_effect=resolver):
            runs.select_for_update.return_value.get.return_value=self.parent
            captures.select_for_update.return_value.select_related.return_value.get.return_value=origin
            sources.select_for_update.return_value.get.return_value=self.source
            with self.assertRaisesRegex(RuntimeError,'verified successor retry'):
                execute_day(day={'business_date':'2026-06-07'},
                    profile={'delivery':{'site_code':'test'}},execution_revision='retry',
                    predecessor=self.parent,mdm_retry='failed-successor')
