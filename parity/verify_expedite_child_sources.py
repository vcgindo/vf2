"""Compare the child-Expedite pure projections with the pinned deployed SQL.

This is a bounded connector proof.  It mutates connection-local temporary
tables only and neither provisions databases nor executes an MTA engine.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.presentation.expedite_child_sources import projections
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha


SOURCE = Path("D:/freshvcf-build/evidence/f3-stage2-git-source-001/PlanningProcessor.decompiled.cs")
SOURCE_SHA = "bf716c4f84e43920b5f2ab302e3d3c78ec685f5d714471c53047d377537d3486"
IL = Path("D:/freshvcf-build/evidence/f3-bpr-wire-source-001/VectorFlowAPIs.il")
IL_SHA = "ccd47dc8d76895a6aa63ad5d6beaadb32f4f53ab75047a68fb8055382fd87ca1"
MODULE = ROOT / "mta/presentation/expedite_child_sources.py"

# PlanningProcessor.ExpediteFromChild, recovered lines 1176-1182 and 1217-1223;
# pinned assembly IL_04b9/IL_04c5-IL_04d6 and IL_062f/IL_063b-IL_064c.
SCALAR_SQL = """SELECT
    remark=(select top(1) request from #OpenExpediteRequests
            where skucode=? and whcode=? and ParentWhCode=?
            order by RequestDate desc),
    intransit=isnull((select lc=OrderNo, cd=CreationDate, slt=SLT,
                             tlt, ag=Ageing, eta=ETA,
                             cl=CurrentLocationCode, qty=InTransitQty,
                             remarks=Remark
                      from #InTransitData
                      where skucode=? and whcode=?
                      for json path, include_null_values),'[]')"""

TIE_SQL = """SELECT TOP(1) request FROM {table}
WHERE skucode=? AND whcode=? AND ParentWhCode=?
ORDER BY RequestDate DESC"""


def _request(parent, request, stamp):
    return dict(SKUCode="SKU-1", WhCode="LOC-1", ParentWhCode=parent,
                Request=request, RequestDate=stamp)


def _transit(**changes):
    row = dict(SKUCode="SKU-1", WhCode="LOC-1", ParentWhCode="PARENT-A",
               OrderNo="ORDER-1", CreationDate="2026-10-06T01:02:03",
               SLT=2, TLT=5, Ageing=7, ETA="2026-10-09T04:05:06",
               CurrentLocationCode="HUB-1", InTransitQty=11, Remark="moving")
    row.update(changes)
    return row


def fixtures():
    duplicate = _transit(OrderNo="DUPLICATE")
    return {
        "parent_scoped_latest": dict(
            requests=[
                _request("PARENT-A", "older-a", "2026-10-01T08:00:00"),
                _request("PARENT-A", "latest-a", "2026-10-02T08:00:00"),
                _request("PARENT-B", "latest-b", "2026-10-03T08:00:00"),
                _request("PARENT-A", "null-date-a", None),
            ], transit=[], lookups=[("SKU-1", "LOC-1", "PARENT-A"),
                                    ("SKU-1", "LOC-1", "PARENT-B")]),
        "duplicate_shipments": dict(
            requests=[], transit=[duplicate, dict(duplicate)],
            lookups=[("SKU-1", "LOC-1", "PARENT-A")]),
        "null_fields_and_dates": dict(
            requests=[], transit=[_transit(
                OrderNo=None, CreationDate=None, SLT=None, TLT=None,
                Ageing=None, ETA=None, CurrentLocationCode=None,
                InTransitQty=None, Remark=None)],
            lookups=[("SKU-1", "LOC-1", "PARENT-A")]),
        "json_string_escaping": dict(
            requests=[], transit=[_transit(
                OrderNo='slash/ quote" backslash\\ tab\t newline\n snowman ☃',
                Remark='remark/"\\\t\nहिन्दी')],
            lookups=[("SKU-1", "LOC-1", "PARENT-A")]),
        "shipment_pair_ignores_parent": dict(
            requests=[], transit=[_transit(OrderNo="PAIR-ONLY")],
            lookups=[("SKU-1", "LOC-1", "PARENT-A"),
                     ("SKU-1", "LOC-1", "OTHER-PARENT")]),
        "absent_pair": dict(
            requests=[], transit=[], lookups=[("MISSING", "NOWHERE", "NONE")]),
    }


def _create_tables(db):
    db.execute("""CREATE TABLE #OpenExpediteRequests(
        SKUCode nvarchar(50) NULL, WhCode nvarchar(50) NULL,
        ParentWhCode nvarchar(50) NULL, Request nvarchar(max) NULL,
        RequestDate datetime2(3) NULL)""")
    db.execute("""CREATE TABLE #InTransitData(
        SKUCode nvarchar(50) NULL, WhCode nvarchar(50) NULL,
        ParentWhCode nvarchar(50) NULL, OrderNo nvarchar(max) NULL,
        CreationDate datetime2(3) NULL, SLT int NULL, TLT int NULL,
        Ageing int NULL, ETA datetime2(3) NULL,
        CurrentLocationCode nvarchar(max) NULL, InTransitQty int NULL,
        Remark nvarchar(max) NULL)""")


def _seed(db, case):
    db.execute("TRUNCATE TABLE #OpenExpediteRequests; TRUNCATE TABLE #InTransitData")
    if case["requests"]:
        db.cursor().executemany(
            "INSERT INTO #OpenExpediteRequests VALUES (?,?,?,?,?)",
            [(r["SKUCode"], r["WhCode"], r["ParentWhCode"], r["Request"],
              r["RequestDate"]) for r in case["requests"]])
    if case["transit"]:
        fields = ("SKUCode", "WhCode", "ParentWhCode", "OrderNo", "CreationDate",
                  "SLT", "TLT", "Ageing", "ETA", "CurrentLocationCode",
                  "InTransitQty", "Remark")
        db.cursor().executemany(
            "INSERT INTO #InTransitData VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [tuple(row[name] for name in fields) for row in case["transit"]])


def _native(db, lookup):
    sku, location, parent = lookup
    row = db.execute(SCALAR_SQL, sku, location, parent, sku, location).fetchone()
    return dict(remark=row[0], intransit=row[1])


def _json_bag(value):
    return Counter(json.dumps(row, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False)
                   for row in json.loads(value))


def _jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def _tie_boundary(db):
    rows = [
        ("SKU-TIE", "LOC-TIE", "PARENT-TIE", "tie-a", "2026-10-05T12:00:00"),
        ("SKU-TIE", "LOC-TIE", "PARENT-TIE", "tie-b", "2026-10-05T12:00:00"),
    ]
    for suffix, direction in (("Asc", "ASC"), ("Desc", "DESC")):
        db.execute(f"""CREATE TABLE #Tie{suffix}(
            SKUCode nvarchar(50), WhCode nvarchar(50), ParentWhCode nvarchar(50),
            Request nvarchar(50), RequestDate datetime2(3));
            CREATE CLUSTERED INDEX IX_Tie{suffix} ON #Tie{suffix}(Request {direction})""")
        db.cursor().executemany(f"INSERT INTO #Tie{suffix} VALUES (?,?,?,?,?)", rows)
    winners = {}
    for suffix in ("Asc", "Desc"):
        winners[suffix.lower()] = db.execute(
            TIE_SQL.format(table="#Tie" + suffix),
            "SKU-TIE", "LOC-TIE", "PARENT-TIE").fetchone()[0]
    modern_error = None
    try:
        projections([dict(SKUCode=r[0], WhCode=r[1], ParentWhCode=r[2],
                          Request=r[3], RequestDate=r[4]) for r in rows], [])
    except Exception as exc:
        modern_error = dict(type=type(exc).__name__, message=str(exc))
    return dict(
        logical_rows=[dict(Request=row[3], RequestDate=row[4]) for row in rows],
        exact_sql=TIE_SQL,
        physical_variants="Same logical request bag; opposite clustered Request order.",
        sql_winners=winners,
        winner_values=sorted(set(winners.values())),
        modern_error=modern_error,
        status="NATIVE_TOP1_TIE_NONDETERMINISTIC_MODERN_DENIED",
    )


