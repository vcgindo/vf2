import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from release.installed_application import verify_export


class InstalledSourceTests(unittest.TestCase):
    def test_exact_source_and_source_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {'manage.py': b'entry', 'mta/config.json': b'{}',
                     'release/service.py': b'service', 'vectorflow/settings.py': b'settings'}
            for name, raw in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            value = dict(schema='vectorflow-release-source-v1', default_data_import=False,
                         source_commit='a' * 40,
                         files={n: hashlib.sha256(v).hexdigest() for n, v in files.items()})
            manifest = root / 'release-source.json'
            manifest.write_text(json.dumps(value))
            self.assertEqual(verify_export(root), 'a' * 40)
            changed = root / 'mta/config.json'
            changed.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                verify_export(root)
            changed.write_bytes(files['mta/config.json'])
            extra = root / 'mta/unknown.py'
            extra.write_bytes(b'unknown')
            with self.assertRaisesRegex(ValueError, 'roster differs'):
                verify_export(root)
            extra.unlink()
            changed.unlink()
            with self.assertRaisesRegex(ValueError, 'roster differs'):
                verify_export(root)

    def test_missing_or_invalid_manifest_is_not_an_empty_install(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                verify_export(directory)
            path = Path(directory) / 'release-source.json'
            path.write_text(json.dumps(dict(schema='other', default_data_import=True)))
            with self.assertRaisesRegex(ValueError, 'manifest is invalid'):
                verify_export(directory)
