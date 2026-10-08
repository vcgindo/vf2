from pathlib import Path
import tempfile
import unittest
import zipfile

from mta.application import operational_io as files
from mta.application.operational_report_files import (
    NORM_REPORTS, SOURCES, UPLOAD_REPORTS, bor_report_files,
    bpr_exception_report_files, no_norm_parent_report_files,
    norm_report_files, upload_log_report_files,
    invalid_data_report_files,failed_force_report_files,phase_exception_report_files,
    unavailable_daily_report_files,
)


def archive_writer(*, root, staging, members, destination):
    stage = files.owned_path(root, staging)
    target = files.owned_path(root, destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError("archive destination exists")
    with zipfile.ZipFile(target, "x") as archive:
        for member in members:
            source = stage / member
            if not source.is_file():
                raise ValueError("missing member")
            archive.write(source, arcname=Path(member).name)
    return {"unit_protocol_writer": True, "members": list(members)}


def present(root, relative):
    return files.owned_path(root, relative).is_file()


class OperationalReportFileTests(unittest.TestCase):
    def test_invalid_data_attachment_choice_preserves_download_zip(self):
        for zipped in (False,True):
            with self.subTest(zipped=zipped),tempfile.TemporaryDirectory() as root:
                payload=b'SKUCode,WarehouseCode,RunDatetime,ReasonDescription\r\n'
                result=invalid_data_report_files(root=root,report_bytes=payload,
                    attach_zip=zipped,archive_writer=archive_writer)
                self.assertTrue(present(root,'download/InvalidDataReport.zip'))
                self.assertEqual(present(root,'output/InvalidDataReport.csv'),not zipped)
                self.assertEqual(present(root,'output/InvalidDataReport.zip'),zipped)
                with zipfile.ZipFile(Path(root,'download/InvalidDataReport.zip')) as archive:
                    self.assertEqual(archive.namelist(),['InvalidDataReport.csv'])
                    self.assertEqual(archive.read('InvalidDataReport.csv'),payload)
                self.assertEqual(result['output_csv'] is None,zipped)

    def test_phase_empty_preserves_native_stale_paths_then_positive_appends(self):
        with tempfile.TemporaryDirectory() as root:
            for path,value in (('output/PhaseInPhaseOutExceptionReport.csv',b'prior\r\n'),
                    ('output/PhaseInPhaseOutExceptionReport.zip',b'old-output-zip'),
                    ('download/PhaseInPhaseOutExceptionReport.csv',b'old-download-csv'),
                    ('download/PhaseInPhaseOutExceptionReport.zip',b'old-download-zip')):
                files.write_file(root,path,value)
            phase_exception_report_files(root=root,exception_count=0,report_bytes=None,archive_writer=None)
            self.assertFalse(present(root,'output/PhaseInPhaseOutExceptionReport.zip'))
            self.assertFalse(present(root,'download/PhaseInPhaseOutExceptionReport.csv'))
            self.assertEqual(Path(root,'download/PhaseInPhaseOutExceptionReport.zip').read_bytes(),b'old-download-zip')
            phase_exception_report_files(root=root,exception_count=1,report_bytes=b'new\r\n',archive_writer=archive_writer)
            self.assertFalse(present(root,'output/PhaseInPhaseOutExceptionReport.csv'))
            with zipfile.ZipFile(Path(root,'download/PhaseInPhaseOutExceptionReport.zip')) as archive:
                self.assertEqual(archive.namelist(),['PhaseInPhaseOutExceptionReport.csv'])
                self.assertEqual(archive.read('PhaseInPhaseOutExceptionReport.csv'),b'prior\r\nnew\r\n')

    def test_failed_force_plain_day_file_and_fullkit_zip_lifecycles(self):
        with tempfile.TemporaryDirectory() as root:
            files.write_file(root,'output/06-FailedForceNormChanges.csv',b'old')
            result=failed_force_report_files(root=root,business_date='2026-06-06',report_bytes=b'header\r\n')
            self.assertEqual(result['output_csv']['relative_path'],'output/06-FailedForceNormChanges.csv')
            self.assertEqual(Path(root,'output/06-FailedForceNormChanges.csv').read_bytes(),b'header\r\n')
            unavailable_daily_report_files(root=root,report_bytes=b'reasons\r\n',archive_writer=archive_writer)
            self.assertFalse(present(root,'output/DailyDataUnavailabilityReport.csv'))
            self.assertTrue(present(root,'output/DailyDataUnavailabilityReport.zip'))
            with zipfile.ZipFile(Path(root,'download/DailyDataUnavailabilityReport.zip')) as archive:
                self.assertEqual(archive.read('DailyDataUnavailabilityReport.csv'),b'reasons\r\n')

    def test_source_wrapper_pins_and_bor_output_download_replacement(self):
        self.assertEqual({len(pin) for _, pin in SOURCES.values()}, {64})
        with tempfile.TemporaryDirectory() as root:
            Path(root, "output").mkdir(); Path(root, "download").mkdir()
            Path(root, "output/BOR_OrderAllocation.csv").write_bytes(b"old")
            Path(root, "download/BOR_OrderAllocation.csv").write_bytes(b"old")
            result = bor_report_files(root=root, report_bytes=b"bor\r\n")
            self.assertEqual(Path(root, "output/BOR_OrderAllocation.csv").read_bytes(), b"bor\r\n")
            self.assertEqual(Path(root, "download/BOR_OrderAllocation.csv").read_bytes(), b"bor\r\n")
            self.assertEqual(result["output_csv"]["sha256"], result["download_csv"]["sha256"])

    def test_bpr_exception_count_branches_and_csv_retention(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "output").mkdir(); Path(root, "download").mkdir()
            Path(root, "output/BPRExceptionReport.csv").write_bytes(b"old")
            Path(root, "download/BPRExceptionReport.zip").write_bytes(b"old")
            empty = bpr_exception_report_files(root=root, exception_count=0,
                report_bytes=None, archive_writer=None)
            self.assertEqual(empty["exception_count"], 0)
            self.assertFalse(present(root, "output/BPRExceptionReport.csv"))
            self.assertFalse(present(root, "download/BPRExceptionReport.zip"))
            populated = bpr_exception_report_files(root=root, exception_count=2,
                report_bytes=b"exceptions", archive_writer=archive_writer)
            self.assertTrue(present(root, "output/BPRExceptionReport.csv"))
            self.assertTrue(present(root, "download/BPRExceptionReport.zip"))
            self.assertFalse(present(root, "output/BPRExceptionReport.zip"))
            self.assertEqual(populated["exception_count"], 2)
            with self.assertRaisesRegex(ValueError, "must not fabricate"):
                bpr_exception_report_files(root=root, exception_count=0,
                    report_bytes=b"", archive_writer=archive_writer)

    def test_parent_norm_uses_literal_byte_size_including_header_only(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "output").mkdir(); Path(root, "download").mkdir()
            empty = no_norm_parent_report_files(root=root, report_bytes=b"", archive_writer=None)
            self.assertEqual(empty["file_size"], 0)
            self.assertTrue(present(root, "output/NoNormParentReport.csv"))
            self.assertFalse(present(root, "output/NoNormParentReport.zip"))
            header = b"SKUCode,WhCode,Norm,ParentWhCode\r\n"
            result = no_norm_parent_report_files(root=root, report_bytes=header,
                                                  archive_writer=archive_writer)
            self.assertEqual(result["file_size"], len(header))
            self.assertFalse(present(root, "output/NoNormParentReport.csv"))
            self.assertTrue(present(root, "output/NoNormParentReport.zip"))
            self.assertTrue(present(root, "download/NoNormParentReport.zip"))

    def test_all_upload_logs_have_output_download_and_optional_client_zips(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "output/UIUploadLogs").mkdir(parents=True)
            Path(root, "download/UIUploadLogs").mkdir(parents=True)
            Path(root, "client").mkdir()
            payloads = {name: (name + "\r\n").encode() for name in UPLOAD_REPORTS}
            result = upload_log_report_files(root=root, payloads=payloads,
                archive_writer=archive_writer, client_folder="client")
            self.assertEqual(tuple(result), UPLOAD_REPORTS)
            for name in UPLOAD_REPORTS:
                self.assertFalse(present(root, "output/UIUploadLogs/" + name + ".csv"))
                self.assertTrue(present(root, "output/UIUploadLogs/" + name + ".zip"))
                self.assertTrue(present(root, "download/UIUploadLogs/" + name + ".zip"))
                self.assertTrue(present(root, "client/" + name + ".zip"))
            with self.assertRaisesRegex(ValueError, "Complete explicit"):
                upload_log_report_files(root=root, payloads={}, archive_writer=archive_writer,
                                        client_folder=None)

    def test_o6_distinct_lifecycles_and_inactive_norm0_rejection(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "output").mkdir(); Path(root, "download").mkdir()
            payloads = {name: name.encode() for name in NORM_REPORTS}
            result = norm_report_files(root=root, payloads=payloads,
                                       archive_writer=archive_writer)
            self.assertFalse(present(root, "output/DBMNormChange.csv"))
            self.assertTrue(present(root, "output/DBMNormChange.zip"))
            self.assertTrue(present(root, "download/DBMNormChange.zip"))
            for key, base in NORM_REPORTS.items():
                if key == "DBMNormChange":
                    continue
                self.assertTrue(present(root, "output/" + base + ".csv"))
                self.assertFalse(present(root, "output/" + base + ".zip"))
                self.assertTrue(present(root, "download/" + base + ".zip"))
            self.assertEqual(set(result), set(NORM_REPORTS))
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "Norm0 file export is inactive"):
                norm_report_files(root=root, payloads={"Norm0_30days": b"x"},
                                  archive_writer=archive_writer)

    def test_archive_failure_is_reported_without_fabricated_success(self):
        def failing(**_):
            raise RuntimeError("archive failed")
        with tempfile.TemporaryDirectory() as root:
            Path(root, "output").mkdir(); Path(root, "download").mkdir()
            with self.assertRaisesRegex(RuntimeError, "archive failed"):
                bpr_exception_report_files(root=root, exception_count=1,
                    report_bytes=b"qualified", archive_writer=failing)
            self.assertTrue(present(root, "output/BPRExceptionReport.csv"))
            self.assertFalse(present(root, "download/BPRExceptionReport.zip"))


if __name__ == "__main__":
    unittest.main()
