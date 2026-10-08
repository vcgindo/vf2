"""Storage mapping scope; database roundtrip is a separate migration proof."""
import unittest
import json
from pathlib import Path

from mta.runtime.complete_daily_state import TABLES, BINDINGS, schema_statements, validate_write
from mta.runtime.input_storage import choose_table
from mta.runtime.relational_state import CATALOG, INPUT_TABLES


class CompleteStateTests(unittest.TestCase):
    def test_pick_extension_preserves_previous_catalogue_and_native_columns(self):
        root = Path(__file__).resolve().parents[1]
        previous = json.loads((root/'baseline/complete-daily-state-schema-v1.json').read_bytes())
        for key, fields in previous['tables'].items():
            self.assertEqual(TABLES[key], fields)
        for binding, key in previous['bindings'].items():
            self.assertEqual(BINDINGS[binding], key)
        self.assertEqual(set(TABLES)-set(previous['tables']), {
            'complete/BPR/LogisticPickList', 'complete/BPR/PickListDataForTruckFormation'})
        for name, size in (('LogisticPickList', 21), ('PickListDataForTruckFormation', 16)):
            key = 'complete/BPR/' + name
            self.assertEqual(len(TABLES[key]), size)
            fields = [n for n, _ in TABLES[key]]
            self.assertEqual(choose_table(fields, 'input/opening/state/complete/' + name + '/values'), key)
            self.assertEqual(BINDINGS['closing/complete/' + name], key)

    def test_old_input_candidates_are_unchanged_for_every_existing_family(self):
        legacy = {**CATALOG['tables'], **INPUT_TABLES}
        for fields in legacy.values():
            names = {name.casefold() for name, _ in fields}
            candidates = [key for key, columns in legacy.items()
                          if names <= {name.casefold() for name, _ in columns}]
            expected = min(candidates, key=lambda key: (not key.startswith('input/'), len(legacy[key]), key))
            self.assertEqual(choose_table([n for n, _ in fields], 'input/day/existing'), expected)

    def test_new_flags_require_explicit_complete_opening_path(self):
        fields = ['ScriptName', 'IsScriptExecuted', 'IsScriptCritical', 'ModuleName']
        with self.assertRaisesRegex(ValueError, 'Unmapped typed input family'):
            choose_table(fields, 'input/day/unapproved')
        self.assertEqual(choose_table(fields, 'input/opening/state/complete/ScriptExecutedFlag/values'),
                         BINDINGS['closing/complete/ScriptExecutedFlag'])

    def test_complete_population_name_and_fields_are_bound(self):
        fields = ['ScriptName', 'IsScriptExecuted', 'IsScriptCritical', 'ModuleName']
        for suffix in ('Unknown/values', 'ScriptExecutedFlag/children/values', 'ScriptExecutedFlag'):
            with self.assertRaisesRegex(ValueError, 'Undeclared'):
                choose_table(fields, 'input/opening/state/complete/' + suffix)
        with self.assertRaisesRegex(ValueError, 'fields differ'):
            choose_table(fields, 'input/opening/state/complete/FGTrendData/values')
        with self.assertRaisesRegex(ValueError, 'declared population'):
            validate_write(BINDINGS['closing/complete/ScriptExecutedFlag'], 'input/arbitrary', None)

    def test_supplement_has_typed_duplicate_ordinal_storage_only(self):
        statements = schema_statements()
        self.assertEqual(len(statements), len(TABLES))
        self.assertTrue(all('PRIMARY KEY(vf_run_id,vf_image,vf_ordinal)' in s for s in statements))
        self.assertFalse(any('json' in s.lower() for s in statements))
        self.assertTrue(all('ON DELETE RESTRICT' in s for s in statements))


if __name__ == '__main__':
    unittest.main()
