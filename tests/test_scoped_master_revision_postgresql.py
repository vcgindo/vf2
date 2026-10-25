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

    def counter_owner(self):
        from mta.runtime.scope_execution import _claim
        from tests.test_scope_revisions_postgresql import bind_metadata_counter_owner
        from mta.runtime.input_reader import read_input
        from mta.serialization import digest
        self.owner(claim=False)
        configuration = digest(read_input(self.run, components=('profile',))['profile'])
        self.initial, self.state, self.cert, self.base, _ = bind_metadata_counter_owner(
            self.run, self.source, configuration_digest=configuration)
        self.attempt = _claim(self.run.pk, scope='UptoBPR', command_key='prepared-master-component',
            worker_reference='METADATA_COMPONENT_NOT_NATIVE_CERTIFICATION', compatibility_digest='a' * 64,
            expected_phase='START', expected_receipt_digest='')

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
