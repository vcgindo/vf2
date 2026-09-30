"""VFTEST-only supplier validation oracle; no modern business producer calls."""
import hashlib
import re

from mta.application.r1_supplier_input import RAW_TABLES, CHECKPOINT_TABLES, STAGES, typed_supplier_tables, sorted_rows
from parity.adapters.legacy import runner
from parity.adapters.legacy.r1_importer_master import _normalize

PINS = dict(zip(STAGES, (
    "043ea717cfec14fd642d8894bcaf415feccb83ca22c39e0d3e2b2ecb8483f8f1",
    "bb3c7118de499e3553875f315b5e388657a4b8a40e0098faea52f2d8cb80342c",
    "0acf1f7f9327794e30476afd920e13da9e8494e90669d65bcc6d2d019ccd9eb1",
    "54185074df4839d2e81156cb1d5417a72dcbd5bd6d8406e8baecd47ba45a2559",
)))
FINISHED = dict(zip(STAGES, ("Finished SOB data validation", "Finished MOQ data Raw1 validation",
                            "Finished MOQ data Raw2 validation", "Finished Flag Reset")))


def read_scripts(now):
    scripts = {}
    for name, pin in PINS.items():
        path = runner.LEGACY / "Importer" / name
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError(f"Supplier oracle source hash changed: {name}")
        sql = raw.decode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "cp1252")
        for key, value in {"IntermediateDatabase": "VFTEST_Intermediate", "ScriptExecutionFlagQuery": runner.SCRIPT_FLAG,
                           "RunDateTime": now, "ImportNoNormData": "0"}.items():
            sql = sql.replace("$(" + key + ")", value)
        if re.search(r"\$\(|\bDemo_", sql):
            raise ValueError("Unsafe/unresolved supplier oracle token")
        scripts[name] = sql
    return scripts


def execute_supplier_legacy(raw, now):
    """Call only after this side's master producer; never reseed its outputs."""
    tables = typed_supplier_tables(raw)
    scripts = read_scripts(now)
    stages, errors, receipts = {}, {}, []
    with runner.connection("VFTEST_Importer") as conn:
        for table, rows in tables.items():
            fields = RAW_TABLES[table]
            for r in rows:
                conn.execute(f"INSERT INTO [{table}]({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", *(r[f] for f in fields))
        for name in STAGES:
            conn.execute("INSERT INTO ScriptExecutedFlag(ScriptName,IsScriptExecuted,IsScriptCritical,ModuleName) VALUES (?,0,0,'Importer')", name)
            cursor = conn.execute(scripts[name])
            messages, stage_errors = [], []
            while True:
                messages.extend(message for _, message in cursor.messages)
                if cursor.description:
                    fields = [c[0] for c in cursor.description]
                    result = cursor.fetchall()
                    if any(f.lower() in {"error", "errornumber", "errormessage"} for f in fields):
                        stage_errors.extend(dict(zip(fields, (_normalize(v) for v in row))) for row in result)
                if not cursor.nextset():
                    break
            messages.extend(message for _, message in cursor.messages)
            captured = {}
            for table, fields in CHECKPOINT_TABLES.items():
                rows = [dict(zip(fields, (_normalize(v) for v in row))) for row in conn.execute(f"SELECT {','.join(fields)} FROM [{table}]")]
                if table == "ImporterSettingsTbl":
                    rows = [{**r, "Value": int(r["Value"])} for r in rows]
                captured[table] = sorted_rows(rows)
            outcome = "SQL_ERROR" if stage_errors else "APPLIED" if any(FINISHED[name] in m for m in messages) else "EARLY_RETURN"
            stages[name] = {"outcome": outcome, "tables": captured}
            errors[name] = stage_errors
            receipts.append({"name": name, "sha256": PINS[name], "path": str(runner.LEGACY / "Importer" / name), "execution_database": "VFTEST_Importer"})
    return stages, {"errors": errors, "scripts": receipts}
