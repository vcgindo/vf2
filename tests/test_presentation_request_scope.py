import unittest
from mta.presentation.request_scope import once_per_request, read_request


class RequestScopeTests(unittest.TestCase):
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
