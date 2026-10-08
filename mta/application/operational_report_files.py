"""Owned report-file lifecycles for the generic Cohort2 wrappers.

Every payload is already formatter-qualified bytes.  Paths are fixed relative
to one explicit owned root.  Archive creation is injected so production can use
``operational_io.archive_files`` with pinned 7-Zip while unit tests exercise the
protocol without claiming native archive proof.
"""
from pathlib import Path
from datetime import date

from mta.application import operational_io as files


SOURCES = {
    "invalid_data": ("Engine/InvalidDataAlert.bat",
            "2f3954b72a5c47f25f160388b9fedad67486106b461781c297e42f6686684d68"),
    "phase_exception": ("Engine/PhaseInPhaseOutException.bat",
            "04b97a15176b2b74ea19fcc76a2e53be5a0f96f8fca431c8b6f6b8146f124d3c"),
    "force_norm": ("Engine/NormChangesRun.bat",
            "1b66cce3e052904bdb55b5c19952b987a264bb045285583be8ec1c9c5d9575b5"),
    "daily_unavailable": ("Engine/DailyDataUnavailabilityAlert.bat",
            "1d21f98e0f1b2b8d2215a17b1a3f44fe61bbbf69d2692bc2b21abd18ed0999bb"),
    "bor": ("Engine/OrderAllocBasedReports.bat",
            "12df6d7a4eba37b4bc56cb03bed12f37d4749483bf19ebb2ceff7336723cf22b"),
    "bpr_exceptions": ("Engine/GenerateBPRExceptionReport.bat",
            "722798af0f50ebec6b15c4d4a07b8e342b8b5ed3a5c2fc18f29e6c1585317b4c"),
    "parent_norm": ("Engine/ValidateParentNorm.bat",
            "afbff90d850afce4247744a87d3ae0c5001ef8ade82d152cbb1e895caa0ea010"),
    "file_size": ("Engine/CheckFileSize.bat",
            "e1ebc3aca43bd84d5baeda460bf3eedc2a460a4d9959e5759782d796f133366e"),
    "upload_roster": ("Engine/GenerateUIUploadLogs.bat",
            "656da66db2a0e7e653b24b66c57765f168a64119fb928074ef76e7c55c222be3"),
    "upload": ("Engine/ExportUIUploadLog.bat",
            "e22099dca963ace3dae23e2cc6ff247eaa4e3c42f5db882aa59646b50aadd847"),
    "dbm_change": ("Engine/SendDBMNormChangeReport.bat",
            "37aad4ea93fb9465f65430183be4fddb874ac5f738d55f2bf8e435b157656cf3"),
    "change_log": ("Engine/GenerateNormChangeLogReport.bat",
            "8d858b9598f8ff9e8285515d27ed358e8eef2fe9713b5b49fa3b8a30f1af4db1"),
    "norm_activation": ("Engine/CheckFlagForNorm0-1-2Reports.bat",
            "9d4d52dd5e101f53f1a315362eb67ee075bc18048a6f1793b72c5fd8cc8cdee7"),
    "norm_report": ("Engine/GenerateNorm0-1-2Report.bat",
            "fcfd8c93659d245c792209c5ae5f58471a8f9754e0f3e1647d09782d8ae2ff47"),
}

UPLOAD_REPORTS = (
    "NMSAddNewSKULocLog", "NMSModifySKULocLog", "NMSRemoveSKULocLog",
    "NMSLocMasterLog", "NMSSKUMasterLog", "NMSSOBMasterLog",
    "NMSMOQMasterLog", "ForceNormChangeUploadLog",
)
NORM_REPORTS = {
    "DBMNormChange": "DBMNormChange",
    "NormChangeLog": "NormChangeLogReport",
    "Norm1_30days": "Norm_1_Report_30Days",
    "Norm2_30days": "Norm_2_Report_30Days",
}


def _payload(value, name):
    if not isinstance(value, bytes):
        raise ValueError("Explicit formatter-qualified bytes required: " + name)
    return value


def _payloads(actual, expected, name):
    if not isinstance(actual, dict) or set(actual) != set(expected):
        raise ValueError("Complete explicit " + name + " payload roster required")
    return {key: _payload(actual[key], key) for key in expected}


def _remove(root, *paths):
    for path in paths:
        files.remove_file(root, path)


def _archive(root, archive_writer, *, staging, member, destination):
    if not callable(archive_writer):
        raise ValueError("Explicit archive writer required")
    receipt = archive_writer(root=root, staging=staging, members=[member],
                             destination=destination)
    actual = files.inspect_file(root, destination)
    return {"writer": receipt, "file": actual}


