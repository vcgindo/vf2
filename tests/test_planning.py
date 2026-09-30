from copy import deepcopy
import json
from pathlib import Path
import unittest

from mta.planning.engine import calculate_current_day, CURRENT_DAY_OUTPUTS, MASTER_OUTPUTS


class PlanningTest(unittest.TestCase):
    def test_reused_math_has_no_runtime_database_dependency(self):
        import ast
        for folder in ['mta/domain', 'mta/application', 'mta/planning']:
            for path in Path(folder).glob('*.py'):
                tree = ast.parse(path.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        self.assertFalse((node.module or '').startswith(('django.', 'mta.runtime', 'mta.canonical')),
                                         str(path))

    def test_retained_input_complete_output_roster_and_immutability(self):
        source = json.loads(Path('mta/fixtures/r1_raw_current_day.json').read_text())
        original = deepcopy(source)
        output = calculate_current_day(source)
        self.assertTrue(set(CURRENT_DAY_OUTPUTS).issubset(output))
        self.assertGreater(len(output['r1_requirement']), 0)
        self.assertEqual(source, original)

    def test_no_expected_ration_seed(self):
        source = json.loads(Path('mta/fixtures/r1_raw_current_day.json').read_text())
        source['rationed_quantity'] = 123
        with self.assertRaises(ValueError):
            calculate_current_day(source)
