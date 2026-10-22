"""Current-owner identity must survive a legitimate successor, never a branch."""
import os
import unittest
from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.mdm import daily_current
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.application.daily_finalization import ACTIVE_POLICY
from mta.mdm.daily_source import SCHEMA
from django.db import connection, transaction, DatabaseError


class _ProjectionField:
    def __init__(self, name):
        self.name = name


class _ProjectionQuery:
    def __init__(self, manager, filters=None, ordering=()):
        self.manager = manager
        self.filters = filters or {}
        self.ordering = ordering

    def _rows(self):
        def matches(row):
            for name, value in self.filters.items():
                if name.endswith('__in'):
                    if getattr(row, name[:-4]) not in value:
                        return False
                elif getattr(row, name) != value:
                    return False
            return True
        rows = [row for row in self.manager.rows if matches(row)]
        for name in reversed(self.ordering):
            rows.sort(key=lambda row: getattr(row, name))
        return rows

    def order_by(self, *names):
        return _ProjectionQuery(self.manager, self.filters, names)

    def only(self, *_names):
        return self

    def iterator(self, *, chunk_size):
        self.manager.iterator_sizes.append(chunk_size)
        return iter(self._rows())

    def filter(self, **filters):
        return _ProjectionQuery(self.manager, {**self.filters, **filters}, self.ordering)

    def count(self):
        return len(self._rows())

    def exists(self):
        return bool(self._rows())

    def values(self, *names):
        return [{name: getattr(row, name) for name in names} for row in self._rows()]

    def delete(self):
        selected = self._rows()
        self.manager.delete_batches.append([row.pk for row in selected])
        selected = {row.pk for row in selected}
        self.manager.rows[:] = [row for row in self.manager.rows if row.pk not in selected]


class _ProjectionManager:
    def __init__(self):
        self.rows = []
        self.next_pk = 1
        self.bulk_updates = []
        self.bulk_creates = []
        self.delete_batches = []
        self.iterator_sizes = []

    def filter(self, **filters):
        return _ProjectionQuery(self, filters)

    def bulk_update(self, rows, fields, *, batch_size):
        self.bulk_updates.append(([row.pk for row in rows], tuple(fields), batch_size))

    def bulk_create(self, rows, *, batch_size):
        for row in rows:
            row.pk = self.next_pk
            self.next_pk += 1
            self.rows.append(row)
        self.bulk_creates.append(([row.ordinal for row in rows], batch_size))


class _ProjectionModel:
    _meta = SimpleNamespace(fields=[_ProjectionField(name) for name in
        ('id', 'source', 'owner', 'ordinal', 'Value', 'Note')])
    objects = _ProjectionManager()

    def __init__(self, **values):
        self.pk = values.pop('pk', None)
        for name, value in values.items():
            setattr(self, name, value)


