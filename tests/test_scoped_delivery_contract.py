"""Finite declared artifacts and cross-release read-only resume boundaries."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from uuid import uuid4

from mta.presentation import scoped_artifacts as artifacts
from mta.runtime.scoped_delivery_resume import frozen_request
from mta.serialization import digest


def declaration():
    return dict(schema=artifacts.SCHEMA, purpose='owned-scoped-test', run_id=str(uuid4()),
        phase_id=str(uuid4()), phase_digest='a'*64, input_digest='b'*64,
        input_manifest_digest='c'*64, site_code='SUPPLIED-INSTANCE',
        post_bpr_hook='explicit-test-no-op', input_download=True,
        importer_database='VFTEST_Fresh_Test', physical_files=list(artifacts.PHYSICAL),
        input_tables=list(artifacts.TABLES), archive_clock='business-midnight-Asia-Kolkata',
        authority='Explicit test declaration')


class ScopedDeliveryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(TemporaryDirectory())
        self.root = Path(self.temp) / 'artifact'
        self.path = Path(self.temp) / 'declaration.json'
        self.value = declaration()
        self.raw = json.dumps(self.value).encode()
        self.path.write_bytes(self.raw)
        self.pin = hashlib.sha256(self.raw).hexdigest()

    def test_exact_declaration_and_hash_duplicate_and_missing_dispositions(self):
        self.assertEqual(artifacts.declaration(self.path, self.pin), self.value)
        for key, value in (('input_download', False), ('post_bpr_hook', None),
                           ('site_code', 'GulfOil'), ('input_tables', [])):
            changed = dict(self.value, **{key: value})
            raw = json.dumps(changed).encode()
            self.path.write_bytes(raw)
            with self.subTest(key=key), self.assertRaises(ValueError):
                artifacts.declaration(self.path, hashlib.sha256(raw).hexdigest())
        raw = self.raw[:-1] + b',"input_download":true}'
        self.path.write_bytes(raw)
        with self.assertRaises(ValueError):
            artifacts.declaration(self.path, hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            artifacts.declaration(self.path, self.pin)

    def producer(self):
        phase = NS(pk=self.value['phase_id'], run_id=self.value['run_id'],
            snapshot=NS(state_digest='d'*64), run=NS(business_date=__import__('datetime').date(2026, 10, 24)))
        physical = {name: b'physical\r\n' for name in artifacts.PHYSICAL}
        exports = {self.value['importer_database']+'_'+name+'.CSV': b'NULL,2\r\n'
                   for name in artifacts.TABLES}
        self.enterContext(patch.object(artifacts, '_bind', return_value=phase))
        self.enterContext(patch.object(artifacts, '_root', return_value=self.root))
        self.enterContext(patch.object(artifacts, 'payloads', return_value=(physical, exports, {'exact-owner': 'digest'})))
        return phase

    def prepare(self):
        return artifacts.prepare(self.value['phase_id'], expected_digest=self.value['phase_digest'],
            declaration_file=self.path, declaration_sha256=self.pin)

    def verify(self, receipt, **kwargs):
        return artifacts.verify(self.value['phase_id'], expected_digest=self.value['phase_digest'],
            declaration_file=self.path, declaration_sha256=self.pin,
            receipt_sha256=receipt['receipt_sha256'], **kwargs)

    def test_archive_has_exact_ten_members_idempotence_and_independent_receipt_pin(self):
        self.producer()
        receipt = self.prepare()
        self.assertEqual(len(receipt['members']), 10)
        self.assertIn('24_10_2026_12_00.txt', receipt['members'])
        self.assertEqual(self.prepare(), receipt)
        self.assertEqual(self.verify(receipt), receipt)
        raw = (self.root/'artifact.json').read_bytes()
        changed = json.loads(raw)
        changed['members'] = {}
        (self.root/'artifact.json').write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'independently pinned'):
            self.verify(receipt)

    def test_failed_private_build_is_retained_and_retry_never_overwrites_it(self):
        self.producer()
        with patch('mta.application.operational_input_archive.files.copy_file', side_effect=OSError('late copy failed')):
            with self.assertRaisesRegex(OSError, 'late copy failed'):
                self.prepare()
        self.assertFalse(self.root.exists())
        partials = list(self.root.parent.glob(self.root.name + '.*'))
        self.assertEqual(len(partials), 1)
        old_zip = (partials[0]/'output/InputData.zip').read_bytes()
        self.prepare()
        self.assertEqual((partials[0]/'output/InputData.zip').read_bytes(), old_zip)

    def test_changed_archive_denies_download_and_invalidates_metadata_identity(self):
        self.producer()
        receipt = self.prepare()
        old = self.verify(receipt, verify_bytes=False)['file_identity']
        path = self.root/'download/InputData.zip'
        raw = path.read_bytes()
        path.write_bytes(b'X' + raw[1:])
        new = self.verify(receipt, verify_bytes=False)['file_identity']
        self.assertNotEqual(old, new)
        with self.assertRaisesRegex(ValueError, 'archive bytes differ'):
            self.verify(receipt)

    @unittest.skipUnless(os.name == 'posix', 'Production directory-relative IO requires POSIX')
    def test_download_returns_the_same_verified_handle_and_denies_replacement_before_open(self):
        self.producer()
        receipt = self.prepare()
        view = NS(bpr=NS(sources=NS(acceptance_id=self.value['phase_id'],
            acceptance_digest=self.value['phase_digest'])))
        from mta.runtime import scoped_pick_files
        original_open = scoped_pick_files._open
        target = self.root/'download/InputData.zip'
        expected = target.read_bytes()
        def replace_before_open(*args, **kwargs):
            target.write_bytes(b'X' + expected[1:])
            return original_open(*args, **kwargs)
        with patch.object(scoped_pick_files, '_open', side_effect=replace_before_open):
            with self.assertRaisesRegex(ValueError, 'changed before opening'):
                artifacts.open_archive(view, self.path, self.pin, receipt['receipt_sha256'])
        target.write_bytes(expected)
        with artifacts.open_archive(view, self.path, self.pin, receipt['receipt_sha256']) as stream:
            replacement = target.with_name('replacement.zip')
            replacement.write_bytes(b'replacement')
            os.replace(replacement, target)
            self.assertEqual(stream.read(), expected)

    def test_frozen_request_changes_only_through_exact_previous_release_and_phase_recipe(self):
        release = {'source_commit': 'old', 'manifest_sha256': 'pinned'}
        recipe = 'same-calculation-recipe'
        frozen = dict(schema='v2', scope='UptoBPR', command_key='same', runtime_reports={'exact': []},
            compatibility_digest=digest(dict(release=release, phase_recipe=recipe)))
        current = dict(frozen, compatibility_digest='new-release-identity')
        self.assertEqual(frozen_request(frozen, current, release, recipe), frozen)
        for field, value in (('command_key', 'foreign'), ('runtime_reports', {'changed': []})):
            with self.subTest(field=field), self.assertRaises(ValueError):
                frozen_request(frozen, dict(current, **{field: value}), release, recipe)
        with self.assertRaises(ValueError):
            frozen_request(frozen, current, release, 'changed-phase-recipe')
        with self.assertRaises(ValueError):
            frozen_request(frozen, current, dict(release, source_commit='wrong'), recipe)