def bor_report_files(*, root, report_bytes):
    """Replace and retain BOR_OrderAllocation.csv in output and download."""
    payload = _payload(report_bytes, "BOR_OrderAllocation")
    output, download = "output/BOR_OrderAllocation.csv", "download/BOR_OrderAllocation.csv"
    _remove(root, output, download)
    output_receipt = files.write_file(root, output, payload)
    download_receipt = files.copy_file(root, output, download)
    return {"output_csv": output_receipt, "download_csv": download_receipt}


def invalid_data_report_files(*, root, report_bytes, attach_zip, archive_writer):
    """Always create the download ZIP; retain the selected output attachment."""
    payload=_payload(report_bytes,'InvalidDataReport')
    if type(attach_zip) is not bool or not callable(archive_writer):
        raise ValueError('Explicit attachment mode and archive writer required')
    csv='output/InvalidDataReport.csv'; zipped='output/InvalidDataReport.zip'
    download='download/InvalidDataReport.zip'
    _remove(root,csv)
    csv_receipt=files.write_file(root,csv,payload)
    _remove(root,zipped)
    zip_receipt=_archive(root,archive_writer,staging='output',member='InvalidDataReport.csv',destination=zipped)
    _remove(root,download)
    download_receipt=files.copy_file(root,zipped,download)
    _remove(root,csv if attach_zip else zipped)
    return dict(output_csv=None if attach_zip else csv_receipt,
                output_zip=zip_receipt if attach_zip else None,download_zip=download_receipt)


def failed_force_report_files(*, root, business_date, report_bytes):
    """NormChangesRun writes a plain day-of-month CSV, including empty results."""
    payload=_payload(report_bytes,'FailedForceNormChanges')
    if not isinstance(business_date,str) or date.fromisoformat(business_date).isoformat()!=business_date:
        raise ValueError('Canonical business date required')
    path=f'output/{date.fromisoformat(business_date).day:02d}-FailedForceNormChanges.csv'
    _remove(root,path)
    return dict(output_csv=files.write_file(root,path,payload))


def phase_exception_report_files(*, root, exception_count, report_bytes, archive_writer):
    """Preserve the wrapper's append and mismatched download cleanup paths."""
    if type(exception_count) is not int or exception_count<0:
        raise ValueError('Explicit nonnegative phase exception count required')
    if exception_count:
        _payload(report_bytes,'PhaseInPhaseOutExceptionReport')
        if not callable(archive_writer):raise ValueError('Explicit archive writer required')
    elif report_bytes is not None:
        raise ValueError('Zero phase exception branch must not fabricate report bytes')
    csv='output/PhaseInPhaseOutExceptionReport.csv'
    zipped='output/PhaseInPhaseOutExceptionReport.zip'
    download='download/PhaseInPhaseOutExceptionReport.zip'
    _remove(root,zipped,'download/PhaseInPhaseOutExceptionReport.csv')
    if not exception_count:
        # Native zero branch does not delete an old output CSV or download ZIP.
        return dict(output_csv=files.inspect_file(root,csv) if files.owned_path(root,csv).exists() else None,
                    output_zip=None,
                    download_zip=files.inspect_file(root,download) if files.owned_path(root,download).exists() else None)
    prior=files.owned_path(root,csv)
    previous=prior.read_bytes() if prior.exists() else b''
    _remove(root,csv)
    files.write_file(root,csv,previous+report_bytes)
    zip_receipt=_archive(root,archive_writer,staging='output',member=Path(csv).name,destination=zipped)
    _remove(root,csv,download)
    return dict(output_csv=None,output_zip=zip_receipt,
                download_zip=files.copy_file(root,zipped,download))


def unavailable_daily_report_files(*, root, report_bytes, archive_writer):
    """Called only at the actual fullkit-alert wrapper activation point."""
    payload=_payload(report_bytes,'DailyDataUnavailabilityReport')
    if not callable(archive_writer):raise ValueError('Explicit archive writer required')
    csv='output/DailyDataUnavailabilityReport.csv'
    zipped='output/DailyDataUnavailabilityReport.zip'
    download='download/DailyDataUnavailabilityReport.zip'
    _remove(root,csv)
    files.write_file(root,csv,payload)
    _remove(root,zipped)
    zip_receipt=_archive(root,archive_writer,staging='output',member=Path(csv).name,destination=zipped)
    _remove(root,csv,download)
    return dict(output_zip=zip_receipt,download_zip=files.copy_file(root,zipped,download))


def bpr_exception_report_files(*, root, exception_count, report_bytes, archive_writer):
    """Apply the count branch; populated CSV remains in output, ZIP only in download."""
    if type(exception_count) is not int or exception_count < 0:
        raise ValueError("Explicit nonnegative BPRExceptions count required")
    if exception_count == 0:
        if report_bytes is not None:
            raise ValueError("Zero exception branch must not fabricate report bytes")
    else:
        _payload(report_bytes, "BPRExceptionReport")
        if not callable(archive_writer):
            raise ValueError("Explicit archive writer required")
    csv_path, zip_path = "output/BPRExceptionReport.csv", "download/BPRExceptionReport.zip"
    _remove(root, csv_path, zip_path)
    if exception_count == 0:
        return {"exception_count": 0, "output_csv": None, "download_zip": None}
    csv_receipt = files.write_file(root, csv_path, report_bytes)
    zip_receipt = _archive(root, archive_writer, staging="output", member="BPRExceptionReport.csv",
                           destination=zip_path)
    return {"exception_count": exception_count, "output_csv": csv_receipt,
            "download_zip": zip_receipt}


