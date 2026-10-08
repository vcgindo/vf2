from pathlib import Path
import tempfile
import unittest
import zipfile

from mta.application import operational_io as files
from mta.application.operational_input_archive import archive_clock, MARKER_BYTES


class OperationalIOTests(unittest.TestCase):
    def test_owned_path_denies_escape_and_noncanonical_names(self):
        with tempfile.TemporaryDirectory() as root:
            for name in ('../outside', '/outside', 'C:/outside', 'a\\b', 'a//b', 'a/./b', ''):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    files.owned_path(root, name)

    def test_exclusive_writes_copy_readback_and_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            receipt = files.write_file(root, 'stage/a.csv', b'a\r\n\\N\r\n')
            self.assertEqual(files.verify_file(root, receipt), receipt)
            with self.assertRaises(FileExistsError):
                files.write_file(root, 'stage/a.csv', b'changed')
            copied = files.copy_file(root, 'stage/a.csv', 'download/a.csv')
            self.assertEqual(receipt['sha256'], copied['sha256'])
            with self.assertRaises(ValueError):
                files.copy_file(root, 'stage/a.csv', 'download/a.csv')
            with self.assertRaises(ValueError):
                files.clear_staging(root, 'stage', ['a.csv', 'unowned.csv'])
            self.assertTrue((Path(root) / 'stage/a.csv').exists())
            files.clear_staging(root, 'stage', ['a.csv'])
            self.assertFalse((Path(root) / 'stage').exists())
            (Path(root) / 'download/a.csv').write_bytes(b'drift')
            with self.assertRaises(ValueError):
                files.verify_file(root, copied)

    def test_zip_readback_denies_path_escape(self):
        with tempfile.TemporaryDirectory() as root:
            with zipfile.ZipFile(Path(root) / 'bad.zip', 'w') as archive:
                archive.writestr('../outside', b'data')
            with self.assertRaises(ValueError):
                files.zip_members(root, 'bad.zip')

    def test_frozen_clock_and_native_echo_trailing_space(self):
        clock = archive_clock('2026-06-06')
        self.assertEqual(clock['marker'], '06_06_2026_12_00.txt')
        self.assertEqual(clock['RunDateTime'], '2026-06-06 12:00AM')
        self.assertEqual(clock['clock'].isoformat(), '2026-06-06T00:00:00+05:30')
        self.assertEqual(MARKER_BYTES, b'File creation date stamp present in file name \r\n')


if __name__ == '__main__':
    unittest.main()
