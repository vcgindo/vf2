"""Materialize business fixtures and execute unchanged recovered legacy SQL."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pyodbc


ROOT = Path(__file__).resolve().parents[3]
LEGACY = Path("F:/VFlow_Local/local-runtime/mta-engine/Scripts")
DATABASES = tuple(
    "VFTEST_" + role
    for role in ("Importer", "BPR", "DBM", "BTR", "Interface", "Intermediate", "Vendor", "Distributor")
)
SCRIPT_FLAG = (
    "update A set A.IsScriptExecuted=1 from "
    "VFTEST_Importer.dbo.ScriptExecutedFlag A where ScriptName="
)
SCRIPTS = {
    "ImportSpikeOrders.sql": (
        LEGACY / "BPR/Ration_Scripts/ImportSpikeOrders.sql",
        "5c8a724f98ef5b8ea830f64e825285e73b924ea03bf8b8e34a0a7e92709e58ce",
    ),
    "StockCalculation.sql": (
        LEGACY / "BPR/Ration_Scripts/StockCalculation.sql",
        "b493932706997cf38697695b74fc87e96332c6cfadd29c200a682ae0dbd462ce",
    ),
    "CalculateReq.sql": (
        LEGACY / "BPR/Ration_Scripts/CalculateReq.sql",
        "587c367323409081b9d1bf8050c23f166ab829a1f1f947cfe7d37bc5cd3902bf",
    ),
    "ConsolidateReq.sql": (
        LEGACY / "BPR/Ration_Scripts/ConsolidateReq.sql",
        "00bac7ce2c83dfc63980b369da2174d4a162875a8c4a2be666f5de5bf0e65415",
    ),
    "CollectDataForDispatchPriority.sql": (
        LEGACY / "BPR/CollectDataForDispatchPriority.sql",
        "3d0602ffd47f9d93489a5440fbd85ac031620fb66e6fe343d9314cc69714d278",
    ),
    "CalculatePenetrationAndColor.sql": (
        LEGACY / "BPR/CalculatePenetrationAndColor.sql",
        "e4a62d592b660fe08d46c45eecaf7a061e60eba7c8d86d3adec239023de5e251",
    ),
    "UpdateDispatchPriority.sql": (
        LEGACY / "BPR/UpdateDispatchPriority.sql",
        "1331f5cb21ece8ffce3ac3c9dbd61e6df7c2e636bdd297c6267b6b5595656e90",
    ),
    "ProcessSeasonality.sql": (
        LEGACY / "DBM/Seasonality/ProcessSeasonality.sql",
        "8ec4e73b9120a871b0209988a95e4b4e0186b53fa51335864d5e69c0d2e3c255",
    ),
    "ApplySeasonalityNormChanges.sql": (
        LEGACY / "DBM/Seasonality/ApplySeasonalityNormChanges.sql",
        "a8490dba69e94027f3fa24008e4c2931cf8ca7d6f2fd09e7e53e0a636ba75112",
    ),
    "CollectPhaseOutData.sql": (
        LEGACY / "DBM/Misc/CollectPhaseOutData.sql",
        "d76f8ed14b491680108b0920bfbbe552d287204004c115eefa663874c6f3a7da",
    ),
    "ProcessPhaseOut.sql": (
        LEGACY / "DBM/Misc/ProcessPhaseOut.sql",
        "73a2f7af4a334aa28b2b48920797d1e946694b6518a30d03a9dbf26bfd2045d1",
    ),
    "CollectPhaseInData.sql": (
        LEGACY / "DBM/Misc/CollectPhaseInData.sql",
        "ea384c334edb3fada9c8447602dfe838f242f01ad6329889c805d5f17b58768b",
    ),
    "ProcessPhaseIn.sql": (
        LEGACY / "DBM/Misc/ProcessPhaseIn.sql",
        "ceac31bab2037a73e7dbd6055300e88c947b55351b642b77cf789b273957f3ff",
    ),
    "CollectDataForNormRationing.sql": (
        LEGACY / "BPR/Ration_Scripts/NormRationing/CollectDataForNormRationing.sql",
        "2ca0cb727cbbd30f2ab8709bdc4e4ba3d14feae6a720dae2b0305de34fa4a087",
    ),
    "FillRationSteps.sql": (
        LEGACY / "BPR/Ration_Scripts/NormRationing/FillRationSteps.sql",
        "3f5821abbfa4719ce0a844ea996a286789b0797e26822fa279e08713b7bab631",
    ),
    "GetReqData.sql": (
        LEGACY / "BPR/Ration_Scripts/NormRationing/GetReqData.sql",
        "a82159e39c32e06be3532b3d7d99460350a87ff898df6ceedcd47902ffc4c61d",
    ),
    "ExcludeReplenishment.sql": (
        LEGACY / "BPR/Ration_Scripts/NormRationing/ExcludeReplenishment.sql",
        "9fec772bd947f15d554b89da5dc9543ff6ba401729a990dc91c32af37fe85ac6",
    ),
    "GetReqDataForParent.sql": (
        LEGACY / "BPR/Ration_Scripts/NormRationing/GetReqDataForParent.sql",
        "2a0bae6e71dce7a967186597f87a602fc7c23b9bada2f5b3bbd1364e6f8c79e0",
    ),
    "GetStepwiseChildReq.sql": (
        LEGACY / "BPR/Ration_Scripts/NormRationing/GetStepwiseChildReq.sql",
        "6581e9d5ca8f2bd8b13d2d7a0a644c8d7002c033424b647846f293c86faf577a",
    ),
    "RationPacksize.sql": (
        LEGACY / "BPR/Ration_Scripts/NormRationing/RationPacksize.sql",
        "316dacda0806d94355556a796bc713c5da650493bb7ad213fd98a6a889c1891e",
    ),
}
DBM_SCRIPTS = {
    "ProcessSeasonality.sql", "ApplySeasonalityNormChanges.sql",
    "CollectPhaseOutData.sql", "ProcessPhaseOut.sql",
    "CollectPhaseInData.sql", "ProcessPhaseIn.sql",
}


from parity.legacy_isolation import connection


def consume(cursor):
    """Legacy TRY/CATCH returns errors as rows, so ODBC success is not enough."""
    while True:
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            if rows and any(column.lower() in {"error", "errornumber", "errormessage"} for column in columns):
                raise RuntimeError(f"Legacy SQL error result set: {columns}: {rows}")
        if not cursor.nextset():
            break


def _read_script(name: str) -> tuple[str, dict]:
    path, expected = SCRIPTS[name]
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Recovered oracle changed: {name} {actual}")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "cp1252"
    substitutions = {
        "ImporterDatabase": "VFTEST_Importer",
        "DBMDatabase": "VFTEST_DBM",
        "DBMDataBase": "VFTEST_DBM",
        "IntermediateDatabase": "VFTEST_Intermediate",
        "IsMTOEnvironment": "0",
        "ScriptExecutionFlagQuery": SCRIPT_FLAG,
        "RecordPenetrationExceptions": "0",
        "RunDate": "SYNTH",
        "RunDateTime": "2026-01-01T00:00:00",
        "PI_PO_FromUI": "0",
    }
    sql = raw.decode(encoding)
    for key, value in substitutions.items():
        sql = sql.replace("$(" + key + ")", value)
    unresolved = sorted(set(re.findall(r"\$\(([^)]+)\)", sql)))
    if unresolved or re.search(r"(?i)\bDemo_[A-Za-z0-9_]+", sql):
        raise RuntimeError(f"Unsafe or unresolved legacy SQL {name}: {unresolved}")
    return sql, {"name": name, "path": str(path), "sha256": actual}


def _reset():
    with connection() as master:
        missing = [name for name in DATABASES if not master.execute("SELECT DB_ID(?)", name).fetchval()]
        if missing:
            raise RuntimeError("Build disposable databases first: " + ", ".join(missing))
    counts = {}
    for database in DATABASES:
        with connection(database) as conn:
            tables = conn.execute(
                "SELECT s.name,t.name FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id "
                "WHERE t.is_ms_shipped=0 ORDER BY s.name,t.name"
            ).fetchall()
            for schema, table in tables:
                consume(conn.execute(f"TRUNCATE TABLE [{schema.replace(']', ']]')}].[{table.replace(']', ']]')}]"))
            counts[database] = len(tables)
    return counts


def _validate_fixture(fixture: dict):
    if set(fixture) != {"scenario_id", "business_date", "capability", "rule_ids", "items"}:
        raise ValueError("Scenario has unknown or missing top-level fields")
    date.fromisoformat(fixture["business_date"])
    if not fixture["items"]:
        raise ValueError("Scenario must contain at least one business item")
    cases = set()
    for item in fixture["items"]:
        required = {"case", "sku", "location", "state", "orders"}
        optional = {"controls", "rlt_days", "location_priority", "stock_for_requirement", "routed_due_spike"}
        if set(item) - required - optional or required - set(item):
            raise ValueError("Item has unknown or missing fields")
        if item["case"] in cases:
            raise ValueError("Duplicate case label")
        cases.add(item["case"])
        if set(item["sku"]) != {"code", "pack_size"} or set(item["state"]) != {"norm", "stock", "git"}:
            raise ValueError("Invalid SKU/state shape")
        if set(item["location"]) not in ({"code"}, {"code", "parent"}):
            raise ValueError("Invalid location shape")
        for value in (*item["state"].values(), item["sku"]["pack_size"]):
            if type(value) is not int or value < 0:
                raise ValueError("Fixture quantities must be non-negative integers")
        for order in item["orders"]:
            if set(order) != {"order_id", "quantity", "accepted_on", "due_date", "established_classification"}:
                raise ValueError("Invalid order shape")
            if order["established_classification"] not in {None, "SPIKE", "PSO"}:
                raise ValueError("Unknown established classification")


def _seed_effective_norm(fixture: dict):
    day = fixture["business_date"]
    old_to_new = {}
    for item in fixture["items"]:
        for control in item.get("controls", []):
            if control["type"] == "phase_in":
                for old in control["old_skus"]:
                    old_to_new[(old["sku_code"], item["location"]["code"])] = item["sku"]["code"]
    script_names = set()
    with connection("VFTEST_Importer") as importer, connection("VFTEST_DBM") as dbm:
        dbm.execute("INSERT INTO LastBatchRunTbl(LastRunDate) VALUES (?)", day)
        for status_id, status in ((1, "Not Started"), (7, "Finished"), (21, "Aborted"), (22, "Rejected"), (23, "Stopped")):
            dbm.execute("INSERT INTO SeasonalityStatus(Id,Status) VALUES (?,?)", status_id, status)
        start_percents = {
            str(control["start_percent"])
            for item in fixture["items"] for control in item.get("controls", [])
            if control["type"] == "phase_in"
        }
        if len(start_percents) > 1:
            raise ValueError("One legacy PhaseInStartPercent per scenario required")
        dbm.execute("INSERT INTO DBMSettingsTbl(Parameter,Value) VALUES ('PhaseInStartPercent',?)", next(iter(start_percents), "50"))
        for item in fixture["items"]:
            sku, location, state = item["sku"]["code"], item["location"]["code"], item["state"]
            season_rlts = {
                control["rlt_days"] for control in item.get("controls", [])
                if control["type"] == "seasonality"
            }
            if len(season_rlts) > 1:
                raise ValueError("One legacy seasonality RLT per SKU-location required")
            rlt = item.get("rlt_days", next(iter(season_rlts), 3))
            norm = state["norm"]
            importer.execute(
                "INSERT INTO MasterData(SKUCode,WhCode,Norm,MinNorm,RLT,RCP,GCP,OCP,MinOrderCount,ParentWhCode,SKUIntroDate) VALUES (?,?,?,0,?,0,0,NULL,NULL,NULL,'2025-01-01')",
                sku, location, norm, rlt,
            )
            prior_dbm_norm = norm
            for control in item.get("controls", []):
                if (control["type"] == "seasonality" and day == control["end"]
                        and control.get("previous_new_norm") is not None):
                    prior_dbm_norm = control["previous_new_norm"]
            dbm.execute(
                "INSERT INTO DBMMaster(SKUCode,WhCode,Norm,MinNorm,RLT,RCP,GCP,OCP,MinOrderCount,ParentWhCode,SKUIntroDate) VALUES (?,?,?,0,?,0,0,NULL,NULL,NULL,'2025-01-01')",
                sku, location, prior_dbm_norm, rlt,
            )
            importer.execute(
                "INSERT INTO DailyDataProcessed(SKUCode,WhCode,Stock,Consumption,GIT,Receipts,PSO,ReportDate) VALUES (?,?,?,0,?,0,0,?)",
                sku, location, state["stock"], state["git"], day,
            )
            for conn in (importer, dbm):
                conn.execute(
                    "INSERT INTO SkuLocAttributeData(SKUCode,LocCode,PackSize,StockPercentForRationing,NormPercentReservation,NonNMS) VALUES (?,?,?,100,0,0)",
                    sku, location, item["sku"]["pack_size"],
                )
            for control in item.get("controls", []):
                kind = control["type"]
                if kind == "seasonality":
                    type_id = 1 if control["direction"] == "HIGHER" else 3
                    dbm.execute(
                        "INSERT INTO Seasonality(SKUCode,WhCode,StartDate,EndDate,TargetNorm,DeltaNormPercentage,UpperLowerCap,OrigNorm,NewNorm,BuildupDuration,ActivateDBM,Type,Status,Comment,LastProcessedOn) VALUES (?,?,?,?,?,NULL,?,?,?,?,0,?,1,NULL,NULL)",
                        sku, location, control["start"], control["end"], control["target_norm"],
                        control["cap"], control["original_norm"], control.get("previous_new_norm", control["original_norm"]),
                        control["buildup_days"], type_id,
                    )
                    script_names.update(("ProcessSeasonality.sql", "ApplySeasonalityNormChanges.sql"))
                elif kind == "phase_out":
                    importer.execute(
                        "INSERT INTO PhaseOut(SKUCode,WhCode,PhaseInSKUCode,Approved) VALUES (?,?,?,1)",
                        sku, location, old_to_new.get((sku, location)),
                    )
                    script_names.update(("CollectPhaseOutData.sql", "ProcessPhaseOut.sql"))
                elif kind == "phase_in":
                    if control["target_norm"] is not None:
                        importer.execute(
                            "INSERT INTO PhaseInNorms(SKUCode,WhCode,TargetNorm,Approved) VALUES (?,?,?,1)",
                            sku, location, control["target_norm"],
                        )
                    script_names.update(("CollectPhaseInData.sql", "ProcessPhaseIn.sql"))
                else:
                    raise ValueError("Unsupported legacy Effective Norm control: " + kind)
        ordered = tuple(name for name in (
            "ProcessSeasonality.sql", "ApplySeasonalityNormChanges.sql",
            "CollectPhaseOutData.sql", "ProcessPhaseOut.sql",
            "CollectPhaseInData.sql", "ProcessPhaseIn.sql",
        ) if name in script_names)
        for name in ordered:
            importer.execute(
                "INSERT INTO ScriptExecutedFlag(ScriptName,IsScriptExecuted,IsScriptCritical,ModuleName) VALUES (?,0,1,'DBM')",
                name,
            )
    return ordered


def _capture_effective_norm(fixture: dict):
    wanted = {(item["sku"]["code"], item["location"]["code"]): item["case"] for item in fixture["items"]}
    with connection("VFTEST_DBM") as conn:
        values = {(row.SKUCode, row.WhCode): row.Norm for row in conn.execute("SELECT SKUCode,WhCode,Norm FROM DBMMaster")}
    return sorted(({
        "case": case, "sku": sku, "location": location, "effective_norm": _number(values[(sku, location)])
    } for (sku, location), case in wanted.items()), key=lambda row: row["case"])


def _seed(fixture: dict, norm_overrides: dict | None = None):
    day = fixture["business_date"]
    norm_overrides = norm_overrides or {}
    with connection("VFTEST_Importer") as conn:
        conn.execute("INSERT INTO ImporterSettingsTbl(Parameter,Value) VALUES ('StockReservationType','1')")
        for script in SCRIPTS:
            conn.execute(
                "INSERT INTO ScriptExecutedFlag(ScriptName,IsScriptExecuted,IsScriptCritical,ModuleName) VALUES (?,0,1,'BPR')",
                script,
            )
        for item in fixture["items"]:
            for order in item["orders"]:
                if order["established_classification"] is None:
                    conn.execute(
                        "INSERT INTO PSOData(OrderID,SKUCode,WhCode,Qty,CustomerExpDate) VALUES (?,?,?,?,?)",
                        order["order_id"], item["sku"]["code"], item["location"]["code"],
                        order["quantity"], order["due_date"],
                    )
    # RRR ranks children by the DBM master RLT and optional importer priority.
    # These are authoritative inputs to the recovered SQL, not work-table state.
    if fixture["capability"] == "rrr":
        with connection("VFTEST_DBM") as dbm, connection("VFTEST_Importer") as importer:
            seen = set()
            excluded_roots = set()
            for item in fixture["items"]:
                sku, location = item["sku"]["code"], item["location"]["code"]
                for code, norm, rlt in ((location, norm_overrides.get((sku, location), item["state"]["norm"]), item.get("rlt_days", 3)),):
                    if (sku, code) not in seen:
                        dbm.execute("INSERT INTO DBMMaster(SKUCode,WhCode,Norm,MinNorm,RLT,RCP,GCP,OCP,MinOrderCount,ParentWhCode,SKUIntroDate) VALUES (?,?,?,0,?,0,0,NULL,NULL,NULL,'2025-01-01')", sku, code, norm, rlt)
                        seen.add((sku, code))
                if item.get("location_priority") is not None:
                    importer.execute("INSERT INTO SKULocPriorityForRationing(SKUCode,WhCode,Priority) VALUES (?,?,?)", sku, location, item["location_priority"])
                parent = item["location"].get("parent")
                root = parent["code"] if parent else location
                if root not in excluded_roots:
                    importer.execute("INSERT INTO ExcludeReplenishment(WhCode) VALUES (?)", root)
                    excluded_roots.add(root)
    with connection("VFTEST_BPR") as conn:
        conn.execute("INSERT INTO LastBatchRunTbl(LastRunDate) VALUES (?)", day)
        for key, value in (("QtyReservationForRationingOnly", "0"), ("StockThresholdForAdvOrderAlloc", "66.67")):
            conn.execute("INSERT INTO BPRSettingsTbl(Parameter,Value) VALUES (?,?)", key, value)
        for sequence, colour in enumerate(("Black", "Red", "Yellow", "Green", "Blue", "White", "Grey"), 1):
            conn.execute("INSERT INTO ColorSequence(Color,SequenceNo) VALUES (?,?)", colour, sequence)
        seeded = {}

        def seed_node(sku, location, norm, stock, git, pack, parent, top, top_norm, top_pack, level):
            key = (sku, location)
            if key in seeded:
                if seeded[key] != (norm, stock, git, pack, parent):
                    raise ValueError("Conflicting node definitions")
                return
            seeded[key] = (norm, stock, git, pack, parent)
            conn.execute(
                "INSERT INTO BPRMaster(SKUCode,WHCode,Norm,ParentWhCode,SKUIntroDate) VALUES (?,?,?,?,?)",
                sku, location, norm, parent, "2025-01-01",
            )
            conn.execute(
                "INSERT INTO DailyConsumption(SKUCode,WHCode,Stock,Consumption,GIT,Receipts,PSO,BlueZone,ReportDate) VALUES (?,?,?,0,?,0,0,0,?)",
                sku, location, stock, git, day,
            )
            conn.execute(
                "INSERT INTO SkuLocAttributeData(SKUCode,LocCode,PackSize,SpikeThreshold,PSOThreshold,StockPercentForRationing,NormPercentReservation,NonNMS) VALUES (?,?,?,NULL,NULL,100,0,0)",
                sku, location, pack,
            )
            conn.execute(
                "INSERT INTO AdditionalMasterData(SKUCode,WhCode,WhLevel,TopmostWhCode,TopmostWhNorm,TopmostWhPacksize,RLTTillPlantSupplier,SpikeThreshold,PSOThreshold,ElephantOrderCapping) VALUES (?,?,?,?,?,?,3,33.33,66.67,2147483647)",
                sku, location, level, top, top_norm, top_pack,
            )

        for item in fixture["items"]:
            sku, loc = item["sku"]["code"], item["location"]["code"]
            state = item["state"]
            resolved_norm = norm_overrides.get((sku, loc), state["norm"])
            parent = item["location"].get("parent")
            if parent:
                seed_node(
                    sku, parent["code"], parent["norm"], parent["stock"], parent["git"],
                    parent["pack_size"], None, parent["code"], parent["norm"], parent["pack_size"], 1,
                )
                seed_node(
                    sku, loc, resolved_norm, state["stock"], state["git"], item["sku"]["pack_size"],
                    parent["code"], parent["code"], parent["norm"], parent["pack_size"], 2,
                )
            else:
                seed_node(
                    sku, loc, resolved_norm, state["stock"], state["git"], item["sku"]["pack_size"],
                    None, loc, resolved_norm, item["sku"]["pack_size"], 1,
                )
            for order in item["orders"]:
                established = order["established_classification"]
                if established is not None:
                    conn.execute(
                        "INSERT INTO SpikeOrderData(CustomerOrderId,PartId,IsSpike,IsElephant,OriginalQty,Qty,SKUCode,WhCode,CustomerExpectedDate,DueDate,IntroDate) VALUES (?,1,?,0,?,?,?,?,?,?,?)",
                        order["order_id"], 1 if established == "SPIKE" else 0,
                        order["quantity"], order["quantity"], sku, loc,
                        order["due_date"], order["due_date"], order["accepted_on"],
                    )


def _execute(names: tuple[str, ...]):
    receipts = []
    for name in names:
        database = "VFTEST_DBM" if name in DBM_SCRIPTS else "VFTEST_BPR"
        with connection(database) as conn:
            conn.timeout = 180
            sql, receipt = _read_script(name)
            consume(conn.execute(sql))
            receipt["execution_database"] = database
            receipts.append(receipt)
    return receipts


def _number(value) -> str:
    if value is None:
        return "0"
    return format(Decimal(value), "f")


def _capture_classification(fixture: dict):
    rows = []
    with connection("VFTEST_BPR") as conn:
        spikes = {
            (row.CustomerOrderId, row.SKUCode, row.WhCode): "SPIKE"
            for row in conn.execute("SELECT CustomerOrderId,SKUCode,WhCode FROM NewSpikeOrders")
        }
        psos = {
            (row.CustomerOrderId, row.SKUCode, row.WhCode): "PSO"
            for row in conn.execute("SELECT CustomerOrderId,SKUCode,WhCode FROM SpikeOrderData WHERE IsSpike=0")
        }
    for item in fixture["items"]:
        for order in item["orders"]:
            key = (order["order_id"], item["sku"]["code"], item["location"]["code"])
            classification = spikes.get(key) or psos.get(key)
            if classification is None:
                raise RuntimeError(f"Legacy engine did not classify {key}")
            rows.append({"case": item["case"], "sku": key[1], "location": key[2], "order_id": key[0], "classification": classification})
    return rows


def _capture_calculation(fixture: dict):
    wanted = {(item["sku"]["code"], item["location"]["code"]): item["case"] for item in fixture["items"]}
    rows = []
    with connection("VFTEST_BPR") as conn:
        result = conn.execute(
            "SELECT r.SKUCode,r.WhCode,r.Norm,r.Stock+r.GIT AS Available,r.PSO,r.RelPSOAndCNR,"
            "r.DirectSpikeOverdue,r.TotalReq,r.VirtualNorm,p.EcoColor "
            "FROM vf_ReqCalculation r LEFT JOIN PenetrationAndColor p ON p.SKUCode=r.SKUCode AND p.WhCode=r.WhCode"
        ).fetchall()
    for row in result:
        case = wanted.get((row.SKUCode, row.WhCode))
        if case is None:
            continue
        rows.append({
            "case": case,
            "sku": row.SKUCode,
            "location": row.WhCode,
            "norm": _number(row.Norm),
            "available_inventory": _number(row.Available),
            "pso": _number(row.PSO),
            "relevant_pso_cnr": _number(row.RelPSOAndCNR),
            "due_spike": _number(row.DirectSpikeOverdue),
            "requirement": _number(row.TotalReq),
            "virtual_norm": _number(row.VirtualNorm),
            "dispatch_colour": (row.EcoColor or "").upper(),
        })
    if len(rows) != len(wanted):
        raise RuntimeError(f"Legacy output closure mismatch: expected {len(wanted)}, captured {len(rows)}")
    if fixture["capability"] == "virtual_norm":
        with connection("VFTEST_BPR") as conn:
            virtual = conn.execute("SELECT SKUCode,WhCode,ParentWhCode,VirtualNorm,OverdueOrderQty FROM VirtualNodes").fetchall()
        by_parent = {(item["sku"]["code"], item["location"]["code"]): item["case"] for item in fixture["items"]}
        for row in virtual:
            case = by_parent.get((row.SKUCode, row.ParentWhCode))
            if case is not None:
                rows.append({"case": case + "_direct", "sku": row.SKUCode, "location": row.WhCode,
                             "norm": "0", "available_inventory": "0", "pso": "0",
                             "relevant_pso_cnr": "0", "due_spike": _number(row.OverdueOrderQty),
                             "requirement": _number(row.OverdueOrderQty), "virtual_norm": _number(row.VirtualNorm),
                             "dispatch_colour": "BLACK"})
    return sorted(rows, key=lambda value: value["case"])


def _capture_rrr(fixture: dict):
    wanted = {(item["sku"]["code"], item["location"]["code"]): item["case"] for item in fixture["items"]}
    direct_parents = {(item["sku"]["code"], item["location"]["code"]): item["case"] + "_virtual"
                      for item in fixture["items"] if item["location"].get("parent") is None and item["orders"]}
    with connection("VFTEST_BPR") as conn:
        rows = conn.execute(
            "SELECT x.SKUCode,x.WhCode,x.ParentWhCode,x.Req,x.Norm,c.Norm AS EffectiveNorm,"
            "x.EcoPen,x.EcoCol,x.Step1_RationReq,x.RationReq,x.LeftoverParentStock,a.PackSize "
            "FROM vf_ReplReq_v3 x LEFT JOIN vf_ReqCalculation c ON c.SKUCode=x.SKUCode AND c.WhCode=x.WhCode "
            "LEFT JOIN SkuLocAttributeData a ON a.SKUCode=x.SKUCode AND a.LocCode=x.ParentWhCode"
        ).fetchall()
    output = []
    for row in rows:
        case = wanted.get((row.SKUCode, row.WhCode))
        if case is None:
            case = direct_parents.get((row.SKUCode, row.ParentWhCode))
        if case is None or row.ParentWhCode is None:
            continue
        pack = Decimal(row.PackSize or 1)
        pre = Decimal(row.Step1_RationReq or 0)
        rounded = (pre // pack) * pack
        output.append({
            "case": case, "sku": row.SKUCode, "parent": row.ParentWhCode, "location": row.WhCode,
            "requirement": _number(row.Req), "effective_norm": _number(row.EffectiveNorm),
            "virtual_norm": _number(row.Norm),
            "penetration": format(Decimal(str(row.EcoPen or 0)).quantize(Decimal("0.0001")), "f"),
            "dispatch_colour": (row.EcoCol or "").upper(), "pre_round_quantity": _number(pre),
            "pack_rounded_quantity": _number(rounded), "residual_allocation": _number(Decimal(row.RationReq or 0) - rounded),
            "final_quantity": _number(row.RationReq), "remaining_parent_stock": _number(row.LeftoverParentStock),
        })
    return sorted(output, key=lambda value: value["case"])


def execute_legacy(fixture: dict) -> dict:
    if fixture.get("schema") == "stage5-remaining-scenarios-v1":
        from parity.adapters.legacy.remaining import execute_remaining_legacy
        return execute_remaining_legacy(fixture)
    _validate_fixture(fixture)
    reset_counts = _reset()
    if fixture["capability"] == "effective_norm":
        names = _seed_effective_norm(fixture)
        receipts = _execute(names) if names else []
        result = _capture_effective_norm(fixture)
    else:
        norm_receipts = []
        norm_overrides = {}
        if any(item.get("controls") for item in fixture["items"]):
            norm_names = _seed_effective_norm(fixture)
            norm_receipts = _execute(norm_names) if norm_names else []
            with connection("VFTEST_DBM") as conn:
                norm_overrides = {
                    (row.SKUCode, row.WhCode): row.Norm
                    for row in conn.execute("SELECT SKUCode,WhCode,Norm FROM DBMMaster")
                }
        _seed(fixture, norm_overrides)
    if fixture["capability"] == "new_order_classification":
        names = ("ImportSpikeOrders.sql",)
        receipts = norm_receipts + _execute(names)
        result = _capture_classification(fixture)
    elif fixture["capability"] != "effective_norm":
        names = (
            "StockCalculation.sql", "CalculateReq.sql", "ConsolidateReq.sql",
            "CollectDataForDispatchPriority.sql", "CalculatePenetrationAndColor.sql",
        )
        receipts = norm_receipts + _execute(names)
        if fixture["capability"] == "rrr":
            rrr_names = ("UpdateDispatchPriority.sql", "CollectDataForNormRationing.sql", "FillRationSteps.sql", "GetReqData.sql",
                         "ExcludeReplenishment.sql", "GetReqDataForParent.sql",
                         "GetStepwiseChildReq.sql", "RationPacksize.sql")
            receipts += _execute(rrr_names)
            names += rrr_names
            result = _capture_rrr(fixture)
        else:
            result = _capture_calculation(fixture)
    return {
        "scenario_id": fixture["scenario_id"],
        "business_date": fixture["business_date"],
        "legacy_execution_seam": list(names),
        "source_tables_output": ["VFTEST_DBM.dbo.DBMMaster"] if fixture["capability"] == "effective_norm"
        else (["VFTEST_BPR.dbo.vf_ReplReq_v3", "VFTEST_BPR.dbo.vf_ReqCalculation"]
              if fixture["capability"] == "rrr" else
              ["VFTEST_BPR.dbo.NewSpikeOrders", "VFTEST_BPR.dbo.SpikeOrderData"]
              if fixture["capability"] == "new_order_classification"
              else ["VFTEST_BPR.dbo.vf_ReqCalculation", "VFTEST_BPR.dbo.PenetrationAndColor"]),
        "rule_ids": fixture["rule_ids"],
        "spec_code_divergence_policy": "PRESERVE_LEGACY_FOR_PARITY",
        "reset_table_counts": reset_counts,
        "scripts": receipts,
        "result": result,
    }
