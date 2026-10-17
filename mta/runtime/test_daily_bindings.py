"""Pure Cohort6 B1 parser, binding and forwarding proof; no daily execution."""
from copy import deepcopy
from datetime import date
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from mta.application.daily_finalization import FLAG_SEED, REQUIRED
from mta.application.operational_capture import CAPTURE_POLICY
from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY
from mta.application.timeline_controls import FORCE_CAPTURE_POLICY
from mta.runtime import daily_bindings
from mta.runtime.management.commands import run_daily


class DailyBindingCommandTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output_root = self.root / 'pick-output'
        self.output_root.mkdir()
        self.artifact = self.root / 'artifact.json'
        self.pick = self.root / 'pick.json'
        self.finalization = self.root / 'finalization.json'
        profile = {
            'delivery': {'site_code': 'B1-FIXTURE'},
            'calculation': {'logistics': {
                'vehicle': {'legacy': 'retained-until-explicit-pick-binding'},
                'items': [{'from_location': 'PARENT'}],
            }},
        }
        opening = {'importer_settings': [
            {'Parameter': 'NMSActive', 'Value': '0'},
            {'Parameter': 'IsBatchFileExecuted', 'Value': '0'},
            {'Parameter': 'IsBPRBatchFileExecuted', 'Value': '0'},
            {'Parameter': 'BatchFileExecutionDate', 'Value': '01/01/2000 12:00AM'},
        ]}
        artifact = {'schema': 'b1-command-fixture-v1', 'case': {
            'case': 'b1-command-fixture', 'profile': profile,
            'opening': opening, 'opening_date': '2026-10-08',
            'days': [{'business_date': '2026-10-09'}], 'static_day': {},
        }}
        self.artifact.write_text(json.dumps(artifact), encoding='utf-8')
        self.artifact_bytes = self.artifact.read_bytes()
        self.artifact_sha = hashlib.sha256(self.artifact_bytes).hexdigest()
        pick = {
            'vehicles': [{'vehicle_id': 7, 'name': 'OWNED',
                          'weight_capacity': 1000, 'volume_capacity': 1000}],
            'location_vehicles': [{'location_code': 'PARENT', 'vehicle_id': 7}],
        }
        self.pick.write_text(json.dumps(pick), encoding='utf-8')
        self.pick_bytes = self.pick.read_bytes()
        self.pick_sha = hashlib.sha256(self.pick_bytes).hexdigest()
        complete = {name: [] for name in REQUIRED}
        complete['ScriptExecutedFlag'] = deepcopy(FLAG_SEED)
        finalization = {
            'schema': 'generic-finalization-input-v1',
            'artifact_sha256': self.artifact_sha,
            'configuration': {'policy': 'generic-finalization-v1',
                              'consumption_days': 15, 'remark_days': 90},
            'opening_complete': complete,
        }
        self.finalization.write_text(json.dumps(finalization), encoding='utf-8')
        self.finalization_bytes = self.finalization.read_bytes()
        self.finalization_sha = hashlib.sha256(self.finalization_bytes).hexdigest()

    def arguments(self):
        return [str(self.artifact), '--sha256', self.artifact_sha,
                '--day-index', '0', '--revision', 'b1-command-test',
                '--mdm-source', '7', '--mdm-source-digest', 'd' * 64,
                '--bpr-remark-horizon', '90']

    def binding_arguments(self):
        return [
            '--finalization-config', str(self.finalization),
            '--finalization-config-sha256', self.finalization_sha,
            '--complete-pick-policy', daily_bindings.PICK_POLICY,
            '--pick-output-root', str(self.output_root),
            '--pick-config', str(self.pick),
            '--pick-config-sha256', self.pick_sha,
            '--operational-sources', CAPTURE_POLICY,
            '--operational-input-sources', INPUT_CAPTURE_POLICY,
            '--operational-force-sources', FORCE_CAPTURE_POLICY,
        ]

    def invoke(self, arguments):
        command = run_daily.Command(stdout=io.StringIO())
        parser = command.create_parser('manage.py', 'run_daily')
        options = vars(parser.parse_args(arguments))
        calls = []
        result = SimpleNamespace(status='SUCCEEDED', pk='fixture-run',
            business_date=date(2026, 10, 9), input_digest='i' * 64,
            output_digest='o' * 64, validation_digest='v' * 64)
        source = SimpleNamespace(pk=7, digest='d' * 64)
        with patch.object(run_daily.MdmSource.objects, 'get', return_value=source), \
                patch('mta.mdm.daily_source.require_binding'), \
                patch.object(run_daily, 'execute_day',
                             side_effect=lambda **kwargs: calls.append(kwargs) or result):
            command.handle(**options)
        return calls

    def test_parser_forwards_exact_complete_bindings_without_changing_artifact(self):
        calls = self.invoke(self.arguments() + self.binding_arguments())
        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call['finalization_config'], self.finalization_bytes)
        self.assertEqual(call['pick_output_root'], self.output_root.resolve())
        self.assertEqual(call['pick_config_sha256'], self.pick_sha)
        profile = call['profile']
        self.assertEqual(profile['complete_daily'], {
            'policy': 'generic-finalization-v1',
            'consumption_days': 15, 'remark_days': 90})
        self.assertEqual(profile['complete_daily_config_sha256'],
                         self.finalization_sha)
        self.assertEqual(profile['complete_daily_artifact_sha256'],
                         self.artifact_sha)
        self.assertEqual(profile['complete_pick'],
                         {'policy': daily_bindings.PICK_POLICY})
        self.assertEqual(profile['operational_sources'], CAPTURE_POLICY)
        self.assertEqual(profile['operational_input_sources'], INPUT_CAPTURE_POLICY)
        self.assertEqual(profile['operational_force_sources'], FORCE_CAPTURE_POLICY)
        logistics = profile['calculation']['logistics']
        self.assertNotIn('vehicle', logistics)
        self.assertEqual(logistics['items'], [{'from_location': 'PARENT'}])
        self.assertEqual(self.artifact.read_bytes(), self.artifact_bytes)

    def test_basic_command_path_adds_no_optional_binding_arguments(self):
        call = self.invoke(self.arguments())[0]
        self.assertNotIn('finalization_config', call)
        self.assertNotIn('pick_output_root', call)
        self.assertNotIn('pick_config_sha256', call)
        self.assertNotIn('complete_daily', call['profile'])
        self.assertNotIn('complete_pick', call['profile'])
        self.assertNotIn('operational_sources', call['profile'])

    def test_shipment_forwarding_requires_complete_binding_and_rejects_replacement(self):
        shipment=self.root/'shipment.json'
        supplied={'schema':'verified-fixture','rows':[{'quantity':None},{'quantity':2}]}
        extra=['--shipment-input',str(shipment),'--shipment-sha256','a'*64]
        with patch.object(run_daily,'shipment_day',return_value=supplied) as load:
            call=self.invoke(self.arguments()+extra)[0]
            self.assertEqual(call['day']['shipment_input'],supplied)
            self.assertEqual(call['shipment_sha256'],'a'*64)
            load.assert_called_once_with(shipment,'a'*64,
                artifact_sha256=self.artifact_sha,business_date='2026-10-09')
        for incomplete in (extra[:2],extra[2:]):
            with self.assertRaisesRegex(CommandError,'supplied together'):
                self.invoke(self.arguments()+incomplete)
        with patch.object(run_daily,'shipment_day',side_effect=ValueError('Shipment digest differs')):
            with self.assertRaisesRegex(CommandError,'Shipment digest differs'):
                self.invoke(self.arguments()+extra)
        artifact=json.loads(self.artifact_bytes)
        artifact['case']['static_day']['shipment_input']={'retained':True}
        self.artifact.write_text(json.dumps(artifact),encoding='utf-8')
        self.artifact_sha=hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        with self.assertRaisesRegex(CommandError,'cannot replace artifact facts'):
            self.invoke(self.arguments()+extra)

    def test_missing_and_unknown_bindings_deny_before_forwarding(self):
        cases = [
            (['--finalization-config', str(self.finalization)], 'supplied together'),
            (['--complete-pick-policy', daily_bindings.PICK_POLICY],
             'supplied together'),
            (['--operational-sources', CAPTURE_POLICY], 'supplied together'),
            (self.binding_arguments()[:-1] + ['unsupported-force-policy'],
             'Unsupported explicit operational'),
        ]
        for extra, message in cases:
            with self.subTest(extra=extra), self.assertRaisesRegex(CommandError, message):
                self.invoke(self.arguments() + extra)

    def test_tampered_hashes_and_unknown_pick_policy_deny(self):
        cases = [
            (['--finalization-config', str(self.finalization),
              '--finalization-config-sha256', '0' * 64], 'digest differs'),
            (['--complete-pick-policy', daily_bindings.PICK_POLICY,
              '--pick-output-root', str(self.output_root),
              '--pick-config', str(self.pick),
              '--pick-config-sha256', '0' * 64], 'digest differs'),
            (['--complete-pick-policy', 'unknown-pick-policy',
              '--pick-output-root', str(self.output_root),
              '--pick-config', str(self.pick),
              '--pick-config-sha256', self.pick_sha], 'Unsupported complete Pick'),
        ]
        for extra, message in cases:
            with self.subTest(extra=extra), self.assertRaisesRegex(CommandError, message):
                self.invoke(self.arguments() + extra)
        missing_root = self.root / 'missing-pick-root'
        with self.assertRaises(CommandError):
            self.invoke(self.arguments() + [
                '--complete-pick-policy', daily_bindings.PICK_POLICY,
                '--pick-output-root', str(missing_root),
                '--pick-config', str(self.pick),
                '--pick-config-sha256', self.pick_sha])


