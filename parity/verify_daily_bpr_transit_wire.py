"""Prove the accepted day-one BPR nested transit wire against deployed SQL.

The owned PostgreSQL read is forced transaction-read-only.  Canonical SQL runs
only against connection-local SQL Server temporary tables.  No service route,
engine, or persistent database population is invoked.
"""
from __future__ import annotations

from datetime import date
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vectorflow.settings")
os.environ.setdefault("VF_SECRET_KEY", "bounded-read-only-proof")
import django
django.setup()

from mta.presentation.bpr_response import response_row, transit_json
from mta.presentation.rrr import index, sql_key
from parity import bpr_queries
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.verify_rrr_consumer import temp_rows


RUN_ID = "63c71fa7-944d-4547-a80f-2316a580d3c7"
OUTPUT_DIGEST = "f14806c1397661e2380ae59282db86bd1b5ca629351a61e73a3b09a407a2388b"
EXPORT = Path(
    "D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/"
    "smoke-day1-transit-source-001.json"
)
EXPORT_SHA256 = "b47b7c0716da382347794843f6b4120786e4a70f0df6dc84e237d709e5480106"
IL = Path("D:/freshvcf-build/evidence/f3-bpr-wire-source-001/VectorFlowAPIs.il")
IL_SHA256 = "ccd47dc8d76895a6aa63ad5d6beaadb32f4f53ab75047a68fb8055382fd87ca1"
EMPTY_RECEIPT = Path("D:/freshvcf-build/evidence/f3-bpr-terminal-003/legacy.json.gz")
EMPTY_RECEIPT_SHA256 = "0e8677fce2877501db95a2bac4360df7b280f049ca2cf6a2aa344dd18d3f368b"
COMPOSE = Path("D:/freshvcf-build/daily-3006/compose.json")
FIELDS = ("lc", "cd", "slt", "tlt", "ag", "eta", "cl", "qty",
          "exeecocolor", "remarks")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_sql():
    # bpr_queries extracts getBPRSelectQuery from the pinned matched decompile
    # and changes table bindings only.  Retain its nested scalar byte-for-byte,
    # replacing only the outer-row values with bound parameters.
    query = bpr_queries.queries("", page=1, size=1)["grid"]
    lower = query.lower()
    start = lower.index("intransit=(select")
    marker = "include_null_values )"
    end = lower.index(marker, start) + len(marker)
    fragment = query[start:end]
    expected = (
        "intransit=(select lc=OrderNo, cd=CreationDate, slt=SLT, tlt, "
        "ag=Ageing, eta=ETA, cl=CurrentLocationCode, qty=InTransitQty,"
        "exeecocolor=a.EcoColor, remarks=Remark  from  #Transit Where "
        "skucode=a.skucode and whcode=a.whcode for json path, include_null_values )"
    )
    _require(fragment == expected, "Pinned BPR nested transit SQL changed")
    bound = fragment.replace("a.EcoColor", "?").replace(
        "a.skucode", "?").replace("a.whcode", "?")
    _require(bound.count("?") == 3, "BPR nested transit bind shape differs")
    return "SELECT " + bound, fragment


def _project_rows():
    code = f"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django,json
django.setup()
from django.conf import settings
settings.DATABASES['default']['OPTIONS']['options'] += ' -c default_transaction_read_only=on -c statement_timeout=30000'
from django.db import connection
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
run=CalculationRun.objects.get(pk={RUN_ID!r})
with connection.cursor() as cursor:
 cursor.execute("SELECT current_database(), current_setting('transaction_read_only')")
 database,read_only=cursor.fetchone()
output=read_outputs(run)
rows=output['BPRReports'][0]['BPR_Table']
print(json.dumps({{'database':database,'transaction_read_only':read_only,
 'run_id':str(run.pk),'output_digest':run.output_digest,
 'rows':[{{'SKUCode':row['SKUCode'],'WhCode':row['WhCode'],
           'EcoColor':row['EcoColor']}} for row in rows]}}))
