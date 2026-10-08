"""Mocked SQL sequencing only; never opens a database or runs a business day."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
import hashlib
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from parity import legacy_isolation as isolation
from parity.adapters.legacy import complete_daily_sql as sql


class Cursor:
    def __init__(self, sets=(), next_error=None):
        self.sets = list(sets) or [(None, [])]
        self.index = 0
        self.next_error = next_error
        self.execute = Mock()
        self.close = Mock()

    @property
    def description(self):
        fields = self.sets[self.index][0]
        return None if fields is None else [(name,) for name in fields]

    def fetchall(self):
        return self.sets[self.index][1]

    def nextset(self):
        if self.next_error:
            raise self.next_error
        self.index += 1
        return self.index < len(self.sets)


class Connection:
    def __init__(self, cursors, autocommit=True):
        self.raw = Mock()
        self.raw.autocommit = autocommit
        self.raw.cursor.side_effect = cursors
        self.raw.commit.side_effect = AssertionError('No global commit')
        self.raw.rollback.side_effect = AssertionError('No rollback')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.raw.close()


class CompleteDailySQLTests(unittest.TestCase):
    owner = '9e0312b1-cf68-44a0-b588-8087b02ea1bd'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.mapping = sql.namespace(self.owner)
        self.patches = [patch.dict(isolation.MAPPING, self.mapping, clear=True),
            patch.object(isolation, 'DATA', sql.data_directory(self.owner)),
            patch.object(isolation, '_lease', object()),
            patch.object(isolation, '_lease_owner', threading.get_ident()),
            patch.object(isolation, 'connection')]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.connect = isolation.connection

    def entry(self, text, name='script.sql', **overrides):
        path = Path(self.temp.name) / name
        path.write_bytes(text.encode('cp1252'))
        entry = dict(source_path=str(path), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                     role='BPR', variables={})
        entry.update(overrides)
        return entry

    def preflight(self, entries):
        return sql.preflight_scripts(entries, owner_id=self.owner, namespace=self.mapping)

    def execute(self, prepared):
        return sql.execute_script(prepared, owner_id=self.owner, namespace=self.mapping)

    def assert_no_transaction(self, connection):
        connection.raw.commit.assert_not_called()
        connection.raw.rollback.assert_not_called()
        connection.raw.close.assert_called_once()

    def test_all_source_hashes_preflight_before_any_connection(self):
        first = self.entry('UPDATE dbo.T SET X=1')
        bad = self.entry('UPDATE dbo.T SET X=2', 'bad.sql', source_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'source identity'):
            self.preflight([first, bad])
        self.connect.assert_not_called()

    def test_source_drift_and_forged_prepared_text_deny_before_connection(self):
        entry = self.entry('SELECT 1')
        prepared = self.preflight([entry])[0]
        with self.assertRaisesRegex(ValueError, 'differs from pinned'):
            self.execute(replace(prepared, sql='DELETE dbo.T'))
        Path(entry['source_path']).write_text('SELECT 2')
        with self.assertRaisesRegex(ValueError, 'source identity'):
            self.execute(prepared)
        self.connect.assert_not_called()

    def test_explicit_variables_guarded_before_connection(self):
        for text, variables in [('SELECT $(Value)', {}),
                                ('USE $(DB)', {'DB': 'master'}),
                                ('$(Statement)', {'Statement': 'REVERT'}),
                                ('SELECT $(Value)', {'Value': '$(Other)'}),
                                ('SELECT $(Value)', {'Value': True})]:
            with self.subTest(text=text, variables=variables), self.assertRaises(ValueError):
                self.preflight([self.entry(text, variables=variables)])
        prepared = self.preflight([self.entry('USE $(DB)\nSELECT $(Value)',
                                variables={'DB': 'VFTEST_BPR', 'Value': 7})])[0]
        self.assertIn(self.mapping['VFTEST_BPR'], prepared.sql)
        self.assertIn('SELECT 7', prepared.sql)
        self.connect.assert_not_called()

    def test_owner_directory_role_and_lease_denials(self):
        for owner in ('temporal-full-001', self.owner.upper(), '00000000-0000-0000-0000-000000000000'):
            with self.assertRaises(ValueError):
                sql.namespace(owner)
        entry = self.entry('SELECT 1')
        with patch.dict(isolation.MAPPING, {'VFTEST_BPR': 'VFTEST_Fresh_BPR'}):
            with self.assertRaisesRegex(ValueError, 'namespace'):
                self.preflight([entry])
        with patch.object(isolation, 'DATA', Path(self.temp.name)):
            with self.assertRaisesRegex(ValueError, 'namespace'):
                self.preflight([entry])
        with self.assertRaises(ValueError):
            self.preflight([dict(entry, role='master')])
        prepared = self.preflight([entry])[0]
        with patch.object(isolation, '_lease', None):
            with self.assertRaisesRegex(ValueError, 'lease'):
                self.execute(prepared)
        self.connect.assert_not_called()

    def test_fresh_script_connections_autocommit_full_typed_results(self):
        prepared = self.preflight([self.entry('SELECT 1\nGO\nSELECT 2'),
                                   self.entry('SELECT 3', 'second.sql')])
        value = Decimal('1.20')
        day = date(2026, 6, 6)
        rows = [(value, None, day), (value, None, day)]
        cursors = [Cursor([(['X', 'X', 'Day'], rows), (['Extra'], [(9,)])]),
                   Cursor(), Cursor()]
        connections = [Connection(cursors[:2]), Connection(cursors[2:])]
        self.connect.side_effect = connections
        receipt = self.execute(prepared[0])
        self.execute(prepared[1])
        self.assertEqual(receipt['status'], 'SUCCEEDED')
        self.assertEqual(receipt['results'][0], {'fields': ['X', 'X', 'Day'], 'rows': [list(r) for r in rows]})
        self.assertIs(receipt['results'][0]['rows'][0][0], value)
        self.assertEqual(len(receipt['results']), 2)
        self.assertEqual(self.connect.call_count, 2)
        self.assertEqual(self.connect.call_args_list[0].args, ('VFTEST_BPR',))
        for connection in connections:
            self.assert_no_transaction(connection)
        for cursor in cursors:
            cursor.close.assert_called_once()

    def test_catch_failure_keeps_partial_effect_receipt_and_stops(self):
        prepared = self.preflight([self.entry('UPDATE dbo.T SET X=1\nGO\nSELECT ERROR_NUMBER() AS ErrorNumber\nGO\nDELETE dbo.T')])[0]
        mutation = Cursor()
        caught = Cursor([(['ErrorNumber', 'ErrorMessage'], [(50000, 'failed')]),
                         (['Further'], [(1,)])])
        connection = Connection([mutation, caught])
        self.connect.return_value = connection
        with self.assertRaises(sql.SQLScriptFailure) as failure:
            self.execute(prepared)
        receipt = failure.exception.receipt
        self.assertEqual(receipt['status'], 'FAILED')
        self.assertEqual(receipt['failure'], 'canonical_error_resultset')
        self.assertEqual(len(receipt['results']), 2)
        self.assertEqual(connection.raw.cursor.call_count, 2)
        mutation.execute.assert_called_once()
        self.assert_no_transaction(connection)

    def test_driver_error_retains_preceding_resultset_without_rollback(self):
        prepared = self.preflight([self.entry('SELECT 1')])[0]
        cursor = Cursor([(['X'], [(1,)])], next_error=RuntimeError('driver'))
        connection = Connection([cursor])
        self.connect.return_value = connection
        with self.assertRaises(sql.SQLScriptFailure) as failure:
            self.execute(prepared)
        self.assertEqual(failure.exception.receipt['results'], [{'fields': ['X'], 'rows': [[1]]}])
        self.assertEqual(failure.exception.receipt['status'], 'FAILED')
        self.assert_no_transaction(connection)

    def test_non_autocommit_connection_never_executes(self):
        prepared = self.preflight([self.entry('UPDATE dbo.T SET X=1')])[0]
        connection = Connection([], autocommit=False)
        self.connect.return_value = connection
        with self.assertRaises(sql.SQLScriptFailure):
            self.execute(prepared)
        connection.raw.cursor.assert_not_called()
        self.assert_no_transaction(connection)

    def test_readback_fresh_typed_occurrences_and_mutation_denial(self):
        prepared = self.preflight([self.entry('UPDATE dbo.T SET X=1')])[0]
        rows = [(Decimal('2.00'), None), (Decimal('2.00'), None)]
        connections = [Connection([Cursor()]), Connection([Cursor([(['X', 'Y'], rows)])])]
        self.connect.side_effect = connections
        self.execute(prepared)
        result = sql.readback(owner_id=self.owner, namespace=self.mapping, role='BPR', query='SELECT X,Y FROM dbo.T ORDER BY Ordinal')
        self.assertEqual(result[0]['rows'], [list(r) for r in rows])
        self.assertEqual(self.connect.call_count, 2)
        for query in ('DELETE dbo.T', 'SELECT 1; DELETE dbo.T', 'SELECT X INTO dbo.Copy FROM dbo.T', 'SELECT * FROM master.dbo.T'):
            with self.subTest(query=query), self.assertRaises(ValueError):
                sql.readback(owner_id=self.owner, namespace=self.mapping, role='BPR', query=query)
        self.assertEqual(self.connect.call_count, 2)
        for connection in connections:
            self.assert_no_transaction(connection)


if __name__ == '__main__':
    unittest.main()
