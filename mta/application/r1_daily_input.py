"""Selected normal-MTA daily producer; raw facts plus independent prior BPR.

This is a typed-table component, not a file reader or a successful full entry.
Generated master/descriptions/rejections come from the preceding producer.
No SQL is executed by this port. Each script's return/error is local to it.
"""
from collections import Counter
from copy import deepcopy
from datetime import date, timedelta
import re

from mta.application.r1_importer_master import TABLE_COLUMNS as MASTER_TABLES, _sql_key, _distinct
from mta.application.r1_supplier_input import sorted_rows
from mta.domain.ordinal_lookup import OrdinalLookup
from mta.row_sequences import RecordRows, is_record_rows

SCHEMA = "r1-daily-input-v1"
METRICS = ("Stock", "Consumption", "GIT", "Receipts", "PSO")
DAILY_COLUMNS = ("SKUCode", "WhCode", *METRICS, "ReportDate")
PRIOR_TABLES = {
    "BPRMaster": ("SKUCode", "WHCode", "Norm", "ParentWhCode", "SKUIntroDate"),
    "Plants": ("PlantCode", "PlantName"),
    "NoNormMaster": ("SKUCode", "WhCode", "ParentWhCode", "RLT", "SKUIntroDate"),
    "DailyConsumption": ("SKUCode", "WHCode", *METRICS, "BlueZone", "ReportDate"),
}
CHECKPOINT_TABLES = {
    "DailyDataRaw": DAILY_COLUMNS, "DailyDataProcessed": DAILY_COLUMNS, "DailyDataRealRaw": DAILY_COLUMNS,
    "NonMasterSKUs": ("SKUCode", "WHCode"), "RejectedMaster": MASTER_TABLES["RejectedMaster"],
    # Actual returned report rows, not a substitute for the cleared LocNames table.
    "LocationInventoryMissingReport": ("LocationCode", "LocationName"),
}
STAGES = ("CollectNonMasterSKUs.sql", "ValidateAndProcessDailyData.sql",
          "ValidateAndProcessDailyDataCarryStock.sql", "ValidateAndProcessDailyDataStockZero.sql",
          "ValidateAndProcessDailyDataNoChange.sql", "GenerateLocationInventoryMissingReport.sql",
          "DBMMissingDailyDataHandling.sql")
FLAGS = ("DistributorSystemActive", "VendorSystemActive", "VectorDMSActive")
MODULE_PAIRS = {'DistributorSystemActive':'distributor_norms','VendorSystemActive':'vendor_master'}


class DailyAmbiguity(ValueError):
    """Consumed source selection is unproven; do not invent a winning row."""


class _SqlError(Exception):
    pass


def _typed_rows(rows, fields, nullable=()):
    if not is_record_rows(rows):
        raise ValueError("Daily source table must be a row list")
    def typed_row(row):
        if not isinstance(row, dict) or set(row) - set(fields):
            raise ValueError("Unknown daily source field")
        typed = {}
        for f in fields:
            v = row.get(f)
            if v is None:
                if f not in nullable:
                    raise ValueError(f"Daily source NOT NULL column: {f}")
            elif f in {*METRICS, "Norm", "RLT", "BlueZone"}:
                if type(v) is not int or not -2147483648 <= v <= 2147483647:
                    raise ValueError("Daily source numeric value must fit SQL int")
            elif f in {"ReportDate", "SKUIntroDate"}:
                if not isinstance(v, str) or date.fromisoformat(v).isoformat() != v:
                    raise ValueError("Daily source date must be an ISO date")
            else:
                limit = 125 if f == "PlantName" else 50
                if not isinstance(v, str) or not v.isascii() or len(v) > limit:
                    raise ValueError("Daily text requires bounded ASCII; wider collation unproven")
            typed[f] = v
        return typed
    if isinstance(rows,RecordRows):
        for row in rows:
            typed_row(row)
        return RecordRows(len(rows),lambda:(typed_row(row) for row in rows),
                          getitem=lambda ordinal:typed_row(rows[ordinal]))
    return [typed_row(row) for row in rows]


def validate_module_configuration(flags, sources=None):
    if (not isinstance(flags,dict) or set(flags)!=set(FLAGS) or
            any(type(value) is not int or value not in (0,1) for value in flags.values())):
        raise ValueError('Explicit daily module flags0/1 required')
    if sources is not None and (not isinstance(sources,dict) or set(sources)-set(MODULE_PAIRS.values())):
        raise ValueError('Explicit daily module source projections required')
    for flag,name in MODULE_PAIRS.items():
        if flags[flag] and (sources is None or name not in sources):
            raise ValueError('Enabled daily module requires its actual master projection: '+name)
        if sources is not None and name in sources:
            _typed_rows(sources[name],('SKUCode','WhCode'))