class DailyBindingPureHelperTests(SimpleTestCase):
    def test_pick_reconstruction_is_deep_copy_and_rejects_unknown_fields(self):
        profile = {'calculation': {'logistics': {
            'vehicle': {'legacy': True},
            'items': [{'from_location': 'PARENT'}],
        }}}
        config = {'vehicles': [{'vehicle_id': 1, 'name': 'V',
                                'weight_capacity': 1, 'volume_capacity': 1}],
                  'location_vehicles': [
                      {'location_code': 'PARENT', 'vehicle_id': 1}]}
        result = daily_bindings.apply_pick(
            profile, json.dumps(config).encode(), daily_bindings.PICK_POLICY)
        self.assertIsNot(result, profile)
        self.assertIn('vehicle', profile['calculation']['logistics'])
        self.assertNotIn('vehicle', result['calculation']['logistics'])
        changed = deepcopy(config)
        changed['unsupported'] = []
        with self.assertRaisesRegex(ValueError, 'exact vehicle'):
            daily_bindings.apply_pick(
                profile, json.dumps(changed).encode(), daily_bindings.PICK_POLICY)
        incomplete = deepcopy(config)
        incomplete['location_vehicles'][0]['location_code'] = 'OTHER'
        with self.assertRaisesRegex(ValueError, 'mapping is incomplete'):
            daily_bindings.apply_pick(
                profile, json.dumps(incomplete).encode(), daily_bindings.PICK_POLICY)

    def test_finalization_rejects_unknown_supplement_keys_before_population_use(self):
        supplement = {
            'schema': 'generic-finalization-input-v1',
            'artifact_sha256': 'a' * 64,
            'configuration': {'policy': 'generic-finalization-v1',
                              'consumption_days': 15, 'remark_days': 90},
            'opening_complete': {}, 'unsupported': True,
        }
        content = json.dumps(supplement).encode()
        with self.assertRaisesRegex(ValueError, 'binding differs'):
            daily_bindings.apply_finalization({}, {}, content,
                artifact_sha256='a' * 64,
                config_sha256=hashlib.sha256(content).hexdigest(),
                business_date='2026-10-09')
