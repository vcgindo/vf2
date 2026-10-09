"""Pure port of Importer/ValidateSeasonalityData.sql.

The caller supplies the ``Seasonality``, ``MasterData``, and ``RejectedMaster``
populations produced by the importer chain.  This step belongs after process
master validation and before daily validation.  It does not write SQL or run a
business day.

The native script uses SQL equality for joins.  In particular, NULL values
group during duplicate detection but never compare equal during deletion.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence


_SCRATCH_TABLES = (
    "DuplicateChecker",
    "InvalidSKULoc",
    "SeasonalityType",
    "ShortSeasonLowerNorm",
    "ShortBuiltupDurLowerNorm",
)


def _sql_key(value: Any) -> Any:
    if isinstance(value, str):
        return value.rstrip().upper()
    return value


def _pair(row: Mapping[str, Any]) -> tuple[Any, Any]:
    return (_sql_key(row["SKUCode"]), _sql_key(row["WhCode"]))


def _sql_join(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_pair = _pair(left)
    right_pair = _pair(right)
    if None in left_pair or None in right_pair:
        return False
    return left_pair == right_pair


def _sql_less_than(left: Any, right: Any) -> bool:
    return left is not None and right is not None and left < right


def _as_date(value: Any, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO date or datetime") from exc
    raise TypeError(f"{field} must be a date, datetime, or ISO string")


def _datediff_days(start: Any, end: Any) -> int | None:
    if start is None or end is None:
        return None
    return (_as_date(end, "EndDate") - _as_date(start, "StartDate")).days


def _require_rows(
    name: str,
    rows: Sequence[Mapping[str, Any]],
    required: Iterable[str],
) -> list[dict[str, Any]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise TypeError(f"{name} must be a sequence of mappings")
    required_fields = tuple(required)
    copied: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise TypeError(f"{name}[{ordinal}] must be a mapping")
        missing = [field for field in required_fields if field not in row]
        if missing:
            raise ValueError(f"{name}[{ordinal}] missing fields: {', '.join(missing)}")
        copied.append(deepcopy(dict(row)))
    return copied


def _rejection(
    row: Mapping[str, Any],
    run_timestamp: str,
    reason_code: int,
    description: str,
) -> dict[str, Any]:
    return {
        "SKUCode": row["SKUCode"],
        "WhCode": row["WhCode"],
        "RejectionDate": run_timestamp,
        "ReasonCode": reason_code,
        "ReasonDescription": description,
    }


def _delete_by_sql_join(
    rows: list[dict[str, Any]],
    rejected_pairs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if not any(_sql_join(row, rejected) for rejected in rejected_pairs)
    ]


def _retain_existing_types(
    typed_rows: list[dict[str, Any]],
    seasonality: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    # Port of LEFT JOIN Seasonality ... WHERE B.SKUCode IS NULL deletion.
    return [
        typed
        for typed in typed_rows
        if any(_sql_join(typed, row) for row in seasonality)
    ]


def _empty_scratch() -> dict[str, list[dict[str, Any]]]:
    return {name: [] for name in _SCRATCH_TABLES}


def validate_seasonality_data(
    seasonality: Sequence[Mapping[str, Any]],
    master_data: Sequence[Mapping[str, Any]],
    rejected_master: Sequence[Mapping[str, Any]],
    run_timestamp: str,
) -> dict[str, Any]:
    """Validate staged seasonality rows using the native importer sequence.

    The result contains replacement ``seasonality`` and ``rejected_master``
    populations.  ``stages`` and ``scratch`` expose the native control-flow and
    clearing contract for focused acceptance evidence; all returned data is a
    deep copy of caller-owned input.
    """

    if not isinstance(run_timestamp, str):
        raise TypeError("run_timestamp must be a string")

    season_rows = _require_rows(
        "seasonality",
        seasonality,
        (
            "SKUCode",
            "WhCode",
            "StartDate",
            "EndDate",
            "TargetNorm",
            "DeltaNormPercentage",
            "BuildupDuration",
            "Approved",
        ),
    )
    masters = _require_rows(
        "master_data", master_data, ("SKUCode", "WhCode", "Norm", "RLT")
    )
    rejections = _require_rows(
        "rejected_master",
        rejected_master,
        ("SKUCode", "WhCode", "RejectionDate", "ReasonCode", "ReasonDescription"),
    )
    initial_rejection_count = len(rejections)
    scratch = _empty_scratch()
    stages = ["clear_all:before", "approved_gate"]

    # RETURN is at batch scope in the native script.  Its trailing scratch clear
    # is therefore not reached, although the initial clear already left scratch
    # empty.
    if not any(row["Approved"] == 1 for row in season_rows):
        stages.append("early_return")
        return {
            "outcome": "EARLY_RETURN",
            "seasonality": season_rows,
            "rejected_master": rejections,
            "rejections_added": 0,
            "scratch": scratch,
            "stages": tuple(stages),
        }

    stages.append("duplicate_check")
    grouped: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for row in season_rows:
        grouped.setdefault(_pair(row), []).append(row)
    scratch["DuplicateChecker"] = [
        {"SKUCode": rows[0]["SKUCode"], "WhCode": rows[0]["WhCode"]}
        for rows in grouped.values()
        if len(rows) > 1
    ]
    stages.append("reject:201")
    for row in scratch["DuplicateChecker"]:
        rejections.append(
            _rejection(
                row,
                run_timestamp,
                201,
                "Seasonality data : Record provided multiple times in the input",
            )
        )
    stages.append("delete:201")
    season_rows = _delete_by_sql_join(season_rows, scratch["DuplicateChecker"])

    stages.append("missing_master_check")
    scratch["InvalidSKULoc"] = [
        {"SKUCode": row["SKUCode"], "WhCode": row["WhCode"]}
        for row in season_rows
        if not any(_sql_join(row, master) for master in masters)
    ]
    stages.append("reject:202")
    for row in scratch["InvalidSKULoc"]:
        rejections.append(
            _rejection(
                row,
                run_timestamp,
                202,
                "Seasonality data : Record not present in the master",
            )
        )
    stages.append("delete:202")
    season_rows = _delete_by_sql_join(season_rows, scratch["InvalidSKULoc"])

    stages.append("type_assign")
    scratch["SeasonalityType"] = []
    for row in season_rows:
        seasonality_type = 1 if row["EndDate"] is not None else 2
        for master in masters:
            if _sql_join(row, master) and (
                _sql_less_than(row["TargetNorm"], master["Norm"])
                or _sql_less_than(row["DeltaNormPercentage"], 0)
            ):
                seasonality_type = 3 if seasonality_type == 1 else 4
                break
        scratch["SeasonalityType"].append(
            {
                "SKUCode": row["SKUCode"],
                "WhCode": row["WhCode"],
                "StartDate": row["StartDate"],
                "EndDate": row["EndDate"],
                "TargetNorm": row["TargetNorm"],
                "DeltaNormPercentage": row["DeltaNormPercentage"],
                "BuildupDuration": row["BuildupDuration"],
                "SeasonalityType": seasonality_type,
            }
        )

    stages.extend(("clear:InvalidSKULoc", "check:204"))
    scratch["InvalidSKULoc"] = [
        {"SKUCode": row["SKUCode"], "WhCode": row["WhCode"]}
        for row in scratch["SeasonalityType"]
        if row["SeasonalityType"] == 3 and row["BuildupDuration"] is None
    ]
    stages.append("reject:204")
    for row in scratch["InvalidSKULoc"]:
        rejections.append(
            _rejection(
                row,
                run_timestamp,
                204,
                "Buildup duration is not provided. (Lower Norm during Season type)",
            )
        )
    stages.append("delete:204")
    season_rows = _delete_by_sql_join(season_rows, scratch["InvalidSKULoc"])
    scratch["SeasonalityType"] = _retain_existing_types(
        scratch["SeasonalityType"], season_rows
    )

    stages.append("check:205")
    scratch["ShortSeasonLowerNorm"] = []
    for row in scratch["SeasonalityType"]:
        season_days = _datediff_days(row["StartDate"], row["EndDate"])
        if (
            row["SeasonalityType"] == 3
            and season_days is not None
            and row["BuildupDuration"] is not None
            and season_days < row["BuildupDuration"]
        ):
            scratch["ShortSeasonLowerNorm"].append(
                {
                    "SKUCode": row["SKUCode"],
                    "WhCode": row["WhCode"],
                    "BuildupDuration": row["BuildupDuration"],
                    "SeasonDur": season_days,
                }
            )
    stages.append("reject:205")
    for row in scratch["ShortSeasonLowerNorm"]:
        description = (
            "Buildup duration is larger than Season duration. Buildup Dur="
            f"{row['BuildupDuration']}, Season Dur={row['SeasonDur']}"
        )
        rejections.append(_rejection(row, run_timestamp, 205, description))
    stages.append("delete:205")
    season_rows = _delete_by_sql_join(
        season_rows, scratch["ShortSeasonLowerNorm"]
    )
    scratch["SeasonalityType"] = _retain_existing_types(
        scratch["SeasonalityType"], season_rows
    )

    stages.append("check:206")
    scratch["ShortBuiltupDurLowerNorm"] = []
    for row in scratch["SeasonalityType"]:
        if row["SeasonalityType"] != 3:
            continue
        for master in masters:
            if _sql_join(row, master) and _sql_less_than(
                row["BuildupDuration"], master["RLT"]
            ):
                scratch["ShortBuiltupDurLowerNorm"].append(
                    {
                        "SKUCode": row["SKUCode"],
                        "WhCode": row["WhCode"],
                        "BuildupDuration": row["BuildupDuration"],
                        "RLT": master["RLT"],
                    }
                )
    stages.append("reject:206")
    for row in scratch["ShortBuiltupDurLowerNorm"]:
        description = (
            f"Buildup duration is smaller than RLT. RLT={row['RLT']}, "
            f"Buildup Dur={row['BuildupDuration']}"
        )
        rejections.append(_rejection(row, run_timestamp, 206, description))
    stages.append("delete:206")
    season_rows = _delete_by_sql_join(
        season_rows, scratch["ShortBuiltupDurLowerNorm"]
    )

    stages.append("clear_all:after")
    scratch = _empty_scratch()
    return {
        "outcome": "VALIDATED",
        "seasonality": season_rows,
        "rejected_master": rejections,
        "rejections_added": len(rejections) - initial_rejection_count,
        "scratch": scratch,
        "stages": tuple(stages),
    }
