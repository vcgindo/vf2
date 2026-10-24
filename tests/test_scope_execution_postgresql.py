"""Owned, rolled-back metadata/guard fixtures; no business phase is accepted."""
import os
import unittest
import uuid

if os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
    import django
    django.setup()


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1',
                     'Explicit owned PostgreSQL proof required')
class ScopeExecutionPostgresTests(unittest.TestCase):
    def setUp(self):
        from django.db import connection, transaction
        from mta.runtime.test_mdm_force_capture import ForceCaptureTests
        if connection.settings_dict['NAME'] != 'VFTEST_Fresh_LifecycleG2_20261024':
            raise RuntimeError('Scope proof requires its uniquely owned isolated database')
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        self.addCleanup(self.rollback)
        fixture = ForceCaptureTests()
        fixture.setUp()
        self.run, self.capture = fixture.bind(fixture.snapshot(), revision='scope-guard-'+uuid.uuid4().hex)
        self.compatibility = 'a'*64

    def rollback(self):
        from django.db import transaction
        transaction.set_rollback(True)
        self.atomic.__exit__(None, None, None)

    def claim(self, **changes):
        from mta.runtime.scope_execution import _claim
        arguments = dict(scope='UptoBPR', command_key='owned-scope-guard',
            worker_reference='rolled-back-metadata-fixture', compatibility_digest=self.compatibility,
            expected_phase='START', expected_receipt_digest='')
        arguments.update(changes)
        return _claim(self.run.pk, **arguments)

    def deny_sql(self, sql, arguments=()):
        from django.db import connection, DatabaseError, transaction
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(sql, arguments)

    def test_exact_claim_has_one_active_worker_and_frozen_input(self):
        from mta.runtime.scope_execution import require_claim, head
        attempt = self.claim()
        self.assertEqual(head(self.run.pk), ('START', ''))
        self.assertEqual(require_claim(attempt.pk, attempt.worker_token,
            compatibility_digest=self.compatibility)[0].pk, attempt.pk)
        with self.assertRaisesRegex(ValueError, 'active worker'):
            self.claim(command_key='other-command')
        for field, value in (('input_digest', 'b'*64), ('status', 'FAILED')):
            self.deny_sql('UPDATE mta.fresh_mta_calculationrun SET '+field+'=%s WHERE id=%s',
                          [value, self.run.pk])
        self.deny_sql("UPDATE mta.fresh_mta_mdmdailyinputcapture SET status='CONSUMED' WHERE id=%s",
                      [self.capture.pk])
        self.deny_sql('DELETE FROM mta.fresh_mta_runscopeattempt WHERE id=%s', [attempt.pk])

    def test_wrong_scope_head_and_stale_worker_are_denied(self):
        from django.db import DatabaseError, transaction
        from mta.runtime.scope_execution import require_claim
        with self.assertRaisesRegex(ValueError, 'phase changed'):
            self.claim(expected_phase='BPR')
        with self.assertRaises(DatabaseError), transaction.atomic():
            self.claim(scope='PostBPR')
        attempt = self.claim()
        with self.assertRaisesRegex(ValueError, 'Stale'):
            require_claim(attempt.pk, uuid.uuid4(), compatibility_digest=self.compatibility)
        with self.assertRaisesRegex(ValueError, 'Stale'):
            require_claim(attempt.pk, attempt.worker_token, compatibility_digest='b'*64)

    def test_explicit_fencing_retains_linear_retry_and_denies_old_token(self):
        from django.utils import timezone
        from mta.runtime.scope_execution import _setting, require_claim
        attempt = self.claim()
        self.deny_sql("UPDATE mta.fresh_mta_runscopeattempt SET status='FAILED', failure=%s, "
            'finished_at=now() WHERE id=%s', ['{"reason":"unfenced"}', attempt.pk])
        with _setting('fresh.scope_fence', attempt.pk):
            attempt.status = 'FAILED'
            attempt.failure = dict(type='FENCED', message='Explicit metadata-fixture recovery')
            attempt.finished_at = timezone.now()
            attempt.save(update_fields=['status', 'failure', 'finished_at'])
        with self.assertRaisesRegex(ValueError, 'Stale'):
            require_claim(attempt.pk, attempt.worker_token, compatibility_digest=self.compatibility)
        with self.assertRaisesRegex(ValueError, 'requires its recorded'):
            self.claim()
        with self.assertRaisesRegex(ValueError, 'cannot change'):
            self.claim(recovery_of=attempt.pk, compatibility_digest='b'*64)
        retry = self.claim(recovery_of=attempt.pk)
        self.assertEqual(retry.attempt_no, 2)
        self.assertEqual(retry.recovery_of_id, attempt.pk)
        self.assertNotEqual(retry.worker_token, attempt.worker_token)
        self.deny_sql('UPDATE mta.fresh_mta_runscopeattempt SET worker_reference=%s WHERE id=%s',
                      ['changed-owner', retry.pk])
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'FAILED')

    def test_unsealed_phase_cannot_commit_and_rolls_back_with_its_rows(self):
        from django.db import connection, DatabaseError, transaction
        from mta.runtime.scope_execution import _setting, _begin_phase, head
        from mta.runtime.models import RunPhaseAcceptance
        attempt = self.claim()
        with self.assertRaisesRegex(DatabaseError, 'seal before commit'), transaction.atomic():
            with _setting('fresh.scope_worker', attempt.worker_token):
                pending = _begin_phase(attempt, self.run, 'PRE_BPR')
                # Actual typed storage, intentionally no phase effects or receipt seal.
                with connection.cursor() as cursor:
                    cursor.execute('INSERT INTO mta_state.phase_sourcing '
                        '(vf_run_id,vf_image,vf_ordinal,sku_code) VALUES (%s,%s,0,%s)',
                        [self.run.pk, 'phase/PRE_BPR/old_sourcing', 'OWNED-GUARD'])
                    cursor.execute('SET CONSTRAINTS phase_acceptance_complete IMMEDIATE')
        self.assertFalse(RunPhaseAcceptance.objects.filter(run=self.run).exists())
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM mta_state.phase_sourcing WHERE vf_run_id=%s', [self.run.pk])
            self.assertEqual(cursor.fetchone()[0], 0)
        self.assertEqual(head(self.run.pk), ('START', ''))

    def test_phase_writes_require_exact_pending_unit_and_worker(self):
        from django.db import DatabaseError, transaction
        from mta.runtime.scope_execution import _setting, _begin_phase
        attempt = self.claim()
        sql = ('INSERT INTO mta_state.phase_sourcing '
               '(vf_run_id,vf_image,vf_ordinal) VALUES (%s,%s,0)')
        self.deny_sql(sql, [self.run.pk, 'phase/PRE_BPR/old_sourcing'])
        with _setting('fresh.scope_worker', attempt.worker_token):
            with self.assertRaises(DatabaseError), transaction.atomic():
                _begin_phase(attempt, self.run, 'BPR')
            with transaction.atomic():
                _begin_phase(attempt, self.run, 'PRE_BPR')
                with _setting('fresh.scope_worker', uuid.uuid4()):
                    self.deny_sql(sql, [self.run.pk, 'phase/PRE_BPR/old_sourcing'])
                transaction.set_rollback(True)

    def test_calculation_release_cannot_claim_a_missing_target(self):
        from mta.runtime.scope_execution import _setting
        attempt = self.claim()
        with _setting('fresh.scope_worker', attempt.worker_token):
            self.deny_sql("UPDATE mta.fresh_mta_runscopeattempt SET status='RELEASED', "
                          'finished_at=now() WHERE id=%s', [attempt.pk])

    def test_public_transaction_owners_reject_nested_transactions(self):
        from mta.runtime import scope_execution as scopes
        for operation in (
            lambda: scopes.claim(self.run.pk, scope='UptoBPR', command_key='nested',
                worker_reference='nested', compatibility_digest=self.compatibility,
                expected_phase='START', expected_receipt_digest=''),
            lambda: scopes.fail(uuid.uuid4(), uuid.uuid4(), compatibility_digest=self.compatibility,
                                error=ValueError('fixture')),
            lambda: scopes.fence(uuid.uuid4(), expected_worker_token=uuid.uuid4(), reason='fixture'),
            lambda: scopes.release(uuid.uuid4(), uuid.uuid4(), compatibility_digest=self.compatibility),
        ):
            with self.assertRaisesRegex(ValueError, 'short transaction'):
                operation()


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1',
                     'Explicit owned PostgreSQL proof required')
