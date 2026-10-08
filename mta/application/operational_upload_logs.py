"""Pure retention and export projections for the eight native UI upload logs.

The canonical exporter delegates scalar spelling, delimiters, whitespace and
line endings to SQL Server plus ``sqlcmd``.  This module therefore returns the
two typed result sets and conversion instructions; it does not claim CSV bytes.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path

from mta.application.operational_inputs import TEXT_TYPES, typed_value


SOURCES = {
    "bindings": ("Engine/GenerateUIUploadLogs.bat",
        "656da66db2a0e7e653b24b66c57765f168a64119fb928074ef76e7c55c222be3"),
    "wrapper": ("Engine/ExportUIUploadLog.bat",
        "e22099dca963ace3dae23e2cc6ff247eaa4e3c42f5db882aa59646b50aadd847"),
    "retention": ("Scripts/Importer/ClearUIUploadLogHistory.sql",
        "8acffa51420fae6c9263dc1f3e20c52212914aee91491b16f15db10d74c6e90e"),
    "export": ("Scripts/Importer/ExportUIUploadLog.sql",
        "a8261731b1482229959192e3518f7294f9090a22377732f03d5094b3baffb3e6"),
    "ddl": ("Scripts/DBCreation/Importer_DBCreation.sql",
        "11c004b7d790bf560549bcad8e3342c3bed15972a63d9e0f26458392edea6309"),
}

SCHEMA_SHA256 = "e3bd3c715a19c78e64c287bbbe63496a77a9c325f709a74c5499b258f5acc079"
_schema_path = Path(__file__).resolve().parents[2] / "baseline/cohort2-native-source-schema.json"
_schema_bytes = _schema_path.read_bytes()
if hashlib.sha256(_schema_bytes).hexdigest() != SCHEMA_SHA256:
    raise ValueError("Pinned Cohort2 native source schema differs")
_schema = json.loads(_schema_bytes)

LOG_BINDINGS = (
    ("UIUploadLogNMSNewItem", "NMSAddNewSKULocLog"),
    ("UIUploadLogNMSModifyItem", "NMSModifySKULocLog"),
    ("UIUploadLogNMSRemoveItem", "NMSRemoveSKULocLog"),
    ("UIUploadLogNMSLocations", "NMSLocMasterLog"),
    ("UIUploadLogNMSSKUs", "NMSSKUMasterLog"),
    ("UIUploadLogNMSSOB", "NMSSOBMasterLog"),
    ("UIUploadLogNMSMOQ", "NMSMOQMasterLog"),
    ("UIUploadLogFNC", "ForceNormChangeUploadLog"),
)
NATIVE_SCHEMAS = {name: tuple(_schema["tables"]["Importer/" + name])
                  for name, _ in LOG_BINDINGS}
ACTION_SCHEMA = tuple(_schema["tables"]["Importer/UIUploadLogActionType"])

NATIVE_FORMATTER_REQUIREMENTS = {
    "sqlcmd_flags": ("-h-1", "-W", "-s", ","),
    "header": "first one-cell result set; embedded commas originate in SQL",
    "body": "SQL Server CONVERT(nvarchar(256), value), then NULLIF/ISNULL; ActionTimeStamp and ActionDesc remain native",
    "bytes": "require the pinned SQL Server/sqlcmd execution boundary; no Python byte spelling is asserted",
}


def _binding(table_name):
    if not isinstance(table_name, str):
        raise ValueError("Explicit canonical UI upload-log table required")
    try:
        report_name = dict(LOG_BINDINGS)[table_name]
    except KeyError:
        raise ValueError("Unknown canonical UI upload-log table: " + table_name) from None
    return report_name, NATIVE_SCHEMAS[table_name]


def _validated(rows, columns, name):
    if not isinstance(rows, list):
        raise ValueError(name + " must be an explicit row list")
    names = {column["name"] for column in columns}
    result = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != names:
            raise ValueError(name + " fields differ from the native source contract")
        result.append({column["name"]: typed_value(row[column["name"]], column, reserve_null_token=False)
                       for column in columns})
    return result


def clear_ui_upload_log_history(*, table_name, rows, today, history_horizon):
    """Apply the canonical date-only delete boundary to one complete log bag."""
    _, columns = _binding(table_name)
    typed = _validated(rows, columns, table_name)
    if isinstance(today, str):
        today = date.fromisoformat(today)
    if type(today) is not date or type(history_horizon) is not int:
        raise ValueError("Explicit native run date and UIUploadLogHorizon int required")
    last_date = today - timedelta(days=history_horizon + 1)
    retained = []
    for source, row in zip(rows, typed, strict=True):
        timestamp = row["ActionTimeStamp"]
        # SQL Convert(Date, ActionTimeStamp) removes the wall-clock component.
        if timestamp.date() > last_date:
            retained.append(deepcopy(source))
    return retained


def _converted_cell(value, column):
    """Represent the SQL conversion without guessing native numeric spelling."""
    if value is None or value == "":
        return {"value": "-", "sql_type": "nvarchar(256)", "native_conversion": None}
    if column["type"] in TEXT_TYPES:
        return {"value": value, "sql_type": "nvarchar(256)", "native_conversion": None}
    return {"value": value, "source_type": column["type"],
            "sql_type": "nvarchar(256)",
            "native_conversion": "CONVERT(nvarchar(256), source_value)"}


def export_ui_upload_log(*, table_name, rows, action_types):
    """Return the canonical header and joined body as typed result-set cells."""
    report_name, columns = _binding(table_name)
    logs = _validated(rows, columns, table_name)
    actions = _validated(action_types, ACTION_SCHEMA, "UIUploadLogActionType")
    body_columns = tuple(column for column in columns
                         if column["name"] not in ("ActionId", "ActionTimeStamp"))
    output_columns = tuple(column["name"] for column in columns
                           if column["name"] != "ActionId") + ("Action",)
    header = ",".join(output_columns)
    projected = []
    for row in logs:
        for action in actions:
            if row["ActionId"] != action["ActionId"]:
                continue
            cells = tuple(_converted_cell(row[column["name"]], column)
                          for column in body_columns)
            cells += (
                {"value": row["ActionTimeStamp"], "sql_type": "datetime",
                 "native_conversion": None},
                {"value": action["ActionDesc"], "sql_type": "nvarchar(128)",
                 "native_conversion": None},
            )
            projected.append(cells)
    return {
        "table_name": table_name,
        "report_name": report_name,
        "header_result_set": (({"value": header, "sql_type": "nvarchar(4000)"},),),
        "data_columns": output_columns,
        "data_result_set": tuple(projected),
        "native_formatter_requirements": NATIVE_FORMATTER_REQUIREMENTS,
    }
