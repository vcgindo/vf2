"""The native database-name correction must preserve every other guard clause."""
from importlib import import_module
import unittest


class CasefoldGuardTests(unittest.TestCase):
    def test_only_database_case_predicate_changes_in_original_definition(self):
        module = import_module('mta.runtime.migrations.0219_scope_read_test_database_casefold')
        self.assertEqual(module.NEW_DEFINITION.replace(module.PREDICATE, module.OLD_PREDICATE),
            module.OLD_DEFINITION)
        self.assertEqual(module.NEW_DEFINITION.count(module.PREDICATE), 1)
        self.assertEqual(module.Migration.dependencies, [('fresh_mta', '0218_scope_read_reference_guards')])
        self.assertTrue(module.SQL.startswith(module.LOCK))
        self.assertTrue(module.REVERSE.startswith(module.LOCK))
        self.assertIn('IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopereadreference)', module.REVERSE)