class CurrentProjectionWriterTests(unittest.TestCase):
    def setUp(self):
        _ProjectionModel.objects = _ProjectionManager()
        self.source = object()
        # This in-memory model verifies orchestration; it has no SQL metadata.
        # Actual PostgreSQL transport is exercised by the owned database proof.
        vendor = patch.object(daily_current.connection, 'vendor', 'in-memory-fixture')
        vendor.start()
        self.addCleanup(vendor.stop)

    def test_scalar_comparison_matches_canonical_storage(self):
        from datetime import datetime, timezone
        from mta.serialization import storage
        values = (None, True, False, 0, -1, 1.25, '', 'NULL',
                  Decimal('1.230'), date(2026, 4, 8),
                  datetime(2026, 4, 8, tzinfo=timezone.utc))
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(daily_current._scalar_storage(value), storage(value))

    def seed(self, rows):
        for ordinal, values in rows:
            row = _ProjectionModel(pk=_ProjectionModel.objects.next_pk,
                source=self.source, owner='Importer', ordinal=ordinal, **values)
            _ProjectionModel.objects.next_pk += 1
            _ProjectionModel.objects.rows.append(row)
        return [row.pk for row in _ProjectionModel.objects.rows]

    def values(self):
        return [(row.pk, row.ordinal, row.Value, row.Note)
                for row in sorted(_ProjectionModel.objects.rows, key=lambda row: row.ordinal)]

    def write(self, rows):
        return daily_current._write_partition(self.source, _ProjectionModel,
            {'owner': 'Importer'}, rows, '/test/current')

    def test_equal_duplicate_occurrences_keep_primary_keys_without_dml(self):
        pks = self.seed([(1, {'Value': 'same', 'Note': None}),
                         (2, {'Value': 'same', 'Note': None})])
        result = self.write([{'Value': 'same', 'Note': None},
                             {'Value': 'same', 'Note': None}])
        self.assertEqual(result, {'updated': 0, 'inserted': 0, 'deleted': 0})
        self.assertEqual([row[0] for row in self.values()], pks)
        self.assertEqual(_ProjectionModel.objects.bulk_updates, [])
        self.assertEqual(_ProjectionModel.objects.bulk_creates, [])
        self.assertEqual(_ProjectionModel.objects.delete_batches, [])
        self.assertEqual(_ProjectionModel.objects.iterator_sizes, [500])

    def test_only_changed_fields_update_and_new_tail_appends(self):
        pks = self.seed([(1, {'Value': 'same', 'Note': None}),
                         (2, {'Value': 'old', 'Note': 'kept'})])
        result = self.write([{'Value': 'same', 'Note': None},
                             {'Value': 'new', 'Note': 'kept'},
                             {'Value': 'new', 'Note': None}])
        self.assertEqual(result, {'updated': 1, 'inserted': 1, 'deleted': 0})
        self.assertEqual(_ProjectionModel.objects.bulk_updates, [([pks[1]], ('Value',), 500)])
        self.assertEqual(_ProjectionModel.objects.bulk_creates, [([3], 500)])
        self.assertEqual(self.values(), [(pks[0], 1, 'same', None),
            (pks[1], 2, 'new', 'kept'), (pks[1] + 1, 3, 'new', None)])

    def test_shrink_deletes_only_excess_tail_in_bounded_batches(self):
        self.seed([(ordinal, {'Value': str(ordinal), 'Note': None})
                   for ordinal in range(1, 1003)])
        result = self.write([])
        self.assertEqual(result, {'updated': 0, 'inserted': 0, 'deleted': 1002})
        self.assertEqual([len(batch) for batch in _ProjectionModel.objects.delete_batches],
                         [500, 500, 2])
        self.assertEqual(self.values(), [])

    def test_growth_inserts_and_verifies_in_bounded_batches(self):
        expected = [{'Value': str(ordinal), 'Note': None}
                    for ordinal in range(1, 1003)]
        result = self.write(expected)
        self.assertEqual(result, {'updated': 0, 'inserted': 1002, 'deleted': 0})
        self.assertEqual([len(ordinals) for ordinals, _size
                          in _ProjectionModel.objects.bulk_creates], [500, 500, 2])
        self.assertEqual(len(self.values()), 1002)

    def test_full_changed_projection_updates_in_bounded_batches(self):
        pks = self.seed([(ordinal, {'Value': 'old', 'Note': None})
                         for ordinal in range(1, 1003)])
        expected = [{'Value': 'new', 'Note': None} for _ordinal in range(1, 1003)]
        result = self.write(expected)
        self.assertEqual(result, {'updated': 1002, 'inserted': 0, 'deleted': 0})
        self.assertEqual([len(updated_pks) for updated_pks, _fields, _size
                          in _ProjectionModel.objects.bulk_updates], [500, 500, 2])
        self.assertEqual([row[0] for row in self.values()], pks)

    def test_ordinal_gap_rejects_before_any_write(self):
        before = self.seed([(1, {'Value': 'one', 'Note': None}),
                            (3, {'Value': 'three', 'Note': None})])
        with self.assertRaisesRegex(ValueError, 'ordinal gap'):
            self.write([{'Value': 'changed', 'Note': None}])
        self.assertEqual([row[0] for row in self.values()], before)
        self.assertEqual(_ProjectionModel.objects.bulk_updates, [])
        self.assertEqual(_ProjectionModel.objects.bulk_creates, [])
        self.assertEqual(_ProjectionModel.objects.delete_batches, [])

    def test_late_ordinal_gap_relies_on_caller_transaction_to_rollback_flushed_batch(self):
        self.seed([(ordinal, {'Value': 'old', 'Note': None})
                   for ordinal in range(1, 501)] +
                  [(502, {'Value': 'old', 'Note': None})])
        expected = [{'Value': 'new', 'Note': None} for _ordinal in range(1, 503)]
        with self.assertRaisesRegex(ValueError, 'ordinal gap'):
            self.write(expected)
        self.assertEqual([len(pks) for pks, _fields, _size
                          in _ProjectionModel.objects.bulk_updates], [500])


