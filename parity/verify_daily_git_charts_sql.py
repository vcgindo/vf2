"""Bounded SQL oracle for the pure nonempty GIT chart port.

The declared rows are connector contract cases, not retained shipment facts.
Only connection-local temporary tables are created or mutated.
"""
from __future__ import annotations

from collections import Counter
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

from mta.presentation.daily_git_charts import datasets, response
from mta.presentation.rrr import sql_key
from parity.git_queries import CHART, CHART_SHA, queries
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha


def _fixture():
    base = dict(
        SKUCode="A", WhCode="L", ParentWhCode="P", TransporterCode="T",
        TransporterName="Carrier", OrderNo="O", IsReceiving=True,
        PhysicalInventoryColor="Red", LRCode="LR1",
    )
    transporter = [
        dict(base, SKUStatus="SuperDelay", TruckStatus="SuperDelay"),
        dict(base, LRCode="LR2", SKUStatus="Delay", TruckStatus="Delay"),
        dict(base, LRCode="LR3", SKUStatus="SuperDelay", TruckStatus="SuperDelay"),
        dict(base, SKUCode="OUT", WhCode="X", ParentWhCode="Q", LRCode="OUT",
             SKUStatus="Delay", TruckStatus="Delay"),
    ]
    transit = [
        dict(SKUCode="A", WhCode="L", TLT=5, SLT=2),
        dict(SKUCode="A", WhCode="L", TLT=9, SLT=2),
        dict(SKUCode="A", WhCode="L", TLT=99, SLT=None),
        dict(SKUCode="OUT", WhCode="X", TLT=8, SLT=1),
    ]
    git_master = [
        dict(SKUCode="A", WhCode="L", ParentWhCode="P",
             PhysicalInventoryColor="Black", Git=1, IsParent=True),
        dict(SKUCode="OUT", WhCode="X", ParentWhCode="Q",
             PhysicalInventoryColor="Black", Git=1, IsParent=True),
        dict(SKUCode="A", WhCode="L", ParentWhCode="P",
             PhysicalInventoryColor="Green", Git=1, IsParent=True),
    ]
    attributes = [
        dict(WHCode="L", LogisticsLocation="LOG", LL1="North", LL2=None,
             LL3=None, LL4=None, LL5=None, c1="Dynamic"),
        # Identical native occurrences deliberately multiply both outer joins.
        dict(WHCode="L", LogisticsLocation="LOG", LL1="North", LL2=None,
             LL3=None, LL4=None, LL5=None, c1="Dynamic"),
        dict(WHCode="X", LogisticsLocation="OUT", LL1="Other", LL2=None,
             LL3=None, LL4=None, LL5=None, c1="Excluded"),
    ]
    descriptions = [
        dict(WHCode="L", WHDescription="L'ocation"),
        dict(WHCode="X", WHDescription="Excluded"),
    ]
    return dict(
        declaration="Bounded connector cases; no retained/generated shipment facts.",
        transporter=transporter,
        transit=transit,
        git_master=git_master,
        location_attributes=attributes,
        location_descriptions=descriptions,
        product_scope={"A": 2},
        location_scope={"P": 1, "L": 1},
        dynamic_attributes=[("custom1", "c1")],
        dynamic_ui_config=[dict(header="Custom 1", colCode="custom1", colPosition=7)],
    )


def _create_tables(db):
    db.execute("CREATE TABLE #PS(SKUCode nvarchar(50) NULL)")
    db.execute("CREATE TABLE #LS(WhCode nvarchar(50) NULL)")
    db.execute("""CREATE TABLE #Git(
        SKUCode nvarchar(50) NULL, WhCode nvarchar(50) NULL,
        ParentWhCode nvarchar(50) NULL, PhysicalInventoryColor nvarchar(20) NULL,
        Git decimal(18,4) NULL, IsParent bit NULL)""")
    db.execute("""CREATE TABLE #Transporter(
        SKUCode nvarchar(50) NULL, WhCode nvarchar(50) NULL,
        ParentWhCode nvarchar(50) NULL, TransporterCode nvarchar(50) NULL,
        TransporterName nvarchar(100) NULL, OrderNo nvarchar(50) NULL,
        IsReceiving bit NULL, PhysicalInventoryColor nvarchar(20) NULL,
        LRCode nvarchar(50) NULL, SKUStatus nvarchar(50) NULL,
        TruckStatus nvarchar(50) NULL)""")
    db.execute("CREATE TABLE #Transit(SKUCode nvarchar(50) NULL, WhCode nvarchar(50) NULL, TLT int NULL, SLT int NULL)")
    db.execute("CREATE TABLE #LocDesc(WHCode nvarchar(50) NULL, WHDescription nvarchar(100) NULL)")
    db.execute("""CREATE TABLE #Loc(
        WHCode nvarchar(50) NULL, LogisticsLocation nvarchar(100) NULL,
        LL1 nvarchar(50) NULL, LL2 nvarchar(50) NULL, LL3 nvarchar(50) NULL,
        LL4 nvarchar(50) NULL, LL5 nvarchar(50) NULL, c1 nvarchar(50) NULL)""")


