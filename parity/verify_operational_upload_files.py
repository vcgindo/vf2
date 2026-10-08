"""Rollback-only native qualification of all eight generic UI upload logs.

Each SQLCMD invocation owns one transaction and one table fixture.  It seeds the
target log plus action lookup, runs the pinned clear and export SQL in the same
restricted NO REVERT session, redirects only the export result to evidence, and
rolls every mutation back.  No engine or business day is invoked.
"""
import argparse
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application.operational_sqlcmd import upload_log_bytes
from mta.application.operational_upload_logs import (
    ACTION_SCHEMA, LOG_BINDINGS, NATIVE_SCHEMAS, SOURCES,
    clear_ui_upload_log_history, export_ui_upload_log,
)
from mta.serialization import storage
from parity.adapters.legacy.complete_daily_sql import namespace, data_directory
from parity.verify_complete_daily_pick_files import prepare
from parity.verify_complete_daily_producers import (
    OWNER, SOURCE, FixtureSQL, compare_rows, guard_options, native_context,
)


SQLCMD = Path("C:/Program Files/Microsoft SQL Server/Client SDK/ODBC/180/Tools/Binn/SQLCMD.EXE")
IMPORTER = "Importer"
ACTION_TABLE = "UIUploadLogActionType"
PRESERVED = tuple((IMPORTER, name) for name, _ in LOG_BINDINGS) + (
    (IMPORTER, ACTION_TABLE), (IMPORTER, "ImporterSettingsTbl"),
    (IMPORTER, "LastBatchRunTbl"), (IMPORTER, "ScriptExecutedFlag"),
)
IMPLEMENTATION_FILES = (
    "mta/application/operational_upload_logs.py",
    "mta/application/operational_sqlcmd.py",
    "mta/application/operational_inputs.py",
    "parity/verify_operational_upload_files.py",
    "parity/verify_complete_daily_pick_files.py",
    "parity/verify_complete_daily_producers.py",
    "parity/adapters/legacy/complete_daily_sql.py",
    "parity/legacy_isolation.py",
)