class CurrentOwnerTests(unittest.TestCase):
    def carrier(self, pk, parent=None, active=True):
        return SimpleNamespace(run_id=pk, nms_active=active,
            run=SimpleNamespace(pk=pk, kind='DAILY_CHAIN', predecessor_id=parent,production_manifest={}))

    def verify(self, carriers, selected):
        source = SimpleNamespace(receipt={'schema': SCHEMA})
        query = Mock()
        query.select_related.return_value = carriers
        with patch.object(MdmDailyInputCapture.objects, 'filter', return_value=query), \
                patch('mta.runtime.input_reader.read_input',
                    return_value={'profile': {'complete_daily': {'policy': ACTIVE_POLICY}}}), \
                patch('mta.runtime.services.read_outputs',
                    side_effect=lambda run: {'ClosingState': [{'own_run': run.pk}]}), \
                patch.object(daily_current, 'verify_current') as live, \
                patch.object(daily_current, 'identity', side_effect=lambda closing, **_kwargs: closing):
            result = daily_current.verify_published(selected.run, source)
        return result, live.call_args

    def test_historical_identity_is_stable_while_live_check_advances(self):
        first = self.carrier('first')
        old, live0 = self.verify([first], first)
        second = self.carrier('second', 'first')
        after, live1 = self.verify([first, second], first)
        self.assertEqual(old, after)
        self.assertEqual(after, {'own_run': 'first'})
        self.assertEqual(live0.args[1], {'own_run': 'first'})
        self.assertEqual(live1.args[1], {'own_run': 'second'})

    def test_branch_and_disconnected_roots_are_rejected(self):
        first = self.carrier('first')
        for carriers in ([first, self.carrier('a', 'first'), self.carrier('b', 'first')],
                         [first, self.carrier('unrelated')],
                         [first, self.carrier('missing-child', 'missing')]):
            with self.subTest(carriers=carriers), self.assertRaisesRegex(ValueError, 'branched|disconnected'):
                self.verify(carriers, first)

    def test_inactive_or_unconsumed_selected_run_cannot_be_blessed(self):
        first = self.carrier('first')
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.verify([self.carrier('first', active=False)], first)
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.verify([first], self.carrier('not-published'))

    def test_current_tampering_also_rejects_historical_run(self):
        first = self.carrier('first'); second = self.carrier('second', 'first')
        query = Mock(); query.select_related.return_value = [first, second]
        with patch.object(MdmDailyInputCapture.objects, 'filter', return_value=query), \
                patch('mta.runtime.input_reader.read_input',
                    return_value={'profile': {'complete_daily': {'policy': ACTIVE_POLICY}}}), \
                patch('mta.runtime.services.read_outputs', return_value={'ClosingState': [{}]}), \
                patch.object(daily_current, 'verify_current', side_effect=ValueError('typed readback differs')):
            with self.assertRaisesRegex(ValueError, 'typed readback'):
                daily_current.verify_published(first.run, SimpleNamespace(receipt={'schema': SCHEMA}))


@unittest.skipUnless(os.environ.get('VF_MDM_CURRENT_PG_PROOF') == '1',
                     'owned PostgreSQL migration0109 proof only')
