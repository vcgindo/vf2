import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from release import optional_initialize


class OptionalInitializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('VF_SECRET_KEY', 'non-serving-bootstrap-tests')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        import django
        django.setup()

    def test_changed_input_cannot_be_staged_as_retained_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                optional_initialize.read_input(path)

    def test_second_initialization_refused_before_native_initializer(self):
        from mta.runtime.models import ProductionInitialization
        with patch.object(ProductionInitialization.objects, 'exists', return_value=True):
            with self.assertRaisesRegex(ValueError, 'second initialization is refused'):
                optional_initialize.require_empty()

    def test_stage_refuses_paths_outside_volume(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(optional_initialize, 'read_input', return_value=(b'bytes', {})):
                with self.assertRaisesRegex(ValueError, 'owned mta_data'):
                    optional_initialize.stage('input', Path(directory) / 'outside.json')
        # Actual transfer/hash/exclusive-create is proved in the packaged Linux
        # container; no fabricated Windows /var/lib mount is used by this test.
