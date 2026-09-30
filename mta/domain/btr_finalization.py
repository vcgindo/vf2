"""Selected Buffer Trend and guided-insight finalization, without I/O.

The contract is pinned in
``.local-stage7/block3-one-pass/delivery-v1/btr-source-contract.json``.
Rows remain SQL-style bags.  Deterministic aggregate multiplicity is preserved;
undefined latest-row or update-source choices are rejected.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import quoteattr


DAYS = tuple(f"D{i}" for i in range(1, 91))
COLOURS = ("White", "Blue", "Green", "Yellow", "Red", "Black")
BPR_SOURCE_FIELDS = (
    "SKUCode", "WhCode", "ParentWhCode", "Norm", "Stock", "TechPen",
    "TechColor", "GIT", "EcoPen", "EcoColor", "VirtualNorm",
    "DispatchPen", "DispatchColor", "PhysicalInventoryPen",
    "PhysicalInventoryColor",
)
BPR_FIELDS = ("SKUCode", "WHCode") + BPR_SOURCE_FIELDS[2:]
PRIOR_TABLES = (
    "BPR", "LocationAttributeData", "SiteDescriptionTbl", "SkuAttributeData",
    "SKUDescriptionTbl", "SkuLocAttributeData",
)
FACT_TABLES = (
    "BPR_Table", "vf_RationedReqReport", "DBMMaster", "Suggestions",
    "SuggestionsLog", "NormChangeLogTbl", "SuspendHistory", "DailyConsumption",
    "LocationAttributeData", "SiteDescriptionTbl", "SkuAttributeData",
    "SkuLocAttributeData", "SKUDescriptionTbl", "CWH_List", "DistributorList",
    "MasterData", "SKULocStandardAttributes", "GoodsInTransitTransporterMaster",
    "ExpediteDispatches",
)
SETTING_NAMES = (
    "CaptureDispatchExecutionEfficiency", "GenerateColorAgeingReport",
    "BRAgeColorTolerance", "CARNoColorToleranceDuration",
    "NormSuggestion_Upward", "NormSuggestion_Downward",
)


def _day(value):
    if type(value) is date:
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise ValueError(f"invalid date value {value!r}")


def _key(row):
    location = row["WhCode"] if "WhCode" in row else row.get("WHCode")
    if location is None:
        raise KeyError("WhCode")
    return row["SKUCode"], location


def _require_rows(container, names, label):
    missing = [name for name in names if name not in container]
    if missing:
        raise ValueError(f"{label} roster drift: missing {missing}")
    for name in names:
        if not isinstance(container[name], list):
            raise ValueError(f"{label}.{name} must be a row list")


def _setting(settings, name):
    if name not in settings:
        raise ValueError(f"settings roster drift: missing {name}")
    return settings[name]


def _selected_settings(settings):
    missing = [name for name in SETTING_NAMES if name not in settings]
    if missing:
        raise ValueError(f"settings roster drift: missing {missing}")
    if str(settings["CaptureDispatchExecutionEfficiency"]) != "0":
        raise ValueError("selected BTR contract excludes CollectRationingHistory")
    return {
        "generate_age": str(settings["GenerateColorAgeingReport"]) == "1",
        "br_tolerance": int(settings["BRAgeColorTolerance"]),
        "age_tolerance": int(settings["CARNoColorToleranceDuration"]),
        "up": {int(v.strip()) for v in str(settings["NormSuggestion_Upward"]).split(",") if v.strip()},
        "down": {int(v.strip()) for v in str(settings["NormSuggestion_Downward"]).split(",") if v.strip()},
    }


def _unique_source(rows, key, fields, label):
    result = {}
    for row in rows:
        item_key = key(row)
        value = tuple(row[field] for field in fields)
        if item_key in result and result[item_key] != value:
            raise ValueError(f"SOURCE_ORDER_AMBIGUITY: conflicting {label} {item_key}")
        result[item_key] = value
    return result


def _sync(previous, incoming, key, fields, live_keys, label):
    source = _unique_source(incoming, key, fields, label)
    retained = [deepcopy(row) for row in previous if key(row) not in source]
    retained.extend({field: deepcopy(row[field]) for field in fields} for row in incoming)
    return [row for row in retained if key(row) in live_keys]


def _import_bpr(today, prior, facts):
    result = deepcopy(prior)
    incoming = []
    for row in facts["vf_RationedReqReport"]:
        imported = {field: deepcopy(row[field]) for field in BPR_SOURCE_FIELDS}
        imported["WHCode"] = imported.pop("WhCode")
        incoming.append(imported | {"ReportDate": today.isoformat()})
    cutoff = today - timedelta(days=90)
    result["BPR"] = [
        deepcopy(row) for row in prior["BPR"]
        if _day(row["ReportDate"]) != today and _day(row["ReportDate"]) > cutoff
    ] + incoming

    location_fields = ("WHCode", "LocationType", "LogisticsLocation", "LL1", "LL2", "LL3", "LL4", "LL5") + tuple(f"c{i}" for i in range(1, 16))
    sku_fields = ("SKUCode", "ElephantOrderCapping", "Weight", "Volume", "SL1", "SL2", "SL3", "SL4", "SL5") + tuple(f"c{i}" for i in range(1, 16))
    sku_loc_fields = ("SKUCode", "LocCode", "PackSize", "SpikeThreshold", "PSOThreshold", "FGRMFlag", "StockPercentForRationing", "NormPercentReservation", "NonNMS") + tuple(f"c{i}" for i in range(1, 16))
    live_locations = {row["WHCode"] for row in result["BPR"]} | {row["ParentWhCode"] for row in result["BPR"]}
    live_skus = {row["SKUCode"] for row in result["BPR"]}
    live_sku_locs = {(row["SKUCode"], row["WHCode"]) for row in result["BPR"]}
    result["LocationAttributeData"] = _sync(
        prior["LocationAttributeData"], facts["LocationAttributeData"], lambda r: r["WHCode"],
        location_fields, live_locations, "BPRDatabase.LocationAttributeData")
    result["SiteDescriptionTbl"] = _sync(
        prior["SiteDescriptionTbl"], facts["SiteDescriptionTbl"], lambda r: r["WHCode"],
        ("WHCode", "WHDescription"), live_locations, "BPRDatabase.SiteDescriptionTbl")
    result["SkuAttributeData"] = _sync(
        prior["SkuAttributeData"], facts["SkuAttributeData"], lambda r: r["SKUCode"],
        sku_fields, live_skus, "BPRDatabase.SkuAttributeData")
    result["SKUDescriptionTbl"] = _sync(
        prior["SKUDescriptionTbl"], facts["SKUDescriptionTbl"], lambda r: r["SKUCode"],
        ("SKUCode", "SKUDescription"), live_skus, "BPRDatabase.SKUDescriptionTbl")
    result["SkuLocAttributeData"] = _sync(
        prior["SkuLocAttributeData"], facts["SkuLocAttributeData"],
        lambda r: (r["SKUCode"], r["LocCode"]), sku_loc_fields, live_sku_locs,
        "BPRDatabase.SkuLocAttributeData")

    cwh = {row["pwhCode"] for row in facts["CWH_List"]}
    distributors = {row["WhCode"] for row in facts["DistributorList"]}
    latest = {}
    for key in live_sku_locs:
        rows = [row for row in result["BPR"] if (row["SKUCode"], row["WHCode"]) == key]
        latest_day = max(_day(row["ReportDate"]) for row in rows)
        parents = {row["ParentWhCode"] for row in rows if _day(row["ReportDate"]) == latest_day}
        if len(parents) != 1:
            raise ValueError(f"SOURCE_ORDER_AMBIGUITY: latest BPR parent {key}")
        latest[key] = next(iter(parents))
    dbm = _unique_source(facts["DBMMaster"], _key, ("ParentWhCode",), "DBMMaster parent")
    for key, value in dbm.items():
        if key in latest:
            latest[key] = value[0]
    child_locations = {location for _, location in latest}
    parent_locations = set(latest.values())
    for row in result["LocationAttributeData"]:
        location = row["WHCode"]
        row["WhType"] = "dist" if location in distributors else "cwh" if location in cwh else "non-cwh"
        row["IsChild"] = location in child_locations
        row["IsParent"] = location in parent_locations
    result["LastBatchRunTbl"] = [{"LastRunDate": today.isoformat() + "T00:00:00"}]
    return result


def _sql_max(values):
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _latest_norms(bpr, dbm):
    by_key = defaultdict(list)
    for row in bpr:
        by_key[_key(row)].append(row)
    result = {}
    for key, rows in by_key.items():
        latest_day = max(_day(row["ReportDate"]) for row in rows)
        values = {(row["Norm"], row["VirtualNorm"], row["ParentWhCode"])
                  for row in rows if _day(row["ReportDate"]) == latest_day}
        if len(values) != 1:
            raise ValueError(f"SOURCE_ORDER_AMBIGUITY: latest BTR norm {key}")
        result[key] = next(iter(values))
    current = _unique_source(dbm, _key, ("Norm", "ParentWhCode"), "DBMMaster norm")
    for key, (norm, parent) in current.items():
        if key in result:
            result[key] = (norm, result[key][1], parent)
    return result


def _pivot(bpr, today, value_field):
    start = today - timedelta(days=89)
    cells = defaultdict(list)
    for row in bpr:
        report_day = _day(row["ReportDate"])
        if start <= report_day <= today:
            cells[(_key(row), report_day)].append(row[value_field])
    keys = {key for key, _ in cells}
    return {
        key: {f"D{offset + 1}": _sql_max(cells.get((key, start + timedelta(days=offset)), []))
              for offset in range(90)}
        for key in keys
    }


def _generate_trends(today, state, facts):
    result = deepcopy(state)
    result["BufferTrendDates"] = [{f"D{i + 1}": (today - timedelta(days=89 - i)).isoformat() for i in range(90)}]
    norms = _latest_norms(result["BPR"], facts["DBMMaster"])
    locations = _unique_source(result["LocationAttributeData"], lambda r: r["WHCode"], ("WhType",), "BTR location type")
    specs = (
        ("BufferTrendReport", "TechColor", False),
        ("BufferTrendReportEcon", "EcoColor", False),
        ("BufferTrendDispatch", "DispatchColor", True),
        ("BufferTrendPhysicalInv", "PhysicalInventoryColor", True),
    )
    for table, field, include_virtual in specs:
        rows = []
        for key, values in sorted(_pivot(result["BPR"], today, field).items()):
            norm, virtual, parent = norms[key]
            row = {"SKUCode": key[0], "WhCode": key[1], "ParentWhCode": parent,
                   "WhType": locations.get(key[1], (None,))[0],
                   "ParentWhType": locations.get(parent, (None,))[0], "Norm": norm}
            if include_virtual:
                row["VirtualNorm"] = virtual
            row.update(values)
            row.update({"Age": 0, **{colour + "Count": 0 for colour in COLOURS}})
            if table in ("BufferTrendDispatch", "BufferTrendPhysicalInv"):
                row.update({"BRAge": None, "BRAgeRedCount": None, "BRAgeBlackCount": None})
            if table == "BufferTrendPhysicalInv":
                row.update({"Availability_01_30": Decimal("0.00"),
                            "Availability_31_60": Decimal("0.00"),
                            "Availability_61_90": Decimal("0.00")})
            rows.append(row)
        result[table] = rows

    latest_counts = defaultdict(int)
    latest_days = {}
    for row in result["BPR"]:
        key, report_day = _key(row), _day(row["ReportDate"])
        if key not in latest_days or report_day > latest_days[key]:
            latest_days[key], latest_counts[key] = report_day, 1
        elif report_day == latest_days[key]:
            latest_counts[key] += 1
    for table, field in (
        ("BPPTrendTech", "TechPen"), ("BPPTrendEcon", "EcoPen"),
        ("BPPTrendDispatch", "DispatchPen"),
        ("BPPTrendPhysicalInv", "PhysicalInventoryPen"),
    ):
        pivot = _pivot(result["BPR"], today, field)
        result[table] = [
            {"SKUCode": key[0], "WhCode": key[1], **deepcopy(values)}
            for key, values in sorted(pivot.items()) for _ in range(latest_counts[key])
        ]
    return result


def _fill_forward(values, tolerance, missing):
    filled = list(values)
    for _ in range(tolerance):
        before = list(filled)
        for index in range(1, len(filled)):
            if filled[index] == missing and before[index - 1] != missing:
                filled[index] = before[index - 1]
    return filled


def _update_br_age(state, facts, table, tolerance, update_expedite=False):
    result = deepcopy(state)
    by_key = {}
    for row in result[table]:
        if row["D90"] not in ("Black", "Red"):
            continue
        values = _fill_forward([row[field] if row[field] is not None else "NA" for field in DAYS], tolerance, "NA")
        last_other = max((index for index, value in enumerate(values) if value not in ("Black", "Red")), default=-1)
        tail = values[last_other + 1:]
        row["BRAge"] = sum(value in ("Black", "Red") for value in tail)
        row["BRAgeRedCount"] = sum(value == "Red" for value in tail)
        row["BRAgeBlackCount"] = sum(value == "Black" for value in tail)
        by_key[_key(row)] = (row["BRAge"], row["BRAgeRedCount"], row["BRAgeBlackCount"])
    if update_expedite:
        result["ExpediteDispatches"] = deepcopy(facts["ExpediteDispatches"])
        for row in result["ExpediteDispatches"]:
            if _key(row) in by_key:
                row.update(zip(("BRAge", "BRAgeRedCount", "BRAgeBlackCount"), by_key[_key(row)]))
    return result


def _availability(state):
    result = deepcopy(state)
    for row in result["BufferTrendPhysicalInv"]:
        for start in (1, 31, 61):
            values = [row[f"D{i}"] for i in range(start, start + 30)]
            total = sum(value is not None for value in values)
            available = Decimal(0) if total == 0 else Decimal(100) * Decimal(total - values.count("Black")) / Decimal(total)
            row[f"Availability_{start:02d}_{start + 29:02d}"] = available.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    return result


def _colour_age(today, state, enabled, tolerance):
    result = deepcopy(state)
    if not enabled:
        return result
    start = today - timedelta(days=89)
    history = defaultdict(lambda: defaultdict(list))
    for row in result["BPR"]:
        report_day = _day(row["ReportDate"])
        if start <= report_day <= today:
            key = _key(row)
            values = (row["TechColor"] or "0", row["EcoColor"] or "0",
                      row["DispatchColor"] or "0", row["PhysicalInventoryColor"] or "0")
            if history[key][report_day] and history[key][report_day][0] != values:
                raise ValueError(f"SOURCE_ORDER_AMBIGUITY: conflicting BPR colours {key} {report_day}")
            history[key][report_day].append(values)
    normalized = {}
    for key, dated in history.items():
        rows = []
        for i in range(90):
            source_rows = dated.get(start + timedelta(days=i))
            rows.append([*source_rows[0], len(source_rows)] if source_rows else ["0", "0", "0", "0", 1])
        missing_today = rows[-1][0] == "0"
        if not missing_today:
            tech = _fill_forward([row[0] for row in rows], tolerance, "0")
            eco = _fill_forward([row[1] for row in rows], tolerance, "0")
            for index in range(90):
                rows[index][0], rows[index][1] = tech[index], eco[index]
        normalized[key] = rows

    mapping = (
        ("BufferTrendReport", 0, True), ("BufferTrendReportEcon", 1, True),
        ("BufferTrendDispatch", 2, False), ("BufferTrendPhysicalInv", 3, False),
    )
    for table, colour_index, initialize_90 in mapping:
        for row in result[table]:
            values = normalized[_key(row)]
            today_colour = values[-1][colour_index]
            differences = [i for i, value in enumerate(values) if value[colour_index] != today_colour]
            if initialize_90:
                row["Age"] = 90
            if differences:
                row["Age"] = 89 - max(differences)
            recent = values[60:]
            for colour in COLOURS:
                row[colour + "Count"] = sum(value[4] for value in recent if value[colour_index] == colour)
    return result


def _xml_rows(rows):
    fragments = []
    for row in rows:
        attrs = " ".join(f"{field}={quoteattr(str(row[field]))}" for field in DAYS if row[field] is not None)
        fragments.append("<X" + (" " + attrs if attrs else "") + "/>")
    return "".join(fragments)


def _snapshot(state):
    result = deepcopy(state)
    indexes = {table: defaultdict(list) for table in (
        "BufferTrendReportEcon", "BufferTrendDispatch", "BufferTrendPhysicalInv",
        "BPPTrendTech", "BPPTrendEcon", "BPPTrendDispatch", "BPPTrendPhysicalInv",
        "BufferTrendReport",
    )}
    for table, index in indexes.items():
        for row in result[table]:
            index[_key(row)].append(row)
    snapshots = []
    for tech in result["BufferTrendReport"]:
        key = _key(tech)
        row = {field: tech[field] for field in ("SKUCode", "WhCode", "ParentWhCode", "WhType", "ParentWhType", "Norm")}
        for label, source in (("Tech", tech), ("Econ", (indexes["BufferTrendReportEcon"][key] or [None])[0]),
                              ("Dispatch", (indexes["BufferTrendDispatch"][key] or [None])[0]),
                              ("PhysicalInv", (indexes["BufferTrendPhysicalInv"][key] or [None])[0])):
            row["TodayColor" + label] = source["D90"] if source else None
            row["Age" + label] = (source["Age"] or 0) if source else 0
            for colour in COLOURS:
                row[colour + "Count" + label] = (source[colour + "Count"] or 0) if source else 0
        for target, table in (("BPPTech", "BPPTrendTech"), ("BPPEcon", "BPPTrendEcon"),
                              ("BPPDispatch", "BPPTrendDispatch"), ("BPPPhysicalInv", "BPPTrendPhysicalInv"),
                              ("ColorsTech", "BufferTrendReport"), ("ColorsEcon", "BufferTrendReportEcon"),
                              ("ColorsDispatch", "BufferTrendDispatch"), ("ColorsPhysicalInv", "BufferTrendPhysicalInv")):
            row[target] = _xml_rows(indexes[table][key])
        snapshots.append(row)
    result["BTRSnapshotForUI"] = snapshots
    return result


def _count_graph(state):
    result = deepcopy(state)
    groups = defaultdict(list)
    for row in result["BPR"]:
        groups[(_day(row["ReportDate"]), row["ParentWhCode"], row["WHCode"])].append(row)
    output = []
    ordering = lambda item: (item[0][0], str(item[0][1]), str(item[0][2]))
    for (report_day, parent, location), rows in sorted(groups.items(), key=ordering):
        row = {"ReportDate": report_day.isoformat(), "SrcWhCode": parent, "DestWhCode": location}
        for prefix, field in (("Tech", "TechColor"), ("Eco", "EcoColor"),
                              ("Dispatch", "DispatchColor"), ("PhysicalInv", "PhysicalInventoryColor")):
            for colour in ("Black", "Red", "Yellow", "Green", "White"):
                row[prefix + colour] = sum(item[field] == colour for item in rows)
        output.append(row)
    result["BufferTrendGraph"] = output
    return result


def _chronic(state, facts):
    result = deepcopy(state)
    masters = defaultdict(list)
    report = defaultdict(list)
    for row in facts["DBMMaster"]:
        masters[_key(row)].append(row)
    for row in facts["vf_RationedReqReport"]:
        report[_key(row)].append(row)
    rows = []
    for trend in result["BufferTrendDispatch"]:
        if trend["D90"] not in ("Black", "Red"):
            continue
        for master in masters[_key(trend)]:
            sources = report[_key(trend)] or [None]
            for source in sources:
                rows.append({"SKUCode": trend["SKUCode"], "WhCode": trend["WhCode"],
                             "ParentWhCode": trend["ParentWhCode"], "RLT": master["RLT"],
                             "BRAge": trend["BRAge"],
                             "PhysicalInventoryPen": source["PhysicalInventoryPen"] if source else None,
                             "PhysicalInventoryColor": source["PhysicalInventoryColor"] if source else None,
                             "PipelineInventoryPen": source["DispatchPen"] if source else None,
                             "PipelineInventoryColor": source["DispatchColor"] if source else None,
                             "RationedQty": source["RationedReq"] if source else None})
    result["ChronicUnavalabilityData"] = rows
    return result


def _norm_suggestions(today, state, facts, selected):
    result = deepcopy(state)
    suggestions = defaultdict(list)
    for row in facts["Suggestions"]:
        suggestions[_key(row)].append(row)
    rows = []
    for master in facts["DBMMaster"]:
        matches = suggestions[_key(master)] or [None]
        for suggestion in matches:
            suggestion_type = suggestion["Type"] if suggestion else None
            label = "No Suggestion" if suggestion is None else (
                "Increase" if suggestion_type in selected["up"] else
                "Decrease" if suggestion_type in selected["down"] else None)
            rows.append({"SKUCode": master["SKUCode"], "WhCode": _key(master)[1],
                         "SuggestionType": suggestion_type, "Suggestion": label,
                         "SuggestionGenerationAge": None, "SuggestionDate": None})

    suspended = set()
    for row in facts["SuspendHistory"]:
        if _day(row["ReportDate"]) == today and any(row[field] == 0 for field in (
                "RedEnabledStockType", "GreenEnabledStockType",
                "RedEnabledConsumptionType", "GreenEnabledConsumptionType")):
            suspended.add(_key(row))
    for row in rows:
        if row["Suggestion"] is None and _key(row) in suspended:
            row.update({"Suggestion": "Suspension", "SuggestionType": None,
                        "SuggestionDate": None, "SuggestionGenerationAge": None})

    last_norm_change = {}
    for row in facts["NormChangeLogTbl"]:
        key, value = _key(row), _day(row["NormChangeDate"])
        last_norm_change[key] = max(value, last_norm_change.get(key, value))
    current_types = {(key, row["Type"]) for key, values in suggestions.items() for row in values}
    logs = defaultdict(list)
    for row in facts["SuggestionsLog"]:
        key = _key(row)
        if (key, row["Type"]) in current_types and (key not in last_norm_change or _day(row["SuggestionDate"]) > last_norm_change[key]):
            multiplier = sum(item["Type"] == row["Type"] for item in suggestions[key])
            logs[key].extend([row] * multiplier)
    starts = {}
    for key, values in logs.items():
        values.sort(key=lambda row: _day(row["SuggestionDate"]))
        for first, second in zip(values, values[1:]):
            if _day(first["SuggestionDate"]) == _day(second["SuggestionDate"]) and first["NewNorm"] != second["NewNorm"]:
                raise ValueError(f"SOURCE_ORDER_AMBIGUITY: tied SuggestionsLog order {key}")
        previous = 0
        changes = []
        for row in values:
            if row["NewNorm"] != previous:
                changes.append(_day(row["SuggestionDate"]))
            previous = row["NewNorm"]
        if changes:
            starts[key] = max(changes)
    for row in rows:
        if _key(row) in starts:
            row["SuggestionDate"] = starts[_key(row)].isoformat()
            row["SuggestionGenerationAge"] = (today - starts[_key(row)]).days
    result["DBMNormSuggestionsData"] = rows
    return result


def _append_category(row, code):
    row["Category"] = code if row.get("Category") in (None, "") else f"{row['Category']}|{code}"


def _categories(today, state, facts, selected):
    result = deepcopy(state)
    attributes = deepcopy(facts["SKULocStandardAttributes"])
    by_key = defaultdict(list)
    for row in attributes:
        by_key[_key(row)].append(row)
    master = _unique_source(facts["MasterData"], _key, ("RLT",), "Importer MasterData RLT")
    snapshots = {_key(row): row for row in result["BTRSnapshotForUI"]}
    physical = {_key(row): row for row in result["BufferTrendPhysicalInv"]}
    for key, snapshot in snapshots.items():
        if key not in master:
            continue
        rlt = master[key][0]
        if snapshot["TodayColorDispatch"] == "Black" and Decimal(snapshot["AgeDispatch"]) > Decimal("1.5") * Decimal(rlt):
            for row in by_key[key]: _append_category(row, "1")
        if snapshot["TodayColorPhysicalInv"] == "Black" and snapshot["AgePhysicalInv"] > rlt:
            for row in by_key[key]: _append_category(row, "2")
        if snapshot["TodayColorPhysicalInv"] == "White" and snapshot["AgePhysicalInv"] >= 2 * rlt:
            consumption = [row["Consumption"] for row in facts["DailyConsumption"]
                           if _key(row) == key and _day(row["ReportDate"]) > today - timedelta(days=2 * rlt)]
            if consumption and all(value is not None for value in consumption) and sum(consumption) == 0:
                for row in by_key[key]: _append_category(row, "5")
    for key, trend in physical.items():
        if key in master and trend["BRAge"] is not None and trend["BRAge"] > master[key][0]:
            for row in by_key[key]: _append_category(row, "3")
    # SQL reads an absent/NULL SKUStatus as non-matching.  Retained transporter
    # directory rows legitimately omit the item-status columns.
    super_delay = {_key(row) for row in facts["GoodsInTransitTransporterMaster"] if row.get("SKUStatus") == "SuperDelay"}
    for key in super_delay:
        for row in by_key[key]: _append_category(row, "4")
    suggestion_codes = defaultdict(set)
    for row in facts["Suggestions"]:
        code = "6" if row["Type"] in selected["up"] else "7" if row["Type"] in selected["down"] else None
        if code:
            suggestion_codes[_key(row)].add(code)
    for key, codes in suggestion_codes.items():
        if len(codes) > 1:
            raise ValueError(f"SOURCE_ORDER_AMBIGUITY: conflicting suggestion category {key}")
        for row in by_key[key]: _append_category(row, next(iter(codes)))
    result["SKULocStandardAttributes"] = attributes
    return result


def btr_stages(today, prior, facts, settings):
    """Yield each selected legacy source boundary and its complete BTR state."""
    today = _day(today)
    _require_rows(prior, PRIOR_TABLES, "prior")
    _require_rows(facts, FACT_TABLES, "facts")
    selected = _selected_settings(settings)
    # Native BPR is required as an independently retained producer boundary even
    # though Import BPR canonically selects from vf_RationedReqReport.
    for row in facts["BPR_Table"]:
        _key(row)

    current = _import_bpr(today, prior, facts)
    yield "1. Import BPR.sql", deepcopy(current)
    current = _generate_trends(today, current, facts)
    yield "2. GenerateBufferTrend.sql", deepcopy(current)
    current = _update_br_age(current, facts, "BufferTrendDispatch", selected["br_tolerance"], True)
    yield "UpdateBRAge.sql", deepcopy(current)
    current = _update_br_age(current, facts, "BufferTrendPhysicalInv", selected["br_tolerance"])
    yield "UpdateBRAgePhysicalInv.sql", deepcopy(current)
    current = _availability(current)
    yield "CalculateAvailabilityPhysicalInv.sql", deepcopy(current)
    current = _colour_age(today, current, selected["generate_age"], selected["age_tolerance"])
    yield "GenerateColorAgeingReport.sql", deepcopy(current)
    current = _snapshot(current)
    yield "3. GenerateSnapshotForUI.sql", deepcopy(current)
    current = _count_graph(current)
    yield "BufferTrendCountGraph.sql", deepcopy(current)
    current = _chronic(current, facts)
    yield "CollectChronicUnavailabilityData.sql", deepcopy(current)
    current = _norm_suggestions(today, current, facts, selected)
    yield "CollectDBMNormSuggestionsData.sql", deepcopy(current)
    current = _categories(today, current, facts, selected)
    yield "UpdateCategoryCol.sql", deepcopy(current)


def btr_finalization(today, prior, facts, settings):
    stages = [{"stage": name, "state": state} for name, state in btr_stages(today, prior, facts, settings)]
    return {**deepcopy(stages[-1]["state"]), "BTRStages": stages}