def validate_daily_entry(entry, business_date):
    fields = {"schema", "raw_daily_data", "prior_bpr", "settings", "vf_settings", "shell_flags",
              "distributor_codes", "vendor_codes", "vector_dms_codes"}
    if not isinstance(entry, dict) or not fields<=set(entry) or set(entry)-fields-{'module_sources'} or entry["schema"] != SCHEMA:
        raise ValueError("Explicit raw daily/prior BPR/config contract required; no derived daily input")
    validate_module_configuration(entry['shell_flags'],entry.get('module_sources'))
    day = date.fromisoformat(business_date)
    state = entry["prior_bpr"]
    if not isinstance(state, dict) or set(state) != {*PRIOR_TABLES, "opening_provenance"}:
        raise ValueError("Independent prior BPR daily tables required")
    p = state["opening_provenance"]
    if (not isinstance(p, dict) or set(p) != {"kind", "identity", "business_date"}
            or p["kind"] != "SYNTHETIC_PRIOR_BPR_DAILY" or not isinstance(p["identity"], str)
            or not p["identity"].strip() or date.fromisoformat(p["business_date"]) >= day):
        raise ValueError("Daily opening must be labelled prior synthetic BPR state")
    value = deepcopy(entry)
    value["raw_daily_data"] = _typed_rows(entry["raw_daily_data"], DAILY_COLUMNS, DAILY_COLUMNS[:-1])
    for table, columns in PRIOR_TABLES.items():
        nullable = ("ParentWhCode", "SKUIntroDate") if table == "BPRMaster" else ("Stock",) if table == "DailyConsumption" else ()
        value["prior_bpr"][table] = _typed_rows(state[table], columns, nullable)
    if any(date.fromisoformat(r["ReportDate"]) > date.fromisoformat(p["business_date"])
           for r in value["prior_bpr"]["DailyConsumption"]):
        raise ValueError("Prior daily history cannot supply current/future calculated stock")
    for field in ("distributor_codes", "vendor_codes", "vector_dms_codes"):
        if not isinstance(entry[field], list):
            raise ValueError("Explicit location membership lists required")
        _typed_rows([{"WhCode": c} for c in entry[field]], ("WhCode",))
    for field, allowed in (("settings", {"MissingDailyDataHandling", "DBM_MissingDailyDataHandling"}),
                           ("vf_settings", {"GenerateBPRForMissingInventoryLoc"})):
        rows = entry[field]
        if not isinstance(rows, list):
            raise ValueError("Daily settings must retain a row multiset")
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {"Parameter", "Value"}
                    or not isinstance(row["Parameter"], str) or len(row["Parameter"]) > 50
                    or _sql_key(row["Parameter"]) not in {_sql_key(a) for a in allowed}
                    or not isinstance(row["Value"], str) or not row["Value"].isascii()
                    or (field == "vf_settings" and len(row["Value"]) > 50)):
                raise ValueError("Daily settings are explicit SQL NVARCHAR NOT NULL rows")
    return value


def _sql_int(value):
    text = value.strip()
    if not text:
        return 0
    if not re.fullmatch(r"[+-]?[0-9]+", text):
        raise _SqlError()
    n = int(text)
    if not -2147483648 <= n <= 2147483647:
        raise _SqlError()
    return n


def _scalar(rows, name):
    values = [r["Value"] for r in rows if _sql_key(r["Parameter"]) == _sql_key(name)]
    if len(values) > 1:
        raise _SqlError()
    return _sql_int(values[0]) if values else None


def _key(r, wh="WhCode"):
    return _sql_key(r["SKUCode"]), _sql_key(r[wh])


def _winner(rows, fields):
    values = {tuple(r[f] for f in fields) for r in rows}
    if len(values) > 1:
        raise DailyAmbiguity("UNPROVEN: consumed daily UPDATE has multiple source values; no winner chosen")
    return rows[0] if rows else None


