"""Pinned pure history aggregations for the existing frontend."""
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

def _colour_counts(rows: list[dict]) -> list[dict]:
    grouped: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        grouped[row["date"]][row["PhysicalColor"]] += 1
    return [{"date": day, "Black": values["Black"], "Red": values["Red"],
             "Yellow": values["Yellow"], "Green": values["Green"],
             "White": values["White"], "Blue": values["Blue"]}
            for day, values in sorted(grouped.items())]

def _historical_availability(rows: list[dict]) -> list[dict]:
    """Project the deployed D1..D90 historical-availability buckets."""
    if not rows:
        return [{
            "availability_01_30": 0,
            "availability_31_60": 0,
            "availability_61_90": 0,
        }]

    # D1..D30 is the oldest band shown as 90-60 days; D61..D90 is the
    # newest band shown as 30-0 days. Missing retained days add no rows.
    latest = max(date.fromisoformat(row["date"]) for row in rows)
    totals = [0, 0, 0]
    black = [0, 0, 0]
    for row in rows:
        age = (latest - date.fromisoformat(row["date"])).days
        if age < 0 or age >= 90:
            continue
        bucket = 2 - age // 30
        totals[bucket] += 1
        black[bucket] += row["PhysicalColor"] == "Black"

    def available(index: int) -> float | int:
        if totals[index] == 0:
            return 0
        return float(round(
            Decimal(totals[index] - black[index]) / Decimal(totals[index]) * Decimal(100),
            2,
        ))

    return [{
        "availability_01_30": available(0),
        "availability_31_60": available(1),
        "availability_61_90": available(2),
    }]

def _buffer_trend_graph(rows: list[dict], trend_type: str) -> dict:
    """Project the selected deployed GetBufferTrendGraphData response.

    The canonical processor reads the physical-inventory history for ``tech``
    and dispatch history for ``eco``.  Its React consumer requires two dated
    series plus the two-row summary and availability value; returning the raw
    history aggregate leaves the accepted route visibly empty.
    """
    colour_field = "DispatchColor" if str(trend_type).casefold() == "eco" else "PhysicalColor"
    grouped: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        grouped[row["date"]][row[colour_field]] += 1

    aliases = (("b", "Black"), ("r", "Red"), ("y", "Yellow"),
               ("g", "Green"), ("bu", "Blue"), ("w", "White"))
    absolute = []
    totals = Counter()
    for day, values in sorted(grouped.items()):
        projected = {"dt": date.fromisoformat(day).strftime("%d-%m-%Y")}
        for alias, colour_name in aliases:
            count = values[colour_name]
            projected[alias] = str(count)
            totals[alias] += count
        absolute.append(projected)

    def percentage(value: int, total: int) -> str:
        if total == 0:
            return "0"
        rounded = round(Decimal(value) / Decimal(total) * Decimal(100), 2)
        return format(rounded, "f")

    percentage_rows = []
    for row in absolute:
        total = sum(int(row[alias]) for alias, _ in aliases)
        percentage_rows.append({
            "dt": row["dt"],
            **{alias: percentage(int(row[alias]), total) for alias, _ in aliases},
        })

    total = sum(totals.values())
    summary = [
        {"category": "Absolute Value", **{
            "sum" + alias.upper(): str(totals[alias]) for alias, _ in aliases
        }},
        {"category": "Percentage", **{
            "sum" + alias.upper(): percentage(totals[alias], total) for alias, _ in aliases
        }},
    ]
    availability = percentage(total - totals["b"], total)
    return {"absolute": absolute, "percentage": percentage_rows,
            "summary": summary, "avail": availability}
