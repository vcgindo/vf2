"""Actual file adapter -> existing receipt walker; database writes are excluded."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'runtime-report-recording-unit-only')
import django
django.setup()

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mta.application import operational_io, runtime_report_files
from mta.runtime import operational_reports
from tests.test_runtime_report_files import row, writer, VARIABLES


class RuntimeReportRecordingTests(unittest.TestCase):
    def test_existing_recorder_registers_only_surviving_plain_or_zip_files(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed), tempfile.TemporaryDirectory() as root:
                payload = b'header\r\nrow\r\n'
                report = dict(row(7), Compression=compressed)
                receipt = runtime_report_files.publish(root=root, definition=report,
                    variables=VARIABLES, report_bytes=payload, archive_writer=writer)
                registered = []
                effect = object()
                def record(actual_effect, *, relative_path, role, archive):
                    self.assertIs(actual_effect, effect)
                    self.assertEqual(role, relative_path.split('/')[0])
                    self.assertEqual(archive, compressed)
                    actual = operational_io.inspect_file(root, relative_path)
                    if archive:
                        members = operational_io.zip_members(root, relative_path)
                        self.assertEqual(members, [dict(ordinal=0,name='Spiker_Order_Dump.csv',
                            sha256=receipt['source_csv']['sha256'],size_bytes=len(payload))])
                    else:
                        self.assertEqual(Path(root, relative_path).read_bytes(), payload)
                    registered.append(actual)
                with patch.object(operational_reports, 'record_file', side_effect=record):
                    operational_reports._record_final_files(effect, receipt)
                extension = 'zip' if compressed else 'csv'
                self.assertEqual([r['relative_path'] for r in registered],
                    ['download/Spiker_Order_Dump.'+extension, 'output/Spiker_Order_Dump.'+extension])
                self.assertEqual(Path(root,'output/Spiker_Order_Dump.csv').exists(), not compressed)
                self.assertNotIn('csv', receipt)
