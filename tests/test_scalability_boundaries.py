"""Non-semantic opening, CSV transport, export and interruption boundaries.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'scalability-focused-only')
import django
django.setup()

from mta.runtime.opening_scope import immutable, opening_scope, release_opening
from mta.application.production_csv import assemble, parse_csv, CsvIntakeError, IssueRows
from mta.application.streamed_input import JsonInputFile
from mta.runtime.production_daily import decode
from mta.runtime import daily_feed, relational_state
from mta.serialization import rows_digest


def owner():
    return SimpleNamespace(pk=17, source_id=3, input_digest='input', input_manifest_digest='manifest',
        receipt_digest='receipt', configuration_digest='configuration', recipe_sha256='recipe',
        implementation_digest='implementation', input_sha256='sha', _state=SimpleNamespace(db='default'))


class ScalabilityBoundaryTests(unittest.TestCase):
    def test_opening_cache_is_operation_identity_and_failure_scoped(self):
        source = owner()
        build = MagicMock(side_effect=lambda: object())
        self.assertIsNot(immutable(source, 'frame', build), immutable(source, 'frame', build))
        with opening_scope():
            first = immutable(source, 'frame', build)
            with opening_scope():
                self.assertIs(immutable(source, 'frame', build), first)
            source.input_manifest_digest = 'new-manifest'
            self.assertIsNot(immutable(source, 'frame', build), first)
            failure = MagicMock(side_effect=[ValueError('drift'), 'checked'])
            with self.assertRaisesRegex(ValueError, 'drift'):
                immutable(source, 'bad', failure)
            self.assertEqual(immutable(source, 'bad', failure), 'checked')
            current = immutable(source, 'frame', build)
            release_opening()
            self.assertIsNot(immutable(source, 'frame', build), current)
        with opening_scope():
            self.assertIsNot(immutable(source, 'frame', build), first)

    def test_opening_scope_never_caches_live_owner_readback(self):
        from mta.mdm import production_families as production
        source = SimpleNamespace(pk=3, receipt={'schema': production.SOURCE_SCHEMA})
        initialized = owner()
        initialized.source = SimpleNamespace(digest='source')
        frame = {'opening': {'state': {'rows': []}}}
        bags = {'force': {'ForceNormChange': [], 'upload_log': []}}
        expected = {'sealed': True}
        actual_owner = SimpleNamespace(source_id=3, provenance=expected,
            receipt_digest=production.digest(expected), root_state_digest=production.digest(frame['opening']['state']))
        family_rows = MagicMock()
        family_rows.order_by.return_value = [SimpleNamespace(master_id=13, receipt=expected,
                                                             digest=production.digest(expected))]
        with opening_scope(), patch.object(production, '_provenance', return_value=expected), \
                patch.object(production, '_actual', side_effect=[bags['force'], {'drift': []}]) as live, \
                patch.object(production.MdmFamilySource.objects, 'filter', return_value=family_rows):
            production._verify_owner(source, actual_owner, 'force', initialized, frame, bags, True)
            with self.assertRaisesRegex(ValueError, 'opening owner differs'):
                production._verify_owner(source, actual_owner, 'force', initialized, frame, bags, True)
            self.assertEqual(live.call_count, 2)

    def test_native_family_creation_never_constructs_an_unbounded_model_batch(self):
        from mta.mdm import production_families as production
        sizes, values = [], []
        model = MagicMock()
        model.__name__ = 'OrdinaryOpeningOwner'
        model.side_effect = lambda **kw: SimpleNamespace(**kw)
        def inserted(batch, **kwargs):
            sizes.append(len(batch))
            values.extend((row.ordinal, row.Value) for row in batch)
        model.objects.bulk_create.side_effect = inserted
        with patch.object(production, '_fields', return_value=['Value']):
            production._create_rows(model, object(), [{'Value': i} for i in range(1001)], ordinal=True)
        self.assertEqual(sizes, [500, 500, 1])
        self.assertEqual(values, [(i + 1, i) for i in range(1001)])

    def test_streamed_csv_native_file_is_byte_identical_and_fully_validated(self):
        from tools.create_daily_csv_example import create
        from mta.application.production_csv_files import load_binding
        with TemporaryDirectory() as directory:
            root = create(Path(__file__).resolve().parents[1] / 'examples/starter-data/vectorflow-starter-inputs-v1.zip',
                          Path(directory) / 'csv')
            binding = load_binding(root / 'binding-template.json')
            batch = json.loads((root / '2026-10-18/batch.json').read_text())
            paths = {name: root / '2026-10-18' / name for name, state in batch['feeds'].items() if state == 'PRESENT'}
            eager, positions = assemble(batch, binding, {name: path.read_bytes() for name, path in paths.items()}, first_day=True)
            target = root / 'native.json'
            streamed, observed = assemble(batch, binding, paths, first_day=True, output_file=target)
            self.assertIsInstance(streamed, JsonInputFile)
            self.assertEqual(target.read_bytes(), eager)
            self.assertEqual(observed, positions)
            sha = hashlib.sha256(eager).hexdigest()
            self.assertEqual(decode(streamed, sha), decode(eager, sha))
            target.write_bytes(eager + b' ')
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                decode(streamed, sha)

    def test_all_csv_rejections_are_disk_backed_not_truncated(self):
        columns = [dict(name='Qty', type='int', nullable=False)]
        with self.assertRaises(CsvIntakeError) as caught:
            parse_csv(b'Qty\n' + b'bad\n' * 10001, columns, 'large.csv')
        issues = caught.exception.issues
        self.assertIsInstance(issues, IssueRows)
        self.assertEqual(len(issues), 10001)
        self.assertEqual(issues[-1]['record'], 10001)
        self.assertEqual([row['record'] for row in issues[:10]], list(range(1, 11)))

    def test_json_input_hashes_the_descriptor_it_actually_decodes(self):
        import io
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'native.json'
            original = b'{"value":1}'
            path.write_bytes(original)
            real_open = Path.open
            def intercepted(current, mode='r', *args, **kwargs):
                # An independently reopened text path could point at another
                # payload while the original pathname/stat is restored.
                if mode == 'r':
                    return io.StringIO('{"value":2}')
                return real_open(current, mode, *args, **kwargs)
            with patch.object(Path, 'open', autospec=True, side_effect=intercepted) as opened:
                value = JsonInputFile(path).decode(hashlib.sha256(original).hexdigest(),
                    object_pairs_hook=dict, parse_constant=lambda value: value)
                self.assertEqual(value, {'value': 1})
                self.assertEqual(opened.call_count, 1)

    def test_lost_daily_connection_records_unreconciled_failure_without_status_rewrite(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'native-day.json'
            path.write_bytes(b'{}')
            attempt = SimpleNamespace(attempt_id='attempt', phase='VALIDATED', run_id=None,
                status='RUNNING', archive_path=directory, input_sha256=hashlib.sha256(b'{}').hexdigest(),
                predecessor=None, batch_digest='batch', pk=1, refresh_from_db=MagicMock())
            checks = MagicMock(side_effect=[None, RuntimeError('session lost')])
            @contextmanager
            def locked(owner):
                yield checks
            with patch.object(daily_feed, 'binding_owner', return_value=({}, object())), \
                    patch.object(daily_feed, '_bound_attempt', return_value=attempt), \
                    patch.object(daily_feed, 'job_lock', locked), \
                    patch.object(daily_feed, '_parameters', return_value={}), \
                    patch.object(daily_feed, 'save') as save, \
                    patch('mta.runtime.production_daily.execute', side_effect=ValueError('database disconnected')):
                with self.assertRaisesRegex(ValueError, 'database disconnected'):
                    daily_feed.execute('attempt', 'binding', pick_root=directory)
            record = json.loads((Path(directory) / 'interrupted.json').read_text())
            self.assertEqual(record['status'], 'INTERRUPTED_RECONCILIATION_REQUIRED')
            self.assertEqual(record['error']['message'], 'database disconnected')
            attempt.refresh_from_db.assert_not_called()
            self.assertEqual(save.call_count, 1)  # initial CALCULATE only

    def test_export_uses_server_cursor_and_preserves_cells_empty_rows_and_digest(self):
        rows = [{'values': ['é', None, 7]}, {'values': []}]
        item = dict(version=2, image='reports/example', count=2, digest=rows_digest(rows))
        chunked = MagicMock()
        chunked.fetchmany.side_effect = [[(0, 3, 0, 'str', 'é', None, None, None),
            (0, 3, 1, 'null', None, None, None, None), (0, 3, 2, 'int', None, 7, None, None),
            (1, 0, None, None, None, None, None, None)], []]
        plain = MagicMock()
        plain.fetchone.return_value = (0,)
        with patch.object(relational_state.connection, 'chunked_cursor') as server, \
                patch.object(relational_state.connection, 'cursor') as normal:
            server.return_value.__enter__.return_value = chunked
            normal.return_value.__enter__.return_value = plain
            self.assertEqual(list(relational_state.iter_export(SimpleNamespace(pk=1), item)), rows)
            self.assertEqual(chunked.execute.call_count, 1)
            self.assertEqual(plain.execute.call_count, 1)

    def test_lost_session_unlock_does_not_mask_original_error(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (True, 123)
        fake = SimpleNamespace(in_atomic_block=False, needs_rollback=False,
            connection=SimpleNamespace(closed=False), cursor=MagicMock())
        fake.cursor.return_value.__enter__.return_value = cursor
        with patch.object(daily_feed, 'connection', fake):
            with self.assertRaisesRegex(ValueError, 'original failure'):
                with daily_feed.job_lock(SimpleNamespace(pk=1)):
                    cursor.execute.side_effect = RuntimeError('connection lost')
                    raise ValueError('original failure')


if __name__ == '__main__':
    unittest.main()
