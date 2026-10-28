"""Nonproducing transport qualification; PostgreSQL protocol proof is separate."""
from contextlib import ExitStack, nullcontext
from datetime import date, datetime, timezone
from decimal import Decimal
import sys
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import uuid4

from mta.application.native_daily_contract import SCHEMA
from mta.row_sequences import RecordRows
from mta.runtime import batch_storage as batch
from mta.runtime import relational_state as relational
from mta.serialization import digest


class CopyCursor:
    """A protocol double, deliberately not a simulation of PostgreSQL guards."""
    def __init__(self, *, failure=None, fail_after=None, finish=None, exit_error=None):
        self.failure, self.fail_after, self.finish = failure, fail_after, finish
        self.exit_error = exit_error
        self.rows, self.events, self.commands = [], [], []
        self.sql = None

    def __enter__(self):
        self.events.append('cursor_enter')
        return self

    def __exit__(self, kind, error, traceback):
        self.events.append(('cursor_exit', kind))

    def execute(self, sql, parameters):
        self.commands.append((sql, parameters))

    def copy(self, sql):
        self.sql = sql
        cursor = self
        class Writer:
            def __enter__(self):
                cursor.events.append('copy_enter')
                return self

            def write_row(self, row):
                if cursor.fail_after == len(cursor.rows):
                    raise cursor.failure
                cursor.rows.append(row)

            def __exit__(self, kind, error, traceback):
                cursor.events.append(('copy_exit', kind))
                if kind is None and cursor.exit_error:
                    raise cursor.exit_error
                if kind is None and cursor.finish:
                    cursor.finish()
        return Writer()


def database(cursor, vendor='postgresql'):
    return SimpleNamespace(vendor=vendor, cursor=lambda: cursor,
        wrap_database_errors=nullcontext())


def owner():
    return SimpleNamespace(pk=uuid4(), attempt_id=uuid4(), initialization_id=uuid4())


def identity(attempt):
    return dict(database_name='unit_transport_only', database_oid=37, source_id=4,
        source_digest='a'*64, initialization_id=str(attempt.initialization_id),
        attempt_id=str(attempt.attempt_id))


def populations(*, internal=False):
    names = batch.DECLARATION['intakes'][SCHEMA]
    if internal:
        names = names + batch.DECLARATION['internal_roster']
    return {name: [] for name in names}


def daily_row():
    return dict(SKUCode='S\t雪\n\\', WhCode='', Stock=0, Consumption=-2,
        GIT=None, Receipts=7, PSO=None, ReportDate='2026-04-08')


class ReadCursor:
    def __init__(self, rows):
        self.rows = iter(rows)

    def __enter__(self):
        return self

    def __exit__(self, *error):
        pass

    def execute(self, *arguments):
        pass

    def fetchmany(self, size):
        from itertools import islice
        return list(islice(self.rows, size))