def pin(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_pins():
    return {name: pin(ROOT / name) for name in IMPLEMENTATION_FILES}


def source_pins():
    selected = {key: SOURCES[key] for key in ("bindings", "wrapper", "retention", "export", "ddl")}
    result = {}
    for key, (relative, wanted) in selected.items():
        path = SOURCE / relative
        actual = pin(path)
        if actual != wanted:
            raise ValueError("Canonical UI upload source changed: " + relative)
        result[key] = {"path": path.as_posix(), "sha256": actual}
    return result


def _sample(column, table):
    name, kind = column["name"], column["type"]
    if name == "ActionTimeStamp":
        return "2026-06-03T12:34:56.123"
    if name == "ActionId":
        return 1
    if column["nullable"]:
        return None
    if kind in ("nvarchar", "varchar", "nchar", "char"):
        width = int(column["parameters"]) if column["parameters"] not in (None, "max") else 64
        return (table[:8] + "_" + name)[:width]
    if kind in ("int", "bigint", "smallint", "tinyint"):
        return 7
    if kind == "bit":
        return True
    if kind in ("decimal", "numeric"):
        scale = int(column["parameters"].split(",")[1])
        return Decimal(1).quantize(Decimal(1).scaleb(-scale))
    if kind in ("float", "real"):
        return 1.25
    if kind == "date":
        return "2026-06-03"
    if kind in ("datetime", "datetime2"):
        return "2026-06-03T12:34:56.123"
    raise ValueError("Unsupported fixture type: " + kind)


def fixture_cases(table):
    kept = {column["name"]: _sample(column, table) for column in NATIVE_SCHEMAS[table]}
    old = deepcopy(kept); old["ActionTimeStamp"] = "2026-06-02T23:59:59.997"
    cases = (
        ("empty", [], []),
        ("positive-null-duplicate-cutoff-action-duplicate", [old, kept, deepcopy(kept)], [
            {"ActionId": 1, "ActionDesc": "First action"},
            {"ActionId": 1, "ActionDesc": "Second action"},
            {"ActionId": 2, "ActionDesc": "Unmatched action"},
        ]),
    )
    if table == 'UIUploadLogNMSSKUs':
        numeric = deepcopy(kept)
        numeric.update(ElephantOrderCapping=17, Weight=Decimal('0.125'),
                       Volume=Decimal('-1.250'), SKUDescription='caf\u00e9, SKU')
        cases += (('numeric-and-native-text', [numeric], [
            {'ActionId': 1, 'ActionDesc': 'Numeric fields'},
        ]),)
    return cases


def _quote(name):
    if not isinstance(name, str) or not name or "]" in name:
        raise ValueError("Unsafe SQL identifier")
    return "[" + name + "]"


def _literal(value, column):
    kind = column["type"]
    if value is None:
        return "NULL"
    if kind in ("nvarchar", "nchar", "varchar", "char"):
        if not isinstance(value, str):
            raise ValueError("Fixture text type differs")
        return "N'" + value.replace("'", "''") + "'"
    if kind in ("int", "bigint", "smallint", "tinyint"):
        if type(value) is not int:
            raise ValueError("Fixture integer type differs")
        return str(value)
    if kind == "bit":
        if type(value) is not bool:
            raise ValueError("Fixture bit type differs")
        return "1" if value else "0"
    if kind in ("decimal", "numeric"):
        if not isinstance(value, Decimal):
            raise ValueError("Fixture decimal type differs")
        return format(value, "f")
    if kind in ("float", "real"):
        if type(value) is not float:
            raise ValueError("Fixture float type differs")
        return repr(value)
    if kind == "date":
        return "CONVERT(date,N'" + value + "',126)"
    if kind in ("datetime", "datetime2"):
        return "CONVERT(" + kind + ",N'" + value + "',126)"
    raise ValueError("Unsupported SQL fixture literal: " + kind)


def _insert(table, columns, rows):
    statements = ["DELETE FROM dbo." + _quote(table) + ";"]
    names = [column["name"] for column in columns]
    for row in rows:
        if set(row) != set(names):
            raise ValueError("Complete fixture row required: " + table)
        values = ",".join(_literal(row[name], column) for name, column in zip(names, columns, strict=True))
        statements.append("INSERT dbo." + _quote(table) + " (" +
            ",".join(_quote(name) for name in names) + ") VALUES (" + values + ");")
    return statements


def _script(table, rows, actions, native_path, log_path):
    retention = (SOURCE / SOURCES["retention"][0]).resolve()
    export = (SOURCE / SOURCES["export"][0]).resolve()
    principal = "freshvcf_oracle_replay"
    if principal != __import__("parity.legacy_isolation", fromlist=["PRINCIPAL"]).PRINCIPAL:
        raise ValueError("Restricted replay principal identity differs")
    lines = [
        ":setvar TableName \"" + table + "\"",
        ":setvar ScriptExecutionFlagQuery \"UPDATE ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName=\"",
        "EXECUTE AS LOGIN = '" + principal + "' WITH NO REVERT;",
        "SET XACT_ABORT ON;",
        "BEGIN TRANSACTION;",
        "UPDATE dbo.ImporterSettingsTbl SET Value='7' WHERE Parameter='UIUploadLogHorizon';",
        "IF @@ROWCOUNT<>1 THROW 51000,'UIUploadLogHorizon owner differs',1;",
        "UPDATE dbo.LastBatchRunTbl SET LastRunDate=CONVERT(datetime,N'2026-06-10T00:00:00',126);",
        "IF @@ROWCOUNT<>1 THROW 51000,'LastBatchRunTbl owner differs',1;",
        *_insert(table, NATIVE_SCHEMAS[table], rows),
        *_insert(ACTION_TABLE, ACTION_SCHEMA, actions),
        "GO",
        ':out "' + str(log_path).replace('"', '""') + '"',
        ':r "' + str(retention).replace('"', '""') + '"',
        "GO",
        ':out "' + str(native_path).replace('"', '""') + '"',
        ':r "' + str(export).replace('"', '""') + '"',
        "GO",
        ":out stdout",
        "IF @@TRANCOUNT<>1 THROW 51000,'Fixture transaction ownership differs',1;",
        "ROLLBACK TRANSACTION;",
        "IF @@TRANCOUNT<>0 THROW 51000,'Fixture rollback failed',1;",
    ]
    return "\n".join(lines) + "\n"


def _diff(directory, stem, native, modern):
    native_path, modern_path = directory / (stem + ".native.bin"), directory / (stem + ".modern.bin")
    native_path.write_bytes(native); modern_path.write_bytes(modern)
    text = "".join(difflib.unified_diff(
        native.decode("latin1").splitlines(keepends=True),
        modern.decode("latin1").splitlines(keepends=True),
        fromfile=native_path.name, tofile=modern_path.name))
    diff_path = directory / (stem + ".diff.txt")
    diff_path.write_text(text, encoding="utf-8")
    return {"native": str(native_path), "modern": str(modern_path), "diff": str(diff_path)}


def run(owner, output):
    output = Path(output).resolve()
    if (owner != OWNER or not output.is_relative_to(Path('D:/freshvcf-build/evidence/cohort2-20261008-001').resolve())
            or output.suffix != '.json' or output.exists()):
        raise ValueError('Exact owned Cohort2 evidence path and SQL owner required')
    from parity import legacy_isolation as isolation
    _, preparation = prepare(owner, isolation)
    os.environ["VFTEST_PROFILE"] = "fresh"
    sources = source_pins()
    code_pins = implementation_pins()
    tool_pin = pin(SQLCMD)
    directory = output.with_suffix("")
    directory.mkdir(exist_ok=False)
    receipt = {
        "schema": "operational-upload-files-native-qualification-v1",
        "status": "STARTED", "owner": owner, "namespace": namespace(owner),
        "data_directory": str(data_directory(owner)), "preparation": preparation,
        "sources": sources, "sqlcmd_sha256": tool_pin, "implementation_pins": code_pins,
        "scope": "eight direct ClearUIUploadLogHistory + ExportUIUploadLog rollback fixtures; zero engine/day invocations",
        "ordering_policy": "strict native byte sequence; no ordering qualification or sorting",
        "cases": [],
    }
    try:
        with isolation.exclusive_replay(validate_schema=True):
            receipt["schema_receipts"] = [json.loads((data_directory(owner) / (db + "-schema.json")).read_text())
                for db in namespace(owner).values()]
            with isolation.connection("VFTEST_Importer") as raw:
                receipt["native_context"] = native_context(raw, isolation)
                sql = FixtureSQL(raw, isolation)
                originals = {key: sql.rows(*key) for key in PRESERVED}
                # Require exact native table shapes before the first SQLCMD mutation.
                for table, columns in {**NATIVE_SCHEMAS, ACTION_TABLE: ACTION_SCHEMA}.items():
                    actual = [column for column in sql.schema(IMPORTER, table)
                              if not column["identity"] and not column["computed"]]
                    def declared(column):
                        kind, parameters = column["type"], column["parameters"]
                        width = -1 if parameters == "max" else (int(parameters) * 2
                            if parameters is not None and kind in ("nvarchar", "nchar") else
                            int(parameters) if parameters is not None and kind in ("varchar", "char") else None)
                        precision, scale = ((map(int, parameters.split(",")))
                                            if kind in ("decimal", "numeric") else (None, None))
                        return (column["name"].casefold(), kind, column["nullable"],
                                width, precision, scale)
                    wanted = [declared(column) for column in columns]
                    observed = [(column["name"].casefold(), column["type_name"], bool(column["nullable"]),
                                 column["max_length"] if column["type_name"] in
                                 ("nvarchar", "nchar", "varchar", "char") else None,
                                 column["precision"] if column["type_name"] in ("decimal", "numeric") else None,
                                 column["scale"] if column["type_name"] in ("decimal", "numeric") else None)
                                for column in actual]
                    if observed != wanted:
                        receipt.setdefault("schema_differences", []).append({
                            "table": table, "observed": observed, "declared": wanted,
                        })
                if receipt.get("schema_differences"):
                    raise ValueError("Native upload-log schemas differ: " + ", ".join(
                        item["table"] for item in receipt["schema_differences"]))
                for table, _ in LOG_BINDINGS:
                    for case_name, rows, actions in fixture_cases(table):
                        retained = clear_ui_upload_log_history(table_name=table, rows=rows,
                            today="2026-06-10", history_horizon=7)
                        projection = export_ui_upload_log(table_name=table, rows=retained,
                                                          action_types=actions)
                        modern = upload_log_bytes(projection)
                        stem = table + "-" + case_name
                        native_path, log_path = directory / (stem + ".native.csv"), directory / (stem + ".clear.log")
                        script_path = directory / (stem + ".sql")
                        script_path.write_text(_script(table, rows, actions, native_path, log_path),
                                               encoding="utf-8", newline="\n")
                        command = [str(SQLCMD), "-C", "-E", "-S", "localhost", "-d",
                            namespace(owner)["VFTEST_Importer"], "-b", "-r", "1", "-f", "i:65001",
                            "-i", str(script_path), "-h-1", "-W", "-s", ","]
                        completed = subprocess.run(command, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
                        native = native_path.read_bytes() if native_path.exists() else b""
                        passed = completed.returncode == 0 and native == modern
                        item = {"table": table, "case": case_name, "status": "PASS" if passed else "FAIL",
                            "fixture_rows": storage(rows), "action_rows": storage(actions),
                            "retained_rows": storage(retained), "script_sha256": pin(script_path),
                            "returncode": completed.returncode, "stdout_hex": completed.stdout.hex(),
                            "stderr_hex": completed.stderr.hex(), "native_sha256": hashlib.sha256(native).hexdigest(),
                            "modern_sha256": hashlib.sha256(modern).hexdigest(),
                            "native_size": len(native), "modern_size": len(modern)}
                        receipt["cases"].append(item)
                        if not passed:
                            item["strict_diff"] = _diff(directory, stem, native, modern)
                receipt["preservation"] = {"/".join(key): compare_rows(sql.rows(*key), rows, sql.schema(*key))
                                            for key, rows in originals.items()}
                if any(item["status"] != "PASS" for item in receipt["preservation"].values()):
                    raise ValueError("SQLCMD rollback did not preserve every touched/source table")
                failed = [item["table"] + "/" + item["case"] for item in receipt["cases"]
                          if item["status"] != "PASS"]
                if failed:
                    raise ValueError("Native upload-log byte differences: " + ", ".join(failed))
        receipt["status"] = "PASS"
    except Exception as error:
        receipt.update(status="FAIL", failure_type=type(error).__name__, failure=str(error))
    finally:
        receipt["implementation_identity_unchanged"] = implementation_pins() == code_pins
        receipt["source_identity_unchanged"] = source_pins() == sources
        receipt["tool_identity_unchanged"] = pin(SQLCMD) == tool_pin
        if not all((receipt["implementation_identity_unchanged"], receipt["source_identity_unchanged"],
                    receipt["tool_identity_unchanged"])):
            receipt.update(status="FAIL", failure="Implementation/source/tool identity changed")
        with output.open("x", encoding="utf-8") as stream:
            json.dump(storage(receipt), stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    result = run(options.owner, options.output)
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]),
                      "output": str(options.output)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
