"""Real migrated PostgreSQL ownership proofs in a uniquely owned disposable DB.

These test storage authority, not calculation acceptance or legacy parity.
No cleanup/flush is attempted against immutable historical owners.
"""
import os
import unittest
from datetime import date
from importlib import import_module
from uuid import uuid4
from contextlib import contextmanager, ExitStack
from types import SimpleNamespace
from unittest.mock import patch, Mock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.db import connection, transaction, DatabaseError
from mta.runtime.models import CalculationRun, RunCommand, PickBand, PickProjection, Checkpoint
from mta.runtime.relational_state import STORAGE_TABLES, table_name, save_image


@unittest.skipUnless(os.environ.get('VF_RUN_ACCEPTED_STATE_PROOF') == '1'
                     and not os.environ.get('VF_DB_NAME', '').endswith('_upgrade'),
                     'Explicit uniquely owned migration-enabled PostgreSQL proof only')
class AcceptedStateOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        assert connection.vendor == 'postgresql'
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            name = cursor.fetchone()[0]
            assert name in ('VFTEST_Fresh_LifecycleG1_20261024',
                            'VFTEST_Fresh_LifecycleG1_20261024_upgrade'), name
            cursor.execute("SELECT count(*) FROM mta.django_migrations WHERE app='fresh_mta' "
                           "AND name='0169_accepted_state_ownership'")
            assert cursor.fetchone() == (1,)

    def run_owner(self, status='RUNNING', **values):
        return CalculationRun.objects.create(input_digest=uuid4().hex * 2,
            execution_revision='ownership-' + uuid4().hex, business_date=date(2026, 4, 8),
            kind='DAILY_CHAIN', input_payload={}, status=status, **values)

    def sql(self, query, params=()):
        with connection.cursor() as cursor:
            cursor.execute(query, params)

    def denied(self, query, params=(), message=None):
        with self.assertRaises(DatabaseError) as caught:
            with transaction.atomic():
                self.sql(query, params)
        if message:
            self.assertIn(message, str(caught.exception))

    def command(self, run, operation='APPLY'):
        return RunCommand.objects.create(run=run, idempotency_key=uuid4().hex,
            payload=dict(operation=operation, selected=[], timestamp='2026-04-08T01:00:00', actor='proof'),
            digest='a'*64, before_digest='b'*64, after_digest='c'*64,
            state_sealed=False)

    def manifest(self, run, event, family='NormAcceptanceTbl', *, nonempty=False):
        domain = 'orders' if family == 'ElephantOrders' else 'dbm'
        key = ('BPR/' if family == 'ElephantOrders' else 'DBM/') + family
        rows = [{field: None for field, _ in STORAGE_TABLES[key]}] if nonempty else []
        return {family: save_image(run, 'action/' + str(event.pk) + '/' + family,
                                   'closing/' + domain + '/' + family, rows)}

    def seal(self, event, manifest):
        event.state_manifest = manifest
        event.save(update_fields=['state_manifest'])
        event.refresh_from_db()
        self.assertTrue(event.state_sealed)

    def test_frozen_typed_roster_covers_current_storage_and_export_tables(self):
        migration = import_module('mta.runtime.migrations.0169_accepted_state_ownership')
        self.assertEqual(set(migration.TYPED_TABLES),
            {table_name(key) for key in STORAGE_TABLES} | {'report_export_row', 'report_export_cell'})

    def test_portable_transition_delta_matches_every_actual_changed_catalogue_entry(self):
        from release.advance_ingestion import catalogue, catalogue_delta
        from mta.runtime.accepted_state_transition import catalogue_delta as expected_delta
        from mta.runtime.accepted_state_ownership import verify_guards
        from mta.serialization import storage
        frozen=import_module('mta.runtime.migrations.0169_accepted_state_ownership')
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SELECT current_user'); owner=cursor.fetchone()[0]
            after=catalogue(cursor)
            # Reverse only the declared new objects within this rollback. This
            # builds the before catalogue without rewriting migration history or
            # retaining any DDL/data changes in this uniquely owned proof DB.
            cursor.execute(frozen.REVERSE)
            cursor.execute('ALTER TABLE mta.fresh_mta_runcommand DROP COLUMN state_sealed')
            before=catalogue(cursor)
            self.assertEqual(storage(catalogue_delta(before,after)), expected_delta(owner=owner))
            transaction.set_rollback(True)
        with connection.cursor() as cursor:
            self.assertTrue(verify_guards(cursor))

    def test_maintenance_scope_requires_both_real_session_locks_and_cleans_up(self):
        """Real PG lock/stamp boundary; stubbed admission is NOT certification."""
        from mta.presentation import report_verification as verification
        from mta.runtime.opening_scope import _current as opening_current
        from mta.runtime.daily_feed import job_lock
        from mta.mdm.supplier_revisions import source_lock, _key
        owner=SimpleNamespace(pk=uuid4(),source_id=uuid4())
        release={'isolated':'LOCK_MECHANICS_ONLY'}
        admission=object()
        visits=[]

        @contextmanager
        def audit(run,actual_owner,admitted,check,stamp,stamp_reader):
            self.assertIs(actual_owner,owner)
            self.assertIs(admitted,admission)
            self.assertIsNotNone(opening_current.get())
            check()
            token=verification._current.set({'isolated_test':True})
            try:
                visits.append('entered')
                yield
                check()
                if stamp_reader()!=stamp:
                    raise ValueError('Isolated test catalogue stamp changed')
            finally:
                verification._current.reset(token)

        with ExitStack() as stack:
            stack.enter_context(patch('release.native_identity.require_current',return_value=release))
            provisioner=stack.enter_context(patch('mta.runtime.ingestion_authority._provisioner'))
            admit=stack.enter_context(patch('mta.runtime.ingestion_admission._admit',return_value=admission))
            stack.enter_context(patch.object(verification,'_verified_owner',side_effect=audit))
            for mode in ('missing-daily','missing-source','complete','lost-source','catalogue-drift','audit-error'):
                with self.subTest(mode=mode), ExitStack() as locks:
                    if mode!='missing-daily':
                        check_session=locks.enter_context(job_lock(owner))
                    else:
                        check_session=Mock()
                    if mode!='missing-source':
                        locks.enter_context(source_lock(owner.source_id))
                    with transaction.atomic():
                        self.sql('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                        if mode.startswith('missing-'):
                            with self.assertRaisesRegex(ValueError,'session/ownership locks'), \
                                 verification._schema_transition_scope(None,owner,release,check_session):
                                self.fail('missing session lock admitted')
                        elif mode=='complete':
                            with verification._schema_transition_scope(None,owner,release,check_session):
                                self.assertIsNotNone(verification._current.get())
                        else:
                            expected={'lost-source':'session/ownership locks',
                                      'catalogue-drift':'catalogue stamp changed',
                                      'audit-error':'audit interrupted'}[mode]
                            with self.assertRaisesRegex(ValueError,expected), \
                                 verification._schema_transition_scope(None,owner,release,check_session):
                                if mode=='lost-source':
                                    self.sql('SELECT pg_advisory_unlock(hashtextextended(%s,0))',[_key(owner.source_id)])
                                elif mode=='catalogue-drift':
                                    self.sql('CREATE TABLE mta.g1_maintenance_stamp_probe (id integer)')
                                else:
                                    raise ValueError('audit interrupted')
                        transaction.set_rollback(True)
                    self.assertIsNone(verification._current.get())
                    self.assertIsNone(opening_current.get())
            self.assertEqual(visits,['entered']*4)
            self.assertTrue(provisioner.called)
            self.assertTrue(all(call.kwargs=={'pending':True} for call in admit.call_args_list))

    def test_installed_guard_recognition_rejects_disable_body_and_execute_grant_drift(self):
        from mta.runtime.accepted_state_ownership import verify_guards
        with connection.cursor() as cursor:
            self.assertTrue(verify_guards(cursor))
        frozen = import_module('mta.runtime.migrations.0169_accepted_state_ownership')
        changes = [
            'ALTER TABLE mta_state.input_string_values DISABLE TRIGGER accepted_rows_insert',
            'DROP TRIGGER accepted_rows_delete ON mta_state.input_string_values',
            'GRANT EXECUTE ON FUNCTION mta.guard_accepted_rows() TO PUBLIC',
            'CREATE OR REPLACE FUNCTION mta.guard_terminal_run() RETURNS trigger LANGUAGE plpgsql '
                'SET search_path=pg_catalog,mta AS $body$BEGIN RETURN NEW; END$body$',
            'CREATE TRIGGER accepted_unexpected AFTER INSERT ON mta_state.input_string_values '
                "REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_accepted_rows('vf_run_id')",
        ]
        for change in changes:
            with self.subTest(change=change), transaction.atomic():
                self.sql(change)
                with connection.cursor() as cursor, self.assertRaisesRegex(ValueError, 'Accepted state'):
                    verify_guards(cursor)
                transaction.set_rollback(True)
        with connection.cursor() as cursor:
            self.assertTrue(verify_guards(cursor))

    def test_running_writes_and_terminal_images_deny_insert_update_delete_rebinding(self):
        run = self.run_owner()
        other = self.run_owner()
        insert = 'INSERT INTO mta_state.input_string_values(vf_run_id,vf_image,vf_ordinal,value) VALUES(%s,%s,%s,%s)'
        self.sql(insert, [run.pk, 'input/test', 0, 'original'])
        self.sql('UPDATE mta_state.input_string_values SET value=%s WHERE vf_run_id=%s', ['working', run.pk])
        run.status = 'SUCCEEDED'; run.save(update_fields=['status'])
        self.denied(insert, [run.pk, 'input/test', 1, 'later'], 'Terminal insert')
        self.denied('UPDATE mta_state.input_string_values SET value=%s WHERE vf_run_id=%s',
                    ['tamper', run.pk], 'immutable')
        self.denied('DELETE FROM mta_state.input_string_values WHERE vf_run_id=%s', [run.pk], 'immutable')
        self.denied('UPDATE mta_state.input_string_values SET vf_run_id=%s WHERE vf_run_id=%s',
                    [other.pk, run.pk], 'immutable')
        self.sql(insert, [other.pk, 'input/other', 0, 'working'])
        self.denied('UPDATE mta_state.input_string_values SET vf_run_id=%s WHERE vf_run_id=%s',
                    [run.pk, other.pk], 'immutable')
        self.denied('TRUNCATE mta_state.input_string_values', message='cannot be truncated')

    def test_failed_origin_rows_and_terminal_header_are_retained(self):
        run = self.run_owner()
        self.sql('INSERT INTO mta_state.input_string_values VALUES(%s,%s,0,%s)', [run.pk, 'input/origin', 'kept'])
        run.status = 'FAILED'; run.save(update_fields=['status'])
        self.denied('UPDATE mta.fresh_mta_calculationrun SET status=%s WHERE id=%s', ['RUNNING', run.pk], 'immutable')
        self.denied('UPDATE mta_state.input_string_values SET value=%s WHERE vf_run_id=%s', ['tamper', run.pk], 'immutable')

    def test_success_header_accepts_only_parity_summary_updates(self):
        run = self.run_owner(status='SUCCEEDED')
        run.parity_summary = {'evidence': 'proof'}; run.save(update_fields=['parity_summary'])
        for field, value in (('output_digest', 'd'*64), ('status', 'RUNNING'),
                             ('production_manifest', '{}')):
            if field == 'production_manifest':
                value = '{"changed":true}'
            self.denied('UPDATE mta.fresh_mta_calculationrun SET ' + field + '=%s WHERE id=%s',
                        [value, run.pk], 'immutable')
        self.denied('DELETE FROM mta.fresh_mta_calculationrun WHERE id=%s', [run.pk], 'immutable')

    def test_pick_and_checkpoint_rows_are_immutable_after_success(self):
        run = self.run_owner()
        PickProjection.objects.create(run=run, calculation_digest='a'*64, rows_digest='b'*64,
                                      row_count=1, provenance={})
        values = dict(run=run, ordinal=0, sku_code='A', location_code='L', parent_location_code='P',
                      **{name: 0 for name in ('to_black','to_red','to_yellow','to_green','to_blue')})
        PickBand.objects.create(**values)
        Checkpoint.objects.create(run=run, name='proof', rows=[], row_count=0, digest='c'*64)
        run.status = 'SUCCEEDED'; run.save(update_fields=['status'])
        for table, field in (('fresh_mta_pickband','ordinal'), ('fresh_mta_pickprojection','version'),
                             ('fresh_mta_checkpoint','row_count')):
            with self.subTest(table=table):
                self.denied('UPDATE mta.' + table + ' SET ' + field + '=' + field + ' WHERE run_id=%s',
                            [run.pk], 'immutable')
                self.denied('DELETE FROM mta.' + table + ' WHERE run_id=%s', [run.pk], 'immutable')
                self.denied('TRUNCATE mta.' + table, message='cannot be truncated')
        with self.assertRaises(DatabaseError), transaction.atomic():
            PickBand.objects.create(**{**values, 'ordinal': 1})

    def test_new_command_must_seal_before_outer_commit_and_cannot_self_mark_sealed(self):
        run = self.run_owner(status='SUCCEEDED')
        for direct_sealed in (False, True):
            with self.subTest(direct_sealed=direct_sealed), self.assertRaises(DatabaseError):
                with transaction.atomic():
                    event = self.command(run)
                    if direct_sealed:
                        self.sql('UPDATE mta.fresh_mta_runcommand SET state_sealed=true WHERE id=%s', [event.pk])
        self.assertFalse(RunCommand.objects.filter(run=run).exists())
        with self.assertRaises(DatabaseError), transaction.atomic():
            RunCommand.objects.create(run=run, idempotency_key=uuid4().hex, payload={},
                digest='a'*64, before_digest='b'*64, after_digest='c'*64)

    def test_apply_sleep_and_no_change_command_seal_and_deny_later_appends(self):
        for operation, family in (('APPLY','NormAcceptanceTbl'), ('SLEEP','Suggestions'),
                                   ('SLEEP','NormsInSleepModeTbl'), ('SLEEP','NormAcceptanceTbl')):
            with self.subTest(operation=operation, family=family):
                run = self.run_owner(status='SUCCEEDED')
                with transaction.atomic():
                    # Nested atomic/savepoint matches the existing HTTP writer.
                    with transaction.atomic():
                        event = self.command(run, operation)
                        manifest = self.manifest(run, event, family, nonempty=True)
                        self.seal(event, manifest)
                table = table_name('DBM/' + family)
                self.denied('INSERT INTO mta_state.' + table + '(vf_run_id,vf_image,vf_ordinal) VALUES(%s,%s,1)',
                    [run.pk, 'action/' + str(event.pk) + '/' + family], 'live unsealed command')
                self.denied('UPDATE mta.fresh_mta_runcommand SET digest=%s WHERE id=%s',
                            ['d'*64, event.pk], 'immutable')
                self.denied('DELETE FROM mta.fresh_mta_runcommand WHERE id=%s', [event.pk], 'retained')
        run = self.run_owner(status='SUCCEEDED')
        with transaction.atomic():
            event = self.command(run)
            self.seal(event, self.manifest(run, event))

    def test_wrong_action_owner_or_unmanifested_population_rolls_back(self):
        run = self.run_owner(status='SUCCEEDED')
        other = self.run_owner(status='SUCCEEDED')
        with self.assertRaises(DatabaseError), transaction.atomic():
            event = self.command(run)
            self.sql('INSERT INTO mta_state.dbm_normacceptancetbl(vf_run_id,vf_image,vf_ordinal) VALUES(%s,%s,0)',
                     [other.pk, 'action/' + str(event.pk) + '/NormAcceptanceTbl'])
        with self.assertRaises(DatabaseError), transaction.atomic():
            event = self.command(run, 'SLEEP')
            self.manifest(run, event, 'Suggestions', nonempty=True)
            self.seal(event, self.manifest(run, event, 'NormAcceptanceTbl'))
        self.assertFalse(RunCommand.objects.filter(run=run).exists())

    def test_existing_writer_reconstructs_apply_sleep_and_elephant_state(self):
        from copy import deepcopy
        from unittest.mock import patch
        from mta.runtime.temporal import record_command, command_states
        initial = {'dbm': {'Suggestions': [{'SKUCode':'A','WhCode':'L','NewNorm':20}],
            'DBMMaster': [{'SKUCode':'A','WhCode':'L','Norm':10}],
            'NormAcceptanceTbl': [], 'NormsInSleepModeTbl': []},
            'orders': {'ElephantOrders': [dict(CustomerOrderID='E1', SKUCode='A', WhCode='L',
                Qty=5, TopmostWhCode='P', TopmostWhNorm=10, RLTUptoSuppOrPlant=2,
                IntroDate='2026-04-08', CustomerExpectedDate=None, DueDate=None)]}}
        for operation in ('APPLY','SLEEP','elephant_due_date'):
            with self.subTest(operation=operation):
                run = self.run_owner(status='SUCCEEDED')
                selected = ([dict(OrderID='E1',SKUCode='A',WhCode='L',DueDate='2026-04-20')]
                            if operation == 'elephant_due_date' else [['A','L']])
                # Supply a small known closing state to exercise the real writer
                # and persisted reader, not a calculation or accepted-day replay.
                with patch('mta.runtime.temporal.read_outputs',
                           return_value={'ClosingState':[deepcopy(initial)]}):
                    event = record_command(run, operation=operation, selected=selected,
                        timestamp='2026-04-08T01:00:00', actor='proof', idempotency_key=uuid4().hex)
                event.refresh_from_db()
                self.assertTrue(event.state_sealed)
                actual, receipts = command_states(run, initial)
                self.assertEqual([r['id'] for r in receipts], [event.pk])
                if operation == 'APPLY':
                    self.assertEqual(actual['dbm']['NormAcceptanceTbl'], [dict(SKUCode='A',WhCode='L',
                        AcceptanceDate='2026-04-08',OldNorm=10,NewNorm=20)])
                elif operation == 'SLEEP':
                    self.assertEqual(actual['dbm']['Suggestions'], [])
                    self.assertEqual(actual['dbm']['NormsInSleepModeTbl'],
                                     [dict(SKUCode='A',WhCode='L',StartDate='2026-04-08')])
                else:
                    self.assertEqual(actual['orders']['ElephantOrders'][0]['DueDate'], '2026-04-20')

    def test_previous_writer_can_omit_seal_column_and_complete_manifest(self):
        run = self.run_owner(status='SUCCEEDED')
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("INSERT INTO mta.fresh_mta_runcommand(run_id,idempotency_key,payload,digest,"
                "before_digest,after_digest,state_manifest,created_at) VALUES(%s,%s,"
                "'{\"operation\":\"APPLY\"}',%s,%s,%s,'{}',CURRENT_TIMESTAMP) RETURNING id,state_sealed",
                [run.pk,uuid4().hex,'a'*64,'b'*64,'c'*64])
            command_id, sealed=cursor.fetchone()
            self.assertFalse(sealed)
            event=RunCommand.objects.get(pk=command_id)
            self.seal(event, self.manifest(run, event))

    def test_report_prefix_or_guc_alone_does_not_authorize_post_success_rows(self):
        run = self.run_owner(status='SUCCEEDED', production_manifest={'version': 3, 'reports': []})
        with transaction.atomic():
            self.sql("SELECT set_config('fresh.report_generation',%s,true)", [str(run.pk)])
            self.denied('INSERT INTO mta_state.btr_buffertrendphysicalinv(vf_run_id,vf_image,vf_ordinal) VALUES(%s,%s,0)',
                        [run.pk, 'closing/btr/BufferTrendPhysicalInv'], 'exact command or report generation')

    def test_original_consumer_guard_still_allows_manifest_only_sealing(self):
        import json
        from mta.mdm.owned_namespace import APPLICATION_WRITE_GUARD_BODY
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('fresh_control.application_capability')")
                self.assertIsNone(cursor.fetchone()[0])
                cursor.execute('CREATE SCHEMA IF NOT EXISTS fresh_control')
                cursor.execute('CREATE TABLE fresh_control.application_capability(singleton boolean,binding jsonb)')
                cursor.execute('SELECT current_user')
                role = cursor.fetchone()[0]
                cursor.execute('INSERT INTO fresh_control.application_capability VALUES(true,%s)',
                    [json.dumps({'original_registration': {'consumer_role': role}})])
                cursor.execute('CREATE FUNCTION mta.original_consumer_guard_proof() RETURNS trigger '
                    'LANGUAGE plpgsql AS $body$' + APPLICATION_WRITE_GUARD_BODY + '$body$')
                cursor.execute('CREATE TRIGGER application_write_boundary BEFORE UPDATE ON '
                    'mta.fresh_mta_runcommand FOR EACH ROW EXECUTE FUNCTION mta.original_consumer_guard_proof()')
                cursor.execute('CREATE TRIGGER application_write_boundary BEFORE INSERT ON '
                    'mta_state.dbm_normacceptancetbl FOR EACH ROW EXECUTE FUNCTION mta.original_consumer_guard_proof()')
            run = self.run_owner(status='SUCCEEDED')
            event = self.command(run)
            self.seal(event, self.manifest(run, event, nonempty=True))
            transaction.set_rollback(True)

    def test_inflight_typed_writer_serializes_with_run_finalization(self):
        from threading import Thread, Event
        from django.db import connections
        run = self.run_owner()
        inserted, release = Event(), Event()
        failures = []
        def writer():
            try:
                with transaction.atomic():
                    with connections['default'].cursor() as cursor:
                        cursor.execute('INSERT INTO mta_state.input_string_values VALUES(%s,%s,0,%s)',
                                       [run.pk, 'input/concurrent', 'owned'])
                    inserted.set()
                    if not release.wait(10):
                        raise AssertionError('writer release timed out')
            except BaseException as error:
                failures.append(error)
                inserted.set()
            finally:
                connections['default'].close()
        thread = Thread(target=writer)
        thread.start()
        try:
            self.assertTrue(inserted.wait(5))
            self.assertEqual(failures, [])
            with self.assertRaisesRegex(DatabaseError, 'lock timeout'), transaction.atomic():
                self.sql("SELECT set_config('lock_timeout','100ms',true)")
                self.sql("UPDATE mta.fresh_mta_calculationrun SET status='SUCCEEDED' WHERE id=%s", [run.pk])
        finally:
            release.set()
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        run.status='SUCCEEDED'; run.save(update_fields=['status'])
        self.denied('INSERT INTO mta_state.input_string_values VALUES(%s,%s,1,%s)',
                    [run.pk, 'input/concurrent', 'late'], 'Terminal insert')

    def test_exact_incomplete_generation_may_append_but_sealed_or_other_owner_may_not(self):
        from mta.runtime.report_generation_models import DailyReportGeneration
        run = self.run_owner(status='SUCCEEDED', production_manifest={'version': 3, 'reports': []},
                             production_digest='a'*64)
        other = self.run_owner(status='SUCCEEDED', production_manifest={'version': 3, 'reports': []},
                               production_digest='a'*64)
        generation = DailyReportGeneration.objects.create(run=run, source_digest='a'*64,
            recipe_digest='b'*64)
        insert = ('INSERT INTO mta_state.btr_buffertrendphysicalinv(vf_run_id,vf_image,vf_ordinal) '
                  'VALUES(%s,%s,%s)')
        image = 'closing/btr/BufferTrendPhysicalInv'
        with transaction.atomic():
            self.sql("SELECT set_config('fresh.report_generation',%s,true)", [str(run.pk)])
            self.sql(insert, [run.pk, image, 0])
            self.denied(insert, [other.pk, image, 0])
            from django.utils import timezone
            generation.status='READY'; generation.digest='c'*64; generation.sealed_at=timezone.now()
            generation.save(update_fields=['status','digest','sealed_at'])
            self.denied(insert, [run.pk, image, 1])

    def test_restricted_consumer_seals_without_new_column_update_or_function_grants(self):
        import json
        from psycopg import sql
        from mta.mdm.owned_namespace import APPLICATION_WRITE_GUARD_BODY
        role = 'g1proof_consumer_' + uuid4().hex[:12]
        run = self.run_owner(status='SUCCEEDED')
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('CREATE SCHEMA IF NOT EXISTS fresh_control')
            cursor.execute('CREATE TABLE fresh_control.application_capability(singleton boolean,binding jsonb)')
            cursor.execute('INSERT INTO fresh_control.application_capability VALUES(true,%s)',
                [json.dumps({'original_registration': {'consumer_role': role}})])
            cursor.execute('CREATE FUNCTION mta.restricted_consumer_guard_proof() RETURNS trigger '
                'LANGUAGE plpgsql AS $body$' + APPLICATION_WRITE_GUARD_BODY + '$body$')
            cursor.execute('REVOKE ALL ON FUNCTION mta.restricted_consumer_guard_proof() FROM PUBLIC')
            for table, events in (('mta.fresh_mta_runcommand','UPDATE'),
                                   ('mta_state.dbm_normacceptancetbl','INSERT')):
                cursor.execute('CREATE TRIGGER application_write_boundary BEFORE ' + events + ' ON ' +
                               table + ' FOR EACH ROW EXECUTE FUNCTION mta.restricted_consumer_guard_proof()')
            cursor.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOINHERIT').format(sql.Identifier(role)))
            for grant in ('USAGE ON SCHEMA mta,mta_state,fresh_control',
                          'SELECT ON ALL TABLES IN SCHEMA mta,mta_state',
                          'SELECT ON fresh_control.application_capability',
                          'INSERT ON mta.fresh_mta_runcommand,mta_state.dbm_normacceptancetbl',
                          'UPDATE(state_manifest) ON mta.fresh_mta_runcommand',
                          'UPDATE(id) ON mta.fresh_mta_calculationrun',
                          'USAGE ON SEQUENCE mta.fresh_mta_runcommand_id_seq'):
                cursor.execute(sql.SQL('GRANT ' + grant + ' TO {}').format(sql.Identifier(role)))
            cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
            event = self.command(run)
            self.seal(event, self.manifest(run, event, nonempty=True))
            cursor.execute('SET CONSTRAINTS accepted_command_complete IMMEDIATE')
            # All fixture DDL/role/grants are confined to this rollback.
            transaction.set_rollback(True)


@unittest.skipUnless(os.environ.get('VF_RUN_ACCEPTED_STATE_PROOF') == '1'
                     and os.environ.get('VF_DB_NAME', '').endswith('_upgrade'),
                     'Explicit uniquely owned migration-enabled PostgreSQL proof only')
class AcceptedStateUpgradeTests(unittest.TestCase):
    def test_upgrade_preserves_existing_legacy_commands_and_accepted_rows(self):
        from django.core.management import call_command
        from mta.runtime.accepted_state_ownership import verify_guards
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            self.assertEqual(cursor.fetchone()[0], 'VFTEST_Fresh_LifecycleG1_20261024_upgrade')
            cursor.execute("SELECT to_regclass('mta.fresh_mta_calculationrun')")
            self.assertIsNone(cursor.fetchone()[0], 'Upgrade proof requires its own fresh database')
        call_command('migrate', 'fresh_mta', '0168_report_guard_owner_sets', interactive=False, verbosity=0)
        run = CalculationRun.objects.create(input_digest=uuid4().hex*2, execution_revision='upgrade-proof',
            business_date=date(2026,4,8), kind='DAILY_CHAIN', input_payload={}, status='RUNNING')
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO mta_state.input_string_values VALUES(%s,%s,0,%s)',
                           [run.pk, 'input/retained', 'before-upgrade'])
        PickProjection.objects.create(run=run, calculation_digest='a'*64, rows_digest='b'*64,
                                      row_count=0, provenance={})
        run.status='SUCCEEDED'; run.save(update_fields=['status'])
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO mta.fresh_mta_runcommand(run_id,idempotency_key,payload,digest,"
                "before_digest,after_digest,state_manifest,created_at) VALUES(%s,'retained-legacy',"
                "'{\"operation\":\"APPLY\"}',%s,%s,%s,'{}',CURRENT_TIMESTAMP) RETURNING id",
                [run.pk,'a'*64,'b'*64,'c'*64])
            command_id=cursor.fetchone()[0]
            snapshots=[]
            for table, field in (('mta.fresh_mta_calculationrun','id'), ('mta.fresh_mta_runcommand','run_id'),
                                 ('mta.fresh_mta_pickprojection','run_id'), ('mta_state.input_string_values','vf_run_id')):
                cursor.execute('SELECT to_jsonb(T) FROM ' + table + ' T WHERE ' + field + '=%s',[run.pk])
                snapshots.append((table, field, cursor.fetchall()))
        call_command('migrate', interactive=False, verbosity=0)
        with connection.cursor() as cursor:
            self.assertTrue(verify_guards(cursor))
            for table, field, before in snapshots:
                projection = "to_jsonb(T)-'state_sealed'" if table.endswith('runcommand') else 'to_jsonb(T)'
                cursor.execute('SELECT ' + projection + ' FROM ' + table + ' T WHERE ' + field + '=%s',[run.pk])
                self.assertEqual(cursor.fetchall(), before, table)
        command=RunCommand.objects.get(pk=command_id)
        self.assertTrue(command.state_sealed)
        self.assertEqual(command.state_manifest, {})
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO mta_state.dbm_normacceptancetbl(vf_run_id,vf_image,vf_ordinal) '
                    'VALUES(%s,%s,0)', [run.pk, 'action/'+str(command_id)+'/NormAcceptanceTbl'])


if __name__ == '__main__':
    unittest.main()
