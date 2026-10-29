"""Accepted input decoding fixtures; no database or admission is exercised."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'accepted-input-reader-unit-only')
import django
django.setup()

from mta.row_sequences import RecordRows
from mta.runtime import accepted_input_read as reader, input_storage, input_v3, relational_state, batch_storage, opening_storage
from mta.serialization import digest, storage
from tests.test_accepted_state_read import Database


def scalar(value):
    return {'scalar': value}


def object_node(**values):
    return {'object': list(values.items())}


class Images:
    def __init__(self):
        self.values, self.reads = {}, []

    def write(self, owner, path, binding, rows, *, table):
        values = storage(list(rows))
        self.values[owner.pk, path] = values
        return dict(image=path, table=table, count=len(values), digest=digest(values))

    def read(self, owner, item):
        self.reads.append((owner.pk, item['image']))
        return deepcopy(self.values[owner.pk, item['image']])


class AcceptedInputReadTests(TestCase):
    def no_audits(self):
        stack = ExitStack()
        for module in (input_storage, input_v3, relational_state, batch_storage, opening_storage):
            for name in ('digest', 'canonical_parts', '_live_identity', 'read_input', 'iter_image',
                         '_resolve_owner', '_resolve_batch', '_resolve_derived_master', 'iter_population'):
                if hasattr(module, name):
                    stack.enter_context(patch.object(module, name,
                        side_effect=AssertionError('Checked input path or hash called: ' + name)))
        stack.enter_context(patch.object(RecordRows, 'from_rows', side_effect=AssertionError('Spool called')))
        return stack

    def packed(self, raw, version=3, aliases=None):
        images = Images()
        owner = SimpleNamespace(pk=uuid4(), input_digest=digest(raw), kind='DAILY_CHAIN')
        identity = lambda current: dict(database_name='fixture', database_oid=1,
            source_digest='a' * 64, owner_kind='run', owner_id=str(current.pk))
        options = dict(image_writer=images.write,
                       table_selector=lambda fields, path, rows: 'fixture' if rows else None)
        if version == 3:
            options.update(identity_resolver=identity, aliases=aliases)
        owner.input_payload = input_storage.save_input(owner, raw, version=version, **options)
        owner.input_manifest_digest = digest(owner.input_payload)
        return owner, images, identity

    def test_v2_and_v3_exact_nested_shape_children_scalars_types_and_pruning(self):
        raw = dict(profile={'delivery': {'site_code': 'fixture'}}, empty=[], nothing=None,
            labels=['雪', None, '雪'], numbers=[0, None, 0],
            rows=[{'code': 'A', 'nil': None, 'amount': 0, 'active': False,
                   'nested': {'price': '1.230', 'children': [{'code': 'X'}, {'code': 'X'}]}},
                  {'code': 'A', 'nil': None, 'amount': 0, 'active': False,
                   'nested': {'price': '1.230', 'children': []}},
                  {'other': 0.5}], only_children=[{'children': []}, {'children': []}])
        for version in (2, 3):
            with self.subTest(version=version):
                owner, images, identity = self.packed(raw, version)
                expected = input_storage.read_input(owner, image_reader=images.read,
                    **({'identity_resolver': identity} if version == 3 else {}))
                with self.no_audits():
                    actual = reader.read_accepted_input(owner, _image_reader=images.read)
                    self.assertEqual(actual, expected)
                    self.assertIs(type(actual['rows'][0]['amount']), int)
                    self.assertIs(type(actual['rows'][0]['active']), bool)
                    self.assertEqual(list(actual['rows'][0]), list(raw['rows'][0]))
                    self.assertEqual(reader.read_accepted_input(owner, components=('absent',),
                        _image_reader=images.read), {})
                    self.assertEqual(reader.read_accepted_input(owner, components=('empty',),
                        _image_reader=images.read), {'empty': []})
                if version == 3:
                    images.reads.clear()
                    with self.no_audits():
                        self.assertEqual(reader.read_accepted_input(owner,
                            components=('input/profile/delivery',), _image_reader=images.read),
                            {'profile': {'delivery': {'site_code': 'fixture'}}})
                    self.assertEqual(images.reads, [])

    def test_one_hop_alias_reads_once_and_mutable_lists_do_not_alias(self):
        rows = [{'code': 'A', 'value': None}, {'code': 'A', 'value': None}]
        raw = dict(profile={'delivery': {'site_code': 'fixture'}}, original=rows, copied=deepcopy(rows))
        owner, images, _ = self.packed(raw, aliases={'input/copied': 'input/original'})
        images.reads.clear()
        with self.no_audits():
            actual = reader.read_accepted_input(owner, _image_reader=images.read)
        self.assertEqual(actual, raw)
        self.assertEqual(images.reads.count((owner.pk, 'input/original/values')), 1)
        actual['copied'][0]['value'] = 'changed'
        self.assertIsNone(actual['original'][0]['value'])
        with self.no_audits():
            second = reader.read_accepted_input(owner, _image_reader=images.read)
        self.assertEqual(second, raw)

    def test_large_uniform_rows_are_lazy_or_explicitly_materialized(self):
        owner, images, _ = self.packed(dict(profile={'delivery': {'site_code': 'fixture'}},
            rows=[{'value': index} for index in range(10001)]))
        original_read = images.read
        scans = []
        def image(current, item):
            def rows():
                scans.append(item['image'])
                yield from original_read(current, item)
            return RecordRows(item['count'], rows)
        with self.no_audits():
            result = reader.read_accepted_input(owner, components=('rows',), _image_reader=image)
            self.assertIsInstance(result['rows'], RecordRows)
            self.assertEqual(scans, [])
            self.assertEqual(sum(row['value'] for row in result['rows']), sum(range(10001)))
            self.assertEqual(scans, ['input/rows/values'])
            result = reader.read_accepted_input(owner, components=('rows',),
                materialized_roots=('input/rows',), _image_reader=image)
            self.assertIsInstance(result['rows'], list)
            self.assertEqual(len(scans), 2)

    def test_owner_references_follow_declared_initialization_and_run_paths(self):
        initial, init_images, _ = self.packed(dict(profile={'delivery': {'site_code': 'INITIAL'}},
            opening={'rows': [{'v': None}, {'v': None}]}), version=2)
        parent, parent_images, _ = self.packed(dict(profile={'delivery': {'site_code': 'PARENT'}},
            mdm_input={'rows': {'sku': {'attributes': [{'id': 7, 'value': False}]}}}))
        owner = SimpleNamespace(pk=uuid4(), input_payload={'schema': reader.V3, 'images': {},
            'tree': object_node(profile={'owner_reference': 'input/profile'},
                opening={'owner_reference': 'input/opening'},
                mdm_input=object_node(rows=object_node(sku=object_node(attributes={
                    'owner_reference': 'input/mdm_input/rows/sku/attributes'})))),
            'owner_references': {
                'input/profile': dict(kind='INITIALIZATION', owner_id=str(initial.pk), path='input/profile'),
                'input/opening': dict(kind='INITIALIZATION', owner_id=str(initial.pk), path='input/opening'),
                'input/mdm_input/rows/sku/attributes': dict(kind='RUN', owner_id=str(parent.pk),
                    path='input/mdm_input/rows/sku/attributes')}})
        def image(current, item):
            return (init_images if current is initial else parent_images).read(current, item)
        resolver = lambda current, reference: initial if reference['kind'] == 'INITIALIZATION' else parent
        with self.no_audits():
            result = reader.read_accepted_input(owner, _image_reader=image, _owner_resolver=resolver)
        self.assertEqual(result, {'profile': {'delivery': {'site_code': 'INITIAL'}},
            'opening': {'rows': [{'v': None}, {'v': None}]},
            'mdm_input': {'rows': {'sku': {'attributes': [{'id': 7, 'value': False}]}}}})
        owner.input_payload['owner_references']['input/opening']['path'] = 'input/missing'
        with self.no_audits(), self.assertRaises(KeyError):
            reader.read_accepted_input(owner, _image_reader=image, _owner_resolver=resolver)

    def test_opening_namespace_and_ownership_columns_are_not_run_storage(self):
        owner = SimpleNamespace(pk=uuid4(), _meta=SimpleNamespace(model_name='productioninitialization'),
            input_payload={'schema': reader.V3, 'images': {'input/rows/values': dict(
                table='input/row_shape', image='input/rows/values', count=2,
                fields=[['shape_id', 'shape_id', 'int']])}, 'tree': object_node(rows={
                    'shape': ['dict', [['shape_id', ['value', ['shape_id']]]]],
                    'count': 2, 'records': 'input/rows/values', 'children': []})})
        database = Database(lambda *_: [(0, 0), (1, 0)])
        with patch.object(reader, 'connection', database), self.no_audits():
            self.assertEqual(reader.read_accepted_input(owner), {'rows': [{'shape_id': 0}, {'shape_id': 0}]})
        sql, params = database.queries[0]
        self.assertIn('FROM mta_opening.', sql)
        self.assertIn('WHERE vf_initialization_id=%s AND vf_image=%s ORDER BY vf_ordinal', sql)
        self.assertEqual(params, [owner.pk, 'input/rows/values'])

    def test_batch_reference_preserves_temporal_wire_text_and_is_lazy_for_large(self):
        filename = '@consumer/remarks/bpr'
        entry = dict(filename=filename, count=10001, fields=[['SKUCode', 'SKUCode', 'str'],
            ['Remark', 'Remark', 'str'], ['RemarkDate', 'RemarkDate', 'str']])
        attempt = SimpleNamespace(attempt_id=uuid4(), accepted_facts={'feeds': [entry]})
        path = 'input/remark_inputs/bpr'
        owner = SimpleNamespace(pk=uuid4(), input_payload={'schema': reader.V3, 'images': {},
            'tree': object_node(remark_inputs=object_node(bpr={'batch_reference': path})),
            'batch_references': {path: dict(attempt_id=str(attempt.attempt_id), filename=filename, count=10001)}})
        stamp = datetime(2037, 4, 10, 1, 2, tzinfo=timezone.utc)
        wire = '2037-04-10T06:32:00+05:30'
        database = Database(lambda *_: ((ordinal, 'S', None, stamp, wire) for ordinal in range(10001)))
        with patch.object(reader, 'connection', database), self.no_audits():
            result = reader.read_accepted_input(owner, _batch_resolver=lambda *_: attempt)
            self.assertEqual(database.queries, [])
            self.assertIsInstance(result['remark_inputs']['bpr'], RecordRows)
            values = list(result['remark_inputs']['bpr'])
        self.assertEqual(values, [{'SKUCode': 'S', 'Remark': None, 'RemarkDate': wire}] * 10001)
        self.assertEqual(len(database.queries), 1)
        self.assertIn('"vf_wire_RemarkDate"', database.queries[0][0])
        self.assertEqual(database.queries[0][1], [str(attempt.attempt_id)])
        self.assertEqual(set(database.fetch_sizes), {500})

    def test_derived_master_exact_raw_projection_with_frozen_overlay_and_duplicates(self):
        from tests.test_master_compatibility import unchanged_snapshot, nms_item, full_raw
        from mta.application.persistent_master import NmsMasterRows
        from mta.application import master_compatibility
        snapshot, values = unchanged_snapshot(), [nms_item(), nms_item()]
        expected = full_raw(snapshot, values)
        raw = dict(profile={'delivery': {'site_code': 'fixture'}},
                   day={'business_date': '2026-10-19', 'raw_master': []}, mdm_input=snapshot)
        owner, images, _ = self.packed(raw)
        reference = {'run_id': str(uuid4())}
        owner.input_payload['derived_references'] = {'input/day/raw_master': reference}
        dict(dict(owner.input_payload['tree']['object'])['day']['object'])['raw_master'].clear()
        dict(dict(owner.input_payload['tree']['object'])['day']['object'])['raw_master'].update(
            derived_master='input/day/raw_master')
        parent = SimpleNamespace(pk=reference['run_id'], production_manifest={'images': {
            'closing/consumer_context/NMSAllItems': {'image': 'parent-nms'}}})
        def image(current, item):
            return deepcopy(values) if current is parent else images.read(current, item)
        with self.no_audits(), patch.object(master_compatibility, 'unchanged_plan',
                side_effect=AssertionError('Compatibility admission repeated')):
            result = reader.read_accepted_input(owner, components=('input/day/raw_master',),
                _image_reader=image, _run_resolver=lambda *_: parent)['day']['raw_master']
            self.assertIsInstance(result, NmsMasterRows)
            self.assertEqual(list(result), expected)

    def test_all_captured_formats_follow_declared_physical_origin_without_audit(self):
        original, images, _ = self.packed(dict(profile={'delivery': {'site_code': 'fixture'}}, rows=[]))
        for schema in reader.CAPTURED:
            with self.subTest(schema=schema):
                owner = SimpleNamespace(pk=uuid4(), input_payload={'schema': schema,
                    'origin_run_id': str(original.pk) if schema.endswith('v1') else 'wrapper'})
                if not schema.endswith('v1'):
                    owner.input_payload['physical_origin_run_id'] = str(original.pk)
                calls = []
                def resolve(current, identifier):
                    calls.append(identifier)
                    return original
                with self.no_audits():
                    self.assertEqual(reader.read_accepted_input(owner, components=('rows',),
                        _image_reader=images.read, _run_resolver=resolve), {'rows': []})
                self.assertEqual(calls, [str(original.pk)])
