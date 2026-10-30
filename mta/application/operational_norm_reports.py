"""Pure O6 adapter over the typed ``read_outputs()['Reports']`` owner.

The accepted DBM projections have already applied the canonical joins, date
horizons and dynamic report configuration.  This adapter validates and labels
those result cells; it never recalculates a report or invents file bytes.
"""
from copy import deepcopy
from datetime import date


SOURCES = {
    "dbm_wrapper": ("Engine/SendDBMNormChangeReport.bat",
        "37aad4ea93fb9465f65430183be4fddb874ac5f738d55f2bf8e435b157656cf3"),
    "dbm_sql": ("Scripts/DBM/DBMNormChange/ExportDBMNormChange.sql",
        "940f0e1a92b97063b91799fa7724071128fcc592ff54a43596eb101a52280aff"),
    "history_wrapper": ("Engine/GenerateNormChangeLogReport.bat",
        "8d858b9598f8ff9e8285515d27ed358e8eef2fe9713b5b49fa3b8a30f1af4db1"),
    "history_sql": ("Scripts/DBM/NormChangeHistory.sql",
        "f1ba8fbcd213c428ebc1ef2a89f76c47b0d2685c02718c9c5f1cb0c1d611a8aa"),
    "activation": ("Engine/CheckFlagForNorm0-1-2Reports.bat",
        "9d4d52dd5e101f53f1a315362eb67ee075bc18048a6f1793b72c5fd8cc8cdee7"),
    "norm_wrapper": ("Engine/GenerateNorm0-1-2Report.bat",
        "fcfd8c93659d245c792209c5ae5f58471a8f9754e0f3e1647d09782d8ae2ff47"),
    "norm1_data": ("Scripts/DBM/Norm 0-1-2 Reports/Norm1Data.sql",
        "64c58d14390ce1133ff39ccb7c619827fc7c4e01625188e92f9dfe15ef53e7d2"),
    "norm2_data": ("Scripts/DBM/Norm 0-1-2 Reports/Norm2Data.sql",
        "9edb9e13504f36d6655cb762aa81853cdd10a4e44bba876fee3ffc8c83c16870"),
    "norm_detail": ("Scripts/DBM/Norm 0-1-2 Reports/GenerateNorm0-1-2Report.sql",
        "d3e0313e1045bda9bf1ea79d2baa4548581d7612e04d92e8127e93f3a7abe72e"),
    "norm_export": ("Scripts/DBM/Norm 0-1-2 Reports/ExportNorm0-1-2Report.sql",
        "45e728d47d5e84b13e6a70460d5c93473938b6bfff50b03fd26d5e1218e53ff2"),
    "norm_clear": ("Scripts/DBM/Norm 0-1-2 Reports/ClearNorm0-1-2ReportData.sql",
        "f8623424bb3e0d4580c26e0c83241801e94b407b81489c090ee0c364b6ae9c0d"),
    "report_configuration": ("Scripts/DBCreation/UI_ReportConfiguration.sql",
        "65141b0418028a01e06f7ec6bfac0ca06802c65d12a8cc84a4e0d16278894352"),
}

REQUIRED_CONFIGURATION = {
    "DBMNormChangeReportHorizon": 1,
    "NormChangeLogHorizon": 7,
    "ActivateNormChangeLogReport": 1,
    "ActivateNorm0Report30Days": 0,
    "ActivateNorm0Report60Days": 0,
    "ActivateNorm0Report90Days": 0,
    "ActivateNorm1Report30Days": 1,
    "ActivateNorm2Report30Days": 1,
}

DBM_HEADER = ("SKUCode", "Location", "New Norm", "Old Norm", "Norm Change Date", "Reason")
HISTORY_HEADER = ("SKUCode", "SKU Name", "Loc Code", "Loc Name", "OldNorm", "NewNorm",
                  "NormChangeDate", "Reason")
NORM_HEADER = ("SKUCode", "SKUName", "WHCode", "WHName", "ParentCode", "ParentNorm",
               "NumOfDaysSold", "TotalSale", "Occurances")

# (logical type, nullable, maximum UTF-16 code units when applicable)
DBM_CELLS = (("nvarchar", False, 50), ("nvarchar", False, 50), ("int", False, None),
             ("int", False, None), ("iso-date-text", False, 10), ("nvarchar", True, 252))
HISTORY_CELLS = (("nvarchar", False, 50), ("nvarchar", True, 125),
                 ("nvarchar", False, 50), ("nvarchar", True, 125),
                 ("int", False, None), ("int", False, None),
                 ("date", False, None), ("nvarchar", True, 250))
NORM_CELLS = tuple(("nvarchar-export", False, None) for _ in NORM_HEADER)

REPORT_BINDINGS = (
    ("DBMNormChange", "norm-change-export", "DBMNormChange.csv", 1, DBM_HEADER, DBM_CELLS),
    ("NormChangeLog", "norm-change-history", "NormChangeLogReport.csv", 7,
     HISTORY_HEADER, HISTORY_CELLS),
    ("Norm1_30days", "norm1-export", "Norm_1_Report_30Days.csv", 30,
     NORM_HEADER, NORM_CELLS),
    ("Norm2_30days", "norm2-export", "Norm_2_Report_30Days.csv", 30,
     NORM_HEADER, NORM_CELLS),
)