class ScopeSnapshotWiringTests(unittest.TestCase):
    def test_real_typed_snapshots_seal_in_order_under_one_worker(self):
        """Rolled-back ledger wiring only; synthetic effect hashes prove no effects."""
        from django.db import connection, DatabaseError, transaction
        from mta.application.native_output_contracts import native_assignments
        from mta.application.stage_calculation_sources import capture_bpr
        from mta.mdm.daily_input import bind_capture
        from mta.runtime import phase_state
        from mta.runtime.input_storage import save_input
        from mta.runtime.models import CalculationRun
        from mta.runtime.production_daily import input_table
        from mta.runtime.scope_execution import _claim, _setting, _begin_phase, _seal_phase, head
        from mta.runtime.test_mdm_force_capture import ForceCaptureTests
        from mta.serialization import digest
        from mta.temporal import chain
        from tests.test_phase_state import native_prepared
        if connection.settings_dict['NAME'] != 'VFTEST_Fresh_LifecycleG2_20261024':
            raise RuntimeError('Scope wiring requires its uniquely owned isolated database')
        with transaction.atomic(), native_assignments(True):
            fixture = ForceCaptureTests()
            fixture.setUp()
            snapshot = fixture.snapshot()
            identity = uuid.uuid4()
            prepared, opening, refs = native_prepared(str(identity))
            raw = dict(profile=refs['profile'], day=refs['day'], mdm_input=snapshot,
                opening=dict(identity='scope-wiring-fixture', opening_date='2037-04-09', state=refs['prior']))
            run = CalculationRun.objects.create(id=identity, input_digest=digest(raw),
                execution_revision='scope-wiring-'+identity.hex, business_date='2037-04-10',
                kind='DAILY_CHAIN', input_payload={})
            run.input_payload = save_input(run, raw, table_selector=input_table)
            run.input_manifest_digest = digest(run.input_payload)
            run.save(update_fields=['input_payload', 'input_manifest_digest'])
            capture = bind_capture(run, snapshot, request_digest='d'*64)
            attempt = _claim(run.pk, scope='UptoDBM', command_key='scope-wiring',
                worker_reference='rolled-back-storage-fixture', compatibility_digest='a'*64,
                expected_phase='START', expected_receipt_digest='')
            parent = None
            with _setting('fresh.scope_worker', attempt.worker_token):
                for phase_name in ('PRE_BPR', 'BPR', 'DBM'):
                    if phase_name == 'BPR':
                        prepared = chain.produce_bpr(prepared)
                        sources = capture_bpr(prepared, opening)
                    elif phase_name == 'DBM':
                        prepared = chain.produce_dbm(prepared)
                    else:sources = None
                    receipt = _begin_phase(attempt, run, phase_name)
                    image = phase_state.save(run, prepared, sources, parent=parent, acceptance=receipt)
                    _seal_phase(receipt, image, effect_digest=digest(dict(fixture='NO-BUSINESS-EFFECTS')),
                                partitions=[])
                    self.assertEqual(head(run.pk), (phase_name, receipt.digest))
                    self.assertEqual(image.acceptance_id, receipt.pk)
                    with connection.cursor() as cursor:
                        cursor.execute('SET CONSTRAINTS phase_acceptance_complete IMMEDIATE')
                        cursor.execute('SET CONSTRAINTS phase_acceptance_complete DEFERRED')
                    with self.assertRaises(DatabaseError), transaction.atomic():
                        type(receipt).objects.filter(pk=receipt.pk).update(digest='0'*64)
                    parent = image
            capture.refresh_from_db()
            run.refresh_from_db()
            self.assertEqual(capture.status, 'CAPTURED')
            self.assertEqual(run.status, 'RUNNING')
            self.assertFalse(run.output_digest)
            self.assertFalse(run.checkpoints.exists())
            transaction.set_rollback(True)
