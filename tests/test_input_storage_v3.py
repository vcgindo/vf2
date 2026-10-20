"""Pure in-memory proof for the bounded v3 typed-input storage contract.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'input-storage-v3-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.runtime import input_reader, input_storage, input_v3
from mta.serialization import digest


OWNER = '2cbe5b35-68cc-4aad-a06e-dbb968311f1c'
SOURCE = 'a' * 64


class MemoryImages:
    def __init__(self):
        self.rows = {}
        self.writes = []

    def write(self, owner, path, binding, rows, *, table):
        values = list(rows)
        self.rows[path] = deepcopy(values)
        self.writes.append(path)
        return dict(image=path, table=table, count=len(values), digest=digest(values))

    def read(self, owner, item):
        values = deepcopy(self.rows[item['image']])
        if len(values) != item['count'] or digest(values) != item['digest']:
            raise ValueError('in-memory image drift')
        return values


def identity(owner):
    return dict(database_name='pure_v3', database_oid=37, source_digest=SOURCE,
                owner_kind='initialization', owner_id=str(owner.pk))


def table(fields, path, rows):
    return 'unit/'+path


class InputStorageV3Tests(unittest.TestCase):
    def test_large_uniform_population_is_reiterable_without_per_row_shape_storage(self):
        from mta.row_sequences import RecordRows
        raw={'profile':{'delivery':{'site_code':'PURE'}},
             'large':[{'code':'A','quantity':None} if i%2 else {'code':'B','quantity':i}
                      for i in range(10001)]}
        _,owner,images=self.packed(raw)
        result=input_storage.read_input(owner,image_reader=images.read,identity_resolver=identity)
        self.assertIsInstance(result['large'],RecordRows)
        self.assertEqual(digest(result),digest(raw))
        self.assertEqual(digest(result),digest(raw))
        self.assertEqual(images.writes,['input/large/values'])

    def raw(self):
        canonical = [
            {'code': 'A', 'quantity': None, 'children': [1, 1, 2]},
            {'code': 'A', 'quantity': None, 'children': []},
        ]
        return {
            'profile': {'delivery': {'site_code': 'PURE'}},
            'uniform': [{'code': 'A', 'quantity': None},
                        {'code': 'A', 'quantity': 0}],
            'mixed': [{'code': 'A', 'quantity': None},
                      {'code': 'B', 'enabled': False}],
            'nested': canonical,
            'alias': deepcopy(canonical),
            'empty': [],
        }

    def packed(self, raw=None, *, aliases=None):
        raw = self.raw() if raw is None else raw
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw), kind='INITIALIZATION')
        images = MemoryImages()
        owner.input_payload = input_storage.save_input(owner, raw, version=3,
            aliases=aliases, image_writer=images.write, table_selector=table,
            identity_resolver=identity)
        owner.input_manifest_digest = digest(owner.input_payload)
        return raw, owner, images

    def test_uniform_mixed_nested_and_empty_roundtrip_preserves_exact_values(self):
        raw, owner, images = self.packed()
        result = input_storage.read_input(owner, image_reader=images.read,
                                          identity_resolver=identity)
        self.assertEqual(result, raw)
        uniform = owner.input_payload['tree']['object'][1][1]
        mixed = owner.input_payload['tree']['object'][2][1]
        nested = owner.input_payload['tree']['object'][3][1]
        empty = owner.input_payload['tree']['object'][5][1]
        self.assertIn('shape', uniform)
        self.assertNotIn('shape_image', uniform)
        self.assertIn('shape_image', mixed)
        self.assertIn('shape', nested)
        self.assertEqual(empty['count'], 0)
        self.assertFalse(any(path.endswith('/uniform/shape') or path.endswith('/nested/shape')
                             for path in images.writes))
        self.assertEqual(result['nested'][0]['children'], [1, 1, 2])
        self.assertIsNone(result['mixed'][0]['quantity'])
        self.assertNotIn('quantity', result['mixed'][1])
        self.assertLess(sum(len(part) for part in input_v3.canonical_parts(owner.input_payload)),
                        1024 * 1024)

    def test_schema_constant_is_an_equivalent_explicit_opt_in(self):
        raw = self.raw()
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw), kind='INITIALIZATION')
        images = MemoryImages()
        owner.input_payload = input_storage.save_input(owner, raw, schema=input_storage.V3,
            image_writer=images.write, table_selector=table, identity_resolver=identity)
        owner.input_manifest_digest = digest(owner.input_payload)
        self.assertEqual(owner.input_payload['schema'], input_storage.V3)
        self.assertEqual(input_storage.read_input(owner, image_reader=images.read,
                                                  identity_resolver=identity), raw)

    def test_alias_writes_canonical_population_once_and_reconstructs_both_paths(self):
        raw, owner, images = self.packed(aliases={'input/alias': 'input/nested'})
        self.assertEqual(input_storage.read_input(owner, image_reader=images.read,
                                                  identity_resolver=identity), raw)
        self.assertFalse(any(path.startswith('input/alias') for path in images.writes))
        self.assertEqual(len(images.writes), len(set(images.writes)))
        node = dict(owner.input_payload['tree']['object'])['alias']
        self.assertEqual(node, {'reference': 'input/nested'})
        rebuilt = input_storage.read_input(owner, image_reader=images.read,
                                           identity_resolver=identity)
        self.assertIsNot(rebuilt['alias'], rebuilt['nested'])

    def test_alias_requires_full_ordered_typed_equality(self):
        variants = []
        value = self.raw(); value['alias'][0]['quantity'] = 0; variants.append(value)
        value = self.raw(); del value['alias'][0]['quantity']; variants.append(value)
        value = self.raw(); value['alias'].reverse(); variants.append(value)
        value = self.raw(); value['alias'][0]['children'][0] = True; variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'population differs'):
                self.packed(value, aliases={'input/alias': 'input/nested'})

    def test_alias_rejects_dangling_ref_to_ref_cycle_and_corruption(self):
        raw, owner, images = self.packed(aliases={'input/alias': 'input/nested'})
        cases = []
        dangling = deepcopy(owner.input_payload)
        dangling['aliases']['input/alias'] = 'input/missing'
        dangling['tree']['object'][4][1]['reference'] = 'input/missing'
        cases.append(dangling)
        corrupt = deepcopy(owner.input_payload)
        corrupt['tree']['object'][4][1]['reference'] = 'input/uniform'
        cases.append(corrupt)
        cyclic = deepcopy(owner.input_payload)
        cyclic['aliases'] = {'input/alias': 'input/nested', 'input/nested': 'input/alias'}
        cyclic['tree']['object'][3][1] = {'reference': 'input/alias'}
        cases.append(cyclic)
        for manifest in cases:
            owner.input_payload = manifest
            owner.input_manifest_digest = digest(manifest)
            with self.assertRaises(ValueError):
                input_storage.read_input(owner, image_reader=images.read,
                                         identity_resolver=identity)

    def test_foreign_or_mutable_owner_identity_is_rejected(self):
        _, owner, images = self.packed(aliases={'input/alias': 'input/nested'})
        def foreign(value):
            result = identity(value)
            result['database_oid'] += 1
            return result
        with self.assertRaisesRegex(ValueError, 'live owner identity drift'):
            input_storage.read_input(owner, image_reader=images.read,
                                     identity_resolver=foreign)
        with patch.object(input_v3, '_live_identity',
                          side_effect=ValueError('Typed input run owner is mutable')):
            with self.assertRaisesRegex(ValueError, 'owner is mutable'):
                input_storage.read_input(owner, image_reader=images.read)

    def test_old_v2_manifest_still_reads_and_input_reader_dispatches_v3(self):
        raw = {'profile': {'delivery': {'site_code': 'PURE'}},
               'rows': [{'value': None}, {'value': 7}, {'value': 7}]}
        owner = SimpleNamespace(pk=OWNER, kind='DAILY_CHAIN', input_digest=digest(raw))
        images = MemoryImages()
        owner.input_payload = input_storage.save_input(owner, raw,
            image_writer=images.write, table_selector=table)
        owner.input_manifest_digest = digest(owner.input_payload)
        self.assertEqual(input_storage.read_input(owner, image_reader=images.read), raw)

        raw, owner, images = self.packed(aliases={'input/alias': 'input/nested'})
        with patch.object(input_v3, '_live_identity', side_effect=lambda value, reading: identity(value)), \
                patch.object(input_storage, 'load_image', side_effect=images.read):
            self.assertEqual(input_reader.read_input(owner), raw)


if __name__ == '__main__':
    unittest.main()
