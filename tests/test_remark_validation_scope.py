"""Read memoization cannot escape a pure phase, transaction, or connection."""
from contextlib import contextmanager
import os,unittest
from unittest.mock import patch
from mta.presentation import request_scope as scope


class Database:
    def __init__(self):
        self.in_atomic_block = True
        # Real driver connections are hashable identities.
        self.connection = type('Physical', (), {'closed': False})()
        self.wrappers = []
        self.executed = []

    @contextmanager
    def execute_wrapper(self, wrapper):
        self.wrappers.append(wrapper)
        try: yield
        finally: self.wrappers.pop()

    def execute(self, sql):
        def execute(sql, params, many, context):self.executed.append(sql)
        for wrapper in self.wrappers:
            previous = execute
            execute = lambda sql, params, many, context, wrapper=wrapper, previous=previous: wrapper(previous,sql,params,many,context)
        return execute(sql, None, False, {})


class RemarkValidationTests(unittest.TestCase):
    def setUp(self):
        self.database = Database()
        self.patch = patch('django.db.connection', self.database)
        self.patch.start();self.addCleanup(self.patch.stop)

    def reader(self):
        calls=[]
        @scope.once_per_request
        def check(value):
            calls.append(value)
            if value=='error':raise ValueError('failed validation')
            return len(calls)
        return check,calls

    def test_opt_in_cache_is_only_inside_one_pure_phase(self):
        check,calls=self.reader()
        with scope.validation_reads():check(1);check(1)
        with scope.remark_validation():
            check(1);check(1)
            with scope.validation_reads():
                self.assertFalse(scope.in_read_request())
                self.assertTrue(scope.in_validation_reads())
                first=check(1);self.assertEqual(check(1),first)
                with scope.validation_reads():self.assertEqual(check(1),first)
            self.assertFalse(scope.in_validation_reads())
            with scope.validation_reads():self.assertNotEqual(check(1),first)
            check(1);check(1)
        self.assertEqual(calls,[1]*8)

    def test_writer_transaction_and_other_cache_boundaries_are_mandatory(self):
        self.database.in_atomic_block=False
        with self.assertRaises(ValueError),scope.remark_validation():pass
        self.database.in_atomic_block=True
        for other in (scope.read_request('/api/GetBPRData'),scope.metadata_operation()):
            with other,self.assertRaises(ValueError),scope.remark_validation():pass
        with scope.remark_validation():
            with self.assertRaises(ValueError),scope.remark_validation():pass
        self.assertFalse(scope.in_validation_reads())

    def test_data_ddl_role_transaction_and_multi_statement_writes_never_execute(self):
        with scope.remark_validation(),scope.validation_reads():
            for sql in ('INSERT INTO x VALUES(1)','UPDATE x SET a=1','DELETE FROM x','TRUNCATE x',
                    'CREATE TABLE x(a int)','SET ROLE x','SAVEPOINT x','RELEASE SAVEPOINT x',
                    'WITH d AS (DELETE FROM x RETURNING *) SELECT * FROM d','SELECT 1; DELETE FROM x',''):
                with self.subTest(sql=sql),self.assertRaises(ValueError):self.database.execute(sql)
            self.database.execute('SELECT 1')
            self.database.execute("SELECT ';' AS punctuation;")
        self.assertEqual(self.database.executed,['SELECT 1',"SELECT ';' AS punctuation;"])
        # Mutation is permitted only after the read phase/cache has gone away.
        self.database.execute('UPDATE x SET a=1')
        self.assertEqual(len(self.database.executed),3)

    def test_failed_reads_and_phase_exceptions_never_reuse_results(self):
        check,calls=self.reader()
        with scope.remark_validation():
            for _ in range(2):
                with self.assertRaisesRegex(ValueError,'failed'),scope.validation_reads():check('error')
                self.assertFalse(scope.in_validation_reads())
            with scope.validation_reads():
                for _ in range(2):
                    with self.assertRaisesRegex(ValueError,'failed'):check('error')
        self.assertEqual(calls,['error']*4)

    def test_new_physical_connection_cannot_inherit_a_successful_binding(self):
        check,calls=self.reader()
        with scope.remark_validation(),scope.validation_reads():
            first=check(1);self.assertEqual(check(1),first)
            previous=self.database.connection
            self.database.connection=type('Physical',(),{'closed':False})()
            second=check(1);self.assertNotEqual(first,second)
            self.database.connection.closed=True
            check(1);check(1)
            self.database.connection=previous
            # The previous connection's exact immutable read is still scoped
            # to this one phase; a new phase always starts empty.
            self.assertEqual(check(1),first)
        self.assertEqual(calls,[1]*4)

    def test_decorated_reader_leaves_no_cache_before_a_write(self):
        check,calls=self.reader()
        @scope.validated_read
        def reader():return check(1),check(1)
        with scope.remark_validation():
            self.assertEqual(reader(),(1,1))
            self.assertFalse(scope.in_validation_reads())
            self.database.execute('UPDATE source SET revision=2')
            self.assertEqual(reader(),(2,2))
        self.assertEqual(calls,[1,1])

    def test_existing_immutable_reader_opens_one_nested_traversal_only(self):
        check,calls=self.reader()
        @scope.once_per_request
        def reader():
            self.database.execute('SELECT 1')
            return check(1),check(1)
        with scope.remark_validation():
            self.assertEqual(reader(),(1,1))
            self.assertFalse(scope.in_validation_reads())
            self.database.execute('UPDATE source SET revision=2')
            self.assertEqual(reader(),(2,2))
            self.assertFalse(scope.in_validation_reads())
        self.assertEqual(calls,[1,1])

    def test_declared_immutable_reader_cannot_write_under_writer_marker(self):
        @scope.once_per_request
        def invalid_reader():self.database.execute('UPDATE source SET revision=2')
        with scope.remark_validation():
            with self.assertRaises(ValueError):invalid_reader()
            self.assertFalse(scope.in_validation_reads())
            self.database.execute('UPDATE source SET revision=3')
        self.assertEqual(self.database.executed,['UPDATE source SET revision=3'])


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ValidationPostgreSQLTests(unittest.TestCase):
    def test_existing_reader_rechecks_a_guard_changed_between_traversals(self):
        from django.db import connection,transaction
        from mta.runtime import ingestion_ownership as guards
        self.assertEqual(connection.settings_dict['NAME'],'VFTEST_Fresh_LifecycleG2_20261024')
        @scope.once_per_request
        def traversal():
            with connection.cursor() as cursor:
                guards.require_guard_coverage(cursor);guards.require_guard_coverage(cursor)
        with transaction.atomic(),patch.object(guards,'_verify_guard_coverage',wraps=guards._verify_guard_coverage) as verify:
            with scope.remark_validation():
                traversal();self.assertEqual(verify.call_count,1)
                self.assertFalse(scope.in_validation_reads())
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mta.fresh_mta_bprliveremark DISABLE TRIGGER ingestion_watch_insert')
                    for _ in range(2):
                        with self.assertRaisesRegex(ValueError,'disabled'):traversal()
                    self.assertEqual(verify.call_count,3)
                    transaction.set_rollback(True)
                traversal();self.assertEqual(verify.call_count,4)
            transaction.set_rollback(True)

    def test_each_real_phase_rechecks_guards_and_writer_sql_never_uses_a_read_cache(self):
        from django.db import connection,transaction
        from mta.runtime import ingestion_ownership as guards
        self.assertEqual(connection.settings_dict['NAME'],'VFTEST_Fresh_LifecycleG2_20261024')
        with transaction.atomic(),patch.object(guards,'_verify_guard_coverage',wraps=guards._verify_guard_coverage) as verify:
            with connection.cursor() as cursor:
                cursor.execute('SELECT oid FROM pg_database WHERE datname=current_database()')
                self.assertEqual(cursor.fetchone(),(84054,))
            with scope.remark_validation():
                with scope.validation_reads(),connection.cursor() as cursor:
                    guards.require_guard_coverage(cursor);guards.require_guard_coverage(cursor)
                    self.assertEqual(verify.call_count,1)
                    for sql in ('UPDATE mta.fresh_mta_calculationrun SET id=id WHERE FALSE',
                            'SELECT 1; UPDATE mta.fresh_mta_calculationrun SET id=id WHERE FALSE'):
                        with self.assertRaises(ValueError):cursor.execute(sql)
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mta.fresh_mta_bprliveremark DISABLE TRIGGER ingestion_watch_insert')
                    with scope.validation_reads(),connection.cursor() as cursor:
                        for _ in range(2):
                            with self.assertRaisesRegex(ValueError,'disabled'):guards.require_guard_coverage(cursor)
                    self.assertEqual(verify.call_count,3)  # Failures are never memoized.
                    transaction.set_rollback(True)
                with scope.validation_reads(),connection.cursor() as cursor:
                    guards.require_guard_coverage(cursor);guards.require_guard_coverage(cursor)
                    self.assertEqual(verify.call_count,4)
                # Outside a pure phase even this opted-in writer must perform
                # the complete original physical verification on every call.
                with connection.cursor() as cursor:
                    guards.require_guard_coverage(cursor);guards.require_guard_coverage(cursor)
                    self.assertEqual(verify.call_count,6)
            transaction.set_rollback(True)
