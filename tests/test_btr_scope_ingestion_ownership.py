"""0246 contracts and opt-in rollback-only PostgreSQL component proofs."""
from importlib import import_module
import os
import unittest
from unittest.mock import Mock, patch

from mta.runtime import ingestion_ownership as ownership

migration = import_module('mta.runtime.migrations.0246_btr_scope_dimension_ingestion_ownership')


class BtrScopeOwnershipContractTests(unittest.TestCase):
    def test_exact_existing_child_owner_case_is_the_only_body_addition(self):
        self.assertEqual(migration.NEW.replace('\n' + migration.SCOPE_CASE, '', 1), migration.OLD)
        self.assertEqual(migration.SCOPE_CASE.replace('fresh_mta_btrscopedimension',
            'fresh_mta_btrpresentationrow'), migration.PRESENTATION_CASE)
        self.assertIn('LEFT JOIN mta.fresh_mta_btrreportinggeneration P ON P.id=N.generation_id', migration.SCOPE_CASE)
        self.assertIn('R.kind<>', migration.SCOPE_CASE)
        self.assertIn('R.status<>', migration.SCOPE_CASE)
        self.assertIn('R.id IS NULL', migration.SCOPE_CASE)
        self.assertIn("IS DISTINCT FROM ''3''", migration.SCOPE_CASE)
        self.assertIn('P.prosrc=$scope_pick_prior$' + migration.OLD, migration.SQL)
        self.assertIn('P.prosrc=$scope_pick_prior$' + migration.NEW, migration.REVERSE)
        self.assertNotIn('DROP FUNCTION', migration.SQL + migration.REVERSE)
        self.assertNotIn('ALTER FUNCTION', migration.SQL + migration.REVERSE)
        self.assertNotIn('btr_scope_dimension_immutable', migration.SQL + migration.REVERSE)

    def test_exact_four_watches_satisfy_actual_coverage_consumer(self):
        from tests import test_report_definition_guards as contract
        with patch.object(contract, 'guards', migration):
            rows = contract.watch_catalogue()
            self.assertEqual(len(rows), 4)
            contract.validate_catalogue(rows)
            for index in range(4):
                with self.assertRaisesRegex(ValueError, 'Missing or incorrectly classified'):
                    contract.validate_catalogue(rows[:index] + rows[index + 1:])
            wrong = list(rows); row = list(wrong[0]); row[6] = 'action\\000'; wrong[0] = tuple(row)
            with self.assertRaisesRegex(ValueError, 'Missing or incorrectly classified'):
                contract.validate_catalogue(wrong)

    def test_exact_revision_body_metadata_only_and_latest_applied_version(self):
        candidate = dict(name='mta.ingestion_watch()', security_definer=True,
            configuration=['search_path=pg_catalog, mta'], returns='trigger', body=migration.NEW)
        self.assertTrue(ownership.is_revision_guard(candidate))
        self.assertTrue(ownership.is_revision_guard(dict(candidate, body=migration.OLD)))
        for key, value in (('body', migration.NEW + '\n'), ('name', 'mta.unknown()'),
                ('security_definer', False), ('configuration', ['search_path=public, mta']),
                ('returns', 'text')):
            self.assertFalse(ownership.is_revision_guard(dict(candidate, **{key:value})))
        cursor = Mock()
        minimum = '0237_intake_diagnostic_guards'
        cursor.fetchall.return_value = [(minimum,)]
        self.assertEqual(ownership.scoped_derived_body(cursor, minimum=minimum), migration.OLD)
        cursor.fetchall.return_value.append(('0246_btr_scope_dimension_ingestion_ownership',))
        self.assertEqual(ownership.scoped_derived_body(cursor, minimum=minimum), migration.NEW)
        cursor.fetchall.return_value = [('0246_btr_scope_dimension_ingestion_ownership',)]
        with self.assertRaisesRegex(ValueError, 'Required scoped derived'):
            ownership.scoped_derived_body(cursor, minimum=minimum)


@unittest.skipUnless(os.environ.get('VF_DAILY_GATE_COMPONENT_PROOF') == '1',
                     'Explicit owned daily-gate component database required')
