"""Run-bound canonical SQL proof for the accepted synthetic day-one transit input.

Only connection-local SQL Server temporary tables are written.  This proof
compares the same exported input against the pure processor, canonical SQL, and
the actual persisted publication without excluding fields or occurrences.
"""
from __future__ import annotations

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
from mta.presentation.daily_shipment_input import load_day
from parity.adapters.legacy.runner import consume
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.verify_daily_transit_sql import (
    SOURCES, TRANSPORTER, VALIDATE, _difference, _read, _rows,
    _transporter_sql, _typed_rows, _validator_sql,
)
from parity.verify_rrr_consumer import temp_rows


EXPORT = Path(
    "D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/"
    "smoke-day1-transit-source-001.json"
)
EXPORT_SHA256 = "b47b7c0716da382347794843f6b4120786e4a70f0df6dc84e237d709e5480106"
BASE = Path(
    "D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/"
    "ten-pair-input-v1.json"
)
BASE_SHA256 = "7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc"
SUPPLEMENT = EXPORT.with_name("ten-pair-shipment-input-v1.json")
SUPPLEMENT_SHA256 = "dee26721ff67a7e09cb70dde849a43976a0132ea71a3a3402705a55b393664ae"
RUN_ID = "63c71fa7-944d-4547-a80f-2316a580d3c7"
INPUT_DIGEST = "b32cfc60920e48f4952e2f952ab5458592c77b56927457aadc5bc094a816bd67"
OUTPUT_DIGEST = "f14806c1397661e2380ae59282db86bd1b5ca629351a61e73a3b09a407a2388b"
BUSINESS_DATE = date(2026, 6, 6)
RUN_TIMESTAMP = datetime(2026, 6, 6, 0, 0, 0)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _dates(rows, names):
    return [{name: (date.fromisoformat(value) if name in names and value is not None
                    else value) for name, value in row.items()} for row in rows]


def _published_validator(rows):
    return _dates(rows, {"CreationDate", "GateOutDate", "ETA", "ReportDate"})


def _published_transporter(rows):
    result = _dates(rows, {"CreationDate", "ETA"})
    for row in result:
        for name in ("PhysicalInventoryPen",):
            if row[name] is not None:
                row[name] = Decimal(row[name])
    return result


def _validator_inputs(payload):
    raw = _dates(payload["shipment"]["rows"],
                 {"CreationDate", "GateOutDate", "ReportDate"})
    standards = []
    for source in payload["sources"]["standards"]:
        row = dict(source)
        if row.get("Price") is not None:
            row["Price"] = Decimal(row["Price"])
        standards.append(row)
    return raw, standards


def _rationed(payload):
    rows = []
    for source in payload["sources"]["rationed"]:
        rows.append({
            "SKUCode": source["SKUCode"], "WhCode": source["WhCode"],
            "ParentWhCode": source["ParentWhCode"], "GIT": source["GIT"],
            "PhysicalInventoryPen": (None if source["PhysicalInventoryPen"] is None
                                      else Decimal(source["PhysicalInventoryPen"])),
            "PhysicalInventoryColor": source["PhysicalInventoryColor"],
            "DispatchColor": source["DispatchColor"],
        })
    return rows


def _seed_validator(db, raw, standards):
    temp_rows(db, "#VRaw", "VFTEST_Importer.dbo.InTransitDataRaw", raw)
    temp_rows(db, "#VTransit", "VFTEST_Importer.dbo.InTransitData", [])
    temp_rows(db, "#VStandard", "VFTEST_Importer.dbo.SKULocStandardAttributes", standards)
    temp_rows(db, "#VRejected", "VFTEST_Importer.dbo.RejectedMaster", [])
    temp_rows(db, "#VNull", "VFTEST_Intermediate.dbo.NullChecker", [])
    temp_rows(db, "#VLastDate", "VFTEST_Importer.dbo.LastBatchRunTbl",
              [{"LastRunDate": BUSINESS_DATE}])


