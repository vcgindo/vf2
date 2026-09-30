"""Independent isolated SQL oracle for the raw-master producer boundary."""
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal

from mta.application.r1_importer_master import TABLE_COLUMNS, validate_master_input
from parity.adapters.legacy import runner


SCRIPT = runner.LEGACY / "Importer/ValidateAndProcessMaster.sql"
SHA256 = "e95e7c2d7c4fa5459a75184a7eb546e77b58a6b9848b5e08befe61a874b85a88"


def read_script(entry):
    raw = SCRIPT.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SHA256:
        raise ValueError("Legacy raw-master producer hash changed")
    sql = raw.decode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "cp1252")
    for name, value in {
        "IntermediateDatabase": "VFTEST_Intermediate", "ScriptExecutionFlagQuery": runner.SCRIPT_FLAG,
        "RunDateTime": entry["run_timestamp"], "ImportNonNMSMasterData": str(int(entry["import_non_nms"])),
    }.items():
        sql = sql.replace("$(" + name + ")", value)
    if re.search(r"\$\(|\bDemo_", sql):
        raise ValueError("Unsafe/unresolved master validation oracle token")
    return sql


def _normalize(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bool):
        return int(value)
    return value


def _delta(rows, opening):
    serialize = lambda r: json.dumps(r, sort_keys=True)
    old = Counter(serialize(r) for r in opening)
    result = []
    for row in rows:
        key = serialize(row)
        if old[key]:
            old[key] -= 1
        else:
            result.append(row)
    if any(old.values()):
        raise ValueError("Legacy unexpectedly removed a retained append-only history row")
    return result


def execute_master_legacy(entry):
    # Shared SQL-type decoding only: no modern validation-rule producer runs.
    opening = validate_master_input(entry)
    sql = read_script(entry)
    reset_counts = runner._reset()
    with runner.connection("VFTEST_Importer") as conn:
        conn.execute("INSERT INTO LastBatchRunTbl(LastRunDate) VALUES (?)", entry["business_date"])
        conn.execute("INSERT INTO ScriptExecutedFlag(ScriptName,IsScriptExecuted,IsScriptCritical,ModuleName) VALUES ('ValidateAndProcessMaster.sql',0,1,'Importer')")
        for row in entry["settings"]:
            conn.execute("INSERT INTO ImporterSettingsTbl(Parameter,Value) VALUES (?,?)", row["Parameter"], str(row["Value"]))
        for table, rows in opening.items():
            columns = TABLE_COLUMNS[table]
            statement = f"INSERT INTO [{table}]({','.join('[' + f + ']' for f in columns)}) VALUES ({','.join('?' for _ in columns)})"
            for row in rows:
                conn.execute(statement, *(row[f] for f in columns))
        messages, errors = [], []
        cursor = conn.execute(sql)
        while True:
            messages.extend(message for _, message in cursor.messages)
            if cursor.description:
                columns = [c[0] for c in cursor.description]
                rows = cursor.fetchall()
                if any(c.lower() in {"error", "errornumber", "errormessage"} for c in columns):
                    errors.extend(dict(zip(columns, (_normalize(v) for v in row))) for row in rows)
            if not cursor.nextset():
                break
        messages.extend(message for _, message in cursor.messages)
        tables = {}
        for table, fields in TABLE_COLUMNS.items():
            rows = conn.execute(f"SELECT {','.join('[' + f + ']' for f in fields)} FROM [{table}]").fetchall()
            tables[table] = sorted([dict(zip(fields, (_normalize(v) for v in row))) for row in rows], key=lambda r: json.dumps(r, sort_keys=True))
    outcome = "SQL_ERROR" if errors else "APPLIED" if any("Finished Master data validation" in message for message in messages) else "EARLY_RETURN"
    return {"outcome": outcome, "tables": tables,
            "rejects_added": _delta(tables["RejectedMaster"], opening["RejectedMaster"]),
            "retired_events_added": _delta(tables["RetiredNormsTbl"], opening["RetiredNormsTbl"]),
            "oracle": {"script_sha256": SHA256, "execution_database": "VFTEST_Importer", "errors": errors, "reset_table_counts": reset_counts}}
