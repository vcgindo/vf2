import hashlib
import json
import tempfile
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from mta.mdm import native_report_compatibility as compatibility
from mta.serialization import digest


class NativeReportCompatibilityTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.root, self.before = base / 'current', base / 'before'
        (self.root / 'mta').mkdir(parents=True)
        (self.before / 'mta').mkdir(parents=True)
        self.prior_bytes = b'alpha\r\nbeta\r\n'
        self.current_bytes = b'alpha\r\nBETA\r\n'
        (self.before / 'mta/a.py').write_bytes(self.prior_bytes)
        (self.root / 'mta/a.py').write_bytes(self.current_bytes)
        (self.root / 'mta/b.py').write_bytes(b'new\n')
        self.prior_files = {'mta/a.py': hashlib.sha256(self.prior_bytes).hexdigest()}
        self.prior_raw = (json.dumps(self.prior_files, sort_keys=True,
                                     separators=(',', ':')) + '\n').encode()
        self.implementation = digest({'a.py': self.prior_files['mta/a.py']})
        self.seal_receipt = dict(source_digest=compatibility.SOURCE,
            initialization_id=compatibility.INITIALIZATION,
            adapter_digest=compatibility.SEALED_ADAPTER,
            source_manifest_digest=compatibility.SEALED_MANIFEST,
            closing_projection_version=compatibility.VERSION)
        self.seal_digest = digest(self.seal_receipt)
        prior_declaration = dict(current_files=self.prior_files,
                                 current_adapter_digest='f' * 64)
        self.prior_declaration_raw = (json.dumps(prior_declaration, sort_keys=True,
            separators=(',', ':')) + '\n').encode()
        patches = {'CHANGED_FILES': {'mta/a.py', 'mta/b.py'}, 'NEW_FILES': {'mta/b.py'},
            'PRIOR_FILES_SHA256': hashlib.sha256(self.prior_raw).hexdigest(),
            'PRIOR_FILES_DIGEST': digest(self.prior_files), 'PRIOR_FILE_COUNT': 1,
            'PRIOR_DECLARATION_SHA256': hashlib.sha256(self.prior_declaration_raw).hexdigest(),
            'IMPLEMENTATION': self.implementation, 'SEAL': self.seal_digest}
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in patches.items():
            self.stack.enter_context(mock.patch.object(compatibility, name, value))
        self.declaration = compatibility.build_declaration(root=self.root,
            before_root=self.before, prior_raw=self.prior_raw,
            implementation_paths=('a.py',), current_adapter_digest='0' * 64)
        self.raw = self._serialize(self.declaration)
        self.source = SimpleNamespace(pk=1, digest=compatibility.SOURCE,
                                      implementation_digest=self.implementation)
        self.initialization = SimpleNamespace(pk=compatibility.INITIALIZATION, source_id=1,
            implementation_digest=self.implementation,
            receipt_digest=compatibility.INITIALIZATION_RECEIPT)
        self.seal = SimpleNamespace(source_id=1, digest=self.seal_digest,
                                    receipt=self.seal_receipt)

    @staticmethod
    def _serialize(value):
        return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()

    def _validate(self, **changes):
        values = dict(source=self.source, initialization=self.initialization, seal=self.seal,
            identity=self.declaration['current_identity'], database=compatibility.DATABASE,
            raw=self.raw, pin=hashlib.sha256(self.raw).hexdigest(), root=self.root,
            files=self.declaration['current_files'], prior_raw=self.prior_raw,
            prior_declaration_raw=self.prior_declaration_raw,
            current_implementation=self.declaration['implementation']['current_digest'],
            implementation_paths=('a.py',))
        values.update(changes)
        return compatibility._validate(**values)

    def test_exact_fixture_reconstructs_prior_identity(self):
        result = self._validate()
        self.assertEqual(result['prior_files'], self.prior_files)
        self.assertEqual(result['retained_implementation_digest'], self.implementation)

    def test_wrong_pin_and_database_are_denied(self):
        with self.assertRaisesRegex(ValueError, 'not pinned'):
            self._validate(pin='0' * 64)
        with self.assertRaisesRegex(ValueError, 'database/source'):
            self._validate(database=('database_004', compatibility.DATABASE[1]))

    def test_current_roster_change_and_extra_file_are_denied(self):
        changed = dict(self.declaration['current_files'])
        changed['mta/a.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'running source identity differs'):
            self._validate(files=changed)
        (self.root / 'mta/extra.py').write_bytes(b'extra\n')
        with self.assertRaisesRegex(ValueError, 'changed file boundary differs'):
            compatibility.build_declaration(root=self.root, before_root=self.before,
                prior_raw=self.prior_raw, implementation_paths=('a.py',),
                current_adapter_digest='0' * 64)

    def test_current_bytes_and_inverse_tampering_are_denied(self):
        (self.root / 'mta/a.py').write_bytes(b'alpha\r\nTAMPER\r\n')
        with self.assertRaisesRegex(ValueError, 'current bytes differ'):
            self._validate()
        (self.root / 'mta/a.py').write_bytes(self.current_bytes)
        declaration = deepcopy(self.declaration)
        declaration['patches']['mta/a.py']['inverse'][0]['prior'] = 'dGFtcGVy'
        raw = self._serialize(declaration)
        with self.assertRaisesRegex(ValueError, 'inverse proof differs'):
            self._validate(raw=raw, pin=hashlib.sha256(raw).hexdigest())

    def test_inverse_delta_preserves_mixed_newlines(self):
        before = b'one\r\ntwo\r\nthree\n'
        after = b'zero\none\r\nTWO\r\nthree\n'
        edits = compatibility.inverse_delta(before, after)
        self.assertEqual(compatibility.apply_inverse(after, edits), before)
