"""Read-only execution history must never admit a mutation or an invalid seal."""
import ast
from copy import deepcopy
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'mdm-read-admission-unit-only')
import django
django.setup()

from mta.mdm import families, production_families as production
from mta.mdm.initialization_contract import SOURCE_SCHEMA
from mta.mdm.location_projection import VERSION
from mta.serialization import digest


class ReadAdmissionTests(unittest.TestCase):
    def seal(self):
        receipt = dict(adapter_digest='a'*64, source_manifest_digest='b'*64,
                       closing_projection_version=VERSION)
        return SimpleNamespace(receipt=receipt, digest=digest(receipt))

    def test_read_retains_original_producer_identity(self):
        seal = self.seal()
        with patch.object(production, 'adapter_digest', side_effect=AssertionError('current code')):
            self.assertEqual(production._read_execution_identity(seal), seal.receipt)

    def test_tampered_seal_and_unknown_schema_are_denied(self):
        for key, value, reseal in (
                ('adapter_digest', 'c'*64, False),
                ('closing_projection_version', 'unsupported', True),
                ('adapter_digest', '', True),
                ('source_manifest_digest', None, True)):
            seal = self.seal()
            seal.receipt[key] = value
            if reseal:
                seal.digest = digest(seal.receipt)
            with self.subTest(key=key, reseal=reseal), self.assertRaises(ValueError):
                production._read_execution_identity(seal)

    def test_family_dispatch_keeps_strict_default_and_explicit_read(self):
        source = SimpleNamespace(receipt={'schema': SOURCE_SCHEMA})
        with patch.object(production, 'require_binding') as check:
            families.require_installed(source, 13)
            check.assert_called_once_with(source, read_only=False)
            check.reset_mock()
            families.require_installed(source, 13, read_only=True)
            check.assert_called_once_with(source, read_only=True)

    def test_only_named_read_endpoints_request_read_admission(self):
        from mta.presentation import mdm_views
        tree = ast.parse(Path(mdm_views.__file__).read_text())
        expected = {'configuration', 'current', 'seasonality_graph', 'task_list',
                    'task_count', 'task_details', 'task_history', 'history_skus'}
        actual = set()
        for function in tree.body:
            if not isinstance(function, ast.FunctionDef):
                continue
            for node in ast.walk(function):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'source':
                    if node.keywords:
                        self.assertEqual([(k.arg, ast.literal_eval(k.value)) for k in node.keywords],
                                         [('read_only', True)])
                        actual.add(function.name)
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
