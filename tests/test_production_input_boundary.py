"""File-only checks for the production/offline input and archive boundary."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('VF_SECRET_KEY', 'input-boundary-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.runtime import input_reader, input_storage, relational_state
from mta.serialization import digest


class ProductionInputBoundaryTests(unittest.TestCase):
    def packed(self):
        # Wire shapes only: duplicates, NULL, missing fields, child ordinals,
        # scalar types and explicit empty collections.
        raw = dict(profile={'delivery': {'site_code': 'unit-only'}},
            day={'rows': [dict(code='A', quantity=None, children=[1, 1, 2]),
                          dict(code='A', quantity=None, children=[]),
                          dict(code='B', quantity=0, enabled=False)]}, opening=None)
        owner = SimpleNamespace(pk='owner', kind='DAILY_CHAIN', input_digest=digest(raw))
        images = {}
        def write(run, path, binding, rows, *, table):
            images[path] = list(rows)
            return dict(image=path, table=table, count=len(images[path]), digest=digest(images[path]))
        owner.input_payload = input_storage.save_input(owner, raw, image_writer=write,
            table_selector=lambda fields, path, rows: 'unit-shape')
        owner.input_manifest_digest = digest(owner.input_payload)
        def read(run, item):
            rows = images[item['image']]
            if len(rows) != item['count'] or digest(rows) != item['digest']:
                raise ValueError('image drift')
            return deepcopy(rows)
        return raw, owner, images, read

    def test_full_and_component_reads_preserve_shapes_and_skip_unselected_images(self):
        raw, run, _, reader = self.packed()
        with patch('mta.runtime.input_storage.load_image', side_effect=reader) as read:
            self.assertEqual(input_reader.read_input(run), raw)
            read.reset_mock()
            self.assertEqual(input_reader.read_input(run, components=('profile',)), {'profile': raw['profile']})
            read.assert_not_called()
            # Optional fields are intentionally queried by existing callers.
            self.assertEqual(input_reader.read_input(run, components=('initialization_binding',)), {})

    def test_changed_or_missing_input_is_never_a_valid_empty_result(self):
        raw, run, images, reader = self.packed()
        with patch('mta.runtime.input_storage.load_image', side_effect=reader):
            first = next(iter(images))
            images[first].pop()
            with self.assertRaises(ValueError):input_reader.read_input(run)
        for mutate in (lambda r: r.input_payload.update(schema='unknown'),
                       lambda r: r.input_payload.update(content_digest='0'*64),
                       lambda r: r.input_payload['images'].clear()):
            _, run, _, reader = self.packed()
            mutate(run)
            with patch('mta.runtime.input_storage.load_image', side_effect=reader), self.assertRaises(ValueError):
                input_reader.read_input(run)
        for value in (raw, {'schema': 'fresh-input-reference-v1', 'path': 'owner/InputSnapshot.jsonl.gz'}):
            run.input_payload = value
            with self.assertRaisesRegex(ValueError, 'native input'):input_reader.read_input(run)

    def test_current_day_inline_input_is_still_owned_and_digest_checked(self):
        value = {'foundation': {'snapshot': {'business_date': '2037-04-10'}}}
        run = SimpleNamespace(kind='CURRENT_DAY', input_payload=value, input_digest=digest(value))
        self.assertEqual(input_reader.read_input(run), value)
        run.input_digest = '0'*64
        with self.assertRaises(ValueError):input_reader.read_input(run)
        run.input_payload = {'schema': 'fresh-input-reference-v1'}
        run.input_digest = digest(run.input_payload)
        with self.assertRaises(ValueError):input_reader.read_input(run)

    def test_typed_reader_keeps_run_image_owner_order_and_digest_guards(self):
        rows = [{'value': None}, {'value': 7}, {'value': 7}]
        table = next(iter(relational_state.STORAGE_TABLES))
        item = dict(table=table, image='input/owned', fields=[['value', 'value', 'int']], count=3, digest=digest(rows))
        run = SimpleNamespace(pk='exact-owner')
        cursor = MagicMock()
        def read(records):
            cursor.fetchmany.side_effect = [records, []]
            with patch.object(relational_state.connection, 'cursor') as context:
                context.return_value.__enter__.return_value = cursor
                return relational_state.load_image(run, item)
        self.assertEqual(read([(0, None), (1, 7), (2, 7)]), rows)
        self.assertEqual(cursor.execute.call_args.args[1], ['exact-owner', 'input/owned'])
        for records in ([(1, None), (2, 7), (3, 7)], [(0, None), (1, 7)],
                        [(0, None), (1, 7), (2, 8)]):
            with self.assertRaises(ValueError):read(records)
        with patch.object(relational_state.connection, 'cursor', side_effect=AssertionError('unknown table queried')):
            with self.assertRaisesRegex(ValueError, 'Unknown operational table'):
                relational_state.load_image(run, dict(item, table='unknown'))

    def test_offline_snapshot_roundtrip_keeps_owner_hash_and_negative_checks(self):
        from development import validation_storage as offline
        raw = {'profile': {'delivery': {'site_code': 'same-wire'}}, 'rows': [None, 1, 1]}
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, VF_EVIDENCE_ROOT=root):
            run = SimpleNamespace(pk='owned')
            run.input_payload = offline.store_input(run.pk, raw)
            self.assertEqual(offline.read_input(run), raw)
            run.input_payload['path'] = 'other/InputSnapshot.jsonl.gz'
            with self.assertRaisesRegex(ValueError, 'owner/path'):offline.read_input(run)
            run.input_payload['path'] = 'owned/InputSnapshot.jsonl.gz'
            path = Path(root) / run.input_payload['path']
            path.write_bytes(path.read_bytes() + b'drift')
            with self.assertRaisesRegex(ValueError, 'file drift'):offline.read_input(run)
            path.unlink()
            with self.assertRaises(FileNotFoundError):offline.read_input(run)

    def test_native_pick_recovery_uses_committed_state_and_never_calculates(self):
        from mta.runtime.temporal import replay_completed
        run = SimpleNamespace(pk='owner', status='SUCCEEDED', production_manifest={})
        complete = {'LogisticPickList': [], 'PickListDataForTruckFormation': []}
        with patch('mta.runtime.temporal.read_outputs', return_value={'ClosingState': [{'complete': complete}]}) as read, \
                patch('mta.application.complete_daily_batch_files.write_run_pick_files') as write, \
                patch('mta.runtime.temporal.calculate_day', side_effect=AssertionError('recalculation')):
            self.assertIs(replay_completed(run, complete_pick=True, pick_output_root='owned'), run)
            self.assertIs(replay_completed(run, complete_pick=True, pick_output_root='owned'), run)
            self.assertEqual(write.call_count, 2)
            write.assert_called_with('owner', complete, 'owned')
            read.side_effect = ValueError('unreadable committed state')
            with self.assertRaises(ValueError):replay_completed(run, complete_pick=True, pick_output_root='owned')
            self.assertEqual(write.call_count, 2)

    def test_supported_runtime_imports_without_parity_offline_or_trace_storage(self):
        code = """
