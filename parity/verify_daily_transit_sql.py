"""Compare the pure daily-transit ports with pinned deployed SQL statements.

The fixtures in this proof are bounded connector contract cases.  They are not
retained shipment facts and do not establish end-to-end application parity.
Only connection-local temporary tables are mutated.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application.daily_transit import transporter_master, validate_goods_in_transit
from parity.adapters.legacy.runner import consume
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.verify_rrr_consumer import temp_rows


VALIDATE = Path("F:/VFlow_Local/local-runtime/mta-engine/Scripts/Importer/ValidateGoodsInTransit.sql")
TRANSPORTER = Path("F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/GoodsInTransitTransporterMaster.sql")
SOURCES = {
    VALIDATE: "6db973f9f72e28fcb6d22d8e9ce2e069708b6f656a7169573680afbd45e81257",
    TRANSPORTER: "79a3a80bd45d989b37ae59d08259c7a39aeda8ef51e2261a722d241cc689a79d",
}


def _read(path):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SOURCES[path]:
        raise ValueError(f"Canonical source hash changed: {path}: {actual}")
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else (
        "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "cp1252")
    return raw.decode(encoding)


def _between(sql, start, end):
    first = sql.index(start)
    last = sql.index(end, first)
    return sql[first:last]


def _validator_sql(source):
    # Preserve the business statements from native lines 20-97.  The preceding
    # ScriptExecutedFlag update and blanket Intermediate database truncations
    # are orchestration bookkeeping, not processor output.  The latter is
    # represented by the owned #VNull table before and after the exact body.
    body = _between(source, "declare @now datetime", "END TRY")
    replacements = (
        ("[$(IntermediateDatabase)].dbo.NullChecker", "#VNull"),
        ("[InTransitDataRaw]", "#VRaw"),
        ("InTransitDataRaw", "#VRaw"),
        ("[InTransitData]", "#VTransit"),
        ("InTransitData", "#VTransit"),
        ("SKULocStandardAttributes", "#VStandard"),
        ("LastBatchRunTbl", "#VLastDate"),
        ("RejectedMaster", "#VRejected"),
        ("$(RunDateTime)", "2026-06-06T02:03:04"),
    )
    for old, new in replacements:
        body = body.replace(old, new)
    if "$(" in body or any(name in body for name in
                            ("InTransitDataRaw", "SKULocStandardAttributes",
                             "LastBatchRunTbl", "RejectedMaster")):
        raise ValueError("Validator extraction left an unresolved source identifier")
    return "TRUNCATE TABLE #VNull; TRUNCATE TABLE #VTransit;\n" + body + "\nTRUNCATE TABLE #VNull;"


def _transporter_sql(source):
    # Preserve native lines 10-98, including statement order.  Extraction starts
    # after the ScriptExecutedFlag bookkeeping and ends before commented graph SQL.
    body = _between(source, "\n\tTruncate table GoodsInTransitTransporterMaster", "--Query for generating graph data")
    body = body.lstrip()
    replacements = (
        ("[$(ImporterDatabase)].dbo.InTransitData", "#TTransit"),
        ("[$(ImporterDatabase)].dbo.TransporterMaster", "#TDirectory"),
        ("[$(ImporterDatabase)].dbo.SKULocStandardAttributes", "#TStandard"),
        ("[$(ImporterDatabase)].dbo.VFSettings", "#TSettings"),
        ("GoodsInTransitTransporterMaster", "#TTransporter"),
        ("vf_RationedReqReport", "#TRationed"),
        ("LastBatchRunTbl", "#TLastDate"),
    )
    for old, new in replacements:
        body = body.replace(old, new)
    if "$(" in body or any(name in body for name in
                            ("GoodsInTransitTransporterMaster", "vf_RationedReqReport",
                             "LastBatchRunTbl")):
        raise ValueError("Transporter extraction left an unresolved source identifier")
    return body


def _raw(**changes):
    row = dict(SKUCode=" A ", ToLocationCode=" L1 ", FromLocationCode="P1",
               CurrentLocationCode=None, LRCode="LR1", OrderNo="O1",
               CreationDate=date(2026, 6, 1), GateOutDate=date(2026, 6, 3),
               InTransitQty=5, TransporterCode="T1", Remark=None,
               ReportDate=date(2026, 6, 6))
    row.update(changes)
    return row


def _transit(sku, wh, parent, lr, order, tlt, slt):
    return dict(SKUCode=sku, WhCode=wh, ParentWhCode=parent,
                CurrentLocationCode=None, LRCode=lr, OrderNo=order,
                CreationDate=date(2026, 6, 1), GateOutDate=date(2026, 6, 2),
                InTransitQty=2, TransporterCode="T1", Ageing=5,
                ETA=date(2026, 6, 3), TLT=tlt, SLT=slt, Remark=None,
                ReportDate=date(2026, 6, 6))


def fixtures():
    raw = [
        _raw(SKUCode=None, ToLocationCode=None, FromLocationCode=None, InTransitQty=-9),
        _raw(),
        _raw(SKUCode="\tA\t", OrderNo="TAB"),
        _raw(SKUCode=None, ToLocationCode="L1", FromLocationCode="P1", OrderNo="PARTIAL"),
        _raw(SKUCode="B", ToLocationCode="L2", FromLocationCode=None,
             InTransitQty=-3, OrderNo="O2"),
    ]
    validator_standards = [
        {"SKUCode": "A", "WhCode": "L1", "SLT": 2},
        {"SKUCode": "A", "WhCode": "L1", "SLT": 3},
        {"SKUCode": "B", "WhCode": "L2", "SLT": None},
    ]
    transit = [
        _transit("A", "P1", "ROOT", "LR-X", "PARENT", 1, 2),
        _transit("A", "L1", "P1", "LR-X", "SUPER", 4, 2),
        _transit("A", "L2", "P1", "LR-Y", "DELAY", 3, 2),
        _transit("A", "L3", "P1", None, "ONTIME", 1, 2),
    ]
    directory = [
        {"TransporterCode": "T1", "TransporterName": "Carrier", "TransporterContact": None},
        {"TransporterCode": "T1", "TransporterName": "Carrier", "TransporterContact": None},
    ]
    reports = [{"SKUCode": row["SKUCode"], "WhCode": row["WhCode"],
                "ParentWhCode": row["ParentWhCode"], "GIT": 1,
                "PhysicalInventoryPen": Decimal("1.25"),
                "PhysicalInventoryColor": "Black", "DispatchColor": "Red"}
               for row in transit]
    transporter_standards = [
        {"SKUCode": "A", "WhCode": wh, "Price": Decimal("12.9")}
        for wh in ("P1", "L1", "L2", "L3")]
    return dict(
        declaration="Bounded connector contract cases; not retained or generated shipment facts.",
        validator=dict(raw=raw, standards=validator_standards,
                       business_date=date(2026, 6, 6),
                       run_timestamp=datetime(2026, 6, 6, 2, 3, 4)),
        transporter=dict(transit=transit, directory=directory, reports=reports,
                         standards=transporter_standards,
                         super_delay_factor=Decimal("1.5")),
    )


def _rows(cursor):
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _typed(value):
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if type(value) is int:
        return {"type": "int", "value": value}
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {"type": "datetime", "value": value.isoformat(timespec="microseconds")}
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    if isinstance(value, str):
        return {"type": "text", "value": value}
    raise TypeError(f"Unsupported proof value {type(value).__name__}")


def _typed_rows(rows):
    return [{name: _typed(value) for name, value in row.items()} for row in rows]


def _bag(rows):
    return Counter(json.dumps(row, sort_keys=True, separators=(",", ":"))
                   for row in _typed_rows(rows))


def _difference(expected, actual):
    left, right = _bag(expected), _bag(actual)
    return dict(missing=list((left - right).elements()), unexpected=list((right - left).elements()))


def _seed_validator(db, case):
    temp_rows(db, "#VRaw", "VFTEST_Importer.dbo.InTransitDataRaw", case["raw"])
    temp_rows(db, "#VTransit", "VFTEST_Importer.dbo.InTransitData", [])
    temp_rows(db, "#VStandard", "VFTEST_Importer.dbo.SKULocStandardAttributes", case["standards"])
    temp_rows(db, "#VRejected", "VFTEST_Importer.dbo.RejectedMaster", [])
    temp_rows(db, "#VNull", "VFTEST_Intermediate.dbo.NullChecker", [])
    temp_rows(db, "#VLastDate", "VFTEST_Importer.dbo.LastBatchRunTbl",
              [{"LastRunDate": case["business_date"]}])


def _seed_transporter(db, case):
    temp_rows(db, "#TTransit", "VFTEST_Importer.dbo.InTransitData", case["transit"])
    temp_rows(db, "#TDirectory", "VFTEST_Importer.dbo.TransporterMaster", case["directory"])
    # The deployed report has many unrelated NOT NULL output columns.  Model the
    # exact seven-column read boundary of this producer with their native types,
    # rather than inventing values for fields the statement never references.
    db.execute("""CREATE TABLE #TRationed(
        SKUCode nvarchar(50) NOT NULL, WhCode nvarchar(50) NOT NULL,
        ParentWhCode nvarchar(50) NOT NULL, GIT int NOT NULL,
        PhysicalInventoryPen decimal(10,2) NULL,
        PhysicalInventoryColor nvarchar(10) NULL, DispatchColor nvarchar(10) NULL)""")
    db.cursor().executemany(
        "INSERT INTO #TRationed VALUES (?,?,?,?,?,?,?)",
        [(row["SKUCode"], row["WhCode"], row["ParentWhCode"], row["GIT"],
          row["PhysicalInventoryPen"], row["PhysicalInventoryColor"], row["DispatchColor"])
         for row in case["reports"]])
    temp_rows(db, "#TStandard", "VFTEST_Importer.dbo.SKULocStandardAttributes", case["standards"])
    temp_rows(db, "#TSettings", "VFTEST_Importer.dbo.VFSettings", [{
        "Parameter": "SuperDelayFactor", "Value": str(case["super_delay_factor"]),
        "Description": "Bounded connector proof value",
    }])
    temp_rows(db, "#TLastDate", "VFTEST_BPR.dbo.LastBatchRunTbl",
              [{"LastRunDate": date(2026, 6, 6)}])
    temp_rows(db, "#TTransporter", "VFTEST_BPR.dbo.GoodsInTransitTransporterMaster", [])


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_daily_transit_sql.py EVIDENCE_DIRECTORY")
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    result = dict(status="FAILED", qualification=(
        "Bounded pure-processor SQL comparison only; no retained shipment, application, or browser parity."),
        persistent_database_writes=False, database_creation=False, engine_replays=0)
    try:
        source_text = {path: _read(path) for path in SOURCES}
        validator_sql = _validator_sql(source_text[VALIDATE])
        transporter_sql = _transporter_sql(source_text[TRANSPORTER])
        cases = fixtures()
        (target / "fixtures.json").write_text(json.dumps(cases, indent=2, default=str), encoding="utf-8")
        (target / "validator.sql").write_text(validator_sql, encoding="utf-8")
        (target / "transporter.sql").write_text(transporter_sql, encoding="utf-8")

        validator_case = cases["validator"]
        transporter_case = cases["transporter"]
        expected_validator = validate_goods_in_transit(
            validator_case["raw"], validator_case["standards"],
            validator_case["business_date"], validator_case["run_timestamp"])
        expected_transporter = transporter_master(
            transporter_case["transit"], transporter_case["directory"],
            transporter_case["reports"], transporter_case["standards"],
            transporter_case["super_delay_factor"])
        os.environ["VFTEST_PROFILE"] = "fresh"
        with exclusive_replay():
            with connection("VFTEST_BPR") as db:
                database = db.execute("SELECT DB_NAME()").fetchval()
                _seed_validator(db, cases["validator"])
                consume(db.execute(validator_sql))
                actual_validator = dict(
                    rows=_rows(db.execute("SELECT * FROM #VTransit")),
                    diagnostics=_rows(db.execute("SELECT * FROM #VRejected")),
                )
                _seed_transporter(db, cases["transporter"])
                consume(db.execute(transporter_sql))
                actual_transporter = _rows(db.execute("SELECT * FROM #TTransporter"))

        differences = {
            "validator_rows": _difference(expected_validator["rows"], actual_validator["rows"]),
            "validator_diagnostics": _difference(expected_validator["diagnostics"], actual_validator["diagnostics"]),
            "transporter_rows": _difference(expected_transporter, actual_transporter),
        }
        observations = dict(
            expected=dict(validator=_typed_rows(expected_validator["rows"]),
                          diagnostics=_typed_rows(expected_validator["diagnostics"]),
                          transporter=_typed_rows(expected_transporter)),
            actual=dict(validator=_typed_rows(actual_validator["rows"]),
                        diagnostics=_typed_rows(actual_validator["diagnostics"]),
                        transporter=_typed_rows(actual_transporter)),
            differences=differences,
        )
        (target / "observations.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
        result.update(
            base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            database=database,
            canonical_sources={str(path): sha for path, sha in SOURCES.items()},
            transformations={
                "validator": [
                    "Extract canonical business statements from declare @now through before END TRY (source lines 20-97).",
                    "Redirect source table identifiers to connection-local #V* tables.",
                    "Substitute the declared RunDateTime fixture literal.",
                    "Omit ScriptExecutedFlag bookkeeping and replace each blanket Intermediate database truncate with TRUNCATE #VNull.",
                ],
                "transporter": [
                    "Extract canonical business statements from target truncate through SKUStatus updates (source lines 10-98).",
                    "Redirect source table identifiers to connection-local #T* tables.",
                    "Omit only preceding ScriptExecutedFlag bookkeeping and trailing commented graph SQL.",
                ],
            },
            comparison="complete unordered typed bags; duplicates preserved",
            counts={
                "validator_expected": len(expected_validator["rows"]),
                "validator_actual": len(actual_validator["rows"]),
                "diagnostics_expected": len(expected_validator["diagnostics"]),
                "diagnostics_actual": len(actual_validator["diagnostics"]),
                "transporter_expected": len(expected_transporter),
                "transporter_actual": len(actual_transporter),
            },
            differences=differences,
        )
        if any(delta[side] for delta in differences.values() for side in ("missing", "unexpected")):
            raise AssertionError("Canonical daily-transit SQL differs from pure processors")
        result["status"] = "PASS_BOUNDED_DAILY_TRANSIT_SQL"
        result["proof_source_sha256"] = file_sha(Path(__file__))
        result["file_hashes"] = {path.name: file_sha(path) for path in target.iterdir() if path.is_file()}
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        (target / "receipt.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