def _source_check():
    if file_sha(SOURCE) != SOURCE_SHA:
        raise ValueError("Pinned PlanningProcessor source hash changed")
    if file_sha(IL) != IL_SHA:
        raise ValueError("Pinned deployed assembly IL hash changed")
    source = SOURCE.read_text(encoding="utf-8-sig")
    fragments = (
        "remark=(select top(1)request from [OpenExpediteRequests] where skucode=a.skucode and whcode=a.whcode and ParentWhCode=a.ParentWhCode order by RequestDate desc)",
        "select lc=OrderNo, cd=CreationDate, slt=SLT, tlt, ag=Ageing, eta=ETA, cl=CurrentLocationCode, qty=InTransitQty, remarks=Remark",
        "Where skucode=a.skucode and whcode=a.whcode for json path, include_null_values",
    )
    missing = [fragment for fragment in fragments if fragment not in source]
    if missing:
        raise ValueError("Pinned child Expedite fragments absent: " + repr(missing))
    return fragments


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_expedite_child_sources.py EVIDENCE_DIRECTORY")
    target = Path(sys.argv[1])
    expected = Path("D:/freshvcf-build/evidence/daily-publication-3006-20261006-001")
    if target.resolve().parent != expected.resolve() or not target.name.startswith('expedite-child-sources-sql-'):
        raise ValueError("Proof must use its declared exclusive evidence directory")
    fragments = _source_check()
    target.mkdir(parents=True, exist_ok=False)
    result = dict(
        status="FAILED", qualification=(
            "Bounded child-Expedite connector proof only; no engine, retained-day, "
            "API, browser, or whole-report parity."),
        persistent_database_writes=False, database_creation=False,
        provisioning=False, engine_replays=0,
        source=dict(path=str(SOURCE), sha256=SOURCE_SHA,
                    assembly_il_path=str(IL), assembly_il_sha256=IL_SHA,
                    anchors=["decompiled 1176-1182", "decompiled 1217-1223",
                             "IL_04b9/IL_04c5-IL_04d6",
                             "IL_062f/IL_063b-IL_064c"],
                    exact_fragments=list(fragments)),
        module=dict(path=str(MODULE.relative_to(ROOT)), sha256=file_sha(MODULE)),
        sql=dict(scalar=SCALAR_SQL, tie=TIE_SQL), observations={}, comparisons={})
    cases = fixtures()
    (target / "fixtures.json").write_text(
        json.dumps(cases, indent=2, ensure_ascii=False, default=_jsonable), encoding="utf-8")
    failure = None
    try:
        os.environ["VFTEST_PROFILE"] = "fresh"
        with exclusive_replay():
            with connection("VFTEST_BPR") as db:
                result["database"] = db.execute("SELECT DB_NAME()").fetchone()[0]
                result["execution_principal"] = db.execute("SELECT SUSER_SNAME()").fetchone()[0]
                _create_tables(db)
                for name, case in cases.items():
                    _seed(db, case)
                    lookup = projections(case["requests"], case["transit"])
                    observations = []
                    for coordinates in case["lookups"]:
                        native = _native(db, coordinates)
                        modern = lookup(*coordinates)
                        raw_equal = native == modern
                        bag_equal = _json_bag(native["intransit"]) == _json_bag(modern["intransit"])
                        observations.append(dict(coordinates=coordinates, native=native,
                                                 modern=modern, raw_equal=raw_equal,
                                                 parsed_duplicate_bag_equal=bag_equal))
                    result["observations"][name] = observations
                    # Raw equality is the consumer contract.  The bag assertion additionally
                    # diagnoses multiplicity independently of JSON member/row presentation.
                    result["comparisons"][name] = dict(
                        raw_equal=all(item["raw_equal"] for item in observations),
                        parsed_duplicate_bag_equal=all(
                            item["parsed_duplicate_bag_equal"] for item in observations))
                pair = result["observations"]["shipment_pair_ignores_parent"]
                result["comparisons"]["shipment_pair_same_for_both_parents"] = (
                    pair[0]["native"]["intransit"] == pair[1]["native"]["intransit"] ==
                    pair[0]["modern"]["intransit"] == pair[1]["modern"]["intransit"])
                result["tie_boundary"] = _tie_boundary(db)

        required = [comparison["raw_equal"] and comparison["parsed_duplicate_bag_equal"]
                    for comparison in result["comparisons"].values()
                    if isinstance(comparison, dict)]
        required.append(result["comparisons"]["shipment_pair_same_for_both_parents"])
        tie = result["tie_boundary"]
        required.extend((tie["winner_values"] == ["tie-a", "tie-b"],
                         tie["modern_error"] == dict(
                             type="ValueError",
                             message="child_expedite_ambiguous_latest_request")))
        if not all(required):
            failure = "child_expedite_source_projection_mismatch"
            result["error"] = failure
        else:
            result["status"] = "PASS"
    except Exception as exc:
        failure = failure or f"{type(exc).__name__}: {exc}"
        result["error"] = failure
    finally:
        (target / "observations.json").write_text(
            json.dumps(result["observations"], indent=2, ensure_ascii=False), encoding="utf-8")
        result["evidence_files"] = {
            path.name: file_sha(path) for path in target.iterdir() if path.is_file()
        }
        (target / "receipt.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if failure:
        raise AssertionError(failure)
    print(json.dumps(dict(status=result["status"], database=result["database"],
                          cases=list(result["comparisons"]),
                          tie_boundary=result["tie_boundary"]["status"])))


if __name__ == "__main__":
    main()