import importlib, importlib.abc, os, sys
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('parity', 'development') or fullname == 'mta.runtime.validation_storage':
            raise AssertionError('Forbidden production import: '+fullname)
sys.meta_path.insert(0, Deny())
os.environ['VF_SECRET_KEY']='import-unit-only'
os.environ['DJANGO_SETTINGS_MODULE']='vectorflow.settings'
import django
django.setup()
from django.db.backends.base.base import BaseDatabaseWrapper
def no_database(*a, **k):raise AssertionError('No database authority')
BaseDatabaseWrapper.ensure_connection=no_database
for name in ('vectorflow.urls', 'mta.runtime.production_daily', 'mta.runtime.temporal',
             'mta.runtime.operational_runner', 'mta.runtime.operational_attempts',
             'mta.presentation.native_publication', 'mta.presentation.daily_rrr_storage',
             'mta.runtime.management.commands.cohort2_operational',
             'mta.runtime.management.commands.register_cohort6_operational'):
    importlib.import_module(name)
print('supported imports PASS; no database access')
"""
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)



    def test_native_pick_writer_and_reader_preserve_duplicate_ordinals_and_reject_drift(self):
        from uuid import uuid4
        from mta.presentation import pick_storage as pick
        from mta.runtime.models import CalculationRun
        run = CalculationRun(pk=uuid4(), kind='DAILY_CHAIN', production_manifest={})
        row = dict(sku_code='SKU', location_code='LOC', parent_location_code='PARENT',
                   to_black='0', to_red='1', to_yellow='2', to_green='3', to_blue='4')
        rows = [row, deepcopy(row)]
        calculated = [dict(capability='r1_ration_bifurcation', rows=rows)]
        saved = []
        receipts = []
        def projection(**values):
            receipt = SimpleNamespace(version=1, **values)
            receipts.append(receipt)
            return receipt
        query = MagicMock()
        query.order_by.return_value.values.side_effect = lambda *fields: [
            {field: getattr(record, field) for field in fields} for record in saved]
        with patch.object(pick.transaction, 'get_autocommit', return_value=False), \
                patch.object(pick.PickProjection.objects, 'create', side_effect=projection), \
                patch.object(pick.PickProjection.objects, 'get', side_effect=lambda **kw: receipts[0]), \
                patch.object(pick.PickBand.objects, 'bulk_create', side_effect=lambda records, **kw: saved.extend(records)), \
                patch.object(pick.PickBand.objects, 'filter', return_value=query), \
                patch.object(pick.Checkpoint.objects, 'get', return_value=SimpleNamespace(digest=digest(calculated))):
            pick.write_pick_bands(run, calculated, provenance={'origin': 'unit-protocol-only'})
            self.assertEqual(pick.read_pick_bands(run), rows)
            self.assertEqual([record.ordinal for record in saved], [0, 1])
            saved[1].ordinal = 0
            with self.assertRaisesRegex(ValueError, 'population/order'):pick.read_pick_bands(run)
            saved[1].ordinal = 1
            saved[1].to_red = 9
            with self.assertRaisesRegex(ValueError, 'values/multiplicity'):pick.read_pick_bands(run)

    def test_offline_writer_is_explicit_and_production_adapter_does_not_supply_it(self):
        from development import temporal as offline
        with patch.object(offline, '_execute_day', return_value='run') as execute:
            self.assertEqual(offline.execute_day(day={'business_date': 'unit-only'}), 'run')
            self.assertIs(execute.call_args.kwargs['checkpoint_writer'], offline.persist_trace)
            offline.execute_day(day={}, evidence_mode='production')
            self.assertNotIn('checkpoint_writer', execute.call_args.kwargs)


if __name__ == '__main__':unittest.main()
