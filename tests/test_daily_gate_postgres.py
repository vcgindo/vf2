"""Explicit owned component proofs; these do not certify a native V3 run."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

if os.environ.get('VF_DAILY_GATE_COMPONENT_PROOF') == '1':
    import django
    django.setup()


@unittest.skipUnless(os.environ.get('VF_DAILY_GATE_COMPONENT_PROOF') == '1',
                     'Explicit owned daily-gate component database required')
class AdmittedCurrentTransportPostgresTests(unittest.TestCase):
    def test_admitted_staging_keeps_types_pk_duplicates_and_late_rollback(self):
        from django.db import connection
        from mta.application import accepted_inputs
        from mta.mdm import daily_current
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from tests.test_bulk_current_postgres import BulkCurrentPostgresTests
        self.assertEqual(connection.settings_dict['NAME'], 'vftest_fresh_dailygate_component_20261030')
        write = daily_current._write_partition
        staged = []

        def admitted(source, model, partition, expected, path):
            capture = MdmDailyInputCapture.objects.get(source=source)
            context = SimpleNamespace(native_daily=True, identity=str(capture.run_id), accepted_inputs=None)
            accepted_inputs._complete(context)
            with accepted_inputs.consume(context):
                staged.append(path)
                return write(source, model, partition, expected, path)

        proof = BulkCurrentPostgresTests('test_occurrences_types_guards_and_late_rollback')
        with patch.object(daily_current, '_write_partition', side_effect=admitted):
            proof.test_occurrences_types_guards_and_late_rollback()
        self.assertGreaterEqual(len(staged), 5)


@unittest.skipUnless(os.environ.get('VF_DAILY_GATE_COMPONENT_PROOF') == '1',
                     'Explicit owned daily-gate component database required')
class DeliveryMigrationPostgresTests(unittest.TestCase):
    def setUp(self):
        from django.db import connection
        self.assertEqual(connection.settings_dict['NAME'], 'vftest_fresh_dailygate_component_20261030')

    def test_guard_forward_reverse_preserves_owners_acls_oids_and_triggers(self):
        from importlib import import_module
        from django.db import connection, transaction
        migration = import_module('mta.runtime.migrations.0244_accepted_current_write_context')
        names = [name for name, *_ in migration.ORIGINALS]
        def identity():
            with connection.cursor() as cursor:
                cursor.execute('SELECT proname,oid::bigint,proowner::bigint,proacl::text,prosrc '
                    'FROM pg_proc WHERE pronamespace=\'mta\'::regnamespace AND proname=ANY(%s) ORDER BY proname', [names])
                functions = cursor.fetchall()
                cursor.execute('SELECT T.oid::bigint,T.tgrelid::bigint,T.tgfoid::bigint,T.tgenabled '
                    'FROM pg_trigger T JOIN pg_proc P ON P.oid=T.tgfoid '
                    'WHERE P.pronamespace=\'mta\'::regnamespace AND P.proname=ANY(%s) ORDER BY T.oid', [names])
                return functions, cursor.fetchall()
        before, triggers = identity()
        self.assertEqual(len(before), 4)
        with transaction.atomic():
            with connection.schema_editor(atomic=False) as editor:
                migration.reverse(None, editor)
                reversed_functions, reversed_triggers = identity()
                originals = {name: sql.split(delimiter)[1] for name, sql, delimiter, _ in migration.ORIGINALS}
                self.assertEqual([row[:4] for row in reversed_functions], [row[:4] for row in before])
                self.assertEqual(reversed_triggers, triggers)
                self.assertTrue(all(row[4] == originals[row[0]] for row in reversed_functions))
                migration.forward(None, editor)
                self.assertEqual(identity(), (before, triggers))
            transaction.set_rollback(True)
        self.assertEqual(identity(), (before, triggers))

    def test_sql_dispatch_is_owner_only_and_stale_or_forged_runtime_context_is_denied(self):
        from uuid import uuid4
        from django.db import connection, transaction, DatabaseError
        from mta.runtime.mdm_models import MdmSource
        from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent as Model
        from mta.mdm.daily_source import SCHEMA, APPROVAL_DAY_ARTIFACT_SHA
        from tests.test_bulk_current_postgres import fixture_rows
        with transaction.atomic():
            source = MdmSource.objects.create(digest=uuid4().hex * 2, dll_digest='c' * 64,
                database_name='owned-component-sql-dispatch-only',
                receipt=dict(schema=SCHEMA, artifact_sha256=APPROVAL_DAY_ARTIFACT_SHA))
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.mdm_current_bootstrap',%s,true)", [str(source.pk)])
            row = Model.objects.create(source=source, owner='Importer', ordinal=1, **fixture_rows(Model, 1)[0])
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.mdm_current_bootstrap','',true),txid_current()::text")
                xid = cursor.fetchone()[1]
            with self.assertRaises(DatabaseError), transaction.atomic():
                Model.objects.filter(pk=row.pk).update(Norm=2)
            run = str(uuid4())
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.mdm_current_run',%s,true),"
                    "set_config('fresh.accepted_current_run',%s,true),"
                    "set_config('fresh.accepted_current_xid',%s,true)", [run, run, xid])
            # The function owner is the existing trusted SQL authority. This
            # deliberately tests SQL dispatch, not Python/native admission.
            self.assertEqual(Model.objects.filter(pk=row.pk).update(Norm=2), 1)
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.accepted_current_xid','0',true)")
            with self.assertRaises(DatabaseError), transaction.atomic():
                Model.objects.filter(pk=row.pk).update(Norm=3)
            with connection.cursor() as cursor:
                # Grants are transaction-local test fixtures and roll back.
                # A trigger denial must remain even if ordinary table UPDATE
                # permission is supplied; permission denial alone is not proof.
                cursor.execute('GRANT USAGE ON SCHEMA mta TO vectorflow_mta_runtime')
                cursor.execute('GRANT SELECT ON ALL TABLES IN SCHEMA mta TO vectorflow_mta_runtime')
                cursor.execute('GRANT UPDATE ON mta.' + connection.ops.quote_name(Model._meta.db_table) +
                               ' TO vectorflow_mta_runtime')
                cursor.execute("SELECT set_config('fresh.accepted_current_xid',%s,true)", [xid])
                cursor.execute('SET LOCAL ROLE vectorflow_mta_runtime')
            with self.assertRaises(DatabaseError) as denied, transaction.atomic():
                Model.objects.filter(pk=row.pk).update(Norm=3)
            cause = denied.exception.__cause__
            # Restricted-role denial may arise from the preserved guard's
            # locked SELECT privilege or explicit RAISE. Require its trigger
            # stack, so a mere lack of UPDATE permission cannot pass this test.
            self.assertIn(getattr(cause, 'sqlstate', None), ('P0001', '42501'))
            trace = getattr(getattr(cause, 'diag', None), 'context', '') or ''
            from mta.runtime.accepted_current_write import GUARDS
            self.assertTrue(any(name in trace for name in GUARDS),
                            str(denied.exception) + '\n' + trace)
            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL ROLE vectorflow_mta_owner')
            row.refresh_from_db()
            self.assertEqual(row.Norm, 2)
            transaction.set_rollback(True)

    def test_compact_btr_dimensions_match_wide_distinct_bags_and_are_immutable(self):
        from datetime import date
        from uuid import uuid4
        from django.db import connection, transaction, DatabaseError
        from django.contrib.postgres.fields import ArrayField
        from mta.runtime.models import CalculationRun, BtrReportingGeneration, BtrPresentationRow, BtrScopeDimension
        from mta.presentation import btr_snapshot as snapshot
        from mta.presentation.btr_snapshot_fields import filter_field
        with transaction.atomic():
            run = CalculationRun.objects.create(kind='CURRENT_DAY', business_date=date(2026, 4, 8),
                input_digest=uuid4().hex * 2, execution_revision='component-btr-dimensions', input_payload={})
            generation = BtrReportingGeneration.objects.create(run=run, version=2, source_kind=run.kind,
                business_date=run.business_date, source_digest=uuid4().hex * 2, lineage={})
            defaults = {}
            for field in BtrPresentationRow._meta.concrete_fields:
                if field.name in ('id', 'generation'):
                    continue
                defaults[field.attname] = (field.get_default() if field.has_default() else None if field.null else
                    [0] * 91 if isinstance(field, ArrayField) else 0 if 'Integer' in field.get_internal_type() else 'S')
            dimensions = {'sa': set(), 'la': set()}
            for sa, la, null_level in ((1, 4, False), (2, 4, False), (1, 4, False), (3, 5, True)):
                values = dict(defaults, branch='tech', sa_ordinal=sa, la_ordinal=la)
                for owner, code, prefix in (('sa', 'SKUCode', 'SL'), ('la', 'WHCode', 'LL')):
                    values[filter_field(owner, code)] = 'same-code' if owner == 'sa' else 'location'
                    for level in (1, 2, 3):
                        values[filter_field(owner, prefix + str(level))] = None if null_level and level == 2 else str(level)
                BtrPresentationRow.objects.create(generation=generation, **values)
                snapshot._collect_dimensions(dimensions, values)
            snapshot._save_dimensions(generation, dimensions)
            actual = snapshot._attributes(generation)
            for owner, table, code, prefix, ordinal in snapshot.SCOPE_SOURCES:
                fields = (code, *(prefix + str(i) for i in (1, 2, 3)))
                with connection.cursor() as cursor:
                    cursor.execute('SELECT DISTINCT ' + ordinal + ',' + ','.join(
                        connection.ops.quote_name(filter_field(owner, field)) for field in fields) +
                        ' FROM ' + snapshot.TABLE + ' WHERE generation_id=%s AND ' + ordinal +
                        ' IS NOT NULL ORDER BY ' + ordinal, [generation.pk])
                    expected = [dict(zip(fields, row[1:])) for row in cursor.fetchall()]
                self.assertEqual(actual[table], expected)
            self.assertEqual(BtrScopeDimension.objects.filter(generation=generation, owner='sa').count(), 3)
            generation.status = 'READY'
            generation.save()
            for operation in ('UPDATE', 'DELETE', 'INSERT', 'TRUNCATE'):
                with self.subTest(operation=operation), self.assertRaises(DatabaseError), transaction.atomic():
                    if operation == 'UPDATE':
                        BtrScopeDimension.objects.filter(generation=generation).update(code='changed')
                    elif operation == 'DELETE':
                        BtrScopeDimension.objects.filter(generation=generation).delete()
                    elif operation == 'INSERT':
                        BtrScopeDimension.objects.create(generation=generation, owner='sa', source_ordinal=99, code='extra')
                    else:
                        with connection.cursor() as cursor:
                            cursor.execute('TRUNCATE mta.fresh_mta_btrscopedimension')
            self.assertEqual(snapshot._attributes(generation), actual)
            transaction.set_rollback(True)
