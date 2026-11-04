import unittest
from unittest.mock import MagicMock, Mock, patch
from mta.presentation.request_scope import once_per_request, read_request


class RequestScopeTests(unittest.TestCase):
    def test_validation_admits_history_cte_and_rejects_writes_and_locks(self):
        from mta.presentation.request_scope import remark_validation, validation_reads

        connection = MagicMock(in_atomic_block=True)
        execute = Mock()
        with patch('django.db.connection', connection), remark_validation(), validation_reads():
            guard, = connection.execute_wrapper.call_args.args
            history = 'WITH prior AS (SELECT 1), changes AS (SELECT 2) SELECT * FROM prior'
            guard(execute, history, (), False, {})
            execute.assert_called_once_with(history, (), False, {})
            execute.reset_mock()

            for sql in (
                'WITH prior AS (DELETE FROM history RETURNING *) SELECT * FROM prior',
                'WITH prior AS (SELECT 1) UPDATE history SET value = 0',
                'WITH prior AS (SELECT 1) SELECT * INTO scratch FROM prior',
                'WITH prior AS (SELECT * FROM history FOR SHARE) SELECT * FROM prior',
                'WITH prior AS (SELECT 1) SELECT * FROM prior FOR UPDATE',
                'WITH prior AS (SELECT 1) SELECT * FROM prior; SET ROLE other_user',
            ):
                with self.subTest(sql=sql), self.assertRaises(ValueError):
                    guard(execute, sql, (), False, {})
            execute.assert_not_called()

    def test_typed_scalar_arguments_do_not_alias_boolean_integer_or_float(self):
        calls = []
        @once_per_request
        def check(value):
            calls.append(type(value))
            return type(value)
        with read_request('/api/GetBPRData'):
            self.assertIs(check(True), bool)
            self.assertIs(check(1), int)
            self.assertIs(check(1.0), float)
            self.assertIs(check(True), bool)
        self.assertEqual(calls, [bool, int, float])

    def test_startup_metadata_passes_are_fresh_and_never_http_reads(self):
        from mta.presentation.request_scope import metadata_operation, in_read_request
        current = ['first']
        calls = []
        @once_per_request
        def check():
            calls.append(current[0])
            return current[0]
        with metadata_operation():
            self.assertFalse(in_read_request())
            self.assertEqual(check(), check())
        current[0] = 'second'
        with metadata_operation():
            self.assertEqual(check(), 'second')
        check(); check()
        self.assertEqual(calls, ['first', 'second', 'second', 'second'])

    def test_startup_only_ancestry_cache_preserves_flags_errors_and_writer_behavior(self):
        from mta.presentation.request_scope import metadata_operation, once_per_metadata_operation
        calls = []
        @once_per_metadata_operation
        def check(*, reading=True, branch=False):
            calls.append((reading, branch))
            if branch:
                raise ValueError('branch changed')
            return len(calls)
        with read_request('/api/mta/GetBPRData'):
            check(); check()
        with metadata_operation():
            self.assertEqual(check(), check())
            check(reading=False); check(reading=False)
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'branch changed'):
                    check(branch=True)
        with metadata_operation():
            self.assertEqual(check(), 8)
        self.assertEqual(len(calls), 8)

    def test_export_reads_revalidate_changed_dependencies_on_next_request(self):
        from mta.presentation.request_scope import in_read_request
        paths = ['GetExportDataAsync', 'SKUDesc', 'WHDesc'] + ['DownloadReports/' + name for name in (
            'LogisticPickListReport', 'LogisticRemainingQtySummary',
            'LogisticRemainingQtyDetails', 'TransportReqSummaryRpt', 'InputData', 'BOR_OrderAllocation',
            'DailyDataUnavailabilityReport','InvalidDataReport','NMSAddNewSKULoc','NMSModifySKULoc',
            'NMSRemoveSKULoc','NMSLocMaster','NMSSKUMaster','NMSSOBMaster','NMSMOQMaster','ForceNormChangeUpload')]
        for path in paths:
            with self.subTest(path=path):
                current = ['accepted']
                calls = []
                @once_per_request
                def check():
                    calls.append(current[0])
                    if current[0] != 'accepted':
                        raise ValueError('selection or grant changed')
                with read_request('/api/mta/' + path):
                    self.assertTrue(in_read_request())
                    check(); check()
                self.assertFalse(in_read_request())
                current[0] = 'changed'
                with read_request('/api/mta/' + path), self.assertRaises(ValueError):
                    check()
                self.assertFalse(in_read_request())
                self.assertEqual(calls, ['accepted', 'changed'])

    def test_download_scope_does_not_include_unknown_or_unrelated_routes(self):
        from mta.presentation.request_scope import in_read_request
        for path in ('DownloadReports/unknown', 'LogisticPickListReport', 'InputData', 'BOR_OrderAllocation',
                     'Other/BOR_OrderAllocation',
                     'Other/InputData', 'Other/LogisticPickListReport', 'DBMApplySelectedNorms',
                     'DBMUpdateSleepTbl', 'AddRemark', 'SaveState'):
            with self.subTest(path=path), read_request('/api/mta/' + path):
                self.assertFalse(in_read_request())

    def test_saved_layout_read_reuses_checks_but_revalidates_next_request(self):
        calls = []
        @once_per_request
        def publication_check():
            calls.append(1)
        for _ in range(2):
            before = len(calls)
            with read_request('/api/mta/GetState'):
                publication_check(); publication_check()
            self.assertEqual(len(calls), before + 1)
        for route in ('SaveState', 'ResetState'):
            before = len(calls)
            with read_request('/api/mta/' + route):
                publication_check(); publication_check()
            self.assertEqual(len(calls), before + 2)

    def test_mdm_current_reads_reuse_but_workflow_writes_do_not(self):
        calls = []
        @once_per_request
        def check():
            calls.append(1)
        for route in ('GetMasterUIConfiguration', 'GetCount', 'GetMasterData'):
            before = len(calls)
            with read_request('/api/mta/' + route):
                check(); check()
            self.assertEqual(len(calls), before + 1)
        for route in ('AddMasterData', 'ModifyMasterData', 'RemoveMasterData', 'draft'):
            before = len(calls)
            with read_request('/api/mta/' + route):
                check(); check()
            self.assertEqual(len(calls), before + 2)

    def test_changed_source_identity_is_not_reused(self):
        from types import SimpleNamespace
        calls = []
        @once_per_request
        def check(source):
            calls.append(source.digest)
        source = SimpleNamespace(_meta=True, pk=1, digest='original')
        with read_request('/api/mta/GetCount'):
            check(source); check(source)
            source.digest = 'changed'
            check(source)
        self.assertEqual(calls, ['original', 'changed'])

    def test_reuses_within_request_and_revalidates_next_request(self):
        calls = []
        @once_per_request
        def check(run):
            calls.append(run)
            return len(calls)
        with read_request('/api/mta/GetBPRData'):
            self.assertEqual(check('one'), check('one'))
            self.assertEqual(check('two'), 2)
        with read_request('/api/mta/GetBPRData'):
            self.assertEqual(check('one'), 3)

    def test_offline_and_write_paths_never_reuse(self):
        calls = []
        @once_per_request
        def check():
            calls.append(1)
        check(); check()
        with read_request('/api/mta/AddRemark'):
            check(); check()
        self.assertEqual(len(calls), 4)

    def test_failed_validation_and_failed_request_do_not_leave_results(self):
        calls = []
        @once_per_request
        def check():
            calls.append(1)
            raise ValueError('changed source')
        for _ in range(2):
            with self.assertRaises(ValueError), read_request('/api/mta/GetBPRData'):
                check()
        self.assertEqual(len(calls), 2)

    def test_full_readback_is_distinct_and_nested_request_reuses(self):
        calls = []
        @once_per_request
        def check(*, verify_rows=False):
            calls.append(verify_rows)
            return len(calls)
        with read_request('/api/mta/GetBPRData'):
            self.assertEqual(check(), 1)
            with read_request('/api/mta/GetBPRData'):
                self.assertEqual(check(), 1)
                self.assertEqual(check(verify_rows=True), 2)
        self.assertEqual(calls, [False, True])

    def test_concurrent_requests_do_not_share_metadata(self):
        import asyncio
        calls = []
        @once_per_request
        def check():
            calls.append(len(calls) + 1)
            return calls[-1]
        async def request(entered, other_entered):
            with read_request('/api/mta/GetBPRData'):
                first = check()
                entered.set()
                await other_entered.wait()
                self.assertEqual(check(), first)
                return first
        async def run():
            first, second = asyncio.Event(), asyncio.Event()
            values = await asyncio.gather(request(first, second), request(second, first))
            self.assertEqual(values, [1, 2])
            # Both task-local caches have ended; the caller is uncached.
            self.assertEqual(check(), 3)
        asyncio.run(run())