def _insert(db, table, columns, rows):
    if not rows:
        return
    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
    db.cursor().executemany(sql, [tuple(row.get(column) for column in columns) for row in rows])


def _seed(db, case):
    _create_tables(db)
    _insert(db, "#PS", ("SKUCode",), [{"SKUCode": "A"}, {"SKUCode": "A"}])
    _insert(db, "#LS", ("WhCode",), [{"WhCode": "P"}, {"WhCode": "L"}])
    _insert(db, "#Git", ("SKUCode", "WhCode", "ParentWhCode", "PhysicalInventoryColor", "Git", "IsParent"), case["git_master"])
    _insert(db, "#Transporter", ("SKUCode", "WhCode", "ParentWhCode", "TransporterCode", "TransporterName", "OrderNo", "IsReceiving", "PhysicalInventoryColor", "LRCode", "SKUStatus", "TruckStatus"), case["transporter"])
    _insert(db, "#Transit", ("SKUCode", "WhCode", "TLT", "SLT"), case["transit"])
    _insert(db, "#LocDesc", ("WHCode", "WHDescription"), case["location_descriptions"])
    _insert(db, "#Loc", ("WHCode", "LogisticsLocation", "LL1", "LL2", "LL3", "LL4", "LL5", "c1"), case["location_attributes"])


def _chart_queries():
    auth = ";WITH cte_SKUs AS (SELECT SKUCode FROM #PS), cte_WhCodes AS (SELECT WhCode FROM #LS) "
    selected = queries(auth, {"product_permissions": [1], "location_permissions": [1]})
    result = []
    for number in range(4):
        query = selected[f"chart-{number}"]
        if number in (0, 1):
            # Exact declared GetUIConfigAttribute composition for LocAttr c1.
            marker = "t3.LogisticsLocation, t3.LL1"
            if marker not in query:
                raise ValueError(f"Missing dynamic SELECT insertion marker in chart {number}")
            query = query.replace(marker, "t3.LogisticsLocation,t3.c1 as custom1, t3.LL1", 1)
            marker = "t3.LogisticsLocation,  t3.LL1" if number == 1 else "t3.LogisticsLocation, t3.LL1"
            if marker not in query:
                raise ValueError(f"Missing dynamic GROUP BY insertion marker in chart {number}")
            query = query.replace(marker, "t3.LogisticsLocation,t3.c1, t3.LL1", 1)
        result.append(query)
    return result


def _rows(cursor):
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _typed(value):
    if value is None:
        return ["null", None]
    if type(value) is bool:
        return ["bool", value]
    if type(value) is int:
        return ["int", value]
    if isinstance(value, Decimal):
        return ["decimal", str(value)]
    if isinstance(value, str):
        return ["text", value]
    raise TypeError(type(value).__name__)


def _typed_rows(rows):
    return [{key: _typed(value) for key, value in row.items()} for row in rows]


def _dll_input(tables):
    result = []
    for rows in tables:
        names = list(rows[0]) if rows else []
        columns = []
        for name in names:
            values = [row[name] for row in rows if row[name] is not None]
            value = values[0] if values else ""
            kind = "decimal" if isinstance(value, Decimal) else "int32" if type(value) is int else "string"
            columns.append({"name": name, "type": kind})
        result.append({
            "columns": columns,
            "rows": [{name: (str(row[name]) if isinstance(row[name], Decimal) else row[name])
                      for name in names} for row in rows],
        })
    return {"tables": result}


def _bag(rows):
    return Counter(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in _typed_rows(rows))


def _difference(expected, actual):
    left, right = _bag(expected), _bag(actual)
    return dict(missing=list((left - right).elements()), unexpected=list((right - left).elements()))


