"""Focused fixture proof for the explicit offline preacceptance action phase."""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import UUID
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from mta.presentation import actions, preacceptance_actions as phase
from mta.serialization import digest


class Rows:
    def __init__(self, rows):
        self.rows = list(rows)

    def order_by(self, *_fields):
        return self

    def __iter__(self):
        return iter(self.rows)


class PreacceptanceFixtureTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        artifact = {'case': {'commands': [],
            'days': [{'business_date': '2026-06-06'}], 'profile': {}}}
        self.paths = {}
        for name, content in (
                ('artifact', json.dumps(artifact).encode()),
                ('finalization', b'finalization'), ('pick_config', b'pick'),
                ('shipment', b'shipment')):
            path = (self.root / (name + '.json')).resolve()
            path.write_bytes(content)
            self.paths[name] = {
                'path': str(path), 'sha256': hashlib.sha256(content).hexdigest()}
        self.access = {
            'product_permissions': [1], 'location_permissions': [2],
            'permissions_sha256': 'p' * 64, 'hierarchy_sha256': 'h' * 64,
        }
        self.source = SimpleNamespace(receipt={
            'owned_namespace': {'registration_id': 'owned-fixture'}})
        self.run = SimpleNamespace(pk='run-1', kind='DAILY_CHAIN', status='SUCCEEDED',
            input_digest='i' * 64, output_digest='o' * 64,
            business_date=date(2026, 6, 6),
            mdm_input_capture=SimpleNamespace(source=self.source),
            commands=Rows([]), successors=MagicMock())
        self.output = {'ClosingState': [{'importer': {
            'SkuAttributeData': [], 'LocationAttributeData': []}}],
            'DBMFinal': [{'Suggestions': [
                {'SKUCode': 'B', 'WhCode': 'L2', 'NewNorm': 20},
                {'SKUCode': 'A', 'WhCode': 'L1', 'NewNorm': 10}],
                'DBMMaster': [], 'NormAcceptanceTbl': [],
                'NormsInSleepModeTbl': []}]}
        self.raw = {'profile': {'bound': True}}
        self.profile_digest = digest(self.raw['profile'])

    def build(self):
        with patch.object(phase, '_validated_state', return_value=(
                self.raw, self.output, self.profile_digest)), \
                patch.object(phase, '_access', return_value=(
                    deepcopy(self.access), {'A', 'B'}, {'L1', 'L2'})), \
                patch.object(phase, '_namespace', return_value={
                    'registration_id': 'owned-fixture'}):
            return phase.build_manifest(self.run, actor='2', access=self.access,
                                        files=self.paths)

    def test_builds_owned_apply_only_plan_with_backend_noon_timestamp(self):
        manifest = self.build()
        self.assertEqual(manifest['actor'], '2')
        self.assertEqual(manifest['run'], {
            'id': 'run-1', 'input_digest': 'i' * 64,
            'output_digest': 'o' * 64, 'profile_digest': self.profile_digest,
            'business_date': '2026-06-06'})
        self.assertEqual(manifest['commands'], [{
            'after_day': 0, 'cohort': 'automatic-own-suggestions',
            'operation': 'APPLY', 'selected': [['A', 'L1'], ['B', 'L2']],
            'timestamp': '2026-06-06T12:00:00+05:30'}])
        self.assertEqual(manifest['phase_identity'], digest({
            key: value for key, value in manifest.items()
            if key != 'phase_identity'}))

    def test_manifest_wrong_actor_access_changed_extra_and_timestamp_deny(self):
        manifest = self.build()
        with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                    'actor_or_access_changed'):
            phase.verify_manifest(self.run, manifest, actor='3', access=self.access)
        changed_access = {**self.access, 'product_permissions': [9]}
        with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                    'actor_or_access_changed'):
            phase.verify_manifest(self.run, manifest, actor='2', access=changed_access)
        extra = {**manifest, 'caller_timestamp': '2026-06-06T13:00:00+05:30'}
        with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                    'manifest_fields_differ'):
            phase.verify_manifest(self.run, extra, actor='2', access=self.access)
        changed = deepcopy(manifest)
        changed['commands'][0]['timestamp'] = '2026-06-06T13:00:00+05:30'
        changed['phase_identity'] = digest({key: value for key, value in changed.items()
                                            if key != 'phase_identity'})
        with patch.object(phase, 'build_manifest', return_value=manifest):
            with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                        'manifest_facts_changed'):
                phase.verify_manifest(self.run, changed, actor='2', access=self.access)

    def test_completed_native_source_receipt_is_required_and_allowed(self):
        receipt = SimpleNamespace(images_digest='source-digest')
        with patch.object(phase, '_sealed', return_value=False), \
                patch('mta.presentation.daily_sources.receipt',
                      return_value=receipt) as verify_source, \
                patch('mta.runtime.validation_storage.read_input',
                      return_value=self.raw), \
                patch('mta.runtime.services.read_outputs',
                      return_value=self.output), \
                patch('mta.presentation.operational_admission.verify_input_domain',
                      return_value=self.profile_digest):
            self.assertEqual(phase._validated_state(self.run, self.paths),
                             (self.raw, self.output, self.profile_digest))
        verify_source.assert_called_once_with(self.run)

    def test_ui_publication_remains_a_seal_after_native_source_receipt(self):
        publication = MagicMock()
        attempt = MagicMock()
        acceptance = MagicMock()
        publication.return_value.exists.return_value = True
        attempt.return_value.exists.return_value = False
        acceptance.return_value.exists.return_value = False
        self.run.successors.exists.return_value = False
        with patch('mta.runtime.models.DailyUiPublication.objects.filter',
                   publication), \
                patch('mta.runtime.models.OperationalAttempt.objects.filter',
                      attempt), \
                patch('mta.runtime.models.OperationalAcceptance.objects.filter',
                      acceptance):
            self.assertTrue(phase._sealed(self.run))
        with patch.object(phase, '_sealed', return_value=True), \
                patch('mta.presentation.daily_sources.receipt',
                      side_effect=AssertionError('sealed run must stop first')):
            with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                        'sealed_or_consumed'):
                phase._validated_state(self.run, self.paths)

    def test_manifest_build_denies_planned_pair_outside_bound_scope(self):
        with patch.object(phase, '_validated_state', return_value=(
                self.raw, self.output, self.profile_digest)), \
                patch.object(phase, '_access', return_value=(
                    deepcopy(self.access), {'A'}, {'L1', 'L2'})), \
                patch.object(phase, '_namespace', return_value={
                    'registration_id': 'owned-fixture'}):
            with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                        'outside_authenticated_scope'):
                phase.build_manifest(self.run, actor='2', access=self.access,
                                     files=self.paths)

    def test_prefix_rejects_changed_and_extra_commands(self):
        manifest = self.build()
        command = manifest['commands'][0]
        event = SimpleNamespace(
            idempotency_key=phase._idempotency_key(manifest['phase_identity'], 1),
            payload=phase._expected_payload(command, '2'))
        self.run.commands = Rows([event])
        with patch('mta.runtime.temporal.command_state', return_value=(
                self.output['DBMFinal'][0], [])):
            prefix, _ = phase._verify_prefix(self.run, self.output, manifest)
        self.assertEqual(prefix, [event])

        event.payload = {**event.payload, 'actor': '3'}
        with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                    'prefix_changed'):
            phase._verify_prefix(self.run, self.output, manifest)
        self.run.commands = Rows([event, event])
        with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                    'extra_existing_command'):
            phase._verify_prefix(self.run, self.output, manifest)

    def test_execute_uses_manifest_timestamp_order_and_deterministic_key(self):
        manifest = self.build()
        state = self.output['DBMFinal'][0]
        event = SimpleNamespace(pk=1)
        seen = []
        def submit(payload, actor, operation, *, preacceptance):
            seen.append((payload, actor, operation, preacceptance))
            return event, {}
        with patch.object(phase, 'configured_manifest', return_value=(
                manifest, self.output, [], state)), \
                patch.object(phase, '_lock_phase_run', return_value=self.run) as lock_run, \
                patch.object(phase.actions, 'submit', side_effect=submit), \
                patch('mta.runtime.temporal.command_state', return_value=(state, [])):
            result = phase.execute.__wrapped__(self.run, actor='2', access=self.access)
        lock_run.assert_called_once_with(self.run)
        self.assertEqual(result, [event])
        payload, actor, operation, context = seen[0]
        self.assertEqual((actor, operation), ('2', 'APPLY'))
        self.assertEqual(payload['data'], [
            {'SKUCode': 'A', 'WHCode': 'L1'},
            {'SKUCode': 'B', 'WHCode': 'L2'}])
        self.assertEqual(context.action_timestamp,
                         '2026-06-06T12:00:00+05:30')
        self.assertEqual(context.idempotency_key,
            phase._idempotency_key(manifest['phase_identity'], 1))

    def test_exact_retry_reuses_prefix_and_eligibility_drift_denies(self):
        manifest = self.build()
        event = SimpleNamespace(pk=1)
        state = self.output['DBMFinal'][0]
        with patch.object(phase, 'configured_manifest', return_value=(
                manifest, self.output, [event], state)), \
                patch.object(phase, '_lock_phase_run', return_value=self.run), \
                patch.object(phase.actions, 'submit',
                             side_effect=AssertionError('must reuse prefix')):
            self.assertEqual(phase.execute.__wrapped__(
                self.run, actor='2', access=self.access), [event])
        changed = {**state, 'Suggestions': []}
        with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                    'eligibility_changed'):
            phase._verify_next_eligibility([], changed, manifest)

    def test_execute_locks_run_and_publication_key_before_manifest_read(self):
        run_id = UUID('12345678-1234-5678-9234-567812345678')
        supplied = SimpleNamespace(pk=run_id)
        locked = SimpleNamespace(pk=run_id)
        manager = MagicMock()
        manager.select_for_update.return_value.get.return_value = locked
        cursor = MagicMock()
        cursor.fetchone.return_value = (True,)
        context = MagicMock()
        context.__enter__.return_value = cursor
        database = MagicMock()
        database.cursor.return_value = context
        order = []
        manager.select_for_update.side_effect = lambda: (
            order.append('row-lock') or manager.select_for_update.return_value)
        context.__enter__.side_effect = lambda: (order.append('advisory-lock') or cursor)

        def configured(run, **_kwargs):
            order.append('manifest')
            self.assertIs(run, locked)
            return self.build(), self.output, [], self.output['DBMFinal'][0]

        with patch('mta.runtime.models.CalculationRun.objects', manager), \
                patch.object(phase, 'connection', database), \
                patch.object(phase, 'configured_manifest', side_effect=configured), \
                patch.object(phase.actions, 'submit', return_value=(SimpleNamespace(pk=1), {})), \
                patch('mta.runtime.temporal.command_state', return_value=(
                    self.output['DBMFinal'][0], [])):
            phase.execute.__wrapped__(supplied, actor='2', access=self.access)
        self.assertEqual(order[:3], ['row-lock', 'advisory-lock', 'manifest'])
        manager.select_for_update.return_value.get.assert_called_once_with(pk=run_id)
        cursor.execute.assert_called_once_with(
            'SELECT pg_try_advisory_xact_lock(%s)',
            [int.from_bytes(run_id.bytes[:8], 'big', signed=True)])

    def test_publication_lock_contention_denies_before_manifest_read(self):
        run_id = UUID('12345678-1234-5678-9234-567812345678')
        run = SimpleNamespace(pk=run_id)
        manager = MagicMock()
        manager.select_for_update.return_value.get.return_value = run
        cursor = MagicMock()
        cursor.fetchone.return_value = (False,)
        context = MagicMock()
        context.__enter__.return_value = cursor
        database = MagicMock()
        database.cursor.return_value = context
        with patch('mta.runtime.models.CalculationRun.objects', manager), \
                patch.object(phase, 'connection', database), \
                patch.object(phase, 'configured_manifest',
                    side_effect=AssertionError('manifest must not be read')):
            with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                        'daily_publication_in_progress'):
                phase.execute.__wrapped__(run, actor='2', access=self.access)

    @override_settings(VF_MTA_PREACCEPTANCE_FILE='',
                       VF_MTA_PREACCEPTANCE_SHA256='')
    def test_phase_is_unavailable_without_explicit_configuration(self):
        with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                    'configuration_required'):
            phase.configured_manifest(self.run, actor='2', access=self.access)

    @override_settings(VF_MTA_PREACCEPTANCE_SHA256='0' * 64)
    def test_configured_manifest_hash_change_denies(self):
        manifest = self.build()
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        with override_settings(VF_MTA_PREACCEPTANCE_FILE=str(path.resolve())):
            with self.assertRaisesRegex(phase.PreacceptanceDenied,
                                        'configured_manifest_digest_changed'):
                phase.configured_manifest(self.run, actor='2', access=self.access)


