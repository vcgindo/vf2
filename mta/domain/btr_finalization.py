"""Selected Buffer Trend and guided-insight finalization, without I/O.

The contract is pinned in
``.local-stage7/block3-one-pass/delivery-v1/btr-source-contract.json``.
Rows remain SQL-style bags.  Deterministic aggregate multiplicity is preserved;
undefined latest-row or update-source choices are rejected.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from itertools import chain
from xml.sax.saxutils import quoteattr
from mta.row_sequences import history_rows, is_record_rows
from mta.domain.sql_identity_keys import group_key, join_key, row_join_key, value_join_key
from mta.domain.ordinal_lookup import OrderedIndex


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
    if "WhCode" not in row and "WHCode" not in row:
        raise KeyError("WhCode")
    return row_join_key(row)


def _require_rows(container, names, label):
    missing = [name for name in names if name not in container]
    if missing:
        raise ValueError(f"{label} roster drift: missing {missing}")
    for name in names:
        if not is_record_rows(container[name]):
            raise ValueError(f"{label}.{name} must be a row list")


def _setting(settings, name):
    if name not in settings:
        raise ValueError(f"settings roster drift: missing {name}")
    return settings[name]


def _selected_settings(settings, importer_vf_settings=None):
    missing = [name for name in SETTING_NAMES if name not in settings]
    if missing:
        raise ValueError(f"settings roster drift: missing {missing}")
    from mta.domain.btr_rationing_history import configuration
    capture = configuration(settings, importer_vf_settings)
    return {
        'capture_history':capture,
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


def _stage_copy(state, changed=(), *, _owned=False):
    """Copy only tables mutated by an operation-owned BTR stage.

    Other populations are read-only throughout this sequence. Public component
    calls retain independent deep-copy results; the connected owner opts into
    sharing and every later in-place writer first copies its changed tables.

    DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
    """
    if not _owned:
        return deepcopy(state)
    return {name: deepcopy(rows) if name in changed else rows
            for name, rows in state.items()}


def _import_bpr(today, prior, facts, *, _owned=False):
    result = _stage_copy(prior, _owned=_owned)
    incoming = []
    for row in facts["vf_RationedReqReport"]:
        imported = {field: deepcopy(row[field]) for field in BPR_SOURCE_FIELDS}
        imported["WHCode"] = imported.pop("WhCode")
        incoming.append(imported | {"ReportDate": today.isoformat()})
    from mta.application.native_output_contracts import validate_produced_rows
    validate_produced_rows(incoming,"BTR/BPR",stage="btr/import-bpr")
    cutoff = today - timedelta(days=90)
    retained = (
        deepcopy(row) for row in prior["BPR"]
        if _day(row["ReportDate"]) != today and _day(row["ReportDate"]) > cutoff
    )
    result["BPR"] = history_rows(chain(retained, incoming), like=prior["BPR"])

    location_fields = ("WHCode", "LocationType", "LogisticsLocation", "LL1", "LL2", "LL3", "LL4", "LL5") + tuple(f"c{i}" for i in range(1, 16))
    sku_fields = ("SKUCode", "ElephantOrderCapping", "Weight", "Volume", "SL1", "SL2", "SL3", "SL4", "SL5") + tuple(f"c{i}" for i in range(1, 16))
    sku_loc_fields = ("SKUCode", "LocCode", "PackSize", "SpikeThreshold", "PSOThreshold", "FGRMFlag", "StockPercentForRationing", "NormPercentReservation", "NonNMS") + tuple(f"c{i}" for i in range(1, 16))
    live_locations, live_skus, live_sku_locs = set(), set(), set()
    latest_days, latest_parents = {}, {}
    for row in result["BPR"]:
        key = join_key(row["SKUCode"], row["WHCode"])
        report_day = _day(row["ReportDate"])
        live_locations.update((value_join_key(row["WHCode"]), value_join_key(row["ParentWhCode"])))
        live_skus.add(value_join_key(row["SKUCode"]))
        live_sku_locs.add(key)
        if key not in latest_days or report_day > latest_days[key]:
            latest_days[key] = report_day
            latest_parents[key] = {row["ParentWhCode"]}
        elif report_day == latest_days[key] and len(latest_parents[key]) < 2:
            latest_parents[key].add(row["ParentWhCode"])
    result["LocationAttributeData"] = _sync(
        prior["LocationAttributeData"], facts["LocationAttributeData"], lambda r: value_join_key(r["WHCode"]),
        location_fields, live_locations, "BPRDatabase.LocationAttributeData")
    result["SiteDescriptionTbl"] = _sync(
        prior["SiteDescriptionTbl"], facts["SiteDescriptionTbl"], lambda r: value_join_key(r["WHCode"]),
        ("WHCode", "WHDescription"), live_locations, "BPRDatabase.SiteDescriptionTbl")
    result["SkuAttributeData"] = _sync(
        prior["SkuAttributeData"], facts["SkuAttributeData"], lambda r: value_join_key(r["SKUCode"]),
        sku_fields, live_skus, "BPRDatabase.SkuAttributeData")
    result["SKUDescriptionTbl"] = _sync(
        prior["SKUDescriptionTbl"], facts["SKUDescriptionTbl"], lambda r: value_join_key(r["SKUCode"]),
        ("SKUCode", "SKUDescription"), live_skus, "BPRDatabase.SKUDescriptionTbl")
    result["SkuLocAttributeData"] = _sync(
        prior["SkuLocAttributeData"], facts["SkuLocAttributeData"],
        lambda r: join_key(r["SKUCode"], r["LocCode"]), sku_loc_fields, live_sku_locs,
        "BPRDatabase.SkuLocAttributeData")

    cwh = {value_join_key(row["pwhCode"]) for row in facts["CWH_List"]}
    distributors = {value_join_key(row["WhCode"]) for row in facts["DistributorList"]}
    latest = {}
    for key, parents in latest_parents.items():
        if len(parents) != 1:
            raise ValueError(f"SOURCE_ORDER_AMBIGUITY: latest BPR parent {key}")
        latest[key] = next(iter(parents))
    dbm = _unique_source(facts["DBMMaster"], _key, ("ParentWhCode",), "DBMMaster parent")
    for key, value in dbm.items():
        if key in latest:
            latest[key] = value[0]
    child_locations = {value_join_key(location) for _, location in latest}
    parent_locations = {value_join_key(location) for location in latest.values()}
    for row in result["LocationAttributeData"]:
        location = value_join_key(row["WHCode"])
        row["WhType"] = "dist" if location in distributors else "cwh" if location in cwh else "non-cwh"
        row["IsChild"] = location in child_locations
        row["IsParent"] = location in parent_locations
    result["LastBatchRunTbl"] = [{"LastRunDate": today.isoformat() + "T00:00:00"}]
    return result


def _sql_max(values):
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _latest_norms(bpr, dbm):
    latest_days = {}
    values = {}
    for row in bpr:
        key, report_day = _key(row), _day(row["ReportDate"])
        if None in key:
            continue
        value = row["Norm"], row["VirtualNorm"], row["ParentWhCode"]
        if key not in latest_days or report_day > latest_days[key]:
            latest_days[key], values[key] = report_day, {value}
        elif report_day == latest_days[key] and len(values[key]) < 2:
            values[key].add(value)
    result = {}
    for key, candidates in values.items():
        if len(candidates) != 1:
            raise ValueError(f"SOURCE_ORDER_AMBIGUITY: latest BTR norm {key}")
        result[key] = next(iter(candidates))
    current = _unique_source(dbm, _key, ("Norm", "ParentWhCode"), "DBMMaster norm")
    for key, (norm, parent) in current.items():
        if key in result:
            result[key] = (norm, result[key][1], parent)
    return result


def _pivot(bpr, today, value_field):
    start = today - timedelta(days=89)
    cells = {}
    spellings = defaultdict(set)
    for row in bpr:
        report_day = _day(row["ReportDate"])
        if start <= report_day <= today:
            key = group_key(row["SKUCode"], row.get("WhCode", row.get("WHCode")))
            spellings[key].add((row["SKUCode"], row.get("WhCode", row.get("WHCode"))))
            cell = key, report_day
            value = row[value_field]
            if cell not in cells or cells[cell] is None:
                cells[cell] = value
            elif value is not None:
                cells[cell] = max(cells[cell], value)
    ambiguous = [key for key, values in spellings.items() if len(values) > 1]
    if ambiguous:
        raise ValueError(f"SOURCE_ORDER_AMBIGUITY: BTR pivot identity spelling {ambiguous[0]}")
    keys = {key for key, _ in cells}
    return {
        key: {f"D{offset + 1}": cells.get((key, start + timedelta(days=offset)))
              for offset in range(90)}
        for key in keys
    }


def _generate_trends(today, state, facts, *, _owned=False):
    result = _stage_copy(state, _owned=_owned)
    result["BufferTrendDates"] = [{f"D{i + 1}": (today - timedelta(days=89 - i)).isoformat() for i in range(90)}]
    norms = _latest_norms(result["BPR"], facts["DBMMaster"])
    locations = _unique_source(result["LocationAttributeData"], lambda r: value_join_key(r["WHCode"]), ("WhType",), "BTR location type")
    specs = (
        ("BufferTrendReport", "TechColor", False),
        ("BufferTrendReportEcon", "EcoColor", False),
        ("BufferTrendDispatch", "DispatchColor", True),
        ("BufferTrendPhysicalInv", "PhysicalInventoryColor", True),
    )
    for table, field, include_virtual in specs:
        rows = []
        for key, values in sorted((key,values) for key,values in _pivot(result["BPR"], today, field).items() if key in norms):
            norm, virtual, parent = norms[key]
            row = {"SKUCode": key[0], "WhCode": key[1], "ParentWhCode": parent,
                   "WhType": locations.get(value_join_key(key[1]), (None,))[0],
                   "ParentWhType": locations.get(value_join_key(parent), (None,))[0], "Norm": norm}
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
            for key, values in sorted((key,values) for key,values in pivot.items() if key in latest_counts)
            for _ in range(latest_counts[key])
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


def _update_br_age(state, facts, table, tolerance, update_expedite=False, *, _owned=False):
    result = _stage_copy(state, (table,), _owned=_owned)
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


def _availability(state, *, _owned=False):
    result = _stage_copy(state, ('BufferTrendPhysicalInv',), _owned=_owned)
    for row in result["BufferTrendPhysicalInv"]:
        for start in (1, 31, 61):
            values = [row[f"D{i}"] for i in range(start, start + 30)]
            total = sum(value is not None for value in values)
            available = Decimal(0) if total == 0 else Decimal(100) * Decimal(total - values.count("Black")) / Decimal(total)
            row[f"Availability_{start:02d}_{start + 29:02d}"] = available.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    return result


def _colour_age(today, state, enabled, tolerance, *, _owned=False):
    result = _stage_copy(state, ('BufferTrendReport', 'BufferTrendReportEcon',
        'BufferTrendDispatch', 'BufferTrendPhysicalInv') if enabled else (), _owned=_owned)
    if not enabled:
        return result
    start = today - timedelta(days=89)
    history = defaultdict(dict)
    for row in result["BPR"]:
        report_day = _day(row["ReportDate"])
        if start <= report_day <= today:
            key = _key(row)
            values = (row["TechColor"] or "0", row["EcoColor"] or "0",
                      row["DispatchColor"] or "0", row["PhysicalInventoryColor"] or "0")
            previous = history[key].get(report_day)
            if previous is not None and previous[0] != values:
                raise ValueError(f"SOURCE_ORDER_AMBIGUITY: conflicting BPR colours {key} {report_day}")
            history[key][report_day] = (values, 1 if previous is None else previous[1] + 1)
    normalized = {}
    for key, dated in history.items():
        rows = []
        for i in range(90):
            source = dated.get(start + timedelta(days=i))
            rows.append([*source[0], source[1]] if source else ["0", "0", "0", "0", 1])
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


def _snapshot(state, *, _owned=False):
    result = _stage_copy(state, _owned=_owned)
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


def _count_graph(state, *, _owned=False):
    result = _stage_copy(state, _owned=_owned)
    groups = defaultdict(Counter)
    spellings = {}
    fields = (("Tech", "TechColor"), ("Eco", "EcoColor"),
              ("Dispatch", "DispatchColor"), ("PhysicalInv", "PhysicalInventoryColor"))
    colours = ("Black", "Red", "Yellow", "Green", "White")
    for row in result["BPR"]:
        identity = (_day(row["ReportDate"]), group_key(row["ParentWhCode"], row["WHCode"]))
        spelling = row["ParentWhCode"], row["WHCode"]
        if identity in spellings and spellings[identity] != spelling:
            raise ValueError(f"SOURCE_ORDER_AMBIGUITY: BTR graph identity spelling {spelling}")
        spellings[identity] = spelling
        counts = groups[identity]
        for prefix, field in fields:
            value = row[field]
            if value in colours:
                counts[prefix, value] += 1
    output = []
    ordering = lambda item: (item[0][0], str(item[0][1][0]), str(item[0][1][1]))
    for (report_day, location_key), counts in sorted(groups.items(), key=ordering):
        parent, location = location_key
        row = {"ReportDate": report_day.isoformat(), "SrcWhCode": parent, "DestWhCode": location}
        for prefix, _ in fields:
            for colour in colours:
                row[prefix + colour] = counts[prefix, colour]
        output.append(row)
    result["BufferTrendGraph"] = output
    return result


def _chronic(state, facts, *, _owned=False):
    result = _stage_copy(state, _owned=_owned)
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


def _norm_suggestions(today, state, facts, selected, *, _owned=False):
    result = _stage_copy(state, _owned=_owned)
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
    type_counts = Counter((key, row["Type"]) for key, values in suggestions.items() for row in values)
    logs = defaultdict(list)
    for row in facts["SuggestionsLog"]:
        key = _key(row)
        if (key, row["Type"]) in current_types and (key not in last_norm_change or _day(row["SuggestionDate"]) > last_norm_change[key]):
            multiplier = type_counts[key, row["Type"]]
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


def _categories(today, state, facts, selected, *, _owned=False):
    result = _stage_copy(state, _owned=_owned)
    attributes = deepcopy(facts["SKULocStandardAttributes"])
    by_key = defaultdict(list)
    for row in attributes:
        # The daily DISTINCT initializer retains NULL-key rows. Canonical
        # UpdateCategoryCol uses SQL equality joins, which cannot match those
        # targets; preserve their values and ordinals without indexing them.
        if "WhCode" not in row and "WHCode" not in row:
            raise KeyError("WhCode")
        if row["SKUCode"] is None or row.get("WhCode", row.get("WHCode")) is None:
            continue
        by_key[_key(row)].append(row)
    master = _unique_source(facts["MasterData"], _key, ("RLT",), "Importer MasterData RLT")
    snapshots = {_key(row): row for row in result["BTRSnapshotForUI"]}
    physical = {_key(row): row for row in result["BufferTrendPhysicalInv"]}
    with OrderedIndex(facts["DailyConsumption"], key=lambda row: tuple(_key(row))) as consumption_index:
        for key, snapshot in snapshots.items():
            if key not in master:
                continue
            rlt = master[key][0]
            if snapshot["TodayColorDispatch"] == "Black" and Decimal(snapshot["AgeDispatch"]) > Decimal("1.5") * Decimal(rlt):
                for row in by_key[key]: _append_category(row, "1")
            if snapshot["TodayColorPhysicalInv"] == "Black" and snapshot["AgePhysicalInv"] > rlt:
                for row in by_key[key]: _append_category(row, "2")
            if snapshot["TodayColorPhysicalInv"] == "White" and snapshot["AgePhysicalInv"] >= 2 * rlt:
                consumption = [row["Consumption"] for row in consumption_index.candidates(tuple(key))
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


def btr_stages(today, prior, facts, settings, *, importer_vf_settings=None, _owned=False):
    """Yield each selected legacy source boundary and its complete BTR state."""
    today = _day(today)
    _require_rows(prior, PRIOR_TABLES, "prior")
    _require_rows(facts, FACT_TABLES, "facts")
    selected = _selected_settings(settings, importer_vf_settings)
    # Native BPR is required as an independently retained producer boundary even
    # though Import BPR canonically selects from vf_RationedReqReport.
    for row in facts["BPR_Table"]:
        _key(row)

    current = prior
    if selected['capture_history']:
        from mta.domain.btr_rationing_history import collect, POPULATION, STAGE
        if POPULATION not in prior or facts.get('LastBatchRunTbl') != [{'LastRunDate':today.isoformat()+'T00:00:00'}]:
            raise ValueError('BTR capture requires its own history and singleton current date owner')
        current = {**_stage_copy(prior, _owned=_owned), POPULATION:collect(today,prior[POPULATION],
            facts['vf_RationedReqReport'],facts.get('BPRDailyConsumption'),facts.get('SupplierDispatchReq'),
            settings['RationingHistoryHorizonBTR'])}
        yield STAGE, current
    current = _import_bpr(today, current, facts, _owned=_owned)
    yield "1. Import BPR.sql", current
    current = _generate_trends(today, current, facts, _owned=_owned)
    yield "2. GenerateBufferTrend.sql", current
    current = _update_br_age(current, facts, "BufferTrendDispatch", selected["br_tolerance"], True, _owned=_owned)
    yield "UpdateBRAge.sql", current
    current = _update_br_age(current, facts, "BufferTrendPhysicalInv", selected["br_tolerance"], _owned=_owned)
    yield "UpdateBRAgePhysicalInv.sql", current
    current = _availability(current, _owned=_owned)
    yield "CalculateAvailabilityPhysicalInv.sql", current
    current = _colour_age(today, current, selected["generate_age"], selected["age_tolerance"], _owned=_owned)
    yield "GenerateColorAgeingReport.sql", current
    current = _snapshot(current, _owned=_owned)
    yield "3. GenerateSnapshotForUI.sql", current
    current = _count_graph(current, _owned=_owned)
    yield "BufferTrendCountGraph.sql", current
    current = _chronic(current, facts, _owned=_owned)
    yield "CollectChronicUnavailabilityData.sql", current
    current = _norm_suggestions(today, current, facts, selected, _owned=_owned)
    yield "CollectDBMNormSuggestionsData.sql", current
    current = _categories(today, current, facts, selected, _owned=_owned)
    yield "UpdateCategoryCol.sql", current


def btr_finalization(today, prior, facts, settings):
    stages = [{"stage": name, "state": state} for name, state in btr_stages(today, prior, facts, settings)]
    return {**deepcopy(stages[-1]["state"]), "BTRStages": stages}
