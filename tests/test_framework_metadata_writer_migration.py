"""Frozen SQL boundaries; actual PostgreSQL migration proof is separate."""
from importlib import import_module
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

module = import_module('mta.runtime.migrations.0240_framework_metadata_writer_guards')


class FrameworkMetadataWriterMigrationTests(unittest.TestCase):
    def editor(self, rows=(), relation=('r',)):
        cursor = MagicMock()
        cursor.fetchone.return_value = relation
        cursor.fetchall.return_value = list(rows)
        connection = SimpleNamespace(vendor='postgresql', cursor=MagicMock())
        connection.cursor.return_value.__enter__.return_value = cursor
        return SimpleNamespace(connection=connection, quote_name=lambda n: '"' + n + '"'), cursor

    def expected(self):
        return sorted(('ingestion_watch_' + suffix, 'O', 'mta', 'ingestion_watch',
            'operational\\000', kind, 1, None, '', old, new)
            for suffix, _op, _ref, kind, old, new in module.SPECS)

    def test_missing_set_installs_exact_statement_and_transition_owners(self):
        editor, cursor = self.editor()
        module.install(None, editor)
        statements = [call.args[0] for call in cursor.execute.call_args_list[2:]]
        self.assertEqual(len(statements), 4)
        for statement, (suffix, op, ref, *_rest) in zip(statements, module.SPECS):
            self.assertEqual(statement, 'CREATE TRIGGER "ingestion_watch_' + suffix + '" AFTER '
                + op + ' ON mta.django_content_type' + (' REFERENCING ' + ref if ref else '')
                + " FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch('operational')")

    def test_complete_existing_set_is_preserved_without_ddl(self):
        editor, cursor = self.editor(self.expected())
        module.install(None, editor)
        self.assertEqual(cursor.execute.call_count, 2)

    def test_partial_or_changed_guards_refuse_without_replacement(self):
        changed = [tuple('D' if i == 1 else v for i, v in enumerate(r)) for r in self.expected()]
        for rows in (self.expected()[:-1], changed):
            editor, cursor = self.editor(rows)
            with self.assertRaisesRegex(ValueError, 'no replacement'):
                module.install(None, editor)
            self.assertEqual(cursor.execute.call_count, 2)

    def test_missing_relation_refuses_and_dependency_is_explicit(self):
        editor, cursor = self.editor(relation=None)
        with self.assertRaisesRegex(ValueError, 'content-type table required'):
            module.install(None, editor)
        self.assertEqual(cursor.execute.call_count, 1)
        self.assertIn(('contenttypes', '0002_remove_content_type_name'), module.Migration.dependencies)
        self.assertFalse(module.Migration.operations[0].reversible)