class CurrentOwnerPostgresTests(unittest.TestCase):
    """Rollback-only component carriers; these are never business-day receipts."""
    def setUp(self):
        from tests.mdm_proof_resources import assert_owned_mdm_proof
        assert_owned_mdm_proof(self, connection)
        self.tx = transaction.atomic(); self.tx.__enter__()
        self.addCleanup(self.rollback)
        from django.db.migrations.recorder import MigrationRecorder
        self.assertTrue(MigrationRecorder.Migration.objects.filter(
            app='fresh_mta', name='0109_active_mdm_current_guards').exists())
        from mta.mdm.daily_source import APPROVAL_DAY_ARTIFACT_SHA, SCHEMA
        from mta.runtime import mdm_models as sku, mdm_skuloc_models as pair
        from mta.mdm.daily_source_install import business_fields
        self.source = sku.MdmSource.objects.create(digest='e'*64, dll_digest='e'*64,
            database_name='rollback-only-current-proof',
            receipt={'schema': SCHEMA, 'artifact_sha256': APPROVAL_DAY_ARTIFACT_SHA})
        def row(model):
            result = {}
            for field in business_fields(model):
                name, kind = field.name, field.get_internal_type()
                if field.null:
                    value = None
                elif kind in ('IntegerField', 'PositiveIntegerField', 'BigIntegerField'):
                    value = 1
                elif kind == 'DecimalField':
                    value = Decimal('1')
                elif kind == 'DateField':
                    value = date(2026, 6, 5)
                elif kind == 'BooleanField':
                    value = False
                else:
                    value = 'S' if 'SKUCode' in name else 'L'
                result[name] = value
            return result
        importer = {
            'SkuAttributeData': [row(sku.MdmSkuAttributes)] * 2,
            'SKUDescriptionTbl': [row(sku.MdmSkuDescription)] * 2,
            'LocationAttributeData': [row(sku.MdmLocationAttributes)] * 2,
            'SiteDescriptionTbl': [row(sku.MdmLocationDescription)] * 2,
            'SkuLocAttributeData': [row(pair.MdmSkuLocPair)] * 2,
            'MasterData': [row(pair.MdmSkuLocMasterPair)] * 2,
        }
        self.closing = dict(importer=deepcopy(importer), btr=deepcopy(importer),
            dbm=deepcopy(importer), consumer_context={
                'NMSAllItems': [row(pair.MdmSkuLocCurrent)] * 2})
        self.guc('fresh.mdm_current_bootstrap', str(self.source.pk))
        for _, model, partition, rows, _ in daily_current.closing_owners(self.closing):
            model.objects.bulk_create([model(source=self.source, ordinal=i, **partition, **values)
                for i, values in enumerate(rows, 1)])
        self.guc('fresh.mdm_current_bootstrap', '')
        from mta.runtime.models import CalculationRun
        self.run = CalculationRun.objects.create(kind='DAILY_CHAIN', business_date='2026-06-06',
            input_digest='rollback-only-current', execution_revision='no-calculation-current-proof',
            input_payload={}, status='RUNNING')
        self.capture = MdmDailyInputCapture.objects.create(run=self.run, source=self.source,
            request_digest='e'*64, revision_digest='e'*64, sku_revision_digest='e'*64,
            location_revision_digest='e'*64, skuloc_revision_digest='e'*64,
            sql_digest='e'*64, nms_active=True)

    def rollback(self):
        transaction.set_rollback(True); self.tx.__exit__(None, None, None)

    def guc(self, key, value):
        with connection.cursor() as cursor:
            cursor.execute('SELECT set_config(%s,%s,true)', [key, value])

    def consume(self):
        from django.utils import timezone
        self.guc('fresh.mdm_consuming_run', str(self.run.pk))
        self.capture.status = 'CONSUMED'; self.capture.consumed_at = timezone.now()
        self.capture.save(update_fields=['status', 'consumed_at'])

    def deny(self, call):
        with self.assertRaises(DatabaseError), transaction.atomic():
            call()

    def test_all_tables_are_guarded_and_wrong_state_update_truncate_denied(self):
        from mta.runtime.mdm_models import MdmSkuUse
        from django.db.migrations.recorder import MigrationRecorder
        tables = {model._meta.db_table for _, model, _, _, _ in daily_current.closing_owners(self.closing)}
        with connection.cursor() as cursor:
            cursor.execute("SELECT C.relname,T.tgname FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid "
                "JOIN pg_namespace N ON N.oid=C.relnamespace WHERE N.nspname='mta' "
                "AND T.tgname IN ('active_mdm_current','active_mdm_current_truncate')")
            guarded = cursor.fetchall()
        self.assertEqual({name for name, _ in guarded}, tables)
        self.assertEqual(len(guarded), 18)
        insert = lambda: MdmSkuUse.objects.create(source=self.source, ordinal=3, SKUCode='LATE')
        self.deny(insert)
        self.guc('fresh.mdm_current_bootstrap', str(self.source.pk)); self.deny(insert)
        self.guc('fresh.mdm_current_bootstrap', '')
        self.guc('fresh.mdm_current_run', str(self.run.pk)); self.deny(insert)
        self.consume()
        if MigrationRecorder.Migration.objects.filter(app='fresh_mta',name='0153_incremental_current_guards').exists():
            self.deny(lambda: MdmSkuUse.objects.filter(source=self.source).update(ordinal=99))
            self.guc('fresh.mdm_current_run','foreign')
            self.deny(lambda: MdmSkuUse.objects.filter(source=self.source).update(SKUCode='CHANGED'))
            self.guc('fresh.mdm_current_run',str(self.run.pk))
        else:
            self.deny(lambda: MdmSkuUse.objects.filter(source=self.source).update(SKUCode='CHANGED'))
        with connection.cursor() as cursor:
            self.deny(lambda: cursor.execute('TRUNCATE mta.fresh_mta_mdmskuuse'))
        insert()  # Exact consumed/run capability permits occurrence insertion.
        self.guc('fresh.mdm_current_run', 'foreign'); self.deny(insert)

    def test_publication_preserves_all_partitions_nulls_and_duplicates(self):
        from mta.application.daily_finalization import ACTIVE_POLICY
        self.consume()
        changed = deepcopy(self.closing)
        changed['importer']['SkuAttributeData'][0]['Weight'] = Decimal('2.125')
        changed['importer']['LocationAttributeData'][0]['c4'] = 'updated'
        changed['importer']['SkuLocAttributeData'][0]['PackSize'] = 2
        with patch('mta.runtime.input_reader.read_input',
                   return_value={'profile': {'complete_daily': {'policy': ACTIVE_POLICY}}}):
            daily_current.publish(self.run, self.capture, changed)
        daily_current.verify_current(self.source, changed)
        self.source.refresh_from_db()
        self.assertEqual(self.source.digest, 'e'*64)
        self.assertEqual(len(daily_current.identity(changed)), 16)

    def test_later_failure_rolls_consumption_and_all_owner_replacements_back(self):
        from mta.application.daily_finalization import ACTIVE_POLICY
        changed = deepcopy(self.closing)
        changed['importer']['SkuAttributeData'][0]['Weight'] = Decimal('2.125')
        with self.assertRaisesRegex(ValueError, 'later output failure'), transaction.atomic():
            self.consume()
            with patch('mta.runtime.input_reader.read_input',
                       return_value={'profile': {'complete_daily': {'policy': ACTIVE_POLICY}}}):
                daily_current.publish(self.run, self.capture, changed)
            raise ValueError('later output failure')
        self.capture.refresh_from_db()
        self.assertEqual(self.capture.status, 'CAPTURED')
        self.assertIsNone(self.capture.consumed_at)
        daily_current.verify_current(self.source, self.closing)

    def test_legacy_owner_behavior_and_active_policy_denial_remain_separate(self):
        from mta.runtime.mdm_models import MdmSource, MdmSkuUse
        from mta.application.daily_finalization import POLICY
        legacy = MdmSource.objects.create(digest='f'*64, dll_digest='f'*64,
            database_name='rollback-only-legacy', receipt={})
        row = MdmSkuUse.objects.create(source=legacy, ordinal=1, SKUCode=None)
        MdmSkuUse.objects.filter(pk=row.pk).update(SKUCode='EXISTING-BEHAVIOR')
        row.refresh_from_db(); self.assertEqual(row.SKUCode, 'EXISTING-BEHAVIOR')
        row.delete()
        self.consume()
        with patch('mta.runtime.input_reader.read_input',
                   return_value={'profile': {'complete_daily': {'policy': POLICY}}}):
            with self.assertRaisesRegex(ValueError, 'active consumed day'):
                daily_current.publish(self.run, self.capture, self.closing)
        daily_current.verify_current(self.source, self.closing)
