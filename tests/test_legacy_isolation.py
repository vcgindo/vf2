import unittest
from parity.legacy_isolation import bind_sql, connection, MAPPING


class IsolationTest(unittest.TestCase):
    def test_only_declared_aliases_bind(self):
        self.assertEqual(bind_sql('SELECT * FROM VFTEST_BPR.dbo.BPR'),
                         'SELECT * FROM VFTEST_Fresh_BPR.dbo.BPR')
        self.assertEqual(len(MAPPING), 8)

    def test_protected_databases_and_unknown_roles_rejected(self):
        for name in ['Demo_BPR_1', 'VFTEST_Block2_DBM', 'VF4_GM_BPR', 'VFTEST_Fresh_Unknown']:
            with self.assertRaises(ValueError, msg=name):
                bind_sql('TRUNCATE TABLE ' + name + '.dbo.Example')

    def test_database_operations_rejected(self):
        for statement in ['DROP DATABASE VFTEST_BPR', 'ALTER DATABASE VFTEST_BPR SET SINGLE_USER',
                          "EXEC sp_configure 'show advanced options',1",'USE master; DROP TABLE dbo.X',
                          'DELETE FROM msdb.dbo.suspect_pages',"EXEC('SELECT 1') AT [OtherServer]",
                          "REVERT", "EXECUTE AS LOGIN='sa'", 'SELECT * FROM AnotherDb.dbo.X']:
            with self.assertRaises(ValueError):
                bind_sql(statement)

    def test_connection_without_ownership_fails_before_odbc(self):
        with self.assertRaisesRegex(ValueError, 'lease'):
            connection('VFTEST_BPR')