def _canonical_response(tables, config):
    """Independent translation of pinned GetGoodsInTransitResponse lines 900-1167."""
    codes = [row["colCode"] for row in config]

    def wire(value):
        return "" if value is None else str(value)

    def status_rows(rows, group, status, name):
        distinct = []
        for row in rows:
            if not any(sql_key(item[group]) == sql_key(row[group]) for item in distinct):
                distinct.append(row)
        result = []
        for first in distinct:
            members = [row for row in rows if sql_key(row[group]) == sql_key(first[group])]
            item = {"superdelay": "0", "delay": "0", "name": wire(first[name])}
            for row in members:
                if row[status] == "SuperDelay":
                    item["superdelay"] = str(row["counts"])
                elif row[status] == "Delay":
                    item["delay"] = str(row["counts"])
            item.update({code: wire(first.get(code))
                         for code in codes if code in first})
            result.append(item)
        return result

    def delay_rows(rows, transporterwise):
        result = []
        for row in rows:
            item = {
                "name": wire(row[("TransporterName" if transporterwise else "Details")]),
                "mean": wire(row["Mean"]), "mind": wire(row["MinDelayDays"]),
                "median": wire(row["Median"]), "maxd": wire(row["MaxDelayDays"]),
                "Q1": wire(row["Q1"]), "Q3": wire(row["Q3"]),
            }
            field = "TransporterCode" if transporterwise else "LogisticsLocation"
            item[field] = wire(row[field])
            item.update({code: wire(row.get(code))
                         for code in codes if code in row})
            result.append(item)
        return result

    location = {
        "maxTechBlackRedColumn": {"data": status_rows(tables[0], "WhCode", "SKUStatus", "Details"), "uiconfig": config},
        "delayDaysStatisticalBox": {"data": delay_rows(tables[1], False), "uiconfig": config},
    }
    transporter = {
        "maxTechBlackRedColumn": {"data": status_rows(tables[2], "TransporterCode", "TruckStatus", "TransporterName"), "uiconfig": config},
        "delayDaysStatisticalBox": {"data": delay_rows(tables[3], True), "uiconfig": config},
    }
    return {"data": {"transporterWise": transporter, "locationWise": location}}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_daily_git_charts_sql.py EVIDENCE_DIRECTORY")
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    receipt = {
        "status": "FAILED", "persistent_database_writes": False,
        "database_creation": False, "engine_replays": 0,
        "qualification": "Bounded chart SQL/assembly connector cases only; no retained shipment or application parity.",
    }
    try:
        if file_sha(CHART) != CHART_SHA:
            raise ValueError("Pinned ExpediteProcessor differs")
        case = _fixture()
        expected = datasets(**{key: value for key, value in case.items() if key != "declaration"})
        sql = _chart_queries()
        (target / "fixtures.json").write_text(json.dumps(case, indent=2, default=str), encoding="utf-8")
        (target / "queries.sql").write_text("\n\n-- NEXT DATASET\n\n".join(sql), encoding="utf-8")
        os.environ["VFTEST_PROFILE"] = "fresh"
        with exclusive_replay():
            with connection("VFTEST_BPR") as db:
                database = db.execute("SELECT DB_NAME()").fetchval()
                _seed(db, case)
                actual = [_rows(db.execute(statement)) for statement in sql]
        differences = {
            str(index): _difference(expected["tables"][index], actual[index])
            for index in range(4)
        }
        config = expected["ui_config"]
        expected_wire = response(expected)
        actual_wire = _canonical_response(actual, config)
        wire_equal = expected_wire == actual_wire
        # The retained actual-DLL harness supplies the five canonical LL fields;
        # its output is compared separately after this SQL probe completes.
        dll_config = [row for row in config if row["colCode"].startswith("ll")]
        dll_expected_wire = response({"tables": expected["tables"], "ui_config": dll_config})
        (target / "actual-dll-input.json").write_text(
            json.dumps(_dll_input(actual), indent=2), encoding="utf-8")
        (target / "actual-dll-expected-wire.json").write_text(
            json.dumps(dll_expected_wire, indent=2), encoding="utf-8")
        observations = {
            "expected": [_typed_rows(rows) for rows in expected["tables"]],
            "actual": [_typed_rows(rows) for rows in actual],
            "differences": differences,
            "expected_wire": expected_wire,
            "actual_wire": actual_wire,
            "wire_equal": wire_equal,
        }
        (target / "observations.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
        if any(delta[side] for delta in differences.values() for side in ("missing", "unexpected")):
            raise AssertionError("One or more pure chart datasets differ from canonical SQL")
        if not wire_equal:
            raise AssertionError("Pure GIT response assembly differs from pinned assembly")
        # Check the explicit source order clauses without asserting unspecified ties.
        if any(actual[0][i]["WhCode"].casefold() > actual[0][i + 1]["WhCode"].casefold()
               for i in range(len(actual[0]) - 1)):
            raise AssertionError("Location chart did not preserve explicit WhCode ordering")
        if any(actual[2][i]["counts"] < actual[2][i + 1]["counts"]
               for i in range(len(actual[2]) - 1)):
            raise AssertionError("Transporter chart did not preserve explicit count ordering")
        receipt.update(
            status="PASS_BOUNDED_GIT_CHART_SQL",
            base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            database=database,
            source={str(CHART): CHART_SHA},
            transformations=[
                "Extract the four statements with parity.git_queries from the pinned deployed method.",
                "Redirect only owned relation identifiers to connection-local #tables.",
                "Compose the declared LocAttr c1/custom1 select and group fragments at the source placeholders.",
                "Supply already-resolved scope occurrences through duplicate #PS/#LS rows.",
            ],
            comparison="complete unordered typed bags with duplicates; explicit partial orders checked separately; full assembled response equality",
            counts={str(index): {"expected": len(expected["tables"][index]), "actual": len(actual[index])}
                    for index in range(4)},
            differences=differences,
            response_equal=wire_equal,
        )
        receipt["proof_source_sha256"] = file_sha(Path(__file__))
        receipt["file_hashes"] = {path.name: file_sha(path) for path in target.iterdir() if path.is_file()}
    except Exception as error:
        receipt["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        (target / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