class IngestionCopyTransportTests(TestCase):
    def test_shared_copy_streams_after_enter_and_quotes_column_identifiers(self):
        cursor = CopyCursor()
        def records():
            self.assertEqual(cursor.events[-1], 'copy_enter')
            yield (None, '', 0, False, Decimal('1.2300'), '雪\t\n\\')
        with patch.object(relational, 'connection', database(cursor)), \
                patch.object(relational, 'summary') as summary:
            relational.copy_rows('mta_state."registered"', ['a"b'], records())
        self.assertEqual(cursor.sql, 'COPY mta_state."registered" ("a""b") FROM STDIN')
        self.assertEqual(cursor.rows, [(None, '', 0, False, Decimal('1.2300'), '雪\t\n\\')])
        self.assertEqual(cursor.events[-2:], [('copy_exit', None), ('cursor_exit', None)])
        summary.assert_called_once_with('typed_transport', rows=1, batches=1, transport='copy')

    def test_batch_empty_threshold_and_non_postgres_fallback(self):
        attempt = owner()
        for count, vendor, expected_copy in ((0, 'postgresql', False),
                (499, 'postgresql', False), (500, 'postgresql', True),
                (501, 'postgresql', True), (501, 'sqlite', False)):
            with self.subTest(count=count, vendor=vendor):
                values = populations()
                values['DailyDataRaw.csv'] = [daily_row() for _ in range(count)]
                cursor, inserted = CopyCursor(), []
                db = database(cursor, vendor)
                with patch.object(batch, 'connection', db), \
                        patch.object(relational, 'connection', db), \
                        patch.object(batch, 'bulk', side_effect=lambda sql, rows: inserted.extend(rows)) as bulk:
                    manifest = batch.save_populations(attempt, SCHEMA, values, _identity_resolver=identity)
                self.assertEqual(cursor.sql is not None, expected_copy)
                self.assertEqual(bulk.call_count, int(count > 0 and not expected_copy))
                rows = cursor.rows if expected_copy else inserted
                self.assertEqual(len(rows), count)
                self.assertEqual([row[1] for row in rows], list(range(count)))
                if count:
                    self.assertTrue(all(row[0] == str(attempt.attempt_id) for row in rows))
                    self.assertEqual(rows[0][2:], ('S\t雪\n\\', '', 0, -2, None, 7, None, date(2026, 4, 8)))
                entry = next(e for e in manifest['feeds'] if e['filename'] == 'DailyDataRaw.csv')
                self.assertEqual(entry['count'], count)
                self.assertEqual(entry['digest'], digest(values['DailyDataRaw.csv']))

    def test_batch_copy_matches_insert_and_exact_temporal_readback(self):
        attempt, values = owner(), populations(internal=True)
        filename = '@consumer/requests'
        row = {name: None for name, _ in batch.TABLES[filename]['columns']}
        row.update(SKUCode='S', WhCode='', Request='雪\n\t\\',
            RequestDate='2026-04-08T12:01:02.123400', ActionDate='2026-04-08T12:01')
        # The production representation above 10,000 rows is reiterable, not a list.
        values[filename] = RecordRows(10001, lambda: (dict(row) for _ in range(10001)))
        copied, manifests = {}, []
        for vendor in ('sqlite', 'postgresql'):
            cursor, inserted = CopyCursor(), []
            db = database(cursor, vendor)
            with patch.object(batch, 'connection', db), patch.object(relational, 'connection', db), \
                    patch.object(batch, 'bulk', side_effect=lambda sql, rows: inserted.extend(rows)):
                manifests.append(batch.save_populations(attempt, SCHEMA, values, _identity_resolver=identity))
            copied[vendor] = cursor.rows if vendor == 'postgresql' else inserted
        self.assertEqual(manifests[0], manifests[1])
        self.assertEqual(copied['sqlite'], copied['postgresql'])
        self.assertTrue(cursor.sql.endswith('"vf_wire_RequestDate","vf_wire_ActionDate","vf_wire_ETA") FROM STDIN'))
        entry = next(e for e in manifests[1]['feeds'] if e['filename'] == filename)
        db = SimpleNamespace(chunked_cursor=lambda: ReadCursor(record[1:] for record in cursor.rows))
        with patch.object(batch, 'connection', db):
            restored = list(batch._iter_population(attempt, entry))
        self.assertEqual(restored, [row] * 10001)
        self.assertEqual(cursor.rows[0][-3:], (row['RequestDate'], row['ActionDate'], None))

    def test_batch_timezone_wire_and_column_order_survive_copy(self):
        attempt, values = owner(), populations(internal=True)
        filename = '@consumer/remarks/bpr'
        row = dict(RemarkDate='2026-04-08T06:31:02.123400Z', Remark='',
            Username=None, WhCode='W', SKUCode='S')
        values[filename] = [dict(row) for _ in range(500)]
        cursor = CopyCursor()
        db = database(cursor)
        with patch.object(batch, 'connection', db), patch.object(relational, 'connection', db):
            manifest = batch.save_populations(attempt, SCHEMA, values, _identity_resolver=identity)
        self.assertIn('("vf_attempt_id","vf_ordinal","RemarkDate","Remark","Username","WhCode","SKUCode","vf_wire_RemarkDate")', cursor.sql)
        self.assertEqual(cursor.rows[0][2], datetime(2026, 4, 8, 6, 31, 2, 123400, tzinfo=timezone.utc))
        entry = next(e for e in manifest['feeds'] if e['filename'] == filename)
        db = SimpleNamespace(chunked_cursor=lambda: ReadCursor(record[1:] for record in cursor.rows))
        with patch.object(batch, 'connection', db):
            self.assertEqual(list(batch._iter_population(attempt, entry)), values[filename])

    def test_copy_error_propagates_without_insert_retry(self):
        for error in (ValueError('conversion interrupted'), RuntimeError('COPY rejected')):
            with self.subTest(error=type(error).__name__):
                attempt, values = owner(), populations()
                values['DailyDataRaw.csv'] = [daily_row() for _ in range(500)]
                cursor = CopyCursor(failure=error, fail_after=7)
                db = database(cursor)
                with patch.object(batch, 'connection', db), patch.object(relational, 'connection', db), \
                        patch.object(batch, 'bulk') as bulk, patch.object(relational, 'summary') as summary:
                    with self.assertRaises(type(error)) as raised:
                        batch.save_populations(attempt, SCHEMA, values, _identity_resolver=identity)
                self.assertIs(raised.exception, error)
                self.assertEqual(cursor.events[-2:], [('copy_exit', type(error)), ('cursor_exit', type(error))])
                self.assertEqual(len(cursor.rows), 7)
                bulk.assert_not_called()
                self.assertFalse(any(call.args[0] == 'typed_transport' for call in summary.call_args_list))

    def test_conversion_failure_inside_copy_aborts_without_insert_retry(self):
        attempt, values = owner(), populations()
        row = daily_row()
        row['Stock'] = 1.5
        values['DailyDataRaw.csv'] = [dict(row) for _ in range(500)]
        cursor = CopyCursor()
        db = database(cursor)
        with patch.object(batch, 'connection', db), patch.object(relational, 'connection', db), \
                patch.object(batch, 'bulk') as bulk:
            with self.assertRaisesRegex(ValueError, 'Fraction in canonical integer column'):
                batch.save_populations(attempt, SCHEMA, values, _identity_resolver=identity)
        self.assertEqual(cursor.rows, [])
        self.assertEqual(cursor.events[-2:], [('copy_exit', ValueError), ('cursor_exit', ValueError)])
        bulk.assert_not_called()

    def test_copy_server_rejection_on_exit_does_not_retry_or_report_success(self):
        attempt, values = owner(), populations()
        values['DailyDataRaw.csv'] = [daily_row() for _ in range(500)]
        error = RuntimeError('server guard rejected COPY')
        cursor = CopyCursor(exit_error=error)
        db = database(cursor)
        with patch.object(batch, 'connection', db), patch.object(relational, 'connection', db), \
                patch.object(batch, 'bulk') as bulk, patch.object(relational, 'summary') as summary:
            with self.assertRaisesRegex(RuntimeError, 'server guard rejected COPY') as raised:
                batch.save_populations(attempt, SCHEMA, values, _identity_resolver=identity)
        self.assertIs(raised.exception, error)
        self.assertEqual(cursor.events[-1], ('cursor_exit', RuntimeError))
        bulk.assert_not_called()
        self.assertFalse(any(call.args[0] == 'typed_transport' for call in summary.call_args_list))

    def test_foreign_and_sealed_attempts_fail_before_transport(self):
        class Owner:
            pass
        attempt = Owner()
        attempt.pk, attempt.attempt_id, attempt.initialization_id = uuid4(), uuid4(), uuid4()
        for status, phase, facts, pk in (('RUNNING', 'VALIDATED', {}, attempt.pk),
                ('RUNNING', 'VALIDATE', {'sealed': True}, attempt.pk),
                ('FAILED', 'VALIDATE', {}, attempt.pk),
                ('RUNNING', 'VALIDATE', {}, uuid4())):
            with self.subTest(status=status, phase=phase, facts=facts, pk=pk):
                current = SimpleNamespace(pk=pk, status=status, phase=phase,
                    accepted_facts=facts, initialization_id=attempt.initialization_id)
                Owner.objects = SimpleNamespace(select_related=lambda *a:
                    SimpleNamespace(get=lambda **k: current))
                with patch.object(batch, '_database_identity') as database_identity, \
                        patch.object(batch, 'bulk') as bulk, patch.object(batch, 'copy_rows') as copy:
                    with self.assertRaisesRegex(ValueError, 'current writable or sealed readable owner'):
                        batch.save_populations(attempt, SCHEMA, populations())
                database_identity.assert_not_called()
                bulk.assert_not_called()
                copy.assert_not_called()


