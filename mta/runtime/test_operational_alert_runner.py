"""Persisted source-to-intent protocol with real files and no engine invocation."""
from copy import deepcopy
from functools import partial
import os
from pathlib import Path
import unittest
import uuid

from mta.application.operational_alerts import ALERT_SEEDS
from mta.application.operational_io import archive_files
from mta.application.operational_norm_reports import REQUIRED_CONFIGURATION
from mta.runtime.test_operational_force_source import ForceCaptureProtocol
from mta.runtime.operational_attempts import register_configuration, start_attempt
from mta.runtime.operational_alert_sources import ABORT_OPENING_POLICY, install_alert_opening, read_alert_inputs
from mta.runtime.operational_alert_runner import ALERT_OPERATION, materialize_alert_operation
from mta.runtime.operational_effects import verify_intent_evaluation
from mta.runtime.operational_lease import operational_run_lease
from mta.runtime.operational_reports import REPORT_OPERATIONS, materialize_report_operation
from mta.runtime.operational_native import read_population
from mta.runtime.operational_models import OperationalAlertIntent
from mta.runtime.services import read_outputs
from mta.serialization import digest
from tests.test_operational_exceptions import master, daily, processed
from tests.test_operational_norm_reports import reports


class AlertRunnerProtocol(unittest.TestCase):
    run_day = ForceCaptureProtocol.run_day

    def setUp(self):
        ForceCaptureProtocol.setUp(self)
        self.profile['delivery']['batch'] = dict(REQUIRED_CONFIGURATION)
        self.profile['force_flags'] = dict(nms_active=False, ignore_master_norm=False)
        self.state.update(bpr=dict(BPRMaster=[master(Norm=100)], DailyConsumption=[daily()]),
            importer=dict(MasterData=[processed(), processed(WhCode='P', Norm=0, ParentWhCode='P')],
                SKUDescriptionTbl=[dict(SKUCode='S', SKUDescription='Some SKU')],
                SiteDescriptionTbl=[dict(WHCode='W', WHDescription='Site')], RejectedMaster=[]),
            controls=dict(phase_out=[]),
            control_aux=dict(phase_requests=[], phase_in_requests=[], phase_exceptions=[]),
            complete=dict(CriticalFiles=[], DataSanitizationResult=[]))
        self.populations['ForceNormChange'] = []
        self.control_reports = dict(failed_force=[], phase_exceptions=[])
        self.writer = partial(archive_files, executable='/cohort2/tools/linux/7zz',
            tool_sha256='d1bc79f00e9815b24048ab167690bdd1dbc387de7dbc47e8d75d68689e49cf4f')

    def calculate(self, *args):
        result = ForceCaptureProtocol.calculate(self, *args)
        result['Reports'] = reports()
        result['Reports'][-1]['tables'] = deepcopy(self.control_reports)
        return result

    def configure(self, run):
        self.root = Path('/cohort2/alert-runtime-a001')/str(run.pk)
        self.root.mkdir(parents=True, exist_ok=False)
        roster = [dict(ordinal=i, group=g, **REPORT_OPERATIONS[g]) for i,g in enumerate(('O3', 'O2'))]
        roster.append(dict(ordinal=2, group='O7', **ALERT_OPERATION))
        config = register_configuration(source_digest=digest(roster), settings=[], tables=[],
            alerts=[dict(ordinal=i, name=seed['name'], active=seed['active']=='1') for i,seed in enumerate(ALERT_SEEDS)],
            bindings=dict(operation_roster=roster, opening_input_digest=run.input_digest,
                abort_opening_policy=ABORT_OPENING_POLICY, abort_opening_digest=digest([]),
                alert_configuration=dict(recipient='Not-Defined', cc_recipient='support@vectorconsulting.in',
                    profile='Not-Defined', site='VECTORFLOW-DEMO', attach_invalid_data_report_zip=True,
                    auto_dbm_active=False, distributor_system_active=False, nms_active=False,
                    fnc_match_master_norm=True)))
        return config

    def prepare(self, run, config):
        owner = start_attempt(run_id=run.pk, configuration_id=config.pk, request_key=uuid.uuid4().hex,
                              owned_root=self.root, expected_output_digest=run.output_digest)
        install_alert_opening(owner.pk, abort_reasons=[])
        for group in ('O3', 'O2'):
            materialize_report_operation(owner.pk, group=group, archive_writer=self.writer)
        return owner

    def test_fourteen_owned_intents_and_exact_real_attachments(self):
        run = self.run_day()
        before = read_outputs(run)
        config = self.configure(run)
        calls = len(self.seen)
        with operational_run_lease(run.pk):
            owner = self.prepare(run, config)
            effect = materialize_alert_operation(owner.pk, archive_writer=self.writer)
            effect.refresh_from_db()
            self.assertEqual(effect.status, 'SUCCEEDED')
            evaluations = list(effect.operationalintentevaluation_set.select_related('intent'))
            self.assertEqual({e.intent.alert_name for e in evaluations}, {s['name'] for s in ALERT_SEEDS})
            self.assertEqual(len(evaluations), 14)
            for evaluation in evaluations:
                verify_intent_evaluation(evaluation)
            parent = next(e.intent for e in evaluations if e.intent.alert_name=='NoNormParentAlert')
            self.assertEqual(parent.disposition, 'RECIPIENT_SUPPRESSED')
            self.assertEqual(list(parent.attachments.values_list('relative_path', flat=True)), ['output/NoNormParentReport.zip'])
            self.assertEqual(read_population(owner, 'closing/RunAbortReasons'), [])
        self.assertEqual(read_outputs(run), before)
        self.assertEqual(len(self.seen), calls)

    def test_positive_missing_sanitation_attachment_is_durable_failure(self):
        self.state['complete']['DataSanitizationResult'] = [dict(Date='2026-06-06', Time=None,
            Critical_Flag='False', Non_Critical_Flag='True')]
        run = self.run_day()
        config = self.configure(run)
        with operational_run_lease(run.pk):
            owner = self.prepare(run, config)
            with self.assertRaisesRegex(ValueError, 'attachment unavailable'):
                materialize_alert_operation(owner.pk, archive_writer=self.writer)
            owner.refresh_from_db()
            self.assertEqual(owner.status, 'FAILED')
            intent = OperationalAlertIntent.objects.get(run=run, alert_name='DailyDataValidationErrorAlert')
            self.assertEqual(intent.disposition, 'ATTACHMENT_UNAVAILABLE')
            self.assertFalse(intent.attachments.exists())

    def test_missing_sanitation_is_not_assumed_empty(self):
        del self.state['complete']['DataSanitizationResult']
        run = self.run_day()
        config = self.configure(run)
        with operational_run_lease(run.pk):
            owner = self.prepare(run, config)
            with self.assertRaisesRegex(ValueError, 'source absent: DataSanitizationResult'):
                read_alert_inputs(owner)