class PreacceptanceActionAdapterFixtureTests(SimpleTestCase):
    def test_out_of_scope_phase_selection_never_reaches_command_writer(self):
        output = {'ClosingState': [{'importer': {}}]}
        dbm = {'Suggestions': [{'SKUCode': 'A', 'WhCode': 'L1'}],
               'DBMMaster': [], 'NormAcceptanceTbl': []}
        run = SimpleNamespace(pk='run-1')
        context = actions.PreacceptanceActionContext(run=run, output=output, dbm=dbm,
            action_timestamp='2026-06-06T12:00:00+05:30',
            idempotency_key='preaccept-' + 'a' * 64 + '-001')
        lock = MagicMock()
        lock.select_for_update.return_value.get.return_value = run
        payload = {'data': [{'SKUCode': 'A', 'WHCode': 'L1'}],
                   'product_permissions': [1], 'location_permissions': [2]}
        with patch.object(actions.CalculationRun, 'objects', lock), \
                patch('mta.runtime.models.OperationalAcceptance.objects.filter') as accepted, \
                patch.object(actions, 'scope', return_value=({'A'}, set())), \
                patch.object(actions, 'record_command',
                             side_effect=AssertionError('must not write')):
            accepted.return_value.exists.return_value = False
            with self.assertRaisesRegex(actions.ActionDenied,
                                        'outside_authenticated_scope'):
                actions.submit.__wrapped__(payload, '2', 'APPLY',
                                           preacceptance=context)

    def test_accepted_run_is_sealed_at_shared_action_writer(self):
        run = SimpleNamespace(pk='run-1')
        context = actions.PreacceptanceActionContext(run=run,
            output={'ClosingState': [{'importer': {}}]}, dbm={'Suggestions': []},
            action_timestamp='2026-06-06T12:00:00+05:30',
            idempotency_key='preaccept-' + 'a' * 64 + '-001')
        lock = MagicMock()
        lock.select_for_update.return_value.get.return_value = run
        payload = {'data': [{'SKUCode': 'A', 'WHCode': 'L1'}]}
        with patch.object(actions.CalculationRun, 'objects', lock), \
                patch('mta.runtime.models.OperationalAcceptance.objects.filter') as accepted, \
                patch.object(actions, 'scope',
                             side_effect=AssertionError('must stop before scope')):
            accepted.return_value.exists.return_value = True
            with self.assertRaisesRegex(actions.ActionDenied,
                                        'operational_acceptance_sealed'):
                actions.submit.__wrapped__(payload, '2', 'APPLY',
                                           preacceptance=context)
