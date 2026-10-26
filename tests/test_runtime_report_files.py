from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from mta.application import runtime_report_files as reports
from mta.application import operational_io as files

FIXTURE = Path(__file__).parent/'fixtures/runtime_reports_retained_20261019.json'


def row(identity=10):
    return next(r for r in json.loads(FIXTURE.read_bytes()) if r['Id'] == identity)


VARIABLES = dict(TotalReqReport='TotalReqReport_2026-04-08', ReportsDownloadLoc='download')


def writer(*, root, staging, members, destination):
    path = files.owned_path(root, destination)
    with zipfile.ZipFile(path, 'x') as archive:
        for name in members:
            archive.write(files.owned_path(root, staging+'/'+name), arcname=name)
    return dict(unit_protocol=True)


def seed(root, relative, value=b'prior'):
    files.write_file(root, relative, value)


class RuntimeReportFilesTests(unittest.TestCase):
    def test_all_retained_layouts_preserve_names_and_zip_branch(self):
        for definition in json.loads(FIXTURE.read_bytes()):
            with self.subTest(identity=definition['Id']):
                before = deepcopy(definition)
                selected = reports.layout(definition, VARIABLES)
                name = VARIABLES['TotalReqReport'] if definition['Id'] == 10 else definition['FileName']
                extension = 'zip' if definition['Compression'] else 'csv'
                self.assertEqual(selected['output'], 'output/'+name+'.'+extension)
                self.assertEqual(selected['download'], 'download/'+name+'.'+extension)
                self.assertEqual(definition, before)
        self.assertEqual(reports.layout(row(7), VARIABLES)['file_name'], 'Spiker_Order_Dump')

    def test_plain_replacement_cleans_previous_and_keeps_new_output_and_download(self):
        with tempfile.TemporaryDirectory() as root:
            definition = row(); before = deepcopy(definition)
            for relative in ('output/TotalReqReport_20260407.csv', 'download/TotalReqReport_20260407.csv',
                             'output/TotalReqReport_2026-04-08.csv', 'download/TotalReqReport_2026-04-08.csv'):
                seed(root, relative)
            result = reports.publish(root=root, definition=definition, variables=VARIABLES, report_bytes=b'new\r\n')
            for folder in ('output', 'download'):
                self.assertFalse(Path(root, folder, 'TotalReqReport_20260407.csv').exists())
                self.assertEqual(Path(root, folder, 'TotalReqReport_2026-04-08.csv').read_bytes(), b'new\r\n')
            self.assertEqual(result['last_generated_file_name'], VARIABLES['TotalReqReport'])
            self.assertEqual(result['output']['sha256'], result['download']['sha256'])
            self.assertEqual(definition, before)

    def test_compressed_cleanup_and_exact_member_preserves_old_destination_when_disabled(self):
        with tempfile.TemporaryDirectory() as root:
            definition = dict(row(7), LastGeneratedFileName='previous', DeleteOldFile=False)
            for relative in ('output/previous.csv', 'output/previous.zip',
                             'output/Spiker_Order_Dump.csv', 'output/Spiker_Order_Dump.zip',
                             'download/previous.zip', 'download/Spiker_Order_Dump.zip'):
                seed(root, relative)
            result = reports.publish(root=root, definition=definition, variables=VARIABLES,
                                     report_bytes=b'header\r\n', archive_writer=writer)
            for relative in ('output/previous.csv','output/previous.zip','output/Spiker_Order_Dump.csv'):
                self.assertFalse(Path(root, relative).exists())
            self.assertEqual(Path(root, 'download/previous.zip').read_bytes(), b'prior')
            for relative in ('output/Spiker_Order_Dump.zip','download/Spiker_Order_Dump.zip'):
                with zipfile.ZipFile(Path(root, relative)) as archive:
                    self.assertEqual(archive.namelist(), ['Spiker_Order_Dump.csv'])
                    self.assertEqual(archive.read('Spiker_Order_Dump.csv'), b'header\r\n')
            self.assertEqual(result['csv']['sha256'], hashlib.sha256(b'header\r\n').hexdigest())

    def test_same_previous_current_name_and_compressed_delete_old_true(self):
        with tempfile.TemporaryDirectory() as root:
            definition = row(7)
            for relative in ('output/Spiker_Order_Dump.zip','download/Spiker_Order_Dump.zip'):
                seed(root, relative)
            result = reports.publish(root=root, definition=definition, variables=VARIABLES,
                                     report_bytes=b'', archive_writer=writer)
            self.assertEqual(result['csv']['size_bytes'], 0)
            self.assertEqual(result['output']['sha256'], result['download']['sha256'])

    def test_invalid_contract_or_path_denies_before_cleaning_any_files(self):
        variants = [dict(row(7), **change) for change in (
            {'Extension':'xlsx'}, {'TemplateName':'template'}, {'Compression':2},
            {'FileName':'../escape'}, {'FileName':'NUL'}, {'FileName':'a%unknown%'},
            {'DestFolder':'../escape'}, {'DestFolder':'output'}, {'DestFolder':'output/sub'},
            {'DestFolder':'OUTPUT'}, {'DestFolder':'output '}, {'DestFolder':'download/..'},
            {'LastGeneratedFileName':''},
            {'Query':'select 1'})]
        with tempfile.TemporaryDirectory() as root:
            seed(root, 'output/Spiker_Order_Dump.csv')
            for definition in variants:
                with self.subTest(definition=definition), self.assertRaises(ValueError):
                    reports.publish(root=root, definition=definition, variables=VARIABLES,
                                    report_bytes=b'new', archive_writer=writer)
                self.assertEqual(Path(root,'output/Spiker_Order_Dump.csv').read_bytes(), b'prior')
            for variables, payload, archive in (({}, b'new', writer), (VARIABLES, 'new', writer),
                                                 (VARIABLES, b'new', None)):
                with self.assertRaises(ValueError):
                    reports.publish(root=root, definition=row(7), variables=variables,
                                    report_bytes=payload, archive_writer=archive)
                self.assertEqual(Path(root,'output/Spiker_Order_Dump.csv').read_bytes(), b'prior')

    def test_failed_archive_returns_no_success_and_does_not_replace_download(self):
        def fail(**kwargs):
            raise RuntimeError('archive failed')
        with tempfile.TemporaryDirectory() as root:
            seed(root, 'download/Spiker_Order_Dump.zip')
            with self.assertRaisesRegex(RuntimeError, 'archive failed'):
                reports.publish(root=root, definition=row(7), variables=VARIABLES,
                                report_bytes=b'new', archive_writer=fail)
            self.assertEqual(Path(root,'download/Spiker_Order_Dump.zip').read_bytes(), b'prior')
            self.assertEqual(Path(root,'output/Spiker_Order_Dump.csv').read_bytes(), b'new')

    def test_null_previous_name_uses_native_one_space_placeholder(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed), tempfile.TemporaryDirectory() as root:
                definition = dict(row(7), Compression=compressed, LastGeneratedFileName=None)
                extension = 'zip' if compressed else 'csv'
                seed(root, 'output/ .csv')
                if compressed:
                    seed(root, 'output/ .zip')
                seed(root, 'download/ .'+extension)
                result = reports.publish(root=root, definition=definition, variables=VARIABLES,
                                         report_bytes=b'header\r\n', archive_writer=writer)
                self.assertFalse(Path(root,'output/ .csv').exists())
                self.assertFalse(Path(root,'output/ .zip').exists())
                self.assertFalse(Path(root,'download/ .'+extension).exists())
                self.assertEqual(result['last_generated_file_name'], 'Spiker_Order_Dump')

    def test_writer_receipt_cannot_substitute_wrong_archive_content(self):
        def wrong(*, root, staging, members, destination):
            with zipfile.ZipFile(files.owned_path(root, destination), 'x') as archive:
                archive.writestr(members[0], b'wrong')
            return dict(success=True)
        with tempfile.TemporaryDirectory() as root:
            seed(root, 'download/Spiker_Order_Dump.zip')
            with self.assertRaisesRegex(ValueError, 'member bytes/roster'):
                reports.publish(root=root, definition=row(7), variables=VARIABLES,
                                report_bytes=b'correct', archive_writer=wrong)
            self.assertEqual(Path(root,'download/Spiker_Order_Dump.zip').read_bytes(), b'prior')
