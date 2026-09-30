"""Serial VFTEST-only daily oracle. Execute unchanged SQL, not the Python port."""
from datetime import datetime
import hashlib
import re

from mta.application.r1_daily_input import CHECKPOINT_TABLES, DAILY_COLUMNS, PRIOR_TABLES, STAGES, validate_daily_entry
from mta.application.r1_supplier_input import sorted_rows
from parity.adapters.legacy import runner
from parity.adapters.legacy.r1_importer_master import _normalize

PINS = dict(zip(STAGES, (
    "ab6c9e863befa2909d691ab22973ea0b492c873922bc2652e80539177c107612",
    "c210e968452e5cb695c68dfcdbe1b03e5aa8e9b6ca095d98c5cf7d7510497fad",
    "52ecb6160aae4472f929a57d6d452665d5f1c5f061b72da7a3153d0890ca0f40",
    "034e26c43545b2e3bbaa936ac25b3652680260682011ac00f7efd0799e6b6783",
    "6868625b49a341f7f3f2af8606b2f88ea252eda7323425962d096380d863ff91",
    "1d995b43f630a56255859270cb2131d5f2d0b21762e5716eb6aa9902b181e68f",
    "526bc472230f3178c74458bf8a43cfa084ae9262400a36bad0d11e55944c97ec",
)))
CLEAR_PIN = "0178c188c7c4c646aabfef7d1c1230f9b52c49f2bc15fd331c9fef66bbd23e3a"
FINISHED = dict(zip(STAGES, (
    "Finished Collecting non master SKUs", "Finished Daily data validation",
    "Finished Daily data validation - Carry forward yesterday stock when daily data not provided",
    "Finished Daily data validation - Make stock zero when daily data not provided",
    "Finished Daily data validation - Do not change when daily data not provided", None,
    "Finished Missing daily data handling in DBM",
)))


def read_scripts(now):
    if datetime.fromisoformat(now).isoformat(timespec="seconds") != now:
        raise ValueError("Oracle requires a canonical bounded timestamp")
    scripts = {}
    for name, pin in {**PINS, "ClearNonMasterInputTables.sql": CLEAR_PIN}.items():
        raw = (runner.LEGACY / "Importer" / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError(f"Daily oracle source hash changed: {name}")
        sql = raw.decode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "cp1252")
        tokens = {"IntermediateDatabase": "VFTEST_Intermediate", "ScriptExecutionFlagQuery": runner.SCRIPT_FLAG,
                  "BPRDB": "VFTEST_BPR", "BPRDatabase": "VFTEST_BPR", "DistributorDatabase": "VFTEST_Distributor",
                  "VendorDatabase": "VFTEST_Vendor", "RunDateTime": now,
                  "DistributorSystemActive": "0", "VendorSystemActive": "0", "VectorDMSActive": "0"}
        for key, value in tokens.items():
            sql = sql.replace("$(" + key + ")", value)
        if re.search(r"\$\(|\bDemo_", sql):
            raise ValueError("Unsafe/unresolved daily oracle token")
        if name in PINS:
            scripts[name] = sql
    return scripts


def _insert(conn, table, fields, rows):
    sql = f"INSERT INTO [{table}]({','.join('[' + f + ']' for f in fields)}) VALUES ({','.join('?' for _ in fields)})"
    for row in rows:
        conn.execute(sql, *(row[f] for f in fields))


