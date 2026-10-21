"""Pure in-memory proof for the bounded v3 typed-input storage contract.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from collections.abc import Sequence
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
from mta.application.persistent_master import NmsMasterRows
from mta.application.r1_importer_master import RAW_COLUMNS


OWNER = '2cbe5b35-68cc-4aad-a06e-dbb968311f1c'
SOURCE = 'a' * 64
ATTEMPT = '7b18db18-a4fc-4d68-937b-5726a6f13fd4'


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


def run_identity(owner):
    return dict(database_name='pure_v3', database_oid=37, source_digest=SOURCE,
                owner_kind='run', owner_id=str(owner.pk))


def table(fields, path, rows):
    return 'unit/'+path


class InputStorageV3Tests(unittest.TestCase):
    def batch(self, rows):
        manifest = {'contract': 'fresh-daily-batch-storage-v1', 'intake': 'unit',
            'database_name': 'pure_v3', 'database_oid': 37, 'source_id': 4,
            'source_digest': SOURCE, 'initialization_id': OWNER, 'attempt_id': ATTEMPT,
            'feeds': [{'filename': 'DailyDataRaw.csv', 'path': 'day/raw_daily',
                'table': 'batch_dailydataraw', 'columns': [], 'fields': [],
                'count': len(rows), 'digest': digest(rows)}]}
        attempt = SimpleNamespace(attempt_id=ATTEMPT, run_id=OWNER, accepted_facts=manifest)
        reference = dict(attempt_id=ATTEMPT, filename='DailyDataRaw.csv',
            manifest_digest=digest(manifest), population_digest=digest(rows), count=len(rows))
        return attempt, reference

    def test_batch_reference_roundtrip_writes_no_duplicate_image_and_audits(self):
        rows = [{'SKUCode': 'A', 'WhCode': None, 'Stock': 7} ,
                {'SKUCode': 'A', 'WhCode': None, 'Stock': 7}]
        raw = {'profile': {'delivery': {'site_code': 'PURE'}},
               'day': {'raw_daily': deepcopy(rows)}}
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw), kind='DAILY_CHAIN')
        attempt, reference = self.batch(rows)
        images = MemoryImages()
        batch_identity = dict(database_name='pure_v3', database_oid=37, source_id=4,
            source_digest=SOURCE, initialization_id=OWNER, attempt_id=ATTEMPT)
        resolver = lambda run, attempt_id: attempt
        refs = {'input/day/raw_daily': reference}
        with patch('mta.runtime.batch_storage._live_identity', return_value=batch_identity), \
                patch('mta.runtime.batch_storage.iter_population',
                      side_effect=lambda *args, **kwargs: iter(deepcopy(rows))):
            owner.input_payload = input_storage.save_input(owner, raw, version=3,
                batch_references=refs, batch_resolver=resolver,
                image_writer=images.write, table_selector=table,
                identity_resolver=run_identity)
            owner.input_manifest_digest = digest(owner.input_payload)
            self.assertFalse(any(path.startswith('input/day/raw_daily') for path in images.writes))
            self.assertEqual(dict(owner.input_payload['tree']['object'])['day']['object'][0][1],
                             {'batch_reference': 'input/day/raw_daily'})
            self.assertEqual(input_storage.read_input(owner, image_reader=images.read,
                identity_resolver=run_identity, batch_resolver=resolver), raw)
            self.assertEqual(input_storage.audit_references(owner,
                identity_resolver=run_identity, batch_resolver=resolver), refs)

    def test_batch_reference_rejects_nonfact_mismatch_foreign_and_failed(self):
        rows = [{'value': 1}]
        raw = {'profile': {'delivery': {'site_code': 'PURE'}},
               'day': {'raw_daily': deepcopy(rows), 'raw_master': deepcopy(rows)}}
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw), kind='DAILY_CHAIN')
        attempt, reference = self.batch(rows)
        resolver = lambda run, attempt_id: attempt
        images = MemoryImages()
        batch_identity = dict(database_name='pure_v3', database_oid=37, source_id=4,
            source_digest=SOURCE, initialization_id=OWNER, attempt_id=ATTEMPT)
        kwargs = dict(version=3, batch_resolver=resolver, image_writer=images.write,
            table_selector=table, identity_resolver=run_identity)
        with patch('mta.runtime.batch_storage._live_identity', return_value=batch_identity), \
                patch('mta.runtime.batch_storage.iter_population',
                      side_effect=lambda *args, **kwargs: iter(deepcopy(rows))):
            changed = deepcopy(reference); changed['population_digest'] = 'b' * 64
            with self.assertRaises(ValueError):
                input_storage.save_input(owner, raw,
                    batch_references={'input/day/raw_daily': changed}, **kwargs)
            with self.assertRaises(ValueError):
                input_storage.save_input(owner, raw,
                    batch_references={'input/day/raw_master': reference}, **kwargs)
            mismatch = deepcopy(raw); mismatch['day']['raw_daily'][0]['value'] = True
            owner.input_digest = digest(mismatch)
            with self.assertRaisesRegex(ValueError, 'population differs'):
                input_storage.save_input(owner, mismatch,
                    batch_references={'input/day/raw_daily': reference}, **kwargs)
        owner.input_digest = digest(raw)
        foreign = dict(batch_identity, database_oid=38)
        with patch('mta.runtime.batch_storage._live_identity', return_value=foreign):
            with self.assertRaisesRegex(ValueError, 'database/source'):
                input_storage.save_input(owner, raw,
                    batch_references={'input/day/raw_daily': reference}, **kwargs)
        with patch('mta.runtime.batch_storage._live_identity',
                   side_effect=ValueError('failed or rejected batch')):
            with self.assertRaisesRegex(ValueError, 'failed or rejected'):
                input_storage.save_input(owner, raw,
                    batch_references={'input/day/raw_daily': reference}, **kwargs)

    def test_own_running_or_failed_run_can_read_only_its_sealed_manifest(self):
        class Run:
            _meta = SimpleNamespace(model_name='calculationrun')
        class Manager:
            def get(self, **kwargs): return current
        Run.objects = Manager()
        owner = Run(); owner.pk = OWNER
        current = Run(); current.pk = OWNER; current.status = 'RUNNING'
        current.input_manifest_digest = 'b' * 64
        current.csv_attempt = SimpleNamespace(initialization=SimpleNamespace(
            source=SimpleNamespace(digest=SOURCE)))
        with patch.object(input_v3, '_database_identity', return_value=('pure_v3', 37)):
            self.assertEqual(input_v3._live_identity(owner, reading=True)['owner_kind'], 'run')
            current.input_manifest_digest = ''
            with self.assertRaisesRegex(ValueError, 'mutable'):
                input_v3._live_identity(owner, reading=True)
            current.input_manifest_digest = 'b' * 64
            current.status = 'FAILED'
            self.assertEqual(input_v3._live_identity(owner, reading=True)['owner_kind'], 'run')
            current.status = 'REJECTED'
            with self.assertRaisesRegex(ValueError, 'mutable'):
                input_v3._live_identity(owner, reading=True)

    def test_failed_batch_reference_is_private_to_original_run(self):
        rows = [{'value': 1}]
        raw = {'profile': {'delivery': {'site_code': 'PURE'}},
               'day': {'raw_daily': deepcopy(rows)}}
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw), kind='DAILY_CHAIN')
        attempt, reference = self.batch(rows)
        resolver = lambda run, attempt_id: attempt
        images = MemoryImages()
        batch_identity = dict(database_name='pure_v3', database_oid=37, source_id=4,
            source_digest=SOURCE, initialization_id=OWNER, attempt_id=ATTEMPT)
        flags = []
        def live(*args, **kwargs):
            flags.append(kwargs.get('allow_owned_failed', False))
            return batch_identity
        with patch('mta.runtime.batch_storage._live_identity', side_effect=live), \
                patch('mta.runtime.batch_storage.iter_population',
                      side_effect=lambda *args, **kwargs: iter(deepcopy(rows))):
            owner.input_payload = input_storage.save_input(owner, raw, version=3,
                batch_references={'input/day/raw_daily': reference}, batch_resolver=resolver,
                image_writer=images.write, table_selector=table,
                identity_resolver=run_identity)
            owner.input_manifest_digest = digest(owner.input_payload)
            self.assertEqual(input_storage.read_input(owner, image_reader=images.read,
                identity_resolver=run_identity, batch_resolver=resolver), raw)
        self.assertIn(False, flags)
        self.assertIn(True, flags)

        target_id = '4ea5c75d-96a0-4961-864a-d42ef981602c'
        target = SimpleNamespace(pk=target_id, input_digest=owner.input_digest,
                                 input_payload=deepcopy(owner.input_payload))
        target.input_payload['identity']['owner_id'] = target_id
        target.input_manifest_digest = digest(target.input_payload)
        target_identity = lambda value: dict(run_identity(value), owner_id=target_id)
        with self.assertRaisesRegex(ValueError, 'batch owner differs'):
            input_storage.read_input(target, image_reader=images.read,
                identity_resolver=target_identity, batch_resolver=resolver)

    def test_audit_exhausts_large_reference_and_detects_late_drift(self):
        rows = [{'value': i} for i in range(10001)]
        raw = {'profile': {'delivery': {'site_code': 'PURE'}},
               'day': {'raw_daily': rows}}
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw), kind='DAILY_CHAIN')
        attempt, reference = self.batch(rows)
        resolver = lambda run, attempt_id: attempt
        images = MemoryImages()
        batch_identity = dict(database_name='pure_v3', database_oid=37, source_id=4,
            source_digest=SOURCE, initialization_id=OWNER, attempt_id=ATTEMPT)
        calls = [0]
        def stream(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                return iter(rows)
            def late_drift():
                for row in rows[:-1]:
                    yield row
                raise ValueError('late ordinal/digest drift')
            return late_drift()
        with patch('mta.runtime.batch_storage._live_identity', return_value=batch_identity), \
                patch('mta.runtime.batch_storage.iter_population', side_effect=stream):
            owner.input_payload = input_storage.save_input(owner, raw, version=3,
                batch_references={'input/day/raw_daily': reference}, batch_resolver=resolver,
                image_writer=images.write, table_selector=table,
                identity_resolver=run_identity)
            owner.input_manifest_digest = digest(owner.input_payload)
            with self.assertRaisesRegex(ValueError, 'late ordinal/digest drift'):
                input_storage.audit_references(owner, identity_resolver=run_identity,
                    batch_resolver=resolver)
        self.assertEqual(calls[0], 2)

    def test_owner_reference_roundtrip_is_physical_one_hop_and_partial(self):
        target_id = '6f2e9e47-2c35-42c8-a1f1-70eb937f1fd3'
        initialization_id = 'df0386c9-35fe-44ce-9447-c86940f35637'
        rows = [{'SKUCode': 'A', 'Weight': '1.250'},
                {'SKUCode': 'A', 'Weight': None}]
        target_raw = {'profile': {'delivery': {'site_code': 'PURE'}},
            'mdm_input': {'rows': {'sku': {'attributes': deepcopy(rows), 'descriptions': []},
                'location': {'attributes': [], 'descriptions': []},
                'skuloc': {'attributes': [], 'descriptions': []}}}}
        target = SimpleNamespace(pk=target_id, status='SUCCEEDED',
            input_digest=digest(target_raw), kind='DAILY_CHAIN',
            _reference_initialization_id=initialization_id, _reference_accepted=True)
        target._reference_identity = run_identity(target)
        target_images = MemoryImages()
        target.input_payload = input_storage.save_input(target, target_raw, version=3,
            image_writer=target_images.write, table_selector=table,
            identity_resolver=lambda value: value._reference_identity)
        target.input_manifest_digest = digest(target.input_payload)

        raw = {'profile': {'delivery': {'site_code': 'CURRENT'}},
            'mdm_input': {'rows': {'sku': {'attributes': deepcopy(rows), 'descriptions': []},
                'location': {'attributes': [], 'descriptions': []},
                'skuloc': {'attributes': [], 'descriptions': []}}}}
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw), kind='DAILY_CHAIN',
            _reference_initialization_id=initialization_id)
        path = 'input/mdm_input/rows/sku/attributes'
        reference = dict(kind='RUN', owner_id=target_id, path=path,
            manifest_digest=target.input_manifest_digest, content_digest=target.input_digest)
        owner_images = MemoryImages()
        resolver = lambda current, body: target
        with patch('mta.runtime.relational_state.load_image', side_effect=target_images.read):
            owner.input_payload = input_storage.save_input(owner, raw, version=3,
                owner_references={path: reference}, owner_resolver=resolver,
                image_writer=owner_images.write, table_selector=table,
                identity_resolver=run_identity)
            owner.input_manifest_digest = digest(owner.input_payload)
            self.assertFalse(any(name.startswith(path) for name in owner_images.writes))
            partial = input_storage.read_input(owner,
                components=('mdm_input/rows/sku/attributes',),
                image_reader=owner_images.read, identity_resolver=run_identity,
                owner_resolver=resolver)
            self.assertEqual(partial, {'mdm_input': {'rows': {'sku': {'attributes': rows}}}})
            self.assertEqual(input_storage.audit_references(owner,
                identity_resolver=run_identity, owner_resolver=resolver), {path: reference})

    def test_owner_reference_rejects_same_mutable_foreign_and_reference_chain(self):
        target_id = '6f2e9e47-2c35-42c8-a1f1-70eb937f1fd3'
        initialization_id = 'df0386c9-35fe-44ce-9447-c86940f35637'
        path = 'input/mdm_input/rows/sku/attributes'
        rows = [{'SKUCode': 'A'}]
        target_raw = {'profile': {'delivery': {'site_code': 'PURE'}},
            'mdm_input': {'rows': {'sku': {'attributes': rows}}}}
        target = SimpleNamespace(pk=target_id, status='SUCCEEDED',
            input_digest=digest(target_raw), _reference_initialization_id=initialization_id,
            _reference_accepted=True, _reference_identity=None)
        target._reference_identity = run_identity(target)
        images = MemoryImages()
        target.input_payload = input_storage.save_input(target, target_raw, version=3,
            image_writer=images.write, table_selector=table,
            identity_resolver=lambda value: value._reference_identity)
        target.input_manifest_digest = digest(target.input_payload)
        raw = deepcopy(target_raw); raw['profile']['delivery']['site_code'] = 'CURRENT'
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw),
            _reference_initialization_id=initialization_id)
        reference = dict(kind='RUN', owner_id=target_id, path=path,
            manifest_digest=target.input_manifest_digest, content_digest=target.input_digest)
        kwargs = dict(version=3, owner_references={path: reference},
            owner_resolver=lambda current, body: target, image_writer=MemoryImages().write,
            table_selector=table, identity_resolver=run_identity)
        with patch('mta.runtime.relational_state.load_image', side_effect=images.read):
            target.status = 'RUNNING'
            with self.assertRaisesRegex(ValueError, 'mutable'):
                input_storage.save_input(owner, raw, **kwargs)
            target.status = 'SUCCEEDED'; target._reference_accepted = False
            with self.assertRaisesRegex(ValueError, 'foreign or unaccepted'):
                input_storage.save_input(owner, raw, **kwargs)
            target._reference_accepted = True; target._reference_initialization_id = 'foreign'
            with self.assertRaisesRegex(ValueError, 'foreign or unaccepted'):
                input_storage.save_input(owner, raw, **kwargs)
            target._reference_initialization_id = initialization_id
            same = dict(reference, owner_id=OWNER)
            with self.assertRaisesRegex(ValueError, 'distinct'):
                input_storage.save_input(owner, raw, **dict(kwargs,
                    owner_references={path: same}))
            node = input_v3._node_at(target.input_payload, path)
            original = deepcopy(node)
            node.clear(); node['owner_reference'] = path
            target.input_manifest_digest = digest(target.input_payload)
            chained = dict(reference, manifest_digest=target.input_manifest_digest)
            with self.assertRaisesRegex(ValueError, 'physical one-hop'):
                input_storage.save_input(owner, raw, **dict(kwargs,
                    owner_references={path: chained}))
            node.clear(); node.update(original)

    def test_initialization_profile_reference_requires_same_initialization(self):
        initialization_id = 'df0386c9-35fe-44ce-9447-c86940f35637'
        target_raw = {'profile': {'delivery': {'site_code': 'PURE'}}, 'opening': {}}
        target = SimpleNamespace(pk=initialization_id, input_digest=digest(target_raw),
            _reference_initialization_id=initialization_id, _reference_accepted=True)
        target._reference_identity = dict(database_name='pure_v3', database_oid=37,
            source_digest=SOURCE, owner_kind='initialization', owner_id=initialization_id)
        target_images = MemoryImages()
        target.input_payload = input_storage.save_input(target, target_raw, version=3,
            image_writer=target_images.write, table_selector=table,
            identity_resolver=lambda value: value._reference_identity)
        target.input_manifest_digest = digest(target.input_payload)
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(target_raw),
            _reference_initialization_id=initialization_id)
        path = 'input/profile'
        reference = dict(kind='INITIALIZATION', owner_id=initialization_id, path=path,
            manifest_digest=target.input_manifest_digest, content_digest=target.input_digest)
        with patch('mta.runtime.opening_storage.load_image', side_effect=target_images.read):
            manifest = input_storage.save_input(owner, target_raw, version=3,
                owner_references={path: reference}, owner_resolver=lambda current, body: target,
                image_writer=MemoryImages().write, table_selector=table,
                identity_resolver=run_identity)
        self.assertEqual(dict(manifest['tree']['object'])['profile'],
                         {'owner_reference': 'input/profile'})
        target._reference_initialization_id = 'foreign'
        with patch('mta.runtime.opening_storage.load_image', side_effect=target_images.read), \
                self.assertRaisesRegex(ValueError, 'foreign or unaccepted'):
            input_storage.save_input(owner, target_raw, version=3,
                owner_references={path: reference}, owner_resolver=lambda current, body: target,
                image_writer=MemoryImages().write, table_selector=table,
                identity_resolver=run_identity)

    def test_initialization_opening_reference_allows_only_m2_local_aliases(self):
        initialization_id = 'df0386c9-35fe-44ce-9447-c86940f35637'
        settings = [{'Parameter': 'NMSActive', 'Value': '1'}]
        sku = [{'SKUCode': 'A', 'Description': 'Alpha'}]
        site = [{'WhCode': 'W', 'Description': 'Warehouse'}]
        target_raw = {'profile': {'delivery': {'site_code': 'PURE'}}, 'opening': {'state': {
            'importer_settings': deepcopy(settings),
            'controls': {'importer_settings': deepcopy(settings)},
            'importer': {'SKUDescriptionTbl': deepcopy(sku),
                         'SiteDescriptionTbl': deepcopy(site)},
            'btr': {'SKUDescriptionTbl': deepcopy(sku),
                    'SiteDescriptionTbl': deepcopy(site)},
            'dbm': {'SKUDescriptionTbl': deepcopy(sku),
                    'SiteDescriptionTbl': deepcopy(site)},
        }}}
        target = SimpleNamespace(pk=initialization_id, input_digest=digest(target_raw),
            _reference_initialization_id=initialization_id, _reference_accepted=True)
        target._reference_identity = dict(database_name='pure_v3', database_oid=37,
            source_digest=SOURCE, owner_kind='initialization', owner_id=initialization_id)
        target_images = MemoryImages()
        target.input_payload = input_storage.save_input(target, target_raw, version=3,
            aliases=input_v3.opening_aliases(target_raw), image_writer=target_images.write,
            table_selector=table, identity_resolver=lambda value: value._reference_identity)
        target.input_manifest_digest = digest(target.input_payload)
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(target_raw),
            _reference_initialization_id=initialization_id)
        path = 'input/opening'
        reference = dict(kind='INITIALIZATION', owner_id=initialization_id, path=path,
            manifest_digest=target.input_manifest_digest, content_digest=target.input_digest)
        owner_images = MemoryImages()
        resolver = lambda current, body: target
        with patch('mta.runtime.opening_storage.load_image', side_effect=target_images.read):
            owner.input_payload = input_storage.save_input(owner, target_raw, version=3,
                owner_references={path: reference}, owner_resolver=resolver,
                image_writer=owner_images.write, table_selector=table,
                identity_resolver=run_identity)
            owner.input_manifest_digest = digest(owner.input_payload)
            self.assertFalse(any(name.startswith(path) for name in owner_images.writes))
            self.assertEqual(input_storage.read_input(owner, image_reader=owner_images.read,
                identity_resolver=run_identity, owner_resolver=resolver), target_raw)
            self.assertEqual(input_storage.audit_references(owner,
                identity_resolver=run_identity, owner_resolver=resolver), {path: reference})

        original = deepcopy(target.input_payload)
        cases = []
        cyclic = deepcopy(original)
        canonical = 'input/opening/state/importer_settings'
        source = 'input/opening/state/controls/importer_settings'
        cyclic['aliases'][canonical] = source
        input_v3._node_at(cyclic, canonical).clear()
        input_v3._node_at(cyclic, canonical)['reference'] = source
        cases.append(('cycle', cyclic))
        chained = deepcopy(original)
        chained_target = 'input/opening/state/importer/SKUDescriptionTbl'
        chained['aliases'][canonical] = chained_target
        input_v3._node_at(chained, canonical).clear()
        input_v3._node_at(chained, canonical)['reference'] = chained_target
        cases.append(('chain', chained))
        external = deepcopy(original)
        input_v3._node_at(external, source).clear()
        input_v3._node_at(external, source)['owner_reference'] = source
        external['aliases'].pop(source)
        cases.append(('external', external))
        for name, manifest in cases:
            with self.subTest(name=name):
                target.input_payload = manifest
                target.input_manifest_digest = digest(manifest)
                changed = dict(reference, manifest_digest=target.input_manifest_digest)
                with patch('mta.runtime.opening_storage.load_image', side_effect=target_images.read), \
                        self.assertRaisesRegex(ValueError, 'physical one-hop'):
                    input_storage.save_input(owner, target_raw, version=3,
                        owner_references={path: changed}, owner_resolver=resolver,
                        image_writer=MemoryImages().write, table_selector=table,
                        identity_resolver=run_identity)
        target.input_payload = original
        target.input_manifest_digest = digest(original)

    def test_third_day_derived_master_uses_parent_image_and_earlier_accepted_cut(self):
        parent_id = '6f2e9e47-2c35-42c8-a1f1-70eb937f1fd3'
        initialization_id = 'df0386c9-35fe-44ce-9447-c86940f35637'
        revision_id = '36a44cc4-07de-4a45-aef7-52c9d6d462a5'
        output_digest = 'b' * 64
        source_rows = [{name: (None if name == 'MOQ' else name + '-value')
                        for name in RAW_COLUMNS}]
        reference = dict(contract=input_v3.MASTER_CONTRACT, run_id=parent_id,
            output_digest=output_digest, initialization_id=initialization_id,
            source_digest=SOURCE, master_revision_id=revision_id)
        raw = {'profile': {'delivery': {'site_code': 'PURE'}},
               'day': {'raw_master': NmsMasterRows(source_rows, reference=reference)}}
        content_identity = dict(database_name='pure_v3', database_oid=37,
            source_digest=SOURCE, initialization_id=initialization_id)
        owner = SimpleNamespace(pk=OWNER, predecessor_id=parent_id,
            _reference_initialization_id=initialization_id,
            production_manifest={'ingestion_preparation': {
                'qualified_master_reuse': True, 'base_revision_id': revision_id,
                'initialization_id': initialization_id}},
            _reference_capture_initialization_id=initialization_id,
            _reference_capture_source_digest=SOURCE, _reference_certified=True)
        owner._reference_identity = run_identity(owner)
        owner.input_digest = input_storage.content_root(raw, content_identity)
        parent = SimpleNamespace(pk=parent_id, status='SUCCEEDED', output_digest=output_digest,
            production_manifest={'images': {input_v3.MASTER_IMAGE: {'image': 'nms'}},
                'ingestion_preparation': {'initialization_id': initialization_id},
                'master_preparation': {'qualified': True, 'master_cut': [7, 3]}},
            _reference_initialization_id=initialization_id,
            _reference_capture_initialization_id=initialization_id,
            _reference_capture_source_digest=SOURCE, _reference_certified=True,
            _reference_accepted_revision_id=revision_id,
            _reference_accepted_revision_cut=[7, 3], _reference_accepted=True,
            _reference_accepted_revision_run_id='5946022f-2b98-45ad-82c3-51eac76424c0')
        parent._reference_identity = run_identity(parent)
        resolver = lambda current, body: parent
        owner_images = MemoryImages()
        with patch('mta.runtime.receipt_integrity.verify_root'), \
                patch('mta.runtime.relational_state.load_image', return_value=source_rows):
            owner.input_payload = input_storage.save_input(owner, raw, version=3,
                content_identity=content_identity, master_resolver=resolver,
                image_writer=owner_images.write, table_selector=table,
                identity_resolver=run_identity)
            owner.input_manifest_digest = digest(owner.input_payload)
            self.assertNotIn('input/day/raw_master/values', owner_images.writes)
            rebuilt = input_storage.read_input(owner, image_reader=owner_images.read,
                identity_resolver=run_identity, master_resolver=resolver)
            self.assertIsInstance(rebuilt['day']['raw_master'], NmsMasterRows)
            self.assertEqual(list(rebuilt['day']['raw_master']), list(raw['day']['raw_master']))
            self.assertEqual(rebuilt['day']['raw_master'].reference, reference)
            self.assertEqual(input_storage.audit_references(owner,
                identity_resolver=run_identity, master_resolver=resolver),
                {input_v3.MASTER_PATH: reference})

        cases = [('wrong-parent', dict(predecessor_id=OWNER)),
                 ('unaccepted', dict(parent_accepted=False)),
                 ('foreign', dict(parent_source='c' * 64)),
                 ('wrong-cut', dict(revision_cut=[7, 2])),
                 ('unqualified', dict(qualified=False)),
                 ('wrong-seed', dict(seed='5946022f-2b98-45ad-82c3-51eac76424c0')),
                 ('wrong-capture', dict(capture='5946022f-2b98-45ad-82c3-51eac76424c0')),
                 ('uncertified', dict(certified=False)),
                 ('wrong-csv', dict(csv='5946022f-2b98-45ad-82c3-51eac76424c0'))]
        for name, change in cases:
            with self.subTest(name=name):
                owner.predecessor_id = change.get('predecessor_id', parent_id)
                owner.production_manifest['ingestion_preparation']['initialization_id'] = change.get(
                    'seed', initialization_id)
                owner._reference_capture_initialization_id = change.get('capture', initialization_id)
                owner._reference_certified = change.get('certified', True)
                owner._reference_csv_initialization_id = change.get('csv')
                parent._reference_accepted = change.get('parent_accepted', True)
                parent._reference_identity = {**run_identity(parent),
                    'source_digest': change.get('parent_source', SOURCE)}
                parent._reference_capture_source_digest = change.get('parent_source', SOURCE)
                parent._reference_accepted_revision_cut = change.get('revision_cut', [7, 3])
                parent.production_manifest['master_preparation']['qualified'] = change.get(
                    'qualified', True)
                with patch('mta.runtime.receipt_integrity.verify_root'), \
                        patch('mta.runtime.relational_state.load_image', return_value=source_rows), \
                        self.assertRaises(ValueError):
                    input_storage.save_input(owner, raw, version=3,
                        content_identity=content_identity, master_resolver=resolver,
                        image_writer=MemoryImages().write, table_selector=table,
                        identity_resolver=run_identity)
        owner.predecessor_id = parent_id
        owner.production_manifest['ingestion_preparation']['initialization_id'] = initialization_id
        owner._reference_capture_initialization_id = initialization_id
        owner._reference_certified = True
        owner._reference_csv_initialization_id = None
        parent.production_manifest['master_preparation']['qualified'] = True

    def test_prepared_content_root_binds_rows_identity_and_refs_without_traversal(self):
        initialization_id = 'df0386c9-35fe-44ce-9447-c86940f35637'
        identity_value = dict(database_name='pure_v3', database_oid=37,
            source_digest=SOURCE, initialization_id=initialization_id)
        reference = dict(kind='RUN', owner_id='6f2e9e47-2c35-42c8-a1f1-70eb937f1fd3',
            path='input/mdm_input/rows/sku/attributes', manifest_digest='b' * 64,
            content_digest='c' * 64)

        class ExplosiveRows(Sequence):
            def __len__(self): return 1000000
            def __getitem__(self, index): raise AssertionError('referenced rows were traversed')
            def __iter__(self): raise AssertionError('referenced rows were traversed')

        raw = {'profile': {'delivery': {'site_code': 'PURE'}},
            'mdm_input': {'rows': {'sku': {'attributes': ExplosiveRows()}}},
            'ordered': [{'value': None}, {'value': 1}]}
        refs = {'input/mdm_input/rows/sku/attributes': reference}
        root = input_storage.content_root(raw, identity_value, owner_references=refs)
        self.assertEqual(root, input_storage.content_root(raw, identity_value,
                                                         owner_references=refs))
        changed = deepcopy({k: v for k, v in raw.items() if k != 'mdm_input'})
        changed['mdm_input'] = raw['mdm_input']
        changed['ordered'] = list(reversed(changed['ordered']))
        self.assertNotEqual(root, input_storage.content_root(changed, identity_value,
                                                            owner_references=refs))
        changed_identity = dict(identity_value, source_digest='d' * 64)
        self.assertNotEqual(root, input_storage.content_root(raw, changed_identity,
                                                            owner_references=refs))
        changed_identity = dict(identity_value,
            initialization_id='5946022f-2b98-45ad-82c3-51eac76424c0')
        self.assertNotEqual(root, input_storage.content_root(raw, changed_identity,
                                                            owner_references=refs))
        changed_ref = dict(reference, content_digest='e' * 64)
        self.assertNotEqual(root, input_storage.content_root(raw, identity_value,
            owner_references={reference['path']: changed_ref}))
        null_changed = {**raw, 'ordered': [{'value': 0}, {'value': 1}]}
        self.assertNotEqual(root, input_storage.content_root(null_changed, identity_value,
                                                            owner_references=refs))

        nms_reference = dict(contract=input_v3.MASTER_CONTRACT,
            run_id='6f2e9e47-2c35-42c8-a1f1-70eb937f1fd3', output_digest='b' * 64,
            initialization_id=initialization_id, source_digest=SOURCE,
            master_revision_id='36a44cc4-07de-4a45-aef7-52c9d6d462a5')
        nms = NmsMasterRows([{name: None for name in RAW_COLUMNS}], reference=nms_reference)
        nms.factory = lambda: (_ for _ in ()).throw(AssertionError('NMS view was traversed'))
        input_storage.content_root({'profile': raw['profile'], 'day': {'raw_master': nms}},
                                   identity_value)

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

    def test_v2_initialization_references_preserve_seals_and_typed_rows(self):
        initialization_id = 'df0386c9-35fe-44ce-9447-c86940f35637'
        raw = {'profile': {'delivery': {'site_code': 'PURE'}},
               'opening': {'rows': [{'value': None}, {'value': 7}, {'value': 7}]}}
        target = SimpleNamespace(pk=initialization_id, input_digest=digest(raw),
            _reference_initialization_id=initialization_id, _reference_accepted=True)
        target._reference_identity = {**identity(target), 'owner_id': initialization_id}
        images = MemoryImages()
        target.input_payload = input_storage.save_input(target, raw,
            image_writer=images.write, table_selector=table)
        target.input_manifest_digest = digest(target.input_payload)
        original = deepcopy(target.input_payload)
        original_images = deepcopy(images.rows)
        owner = SimpleNamespace(pk=OWNER, input_digest=digest(raw),
            _reference_initialization_id=initialization_id)
        refs = {path: dict(kind='INITIALIZATION', owner_id=initialization_id, path=path,
            manifest_digest=target.input_manifest_digest, content_digest=target.input_digest)
            for path in ('input/profile', 'input/opening')}
        own_images = MemoryImages()
        kwargs = dict(owner_resolver=lambda current, body: target, identity_resolver=run_identity)
        with patch('mta.runtime.opening_storage.load_image', side_effect=images.read):
            owner.input_payload = input_storage.save_input(owner, raw, version=3,
                owner_references=refs, image_writer=own_images.write, table_selector=table, **kwargs)
            owner.input_manifest_digest = digest(owner.input_payload)
            self.assertEqual(own_images.writes, [])
            self.assertEqual(input_storage.read_input(owner, image_reader=own_images.read, **kwargs), raw)
            self.assertEqual(input_storage.audit_references(owner, **kwargs), refs)
        self.assertEqual(target.input_payload, original)
        self.assertEqual(target.input_manifest_digest, digest(original))
        self.assertEqual(images.rows, original_images)

        path = 'input/opening'
        def resolve(reference=None):
            return input_v3._resolve_owner(owner, path, reference or refs[path],
                run_identity(owner), kwargs['owner_resolver'])

        for field, foreign in (('database_name', 'foreign'), ('database_oid', 38),
                               ('source_digest', 'b'*64), ('owner_kind', 'run')):
            with self.subTest(identity=field):
                target._reference_identity[field] = foreign
                with self.assertRaises(ValueError): resolve()
                target._reference_identity = {**identity(target), 'owner_id': initialization_id}
        target._reference_initialization_id = 'foreign'
        with self.assertRaisesRegex(ValueError, 'foreign or unaccepted'): resolve()
        target._reference_initialization_id = initialization_id
        for field in ('manifest_digest', 'content_digest'):
            with self.subTest(root=field), self.assertRaises(ValueError):
                resolve({**refs[path], field: 'b'*64})
        for node_kind in ('reference', 'owner_reference', 'batch_reference', 'derived_master'):
            with self.subTest(chain=node_kind):
                target.input_payload = deepcopy(original)
                node = input_v3._node_at(target.input_payload, path)
                node.clear(); node[node_kind] = path
                target.input_manifest_digest = digest(target.input_payload)
                with self.assertRaisesRegex(ValueError, 'physical one-hop'):
                    resolve({**refs[path], 'manifest_digest': target.input_manifest_digest})
        target.input_payload = original
        target.input_manifest_digest = digest(original)
        target.status = 'SUCCEEDED'
        target._reference_identity['owner_kind'] = 'run'
        run_path = 'input/mdm_input/rows/sku/attributes'
        with self.assertRaisesRegex(ValueError, 'manifest/content'):
            input_v3._resolve_owner(owner, run_path,
                {**refs[path], 'kind': 'RUN', 'path': run_path},
                run_identity(owner), kwargs['owner_resolver'])

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
