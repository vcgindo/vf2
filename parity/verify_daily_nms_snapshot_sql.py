"""Bounded SQL connector proof for the pure NMSCreateSnapshot port.

Only connection-local temporary tables are written.  This does not install an
MDM source, provision a database, execute an engine, or publish a run.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application.daily_nms_snapshot import (
    LOCATION_FIELDS, MASTER_FIELDS, NMS_FIELDS, SKU_FIELDS, SKULOC_FIELDS,
    NmsSnapshotAmbiguity, create_snapshot,
)
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha


SOURCE = Path("F:/VFlow_Local/local-runtime/mta-engine/Scripts/Importer/NMSCreateSnapshot.sql")
SOURCE_SHA = "f306ea8dc185611197d55d5deb7dd8bf5d1ab5523a581577bc0b8f1ec63a47ab"

TABLE_REDIRECTS = (
    ("$(DBMDataBase).dbo.DBMMaster", "#DBMMaster"),
    ("SkuLocAttributeData", "#Pair"), ("SKUDescriptionTbl", "#SkuDesc"),
    ("SiteDescriptionTbl", "#SiteDesc"), ("LocationAttributeData", "#Location"),
    ("SkuAttributeData", "#Sku"), ("NMSAllItems", "#NMS"),
    ("MasterData", "#Master"), ("Exclusions", "#Exclusion"),
)


def _extract_sql(source):
    """Extract the pinned business statements; redirect identifiers only.

    ScriptExecutionFlag logging, PRINT/TRY/CATCH orchestration, and the source
    RETURN cannot run inside a reusable connector batch.  Its NMSActive test is
    represented by an equivalent positive IF wrapper around the untouched
    UPDATE/TRUNCATE/INSERT body.
    """
    start = source.index("\tupdate A set SKUIntroDate=B.SKUIntroDate")
    marker = "\twhere B.NonNMS=0"
    end = source.index(marker, start) + len(marker)
    body = source[start:end]
    for original, temporary in TABLE_REDIRECTS:
        if original not in body:
            raise ValueError("Canonical NMS table identifier absent: " + original)
        body = body.replace(original, temporary)
    if "$(" in body:
        raise ValueError("NMSCreateSnapshot extraction left an unresolved variable")
    return ("IF EXISTS(SELECT 1 FROM #Settings WHERE Parameter='NMSActive' AND Value='1')\n"
            "BEGIN\n" + body + "\nEND")


def _blank(fields, **changes):
    row = dict.fromkeys(fields)
    row.update(changes)
    return row


def fixture():
    master = _blank(MASTER_FIELDS, SKUCode="SKU", WhCode="LOC", Norm=4,
        MinNorm=1, RLT=2, RCP=3, GCP=4, OCP=None, MinOrderCount=5,
        ParentWhCode="PARENT", SKUIntroDate=date(2025, 1, 1))
    null_master = dict(master, SKUCode="NULLSKU", WhCode="NULLLOC", SKUIntroDate=None)
    dbm = [dict(master, SKUIntroDate=date(2026, 1, 1)),
           dict(null_master, SKUIntroDate=date(2026, 2, 1))]
    pair = _blank(SKULOC_FIELDS, SKUCode="SKU", LocCode="LOC", PackSize=6,
        SpikeThreshold=Decimal("1.25"), PSOThreshold=None, FGRMFlag=None,
        StockPercentForRationing=90, NormPercentReservation=10, NonNMS=False,
        **{"c%d" % i: "pair-%d" % i for i in range(1, 16)})
    null_pair = dict(pair, SKUCode="NULLSKU", LocCode="NULLLOC")
    non_nms = dict(pair, NonNMS=True, PackSize=999)
    sku = _blank(SKU_FIELDS, SKUCode="SKU", ElephantOrderCapping=None,
        Weight=Decimal("2.500"), Volume=None,
        **{"SL%d" % i: "sl-%d" % i for i in range(1, 6)},
        **{"c%d" % i: "sku-%d" % i for i in range(1, 16)})
    null_sku = dict(sku, SKUCode="NULLSKU")
    location = _blank(LOCATION_FIELDS, WHCode="LOC", LocationType=None,
        LogisticsLocation="Y", **{"LL%d" % i: "ll-%d" % i for i in range(1, 6)},
        **{"c%d" % i: "loc-%d" % i for i in range(1, 16)})
    null_location = dict(location, WHCode="NULLLOC")
    return dict(master_data=[master, null_master], dbm_master=dbm,
        skuloc_attributes=[pair, non_nms, null_pair],
        sku_descriptions=[{"SKUCode": "SKU", "SKUDescription": "Product"},
                          {"SKUCode": "sku ", "SKUDescription": "Product"},
                          {"SKUCode": "NULLSKU", "SKUDescription": "Null Product"}],
        site_descriptions=[{"WHCode": "LOC", "WHDescription": "Location"},
                           {"WHCode": "NULLLOC", "WHDescription": "Null Location"},
                           {"WHCode": "PARENT", "WHDescription": "Parent"}],
        exclusions=[{"SKUCode": "SKU", "WhCode": "LOC"},
                    {"SKUCode": "sku ", "WhCode": "loc"}],
        sku_attributes=[sku, null_sku],
        location_attributes=[location, null_location])


def _types(fields, groups):
    result = []
    for name in fields:
        kind = next((sql_type for names, sql_type in groups if name in names), "nvarchar(125)")
        result.append("[" + name + "] " + kind + " NULL")
    return ",".join(result)


def _create(db):
    ints = {"Norm", "MinNorm", "RLT", "RCP", "GCP", "OCP", "MinOrderCount",
            "PackSize", "StockPercentForRationing", "NormPercentReservation",
            "ElephantOrderCapping"}
    thresholds = {"SpikeThreshold", "DefaultSpikeThreshold", "PSOThreshold",
                  "DefaultPSOThreshold"}
    measures = {"Weight", "Volume"}
    dates = {"SKUIntroDate"}
    bits = {"NonNMS", "DBMActive"}
    groups = ((ints, "int"), (thresholds, "decimal(10,2)"),
              (measures, "decimal(13,3)"), (dates, "date"), (bits, "bit"))
    definitions = {
        "#Master": MASTER_FIELDS, "#DBMMaster": MASTER_FIELDS,
        "#Pair": SKULOC_FIELDS, "#Sku": SKU_FIELDS,
        "#Location": LOCATION_FIELDS, "#NMS": NMS_FIELDS,
    }
    for table, fields in definitions.items():
        db.execute("CREATE TABLE " + table + "(" + _types(fields, groups) + ")")
    db.execute("CREATE TABLE #SkuDesc(SKUCode nvarchar(50),SKUDescription varchar(125))")
    db.execute("CREATE TABLE #SiteDesc(WHCode nvarchar(50),WHDescription varchar(125))")
    db.execute("CREATE TABLE #Exclusion(SKUCode nvarchar(50),WhCode nvarchar(50))")
    db.execute("CREATE TABLE #Settings(Parameter nvarchar(250),Value nvarchar(max))")


def _insert(db, table, rows):
    if not rows:
        return
    fields = tuple(rows[0])
    if any(tuple(row) != fields for row in rows):
        raise ValueError("Mixed proof row shape")
    columns = ",".join("[" + name + "]" for name in fields)
    db.cursor().executemany("INSERT INTO " + table + "(" + columns + ") VALUES (" +
        ",".join("?" for _ in fields) + ")", [tuple(row[name] for name in fields) for row in rows])


def _seed(db, case):
    for table, key in (("#Master", "master_data"), ("#DBMMaster", "dbm_master"),
            ("#Pair", "skuloc_attributes"), ("#SkuDesc", "sku_descriptions"),
            ("#SiteDesc", "site_descriptions"), ("#Exclusion", "exclusions"),
            ("#Sku", "sku_attributes"), ("#Location", "location_attributes")):
        _insert(db, table, case[key])
    _insert(db, "#Settings", [{"Parameter": "NMSActive", "Value": "1"}])


def _rows(cursor):
    fields = [column[0] for column in cursor.description]
    return [dict(zip(fields, row)) for row in cursor.fetchall()]


def _json(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(type(value).__name__)


def _bag(rows):
    return Counter(json.dumps(row, sort_keys=True, separators=(",", ":"), default=_json)
                   for row in rows)


def _validate_source():
    if file_sha(SOURCE) != SOURCE_SHA:
        raise ValueError("Canonical NMSCreateSnapshot.sql hash changed")
    source = SOURCE.read_text(encoding="utf-8-sig")
    for fragment in ("where A.SKUIntroDate<>B.SKUIntroDate", "Truncate table NMSAllItems",
                     "where B.NonNMS=0", "DBMActive=case when F.SKUCode is null then 1 else 0 end"):
        if fragment not in source:
            raise ValueError("Canonical NMSCreateSnapshot fragment changed: " + fragment)
    return source


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_daily_nms_snapshot_sql.py EVIDENCE_DIRECTORY")
    source = _validate_source()
    core_sql = _extract_sql(source)
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    case = fixture()
    result = dict(status="FAILED", source_sha256=SOURCE_SHA,
        qualification="Bounded connector proof only; no source install, engine, run, or publication.",
        persistent_database_writes=False, database_creation=False, engine_replays=0,
        sql=core_sql, extraction=dict(
            start="update A set SKUIntroDate=B.SKUIntroDate",
            end="where B.NonNMS=0", redirects=list(TABLE_REDIRECTS),
            omitted="ScriptExecutionFlag, PRINT, TRY/CATCH; RETURN gate represented by positive IF"),
        comparisons={})
    failure = None
    try:
        modern = create_snapshot(nms_active=True, **case)
        os.environ["VFTEST_PROFILE"] = "fresh"
        with exclusive_replay():
            with connection("VFTEST_Importer") as db:
                result["database"] = db.execute("SELECT DB_NAME()").fetchone()[0]
                result["principal"] = db.execute("SELECT SUSER_SNAME()").fetchone()[0]
                _create(db); _seed(db, case); db.execute(core_sql)
                native_master = _rows(db.execute("SELECT " + ",".join(MASTER_FIELDS) + " FROM #Master"))
                native_nms = _rows(db.execute("SELECT " + ",".join(NMS_FIELDS) + " FROM #NMS"))
                result["comparisons"]["active_master_bag"] = _bag(native_master) == _bag(modern["MasterData"])
                result["comparisons"]["active_nms_bag"] = _bag(native_nms) == _bag(modern["NMSAllItems"])
                result["counts"] = {"native": len(native_nms), "modern": len(modern["NMSAllItems"])}
                db.execute("UPDATE #Settings SET Value='0'; DELETE FROM #DBMMaster")
                before_master, before_nms = list(native_master), list(native_nms)
                db.execute(core_sql)
                gated_master = _rows(db.execute("SELECT " + ",".join(MASTER_FIELDS) + " FROM #Master"))
                gated_nms = _rows(db.execute("SELECT " + ",".join(NMS_FIELDS) + " FROM #NMS"))
                gated_modern = create_snapshot(nms_active=False, master_data=before_master,
                    dbm_master=None, skuloc_attributes=None, sku_descriptions=None,
                    site_descriptions=None, exclusions=None, sku_attributes=None,
                    location_attributes=None, nms_all_items=before_nms)
                result["comparisons"]["inactive_master_untouched"] = gated_master == gated_modern["MasterData"]
                result["comparisons"]["inactive_nms_untouched"] = gated_nms == gated_modern["NMSAllItems"]

        ambiguous = fixture()
        ambiguous["dbm_master"].append(dict(ambiguous["dbm_master"][0],
                                             SKUIntroDate=date(2027, 1, 1)))
        try:
            create_snapshot(nms_active=True, **ambiguous)
        except NmsSnapshotAmbiguity as exc:
            result["ambiguity"] = {"status": "DENIED_NO_NATIVE_WINNER", "message": str(exc)}
        else:
            result["ambiguity"] = {"status": "UNEXPECTEDLY_SELECTED"}
        if not all(result["comparisons"].values()) or result["ambiguity"]["status"] != "DENIED_NO_NATIVE_WINNER":
            failure = "daily_nms_snapshot_sql_mismatch"
            result["error"] = failure
        else:
            result["status"] = "PASS"
    except Exception as exc:
        failure = failure or "%s: %s" % (type(exc).__name__, exc)
        result["error"] = failure
    finally:
        (target / "fixture.json").write_text(json.dumps(case, indent=2, default=_json), encoding="utf-8")
        (target / "receipt.json").write_text(json.dumps(result, indent=2, default=_json), encoding="utf-8")
    if failure:
        raise AssertionError(failure)
    print(json.dumps({"status": result["status"], "comparisons": result["comparisons"],
                      "counts": result["counts"], "ambiguity": result["ambiguity"]["status"]}))


if __name__ == "__main__":
    main()