def _seed_transporter(db, transit, payload, standards):
    temp_rows(db, "#TTransit", "VFTEST_Importer.dbo.InTransitData", transit)
    temp_rows(db, "#TDirectory", "VFTEST_Importer.dbo.TransporterMaster",
              payload["sources"]["directory"])
    db.execute("""CREATE TABLE #TRationed(
        SKUCode nvarchar(50) NOT NULL, WhCode nvarchar(50) NOT NULL,
        ParentWhCode nvarchar(50) NOT NULL, GIT int NOT NULL,
        PhysicalInventoryPen decimal(10,2) NULL,
        PhysicalInventoryColor nvarchar(10) NULL, DispatchColor nvarchar(10) NULL)""")
    reports = _rationed(payload)
    db.cursor().executemany(
        "INSERT INTO #TRationed VALUES (?,?,?,?,?,?,?)",
        [(row["SKUCode"], row["WhCode"], row["ParentWhCode"], row["GIT"],
          row["PhysicalInventoryPen"], row["PhysicalInventoryColor"], row["DispatchColor"])
         for row in reports],
    )
    temp_rows(db, "#TStandard", "VFTEST_Importer.dbo.SKULocStandardAttributes", standards)
    temp_rows(db, "#TSettings", "VFTEST_Importer.dbo.VFSettings",
              payload["sources"]["settings"])
    temp_rows(db, "#TLastDate", "VFTEST_BPR.dbo.LastBatchRunTbl",
              [{"LastRunDate": BUSINESS_DATE}])
    temp_rows(db, "#TTransporter", "VFTEST_BPR.dbo.GoodsInTransitTransporterMaster", [])
    return reports


