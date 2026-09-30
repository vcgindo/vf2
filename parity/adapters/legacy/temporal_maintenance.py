"""Execute step-7 SQL with the single approved tempdb maintenance capture."""

import hashlib

import os

from pathlib import Path

LOCAL = Path("F:/VFlow_Local/local-runtime/mta-engine")

DEPLOYED = Path("F:/VFlow_Source_Backup/deployed-demo/MTA/V6")

API = Path("F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll")

API_REF = Path("F:/VFlow_Source_Backup/deployed-demo/MTA/BackEndAPI/VectorFlowAPIs.dll")

BATCH = LOCAL / "Engine/RunCoreDBM.bat"

BATCH_REF = DEPLOYED / "Engine/RunCoreDBM.bat"

SQL = LOCAL / "Scripts/DBM/SuspensionRules/03.1 AcceptedNormsStockType.sql"

SQL_REF = DEPLOYED / "Scripts/DBM/SuspensionRules/03.1 AcceptedNormsStockType.sql"

API_SHA256 = "0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346"

BATCH_SHA256 = "b01193968e3b8ff5bd81b404ddb954f0978e7857eae5aa3acbe73be6d004da17"

BATCH_REF_SHA256 = "1e8429b300e0039a14086a926e961d20c5247bd34b2e45d0c14109227a55389f"

SQL_SHA256 = "80daf002096c427038c2db79c05fca4ed248abdec76b102e63891922bf6c74cc"

MAINTENANCE = b"DBCC SHRINKDATABASE(N'tempdb')"

TABLES = (
    "NormAcceptanceTbl", "DBMMaster", "DailyConsumption",
    "SuspendAcceptedNormsStockType", "SuspendStockType", "LastBatchRunTbl",
)

def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_receipt():
    for path in (API, API_REF):
        if _sha(path) != API_SHA256:
            raise RuntimeError("Selected legacy API/reference hash changed: " + str(path))
    if _sha(BATCH) != BATCH_SHA256 or _sha(BATCH_REF) != BATCH_REF_SHA256:
        raise RuntimeError("Selected/preserved batch source hash changed")
    if _sha(SQL) != SQL_SHA256 or _sha(SQL_REF) != SQL_SHA256:
        raise RuntimeError("Selected/preserved accepted-Norm SQL hash changed")
    original = SQL.read_bytes()
    if original.count(MAINTENANCE) != 1:
        raise RuntimeError("Expected exactly one approved tempdb statement to capture")
    replay = original.replace(
        MAINTENANCE,
        b"-- Approved capture-only omission: shared tempdb maintenance is outside rollback",
    )
    return {
        "selected_api": {"path": str(API), "sha256": API_SHA256},
        "api_reference": {"path": str(API_REF), "sha256": API_SHA256},
        "selected_batch": {"path": str(BATCH), "sha256": BATCH_SHA256},
        "preserved_batch": {"path": str(BATCH_REF), "sha256": BATCH_REF_SHA256,
                            "difference_disposition": "see contract-freeze/batch-differences.json"},
        "selected_sql": {"path": str(SQL), "sha256": SQL_SHA256},
        "preserved_sql": {"path": str(SQL_REF), "sha256": SQL_SHA256},
        "maintenance_capture": {
            "statement": MAINTENANCE.decode("ascii"), "occurrences": 1,
            "handling": "omitted only from isolated oracle execution with explicit user approval",
            "original_sha256": SQL_SHA256,
            "isolated_replay_sql_sha256": hashlib.sha256(replay).hexdigest(),
        },
        "selected_order": "mta-engine RunCoreDBM.bat SUSP3.1",
    }