class IngestionSealRevisionTests(TestCase):
    def test_seal_observes_transport_revision_cut_and_stale_preparation_is_denied(self):
        from mta.runtime import accepted_daily as accepted
        from mta.runtime import ingestion_admission
        for count in (499, 500):
            with self.subTest(count=count), ExitStack() as patches:
                attempt, values = owner(), populations()
                values['DailyDataRaw.csv'] = [daily_row() for _ in range(count)]
                epochs = [2, 3, 17, 5, 7]
                before = tuple(epochs)
                def advance(amount=1):
                    epochs[2] += amount
                cursor = CopyCursor(finish=advance)
                db = database(cursor)
                attempt.initialization = SimpleNamespace(source_id=4, source=SimpleNamespace(digest='a'*64))
                attempt.input_sha256, attempt.batch_digest = 'b'*64, 'c'*64
                attempt.status, attempt.phase = 'RUNNING', 'VALIDATE'
                attempt.accepted_facts, attempt.prepared_context, attempt.run_id = {}, {}, None
                revision_id = uuid4()
                attempt.master_revision = SimpleNamespace(status='ACCEPTED')
                attempt.certification = SimpleNamespace(status='CERTIFIED', receipt_digest='d'*64)
                attempt.save = Mock(side_effect=lambda **kwargs: advance())
                readiness = SimpleNamespace(revisions=SimpleNamespace(as_tuple=lambda: before),
                    source_digest='a'*64, certification_digest='d'*64,
                    master_revision_id=str(revision_id), configuration_digest='e'*64)
                manager = SimpleNamespace(select_for_update=lambda: SimpleNamespace(get=lambda **kwargs: attempt))
                models = {
                    'mta.runtime.daily_feed_models': SimpleNamespace(DailyFeedAttempt=SimpleNamespace(objects=manager)),
                    'mta.runtime.ingestion_models': SimpleNamespace(InitializationCertification=SimpleNamespace(
                        objects=SimpleNamespace(get=lambda **kwargs: SimpleNamespace(pk=uuid4())))),
                    'mta.mdm.supplier_revisions': SimpleNamespace(source_lock=lambda *args: nullcontext()),
                }
                patches.enter_context(patch.dict(sys.modules, models))
                patches.enter_context(patch.object(accepted, 'connection', db))
                patches.enter_context(patch.object(batch, 'connection', db))
                patches.enter_context(patch.object(relational, 'connection', db))
                patches.enter_context(patch.object(accepted, 'transaction', SimpleNamespace(atomic=nullcontext)))
                patches.enter_context(patch.object(accepted, 'epochs', side_effect=lambda *a, **k: list(epochs)))
                patches.enter_context(patch.object(accepted, 'split', return_value=({}, values)))
                patches.enter_context(patch.object(batch, '_identity', return_value=identity(attempt)))
                # INSERT emits one statement per row; the COPY double reports one
                # statement. This checks Python cut consumption, not SQL triggers.
                patches.enter_context(patch.object(batch, 'bulk', side_effect=lambda sql, rows: advance(len(list(rows)))))
                prepared = SimpleNamespace(checked=lambda sha: {'schema': SCHEMA})
                accepted.seal(attempt, prepared, {}, readiness)
                expected_delta = 2 if count == 500 else count + 1
                self.assertEqual(epochs[2], before[2] + expected_delta)
                self.assertEqual(attempt.prepared_context['revisions'], epochs)
                self.assertEqual(attempt.phase, 'VALIDATED')
                self.assertEqual(attempt.save.call_count, 1)
                with patch.object(ingestion_admission, 'preparation_readiness', return_value=readiness):
                    self.assertEqual(accepted.check(attempt, {}), attempt.prepared_context)
                advance()
                with self.assertRaisesRegex(ValueError, 'preparation is stale'):
                    accepted.check(attempt, {})