def _load_export():
    _require(_sha(EXPORT) == EXPORT_SHA256, "Run-bound transit export identity differs")
    _require(_sha(BASE) == BASE_SHA256, "Registered ten-pair base identity differs")
    _require(_sha(SUPPLEMENT) == SUPPLEMENT_SHA256,
             "Registered shipment supplement identity differs")
    payload = json.loads(EXPORT.read_bytes())
    _require(set(payload) == {"business_date", "input_digest", "output_digest",
                              "published", "run_id", "shipment", "sources"},
             "Run-bound transit export shape differs")
    _require(payload["run_id"] == RUN_ID and payload["input_digest"] == INPUT_DIGEST
             and payload["output_digest"] == OUTPUT_DIGEST
             and payload["business_date"] == BUSINESS_DATE.isoformat(),
             "Accepted run identity differs")
    _require(set(payload["sources"]) == {"directory", "rationed", "settings", "standards"}
             and set(payload["published"]) == {"rejections", "transporter", "validated"},
             "Run-bound transit populations differ")
    registered = load_day(SUPPLEMENT, expected_sha256=SUPPLEMENT_SHA256,
                          business_date=BUSINESS_DATE,
                          base_artifact_sha256=BASE_SHA256)
    _require(payload["shipment"] == registered,
             "Exported shipment input differs from the registered supplement")
    _require(len(registered["rows"]) == 15
             and sum(row["InTransitQty"] for row in registered["rows"]) == 448,
             "Day-one shipment occurrence or quantity population differs")
    _require(all(row["SLT"] is None and row["Price"] is None
                 for row in payload["sources"]["standards"]),
             "Produced NULL SLT/Price population differs")
    return payload


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_daily_transit_run.py EVIDENCE_DIRECTORY")
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    result = {
        "status": "FAILED",
        "qualification": (
            "Accepted run-bound day-one canonical transit SQL comparison; "
            "no engine replay or permanent database writes."
        ),
        "persistent_database_writes": False,
        "database_creation": False,
        "engine_replays": 0,
    }
    try:
        payload = _load_export()
        sources = {path: _read(path) for path in SOURCES}
        validator_sql = _validator_sql(sources[VALIDATE]).replace(
            "2026-06-06T02:03:04", RUN_TIMESTAMP.isoformat())
        transporter_sql = _transporter_sql(sources[TRANSPORTER])
        _require(RUN_TIMESTAMP.isoformat() in validator_sql,
                 "Canonical validator timestamp substitution differs")
        (target / "validator.sql").write_text(validator_sql, encoding="utf-8")
        (target / "transporter.sql").write_text(transporter_sql, encoding="utf-8")

        raw, standards = _validator_inputs(payload)
        reports = _rationed(payload)
        settings = [row for row in payload["sources"]["settings"]
                    if row["Parameter"] == "SuperDelayFactor"]
        _require(len(settings) == 1, "Produced SuperDelayFactor population differs")
        factor = Decimal(settings[0]["Value"])
        pure_validator = validate_goods_in_transit(
            raw, standards, BUSINESS_DATE, RUN_TIMESTAMP
        )
        pure_transporter = transporter_master(
            pure_validator["rows"], payload["sources"]["directory"], reports,
            standards, factor,
        )
        published = {
            "validator": _published_validator(payload["published"]["validated"]),
            "diagnostics": payload["published"]["rejections"],
            "transporter": _published_transporter(payload["published"]["transporter"]),
        }

        os.environ["VFTEST_PROFILE"] = "fresh"
        with exclusive_replay():
            with connection("VFTEST_BPR") as db:
                database = db.execute("SELECT DB_NAME()").fetchval()
                _seed_validator(db, raw, standards)
                consume(db.execute(validator_sql))
                canonical_validator = {
                    "rows": _rows(db.execute("SELECT * FROM #VTransit")),
                    "diagnostics": _rows(db.execute("SELECT * FROM #VRejected")),
                }
                _seed_transporter(db, canonical_validator["rows"], payload, standards)
                consume(db.execute(transporter_sql))
                canonical_transporter = _rows(db.execute("SELECT * FROM #TTransporter"))

        differences = {
            "validator_sql_vs_pure": _difference(canonical_validator["rows"],
                                                  pure_validator["rows"]),
            "validator_sql_vs_persisted": _difference(canonical_validator["rows"],
                                                       published["validator"]),
            "diagnostics_sql_vs_pure": _difference(canonical_validator["diagnostics"],
                                                    pure_validator["diagnostics"]),
            "diagnostics_sql_vs_persisted": _difference(canonical_validator["diagnostics"],
                                                         published["diagnostics"]),
            "transporter_sql_vs_pure": _difference(canonical_transporter,
                                                    pure_transporter),
            "transporter_sql_vs_persisted": _difference(canonical_transporter,
                                                         published["transporter"]),
        }
        observations = {
            "canonical": {
                "validator": _typed_rows(canonical_validator["rows"]),
                "diagnostics": _typed_rows(canonical_validator["diagnostics"]),
                "transporter": _typed_rows(canonical_transporter),
            },
            "pure": {
                "validator": _typed_rows(pure_validator["rows"]),
                "diagnostics": _typed_rows(pure_validator["diagnostics"]),
                "transporter": _typed_rows(pure_transporter),
            },
            "persisted": {name: _typed_rows(rows) for name, rows in published.items()},
            "differences": differences,
        }
        (target / "observations.json").write_text(
            json.dumps(observations, indent=2), encoding="utf-8"
        )
        first = next((name for name, delta in differences.items()
                      if delta["missing"] or delta["unexpected"]), None)
        result.update(
            base_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            database=database,
            run={"id": RUN_ID, "business_date": BUSINESS_DATE.isoformat(),
                 "input_digest": INPUT_DIGEST, "output_digest": OUTPUT_DIGEST,
                 "run_timestamp": RUN_TIMESTAMP.isoformat()},
            inputs={"base_artifact": {"path": str(BASE), "sha256": BASE_SHA256},
                    "shipment_supplement": {"path": str(SUPPLEMENT),
                                            "sha256": SUPPLEMENT_SHA256},
                    "run_export": {"path": str(EXPORT), "sha256": EXPORT_SHA256}},
            canonical_sources={str(path): sha for path, sha in SOURCES.items()},
            transformations={
                "validator": (
                    "Existing pinned extractor; identifiers redirected only to #V tables; "
                    "RunDateTime set to accepted run midnight; orchestration bookkeeping omitted."
                ),
                "transporter": (
                    "Existing pinned extractor; identifiers redirected only to #T tables; "
                    "preceding bookkeeping and trailing commented graph SQL omitted."
                ),
            },
            comparison="complete unordered typed bags; duplicates and NULLs preserved",
            counts={"raw": len(raw), "standards": len(standards),
                    "directory": len(payload["sources"]["directory"]),
                    "rationed": len(reports),
                    "validator": len(canonical_validator["rows"]),
                    "diagnostics": len(canonical_validator["diagnostics"]),
                    "transporter": len(canonical_transporter)},
            differences=differences,
            first_difference=first,
        )
        if first is not None:
            raise AssertionError("Accepted daily transit differs at " + first)
        result["status"] = "PASS_ACCEPTED_DAY1_DAILY_TRANSIT_SQL"
        result["proof_source_sha256"] = file_sha(Path(__file__))
        result["file_hashes"] = {
            path.name: file_sha(path) for path in target.iterdir() if path.is_file()
        }
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        (target / "receipt.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
