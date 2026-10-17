"""The packaged optional procedure cannot silently substitute or repeat inputs.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
from contextlib import nullcontext
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'optional-procedure-unit-only')
import django
django.setup()
from mta.mdm import production_families  # Load decorators before transaction isolation below.
from release.optional_initialize import inspect_input, initialize


class OptionalProcedureTests(unittest.TestCase):
    def test_changed_artifact_is_refused_before_native_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input.json'
            path.write_text('not an approved input')
            with patch('mta.mdm.initialization_contract.decode') as decode:
                with self.assertRaisesRegex(ValueError, 'substitution'):
                    inspect_input(path)
                decode.assert_not_called()

    def test_duplicate_optional_apply_never_calls_native_initializer(self):
        cursor = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        with patch('release.optional_initialize.inspect_input', return_value={}), \
                patch('django.db.transaction.atomic', side_effect=lambda: nullcontext()), \
                patch('django.db.connection.cursor', return_value=cursor), \
                patch('mta.runtime.models.ProductionInitialization.objects.exists', return_value=True), \
                patch('mta.mdm.initialization.initialize') as native:
            with self.assertRaisesRegex(ValueError, 'second apply refused'):
                initialize('/not-read-on-duplicate', apply=True)
            native.assert_not_called()