"""
    command = [
        "docker", "compose", "-f", str(COMPOSE), "run", "--rm", "--no-deps", "-T",
        "-v", str(ROOT / "mta") + ":/app/mta:ro",
        "-v", str(ROOT / "vectorflow") + ":/app/vectorflow:ro",
        "--entrypoint", "python", "mta", "-c", code,
    ]
    completed = subprocess.run(command, text=True, encoding="utf-8",
                               capture_output=True, timeout=60)
    if completed.returncode:
        raise RuntimeError("Owned3006 project-row read failed: " + completed.stderr[-1000:])
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    _require(lines, "Owned3006 project-row read returned no data")
    value = json.loads(lines[-1])
    _require(value["database"] == "daily_3006"
             and value["transaction_read_only"] == "on",
             "Owned3006 project-row read was not transaction-read-only")
    _require(value["run_id"] == RUN_ID and value["output_digest"] == OUTPUT_DIGEST,
             "Owned3006 project-row identity differs")
    _require(len(value["rows"]) == 10, "Owned3006 BPR project population differs")
    keys = [sql_key(row["SKUCode"], row["WhCode"]) for row in value["rows"]]
    _require(len(set(keys)) == len(keys), "Owned3006 BPR project pair is duplicated")
    return value


def _transit_rows(payload):
    result = []
    for source in payload["published"]["validated"]:
        row = dict(source)
        for field in ("CreationDate", "GateOutDate", "ETA", "ReportDate"):
            if row[field] is not None:
                row[field] = date.fromisoformat(row[field])
        result.append(row)
    return result


def _retained_empty_boundary():
    _require(_sha(EMPTY_RECEIPT) == EMPTY_RECEIPT_SHA256,
             "Retained canonical BPR empty-wire receipt changed")
    cases = json.loads(gzip.decompress(EMPTY_RECEIPT.read_bytes()))
    values = [row["intransit"] for case in cases for row in case["rows"]]
    _require(values and all(value == {"type": "null", "value": None}
                            for value in values),
             "Retained canonical BPR empty-wire scalar differs")
    return {"path": str(EMPTY_RECEIPT), "sha256": EMPTY_RECEIPT_SHA256,
            "cases": len(cases), "rows": len(values),
            "raw_scalar": {"type": "null", "value": None},
            "deployed_wire_after_ToString": ""}


def _projection(rows, eco):
    return [{
        "lc": row["OrderNo"], "cd": row["CreationDate"].isoformat()
              if row["CreationDate"] is not None else None,
        "slt": row["SLT"], "tlt": row["TLT"], "ag": row["Ageing"],
        "eta": row["ETA"].isoformat() if row["ETA"] is not None else None,
        "cl": row["CurrentLocationCode"], "qty": row["InTransitQty"],
        "exeecocolor": eco, "remarks": row["Remark"],
    } for row in rows]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_daily_bpr_transit_wire.py EVIDENCE_DIRECTORY")
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    receipt = {
        "status": "FAILED",
        "qualification": (
            "Accepted day-one BPR nested-transit wire only; PostgreSQL read-only "
            "and SQL Server connection-local temporary tables only."
        ),
        "persistent_database_writes": False,
        "engine_replays": 0,
    }
    failure = None
    try:
        _require(_sha(EXPORT) == EXPORT_SHA256, "Run transit export identity differs")
        _require(_sha(IL) == IL_SHA256, "Pinned deployed assembly IL changed")
        payload = json.loads(EXPORT.read_bytes())
        retained_empty = _retained_empty_boundary()
        _require(payload["run_id"] == RUN_ID
                 and payload["output_digest"] == OUTPUT_DIGEST,
                 "Run transit export binding differs")
        _require(payload["business_date"] == "2026-06-06",
                 "Run transit business date differs")
        transit = _transit_rows(payload)
        _require(len(transit) == 15, "Accepted day-one transit population differs")
        projects = _project_rows()
        (target / "project-rows.json").write_text(
            json.dumps(projects, indent=2), encoding="utf-8"
        )
        sql, source_fragment = _canonical_sql()
        (target / "nested-transit.sql").write_text(sql, encoding="utf-8")
        grouped = index(transit, "SKUCode", "WhCode")
        observations = []
        os.environ["VFTEST_PROFILE"] = "fresh"
        with exclusive_replay():
            with connection("VFTEST_BPR") as db:
                database = db.execute("SELECT DB_NAME()").fetchone()[0]
                temp_rows(db, "#Transit", "VFTEST_Importer.dbo.InTransitData", transit)
                for project in projects["rows"]:
                    key = sql_key(project["SKUCode"], project["WhCode"])
                    projected = _projection(grouped.get(key, []), project["EcoColor"])
                    native = db.execute(sql, project["EcoColor"],
                                        project["SKUCode"], project["WhCode"]).fetchone()[0]
                    serializer = transit_json(projected)
                    full_wire = response_row(
                        {"intransit": projected}, daily_transit=True
                    )["intransit"]
                    observations.append({
                        "SKUCode": project["SKUCode"], "WhCode": project["WhCode"],
                        "EcoColor": project["EcoColor"], "occurrences": len(projected),
                        "native": native, "serializer": serializer,
                        "full_wire": full_wire,
                        "raw_equal": native == serializer == full_wire,
                        "parsed_equal": json.loads(native) == projected,
                    })
                empty_native = db.execute(
                    sql, "White", "__MISSING_SKU__", "__MISSING_WH__"
                ).fetchone()[0]
        empty = {
            "native": empty_native,
            "native_scalar_type": "null" if empty_native is None else "text",
            # StreamResults applies DBNull.ToString()/ToString to this
            # non-number column.  The retained terminal receipt independently
            # establishes a NULL scalar for empty correlated populations.
            "expected_wire": "" if empty_native is None else str(empty_native),
            "full_wire_from_readmodel_none": response_row(
                {"intransit": None}, daily_transit=True
            )["intransit"],
        }
        empty["full_wire_equal"] = (
            empty["expected_wire"] == empty["full_wire_from_readmodel_none"]
        )
        (target / "observations.json").write_text(
            json.dumps({"positive": observations, "empty": empty}, indent=2,
                       ensure_ascii=False), encoding="utf-8"
        )
        positive = all(row["raw_equal"] and row["parsed_equal"]
                       for row in observations)
        receipt.update(
            database=database,
            run={"id": RUN_ID, "output_digest": OUTPUT_DIGEST,
                 "business_date": payload["business_date"]},
            inputs={"export": {"path": str(EXPORT), "sha256": EXPORT_SHA256},
                    "project_rows_digest": hashlib.sha256(json.dumps(
                        projects["rows"], sort_keys=True, separators=(",", ":")
                    ).encode()).hexdigest()},
            source={"decompiled": {"path": str(bpr_queries.SOURCE),
                                    "sha256": bpr_queries.SOURCE_SHA},
                    "assembly_il": {"path": str(IL), "sha256": IL_SHA256},
                    "retained_empty_boundary": retained_empty,
                    "anchor": "getBPRSelectQuery decompiled line416; IL96037-96040",
                    "exact_fragment": source_fragment},
            serializer={"module": "mta/presentation/bpr_response.py",
                        "sha256": file_sha(ROOT / "mta/presentation/bpr_response.py"),
                        "field_order": list(FIELDS),
                        "encoding": "compact UTF-8 JSON; ensure_ascii=False; solidus escaped"},
            counts={"projects": len(projects["rows"]), "transit": len(transit),
                    "positive_projects": sum(row["occurrences"] > 0 for row in observations),
                    "nested_occurrences": sum(row["occurrences"] for row in observations)},
            positive_rows_equal=positive,
            empty=empty,
            first_difference=(None if positive and empty["full_wire_equal"]
                              else "empty_readmodel_none_wire" if positive
                              else next(row for row in observations if not row["raw_equal"])),
        )
        if not positive:
            failure = "actual_day1_nested_transit_wire_differs"
        elif not empty["full_wire_equal"]:
            failure = "empty_transit_integration_differs"
        if failure:
            receipt["error"] = failure
        else:
            receipt["status"] = "PASS_ACCEPTED_DAY1_BPR_TRANSIT_WIRE"
    except Exception as error:
        failure = failure or f"{type(error).__name__}: {error}"
        receipt["error"] = failure
    finally:
        receipt["proof_source_sha256"] = file_sha(Path(__file__))
        receipt["evidence_files"] = {
            path.name: file_sha(path) for path in target.iterdir() if path.is_file()
        }
        (target / "receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    if failure:
        raise AssertionError(failure)
    print(json.dumps({"status": receipt["status"], "counts": receipt["counts"]}))


if __name__ == "__main__":
    main()