def no_norm_parent_report_files(*, root, report_bytes, archive_writer):
    """Branch on literal CSV byte size, including a nonempty header-only report."""
    payload = _payload(report_bytes, "NoNormParentReport")
    csv_path = "output/NoNormParentReport.csv"
    output_zip = "output/NoNormParentReport.zip"
    download_zip = "download/NoNormParentReport.zip"
    if len(payload) and not callable(archive_writer):
        raise ValueError("Explicit archive writer required")
    _remove(root, output_zip, download_zip, csv_path)
    csv_receipt = files.write_file(root, csv_path, payload)
    size = files.inspect_file(root, csv_path)["size_bytes"]
    if size == 0:
        return {"file_size": 0, "output_csv": csv_receipt,
                "output_zip": None, "download_zip": None}
    archive_receipt = _archive(root, archive_writer, staging="output", member="NoNormParentReport.csv",
                               destination=output_zip)
    # Canonical deletion is conditional on the output ZIP existing.
    files.remove_file(root, csv_path)
    download_receipt = files.copy_file(root, output_zip, download_zip)
    return {"file_size": size, "output_csv": None, "output_zip": archive_receipt,
            "download_zip": download_receipt}


def upload_log_report_files(*, root, payloads, archive_writer, client_folder):
    """Create all eight output/download ZIPs and optional owned client copies."""
    qualified = _payloads(payloads, UPLOAD_REPORTS, "UI upload-log")
    if not callable(archive_writer):
        raise ValueError("Explicit archive writer required")
    if client_folder is not None:
        client = files.owned_path(root, client_folder)
        if not client.is_dir():
            raise ValueError("Optional client folder must already exist inside owned root")
    result = {}
    for report in UPLOAD_REPORTS:
        csv_name, zip_name = report + ".csv", report + ".zip"
        csv_path = "output/UIUploadLogs/" + csv_name
        output_zip = "output/UIUploadLogs/" + zip_name
        download_zip = "download/UIUploadLogs/" + zip_name
        _remove(root, output_zip, csv_path)
        csv_receipt = files.write_file(root, csv_path, qualified[report])
        archive_receipt = _archive(root, archive_writer, staging="output/UIUploadLogs", member=csv_name,
                                   destination=output_zip)
        files.remove_file(root, csv_path)
        _remove(root, download_zip)
        download_receipt = files.copy_file(root, output_zip, download_zip)
        client_receipt = None
        if client_folder is not None:
            client_path = client_folder + "/" + zip_name
            _remove(root, client_path)
            client_receipt = files.copy_file(root, download_zip, client_path)
        result[report] = {"source_csv": csv_receipt, "output_zip": archive_receipt,
                          "download_zip": download_receipt, "client_zip": client_receipt}
    return result


def norm_report_files(*, root, payloads, archive_writer):
    """Apply the four enabled generic O6 file lifecycles; Norm0 is unsupported."""
    if isinstance(payloads, dict) and any(name.casefold().startswith("norm0") or
            name.casefold().startswith("norm_0") for name in payloads):
        raise ValueError("Norm0 file export is inactive in the generic profile")
    qualified = _payloads(payloads, NORM_REPORTS, "enabled O6 report")
    if not callable(archive_writer):
        raise ValueError("Explicit archive writer required")
    result = {}
    for key, base in NORM_REPORTS.items():
        csv_name, zip_name = base + ".csv", base + ".zip"
        csv_path, download_zip = "output/" + csv_name, "download/" + zip_name
        if key == "DBMNormChange":
            output_zip = "output/" + zip_name
            _remove(root, output_zip, download_zip, csv_path)
            source_receipt = files.write_file(root, csv_path, qualified[key])
            archive_receipt = _archive(root, archive_writer, staging="output", member=csv_name,
                                       destination=output_zip)
            files.remove_file(root, csv_path)
            download_receipt = files.copy_file(root, output_zip, download_zip)
            result[key] = {"source_csv": source_receipt, "output_csv": None,
                           "output_zip": archive_receipt, "download_zip": download_receipt}
        else:
            _remove(root, csv_path, download_zip)
            csv_receipt = files.write_file(root, csv_path, qualified[key])
            archive_receipt = _archive(root, archive_writer, staging="output", member=csv_name,
                                       destination=download_zip)
            result[key] = {"output_csv": csv_receipt, "output_zip": None,
                           "download_zip": archive_receipt}
    return result
