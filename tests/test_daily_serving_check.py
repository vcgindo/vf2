"""Image-owned bootstrap loading for the read-only serving verifier.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from release.daily_serving_check import configure_image


class ServingCheckBootstrapTests(unittest.TestCase):
    def test_running_service_check_never_repeats_exclusive_admission(self):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'serving-unit-only')
        import django
        django.setup()
        from django.test import override_settings
        from release.daily_serving_check import check
        run = SimpleNamespace(pk='run', output_digest='output')
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"ready":true,"admission_digest":"identity"}'
        with override_settings(VF_MTA_SELECTION_FILE='/selected.json'), \
                patch('release.daily_serving_check.configure_image'), \
                patch('mta.presentation.admission.admit', side_effect=AssertionError('exclusive audit')), \
                patch('mta.presentation.admission.binding', return_value=(run, 'identity')) as binding, \
                patch('mta.presentation.native_selection.read', return_value={'selection_digest':'selected'}), \
                patch('urllib.request.urlopen', return_value=Response()):
            self.assertTrue(check('run', 'output')['ready'])
            self.assertEqual(binding.call_count, 2)
            binding.side_effect = [(run, 'identity'), (run, 'changed')]
            with self.assertRaisesRegex(ValueError, 'changed during'):
                check('run', 'output')

    def test_admission_only_checks_selected_identity_before_service_recovery(self):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'serving-unit-only')
        import django
        django.setup()
        from django.test import override_settings
        from release.daily_serving_check import check
        with override_settings(VF_MTA_SELECTION_FILE='/selected.json'), \
                patch('release.daily_serving_check.configure_image'), \
                patch('mta.presentation.admission.admit', return_value={'run_id':'latest','output_digest':'digest'}), \
                patch('mta.presentation.native_selection.read', return_value={'selection_digest':'selection'}) as read, \
                patch('urllib.request.urlopen') as http:
            self.assertTrue(check('latest','digest',admission_only=True)['selected'])
            with self.assertRaisesRegex(ValueError, 'another run'):
                check('older','old-digest',admission_only=True)
            self.assertEqual(read.call_count,1)
            http.assert_not_called()

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