NATIVE_FORMATTER_REQUIREMENTS = {
    "sqlcmd_flags": ("-h-1", "-W", "-s", ","),
    "cell_contract": "values are already canonical SQL projection cells from the typed Reports owner",
    "bytes": "pinned SQL Server/sqlcmd must supply delimiter, NULL, whitespace, encoding and line endings",
    "unsupported_adapter_values": ("bool", "float", "decimal", "bytes", "date/datetime objects"),
}


def _stages(reports):
    if not isinstance(reports, list):
        raise ValueError("Complete read_outputs Reports list required")
    found = {}
    for item in reports:
        if not isinstance(item, dict) or set(item) != {"stage", "tables"}:
            raise ValueError("Reports stage shape differs")
        if not isinstance(item["stage"], str) or not isinstance(item["tables"], dict):
            raise ValueError("Reports stage types differ")
        found.setdefault(item["stage"], []).append(item["tables"])
    required = {binding[1] for binding in REPORT_BINDINGS}
    if any(len(found.get(stage, [])) != 1 for stage in required):
        raise ValueError("Each required typed Reports stage must occur exactly once")
    return {stage: found[stage][0] for stage in required}


def _values(rows, width, name):
    if not isinstance(rows, list):
        raise ValueError(name + " must be an explicit typed result-set list")
    result = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"values"} or not isinstance(row["values"], list):
            raise ValueError(name + " result row shape differs")
        if len(row["values"]) != width:
            raise ValueError(name + " result row width differs")
        result.append(row["values"])
    return result


def _cell(value, specification, report_name, column):
    kind, nullable, width = specification
    if value is None:
        if not nullable:
            raise ValueError(f"NULL in required {report_name} cell {column}")
        return {"value": None, "native_type": kind}
    if kind == "int":
        if type(value) is not int:
            raise ValueError(f"Native int required in {report_name} cell {column}")
    elif kind in ("nvarchar", "nvarchar-export", "iso-date-text"):
        if not isinstance(value, str):
            raise ValueError(f"Native text required in {report_name} cell {column}")
        if width is not None and len(value.encode("utf-16-le")) // 2 > width:
            raise ValueError(f"Native text width exceeded in {report_name} cell {column}")
        if kind == "iso-date-text":
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError(f"ISO date text required in {report_name} cell {column}") from None
    elif kind == "date":
        if not isinstance(value, str):
            raise ValueError(f"Persisted native date text required in {report_name} cell {column}")
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError(f"Persisted native date text required in {report_name} cell {column}") from None
    else:
        raise ValueError("Unsupported O6 cell type: " + kind)
    return {"value": deepcopy(value), "native_type": kind}


def norm_report_resultsets(*, reports, configuration, occurrence_text_policy=None):
    """Validate and label the four enabled generic report result sets."""
    if not isinstance(configuration, dict) or configuration != REQUIRED_CONFIGURATION:
        raise ValueError("Exact generic O6 activation and horizon source identity required")
    stages = _stages(reports)
    result = {}
    for name, stage, filename, horizon, expected_header, specifications in REPORT_BINDINGS:
        tables = stages[stage]
        if "ReportHeader" not in tables or "ReportRows" not in tables:
            raise ValueError("Required typed report source absent: " + stage)
        headers = _values(tables["ReportHeader"], len(expected_header), stage + "/ReportHeader")
        if headers != [list(expected_header)]:
            raise ValueError("Canonical report header differs: " + stage)
        rows = _values(tables["ReportRows"], len(expected_header), stage + "/ReportRows")
        typed_rows = tuple(tuple(_cell(value, specification, name, expected_header[index])
                                 for index, (value, specification) in enumerate(zip(row, specifications, strict=True)))
                           for row in rows)
        if stage == "norm-change-history":
            dates = [date.fromisoformat(row[6]["value"]) for row in typed_rows]
            if dates != sorted(dates, reverse=True):
                raise ValueError("NormChangeHistory source order is not date-descending")
        result[name] = {
            "source_stage": stage,
            "horizon_days": horizon,
            "csv_name": filename,
            "header_result_set": tuple({"value": value, "native_type": "varchar-literal"}
                                       for value in expected_header),
            "data_result_set": typed_rows,
            "native_formatter_requirements": NATIVE_FORMATTER_REQUIREMENTS,
        }
        if occurrence_text_policy is not None and stage in ('norm1-export', 'norm2-export'):
            from mta.application import occurrence_text_policy as policy
            norm = 1 if stage == 'norm1-export' else 2
            policy.verify_export(tables, occurrence_text_policy, norm=norm)
            result[name].update(occurrence_text_policy=deepcopy(occurrence_text_policy),
                occurrence_classification=policy.CLASSIFICATION,
                occurrence_text_availability=policy.summaries(
                    [dict(stage=stage, tables=tables)], occurrence_text_policy)[stage])
    return result
