"""Generation-owned compact BTR scopes preserve occurrence multiplicity."""
from contextlib import ExitStack, nullcontext
from importlib import import_module
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.presentation import btr_snapshot as snapshot, context
from mta.presentation.btr_snapshot_fields import filter_field
from mta.runtime.models import BtrReportingGeneration, BtrScopeDimension
from mta.serialization import digest


def source(ordinal=1, *, location=7, null_level=False):
    value = dict(sa_ordinal=ordinal, la_ordinal=location)
    for owner, code, prefix in (('sa', 'SKUCode', 'SL'), ('la', 'WHCode', 'LL')):
        value[filter_field(owner, code)] = 'same-code' if owner == 'sa' else 'location'
        for level in (1, 2, 3):
            value[filter_field(owner, prefix+str(level))] = None if null_level and owner=='sa' and level==2 else str(level)
    return value


class BtrScopeDimensionTests(unittest.TestCase):
    def test_duplicate_codes_keep_source_occurrences_and_nulls_are_not_filled(self):
        dimensions = {'sa': set(), 'la': set()}
        for row in (source(1), source(1), source(2), source(3, null_level=True)):
            snapshot._collect_dimensions(dimensions, row)
        missing = source(None, location=None)
        snapshot._collect_dimensions(dimensions, missing)
        self.assertEqual(len(dimensions['sa']), 3)
        self.assertIn((3, 'same-code', '1', None, '3'), dimensions['sa'])
        generation = BtrReportingGeneration(pk=uuid4())
        with patch.object(BtrScopeDimension.objects, 'bulk_create') as create:
            snapshot._save_dimensions(generation, dimensions)
        rows = create.call_args.args[0]
        self.assertEqual([row.source_ordinal for row in rows if row.owner=='sa'], [1, 2, 3])
        self.assertEqual([row.code for row in rows if row.owner=='sa'], ['same-code']*3)
        self.assertTrue(all(row.generation is generation for row in rows))

    def test_attributes_reads_only_compact_generation_and_keeps_permission_weights(self):
        generation = object()
        # A wide grid repeats the same source occurrence many times; the
        # compact bag holds it once while retaining distinct source ordinals.
        compact = [('la', 'location', '1', '2', '3'),
                   ('sa', 'same-code', '1', '2', '3'),
                   ('sa', 'same-code', '1', '2', '3'),
                   ('sa', 'null-hierarchy', '1', None, '3')]
        query = MagicMock()
        query.order_by.return_value.values_list.return_value = compact
        with patch.object(BtrScopeDimension.objects, 'filter', return_value=query) as select, \
                patch.object(snapshot.connection, 'cursor', side_effect=AssertionError('wide-grid scan')):
            attributes = snapshot._attributes(generation)
        select.assert_called_once_with(generation=generation)
        query.order_by.assert_called_once_with('owner', 'source_ordinal')
        self.assertEqual(attributes['SkuAttributeData'][0], attributes['SkuAttributeData'][1])
        self.assertIsNone(attributes['SkuAttributeData'][2]['SL2'])
        catalogue = {name: {'records': [dict(id=i, level_1='1', level_2='2', level_3='3') for i in (1, 2)]}
                     for name in ('products', 'locations')}
        with patch.object(context, 'permission_catalogue', return_value=catalogue):
            products, locations = context.scope(dict(product_permissions=[1, 2], location_permissions=[1, 2]),
                                                attributes=attributes)
        self.assertEqual(products.multiplicities, {'same-code': 4})
        self.assertEqual(locations.multiplicities, {'location': 2})
        self.assertNotIn('null-hierarchy', products)

    def setup_build(self, stack, *, existing=None):
        run = SimpleNamespace(pk=uuid4(), kind='DAILY_CHAIN', business_date='2026-04-08')
        lineage = {'pinned': 'unchanged'}
        reference = SimpleNamespace(run_id=run.pk, version=1, status='READY', eligible=True,
            source_digest=digest(lineage), pk=uuid4(), qualification={'populations': {'tech_grid': 2, 'eco_grid': 2}})
        generation = BtrReportingGeneration(pk=uuid4(), run_id=run.pk)
        stack.enter_context(patch.object(generation, 'save'))
        stack.enter_context(patch.object(snapshot.transaction, 'get_autocommit', return_value=False))
        stack.enter_context(patch.object(snapshot.transaction, 'atomic', side_effect=nullcontext))
        stack.enter_context(patch.object(snapshot.connection, 'cursor', return_value=MagicMock()))
        stack.enter_context(patch.object(snapshot.btr_reporting, 'source_identity', return_value=lineage))
        verify = stack.enter_context(patch.object(snapshot.btr_reporting, 'verify_generation', side_effect=AssertionError('full verification')))
        manager = stack.enter_context(patch.object(snapshot.BtrReportingGeneration, 'objects'))
        manager.filter.return_value.first.return_value = existing
        manager.create.return_value = generation
        stack.enter_context(patch.object(snapshot, '_source_operands', return_value={'reference': 'pg_temp.owned_reference'}))
        stream = stack.enter_context(patch.object(snapshot, '_source_rows',
            side_effect=lambda *_args, **_kwargs: iter([(source(1), {}), (source(2), {})])))
        stack.enter_context(patch.object(snapshot, 'prepared_values', return_value={}))
        stack.enter_context(patch.object(snapshot.BtrPresentationRow.objects, 'bulk_create'))
        stack.enter_context(patch.object(snapshot, 'rows_identity', return_value=(4, 'row-identity')))
        stack.enter_context(patch.object(snapshot, 'image_rows', return_value=[]))
        dimensions = stack.enter_context(patch.object(snapshot.BtrScopeDimension.objects, 'bulk_create'))
        return run, reference, generation, dimensions, stream, verify

    def test_build_writes_dimensions_once_and_ready_reuse_writes_nothing(self):
        with ExitStack() as stack:
            run, reference, generation, dimensions, stream, verify = self.setup_build(stack)
            self.assertIs(snapshot._build(run, reference, allow_outer=True), generation)
            dimensions.assert_called_once()
            written = dimensions.call_args.args[0]
            self.assertEqual([(row.owner, row.source_ordinal) for row in written], [('sa', 1), ('sa', 2), ('la', 7)])
            self.assertEqual(stream.call_count, 2)
            snapshot.BtrReportingGeneration.objects.filter.return_value.first.return_value = generation
            self.assertIs(snapshot._build(run, reference, allow_outer=True), generation)
            dimensions.assert_called_once()
            self.assertEqual(stream.call_count, 2)
            verify.assert_not_called()

    def test_new_generation_owns_independent_dimensions(self):
        owners = []
        for _ in range(2):
            with ExitStack() as stack:
                run, reference, generation, dimensions, *_ = self.setup_build(stack)
                snapshot._build(run, reference, allow_outer=True)
                owners.append({row.generation_id for row in dimensions.call_args.args[0]})
        self.assertEqual([len(owner) for owner in owners], [1, 1])
        self.assertFalse(owners[0] & owners[1])

    def test_failed_build_retry_creates_new_generation_without_reusing_partial_dimensions(self):
        with ExitStack() as stack:
            run, reference, failed, dimensions, stream, _ = self.setup_build(stack)

            def interrupted(*_args, **_kwargs):
                yield source(1), {}
                raise RuntimeError('interrupted private build')

            stream.side_effect = interrupted
            with self.assertRaisesRegex(RuntimeError, 'interrupted private build'):
                snapshot._build(run, reference, allow_outer=True)
            dimensions.assert_not_called()
            self.assertTrue(any(call.kwargs.get('status')=='FAILED'
                for call in snapshot.BtrReportingGeneration.objects.filter.return_value.update.call_args_list))
            rebuilt = BtrReportingGeneration(pk=uuid4(), run_id=run.pk)
            stack.enter_context(patch.object(rebuilt, 'save'))
            snapshot.BtrReportingGeneration.objects.create.return_value = rebuilt
            stream.side_effect = lambda *_args, **_kwargs: iter([(source(1), {}), (source(2), {})])
            self.assertIs(snapshot._build(run, reference, allow_outer=True), rebuilt)
            dimensions.assert_called_once()
            self.assertTrue(all(row.generation is rebuilt for row in dimensions.call_args.args[0]))
            self.assertNotEqual(rebuilt.pk, failed.pk)

    def test_upgrade_backfill_is_once_before_immutable_guard_and_retains_ordinals(self):
        migration = import_module('mta.runtime.migrations.0245_btr_scope_dimensions')
        self.assertEqual(migration.Migration.dependencies, [('fresh_mta', '0244_accepted_current_write_context')])
        sql = migration.SCOPE_SQL
        for owner in ('sa', 'la'):
            self.assertIn("SELECT DISTINCT P.generation_id,'"+owner+"',P."+owner+'_ordinal', sql)
            self.assertIn("G.status='READY' AND P."+owner+'_ordinal IS NOT NULL', sql)
        self.assertLess(sql.rindex('INSERT INTO'), sql.index('CREATE TRIGGER'))
        self.assertIn('mta.guard_btr_reference()', sql)
        self.assertIn('mta.deny_btr_reporting_truncate()', sql)
        self.assertNotIn('GRANT ', sql)
