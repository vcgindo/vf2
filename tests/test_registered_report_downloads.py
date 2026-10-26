"""Registered intermediate download contracts; storage and safe-open are mocked."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date
from pathlib import Path
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import patch
from django import conf


@unittest.skipUnless(conf.settings.configured, 'Offline Django settings required; no database used')
class RegisteredDownloadTests(unittest.TestCase):
    def setUp(self):
        global downloads
        from mta.presentation import registered_report_downloads as downloads
        from tests.test_runtime_report_candidates import arguments
        from tests.test_runtime_report_files import VARIABLES
        from mta.application.runtime_report_files import layout
        self.args = arguments()
        self.definitions = self.args['report_configuration']['RuntimeReports']
        self.run = Obj(pk='owned-run', business_date=date(2026, 4, 8))
        self.row = Obj(pk='post-bpr', digest='a'*64, phase_id='bpr', metadata={
            'candidate': {'reports': []}, 'authority': {'images': {'images': {}}}, 'catalogue': {}})
        self.sources = {}
        for definition in self.definitions:
            spec = layout(definition, VARIABLES)
            self.row.metadata['candidate']['reports'].append(dict(report_id=definition['Id'],
                last_generated_file_name=spec['file_name']))
            self.row.metadata['catalogue'][spec['download']] = dict(candidate_id=self.row.pk,
                file=dict(size_bytes=20, sha256='b'*64))
            self.sources.update(self.args['inputs'][definition['Id']]['sources'])
        for name, rows in self.sources.items():
            self.row.metadata['authority']['images']['images'][name] = {
                'fields': [(field, 'test-type') for field in rows[0]] if rows else []}
        self.config = {'schema': downloads.attachment.SCHEMA,
                       'post_bpr': dict(id=self.row.pk, digest=self.row.digest)}
        self.view = Obj(run=self.run, run_id=self.run.pk,
            reference=Obj(metadata=dict(runtime_reports=deepcopy(self.config), scope_request_digest='c'*64)),
            bpr=Obj(sources=Obj(acceptance_id='bpr')),
            planning=Obj(attributes=lambda: 'retained-attributes'))

    @contextmanager
    def storage(self):
        with patch.object(downloads.attachment, 'configuration', return_value=(self.config, 'c'*64)), \
                patch.object(downloads.publication, 'configuration',
                    return_value=({}, None, self.args['report_configuration'], None)), \
                patch.object(downloads.publication, 'read', return_value=self.row) as read, \
                patch.object(downloads.images, 'read',
                    side_effect=lambda _run, _manifest, **kw: {name:self.sources[name] for name in kw['fields']}) as images, \
                patch.object(downloads, 'scope', return_value=({'S'}, {'W', 'L', 'P'})) as scope, \
                patch.object(downloads.publication, 'root', return_value=Path('owned-root')), \
                patch.object(downloads, '_open', return_value='verified-stream') as opened:
            yield read, images, scope, opened

    def test_existing_dispatch_preserves_two_names_and_actual_projection_permissions(self):
        from mta.presentation import runtime_report_downloads as dispatch
        with self.storage() as (read, images, scope, opened):
            paths = dispatch.report_paths(self.view)
            self.assertEqual(set(paths), set(downloads.SELECTORS))
            self.assertEqual(paths['Spike_Order_Dump']['downloadName'], 'Spiker_Order_Dump.zip')
            self.assertEqual(paths['TotalReqReport_YYYY-MM-DD']['downloadName'], 'TotalReqReport_2026-04-08.csv')
            for selector in downloads.SELECTORS:
                stream, filename, mime = dispatch.open_file(self.view, {'grants':'fixture'}, selector)
                self.assertEqual(stream, 'verified-stream')
                self.assertEqual((filename, mime), (paths[selector]['downloadName'], paths[selector]['fileType']))
                self.assertEqual(images.call_args.kwargs['candidate_id'], 'post-bpr')
                self.assertEqual(images.call_args.kwargs['placement'], 'PostBPR')
                scope.assert_called_with({'grants':'fixture'}, attributes='retained-attributes')
                self.assertEqual(opened.call_args.args[0], Path('owned-root/post-bpr'))
                self.assertTrue(read.call_args.kwargs['verify_bytes'])

    def test_reference_phase_and_selector_mismatches_deny(self):
        from mta.presentation.context import PublicationUnavailable
        for change in ('request', 'reference', 'phase', 'roster'):
            self.setUp()
            if change == 'request': self.view.reference.metadata['scope_request_digest'] = 'x'*64
            if change == 'reference': self.view.reference.metadata['runtime_reports']['post_bpr']['id'] = 'foreign'
            if change == 'phase': self.row.phase_id = 'foreign'
            if change == 'roster': self.definitions[0]['Active'] = False
            with self.subTest(change=change), self.storage(), self.assertRaises(PublicationUnavailable):
                downloads.binding(self.view)

    def test_dbm_download_revalidates_own_composition(self):
        self.view.dbm_phase = Obj(pk='dbm')
        with self.storage(), patch.object(downloads.attachment, 'require_dbm') as require:
            downloads.report_paths(self.view)
            require.assert_called_once_with(self.view, self.view.dbm_phase)

    def test_duplicate_event_and_terminal_selector_refused(self):
        from mta.presentation.context import PublicationUnavailable
        self.row.metadata['candidate']['reports'].append(self.row.metadata['candidate']['reports'][0])
        with self.storage() as (_, _, _, opened):
            with self.assertRaises(PublicationUnavailable): downloads.report_paths(self.view)
            with self.assertRaises(PublicationUnavailable): downloads.open_file(self.view, {}, 'BOR_OrderAllocationHistory')
            opened.assert_not_called()

    def test_partial_permission_denies_before_file_open(self):
        with self.storage() as (read, _, scope, opened):
            scope.return_value = ({'S'}, {'L'})  # Total requirement also requires parent P.
            with self.assertRaises(PermissionError):
                downloads.open_file(self.view, {}, 'TotalReqReport_YYYY-MM-DD')
            opened.assert_not_called()
            self.assertFalse(any(call.kwargs['verify_bytes'] for call in read.call_args_list))

    def test_changed_publication_or_foreign_catalogue_cannot_open(self):
        from mta.presentation.context import PublicationUnavailable
        for change in ('receipt', 'catalogue'):
            self.setUp()
            with self.subTest(change=change), self.storage() as (read, _, _, opened):
                if change == 'receipt':
                    changed = deepcopy(self.row); changed.digest = 'f'*64
                    read.side_effect = [self.row, changed]
                else:
                    for entry in self.row.metadata['catalogue'].values(): entry['candidate_id'] = 'foreign'
                with self.assertRaises(PublicationUnavailable):
                    downloads.open_file(self.view, {}, 'Spike_Order_Dump')
                opened.assert_not_called()

    def test_empty_typed_image_uses_declared_fields_and_requires_grants(self):
        logical = next(iter(self.args['inputs'][7]['sources']))
        self.sources[logical] = []
        self.row.metadata['authority']['images']['images'][logical]['fields'] = []
        with self.storage() as (_, images, scope, opened):
            downloads.open_file(self.view, {}, 'Spike_Order_Dump')
            self.assertEqual(images.call_args.kwargs['fields'][logical],
                             [field for field, _kind in downloads.images.LOGICAL[logical]])
            opened.reset_mock(); scope.return_value = (set(), {'W'})
            with self.assertRaises(PermissionError): downloads.open_file(self.view, {}, 'Spike_Order_Dump')
            opened.assert_not_called()