def process_daily_validation(entry, master_validation, business_date, now):
    entry = validate_daily_entry(entry, business_date)
    prior = entry["prior_bpr"]
    master = master_validation["tables"]
    tables = {k: [] for k in CHECKPOINT_TABLES}
    tables["DailyDataRaw"] = entry["raw_daily_data"]
    tables["RejectedMaster"] = deepcopy(master["RejectedMaster"])
    stages = {}

    def grouped(rows, key=_key):
        result = {}
        for row in rows:
            result.setdefault(key(row), []).append(row)
        return result

    def collect():
        plants = {_sql_key(r["PlantCode"]) for r in prior["Plants"]}
        current = {_key(r) for r in master["MasterData"]}
        tables["NonMasterSKUs"] = [r for r in _distinct([
            {"SKUCode": r["SKUCode"], "WHCode": r["ParentWhCode"]} for r in prior["BPRMaster"]
            if r["ParentWhCode"] is not None and _sql_key(r["ParentWhCode"]) in plants], ("SKUCode", "WHCode"))
            if _key(r, "WHCode") not in current]
        return "APPLIED"

    def reject(code, message, rows=None):
        tables["RejectedMaster"].extend({"SKUCode": r["SKUCode"], "WhCode": r["WhCode"],
            "RejectionDate": now, "ReasonCode": code, "ReasonDescription": message}
            for r in (rows if rows is not None else [{"SKUCode": "-NA-", "WhCode": "-NA-"}]))

    def base():
        rows = tables["DailyDataRaw"]
        if not rows:
            reject(12, "Daily data file/table is not available or unreadable or no data provided.")
            return "EARLY_RETURN"
        for row in rows:
            for f in ("SKUCode", "WhCode"):
                if row[f] is not None:
                    row[f] = row[f].strip(" ")
        flags=entry['shell_flags']
        distributors={_sql_key(c) for c in entry['distributor_codes']}
        vendors={_sql_key(c) for c in entry['vendor_codes']}
        dms={_sql_key(c) for c in entry['vector_dms_codes']}
        if (any(flags.values()) and any(_sql_key(r['WhCode']) not in distributors|vendors for r in master['MasterData'])
                and not any(r['WhCode'] is None or _sql_key(r['WhCode']) not in distributors|vendors|dms for r in rows)):
            reject(13,'Daily data file/table is invalid/not available for non-distributor/non-Vendor records')
        rows[:] = [r for r in rows if r["SKUCode"] is not None and r["WhCode"] is not None
                   and any(r[f] is not None for f in METRICS)]
        if not rows:
            reject(21, "Null values are provided from all records in daily data.")
            return "EARLY_RETURN"
        def reject_subset(selected,code,message,multiplicity=None):
            counts=Counter(_key(r) for r in selected) if multiplicity is None else multiplicity
            duplicates=_distinct([r for r in selected if counts[_key(r)]>1],('SKUCode','WhCode'))
            if duplicates:
                reject(code,message,duplicates)
                keys={_key(r) for r in selected}
                rows[:]=[r for r in rows if _key(r) not in keys]
        if flags['DistributorSystemActive'] or flags['VectorDMSActive']:
            reject_subset([r for r in rows if _sql_key(r['WhCode']) in distributors|dms],14,
                          'Duplicate entries SKU+Location in Distributor daily data file/table')
        if flags['VendorSystemActive']:
            selected=[r for r in rows if _sql_key(r['WhCode']) in vendors]
            counts=Counter(_key(r) for r in selected for code in entry['vendor_codes']
                           if _sql_key(code)==_sql_key(r['WhCode']))
            reject_subset(selected,15,'Duplicate entries SKU+Location in Vendor daily data file/table',counts)
        ordinary = [r for r in rows if _sql_key(r["WhCode"]) not in distributors]
        counts = Counter(_key(r) for r in ordinary)
        duplicates = _distinct([r for r in ordinary if counts[_key(r)] > 1], ("SKUCode", "WhCode"))
        if duplicates:
            message=('Duplicate entries SKU+Location in Non-Distributor/Non-Vendor daily data file/table'
                     if flags['DistributorSystemActive'] or flags['VendorSystemActive'] else
                     'Duplicate entries SKU+Location in daily data file/table')
            reject(6, message, duplicates)
            rows[:] = [r for r in rows if _sql_key(r["WhCode"]) in distributors]
        for row in rows:
            for f in METRICS:
                if f == "Stock":
                    row[f] = max(row[f], 0) if row[f] is not None else None
                else:
                    row[f] = max(row[f] or 0, 0)
        sources=entry.get('module_sources',{})
        for flag,name in MODULE_PAIRS.items():
            if flags[flag]:
                source_counts=Counter(_key(source) for source in sources[name])
                tables['DailyDataProcessed'].extend(deepcopy(row) for row in rows
                    for _ in range(source_counts.get(_key(row),0)) if row['Stock'] is not None)
        if flags['VectorDMSActive']:
            code_counts=Counter(_sql_key(code) for code in entry['vector_dms_codes'])
            master_counts=Counter(_key(current) for current in master['MasterData'])
            tables['DailyDataProcessed'].extend(deepcopy(row) for row in rows
                for _ in range(code_counts.get(_sql_key(row['WhCode']),0)*master_counts.get(_key(row),0))
                if row['Stock'] is not None)
        return "APPLIED"

    def locations():
        return _distinct([{f: r[f] for f in ("SKUCode", "WhCode")} for r in master["MasterData"]]
                         + [{"SKUCode": r["SKUCode"], "WhCode": r["WHCode"]} for r in tables["NonMasterSKUs"]]
                         + [{f: r[f] for f in ("SKUCode", "WhCode")} for r in prior["NoNormMaster"]], ("SKUCode", "WhCode"))

    def mode(number):
        setting = _scalar(entry["settings"], "MissingDailyDataHandling")
        # SQL NULL <> n is UNKNOWN: absence executes all three scripts.
        if setting is not None and setting != number:
            return "EARLY_RETURN"
        excluded=set()
        for flag,name in zip(FLAGS,('distributor_codes','vendor_codes','vector_dms_codes')):
            if entry['shell_flags'][flag]:excluded.update(_sql_key(c) for c in entry[name])
        rows = [r for r in tables['DailyDataRaw'] if _sql_key(r['WhCode']) not in excluded]
        if number != 1 and not any(r["Stock"] is not None for r in rows):
            return "EARLY_RETURN"
        targets = [r for r in locations() if _sql_key(r['WhCode']) not in excluded]
        if number == 1:
            keys = {_key(r) for r in targets}
            output = [deepcopy(r) for r in rows if _key(r) in keys and r["Stock"] is not None]
        else:
            output = []
            yesterday = (date.fromisoformat(business_date) - timedelta(days=1)).isoformat()
            by_key = grouped(rows)
            for target in targets:
                matches = by_key.get(_key(target), [])
                source = _winner(matches, METRICS)
                row = {**target, **dict.fromkeys(METRICS, 0), "ReportDate": business_date}
                if source:
                    row.update({f: source[f] or 0 for f in METRICS})
                if number == 3 and (source is None or source["Stock"] is None):
                    history = [r for r in history_index.matching(prior["DailyConsumption"],_key(target))
                               if r["ReportDate"] == yesterday]
                    old = _winner(history, ("Stock",))
                    row["Stock"] = (old["Stock"] or 0) if old else 0
                output.append(row)
        tables["DailyDataProcessed"].extend(output)
        return "APPLIED"

    def missing():
        if not tables["DailyDataRaw"]:
            return "EARLY_RETURN"
        names = []
        keys_by_wh = {}
        for row in master["MasterData"]:
            keys_by_wh.setdefault(_sql_key(row["WhCode"]),set()).add(_key(row))
        stocked = {_key(row) for row in tables["DailyDataRaw"] if row["Stock"] is not None}
        sites_by_wh = {}
        for row in master["SiteDescriptionTbl"]:
            sites_by_wh.setdefault(_sql_key(row["WHCode"]),[]).append(row)
        for row in master["MasterData"]:
            wh = _sql_key(row["WhCode"])
            if stocked & keys_by_wh[wh]:
                continue
            names.extend({"WHCode": row["WhCode"], "WHDescription": d["WHDescription"]}
                         for d in sites_by_wh.get(wh,()))
        names = _distinct(names, ("WHCode", "WHDescription"))
        setting = _scalar(entry["vf_settings"], "GenerateBPRForMissingInventoryLoc")
        if setting == 0:
            absent = {_sql_key(r["WHCode"]) for r in names}
            tables["DailyDataProcessed"] = [r for r in tables["DailyDataProcessed"] if _sql_key(r["WhCode"]) not in absent]
        tables["LocationInventoryMissingReport"] = [{"LocationCode": r["WHCode"], "LocationName": r["WHDescription"]} for r in names]
        return "APPLIED"

    def dbm():
        tables["DailyDataRealRaw"].extend(deepcopy(tables["DailyDataRaw"]))
        values = [r["Value"] for r in entry["settings"] if _sql_key(r["Parameter"]) == "DBM_MISSINGDAILYDATAHANDLING"]
        try:
            flags = [_sql_int(v) for v in values]
        except _SqlError:
            if len(values) > 1:
                raise DailyAmbiguity("UNPROVEN: DBM EXISTS with mixed valid/invalid conversions") from None
            raise
        if 1 in flags:
            tables["DailyDataRaw"] = deepcopy(tables["DailyDataProcessed"])
        return "APPLIED"

    with OrdinalLookup(prior["DailyConsumption"],key=lambda row:_key(row,"WHCode")) as history_index:
        for stage, operation in zip(STAGES, (collect, base, lambda: mode(3), lambda: mode(2), lambda: mode(1), missing, dbm)):
            try:
                outcome = operation()
            except _SqlError:
                outcome = "SQL_ERROR"
            stages[stage] = {"outcome": outcome, "tables":
                {k: sorted_rows(v) for k, v in tables.items()} if stage==STAGES[-1] else {}}
    return stages
