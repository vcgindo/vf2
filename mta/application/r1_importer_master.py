"""Port ValidateAndProcessMaster.sql, before DBM master reconciliation.

Source-shaped rows retain SQL column names at this boundary. They are raw
facts or labelled prior Importer state, never current-day calculated outputs.
Source-declared rejections return retained state; ambiguous SQL selections
raise an explicit legacy-flaw boundary instead of inventing a winner.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json


SCHEMA = "r1-importer-master-input-v1"
MASTER_COLUMNS = ("SKUCode", "WhCode", "Norm", "MinNorm", "RLT", "RCP", "GCP", "OCP",
                  "MinOrderCount", "ParentWhCode", "SKUIntroDate")
SKU_LEVELS = tuple(f"SL{i}" for i in range(1, 6))
LOC_LEVELS = tuple(f"LL{i}" for i in range(1, 6))
CUSTOM = tuple(f"c{i}" for i in range(1, 16))
RAW_CUSTOM = tuple(f"{prefix}{i:02}" for prefix in ("SKUAtt", "LocAtt", "SKULocAtt") for i in range(1, 16))
SKU_ATTRIBUTES = ("SKUCode", "ElephantOrderCapping", "Weight", "Volume", *SKU_LEVELS, *CUSTOM)
LOC_ATTRIBUTES = ("WHCode", "LocationType", "LogisticsLocation", *LOC_LEVELS, *CUSTOM)
SKULOC_ATTRIBUTES = ("SKUCode", "LocCode", "PackSize", "SpikeThreshold", "PSOThreshold", "FGRMFlag",
                     "StockPercentForRationing", "NormPercentReservation", "NonNMS", *CUSTOM)
RAW_COLUMNS = (*MASTER_COLUMNS, "SKUDescription", "WHDescription", "ParentDescription", "PackSize",
               "SpikeThreshold", "PSOThreshold", "FGRMFlag", "MOQ", "StockPercentForRationing", "NormPercentReservation",
               "ElephantOrderCapping", "Weight", "Volume", *SKU_LEVELS, "LocationType", "LogisticsLocation", *LOC_LEVELS, *RAW_CUSTOM)
NO_NORM_COLUMNS = tuple(f for f in RAW_COLUMNS if f not in {
    "Norm", "MinNorm", "RCP", "GCP", "OCP", "MinOrderCount", "PackSize", "SpikeThreshold", "PSOThreshold",
    "FGRMFlag", "MOQ", "StockPercentForRationing", "NormPercentReservation",
})
TABLE_COLUMNS = {
    "MasterData": MASTER_COLUMNS,
    "SKUDescriptionTbl": ("SKUCode", "SKUDescription"),
    "SiteDescriptionTbl": ("WHCode", "WHDescription"),
    "SkuAttributeData": SKU_ATTRIBUTES,
    "LocationAttributeData": LOC_ATTRIBUTES,
    "SkuLocAttributeData": SKULOC_ATTRIBUTES,
    "RetiredNormsTbl": ("SKUCode", "WhCode", "Norm", "Event_Date", "Event_Type"),
    "RejectedMaster": ("SKUCode", "WhCode", "RejectionDate", "ReasonCode", "ReasonDescription"),
    "ForceNormChange": ("SKUCode", "WhCode", "NewNorm", "Approved", "RequestedBy"),
    "MasterDataRaw": RAW_COLUMNS,
    "MasterDataRawNonNMS": RAW_COLUMNS,
    "NoNormMasterRaw": NO_NORM_COLUMNS,
}
PRIOR_TABLES = tuple(list(TABLE_COLUMNS)[:9])
INT_COLUMNS = {"Norm", "MinNorm", "RLT", "RCP", "GCP", "OCP", "MinOrderCount", "PackSize", "MOQ",
               "StockPercentForRationing", "NormPercentReservation", "ElephantOrderCapping", "NewNorm", "ReasonCode"}
DECIMAL_COLUMNS = {"SpikeThreshold": (10, 2), "PSOThreshold": (10, 2), "Weight": (13, 3), "Volume": (13, 3)}
BIT_COLUMNS = {"Approved", "NonNMS", "Event_Type"}
DATE_COLUMNS = {"SKUIntroDate", "Event_Date"}
DESCRIPTIONS = ("SKUDescription", "WHDescription", "ParentDescription")
REFRESH = ("ParentWhCode", "RLT", "RCP", "GCP", "MinNorm", "OCP", "MinOrderCount")


class LegacyMasterAmbiguity(ValueError):
    """No exact result is claimed for a source selection without a winner."""


def _sql_key(value):
    # Tested ASCII subset of SQL_Latin1_General_CP1_CI_AS. Unicode collation
    # equivalence is not silently approximated by Python Unicode casefold.
    return value.rstrip(" ").upper() if isinstance(value, str) else value


def _key(row, fields=("SKUCode", "WhCode")):
    return tuple(_sql_key(row[f]) for f in fields)


def _join(a, b, fields=("SKUCode", "WhCode")):
    ka, kb = _key(a, fields), _key(b, fields)
    return None not in ka and None not in kb and ka == kb


def _distinct(rows, fields):
    found = {}
    for row in rows:
        key = _key(row, fields)
        result = {f: row[f] for f in fields}
        if key in found and found[key] != result:
            raise LegacyMasterAmbiguity("LEGACY_FLAW: collation-equal output has unspecified spelling")
        found[key] = result
    return list(found.values())


def _typed_row(row, fields):
    if not isinstance(row, dict) or set(row) - set(fields):
        raise ValueError("Unexpected raw/prior Importer fields")
    result = {}
    for field in fields:
        value = row.get(field)
        if value is None:
            result[field] = None
            continue
        if field in INT_COLUMNS | BIT_COLUMNS | set(DECIMAL_COLUMNS):
            try:
                number = Decimal(str(value))
            except (InvalidOperation, ValueError):
                raise ValueError(f"Invalid Importer numeric field: {field}") from None
            if isinstance(value, bool) or not number.is_finite():
                raise ValueError(f"Invalid Importer numeric field: {field}")
            if field in DECIMAL_COLUMNS:
                precision, scale = DECIMAL_COLUMNS[field]
                if number != number.quantize(Decimal(1).scaleb(-scale)) or abs(number) >= 10 ** (precision - scale):
                    raise ValueError(f"Importer {field} must already fit its source decimal type")
                result[field] = format(number, f".{scale}f")
            else:
                if number != number.to_integral_value() or not -2147483648 <= number <= 2147483647 or field in BIT_COLUMNS and number not in (0, 1):
                    raise ValueError(f"Importer {field} must fit its source integer/bit type")
                result[field] = int(number)
        elif field in DATE_COLUMNS:
            if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                raise ValueError(f"Importer {field} must be YYYY-MM-DD")
            result[field] = value
        elif field == "RejectionDate":
            if not isinstance(value, str) or datetime.fromisoformat(value).isoformat(timespec="seconds") != value:
                raise ValueError("Importer rejection clock must be second-precision ISO timestamp")
            result[field] = value
        else:
            limit = 125 if field in DESCRIPTIONS else 100 if field == "ReasonDescription" else 256 if field == "RequestedBy" else 10 if field == "FGRMFlag" else 50
            if not isinstance(value, str) or len(value) > limit or not value.isascii():
                raise ValueError(f"Importer {field} requires bounded ASCII source text; wider collation is unproven")
            result[field] = value
    return result


def validate_master_input(payload):
    required = {"schema", "business_date", "run_timestamp", "import_non_nms", "settings", "prior_provenance", "prior",
                "raw_master", "raw_non_nms", "raw_no_norm"}
    if not isinstance(payload, dict) or set(payload) != required or payload["schema"] != SCHEMA:
        raise ValueError("Invalid R1 Importer master input contract")
    day = date.fromisoformat(payload["business_date"])
    now = datetime.fromisoformat(payload["run_timestamp"])
    if day.isoformat() != payload["business_date"] or now.isoformat(timespec="seconds") != payload["run_timestamp"] or now.tzinfo:
        raise ValueError("Importer clock requires explicit date and naive second-precision run timestamp")
    provenance = payload["prior_provenance"]
    if (not isinstance(provenance, dict) or set(provenance) != {"kind", "identity", "business_date"}
            or provenance["kind"] != "SYNTHETIC_PRIOR_IMPORTER"
            or not isinstance(provenance["identity"], str) or not provenance["identity"].strip()
            or date.fromisoformat(provenance["business_date"]) >= day):
        raise ValueError("Importer opening requires labelled prior synthetic provenance")
    if type(payload["import_non_nms"]) is not bool:
        raise ValueError("ImportNonNMSMasterData must be explicit")
    if not isinstance(payload["settings"], list) or any(
        not isinstance(r, dict) or set(r) != {"Parameter", "Value"}
        or r["Parameter"] not in {"NMSActive", "DBMActive", "UpdatePWh_RLT_RCP_GCP"}
        or type(r["Value"]) is not int or r["Value"] not in (0, 1) for r in payload["settings"]
    ):
        raise ValueError("Invalid source Importer settings rows")
    if not isinstance(payload["prior"], dict) or set(payload["prior"]) != set(PRIOR_TABLES):
        raise ValueError("Importer prior state must explicitly include every retained table")
    tables = {}
    for table, rows in {**payload["prior"], "MasterDataRaw": payload["raw_master"],
                        "MasterDataRawNonNMS": payload["raw_non_nms"], "NoNormMasterRaw": payload["raw_no_norm"]}.items():
        if not isinstance(rows, list):
            raise ValueError(f"Importer table must be a list: {table}")
        tables[table] = [_typed_row(r, TABLE_COLUMNS[table]) for r in rows]
    # A prior SQL table is a prior persisted state, not another nullable raw feed.
    nonnull = {
        "MasterData": ("SKUCode", "WhCode", "Norm", "MinNorm", "RLT", "RCP", "GCP"),
        "SKUDescriptionTbl": TABLE_COLUMNS["SKUDescriptionTbl"], "SiteDescriptionTbl": TABLE_COLUMNS["SiteDescriptionTbl"],
        "SkuAttributeData": ("SKUCode",), "LocationAttributeData": ("WHCode",),
        "SkuLocAttributeData": ("SKUCode", "LocCode", "PackSize", "StockPercentForRationing", "NormPercentReservation", "NonNMS"),
        "RetiredNormsTbl": TABLE_COLUMNS["RetiredNormsTbl"],
        "RejectedMaster": ("SKUCode", "WhCode", "RejectionDate", "ReasonCode"),
    }
    for table, fields in nonnull.items():
        if any(any(row[f] is None for f in fields) for row in tables[table]):
            raise ValueError(f"Invalid NULL in prior Importer table: {table}")
    return tables


def process_importer_master(payload):
    """Return exact supported source table transitions, including early return."""
    tables = validate_master_input(payload)
    day, now = payload["business_date"], payload["run_timestamp"]
    raw = tables["MasterDataRaw"]
    nonnms = tables["MasterDataRawNonNMS"]
    # Selected legacy DDL creates these three MasterDataRaw VARCHAR columns
    # with ANSI_PADDING OFF. Its INSERT trims trailing spaces before the SQL
    # producer begins; NonNMS/NoNorm/description tables have padding ON.
    for row in raw:
        for field in DESCRIPTIONS:
            if row[field] is not None:
                # SQL Server retains one space for a nonempty all-space
                # value in this old ANSI_PADDING-OFF column, but not for ''.
                row[field] = row[field].rstrip(" ") or (" " if row[field] else "")
    reject_count = len(tables["RejectedMaster"])
    retired_count = len(tables["RetiredNormsTbl"])

    def finish(outcome):
        # Table row order is not a SQL contract. Keep duplicates and compare
        # deterministic multisets rather than making insertion order a rule.
        return {"outcome": outcome, "tables": {name: sorted(rows, key=lambda r: json.dumps(r, sort_keys=True)) for name, rows in tables.items()},
                "rejects_added": sorted(tables["RejectedMaster"][reject_count:], key=lambda r: json.dumps(r, sort_keys=True)),
                "retired_events_added": sorted(tables["RetiredNormsTbl"][retired_count:], key=lambda r: json.dumps(r, sort_keys=True))}

    def reject(rows, code, message, *, clear=True):
        for row in rows:
            tables["RejectedMaster"].append({"SKUCode": row["SKUCode"], "WhCode": row["WhCode"],
                "RejectionDate": now, "ReasonCode": code, "ReasonDescription": message(row) if callable(message) else message})
        if clear:
            raw.clear()
        return finish("EARLY_RETURN")

    def setting(name, value):
        return sum(r["Parameter"] == name and r["Value"] == value for r in payload["settings"])

    def normalize(rows, *, trim):
        for row in rows:
            if trim:
                for field in ("SKUCode", "WhCode", "ParentWhCode", *SKU_LEVELS, *LOC_LEVELS,
                              "LocationType", "LogisticsLocation", *RAW_CUSTOM):
                    if row[field] is not None:
                        row[field] = row[field].strip(" ")
            for field in DESCRIPTIONS:
                row[field] = (row[field] or "").strip(" ") or "-ND-"
            row["SKUIntroDate"] = row["SKUIntroDate"] or day

    if payload["import_non_nms"]:
        nonnms[:] = [r for r in nonnms if r["SKUCode"] is not None or r["WhCode"] is not None]
        if not nonnms:
            reject([{"SKUCode": "-NA-", "WhCode": "-NA-"}], 26, "Non-NMS Master file/table is not available or unreadable", clear=False)
        normalize(nonnms, trim=True)
    if not raw:
        return reject([{"SKUCode": "-NA-", "WhCode": "-NA-"}], 11, "Master file/table is not available or unreadable", clear=False)
    if setting("NMSActive", 0):
        raw[:] = [r for r in raw if r["SKUCode"] is not None or r["WhCode"] is not None]
        normalize(raw, trim=True)
    if setting("NMSActive", 1):
        normalize(raw, trim=False)
    if not raw:
        return reject([{"SKUCode": "-NA-", "WhCode": "-NA-"}], 22, "All records in master data have null values for SKU code and Location code", clear=False)

    added_non_nms, auto_force = [], []
    if payload["import_non_nms"]:
        added_non_nms = deepcopy([r for r in nonnms if not any(_join(r, n) for n in raw)])

        def names(old, candidates, keyfield, valuefield):
            result = defaultdict(set)
            for row in old:
                result[_sql_key(row[keyfield])].add(row[valuefield])
            grouped = defaultdict(set)
            for row in candidates:
                if row[keyfield] is not None:
                    grouped[_sql_key(row[keyfield])].add(row[valuefield])
            for key, values in grouped.items():
                result[key] = values
            return result

        sku_names = names(tables["SKUDescriptionTbl"], raw, "SKUCode", "SKUDescription")
        loc_names = names(
            tables["SiteDescriptionTbl"], [{"WHCode": r["WhCode"], "WHDescription": r["WHDescription"]} for r in raw], "WHCode", "WHDescription")
        # Existing locations are updated first by location then parent names;
        # new parent names are inserted before new ordinary location names.
        parents = [{"WHCode": r["ParentWhCode"], "WHDescription": r["ParentDescription"]} for r in raw]
        parent_names = names([], parents, "WHCode", "WHDescription")
        loc_names.update(parent_names)
        for row in added_non_nms:
            for field, mapping, code in (("SKUDescription", sku_names, "SKUCode"), ("WHDescription", loc_names, "WhCode"), ("ParentDescription", loc_names, "ParentWhCode")):
                if row[code] is not None and _sql_key(row[code]) in mapping:
                    values = mapping[_sql_key(row[code])]
                    # Only consumed name choices affect this durable boundary.
                    # An unused ambiguous temporary UPDATE must not hide the
                    # later deterministic master-file rejection.
                    if len(values) != 1:
                        raise LegacyMasterAmbiguity("UNPROVEN: consumed Non-NMS name UPDATE has multiple source values")
                    row[field] = next(iter(values))
        prior_attrs = tables["SkuLocAttributeData"]
        for population, expected in ((added_non_nms, 0), (raw, 1)):
            for row in population:
                for attr in prior_attrs:
                    if _join(row, {"SKUCode": attr["SKUCode"], "WhCode": attr["LocCode"]}) and attr["NonNMS"] == expected:
                        auto_force.append({"SKUCode": row["SKUCode"], "WhCode": row["WhCode"], "NewNorm": row["Norm"], "Approved": 1, "RequestedBy": None})
        raw.extend(deepcopy(added_non_nms))

    overlap = [r for r in raw for n in tables["NoNormMasterRaw"] if _join(r, n)]
    if overlap:
        tables["NoNormMasterRaw"].clear()
        return reject(overlap, 20, "Both Master file and No Norm Master file rejected,both have same SKU-Locations")
    if setting("DBMActive", 0):
        for row in raw:
            for field in ("RLT", "RCP", "GCP"):
                if row[field] is None or row[field] < 3:
                    row[field] = 3
    norms = deepcopy([r for r in raw if r["SKUCode"] is not None and r["WhCode"] is not None])
    invalid = [r for r in norms if r["ParentWhCode"] is None or r["Norm"] is None]
    if invalid:
        return reject(invalid, 5, "Null ParentWHCode/Norm Present in Master File/table")
    counts = Counter(_key(r) for r in norms)
    duplicate = _distinct([r for r in norms if counts[_key(r)] > 1], ("SKUCode", "WhCode"))
    if duplicate:
        return reject(duplicate, 1, "Duplicate entries SKU+Location in Master File/table")
    invalid = [r for r in norms if _sql_key(r["WhCode"]) == _sql_key(r["ParentWhCode"])]
    if invalid:
        return reject(invalid, 2, "Same source and destination in Master File/table")
    for kind in ("SKU", "Location"):
        if kind == "SKU":
            pairs = [{"code": r["SKUCode"], "name": r["SKUDescription"]} for r in raw if r["SKUCode"] is not None]
        else:
            pairs = [{"code": r[c], "name": r[n]} for r in raw for c, n in (("WhCode", "WHDescription"), ("ParentWhCode", "ParentDescription")) if r[c] is not None]
        grouped = defaultdict(set)
        identities = {}
        for r in pairs:
            grouped[_sql_key(r["code"])].add(_sql_key(r["name"]))
            identities[_sql_key(r["code"])] = r["code"]
        invalid = [{"SKUCode": identities[k] if kind == "SKU" else "", "WhCode": "" if kind == "SKU" else identities[k]} for k, v in grouped.items() if len(v) > 1]
        if invalid:
            return reject(invalid, 3 if kind == "SKU" else 4, "SKU Code with multiple names in Master File/table" if kind == "SKU" else "Location/Parent Code with multiple names in Master File/table")
    rules = [
        ("MinNorm", 7, "Min Norm is invalid", lambda v: v is None),
        ("RLT", 8, "RLT is invalid", lambda v: v is None),
        ("RCP", 9, "RCP is invalid", lambda v: v is None),
        ("GCP", 10, "GCP is invalid", lambda v: v is None),
        ("PackSize", 24, "PackSize is invalid", lambda v: v is not None and v <= 0),
        ("SpikeThreshold", 29, "Spike Threshold is invalid", lambda v: v is not None and Decimal(v) < 0),
        ("PSOThreshold", 30, "PSO Threshold is invalid", lambda v: v is not None and Decimal(v) < 0),
        ("FGRMFlag", 28, "FG/RM flag is invalid", lambda v: v is not None and _sql_key(v) not in ("FG", "RM")),
        ("ElephantOrderCapping", 31, "ElephantOrderCapping is invalid", lambda v: v is not None and v < 0),
        ("Weight", 31, "Weight is invalid", lambda v: v is not None and Decimal(v) < 0),
        ("Volume", 31, "Volume is invalid", lambda v: v is not None and Decimal(v) < 0),
    ]
    for field, code, message, check in rules:
        invalid = [r for r in norms if check(r[field])]
        if invalid:
            return reject(invalid, code, message)
    hierarchy, iteration = norms[:], 0
    while hierarchy and iteration < 100:
        parent_keys = {(_sql_key(r["SKUCode"]), _sql_key(r["ParentWhCode"])) for r in hierarchy}
        hierarchy = [r for r in hierarchy if _key(r) in parent_keys]
        iteration += 1
    if iteration >= 100:
        return reject(hierarchy, 25, lambda r: "ParentWhCode=" + r["ParentWhCode"] + ", Parent-Child relationship is forming a loop")

    descriptions = _distinct([r for r in raw if r["SKUCode"] is not None], ("SKUCode", "SKUDescription"))
    tables["SKUDescriptionTbl"] = []  # TRUNCATE commits before the INSERT.
    if any(r["SKUDescription"] is None for r in descriptions):
        # Without either NMSActive setting, source normalization never runs.
        # SQL catches the NOT NULL failure, keeping prior later tables, not
        # pretending a raw rejection or an applied master update occurred.
        return finish("SQL_ERROR")
    tables["SKUDescriptionTbl"] = descriptions
    descriptions = _distinct([{"WHCode": r[c], "WHDescription": r[n]} for r in raw for c, n in (("WhCode", "WHDescription"), ("ParentWhCode", "ParentDescription")) if r[c] is not None], ("WHCode", "WHDescription"))
    tables["SiteDescriptionTbl"] = []
    if any(r["WHDescription"] is None for r in descriptions):
        return finish("SQL_ERROR")
    tables["SiteDescriptionTbl"] = descriptions
    for row in norms:
        for field, default in (("PackSize", 1), ("StockPercentForRationing", 100), ("NormPercentReservation", 0)):
            if row[field] is None:
                row[field] = default

    def attributes(identity, fields):
        grouped = defaultdict(list)
        for row in raw:
            if row[identity] is not None:
                grouped[_sql_key(row[identity])].append(row)
        results = []
        for group in grouped.values():
            if len({r[identity] for r in group}) != 1:
                raise LegacyMasterAmbiguity("LEGACY_FLAW: attribute identity collation has unspecified spelling")
            item = {"SKUCode" if identity == "SKUCode" else "WHCode": group[0][identity]}
            for source, target in fields:
                values = [r[source] for r in group]
                numeric = source in {"ElephantOrderCapping", "Weight", "Volume"}
                preferred = [v for v in values if v is not None] if numeric else [v for v in values if v is not None and len(v.rstrip(" ")) > 0]
                candidates = preferred or values
                if target in CUSTOM:
                    candidates = [v if v is not None else "" for v in candidates]
                if len(set(candidates)) != 1:
                    raise LegacyMasterAmbiguity(f"LEGACY_FLAW: FIRST_VALUE has multiple equally-preferred values: {identity}={group[0][identity]} {source}")
                item[target] = candidates[0]
            results.append(item)
        return results

    tables["SkuAttributeData"] = attributes("SKUCode", [(f, f) for f in ("ElephantOrderCapping", "Weight", "Volume", *SKU_LEVELS)] + [(f"SKUAtt{i:02}", f"c{i}") for i in range(1, 16)])
    tables["LocationAttributeData"] = attributes("WhCode", [(f, f) for f in ("LocationType", "LogisticsLocation", *LOC_LEVELS)] + [(f"LocAtt{i:02}", f"c{i}") for i in range(1, 16)])
    existing_locations = {_sql_key(r["WHCode"]) for r in tables["LocationAttributeData"]}
    tables["LocationAttributeData"].extend({f: r["WHCode"] if f == "WHCode" else None for f in LOC_ATTRIBUTES}
                                          for r in tables["SiteDescriptionTbl"] if _sql_key(r["WHCode"]) not in existing_locations)
    tables["SkuLocAttributeData"] = [
        {"SKUCode": r["SKUCode"], "LocCode": r["WhCode"], **{f: r[f] for f in SKULOC_ATTRIBUTES[2:8]},
         "NonNMS": int(any(_join(r, n) for n in added_non_nms)), **{f"c{i}": r[f"SKULocAtt{i:02}"] for i in range(1, 16)}} for r in norms
    ]
    prior = tables["MasterData"]
    for row in prior:
        if not any(_join(row, n) for n in norms):
            tables["RetiredNormsTbl"].append({"SKUCode": row["SKUCode"], "WhCode": row["WhCode"], "Norm": row["Norm"], "Event_Date": day, "Event_Type": 0})
    retained = [r for r in prior if any(_join(r, n) for n in norms)]
    if setting("UpdatePWh_RLT_RCP_GCP", 1) == 1:
        for row in retained:
            incoming = next(n for n in norms if _join(row, n))
            row.update({f: incoming[f] for f in REFRESH})
    new = [r for r in norms if not any(_join(r, p) for p in retained)]
    for row in new:
        if any(_join(row, h) for h in tables["RetiredNormsTbl"]):
            tables["RetiredNormsTbl"].append({"SKUCode": row["SKUCode"], "WhCode": row["WhCode"], "Norm": row["Norm"], "Event_Date": day, "Event_Type": 1})
    tables["MasterData"] = retained + [{f: day if f == "SKUIntroDate" else r[f] for f in MASTER_COLUMNS} for r in new]
    tables["ForceNormChange"] = [r for r in tables["ForceNormChange"] if not any(_join(r, a) for a in auto_force)] + auto_force
    return finish("APPLIED")
