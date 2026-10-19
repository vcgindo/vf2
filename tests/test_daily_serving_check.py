"""Image-owned bootstrap loading for the read-only serving verifier.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from release.daily_serving_check import configure_image


class ServingCheckBootstrapTests(unittest.TestCase):
    def test_packaged_bootstrap_loads_from_its_real_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = root / 'release.json'
            identity.write_text(json.dumps(dict(source_commit='a'*40, native_sha256='b'*64, source_sha256='c'*64)))
            shutil.copyfile(Path(__file__).resolve().parents[1]/'release/image_entrypoint.py', root/'image_entrypoint.py')
            with patch.dict(os.environ, {}, clear=True):
                configure_image(identity)
                self.assertEqual(os.environ['VF_NATIVE_RELEASE_COMMIT'], 'a'*40)
                self.assertEqual(os.environ['VF_NATIVE_RELEASE_SHA256'], 'b'*64)
                os.environ['VF_NATIVE_RELEASE_SHA256'] = 'd'*64
                before = dict(os.environ)
                with self.assertRaisesRegex(ValueError, 'differs'):
                    configure_image(identity)
                self.assertEqual(dict(os.environ), before)

    def test_non_image_check_does_not_load_an_operator_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('release.daily_serving_check.runpy.run_path') as loader:
                configure_image(Path(directory)/'absent.json')
                loader.assert_not_called()
