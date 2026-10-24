"""Actual migrated row/readback/ownership proofs in the one owned G2 test DB."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

if os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
    import django
    django.setup()


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1',
                     'Explicit owned PostgreSQL proof required')
class PhaseStatePostgresTests(unittest.TestCase):
    def setUp(self):
        from django.db import connection, transaction
        if connection.settings_dict['NAME'] != 'VFTEST_Fresh_LifecycleG2_20261024':
            raise RuntimeError('Phase proof requires its uniquely owned isolated database')
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        self.addCleanup(self.rollback)

    def rollback(self):
        from django.db import transaction
        transaction.set_rollback(True)
        self.atomic.__exit__(None, None, None)

    def owner(self, *, prepared=False):
        from uuid import uuid4
        from mta.runtime.models import CalculationRun
        from mta.runtime.input_storage import save_input
        from mta.runtime.production_daily import input_table
        from mta.application.native_output_contracts import native_assignments
        from mta.serialization import digest
        from tests.test_phase_state import native_bpr, native_prepared
        identity = uuid4()
        with native_assignments(True):
            phase, sources, refs = (native_prepared if prepared else native_bpr)(str(identity))
        raw = dict(profile=refs['profile'], day=refs['day'],
            opening=dict(identity='phase-supplied-fixture', opening_date='2037-04-09', state=refs['prior']))
        run = CalculationRun.objects.create(id=identity, input_digest=digest(raw),
            execution_revision='native-phase-storage-proof-'+identity.hex[:12], business_date='2037-04-10',
            kind='DAILY_CHAIN', input_payload={})
        run.input_payload = save_input(run, raw, table_selector=input_table)
        run.input_manifest_digest = digest(run.input_payload)
        run.save(update_fields=['input_payload', 'input_manifest_digest'])
        return run, phase, sources

    def references(self, run):
        from mta.runtime.input_reader import read_input
        raw = read_input(run)
        return dict(prior=raw['opening']['state'], day=raw['day'], profile=raw['profile'],
                    master_snapshot=None)

    def test_native_bpr_dbm_typed_readers_match_full_terminal_projection(self):
        from mta.runtime import phase_state
        from mta.application.native_output_contracts import native_assignments
        from mta.temporal import chain
        from mta.serialization import storage
        from mta.runtime.relational_state import production_projection
        run, bpr, sources = self.owner()
        with native_assignments(True):
            expected = chain.produce_btr(chain.produce_dbm(deepcopy(bpr)))
            first = phase_state.save(run, bpr, sources)
            restored, captured = phase_state.read(first, **self.references(run))
            self.assertIsNone(restored.calculated)
            dbm = chain.produce_dbm(restored)
            second = phase_state.save(run, dbm, captured, parent=first)
            terminal, captured = phase_state.read(second, **self.references(run))
            result = chain.produce_btr_from_snapshot(terminal, captured,
                pick_source_digests=second.manifest['metadata']['pick_source_digests'])
        self.assertEqual(storage(production_projection(result.output)),
                         storage(production_projection(expected)))
        self.assertEqual(storage(result.calculation_sources.__dict__), storage(sources.__dict__))
        self.assertEqual(second.manifest['images']['phase/DBM/bpr_master'],
                         first.manifest['images']['phase/BPR/bpr_master'])
        self.assertNotIn('SUPPLIED-Z9', str(second.manifest))
        run.refresh_from_db()
        self.assertEqual(run.status, 'RUNNING')
        self.assertFalse(run.output_digest)
        self.assertFalse(run.checkpoints.exists())

    def test_prepared_native_rows_continue_through_bpr_without_repeating_intake(self):
        from django.db import connection, DatabaseError, transaction
        from mta.runtime import phase_state
        from mta.application.native_output_contracts import native_assignments
        from mta.application.stage_calculation_sources import capture_bpr
        from mta.temporal import chain
        from mta.serialization import storage
        from tests.test_daily_calculation_phases import calculation
        run, prepared, opening = self.owner(prepared=True)
        with native_assignments(True):
            expected_bpr = chain.produce_bpr(deepcopy(prepared))
            expected_sources = capture_bpr(expected_bpr, opening)
            expected = chain.produce_btr(chain.produce_dbm(expected_bpr))
            before_bpr = phase_state.save(run, prepared, None)
            restored, absent = phase_state.read(before_bpr, **self.references(run),
                                                execute_calculation=calculation)
            self.assertIsNone(absent)
            with patch('mta.temporal.entry_preparation.prepare', side_effect=AssertionError('intake replay')):
                bpr = chain.produce_bpr(restored)
            sources = capture_bpr(bpr, opening)
            first = phase_state.save(run, bpr, sources, parent=before_bpr)
            restored, sources = phase_state.read(first, **self.references(run))
            dbm = chain.produce_dbm(restored)
            second = phase_state.save(run, dbm, sources, parent=first)
            restored, sources = phase_state.read(second, **self.references(run))
            result = chain.produce_btr_from_snapshot(restored, sources,
                pick_source_digests=second.manifest['metadata']['pick_source_digests'])
        from mta.runtime.relational_state import production_projection
        self.assertEqual(storage(production_projection(result.output)), storage(production_projection(expected)))
        self.assertEqual(storage(sources.__dict__), storage(expected_sources.__dict__))
        self.assertEqual(first.parent_id, before_bpr.pk)
        self.assertEqual(first.manifest['images']['phase/BPR/importer/MasterData'],
                         before_bpr.manifest['images']['phase/PRE_BPR/importer/MasterData'])
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('UPDATE mta_state.phase_sourcing SET moq=999 '
                    "WHERE vf_run_id=%s AND vf_image='phase/PRE_BPR/old_sourcing'", [run.pk])
        run.refresh_from_db()
        self.assertEqual(run.status, 'RUNNING')
        self.assertFalse(run.checkpoints.exists())

    def test_actual_snapshot_and_rows_are_immutable_while_day_is_running(self):
        from django.db import connection, DatabaseError, transaction
        from mta.runtime import phase_state
        from mta.runtime.models import DailyPhaseSnapshot
        run, bpr, sources = self.owner()
        snapshot = phase_state.save(run, bpr, sources)
        cases = [
            ('UPDATE mta.fresh_mta_dailyphasesnapshot SET state_digest=%s WHERE id=%s', ['0'*64, snapshot.pk]),
            ('DELETE FROM mta.fresh_mta_dailyphasesnapshot WHERE id=%s', [snapshot.pk]),
            ('UPDATE mta_state.bpr_bprmaster SET "Norm"=999 WHERE vf_run_id=%s AND vf_image=%s',
             [run.pk, 'phase/BPR/bpr_master']),
            ('DELETE FROM mta_state.bpr_bprmaster WHERE vf_run_id=%s AND vf_image=%s',
             [run.pk, 'phase/BPR/bpr_master']),
            ('INSERT INTO mta_state.phase_pickband(vf_run_id,vf_image,vf_ordinal) VALUES (%s,%s,999)',
             [run.pk, 'phase/BPR/sources/pick']),
            ('TRUNCATE mta_state.phase_pickband', []),
            ('TRUNCATE mta.fresh_mta_dailyphasesnapshot', []),
        ]
        for query, parameters in cases:
            with self.subTest(query=query), self.assertRaises(DatabaseError), transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(query, parameters)
        self.assertEqual(DailyPhaseSnapshot.objects.filter(run=run).count(), 1)
        phase_state.read(snapshot, **self.references(run))

    def test_late_failure_rolls_back_images_even_when_caller_catches_it(self):
        from django.db import connection
        from mta.runtime import phase_state
        from mta.runtime.models import DailyPhaseSnapshot
        run, bpr, sources = self.owner()
        original = phase_state._write_rows
        calls = []
        def fail_late(*args):
            calls.append(args[1])
            if len(calls) == 6:raise RuntimeError('deliberate phase image failure')
            return original(*args)
        with patch.object(phase_state, '_write_rows', side_effect=fail_late), \
                self.assertRaisesRegex(RuntimeError, 'deliberate phase'):
            phase_state.save(run, bpr, sources)
        self.assertEqual(len(calls), 6)
        self.assertFalse(DailyPhaseSnapshot.objects.filter(run=run).exists())
        with connection.cursor() as cursor:
            for table in {meta for meta in phase_state.REGISTRY}:
                cursor.execute('SELECT 1 FROM '+phase_state.typed.table_sql(table)+
                    " WHERE vf_run_id=%s AND vf_image LIKE 'phase/%%' LIMIT 1", [run.pk])
                self.assertIsNone(cursor.fetchone(), table)

    def test_typed_columns_preserve_nulls_duplicates_and_ordinals(self):
        from mta.runtime import phase_state
        run, _, _ = self.owner()
        for table in phase_state.TABLES:
            fields = phase_state.TABLES[table]
            row = {name: 17 if kind == 'bigint' else '17.125' if kind == 'numeric' else 'Text  '
                   for name, kind in fields}
            values = [row, deepcopy(row), {name: None for name, _ in fields}]
            metadata = phase_state._write_rows(run, 'phase/BPR/test/'+table.rsplit('/', 1)[-1],
                                             table, values)
            self.assertEqual(phase_state.typed.load_image(run, metadata,
                             table_registry=phase_state.REGISTRY), values)
