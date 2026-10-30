"""In-memory capture-reference proof; no database connection is exercised."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from tests.test_input_storage_v3 import MemoryImages, table, SOURCE, run_identity
from mta.runtime import input_storage, input_v3, accepted_reference_write as accepted
from mta.runtime.capture_preparation import seed
from mta.runtime.ingestion_admission import CertifiedReadiness
from mta.runtime.ingestion_context import RevisionCut
from mta.runtime.opening_scope import opening_scope, certify_opening
from mta.application.persistent_master import NmsMasterRows
from mta.application.r1_importer_master import RAW_COLUMNS
from mta.serialization import digest


class AcceptedReferenceWriteTests(TestCase):
    def fixture(self):
        init_id, parent_id, run_id, revision_id, attempt_id = [str(uuid4()) for _ in range(5)]
        source = SimpleNamespace(pk=4, digest=SOURCE)
        profile = {'delivery': {'site_code': 'fixture'}, 'typed': [None, 'fixture']}
        duplicate = {'SKUCode': 'fixture', 'quantity': None, 'flag': False, 'number': 1.5}
        raw_init = {'profile': profile, 'opening': {'state': {'rows': [duplicate, duplicate]}}}
        initialized = SimpleNamespace(pk=init_id, source_id=4, source=source,
            input_digest=digest(raw_init), receipt_digest='receipt', configuration_digest=digest(profile),
            recipe_sha256='recipe', implementation_digest='implementation', input_sha256='file',
            _reference_initialization_id=init_id, _reference_accepted=True)
        initialized._reference_identity = dict(run_identity(initialized), owner_kind='initialization')
        init_images = MemoryImages()
        initialized.input_payload = input_storage.save_input(initialized, raw_init, version=2,
            image_writer=init_images.write, table_selector=table)
        initialized.input_manifest_digest = digest(initialized.input_payload)
        parent_raw = {'profile': profile, 'mdm_input': {'rows': {'sku': {'attributes': [duplicate, duplicate]}}}}
        parent = SimpleNamespace(pk=parent_id, status='SUCCEEDED', input_digest=digest(parent_raw),
            output_digest='c' * 64, _reference_identity=None, _reference_initialization_id=init_id,
            _reference_accepted=True, _reference_accepted_revision_id=revision_id,
            _reference_accepted_revision_cut=[2, 3], _reference_capture_initialization_id=init_id,
            _reference_capture_source_digest=SOURCE, _reference_certified=True)
        parent._reference_identity = run_identity(parent)
        parent_images = MemoryImages()
        parent.input_payload = input_storage.save_input(parent, parent_raw, version=3,
            identity_resolver=run_identity, image_writer=parent_images.write, table_selector=table)
        parent.input_manifest_digest = digest(parent.input_payload)
        parent.production_manifest = {'master_preparation': {'qualified': True, 'master_cut': [2, 3]},
            'ingestion_preparation': {'initialization_id': init_id},
            'images': {input_v3.MASTER_IMAGE: {'image': input_v3.MASTER_IMAGE, 'count': 2}}}
        readiness = CertifiedReadiness(init_id, SOURCE, 'certificate', revision_id,
            initialized.configuration_digest, RevisionCut(2, 3, 4, 5, 6))
        run = SimpleNamespace(pk=run_id, status='RUNNING', kind='DAILY_CHAIN', evidence_mode='production',
            predecessor_id=parent_id, business_date=date(2026, 4, 9),
            production_manifest={'ingestion_preparation': seed(readiness, reused=True)},
            mdm_input_capture=SimpleNamespace(source_id=4, source=source),
            _reference_initialization_id=init_id, _reference_capture_initialization_id=init_id,
            _reference_capture_source_digest=SOURCE, _reference_certified=True,
            _reference_csv_initialization_id=init_id)
        run._reference_identity = run_identity(run)
        rows = [dict(duplicate), dict(duplicate)]
        manifest = {'feeds': [{'filename': 'DailyDataRaw.csv', 'count': 2, 'digest': digest(rows)}]}
        attempt = SimpleNamespace(pk=attempt_id, attempt_id=attempt_id, initialization_id=init_id,
            run_id=run_id, status='RUNNING', business_date=run.business_date, accepted_facts=manifest)
        batch = {'input/day/raw_daily': dict(attempt_id=attempt_id, filename='DailyDataRaw.csv',
            manifest_digest=digest(manifest), population_digest=digest(rows), count=2)}
        def ref(target, kind, path):
            return dict(kind=kind, owner_id=target.pk, path=path,
                manifest_digest=target.input_manifest_digest, content_digest=target.input_digest)
        owners = {path: ref(initialized, 'INITIALIZATION', path) for path in ('input/profile', 'input/opening')}
        path = 'input/mdm_input/rows/sku/attributes'
        owners[path] = ref(parent, 'RUN', path)
        master_reference = dict(contract=input_v3.MASTER_CONTRACT, run_id=parent_id,
            output_digest=parent.output_digest, initialization_id=init_id, source_digest=SOURCE,
            master_revision_id=revision_id)
        source_rows = [{**{name: None for name in RAW_COLUMNS}, 'SKUCode': 'fixture'}] * 2
        master = NmsMasterRows(source_rows, reference=master_reference)
        raw = dict(profile=deepcopy(profile), opening=deepcopy(raw_init['opening']),
            mdm_input=deepcopy(parent_raw['mdm_input']), day={'raw_daily': deepcopy(rows),
            'raw_master': master}, new_rows=[duplicate, duplicate, {'SKUCode': 'other', 'quantity': 0}])
        content_identity = dict(database_name='pure_v3', database_oid=37, source_digest=SOURCE,
            initialization_id=init_id)
        run.input_digest = input_storage.content_root(raw, content_identity,
            owner_references=owners, batch_references=batch)
        return SimpleNamespace(**locals())

    def metadata(self, f):
        stack = ExitStack()
        stack.enter_context(patch.object(accepted, 'connection', SimpleNamespace(
            in_atomic_block=True, atomic_blocks=[object()])))
        stack.enter_context(patch('mta.runtime.batch_storage._live_identity', return_value=dict(
            database_name='pure_v3', database_oid=37, source_digest=SOURCE)))
        stack.enter_context(patch('mta.runtime.receipt_integrity.verify_root'))
        return stack

    def issue(self, f):
        certify_opening(f.initialized, (str(f.initialized.pk), SOURCE,
            f.initialized.configuration_digest, 'certificate', f.revision_id, 2, 3, {}))
        return accepted._capture(f.run, f.raw, f.initialized, f.readiness, f.attempt, f.parent,
            owner_references=f.owners, batch_references=f.batch, content_identity=f.content_identity)

    def write(self, f, images):
        return input_storage.save_input(f.run, f.raw, version=3, image_writer=images.write,
            table_selector=table, identity_resolver=run_identity, owner_references=f.owners,
            owner_resolver=lambda run, ref: f.initialized if ref['kind'] == 'INITIALIZATION' else f.parent,
            batch_references=f.batch, batch_resolver=lambda run, attempt: f.attempt,
            master_resolver=lambda run, ref: f.parent, content_identity=f.content_identity)

    def test_manifest_and_new_physical_images_equal_strict_writer_without_reference_reads(self):
        f = self.fixture()
        strict_images, accepted_images = MemoryImages(), MemoryImages()
        with self.metadata(f), patch('mta.runtime.opening_storage.load_image', side_effect=f.init_images.read), \
                patch('mta.runtime.relational_state.load_image', side_effect=lambda owner, image:
                    f.source_rows if image['image'] == input_v3.MASTER_IMAGE else f.parent_images.read(owner, image)), \
                patch('mta.runtime.batch_storage.iter_population', return_value=iter(f.rows)):
            expected = self.write(f, strict_images)
        with opening_scope(), self.metadata(f), self.issue(f), ExitStack() as stack:
            for path in ('mta.runtime.input_storage.read_input', 'mta.runtime.opening_storage.load_image',
                         'mta.runtime.relational_state.load_image', 'mta.runtime.batch_storage.iter_population',
                         'mta.runtime.input_v3._typed_equal', 'mta.runtime.input_v3.content_root'):
                stack.enter_context(patch(path, side_effect=AssertionError(path)))
            actual = self.write(f, accepted_images)
        self.assertEqual(actual, expected)
        self.assertEqual(digest(actual), digest(expected))
        self.assertEqual(accepted_images.rows, strict_images.rows)
        self.assertEqual(accepted_images.writes, strict_images.writes)

    def test_foreign_graph_reference_transaction_and_stale_seal_denied(self):
        for change in ('graph', 'reference', 'transaction', 'seal', 'root', 'run', 'database'):
            f = self.fixture()
            with self.subTest(change=change), opening_scope(), self.metadata(f), self.issue(f):
                if change == 'graph':
                    f.raw['opening'] = deepcopy(f.raw['opening'])
                elif change == 'reference':
                    f.owners['input/profile']['content_digest'] = 'd' * 64
                elif change == 'transaction':
                    accepted.connection.atomic_blocks[:] = [object()]
                elif change == 'seal':
                    f.initialized.input_manifest_digest = 'd' * 64
                elif change == 'root':
                    f.run.input_digest = 'd' * 64
                elif change == 'run':
                    f.run = SimpleNamespace(**vars(f.run))
                else:
                    f.content_identity['database_oid'] += 1
                with self.assertRaises(ValueError):
                    self.write(f, MemoryImages())

    def test_capability_requires_handle_and_real_readiness(self):
        f = self.fixture()
        with self.metadata(f), self.assertRaisesRegex(ValueError, 'absent or stale'):
            with accepted._capture(f.run, f.raw, f.initialized, f.readiness, f.attempt, f.parent,
                    owner_references=f.owners, batch_references=f.batch, content_identity=f.content_identity):
                pass
        with opening_scope(), self.metadata(f):
            certify_opening(f.initialized, (str(f.initialized.pk), SOURCE,
                f.initialized.configuration_digest, 'certificate', f.revision_id, 2, 3, {}))
            with self.assertRaisesRegex(ValueError, 'ownership differs'):
                with accepted._capture(f.run, f.raw, f.initialized, object(), f.attempt, f.parent,
                        owner_references=f.owners, batch_references=f.batch, content_identity=f.content_identity):
                    pass

    def test_admitted_metadata_failure_still_rejects_before_image_write(self):
        f = self.fixture()
        with opening_scope(), self.metadata(f), self.issue(f):
            f.parent.input_manifest_digest = 'd' * 64
            images = MemoryImages()
            with self.assertRaisesRegex(ValueError, 'manifest/content differs'):
                self.write(f, images)
            self.assertEqual(images.writes, [])

    def test_capability_expires_and_unadmitted_writer_still_compares_cells(self):
        f = self.fixture()
        with opening_scope(), self.metadata(f):
            with self.issue(f):
                self.assertIsNotNone(accepted._for_write(f.run, f.raw, run_identity(f.run),
                    f.owners, f.batch, f.content_identity))
            self.assertIsNone(accepted._for_write(f.run, f.raw, run_identity(f.run),
                f.owners, f.batch, f.content_identity))
            f.raw['day']['raw_daily'][0]['quantity'] = 0
            with patch('mta.runtime.batch_storage.iter_population', return_value=iter(f.rows)), \
                    self.assertRaisesRegex(ValueError, 'batch population differs'):
                self.write(f, MemoryImages())
