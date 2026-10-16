"""A pinned export ancestry cannot admit unrelated production differences."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest import TestCase, mock

from release import sealed_export as export
from mta.mdm import native_report_compatibility as c
from mta.serialization import digest


class SealedExportTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        special = export.INSTALLATION_FILES | {export.VERIFIER}
        self.original = {n: (n + '\noriginal\n').encode() for n in special}
        self.original.update({'mta/keep_%03d.py' % n: b'unchanged\n' for n in range(718)})
        self.omitted = {export.OMITTED_NEW_TEST: b'omitted test\n'}
        self.omitted.update({'mta/test_omitted_%03d.py' % n: b'validation\n' for n in range(186)})
        self.original.update(self.omitted)
        self.reviewed = {n: raw for n, raw in self.original.items() if n not in self.omitted}
        for n in export.INSTALLATION_FILES:
            self.reviewed[n] += b'fresh installation\n'
        self.current = dict(self.reviewed)
        for n in (export.VERIFIER, export.LAYOUT_VERIFIER):
            self.current[n] += b'bounded amendment\n'
        for n, raw in self.current.items():
            f = self.root / n
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(raw)
        self.original_files = {n: c._sha(raw) for n, raw in self.original.items()}
        self.files = {n: c._sha(raw) for n, raw in self.current.items()}
        self.identity = dict(adapter_digest='a'*64, closing_projection_version=c.VERSION,
                             source_manifest_digest=digest(self.files))
        self.old_identity = dict(self.identity, adapter_digest='b'*64,
                                 source_manifest_digest=digest(self.original_files))
        self.logistics = json.dumps(dict(current_files=self.original_files,
            current_identity=self.old_identity, inverse={export.OMITTED_NEW_TEST:
                c.inverse_delta(b'', self.omitted[export.OMITTED_NEW_TEST])})).encode()
        reviewed_files = {n: c._sha(raw) for n, raw in self.reviewed.items()}
        omitted_files = {n: c._sha(raw) for n, raw in self.omitted.items()}
        self.value = dict(schema=export.SCHEMA, reviewed_commit=export.REVIEWED_COMMIT,
            reviewed_files=reviewed_files, omitted_files=omitted_files,
            installation_inverse={n: c.inverse_delta(self.original[n], self.reviewed[n])
                                  for n in export.INSTALLATION_FILES},
            descendant_inverse={n: c.inverse_delta(self.reviewed[n], self.current[n])
                                for n in (export.VERIFIER, export.LAYOUT_VERIFIER)},
            current_files=self.files, current_identity=self.identity)
        p = mock.patch.multiple(export, LOGISTICS_SHA256=c._sha(self.logistics),
            REVIEWED_DIGEST=digest(reviewed_files), OMITTED_DIGEST=digest(omitted_files))
        p.start()
        self.addCleanup(p.stop)

    def validate(self, value=None, **kwargs):
        raw = json.dumps(self.value if value is None else value).encode()
        args = dict(raw=raw, pin=c._sha(raw), logistics_raw=self.logistics,
                    root=self.root, files=self.files, identity=self.identity)
        args.update(kwargs)
        return export.validate(**args)

    def test_exact_reviewed_export_reconstructs_original_without_restoring_test_files(self):
        files, overrides, identity = self.validate()
        self.assertEqual(files, self.original_files)
        self.assertEqual(identity, self.old_identity)
        self.assertEqual(set(overrides), export.INSTALLATION_FILES | {export.VERIFIER, export.OMITTED_NEW_TEST})
        for n, raw in overrides.items():
            self.assertEqual(raw, self.original[n])
        self.assertFalse((self.root / export.OMITTED_NEW_TEST).exists())

    def test_wrong_pin_lineage_identity_and_forged_manifest_are_denied(self):
        for kwargs in (dict(pin='0'*64), dict(logistics_raw=b'{}'),
                       dict(identity={**self.identity, 'adapter_digest':'0'*64}),
                       dict(files={**self.files, export.VERIFIER:'0'*64})):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.validate(**kwargs)

    def test_actual_added_missing_and_modified_production_files_are_denied(self):
        added = self.root/'mta/extra.py'
        added.write_bytes(b'unapproved\n')
        with self.assertRaises(ValueError): self.validate()
        added.unlink()
        target = self.root/'mta/keep_000.py'
        target.unlink()
        with self.assertRaises(ValueError): self.validate()
        target.write_bytes(b'changed\n')
        with self.assertRaises(ValueError): self.validate()

    def test_repin_cannot_alter_fixed_rosters_lineage_or_change_boundary(self):
        mutations = (
            lambda v: v.update(reviewed_commit='0'*40),
            lambda v: v.update(schema='generic-allowlist'),
            lambda v: v['omitted_files'].pop(export.OMITTED_NEW_TEST),
            lambda v: v['omitted_files'].update({export.OMITTED_NEW_TEST:'0'*64}),
            lambda v: v['reviewed_files'].update({'mta/keep_000.py':'0'*64}),
            lambda v: v['descendant_inverse'].update({'mta/keep_000.py':[]}),
            lambda v: v['installation_inverse'].pop(export.LAYOUT_VERIFIER),
            lambda v: v['installation_inverse'].update({export.VERIFIER:[]}),
            lambda v: v['descendant_inverse'].update({export.VERIFIER:[]}),
            lambda v: v.update(untrusted_byte_map={export.VERIFIER:'anything'}),
        )
        for mutate in mutations:
            value = deepcopy(self.value)
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.validate(value)

    def test_an_unrelated_change_still_denies_when_current_metadata_is_repinned(self):
        name = 'mta/keep_000.py'
        raw = b'unapproved production change\n'
        (self.root/name).write_bytes(raw)
        files = {**self.files, name:c._sha(raw)}
        identity = {**self.identity, 'source_manifest_digest':digest(files)}
        value = deepcopy(self.value)
        value.update(current_files=files, current_identity=identity)
        value['descendant_inverse'][name] = c.inverse_delta(self.reviewed[name], raw)
        with self.assertRaisesRegex(ValueError, 'changed production file boundary'):
            self.validate(value, files=files, identity=identity)

    def test_opt_in_requires_immutable_evidence_before_reading_it(self):
        with mock.patch.dict('os.environ', {export.PIN_ENV:'a'*64}), \
             mock.patch.object(c, '_readonly', side_effect=ValueError('writable')) as readonly:
            with self.assertRaisesRegex(ValueError, 'writable'):
                export.retained_source(self.root, self.files, self.identity, self.logistics)
            readonly.assert_called_once_with(export.DECLARATION)

    def test_default_install_has_no_sealed_export_opt_in(self):
        with mock.patch.dict('os.environ', {}, clear=True):
            self.assertEqual(export.retained_source(self.root, self.files, self.identity, b''),
                             (self.files, None, self.identity))
