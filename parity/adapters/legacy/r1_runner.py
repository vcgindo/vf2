"""Independent, VFTEST-only oracle execution for the bounded R1 MTA spine.

The Stage 5 adapter has a deliberately smaller input contract.  This module
must remain separate: it accepts the R1 raw source-fact contract, seeds only
the disposable ``VFTEST_*`` databases, runs recovered SQL unchanged except for
database/configuration token substitution, and returns normalized checkpoints.
It is an oracle adapter, never a production execution route.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from mta.application.r1_input import (
    validate_r1_raw_input, validate_r1_source_consistency, resolve_r1_stock_configuration,
    resolve_r1_replenishment_exclusions,
)
from mta.application.r1_master_state import MASTER_SCHEMA, MASTER_FIELDS, MASTER_NUMERIC, source_calculation_view
from mta.application.r1_raw_master_entry import RAW_MASTER_SCHEMA, generated_master_view
from mta.application.r1_supplier_entry import RAW_SUPPLIER_SCHEMA, master_input_skeleton
from mta.application.r1_daily_entry import RAW_DAILY_SCHEMA, generated_daily_view
from mta.application.r1_supplier_input import OPENING_TABLES, typed_supplier_tables, sorted_rows
from parity.adapters.legacy import runner as stage5


LEGACY = stage5.LEGACY
SCRIPT_FLAG = (
    "update A set A.IsScriptExecuted=1 from "
    "VFTEST_Importer.dbo.ScriptExecutedFlag A where ScriptName="
)

# Explicitly pin every recovered source file used by the bounded R1 seam.  A
# source change must be reviewed before it can silently become a new oracle.
R1_SCRIPTS = {
    "01. ImportData.sql": ("BPR/01. ImportData.sql", "c248baeedda13d74a71a499c8b59b7ec46f05f11db00938de59a746bce94ce93"),
    "StockCalculation.sql": ("BPR/Ration_Scripts/StockCalculation.sql", "b493932706997cf38697695b74fc87e96332c6cfadd29c200a682ae0dbd462ce"),
    "GenerateAddionalMasterData.sql": ("BPR/Ration_Scripts/GenerateAddionalMasterData.sql", "831092defb102e1efbe342fa3515f3319e556a6d47d77388e44286d420ea0123"),
    "ImportSpikeOrders.sql": ("BPR/Ration_Scripts/ImportSpikeOrders.sql", "5c8a724f98ef5b8ea830f64e825285e73b924ea03bf8b8e34a0a7e92709e58ce"),
    "CalculateDD.sql": ("BPR/Ration_Scripts/CalculateDD.sql", "98ddd068735a7154b53b4171e63899579363844d965541501f8dbd5e375bd210"),
    "CalculateRoute.sql": ("BPR/Ration_Scripts/CalculateRoute.sql", "66abe2e41ce2fb9d9a3f8583001d53a7cdc7a4fa2306a73a4da66f36f7416a41"),
    "CalculateReq.sql": ("BPR/Ration_Scripts/CalculateReq.sql", "587c367323409081b9d1bf8050c23f166ab829a1f1f947cfe7d37bc5cd3902bf"),
    "ConsolidateReq.sql": ("BPR/Ration_Scripts/ConsolidateReq.sql", "00bac7ce2c83dfc63980b369da2174d4a162875a8c4a2be666f5de5bf0e65415"),
    "UpdateBPPAndColorForOrder.sql": ("BPR/Ration_Scripts/UpdateBPPAndColorForOrder.sql", "317228062943593d9960bc106febbffb215e62e0990b220e31b74f36b7353ce2"),
    "ReqInColorBand.sql": ("BPR/Ration_Scripts/ReqInColorBand.sql", "ea2d235b5712db53a76722f4b74d34d76173e651d63e2c95c14ecdbc43d98478"),
    "CollectDataForBPR.sql": ("BPR/CollectDataForBPR.sql", "1236b702861dce1d9f2492f9c7d9a280bbef20245326ff49628dd6b09308a7c7"),
    "PhysicalInventoryColour": ("BPR/CalculatePenetrationAndColor.sql", "e4a62d592b660fe08d46c45eecaf7a061e60eba7c8d86d3adec239023de5e251"),
    "GenerateBPR.sql": ("BPR/GenerateBPR.sql", "36f06df7a79a0e849ff728659df3ada0ad5a567fa6e0257a4b50b3baeffa4647"),
    "CollectDataForDispatchPriority.sql": ("BPR/CollectDataForDispatchPriority.sql", "3d0602ffd47f9d93489a5440fbd85ac031620fb66e6fe343d9314cc69714d278"),
    "CalculatePenetrationAndColor.sql": ("BPR/CalculatePenetrationAndColor.sql", "e4a62d592b660fe08d46c45eecaf7a061e60eba7c8d86d3adec239023de5e251"),
    "UpdateDispatchPriority.sql": ("BPR/UpdateDispatchPriority.sql", "1331f5cb21ece8ffce3ac3c9dbd61e6df7c2e636bdd297c6267b6b5595656e90"),
    "CollectDataForNormRationing.sql": ("BPR/Ration_Scripts/NormRationing/CollectDataForNormRationing.sql", "2ca0cb727cbbd30f2ab8709bdc4e4ba3d14feae6a720dae2b0305de34fa4a087"),
    "FillRationSteps.sql": ("BPR/Ration_Scripts/NormRationing/FillRationSteps.sql", "3f5821abbfa4719ce0a844ea996a286789b0797e26822fa279e08713b7bab631"),
    "GetReqData.sql": ("BPR/Ration_Scripts/NormRationing/GetReqData.sql", "a82159e39c32e06be3532b3d7d99460350a87ff898df6ceedcd47902ffc4c61d"),
    "ExcludeReplenishment.sql": ("BPR/Ration_Scripts/NormRationing/ExcludeReplenishment.sql", "9fec772bd947f15d554b89da5dc9543ff6ba401729a990dc91c32af37fe85ac6"),
    "GetReqDataForParent.sql": ("BPR/Ration_Scripts/NormRationing/GetReqDataForParent.sql", "2a0bae6e71dce7a967186597f87a602fc7c23b9bada2f5b3bbd1364e6f8c79e0"),
    "GetStepwiseChildReq.sql": ("BPR/Ration_Scripts/NormRationing/GetStepwiseChildReq.sql", "6581e9d5ca8f2bd8b13d2d7a0a644c8d7002c033424b647846f293c86faf577a"),
    "RationPacksize.sql": ("BPR/Ration_Scripts/NormRationing/RationPacksize.sql", "316dacda0806d94355556a796bc713c5da650493bb7ad213fd98a6a889c1891e"),
    "CollectDataForPSORationing.sql": ("BPR/Ration_Scripts/CollectDataForPSORationing.sql", "7f74f75aeaaa3007ae62f69382e2ffea6505726b8203be26db068405c6495a01"),
    "PSORationing.sql": ("BPR/Ration_Scripts/PSORationing.sql", "89d4f88e851a2891a5edf5becab5026acf3da4064d69e0baf46e7cffd5b9ee12"),
    "GenerateRationReqReport.sql": ("BPR/Ration_Scripts/GenerateRationReqReport.sql", "eca76c08c57a553c65f3c9bb460434adfbbcc88341a3a607bbe80a84c825f9c3"),
    "GenerateBifurcationOfRationedReq.sql": ("BPR/Ration_Scripts/GenerateBifurcationOfRationedReq.sql", "8da7fde0a88fd29a8c1f3af0d92ff578be50262f1b5605be8421a1686c45f0b5"),
    "GenerateLogisticPickList.sql": ("BPR/Ration_Scripts/GenerateLogisticPickList.sql", "b5044bcb979e57c270d944fdcf3a7998bee33484a384dae89aaaf414c7d05dfb"),
    # RunCoreBPR calls OrderAllocBasedReports before its later
    # GenSupplierWiseReq producer.  BOR-OA therefore consumes BPR's supplied
    # opening SOB/MOQ state, while supplier BOR consumes the subsequent
    # importer refresh.  These are distinct raw inputs, not report outputs.
    "CollectBOR_OrderAllocationData.sql": ("BPR/OrderAllocationReports/CollectBOR_OrderAllocationData.sql", "e06d22c31b0b51b6ba375c4bdf8ddeac52806d6e0b5b1c362a77dd8d3b4b18da"),
    "UpdateBPR.sql": ("BPR/UpdateBPR.sql", "fb050b8cb30a8c582dcf8ef5c4a50dff52c5252f82fc6318862fabfa6708722b"),
    "GenSupplierWiseReq.sql": ("BPR/Ration_Scripts/GenSupplierWiseReq.sql", "fae0668e77fb3e149f62301f4e5e3cda1c1b546180a66f8262ca899644f16a9b"),
}

R1_SEQUENCE = tuple(R1_SCRIPTS)
R1_MASTER_SCRIPTS = {
    "01. ImportMasterData.sql": ("DBM/DailyDataImportExport/01. ImportMasterData.sql", "dbf3b8b5f22daec422d239ede310a7ba1639e860fa2a5ba42649ae3b68a09a76", "VFTEST_DBM"),
    "UpdateNormChanges.sql": ("Importer/Misc/UpdateNormChanges.sql", "20eee2a6847084129c33bdaa06bcb684086d5f66631544555c21db9bd9bea3bb", "VFTEST_Importer"),
}

R1_FORCE_SCRIPTS = {
    'CollectFailedForceNormData.sql': ('DBM/Misc/CollectFailedForceNormData.sql','1e54175d733b3551416ad522c7c1b297aa01c8484b2e43d9e1a80beba2284c0c','VFTEST_DBM'),
    'FailedForceNormChange.sql': ('DBM/Misc/FailedForceNormChange.sql','6446f1445c89a3859234f6ea5a03eada4a97695daeeae8282a4e5747a8ca7c1a','VFTEST_DBM'),
    'GeneratePhaseInPhaseOutExceptionReport.sql': ('DBM/Misc/GeneratePhaseInPhaseOutExceptionReport.sql','0d8435f3276fa3209ef5a255083ed121fea84a4c46d06bab9e42c84d1128fa9e','VFTEST_DBM'),
    'UpdateInTransitDataTags.sql': ('Importer/UpdateInTransitDataTags.sql', '9a0cad3e75c06f51ee24e03f18680ac307f3f7023750b347b6fb38c1ed15957b', 'VFTEST_Importer'),
    'CollectSeasonalityData.sql': ('DBM/Seasonality/CollectSeasonalityData.sql', '31739f5e5dc2ec1a85159d8c9babc0eb53256c5f273864238209c0ea47b4fcb6', 'VFTEST_DBM'),
    'ProcessSeasonality.sql': ('DBM/Seasonality/ProcessSeasonality.sql', '8ec4e73b9120a871b0209988a95e4b4e0186b53fa51335864d5e69c0d2e3c255', 'VFTEST_DBM'),
    'ApplySeasonalityNormChanges.sql': ('DBM/Seasonality/ApplySeasonalityNormChanges.sql', 'a8490dba69e94027f3fa24008e4c2931cf8ca7d6f2fd09e7e53e0a636ba75112', 'VFTEST_DBM'),
    'InsertParentOrderTypeSuggestions.sql': ('DBM/Misc/InsertParentOrderTypeSuggestions.sql', 'de2479ad078e16b13739cc2259e8129db0a218f192b36058b6f3edec02cdc8f8', 'VFTEST_DBM'),
    'UpdateAcceptedNorms.sql': ('DBM/Misc/UpdateAcceptedNorms.sql', '1e602d7aaf355b03060d33328316b296b68bd76f7eceab270e803108104f9f97', 'VFTEST_DBM'),
    'ClearPhaseInPhaseOutData.sql': ('Importer/ClearPhaseInPhaseOutData.sql', 'aea7f0f33a4e68611409d035b8974041d411af68a9af2781be3167d9f397b549', 'VFTEST_Importer'),
    'CollectPhaseOutData.sql': ('DBM/Misc/CollectPhaseOutData.sql', 'd76f8ed14b491680108b0920bfbbe552d287204004c115eefa663874c6f3a7da', 'VFTEST_DBM'),
    'ProcessPhaseOut.sql': ('DBM/Misc/ProcessPhaseOut.sql', '73a2f7af4a334aa28b2b48920797d1e946694b6518a30d03a9dbf26bfd2045d1', 'VFTEST_DBM'),
    'CollectPhaseInData.sql': ('DBM/Misc/CollectPhaseInData.sql', 'ea384c334edb3fada9c8447602dfe838f242f01ad6329889c805d5f17b58768b', 'VFTEST_DBM'),
    'ProcessPhaseIn.sql': ('DBM/Misc/ProcessPhaseIn.sql', 'ceac31bab2037a73e7dbd6055300e88c947b55351b642b77cf789b273957f3ff', 'VFTEST_DBM'),
    'ImportForceNormChange.sql': ('DBM/DailyDataImportExport/ImportForceNormChange.sql', 'c2b348323a6c4621800bae55387d24af768b38452453b7fc2be158ff3e1d7253', 'VFTEST_DBM'),
    'UpdateForceChangedNorms.sql': ('DBM/Misc/UpdateForceChangedNorms.sql', '643903eb339835f1492a2b5b0302a2d362e089f456894b9668ceb6a46a85fe70', 'VFTEST_DBM'),
    'ClearForceNormChange.sql': ('DBM/Misc/ClearForceNormChange.sql', '37f6da04a127dd2045c18029662f51d2f690075bb688800035dc451733ef96ae', 'VFTEST_Importer'),
}


def _read_script(name: str, *, force_from_ui=True, phase_from_ui=False, run_timestamp='2026-01-15T00:00:00') -> tuple[str, dict]:
    if name in R1_MASTER_SCRIPTS or name in R1_FORCE_SCRIPTS:
        relative_path, expected, database = {**R1_MASTER_SCRIPTS, **R1_FORCE_SCRIPTS}[name]
    else:
        relative_path, expected = R1_SCRIPTS[name]
        database = "VFTEST_BPR"
    path = LEGACY / relative_path
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Recovered R1 oracle changed: {name} {actual}")
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else ("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "cp1252")
    sql = raw.decode(encoding)
    substitutions = {
        "ImporterDatabase": "VFTEST_Importer", "ImporterDB": "VFTEST_Importer", "DBMDatabase": "VFTEST_DBM",
        "DBMDataBase": "VFTEST_DBM", "DBMDB": "VFTEST_DBM", "IntermediateDatabase": "VFTEST_Intermediate",
        "VendorDatabase": "VFTEST_Vendor",
        "IsMTOEnvironment": "0", "ScriptExecutionFlagQuery": SCRIPT_FLAG,
        "RecordPenetrationExceptions": "1" if name == "PhysicalInventoryColour" else "0",
        "BPR_ShowNormZeroItems": "1", "RunDate": run_timestamp[:10] if name == 'InsertParentOrderTypeSuggestions.sql' else "SYNTH",
        "RunDateTime": run_timestamp, "PI_PO_FromUI": str(int(phase_from_ui)),
        "FNCFromUI": str(int(force_from_ui)),
    }
    for key, value in substitutions.items():
        sql = sql.replace("$(" + key + ")", value)
    unresolved = sorted(set(re.findall(r"\$\(([^)]+)\)", sql)))
    if unresolved or re.search(r"(?i)\bDemo_[A-Za-z0-9_]+", sql):
        raise RuntimeError(f"Unsafe or unresolved legacy R1 SQL {name}: {unresolved}")
    return sql, {"name": name, "path": str(path), "sha256": actual, "execution_database": database}


def _as_number(value) -> str:
    if value is None:
        raise ValueError("Legacy R1 checkpoint contains a missing numeric value")
    return format(Decimal(value), "f")


def _seed_raw(payload: dict, *, importer_generated=False, supplier_opening=None, vendor_codes=None, daily_generated=False, order_input=None) -> None:
    """Seed source facts only; never seed a current-day calculation product."""
    validate_r1_raw_input(payload)
    master_state = payload.get("master_state")
    if payload["schema"] == MASTER_SCHEMA:
        # This projects only processed Importer facts. Prior DBM rows below
        # are loaded independently; never call the modern reconciler here.
        payload = source_calculation_view(payload)
    stock_configuration = resolve_r1_stock_configuration(payload)
    foundation = payload["foundation"]
    day = foundation["snapshot"]["business_date"]
    master = {(r["sku_code"], r["location_code"]): r for r in foundation["sku_locations"]}
    inventory = {(r["sku_code"], r["location_code"]): r for r in foundation["inventory_positions"]}
    openings = {(r["sku_code"], r["location_code"]): r for r in payload["stock_openings"]}
    parent = {(r["sku_code"], r["child_location_code"]): r["parent_location_code"] for r in foundation["hierarchy"]}
    routing = {(r["sku_code"], r["location_code"]): r for r in payload["routing"]}
    policies = {(r["sku_code"], r["location_code"]): r for r in payload["policies"]}
    sourcing = {(r["sku_code"], r["location_code"]): r for r in payload["sourcing"]}
    seeded_sku_descriptions: set[str] = set()
    seeded_site_descriptions: set[str] = set()

    with stage5.connection("VFTEST_Importer") as importer, stage5.connection("VFTEST_DBM") as dbm, stage5.connection("VFTEST_BPR") as bpr:
        importer.execute("INSERT INTO ImporterSettingsTbl(Parameter,Value) VALUES ('StockReservationType',?)", str(stock_configuration["reservation_type"]))
        for name in (*R1_MASTER_SCRIPTS, *R1_SEQUENCE) if master_state is not None else R1_SEQUENCE:
            importer.execute("INSERT INTO ScriptExecutedFlag(ScriptName,IsScriptExecuted,IsScriptCritical,ModuleName) VALUES (?,0,1,'BPR')", name)
        dbm.execute("INSERT INTO LastBatchRunTbl(LastRunDate) VALUES (?)", day)
        bpr.execute("INSERT INTO LastBatchRunTbl(LastRunDate) VALUES (?)", day)
        for key, value in (("QtyReservationForRationingOnly", str(int(stock_configuration["reservation_for_rationing_only"]))), (
            "StockThresholdForAdvOrderAlloc", payload["allocation"]["advance_stock_threshold_percent"],
        )):
            bpr.execute("INSERT INTO BPRSettingsTbl(Parameter,Value) VALUES (?,?)", key, value)
        for key, field in (("SpikeThresholdForHighNorm", "spike_high"), ("SpikeThresholdForLowNorm", "spike_low"), ("PSOThresholdForHighNorm", "pso_high"), ("PSOThresholdForLowNorm", "pso_low")):
            defaults = {Decimal(row["policy"][field]) for row in payload["policies"]}
            if len(defaults) != 1:
                raise ValueError(f"Legacy {field} is global; use explicit per-item overrides")
            bpr.execute("INSERT INTO BPRSettingsTbl(Parameter,Value) VALUES (?,?)", key, str(defaults.pop()))
        for sequence, colour in enumerate(("Black", "Red", "Yellow", "Green", "Blue", "White", "Grey"), 1):
            bpr.execute("INSERT INTO ColorSequence(Color,SequenceNo) VALUES (?,?)", colour, sequence)

        if master_state is not None:
            columns = "SKUCode,WhCode,Norm,MinNorm,RLT,RCP,GCP,OCP,MinOrderCount,ParentWhCode,SKUIntroDate"
            for conn, table, rows in ((dbm, "DBMMaster", master_state["dbm_opening"]),
                                      (importer, "MasterData", master_state["importer_master"])):
                if importer_generated and table == "MasterData":
                    continue
                for row in rows:
                    values = [int(Decimal(str(row[f]))) if f in MASTER_NUMERIC and row[f] is not None else row[f] for f in MASTER_FIELDS]
                    conn.execute(f"INSERT INTO {table}({columns}) VALUES (?,?,?,?,?,?,?,?,?,?,?)", *values)

        for (sku, location), source in sorted(master.items()):
            inv, opening, route, policy = inventory[(sku, location)], openings[(sku, location)], routing[(sku, location)], policies[(sku, location)]
            parent_location = parent.get((sku, location))
            # Legacy report/intermediate tables require a non-null parent even
            # for a topmost BPR location.  The raw sourcing closure owns that
            # terminal supplier fact; it is not a seeded calculation output.
            legacy_parent_location = parent_location or sourcing.get((sku, location), {}).get("supplier")
            config = policy["policy"]
            threshold = config.get("spike_override")
            pso_threshold = config.get("pso_override")
            rlt = source["replenishment_lead_time_days"]
            if master_state is None:
                dbm.execute("INSERT INTO DBMMaster(SKUCode,WhCode,Norm,MinNorm,RLT,RCP,GCP,OCP,MinOrderCount,ParentWhCode,SKUIntroDate) VALUES (?,?,?,0,?,0,0,NULL,NULL,?,'2025-01-01')", sku, location, source["base_norm"], rlt, legacy_parent_location)
            # Enter through the canonical import producer rather than seed its
            # BPR outputs. Upstream file validation/processing is still a
            # separate, explicitly uncovered R1 entry boundary.
            if master_state is None:
                importer.execute("INSERT INTO MasterData(SKUCode,WhCode,Norm,MinNorm,RLT,RCP,GCP,OCP,MinOrderCount,ParentWhCode,SKUIntroDate) VALUES (?,?,?,0,?,0,0,NULL,NULL,?,'2025-01-01')", sku, location, source["base_norm"], rlt, legacy_parent_location)
            if not daily_generated:
                importer.execute("INSERT INTO DailyDataProcessed(SKUCode,WhCode,Stock,Consumption,GIT,Receipts,PSO,ReportDate) VALUES (?,?,?,0,?,0,0,?)", sku, location, inv["stock_quantity"], inv["goods_in_transit_quantity"], day)
            if not importer_generated:
                importer.execute("INSERT INTO SkuLocAttributeData(SKUCode,LocCode,PackSize,SpikeThreshold,PSOThreshold,StockPercentForRationing,NormPercentReservation,NonNMS) VALUES (?,?,?,?,?,?,?,0)", sku, location, source["pack_size"], threshold, pso_threshold, int(Decimal(opening.get("stock_percent_reservation", 100))), int(Decimal(opening.get("norm_percent_reservation", 0))))
            importer.execute("INSERT INTO AdditionalDailyData(SKUCode,WhCode,UtilizedStock,StockForRationing,ReportDate) VALUES (?,?,?,?,?)", sku, location, opening.get("utilized_stock", 0), opening.get("stock_for_rationing_override"), day)
            if opening.get("stock_for_requirement_override") is not None:
                importer.execute("INSERT INTO AdditionalDataStockForReqCalc(SKUCode,WhCode,StockForReqCalc,ReportDate) VALUES (?,?,?,?)", sku, location, opening["stock_for_requirement_override"], day)
            importer.execute("INSERT INTO SKULocPriorityForRationing(SKUCode,WhCode,Priority) VALUES (?,?,?)", sku, location, policy.get("rationing_priority", 999999))
            if not importer_generated and sku not in seeded_sku_descriptions:
                importer.execute("INSERT INTO SKUDescriptionTbl(SKUCode,SKUDescription) VALUES (?,?)", sku, sku)
                # Pre-v3 fixtures explicitly exercise the non-Elephant slice.
                importer.execute("INSERT INTO SKUAttributeData(SKUCode,ElephantOrderCapping) VALUES (?,2147483647)", sku)
                seeded_sku_descriptions.add(sku)
            if not importer_generated and location not in seeded_site_descriptions:
                importer.execute("INSERT INTO SiteDescriptionTbl(WHCode,WHDescription) VALUES (?,?)", location, location)
                seeded_site_descriptions.add(location)
        for location in resolve_r1_replenishment_exclusions(payload):
            importer.execute("INSERT INTO ExcludeReplenishment(WhCode) VALUES (?)", location)
        for source in payload["sourcing"] if supplier_opening is None else ():
            # Later supplier BOR consumes the raw importer feed through
            # GenSupplierWiseReq.sql.
            importer.execute(
                "INSERT INTO SOBDataRaw(SKUCode,WHCode,SupplierCode,SupplierDescription,SOB) VALUES (?,?,?,?,?)",
                source["sku_code"], source["location_code"], source["supplier"], source["supplier"], source["sob"],
            )
            importer.execute(
                "INSERT INTO MOQDataRaw2(SKUCode,WHCode,SupplierCode,SupplierDescription,MOQ) VALUES (?,?,?,?,?)",
                source["sku_code"], source["location_code"], source["supplier"], source["supplier"], source["moq"],
            )
        for source in payload.get("supplier_openings", payload["sourcing"]) if supplier_opening is None else ():
            # BOR-OA runs first and reads BPR's pre-batch supplier opening.
            # This is a source-shaped synthetic opening, not a calculation or
            # report product.  v1 compatibility falls back to the importer
            # source only for pre-v2 regression fixtures.
            bpr.execute(
                "INSERT INTO SOBData(SKUCode,WHCode,SupplierCode,SOB) VALUES (?,?,?,?)",
                source["sku_code"], source["location_code"], source["supplier"], source["sob"],
            )
            bpr.execute(
                "INSERT INTO MOQData(SKUCode,WHCode,SupplierCode,MOQ) VALUES (?,?,?,?)",
                source["sku_code"], source["location_code"], source["supplier"], source["moq"],
            )
        if supplier_opening is not None:
            # Seed independently labelled prior BPR state only, never a modern
            # supplier projection or the SQL-generated validated raw feed.
            for table, rows in typed_supplier_tables(supplier_opening, OPENING_TABLES).items():
                fields = OPENING_TABLES[table]
                for row in rows:
                    bpr.execute(f"INSERT INTO {table}({','.join(fields)}) VALUES (?,?,?,?)", *(row[f] for f in fields))
        if vendor_codes is not None:
            with stage5.connection("VFTEST_Vendor") as vendor:
                for code in vendor_codes:
                    vendor.execute("INSERT INTO VendorList(WhCode) VALUES (?)", code)
        for row in payload["policies"]:
            for control in row.get("controls", []):
                if control.get("type") != "phase_out":
                    continue
                if control.get("activation_kind") != "EXISTING":
                    raise RuntimeError("R1 legacy phase oracle supports only an existing PhaseOutTbl opening")
                dbm.execute("INSERT INTO PhaseOutTbl(SKUCode,WHCode,OldNorm,NewNorm,PhaseOutFinished,PhaseOutStartDate,LastProcessedDate,PhaseInSKUCode) VALUES (?,?,?,?,0,?,?,NULL)", row["sku_code"], row["location_code"], control["original_norm"], control["previous_new_norm"], control["started_on"], day)
        # Preserve supplied historical identity before automatic identities
        # are assigned to compatibility openings. This prevents an implicit
        # insert from occupying an explicitly supplied historical key.
        for order in sorted(payload["orders"], key=lambda row: "established_order_key" not in row):
            importer.execute("INSERT INTO PSOData(OrderID,SKUCode,WhCode,Qty,CustomerExpDate) VALUES (?,?,?,?,?)", order["order_id"], order["sku_code"], order["location_code"], order["outstanding_quantity"], order["customer_expected_date"])
            if order["established_is_spike"] is not None:
                columns = "CustomerOrderId,PartId,IsSpike,IsElephant,OriginalQty,Qty,SKUCode,WhCode,CustomerExpectedDate,FirstServicingWhCode,DueDate,IntroDate"
                values = [order["order_id"], 1, int(order["established_is_spike"]), 0, order["outstanding_quantity"], order["outstanding_quantity"], order["sku_code"], order["location_code"], order["customer_expected_date"], order["first_servicing_location_code"], order["established_due_date"], order["accepted_on"]]
                explicit_key = "established_order_key" in order
                if explicit_key:
                    columns = "OrderKey," + columns
                    values.insert(0, order["established_order_key"])
                    bpr.execute("SET IDENTITY_INSERT SpikeOrderData ON")
                try:
                    bpr.execute(f"INSERT INTO SpikeOrderData({columns}) VALUES ({','.join('?' for _ in values)})", *values)
                finally:
                    if explicit_key:
                        bpr.execute("SET IDENTITY_INSERT SpikeOrderData OFF")
        if order_input is not None:
            from mta.application.r1_order_input import FEED_FIELDS, ORDER_FIELDS, CLOSURE_FIELDS
            for row in order_input.get('sku_attributes', []):
                importer.execute('UPDATE SKUAttributeData SET ElephantOrderCapping=? WHERE SKUCode=?',
                                 row['ElephantOrderCapping'], row['SKUCode'])
            for row in order_input['feed_rows']:
                importer.execute('INSERT INTO PSOData('+','.join(FEED_FIELDS)+') VALUES (?,?,?,?,?)',
                                 *(row[f] for f in FEED_FIELDS))
            bpr.execute('SET IDENTITY_INSERT SpikeOrderData ON')
            try:
                for row in order_input['opening_orders']:
                    bpr.execute('INSERT INTO SpikeOrderData('+','.join(ORDER_FIELDS)+') VALUES ('+
                                ','.join('?' for _ in ORDER_FIELDS)+')', *(row[f] for f in ORDER_FIELDS))
            finally:
                bpr.execute('SET IDENTITY_INSERT SpikeOrderData OFF')
            if 'identity_last_value' in order_input:
                # Explicit historical counter; surviving MAX(OrderKey) is insufficient.
                # Validation requires nonempty historical rows, so SQL's next value
                # after RESEED is counter+1 (not the empty/TRUNCATE special case).
                counter = order_input['identity_last_value']
                bpr.execute(f"DBCC CHECKIDENT ('SpikeOrderData', RESEED, {counter}) WITH NO_INFOMSGS")
            for row in order_input['closure_history']:
                bpr.execute('INSERT INTO SpikeOrderClosureHistory('+','.join(CLOSURE_FIELDS)+') VALUES ('+
                            ','.join('?' for _ in CLOSURE_FIELDS)+')', *(row[f] for f in CLOSURE_FIELDS))
        logistics = payload['logistics']
        vehicles = logistics.get('vehicles', [dict(vehicle_id=1, **logistics['vehicle'])] if 'vehicle' in logistics else [])
        for vehicle in vehicles:
            bpr.execute("INSERT INTO VehicleMaster(VehicleID,VehicleName,Weight,Volume) VALUES (?,?,?,?)", vehicle['vehicle_id'], vehicle["name"], vehicle["weight_capacity"], vehicle["volume_capacity"])
        logistics_skus, logistics_locations, logistics_parents = set(), set(), set()
        for item in payload["logistics"]["items"]:
            logistics_skus.add((item["sku_code"], item["weight"], item["volume"]))
            logistics_locations.add((item["to_location"], item["logistics_location"]))
            logistics_parents.add(item["from_location"])
        for sku, weight, volume in sorted(logistics_skus):
            if not importer_generated:
                importer.execute("UPDATE SkuAttributeData SET Weight=?,Volume=? WHERE SKUCode=?", weight, volume, sku)
        for location, logistics_location in sorted(logistics_locations):
            if not importer_generated:
                importer.execute("INSERT INTO LocationAttributeData(WHCode,LogisticsLocation) VALUES (?,?)", location, logistics_location)
        mappings = logistics.get('location_vehicles', [dict(location_code=p, vehicle_id=1) for p in sorted(logistics_parents)])
        for mapping in mappings:
            bpr.execute("INSERT INTO LocationVehicleMaster(LocationID,VehicleID) VALUES (?,?)", mapping['location_code'], mapping['vehicle_id'])


def _diagnostic_report(name, fields, timestamp):
    sql, receipt = _read_script(name,run_timestamp=timestamp)
    rows = []
    with stage5.connection('VFTEST_DBM') as conn:
        cursor = conn.execute(sql)
        while True:
            if cursor.description:
                rows.extend([dict(zip(fields,(v.isoformat() if isinstance(v,date) else v for v in row))) for row in cursor.fetchall()])
            if not cursor.nextset(): break
    if not rows or list(rows[0].values()) != list(fields):
        raise ValueError('Unexpected canonical diagnostic report header')
    return rows[1:],receipt


def _execute(sequence=R1_SEQUENCE, *, force_from_ui=True, phase_from_ui=False, run_timestamp='2026-01-15T00:00:00', order_state=None) -> list[dict]:
    receipts = []
    for name in sequence:
        sql, receipt = _read_script(name, force_from_ui=force_from_ui, phase_from_ui=phase_from_ui, run_timestamp=run_timestamp)
        with stage5.connection(receipt["execution_database"]) as conn:
            conn.timeout = 180
            stage5.consume(conn.execute(sql))
        receipts.append(receipt)
        if name == 'ImportSpikeOrders.sql' and order_state is not None:
            from mta.application.r1_order_input import ORDER_FIELDS, CLOSURE_FIELDS
            for target, table, fields in (
                ('orders','SpikeOrderData',ORDER_FIELDS), ('closure_history','SpikeOrderClosureHistory',CLOSURE_FIELDS),
                ('new_spikes','NewSpikeOrders',('CustomerOrderId','SKUCode','WhCode','Qty','CustomerExpectedDate')),
            ):
                with stage5.connection('VFTEST_BPR') as conn:
                    order_state[target] = [dict(zip(fields, (v.isoformat() if isinstance(v,date) else int(v) if isinstance(v,bool) else v for v in row)))
                        for row in conn.execute('SELECT '+','.join(fields)+' FROM '+table)]
    return receipts


def _rows(sql: str, fields: tuple[str, ...], *, database="VFTEST_BPR") -> list[dict]:
    with stage5.connection(database) as conn:
        result = conn.execute(sql).fetchall()
    def normalize(value):
        if isinstance(value, (Decimal, int, float)):
            return _as_number(value)
        if isinstance(value, date):
            return value.isoformat()
        return value
    return [dict(zip(fields, (normalize(value) for value in row), strict=True)) for row in result]


def _capture(*, order_parts=False) -> dict[str, list[dict]]:
    def order_rows(sql, fields):
        if order_parts:
            sql = sql.replace('SELECT A.CustomerOrderId,', 'SELECT A.OrderKey,A.PartId,A.CustomerOrderId,', 1)
            fields = ('order_key', 'part_id', *fields)
        return _rows(sql, fields)
    return {
        "pick_remaining": _rows("SELECT SKUCode,WhCode,ParentWhCode,LogisticLocation,Priority,ColorWiseAlloction,VehicleName FROM PickListDataForTruckFormation ORDER BY NewSrNo", ("sku", "to_location", "from_location", "logistics_location", "priority", "remaining_quantity", "vehicle")),
        "additional_master": _rows("SELECT SKUCode,WhCode,WhLevel,TopmostWhCode,TopmostWhNorm,TopmostWhPacksize,RLTTillPlantSupplier,SpikeThreshold,PSOThreshold FROM AdditionalMasterData ORDER BY SKUCode,WhCode", ("sku_code", "location_code", "wh_level", "topmost_location_code", "topmost_norm", "topmost_pack_size", "cumulative_rlt_days", "spike_threshold_percent", "pso_threshold_percent")),
        "stock": _rows("SELECT SKUCode,WhCode,StockForReqCalc,StockForRationing FROM Vf_StockCalculation ORDER BY SKUCode,WhCode", ("sku_code", "location_code", "stock_for_requirement", "stock_for_rationing")),
        "routes": order_rows("SELECT A.CustomerOrderId,B.SrcWhCode,B.DestWhCode,B.DueDate FROM SpikeOrderData A JOIN SpikeOrderRouteOriginal B ON A.OrderKey=B.OrderKey ORDER BY A.CustomerOrderId,B.SrcWhCode", ("order_id", "location_code", "child_location_code", "due_date")),
        "order_bpp": order_rows("SELECT A.CustomerOrderId,B.SKUCode,B.SrcWhCode,B.DestWhCode,B.DueDate,B.DueDateAtDest,B.BPP,B.OrderColor,B.Qty FROM SpikeOrderData A JOIN OrderRequirementColor B ON A.OrderKey=B.OrderKey ORDER BY A.CustomerOrderId,B.SrcWhCode,B.DestWhCode", ("order_id", "sku_code", "source_location_code", "destination_location_code", "route_due_date", "due_date_at_destination", "bpp", "colour", "quantity")),
        "advance_stock": order_rows("SELECT A.CustomerOrderId,B.SrcWhCode,B.DestWhCode,B.DueDate,B.Qty FROM SpikeOrderData A JOIN SpikeOrderRouteDaily B ON A.OrderKey=B.OrderKey WHERE B.Type='adv-stock' ORDER BY A.CustomerOrderId,B.SrcWhCode", ("order_id", "source_location_code", "destination_location_code", "business_date", "allocated_quantity")),
        "git_advance": order_rows("SELECT A.CustomerOrderId,B.SrcWhCode,B.DestWhCode,B.DueDate,B.Qty FROM SpikeOrderData A JOIN SpikeOrderRouteDaily B ON A.OrderKey=B.OrderKey WHERE B.Type='git' ORDER BY A.CustomerOrderId,B.SrcWhCode", ("order_id", "source_location_code", "destination_location_code", "business_date", "allocated_quantity")),
        "requirements": _rows("SELECT SKUCode,WhCode,Norm,StockForReqCalc,StockForRationing,DirectSpikeOverdue,PSO,RelPSOAndCNR,TotalReq,CNR,SpikeOverdueAtParent,ResidualChildrenSnP,SnPToNetOff,SnPNettedOff,ResidualSnP,NormReq,VirtualNorm,BlueReq,DispatchPen,DispatchColor FROM vf_ReqCalculation ORDER BY SKUCode,WhCode", ("sku_code", "location_code", "norm", "stock_for_requirement", "stock_for_rationing", "direct_spike_overdue", "pso", "relevant_pso_cnr", "requirement", "cnr", "routed_due_spike", "residual_children", "additional_demand", "netted_additional", "residual_additional", "normal_gap", "virtual_norm", "blue_requirement", "dispatch_pen", "dispatch_colour")),
        "bands": _rows("SELECT SKUCode,WhCode,NormBucketBlackBand,NormBucketRedBand,NormBucketYellowBand,NormBucketGreenBand,OrderBlackBand,OrderRedBand,OrderYellowBand,OrderGreenBand,OrderBlueBand,NormReqBlack,NormReqRed,NormReqYellow,NormReqGreen,OrderReqBlack,OrderReqRed,OrderReqYellow,OrderReqGreen,OrderReqBlue,RemainingStock FROM RequirementInColorBand ORDER BY SKUCode,WhCode", ("sku_code", "location_code", "norm_black_band", "norm_red_band", "norm_yellow_band", "norm_green_band", "order_black_band", "order_red_band", "order_yellow_band", "order_green_band", "order_blue_band", "norm_req_black", "norm_req_red", "norm_req_yellow", "norm_req_green", "order_req_black", "order_req_red", "order_req_yellow", "order_req_green", "order_req_blue", "remaining_stock")),
        "supplier_bor": _rows("SELECT SKUCode,WHCode,SupplierCode,OriginalReq,DispatchReq,ReqTopOfRed,ReqTopOfYellow,ReqTopOfGreen,ReqTopOfBlue FROM SupplierDispatchReq ORDER BY SKUCode,WHCode,SupplierCode", ("sku_code", "location_code", "supplier_code", "original_requirement", "dispatch_requirement", "to_red", "to_yellow", "to_green", "to_blue")),
        "bor_oa": _rows("SELECT SKUCode,WhCode,SupplierCode,Requirement,DispatchQty,Req_TOB,Req_TOR,Req_TOY,Req_TOG,Req_TOBlue,Dispatch_TOB,Dispatch_TOR,Dispatch_TOY,Dispatch_TOG,Dispatch_ToBlue,DispatchColor FROM BORWithOrderAllocation ORDER BY SKUCode,WhCode,SupplierCode", ("sku_code", "location_code", "supplier_code", "requirement", "dispatch_quantity", "req_black", "req_red", "req_yellow", "req_green", "req_blue", "dispatch_black", "dispatch_red", "dispatch_yellow", "dispatch_green", "dispatch_blue", "dispatch_colour")),
        "pso_ration": _rows("SELECT SKUCode,WhCode,ParentWhCode,StartingSnPReq,RemSnPReq,TotalAllocation,ParentLeftover FROM vf_PSOAllocation ORDER BY SKUCode,WhCode", ("sku_code", "location_code", "parent_location_code", "starting_requirement", "remaining_requirement", "total_allocation", "parent_leftover")),
        "normal_ration": _rows("SELECT SKUCode,WhCode,ParentWhCode,Norm,StockForReqCalc,GIT,Req,Step1_RationReq,Step1_LeftoverParentStock,RationReq,LeftoverParentStock FROM vf_ReplReq_v3 ORDER BY SKUCode,WhCode", ("sku_code", "location_code", "parent_location_code", "virtual_norm", "stock_for_requirement", "goods_in_transit", "requirement", "pre_round_quantity", "step1_parent_leftover", "final_quantity", "remaining_parent_stock")),
        "bifurcation": _rows("SELECT SKUCode,WhCode,ParentWhCode,TOR_B,TOR_R,TOY,TOG,TOBlue FROM vf_PickListReport ORDER BY SKUCode,WhCode", ("sku_code", "location_code", "parent_location_code", "to_black", "to_red", "to_yellow", "to_green", "to_blue")),
        "logistic_pick": _rows("SELECT SKUCode,WHCode,ParentWHCode,Priority,ColorWiseAlloction,VehicleName,TruckCount,LogisticLocation,TotalWeight,TotalVolume FROM LogisticPickList ORDER BY NewSRNo", ("sku_code", "location_code", "parent_location_code", "priority", "picked_quantity", "vehicle", "truck", "logistics_location", "total_weight", "total_volume")),
    }


def execute_r1_legacy(payload: dict, *, site_profile=None) -> dict:
    if site_profile not in (None, 'GulfOil'):
        raise ValueError('Unsupported selected site profile')
    """Run the recovered bounded R1 spine on a raw synthetic input closure."""
    validate_r1_raw_input(payload)
    order_input = payload.get('order_input')
    if order_input is not None:
        payload = {k:v for k,v in payload.items() if k != 'order_input'}
    daily_required = payload["schema"] == RAW_DAILY_SCHEMA
    supplier_required = payload["schema"] in {RAW_SUPPLIER_SCHEMA, RAW_DAILY_SCHEMA}
    raw_master_required = payload["schema"] in {RAW_MASTER_SCHEMA, RAW_SUPPLIER_SCHEMA, RAW_DAILY_SCHEMA}
    if not raw_master_required:
        validate_r1_source_consistency(payload)
    master_required = payload["schema"] in {MASTER_SCHEMA, RAW_MASTER_SCHEMA, RAW_SUPPLIER_SCHEMA, RAW_DAILY_SCHEMA}
    for name in (*R1_MASTER_SCRIPTS, *R1_SEQUENCE) if master_required else R1_SEQUENCE:
        _read_script(name)  # Verify the oracle pins before any isolated reset.
    receipts, masters = [], {}
    supplier_opening, vendor_codes = None, None
    if supplier_required:
        from parity.adapters.legacy.r1_supplier_input import read_scripts, execute_supplier_legacy
        read_scripts(payload["raw_master_entry"]["run_timestamp"])
        supplier_opening = {k: payload["supplier_state"][k] for k in OPENING_TABLES}
        vendor_codes = payload["raw_daily_entry"]["vendor_codes"] if daily_required else payload["vendor_codes"]
    if daily_required:
        from parity.adapters.legacy.r1_daily_input import read_scripts as read_daily_scripts, execute_daily_legacy
        read_daily_scripts(payload["raw_master_entry"]["run_timestamp"])
    if raw_master_required:
        from parity.adapters.legacy.r1_importer_master import execute_master_legacy, SCRIPT, SHA256
        # Only this side's SQL-produced state may enter its source projection.
        validation = execute_master_legacy(payload["raw_master_entry"])
        reset_table_counts = validation["oracle"]["reset_table_counts"]
        receipts.append({"name": "ValidateAndProcessMaster.sql", "path": str(SCRIPT), "sha256": SHA256,
                         "execution_database": "VFTEST_Importer"})
        masters["importer_validation"] = {k: v for k, v in validation.items() if k != "oracle"}
        if supplier_required:
            stages, supplier_receipt = execute_supplier_legacy(payload["raw_supplier_entry"], payload["raw_master_entry"]["run_timestamp"])
            masters["supplier_validation"] = stages
            receipts.extend(supplier_receipt["scripts"])
            if any(s["outcome"] == "SQL_ERROR" for s in stages.values()):
                raise ValueError("R1 supplier SQL_ERROR: full-entry continuation remains unproven; use component oracle for partial-state evidence")
            if daily_required:
                daily, daily_receipt = execute_daily_legacy(payload["raw_daily_entry"], payload["raw_master_entry"]["business_date"], payload["raw_master_entry"]["run_timestamp"])
                masters["daily_validation"] = daily
                receipts.extend(daily_receipt["scripts"])
                payload = generated_daily_view(payload, validation, daily)
            payload = master_input_skeleton(payload)
        payload = generated_master_view(payload, validation)
        validate_r1_raw_input(payload)
        validate_r1_source_consistency(payload)
    else:
        reset_table_counts = stage5._reset()
    _seed_raw(payload, importer_generated=raw_master_required, supplier_opening=supplier_opening,
              vendor_codes=None if daily_required else vendor_codes, daily_generated=daily_required, order_input=order_input)
    if supplier_required:
        masters["supplier_state"] = _capture_supplier_state("prior")
    if master_required:
        receipts.extend(_execute(("01. ImportMasterData.sql",)))
        season = payload['master_state'].get('season_control_input')
        if season is not None:
            from mta.application.r1_seasonality import REQUEST_FIELDS, SEASON_FIELDS
            for name,fields,db in (('season_requests',REQUEST_FIELDS,'VFTEST_Importer'),('seasonality',SEASON_FIELDS,'VFTEST_DBM')):
                with stage5.connection(db) as conn:
                    for row in season[name]:
                        conn.execute('INSERT INTO Seasonality('+','.join('['+f+']' for f in fields)+') VALUES ('+
                            ','.join('?' for _ in fields)+')', *(row[f] for f in fields))
        phase = payload['master_state'].get('phase_control_input')
        if phase is not None:
            from mta.application.r1_phase_entry import PHASE_FIELDS
            table_names = dict(phase_out='PhaseOutTbl', phase_in='PhaseInTbl', phase_map='PhaseInPhaseOutMap',
                phase_in_norms='PhaseInNorms', phase_exceptions='PhaseInPhaseOutExceptionLog',
                phase_requests='PhaseOut', phase_stops='PhaseOutStop', phase_in_requests='PhaseInNorms',
                seasonality='Seasonality', season_status='SeasonalityStatus')
            for name, fields in PHASE_FIELDS.items():
                if name == 'seasonality' and season is not None:
                    continue
                db = 'VFTEST_Importer' if name in {'phase_requests','phase_stops','phase_in_requests'} else 'VFTEST_DBM'
                with stage5.connection(db) as conn:
                    for row in phase[name]:
                        conn.execute('INSERT INTO ' + table_names[name] + '(' + ','.join('['+f+']' for f in fields)
                            + ') VALUES (' + ','.join('?' for _ in fields) + ')', *(row[f] for f in fields))
            with stage5.connection('VFTEST_DBM') as conn:
                if phase['start_percent'] is not None:
                    conn.execute("INSERT INTO DBMSettingsTbl(Parameter,Value) VALUES ('PhaseInStartPercent',?)", str(phase['start_percent']))
                if phase.get('history_horizon') is not None:
                    conn.execute("INSERT INTO DBMSettingsTbl(Parameter,Value) VALUES ('PhaseInPhaseOutExceptionLogHorizon',?)", str(phase['history_horizon']))
            if not raw_master_required:
                with stage5.connection('VFTEST_Importer') as conn:
                    conn.execute('INSERT INTO LastBatchRunTbl(LastRunDate) VALUES (?)', payload['foundation']['snapshot']['business_date'])
            receipts.extend(_execute(('CollectPhaseOutData.sql','ProcessPhaseOut.sql','CollectPhaseInData.sql','ProcessPhaseIn.sql'),
                phase_from_ui=phase['from_ui'], run_timestamp=phase['run_timestamp']))
            if payload['master_state'].get('control_diagnostics'):
                rows,receipt = _diagnostic_report('GeneratePhaseInPhaseOutExceptionReport.sql',('PhaseOutSKUCode','WhCode','PhaseInSKUCode','TargetNorm','Reason','Date'),phase['run_timestamp'])
                masters['phase_diagnostic_state'] = [dict(table='phase_report',rows=rows)]
                receipts.append(receipt)
        if season is not None:
            receipts.extend(_execute(('CollectSeasonalityData.sql','ProcessSeasonality.sql','ApplySeasonalityNormChanges.sql')))
        force = payload['master_state'].get('force_norm_input')
        if force is not None:
            # Only original requests/raw-master facts are seeded here. The
            # canonical SQL independently creates the force change table.
            with stage5.connection('VFTEST_Importer') as importer, stage5.connection('VFTEST_DBM') as dbm:
                if not raw_master_required:
                    importer.execute("INSERT INTO ImporterSettingsTbl(Parameter,Value) VALUES ('NMSActive',?)", str(int(force['nms_active'])))
                dbm.execute("INSERT INTO DBMSettingsTbl(Parameter,Value) VALUES ('FNC_MatchMasterNorm',?)", str(int(not force['ignore_master_norm'])))
                for row in ([] if raw_master_required else force['raw_master']):
                    importer.execute('INSERT INTO MasterDataRaw(SKUCode,WhCode,Norm,MinNorm) VALUES (?,?,?,?)', row['SKUCode'], row['WhCode'], row['Norm'], row['MinNorm'])
                for row in ([] if raw_master_required else force['requests']):
                    importer.execute('INSERT INTO ForceNormChange(SKUCode,WhCode,NewNorm,Approved) VALUES (?,?,?,?)', row['SKUCode'], row['WhCode'], row['NewNorm'], row['Approved'])
            receipts.extend(_execute(('ImportForceNormChange.sql',), force_from_ui=force['from_ui']))
        accepted = payload['master_state'].get('accepted_norm_input')
        if accepted is not None:
            from mta.application.r1_parent_suggestions import ACCEPTED_FIELDS
            accepted_tables = dict(accepted='AcceptedNorms',suggestions='Suggestions',acceptance='NormAcceptanceTbl',
                reason_codes='ReasonCodes',suggestions_log='SuggestionsLog',order_summary='OrderDataSummary',suspend_order_type='SuspendOrderType')
            for name, fields in ACCEPTED_FIELDS.items():
                with stage5.connection('VFTEST_Importer' if name == 'accepted' else 'VFTEST_DBM') as conn:
                    for row in accepted[name]:
                        conn.execute('INSERT INTO '+accepted_tables[name]+'('+','.join('['+f+']' for f in fields)+') VALUES ('+
                            ','.join('?' for _ in fields)+')', *(row[f] for f in fields))
            receipts.extend(_execute(('InsertParentOrderTypeSuggestions.sql','UpdateAcceptedNorms.sql'),
                run_timestamp=payload['foundation']['snapshot']['business_date']+'T00:00:00'))
        if force is not None:
            receipts.extend(_execute(('UpdateForceChangedNorms.sql',), force_from_ui=force['from_ui']))
        columns = "SKUCode,WhCode,Norm,MinNorm,RLT,RCP,GCP,OCP,MinOrderCount,ParentWhCode,SKUIntroDate"
        trigger_sql = "SELECT SKUCode,WhCode,NewNorm,Reason FROM NormChangeTriggerTbl ORDER BY SKUCode,WhCode"
        trigger_fields = ("sku_code", "location_code", "new_norm", "reason")
        masters["dbm_master"] = _rows(f"SELECT {columns} FROM DBMMaster ORDER BY SKUCode,WhCode", MASTER_FIELDS, database="VFTEST_DBM")
        masters["norm_change_export"] = _rows(trigger_sql, trigger_fields, database="VFTEST_DBM")
        receipts.extend(_execute(("UpdateNormChanges.sql",)))
        if payload['master_state'].get('control_diagnostics'):
            receipts.extend(_execute(('CollectFailedForceNormData.sql',)))
            rows,receipt = _diagnostic_report('FailedForceNormChange.sql',('SKUCode','WHCode','VectorFlowNorm','Reason'),phase['run_timestamp'])
            masters['force_diagnostic_state'] = [dict(table='force_report',rows=[{('WhCode' if k=='WHCode' else k):v for k,v in r.items()} for r in rows])]
            receipts.append(receipt)
        if force is not None:
            receipts.extend(_execute(('ClearForceNormChange.sql',), force_from_ui=force['from_ui']))
        if phase is not None:
            receipts.extend(_execute(('ClearPhaseInPhaseOutData.sql',)))
            from mta.application.r1_phase_entry import STATE_FIELDS, phase_checkpoint
            table_names.update(log='NormChangeLogTbl', force_requests='ForceNormChange')
            captured = {}
            for name, fields in STATE_FIELDS.items():
                database = 'VFTEST_Importer' if name in {'phase_requests','phase_stops','phase_in_requests','force_requests'} else 'VFTEST_DBM'
                with stage5.connection(database) as conn:
                    cursor = conn.execute('SELECT ' + ','.join('['+f+']' for f in fields) + ' FROM ' + table_names[name])
                    captured[name] = [dict(zip(fields, (v.isoformat() if isinstance(v,date) else v for v in row))) for row in cursor.fetchall()]
            masters['phase_control_state'] = phase_checkpoint(captured)
        masters["importer_master"] = _rows(f"SELECT {columns} FROM MasterData ORDER BY SKUCode,WhCode", MASTER_FIELDS, database="VFTEST_Importer")
        masters["norm_change_export_remaining"] = _rows(trigger_sql, trigger_fields, database="VFTEST_DBM")
        if 'transit_tag_input' in payload['master_state']:
            with stage5.connection('VFTEST_Importer') as conn:
                for row in payload['master_state']['transit_tag_input']:
                    conn.execute('INSERT INTO SKULocStandardAttributes(SKUCode,WhCode,Tags) VALUES (?,?,?)',row['SKUCode'],row['WhCode'],row['Tags'])
            receipts.extend(_execute(('UpdateInTransitDataTags.sql',)))
            masters['transit_tag_state'] = _rows('SELECT SKUCode,WhCode,Tags FROM SKULocStandardAttributes', ('SKUCode','WhCode','Tags'), database='VFTEST_Importer')
        if season is not None:
            from mta.application.r1_seasonality import STATE_FIELDS as SEASON_STATE_FIELDS, seasonal_checkpoint
            captured = {}
            for name,fields in SEASON_STATE_FIELDS.items():
                with stage5.connection('VFTEST_Importer' if name == 'season_requests' else 'VFTEST_DBM') as conn:
                    cursor = conn.execute('SELECT '+','.join('['+f+']' for f in fields)+' FROM '+('NormChangeLogTbl' if name == 'log' else 'Seasonality'))
                    captured[name] = [dict(zip(fields,(int(v) if isinstance(v,bool) else v.isoformat() if isinstance(v,date) else v for v in row))) for row in cursor.fetchall()]
            masters['season_control_state'] = seasonal_checkpoint(captured)
        if accepted is not None:
            from mta.application.r1_parent_suggestions import ACCEPTED_STATE_FIELDS, accepted_checkpoint
            accepted_tables['log'] = 'NormChangeLogTbl'
            captured = {}
            for name,fields in ACCEPTED_STATE_FIELDS.items():
                with stage5.connection('VFTEST_Importer' if name == 'accepted' else 'VFTEST_DBM') as conn:
                    cursor = conn.execute('SELECT '+','.join('['+f+']' for f in fields)+' FROM '+accepted_tables[name])
                    captured[name] = [dict(zip(fields,(int(v) if isinstance(v,bool) else v.isoformat() if isinstance(v,date) else v for v in row))) for row in cursor.fetchall()]
            masters['accepted_control_state'] = accepted_checkpoint(captured)
    if site_profile == 'GulfOil':
        site_script = LEGACY / 'SiteSpecific/GulfOil/Importer/ConvertNonNMSItemsToNMS.sql'
        with stage5.connection('VFTEST_Importer') as conn:
            stage5.consume(conn.execute(site_script.read_text()))
        receipts.append(dict(name=site_script.name, path=str(site_script),
                             sha256=hashlib.sha256(site_script.read_bytes()).hexdigest(),
                             execution_database='VFTEST_Importer'))
    if daily_required:
        # The ported daily producer owns the BPR import boundary, not later
        # BPR mutations to DailyConsumption.BlueZone. Capture immediately
        # after the same ordered import script on the SQL side.
        receipts.extend(_execute(R1_SEQUENCE[:1]))
        from parity.adapters.legacy.r1_importer_master import _normalize
        from mta.application.r1_daily_entry import DAILY_CONSUMPTION_FIELDS
        with stage5.connection("VFTEST_BPR") as conn:
            masters["daily_consumption"] = sorted_rows([dict(zip(DAILY_CONSUMPTION_FIELDS, (_normalize(v) for v in row)))
                for row in conn.execute("SELECT " + ",".join(DAILY_CONSUMPTION_FIELDS) + " FROM DailyConsumption")])
        receipts.extend(_execute(R1_SEQUENCE[1:], order_state=masters.setdefault('order_import_state',{}) if order_input is not None else None))
    else:
        receipts.extend(_execute(order_state=masters.setdefault('order_import_state',{}) if order_input is not None else None))
    if order_input is not None:
        masters['order_import_state'] = [dict(table=name,rows=rows) for name,rows in masters['order_import_state'].items()]
        if ('identity_last_value' in order_input or len({r['CustomerOrderId'] for r in order_input['opening_orders']}) < len(order_input['opening_orders'])):
            # CalculateReq truncates IntermediateDB before returning. Compare
            # quantity conservation from retained native order/daily-route rows,
            # not a fabricated claim to have captured the cleared temp table.
            # Its remainder UPDATE is original Qty minus cumulative route Qty;
            # retain negative over-pack remainders, with no clamp or tolerance.
            masters['order_remaining'] = _rows(
                'SELECT A.OrderKey,A.CustomerOrderId,A.PartId,A.Qty-ISNULL(B.Alloc,0) '
                'FROM SpikeOrderData A LEFT JOIN '
                '(SELECT OrderKey,SUM(Qty) Alloc FROM SpikeOrderRouteDaily GROUP BY OrderKey) B '
                'ON A.OrderKey=B.OrderKey WHERE A.IsSpike=1',
                ('order_key','order_id','part_id','remaining_quantity'))
    if supplier_required:
        masters["supplier_state"].update(_capture_supplier_state("refreshed"))
        masters["vendor_bor"] = _rows("SELECT SKUCode,WHCode,VendorCode,OriginalReq,DispatchReq,ReqTopOfRed,ReqTopOfYellow,ReqTopOfGreen,ReqTopOfBlue FROM VendorDispatchReq ORDER BY SKUCode,WHCode,VendorCode", ("sku_code", "location_code", "supplier_code", "original_requirement", "dispatch_requirement", "to_red", "to_yellow", "to_green", "to_blue"))
    if master_required:
        masters["bpr_master"] = _rows("SELECT SKUCode,WhCode,Norm,ParentWhCode,SKUIntroDate FROM BPRMaster ORDER BY SKUCode,WhCode",
                                      ("sku_code", "location_code", "norm", "parent_location_code", "sku_intro_date"))
    return {
        "schema": "r1-legacy-oracle-output-v1",
        "business_date": payload["foundation"]["snapshot"]["business_date"],
        "reset_table_counts": reset_table_counts,
        "scripts": receipts,
        "checkpoints": {**masters, **_capture(order_parts=order_input is not None and
            ('identity_last_value' in order_input or len({r['CustomerOrderId'] for r in order_input['opening_orders']}) < len(order_input['opening_orders'])))},
    }


def _capture_supplier_state(prefix):
    from parity.adapters.legacy.r1_importer_master import _normalize
    result = {}
    with stage5.connection("VFTEST_BPR") as conn:
        for table, suffix in (("SOBData", "sob"), ("MOQData", "moq")):
            fields = OPENING_TABLES[table]
            result[prefix + "_" + suffix] = sorted_rows([
                dict(zip(fields, (_normalize(v) for v in row)))
                for row in conn.execute(f"SELECT {','.join(fields)} FROM {table}")])
    return result