class BtrScopeOwnershipPostgresTests(unittest.TestCase):
    def setUp(self):
        import django
        django.setup()
        from django.db import connection
        self.assertEqual(connection.settings_dict['NAME'], 'vftest_fresh_dailygate_component_20261030')
        with connection.cursor() as cursor:
            cursor.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(cursor.fetchone()[0],
                'owned daily-single-ingestion component proof 20261030; synthetic only')

    def test_complete_actual_coverage_and_exact_reversible_function_identity(self):
        from django.db import connection, transaction, DatabaseError
        def identity(cursor):
            cursor.execute("SELECT oid::bigint,proowner::bigint,proacl::text,prosecdef,proconfig,prosrc "
                "FROM pg_proc WHERE oid='mta.ingestion_watch()'::regprocedure")
            function = cursor.fetchone()
            cursor.execute("SELECT oid::bigint,tgname,tgfoid::bigint,tgenabled FROM pg_trigger "
                "WHERE tgrelid='mta.fresh_mta_btrscopedimension'::regclass AND NOT tgisinternal ORDER BY tgname")
            return function, cursor.fetchall()
        with transaction.atomic(), connection.cursor() as cursor:
            before, triggers = identity(cursor)
            self.assertEqual(before[-1], migration.NEW)
            # The complete real schema roster, not a one-table mocked subset.
            ownership._verify_guard_coverage(cursor)
            business = [row for row in triggers if not row[1].startswith('ingestion_watch_')]
            self.assertEqual({row[1] for row in business},
                {'btr_scope_dimension_immutable', 'btr_scope_dimension_no_truncate'})
            cursor.execute(migration.REVERSE)
            reversed_function, reversed_triggers = identity(cursor)
            self.assertEqual(reversed_function[:-1], before[:-1])
            self.assertEqual(reversed_function[-1], migration.OLD)
            self.assertEqual(reversed_triggers, business)
            with self.assertRaisesRegex(ValueError, 'fresh_mta_btrscopedimension'):
                ownership._verify_guard_coverage(cursor)
            cursor.execute(migration.SQL)
            function, restored_triggers = identity(cursor)
            self.assertEqual(function, before)
            self.assertEqual([row for row in restored_triggers if not row[1].startswith('ingestion_watch_')], business)
            ownership._verify_guard_coverage(cursor)
            # A stale predecessor is rejected before an additional trigger can
            # be installed. Keep this failed command in its own savepoint.
            with self.assertRaises(DatabaseError), transaction.atomic():
                cursor.execute(migration.SQL)
            transaction.set_rollback(True)

    def test_derived_dml_keeps_epochs_and_unknown_or_completed_generation_is_denied(self):
        from datetime import date
        from uuid import uuid4
        from django.db import connection, transaction, DatabaseError
        from mta.runtime.models import CalculationRun, BtrReportingGeneration, BtrScopeDimension
        from mta.runtime.mdm_models import MdmSource
        from mta.runtime.initialization_models import ProductionInitialization
        from mta.runtime.ingestion_models import InitializationCertification, IngestionRevisionState
        # Explicit metadata carriers exercise real certified counters, not a
        # native initialization or a business-day acceptance claim. No trigger
        # is disabled; every fixture and write rolls back at method exit.
        with transaction.atomic(), connection.cursor() as cursor:
            ownership._verify_guard_coverage(cursor)
            source = MdmSource.objects.create(digest=uuid4().hex * 2, dll_digest='c' * 64,
                database_name='METADATA_ONLY_BTR_SCOPE_COUNTERS', receipt={})
            initial_id = uuid4()
            cursor.execute("SELECT set_config('fresh.production_initialization',%s,true)", [str(initial_id)])
            initial = ProductionInitialization.objects.create(id=initial_id, source=source,
                opening_identity='METADATA_ONLY_' + initial_id.hex, opening_date=date(2026, 4, 7),
                input_sha256=uuid4().hex * 2, recipe_sha256='b' * 64, configuration_digest='c' * 64,
                implementation_digest='d' * 64, input_digest='e' * 64)
            cursor.execute("SELECT set_config('fresh.production_initialization','',true)")
            state = IngestionRevisionState.objects.create(initialization=initial)
            cursor.execute('SELECT oid FROM pg_database WHERE datname=current_database()')
            InitializationCertification.objects.create(initialization=initial, contract='METADATA_ONLY_BTR_SCOPE_COUNTERS',
                database_name=connection.settings_dict['NAME'], database_oid=cursor.fetchone()[0], namespace=uuid4(),
                source_digest=source.digest, content_digest='e' * 64, configuration_digest='c' * 64,
                schema_digest='1' * 64, guard_digest='2' * 64, release_digest='3' * 64,
                receipt_digest='4' * 64, populations={'fixture':'NO_NATIVE_OR_BUSINESS_CERTIFICATION'})
            def epochs():
                state.refresh_from_db()
                return (state.master_epoch, state.configuration_epoch, state.fact_epoch,
                        state.operational_epoch, state.action_epoch)
            def generation(kind, status='SUCCEEDED', manifest=None):
                run = CalculationRun.objects.create(kind=kind, status=status, business_date=date(2026, 4, 8),
                    input_digest=uuid4().hex * 2, execution_revision='metadata-only-btr-scope-' + uuid4().hex,
                    input_payload={}, production_manifest={'version':3} if manifest is None else manifest)
                return BtrReportingGeneration.objects.create(run=run, version=2, source_kind=kind,
                    business_date=run.business_date, source_digest=uuid4().hex * 2, lineage={})
            qualified = generation('DAILY_CHAIN')
            before = epochs()
            rows = BtrScopeDimension.objects.bulk_create([
                BtrScopeDimension(generation=qualified, owner='sa', source_ordinal=i, code='duplicate', level_2=None)
                for i in (1, 2)])
            BtrScopeDimension.objects.filter(pk=rows[0].pk).update(level_1='changed')
            BtrScopeDimension.objects.filter(pk=rows[1].pk).delete()
            self.assertEqual(epochs(), before)
            self.assertEqual(list(BtrScopeDimension.objects.filter(generation=qualified)
                .values_list('source_ordinal','code','level_1','level_2')), [(1,'duplicate','changed',None)])
            qualified.status = 'READY'; qualified.save(update_fields=['status'])
            for generation_id in (uuid4(), qualified.pk):
                with self.assertRaises(DatabaseError), transaction.atomic():
                    BtrScopeDimension.objects.create(generation_id=generation_id, owner='sa', source_ordinal=99)
            self.assertEqual(epochs(), before)
            # Nonqualified real rows must still invalidate operational input;
            # the table is never excluded wholesale.
            nonqualified = generation('CURRENT_DAY')
            baseline = epochs()
            BtrScopeDimension.objects.create(generation=nonqualified, owner='la', source_ordinal=1)
            self.assertEqual(epochs(), baseline[:3] + (baseline[3] + 1, baseline[4]))
            transaction.set_rollback(True)


if __name__ == '__main__':
    unittest.main()
