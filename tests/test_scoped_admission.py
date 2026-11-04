"""Phase WSGI wiring and fail-closed identities; native serving needs PG proof."""
from contextlib import contextmanager
from datetime import date
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from django.test import override_settings
from mta.presentation import admission, scoped_admission, scoped_selection
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


class ScopedAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        permissions = root / 'permissions.json'
        raw = json.dumps(dict(version='block1-permissions-v1', **{
            name: dict(records=[dict(id=1, level_1='A', level_2='B', level_3='C')])
            for name in ('products', 'locations')})).encode()
        permissions.write_bytes(raw)
        self.run = SimpleNamespace(pk=uuid4(), kind='DAILY_CHAIN', evidence_mode='production',
            status='RUNNING', input_digest='a' * 64, input_manifest_digest='b' * 64,
            business_date=date(2037, 4, 10), output_digest='')
        self.source = SimpleNamespace(pk=7, digest='c' * 64)
        self.phase = SimpleNamespace(run=self.run, phase='BPR', state_sealed=True,
            digest='d' * 64, source_id=7, snapshot=SimpleNamespace(state_digest='e' * 64))
        self.capture = SimpleNamespace(source=self.source, source_id=7,
            revision_digest='f' * 64, status='CAPTURED')
        value = dict(schema=scoped_selection.SCHEMA, run_id=str(self.run.pk), phase_id=str(uuid4()),
            phase_digest=self.phase.digest, snapshot_digest=self.phase.snapshot.state_digest,
            input_digest=self.run.input_digest, input_manifest_digest=self.run.input_manifest_digest,
            capture_digest=self.capture.revision_digest, configuration_digest='1' * 64,
            native_digest='2' * 64, permissions_sha256=hashlib.sha256(raw).hexdigest(),
            recipe_digest='3' * 64, business_date='2037-04-10')
        value['selection_digest'] = digest(value)
        self.anchor = value; self.path = root / 'phase.json'
        scoped_selection.write(self.path, value)
        settings = override_settings(VF_MTA_PHASE_SELECTION_FILE=str(self.path), VF_MTA_PHASE_SELECTION=value,
            VF_MTA_SELECTION_FILE='', VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST='',
            VF_MTA_HIERARCHY_FILE='', VF_MTA_HIERARCHY_SHA256='',
            VF_MDM_SOURCE_DIGEST=self.source.digest, VF_MTA_PERMISSIONS_FILE=str(permissions),
            VF_MTA_PERMISSIONS_SHA256=value['permissions_sha256'])
        settings.enable(); self.addCleanup(settings.disable)
        phases = patch.object(scoped_admission.RunPhaseAcceptance.objects, 'select_related')
        phases.start().return_value.get.return_value = self.phase; self.addCleanup(phases.stop)
        captures = patch.object(scoped_admission.MdmDailyInputCapture.objects, 'select_related')
        captures.start().return_value.get.return_value = self.capture; self.addCleanup(captures.stop)
        certified = patch.object(scoped_admission, 'certified_source', return_value=self.source)
        self.certified = certified.start(); self.addCleanup(certified.stop)
        # This unit fixture predates registered/scoped report input dispatch.
        # Declare its unregistered input explicitly; typed input ownership is
        # exercised by the PostgreSQL scope tests, not this metadata fixture.
        inputs = patch('mta.runtime.input_reader.read_input', return_value={})
        inputs.start(); self.addCleanup(inputs.stop)
        recipe = patch.object(scoped_selection, 'recipe_digest', return_value='3' * 64)
        recipe.start(); self.addCleanup(recipe.stop)
        old = admission._admitted; self.addCleanup(setattr, admission, '_admitted', old)
        admission._admitted = None

    def test_binding_requires_certified_current_source_and_is_stable_for_refresh(self):
        run, initial = scoped_admission.binding()
        self.assertEqual(run.pk, self.run.pk)
        self.certified.assert_called_with(self.source.digest)
        # Current view-reference/remark/action values do not replace the logical anchor.
        self.phase.current_reference = uuid4()
        self.phase.current_action_revision = 19
        self.assertEqual(scoped_admission.binding()[1], initial)
        self.certified.return_value = None
        with self.assertRaisesRegex(PublicationUnavailable, 'certified_source'):
            scoped_admission.binding()

    def test_source_phase_input_and_mode_drift_deny(self):
        for target, key, value in ((self.phase, 'state_sealed', False),
                (self.phase, 'source_id', 8), (self.phase, 'phase', 'DBM'),
                (self.run, 'evidence_mode', 'fixture'), (self.run, 'input_digest', '0' * 64),
                (self.capture, 'status', 'CONSUMED')):
            before = getattr(target, key); setattr(target, key, value)
            try:
                with self.subTest(key=key), self.assertRaises(PublicationUnavailable):
                    scoped_admission.binding()
            finally:
                setattr(target, key, before)
        with self.assertRaises(PublicationUnavailable):
            scoped_admission.binding(SimpleNamespace(pk=uuid4()))

    def test_report_read_scope_starts_after_certification_and_ends_after_binding(self):
        from mta.presentation.request_scope import in_read_request
        expected = scoped_admission.binding()
        events = []

        def certified(_):
            self.assertFalse(in_read_request())
            events.append('certified')
            return self.source

        @contextmanager
        def snapshot():
            events.append('snapshot')
            try:
                yield
            finally:
                self.assertFalse(in_read_request())
                events.append('closed')

        select = scoped_admission._selection_identity

        def selection(*args):
            self.assertTrue(in_read_request())
            events.append('selection')
            return select(*args)

        with patch.object(self.certified, 'side_effect', certified), \
                patch('mta.presentation.publication_binding.snapshot', snapshot), \
                patch.object(scoped_admission, '_selection_identity', selection):
            self.assertEqual(scoped_admission.binding(report_path='/api/mta/PublicationBinding'), expected)
        self.assertEqual(events, ['certified', 'snapshot', 'selection', 'closed'])

    def test_changed_file_configuration_or_recipe_cannot_be_reused(self):
        with override_settings(VF_MTA_PUBLISHED_RUN=str(uuid4())):
            with self.assertRaises(PublicationUnavailable): scoped_admission.binding()
        with patch.object(scoped_selection, 'recipe_digest', return_value='9' * 64):
            with self.assertRaises(PublicationUnavailable): scoped_admission.binding()
        changed = dict(self.anchor, native_digest='8' * 64)
        changed['selection_digest'] = digest({k: v for k, v in changed.items() if k != 'selection_digest'})
        scoped_selection.write(self.path, changed)
        with self.assertRaisesRegex(PublicationUnavailable, 'restart_required'):
            scoped_admission.binding()

    def test_startup_checks_real_selected_view_and_rejects_binding_race(self):
        view = SimpleNamespace(run_id=self.run.pk, read_identity=dict(id='read', digest='4' * 64))
        with patch.object(scoped_selection, 'selected', return_value=view) as selected:
            run, value, reference = scoped_admission.startup()
            self.assertEqual((run.pk, reference), (self.run.pk, view.read_identity))
            selected.assert_called_once_with()
        with patch.object(scoped_admission, 'binding', side_effect=[(self.run, 'old'), (self.run, 'new')]), \
                patch.object(scoped_selection, 'selected', return_value=view):
            with self.assertRaisesRegex(PublicationUnavailable, 'changed_during'):
                scoped_admission.startup()

    def test_admit_uses_phase_validation_without_completed_day_audit(self):
        with patch.object(scoped_admission, 'startup', return_value=(self.run, 'phase', {'id': 'read'})), \
                patch.object(admission, 'verify') as full:
            result = admission.admit()
        self.assertEqual(result['validation'], 'accepted_phase_metadata')
        self.assertEqual(admission._admitted, 'phase')
        full.assert_not_called()
        with patch.object(scoped_admission, 'startup', side_effect=PublicationUnavailable('source changed')):
            with self.assertRaises(PublicationUnavailable): admission.admit()
        self.assertIsNone(admission._admitted)

    def test_configured_phase_cannot_take_unselected_shell_startup(self):
        with override_settings(VF_MTA_ALLOW_UNSELECTED_STARTUP=True, VF_MTA_DAILY_PUBLICATION=True), \
                patch('release.native_identity.require_current'), \
                patch.object(admission, 'admit', return_value={'phase': 'BPR'}) as admit:
            admission.AdmittedApplication(Mock())
        admit.assert_called_once_with()