def execute_daily_legacy(entry, business_date, now):
    """After this side's generated master, before DBM import/BPR reconstruction.

    The initial full VFTEST reset establishes the selected three daily clears.
    Do not call ClearNonMasterInputTables here: its earlier runtime position also
    clears controls/PSO, which must not be destroyed after upstream production.
    """
    entry = validate_daily_entry(entry, business_date)  # SQL type/provenance only.
    scripts = read_scripts(now)
    with runner.connection("VFTEST_Importer") as conn:
        for table in ("DailyDataRaw", "DailyDataRealRaw", "DailyDataProcessed"):
            if conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchval():
                raise ValueError("Daily oracle must start after clear and before raw import")
        clocks = conn.execute("SELECT CONVERT(date,LastRunDate) FROM LastBatchRunTbl").fetchall()
        if len(clocks) != 1 or clocks[0][0].isoformat() != business_date:
            raise ValueError("Daily component requires one independently seeded run clock")
        if conn.execute("SELECT COUNT(*) FROM ImporterSettingsTbl WHERE Parameter IN ('MissingDailyDataHandling','DBM_MissingDailyDataHandling')").fetchval():
            raise ValueError("Daily settings must have one explicit input owner")
        _insert(conn, "DailyDataRaw", DAILY_COLUMNS, entry["raw_daily_data"])
        _insert(conn, "ImporterSettingsTbl", ("Parameter", "Value"), entry["settings"])
        _insert(conn, "VFSettings", ("Parameter", "Value", "Description"), [{**r, "Description": "Synthetic daily policy"} for r in entry["vf_settings"]])
        _insert(conn, "VectorDMSDistributors", ("WhCode",), [{"WhCode": c} for c in entry["vector_dms_codes"]])
    with runner.connection("VFTEST_BPR") as conn:
        for table, columns in PRIOR_TABLES.items():
            if conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchval():
                raise ValueError("Prior daily BPR state must precede current-day reconstruction")
            _insert(conn, table, columns, entry["prior_bpr"][table])
    for database, table, field in (("VFTEST_Distributor", "DistributorList", "distributor_codes"),
                                    ("VFTEST_Vendor", "VendorList", "vendor_codes")):
        with runner.connection(database) as conn:
            if conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchval():
                raise ValueError("Daily membership must have one explicit input owner")
            _insert(conn, table, ("WhCode",), [{"WhCode": c} for c in entry[field]])
    stages, errors, receipts, report = {}, {}, [], []
    for name in STAGES:
        # Legacy BAT uses a new sqlcmd session for every script (SET/RETURN scope).
        with runner.connection("VFTEST_Importer") as conn:
            raw_count = conn.execute("SELECT COUNT(*) FROM DailyDataRaw").fetchval()
            conn.execute("INSERT INTO ScriptExecutedFlag(ScriptName,IsScriptExecuted,IsScriptCritical,ModuleName) VALUES (?,0,0,'Importer')", name)
            cursor = conn.execute(scripts[name])
            messages, stage_errors = [], []
            while True:
                messages.extend(message for _, message in cursor.messages)
                if cursor.description:
                    fields = [c[0] for c in cursor.description]
                    rows = [dict(zip(fields, (_normalize(v) for v in row))) for row in cursor.fetchall()]
                    if any(f.lower() in {"error", "errornumber", "errormessage"} for f in fields):
                        stage_errors.extend(rows)
                    elif fields == ["LocationCode", "LocationName"]:
                        report = rows
                if not cursor.nextset():
                    break
            messages.extend(message for _, message in cursor.messages)
            captured = {}
            for table, fields in CHECKPOINT_TABLES.items():
                rows = report if table == "LocationInventoryMissingReport" else [dict(zip(fields, (_normalize(v) for v in row)))
                    for row in conn.execute(f"SELECT {','.join('[' + f + ']' for f in fields)} FROM [{table}]")]
                captured[table] = sorted_rows(rows)
            applied = bool(raw_count) if name == STAGES[5] else any(FINISHED[name] in m for m in messages)
            outcome = "SQL_ERROR" if stage_errors else "APPLIED" if applied else "EARLY_RETURN"
            stages[name] = {"outcome": outcome, "tables": captured}
            errors[name] = stage_errors
            receipts.append({"name": name, "sha256": PINS[name], "path": str(runner.LEGACY / "Importer" / name), "execution_database": "VFTEST_Importer"})
    return stages, {"errors": errors, "scripts": receipts, "clear_precondition": {
        "source": "ClearNonMasterInputTables.sql", "sha256": CLEAR_PIN,
        "scope": "ASSERTED_EMPTY_DAILY_TABLES_AFTER_VFTEST_RESET_NOT_FULL_ENTRY_CLEAR_PROOF"}}
