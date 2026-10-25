"""Prepared master metadata over actual typed phases; not native certification."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from tests import test_prepared_effects_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class ScopedMasterRevisionTests(unittest.TestCase):
    for name in ('setUp', 'rollback', 'owner', 'accept'):
        locals()[name] = getattr(fixtures.PreparedEffectsPostgresTests, name)

    def counter_owner(self, scope='UptoBPR'):
        from mta.runtime.scope_execution import _claim
        from tests.test_scope_revisions_postgresql import bind_metadata_counter_owner
        from mta.runtime.input_reader import read_input
        from mta.serialization import digest
        self.owner(claim=False)
        configuration = digest(read_input(self.run, components=('profile',))['profile'])
        self.initial, self.state, self.cert, self.base, _ = bind_metadata_counter_owner(
            self.run, self.source, configuration_digest=configuration)
        self.attempt = _claim(self.run.pk, scope=scope, command_key='prepared-master-component',
            worker_reference='METADATA_COMPONENT_NOT_NATIVE_CERTIFICATION', compatibility_digest='a' * 64,
            expected_phase='START', expected_receipt_digest='')

    def dbm_basis(self):
        from mta.runtime import master_revisions
        from mta.temporal.chain import produce_bpr, produce_dbm
        from mta.application.native_output_contracts import native_assignments
        from mta.application.stage_calculation_sources import capture_bpr
        from mta.runtime.calculation_effects import _accept_calculation
        self.counter_owner(scope='UptoDBM')
        prepared = self.accept()
        master_revisions._accept_phase(prepared, self.initial)
        with native_assignments(True):
            bpr = produce_bpr(self.prepared)
        sources = capture_bpr(bpr, bpr.context.prior)
        phase = _accept_calculation(self.attempt.pk, self.attempt.worker_token, bpr, sources,
                                   parent=prepared, compatibility_digest='a' * 64)
        master_revisions._accept_phase(phase, self.initial)
        with native_assignments(True):
            dbm = produce_dbm(bpr)
        return phase, dbm, sources

    def test_dbm_metadata_publication_is_atomic_and_rolls_back_with_its_phase(self):
        from mta.runtime import master_revisions
        from mta.runtime.calculation_effects import _accept_calculation
        from mta.runtime.ingestion_models import MasterInputRevision
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.models import RunPhaseAcceptance, DailyPhaseSnapshot
        from tests.test_calculation_effects_postgresql import CalculationEffectsPostgresTests
        bpr, dbm, sources = self.dbm_basis()
        def state():
            return (require_current(self.run), list(MasterInputRevision.objects.filter(
                initialization=self.initial).order_by('id').values()),
                list(RunPhaseAcceptance.objects.filter(run=self.run).order_by('id').values()),
                list(DailyPhaseSnapshot.objects.filter(run=self.run).order_by('id').values()))
        old = state()
        def publish(phase):
            return master_revisions._accept_phase(phase, self.initial)
        def fail_after_append(phase):
            publish(phase)
            raise OSError('after DBM master metadata')
        with patch('mta.runtime.master_revisions.accept_phase', side_effect=fail_after_append), \
                self.assertRaisesRegex(OSError, 'after DBM master metadata'):
            _accept_calculation(self.attempt.pk, self.attempt.worker_token, dbm, sources,
                                parent=bpr, compatibility_digest='a' * 64)
        self.assertEqual(state(), old)
        with patch('mta.runtime.master_revisions.accept_phase', side_effect=publish) as publication:
            phase = _accept_calculation(self.attempt.pk, self.attempt.worker_token, dbm, sources,
                                       parent=bpr, compatibility_digest='a' * 64)
        publication.assert_called_once_with(phase)
        current = MasterInputRevision.objects.get(initialization=self.initial,
            master_epoch=phase.metadata['revision_after'][0], status='ACCEPTED')
        self.assertEqual(current.partitions['phase_id'], str(phase.pk))
        self.assertEqual(master_revisions.validate(current.partitions, self.initial.pk).pk, self.run.pk)
        CalculationEffectsPostgresTests.assert_copies(self, 'DBM', dbm.final_dbm)
        self.assertEqual(require_current(self.run), phase.metadata['revision_after'])

    def test_released_dbm_metadata_preserves_receipts_and_rejects_unowned_changes(self):
        from django.db import connection, transaction
        from mta.runtime import master_revisions
        from mta.runtime.calculation_effects import _accept_calculation
        from mta.runtime.scope_execution import _setting, _close_attempt
        from mta.runtime.models import RunPhaseAcceptance
        from mta.runtime.ingestion_models import MasterInputRevision
        bpr, dbm, sources = self.dbm_basis()
        # Reproduce the old implementation's omitted metadata, not a new acceptance policy.
        with patch('mta.runtime.master_revisions.accept_phase', return_value=None):
            phase = _accept_calculation(self.attempt.pk, self.attempt.worker_token, dbm, sources,
                                       parent=bpr, compatibility_digest='a' * 64)
        with self.assertRaisesRegex(ValueError, 'released current UptoDBM'):
            master_revisions._accept_phase(phase, self.initial, released_dbm=True)
        with _setting('fresh.scope_worker', self.attempt.worker_token):
            _close_attempt(self.attempt, self.run, 'RELEASED', {})
        before = list(RunPhaseAcceptance.objects.filter(run=self.run).order_by('id').values())
        count = MasterInputRevision.objects.filter(initialization=self.initial).count()
        with self.assertRaisesRegex(ValueError, 'exact owned acceptance cut'):
            master_revisions._accept_phase(phase, self.initial)
        candidate = master_revisions._accept_phase(phase, self.initial, released_dbm=True)
        self.assertEqual(master_revisions._accept_phase(phase, self.initial, released_dbm=True).pk,
                         candidate.pk)
        self.assertEqual(MasterInputRevision.objects.filter(initialization=self.initial).count(), count + 1)
        self.assertEqual(list(RunPhaseAcceptance.objects.filter(run=self.run).order_by('id').values()), before)
        for column in ('master_epoch', 'configuration_epoch', 'operational_epoch'):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('UPDATE mta.fresh_mta_ingestionrevisionstate SET '+column+'='+column+'+1 '
                                   'WHERE initialization_id=%s', [self.initial.pk])
                with self.assertRaisesRegex(ValueError, 'revision changed'):
                    master_revisions._accept_phase(phase, self.initial, released_dbm=True)
                transaction.set_rollback(True)

    def test_phase_metadata_is_current_repeatable_and_does_not_complete_the_day(self):
        from mta.runtime import master_revisions
        from mta.runtime.ingestion_admission import receipt, REVISION_FIELDS
        from mta.runtime.ingestion_models import MasterInputRevision
        self.counter_owner()
        phase = self.accept()
        candidate = master_revisions._accept_phase(phase, self.initial)
        self.assertNotEqual(candidate.pk, self.base.pk)
        self.assertEqual(candidate.parent_id, self.base.pk)
        self.state.refresh_from_db()
        self.assertEqual((candidate.master_epoch, candidate.configuration_epoch),
                         (self.state.master_epoch, self.state.configuration_epoch))
        self.assertEqual(candidate.status, 'ACCEPTED')
        self.assertEqual(master_revisions.validate(candidate.partitions, self.initial.pk).pk, self.run.pk)
        body = MasterInputRevision.objects.filter(pk=candidate.pk).values(*REVISION_FIELDS).get()
        self.assertEqual(candidate.receipt_digest, receipt(body))
        self.assertEqual(master_revisions._accept_phase(phase, self.initial).pk, candidate.pk)
        self.run.refresh_from_db(); self.capture.refresh_from_db()
        self.assertEqual((self.run.status, self.capture.status), ('RUNNING', 'CAPTURED'))
        self.assertFalse(self.run.output_digest)
        self.assertFalse(self.run.checkpoints.exists())

    def test_changed_roots_or_snapshot_or_other_initialization_are_denied(self):
        from mta.runtime import master_revisions
        self.counter_owner()
        phase = self.accept()
        candidate = master_revisions._accept_phase(phase, self.initial)
        for key in ('source_digest', 'input_manifest_digest', 'phase_digest', 'snapshot_digest'):
            value = deepcopy(candidate.partitions); value[key] = '0' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                master_revisions.validate(value, self.initial.pk)
        value = deepcopy(candidate.partitions); value['roots']['MasterData']['count'] += 1
        with self.assertRaises(ValueError):
            master_revisions.validate(value, self.initial.pk)
        value = deepcopy(candidate.partitions); value['revision_cut'][0] += 1
        with self.assertRaises(ValueError):
            master_revisions.validate(value, self.initial.pk)

    def test_bpr_projection_gets_its_own_current_cut_and_unknown_writes_cannot_be_adopted(self):
        from django.db import connection, transaction
        from mta.runtime import master_revisions
        from mta.temporal.chain import produce_bpr
        from mta.application.native_output_contracts import native_assignments
        from mta.application.stage_calculation_sources import capture_bpr
        from mta.runtime.calculation_effects import _accept_calculation
        self.counter_owner()
        prepared = self.accept()
        first = master_revisions._accept_phase(prepared, self.initial)
        with native_assignments(True):
            bpr = produce_bpr(self.prepared)
        sources = capture_bpr(bpr, {'supplier': bpr.context.prior['supplier']})
        phase = _accept_calculation(self.attempt.pk, self.attempt.worker_token, bpr, sources,
                                   parent=prepared, compatibility_digest='a' * 64)
        current = master_revisions._accept_phase(phase, self.initial)
        self.assertNotEqual(current.pk, first.pk)
        self.assertEqual(current.parent_id, first.pk)
        self.assertEqual(current.partitions['phase_id'], str(phase.pk))
        self.assertEqual(master_revisions.validate(current.partitions, self.initial.pk).pk, self.run.pk)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('UPDATE mta.fresh_mta_ingestionrevisionstate SET master_epoch=master_epoch+1 '
                               'WHERE initialization_id=%s', [self.initial.pk])
            with self.assertRaisesRegex(ValueError, 'revision changed'):
                master_revisions._accept_phase(phase, self.initial)
            transaction.set_rollback(True)
        self.assertEqual(master_revisions._accept_phase(phase, self.initial).pk, current.pk)

    def test_late_master_publication_failure_rolls_back_prepared_effects_and_phase(self):
        from mta.runtime.models import RunPhaseAcceptance, DailyPhaseSnapshot
        from mta.runtime.mdm_models import MdmSkuApproved, MdmSkuDescription
        from mta.serialization import digest
        self.counter_owner()
        def before():
            self.state.refresh_from_db()
            return dict(approved=digest(list(MdmSkuApproved.objects.filter(source=self.source).order_by('id').values())),
                descriptions=digest(list(MdmSkuDescription.objects.filter(source=self.source).order_by('id').values())),
                epochs=[getattr(self.state, key) for key in ('master_epoch', 'configuration_epoch',
                    'fact_epoch', 'operational_epoch', 'action_epoch')])
        old = before()
        with patch('mta.runtime.master_revisions.accept_phase', side_effect=OSError('late master receipt fault')), \
                self.assertRaisesRegex(OSError, 'late master receipt fault'):
            self.accept()
        self.assertEqual(before(), old)
        self.assertFalse(RunPhaseAcceptance.objects.filter(run=self.run).exists())
        self.assertFalse(DailyPhaseSnapshot.objects.filter(run=self.run).exists())
        self.assertTrue(self.accept().state_sealed)
