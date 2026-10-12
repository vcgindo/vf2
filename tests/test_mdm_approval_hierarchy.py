from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest

from mta.mdm.approval_hierarchy import project, project_rows


class ApprovalHierarchyTests(unittest.TestCase):
    def test_missing_changed_and_wrong_artifact_bindings_are_denied(self):
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
        django.setup()
        from mta.mdm.daily_source import APPROVAL_DAY_ARTIFACT_SHA
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'changed.json'
            path.write_text('{}', encoding='utf-8')
            for selected, artifact in (('', APPROVAL_DAY_ARTIFACT_SHA),
                                       (str(path), '0' * 64),
                                       (str(path), APPROVAL_DAY_ARTIFACT_SHA)):
                with self.subTest(path=selected, artifact=artifact), self.assertRaises(ValueError):
                    project([self.row], path=selected, artifact_sha256=artifact)

    def setUp(self):
        self.binding = {kind: [dict(code=code, level_1='Root', level_2='Group', level_3='Leaf')]
                        for kind, code in (('products', '6120'), ('locations', 'LDC001'))}
        self.row = dict(SKUCode='6120', WhCode='LDC001', Norm=73, Weight=None,
                        SKUAtt04=None, LocAtt04='untouched', SL4=None, LL4='retained')
        for prefix, custom in (('SL', 'SKUAtt'), ('LL', 'LocAtt')):
            for i, value in enumerate(('Root', 'Group', 'Leaf'), 1):
                self.row[prefix + str(i)] = None
                self.row[custom + f'{i:02}'] = value

    def test_exact_six_field_projection_preserves_ordinals_duplicates_nulls(self):
        rows = [deepcopy(self.row), deepcopy(self.row)]
        before = deepcopy(rows)
        actual = project_rows(rows, self.binding)
        self.assertEqual(rows, before)
        self.assertEqual(len(actual), 2)
        changed = {prefix + str(i) for prefix in ('SL', 'LL') for i in (1, 2, 3)}
        for old, new in zip(rows, actual):
            self.assertEqual({k for k in old if old[k] != new[k]}, changed)
            self.assertEqual(set(old), set(new))
        self.assertEqual(project_rows(actual, self.binding), actual)

    def test_description_only_parent_preserves_native_null_attributes(self):
        binding = deepcopy(self.binding)
        binding['locations'].append(dict(code='PL001', level_1='Root', level_2='Group', level_3='Leaf'))
        parent = {k: None for k in self.row}
        parent['WhCode'] = 'PL001'
        actual = project_rows([self.row, parent], binding)
        self.assertEqual(actual[1], parent)
        self.assertEqual(len(actual), 2)

    def test_conflicts_and_missing_identity_are_denied(self):
        for field in ('SL1', 'LL2', 'SKUAtt01', 'LocAtt03', 'SKUCode', 'WhCode'):
            row = {**self.row, field: 'conflict'}
            with self.subTest(field=field), self.assertRaises(ValueError):
                project_rows([row], self.binding)
        duplicate = deepcopy(self.binding)
        duplicate['products'] *= 2
        with self.assertRaises(ValueError):
            project_rows([self.row], duplicate)


if __name__ == '__main__':
    unittest.main()
