"""Pure, fail-closed reduction of the registered sizeable temporal input.

Only the ten SKU 6120 pairs qualified by ``prepare_daily_smoke.py`` are kept.
Rows are never regenerated or reordered.  Every operational list population is
classified below as pair, SKU, location, global/control, empty-only, or a
dependency-bearing command/request.  A new population, a nonempty table that
was declared empty, or a retained row that also references an external pair is
an error.

The full-estate ``retained_identity`` and ``identity_guard`` projections are
deliberately not copied: their hashes describe 1,240 pairs.  The derivative has
new provenance and recomputed external-ledger counts/hashes, but remains
unregistered until the primary governance step adopts its immutable bytes.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mta.serialization import digest
from parity.temporal_ledger import validate


SOURCE = Path("F:/vflow_integrated/.local-stage7/block3-sizeable/v1/sizeable-input.json")
SOURCE_SHA256 = "0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546"
SOURCE_SCHEMA = "block3-sizeable-input-v1"
RECIPE = "fresh-ten-pair-daily-reduction-v1"
TARGET_SKU = "6120"
TARGET_LOCATIONS = (
    "AG515802", "DP010290", "DP020819", "LDC001", "LDC002",
    "LDC006", "LP001", "LP002", "MT0513", "PPI000604",
)
EXTERNAL_PARENT = "PL001"
TARGET_PAIRS = tuple((TARGET_SKU, location) for location in TARGET_LOCATIONS)


PAIR_PATHS = (
    "case/external_fact_ledger/daily_reconciliation",
    "case/external_fact_ledger/shipments",
    "case/opening/bpr/BPRMaster", "case/opening/bpr/DailyConsumption",
    "case/opening/controls/dbm_master", "case/opening/controls/importer_master",
    "case/opening/dbm/DBMMaster", "case/opening/dbm/DailyConsumption",
    "case/opening/dbm/SKULocStandardAttributes",
    "case/opening/dbm/SkuLocAttributeData",
    "case/opening/dbm/SuspendExistingDisabledNormsTbl",
    "case/opening/importer/MasterData", "case/opening/importer/SkuLocAttributeData",
    "case/opening/supplier/MOQData", "case/opening/supplier/SOBData",
    "case/profile/calculation/policies", "case/profile/calculation/stock_openings",
    "case/static_day/raw_master", "case/static_day/supplier_feeds/SOBDataRaw",
    "case/days/*/raw_daily", "cohort_assignment",
)

SKU_PATHS = (
    "case/opening/dbm/SKUDescriptionTbl", "case/opening/dbm/SkuAttributeData",
    "case/opening/importer/SKUDescriptionTbl", "case/opening/importer/SkuAttributeData",
    "case/profile/calculation/skus", "case/static_day/supplier_feeds/MOQDataRaw1",
)

LOCATION_PATHS = (
    "case/opening/dbm/LocationAttributeData", "case/opening/dbm/SiteDescriptionTbl",
    "case/opening/importer/LocationAttributeData", "case/opening/importer/SiteDescriptionTbl",
    "case/profile/calculation/locations",
)

GLOBAL_PATHS = (
    "case/opening/bpr/Plants",
    "case/opening/consumer_context/CategoryColDescription",
    "case/opening/consumer_context/GoodsInTransitTransporterMaster",
    "case/opening/control_aux/season_status",
    "case/opening/controls/IntermediateTables", "case/opening/controls/dbm_settings",
    "case/opening/controls/importer_settings", "case/opening/controls/last_batch",
    "case/opening/controls/reason_codes", "case/opening/dbm/DBMSettingsTbl",
    "case/opening/dbm/FirstReplenishmentPercentageTbl",
    "case/opening/dbm/IntermediateTables", "case/opening/dbm/LastBatchRunTbl",
    "case/opening/dbm/ReasonCodes", "case/opening/dbm/VFSettings",
    "case/opening/dbm/ui_ReportConfigurations", "case/opening/importer_settings",
    "case/opening/orders/OrderIdentity", "case/profile/daily/settings",
    "case/profile/daily/vf_settings",
)

EMPTY_PATHS = (
    "case/days/*/accepted_feed",
    "case/opening/bpr/NoNormMaster",
    "case/opening/btr/BPR", "case/opening/btr/LocationAttributeData",
    "case/opening/btr/SKUDescriptionTbl", "case/opening/btr/SiteDescriptionTbl",
    "case/opening/btr/SkuAttributeData", "case/opening/btr/SkuLocAttributeData",
    "case/opening/consumer_context/CWH_List", "case/opening/consumer_context/DistributorList",
    "case/opening/consumer_context/NMSAllItems",
    "case/opening/control_aux/phase_exceptions", "case/opening/control_aux/phase_in_norms",
    "case/opening/control_aux/phase_in_requests", "case/opening/control_aux/phase_map",
    "case/opening/control_aux/phase_requests", "case/opening/control_aux/phase_stops",
    "case/opening/control_aux/season_requests",
    "case/opening/controls/acceptance", "case/opening/controls/accepted",
    "case/opening/controls/force_requests", "case/opening/controls/forced",
    "case/opening/controls/log", "case/opening/controls/order_summary",
    "case/opening/controls/phase_in", "case/opening/controls/phase_out",
    "case/opening/controls/raw_master", "case/opening/controls/seasonality",
    "case/opening/controls/suggestions", "case/opening/controls/suggestions_log",
    "case/opening/controls/suspend_order_type", "case/opening/controls/triggers",
    "case/opening/controls/upload_log",
    "case/opening/dbm/DBMDelistingOfNormsWithHits", "case/opening/dbm/DiscardedSuggestions",
    "case/opening/dbm/ForcedNormChangeTbl", "case/opening/dbm/Norm0Norm1Norm2Report",
    "case/opening/dbm/Norm0_1_2ReportDetails", "case/opening/dbm/Norm1IncreaseSuggestions",
    "case/opening/dbm/NormAcceptanceTbl", "case/opening/dbm/NormChangeLogTbl",
    "case/opening/dbm/NormsInSleepModeTbl", "case/opening/dbm/OrderData",
    "case/opening/dbm/OrderDataSummary", "case/opening/dbm/OrderRuleSummary",
    "case/opening/dbm/PhaseInTbl", "case/opening/dbm/PhaseOutTbl",
    "case/opening/dbm/Seasonality", "case/opening/dbm/SpikeReport",
    "case/opening/dbm/Suggestions", "case/opening/dbm/SuggestionsLog",
    "case/opening/dbm/SuspendAcceptedNormsConsumptionType",
    "case/opening/dbm/SuspendAcceptedNormsStockType", "case/opening/dbm/SuspendAggrCommon",
    "case/opening/dbm/SuspendAggrCommonWithOrderType",
    "case/opening/dbm/SuspendAggrConsumptionType", "case/opening/dbm/SuspendAggrStockType",
    "case/opening/dbm/SuspendConsumptionType", "case/opening/dbm/SuspendConsumptionTypePre",
    "case/opening/dbm/SuspendCustomSKUTbl", "case/opening/dbm/SuspendHistory",
    "case/opening/dbm/SuspendInsuffDataPointsTbl", "case/opening/dbm/SuspendMinNormTbl",
    "case/opening/dbm/SuspendNewSKUTbl", "case/opening/dbm/SuspendNormsForceChangedTbl",
    "case/opening/dbm/SuspendNormsInSleepModeTbl", "case/opening/dbm/SuspendOrderType",
    "case/opening/dbm/SuspendOrderTypePre", "case/opening/dbm/SuspendPhaseInTbl",
    "case/opening/dbm/SuspendPhaseOutTbl", "case/opening/dbm/SuspendSeasonalityTbl",
    "case/opening/dbm/SuspendSpikeTbl", "case/opening/dbm/SuspendStepOneOrderTypeTbl",
    "case/opening/dbm/SuspendStepOneTbl", "case/opening/dbm/SuspendStockType",
    "case/opening/dbm/SuspendStockTypePre", "case/opening/dbm/SuspendSupplyIssueTbl",
    "case/opening/dbm/SuspendWhitesTbl", "case/opening/importer/ForceNormChange",
    "case/opening/importer/RejectedMaster", "case/opening/importer/RetiredNormsTbl",
    "case/opening/orders/ElephantOrders", "case/opening/orders/NewSpikeOrders",
    "case/opening/orders/SpikeOrderClosureHistory", "case/opening/orders/SpikeOrderData",
    "case/profile/calculation/replenishment_exclusions",
    "case/profile/daily/distributor_codes", "case/profile/daily/vector_dms_codes",
    "case/profile/daily/vendor_codes", "case/static_day/distributor_transactions",
    "case/static_day/exclusions", "case/static_day/order_raw", "case/static_day/raw_no_norm",
    "case/static_day/raw_non_nms", "case/static_day/supplier_feeds/MOQDataRaw2",
    "case/static_day/vendor_transactions",
)

SPECIAL_PATHS = (
    "case/commands", "case/days/*/control_requests/phase_in_requests",
    "case/days/*/control_requests/phase_requests",
    "case/days/*/control_requests/phase_stops",
    "case/days/*/control_requests/season_requests", "case/days/*/new_force_requests",
    "case/days/*/order_feed", "case/profile/calculation/logistics/items",
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _value(row, names, path):
    found = [row[name] for name in names if name in row]
    if len(found) != 1 or found[0] is None:
        raise ValueError("Classified population lacks one identity field: " + path)
    return str(found[0])


def _sku(row, path):
    return _value(row, ("SKUCode", "sku_code"), path)


def _location(row, path):
    return _value(row, ("WhCode", "WHCode", "LocCode", "location_code"), path)


def _record(records, path, strategy, source, output):
    records.setdefault(path, {"strategy": strategy, "source": [], "output": []})
    entry = records[path]
    if entry["strategy"] != strategy:
        raise ValueError("Population classification changed: " + path)
    entry["source"].append(source)
    entry["output"].append(output)


def _leaf_populations(value, path="case"):
    result = set()
    if isinstance(value, dict):
        for name, child in value.items():
            result |= _leaf_populations(child, path + "/" + name)
    elif isinstance(value, list):
        if path == "case/days":
            for child in value:
                result |= _leaf_populations(child, "case/days/*")
        else:
            result.add(path)
    return result


def _get(root, path):
    value = root
    for name in path.split("/"):
        value = value[name]
    return value


def _set(root, path, value):
    names = path.split("/")
    target = root
    for name in names[:-1]:
        target = target[name]
    target[names[-1]] = value


def _filter_pair(rows, path, pairs):
    output = []
    for row in rows:
        sku = _sku(row, path)
        location = _location(row, path)
        pair = (sku, location)
        if sku == TARGET_SKU and pair not in pairs:
            raise ValueError("Selected SKU has an external pair dependency: " + path)
        if pair in pairs:
            output.append(row)
    return output


def _referenced_pairs(row, path):
    location = _location(row, path)
    names = [name for name in ("SKUCode", "PhaseInSKUCode") if row.get(name) is not None]
    if not names:
        raise ValueError("Dependency row has no SKU reference: " + path)
    return {(str(row[name]), location) for name in names}


def _filter_dependencies(rows, path, pairs):
    output = []
    for row in rows:
        references = _referenced_pairs(row, path)
        intersection = references & pairs
        if intersection and references != intersection:
            raise ValueError("Cross-SKU/pair dependency touches retained smoke scope: " + path)
        if intersection:
            output.append(row)
    return output


def _filter_commands(rows, pairs):
    output = []
    for row in rows:
        selected = {tuple(map(str, pair)) for pair in row.get("selected", [])}
        intersection = selected & pairs
        if intersection and selected != intersection:
            raise ValueError("Command mixes retained and external pairs")
        if intersection:
            output.append(row)
    return output


def _validate_intermediate_directory(rows, path):
    if any(set(row) != {"table", "rows"} or not isinstance(row["table"], str)
           or row["rows"] != [] for row in rows):
        raise ValueError("Intermediate table directory gained state rows: " + path)


def _reduce_case(source, records):
    if set(source) != {"case", "commands", "days", "external_fact_ledger", "opening",
                       "opening_date", "profile", "static_day"}:
        raise ValueError("Temporal case schema differs")
    pairs = set(TARGET_PAIRS)
    required_locations = set(TARGET_LOCATIONS) | {EXTERNAL_PARENT}

    classified = set(PAIR_PATHS) | set(SKU_PATHS) | set(LOCATION_PATHS) | \
        set(GLOBAL_PATHS) | set(EMPTY_PATHS) | set(SPECIAL_PATHS)
    classified.discard("cohort_assignment")
    actual = _leaf_populations(source)
    if actual != classified:
        raise ValueError("Unclassified temporal populations: " +
                         repr(sorted(actual ^ classified)))
    result = deepcopy(source)
    result["case"] = "ten-pair-smoke-derivative"

    for full_path in PAIR_PATHS:
        if full_path in ("case/days/*/raw_daily", "cohort_assignment"):
            continue
        path = full_path.removeprefix("case/")
        before = _get(source, path)
        after = _filter_pair(before, full_path, pairs)
        _set(result, path, after)
        _record(records, full_path, "exact-pair", before, after)
    for full_path in SKU_PATHS:
        path = full_path.removeprefix("case/")
        before = _get(source, path)
        after = [row for row in before if _sku(row, full_path) == TARGET_SKU]
        _set(result, path, after)
        _record(records, full_path, "target-SKU-directory", before, after)
    for full_path in LOCATION_PATHS:
        path = full_path.removeprefix("case/")
        before = _get(source, path)
        after = [row for row in before if _location(row, full_path) in required_locations]
        _set(result, path, after)
        _record(records, full_path, "selected-plus-parent-location-directory", before, after)
    for full_path in GLOBAL_PATHS:
        path = full_path.removeprefix("case/")
        before = _get(source, path)
        if full_path.endswith("/IntermediateTables"):
            _validate_intermediate_directory(before, full_path)
        _record(records, full_path, "preserved-global-control", before, before)
    for full_path in EMPTY_PATHS:
        if full_path.startswith("case/days/*/"):
            continue
        path = full_path.removeprefix("case/")
        before = _get(source, path)
        if before:
            raise ValueError("Population declared empty is nonempty: " + full_path)
        _record(records, full_path, "assert-empty", before, before)

    logistics_path = "case/profile/calculation/logistics/items"
    logistics = source["profile"]["calculation"]["logistics"]["items"]
    reduced_logistics = []
    for row in logistics:
        sku = _sku(row, logistics_path)
        location = _location(row, logistics_path)
        if sku == TARGET_SKU:
            if (sku, location) not in pairs or any(str(row[name]) not in required_locations
                    for name in ("from_location", "to_location", "logistics_location")):
                raise ValueError("Selected logistics row references an external location")
            reduced_logistics.append(row)
    result["profile"]["calculation"]["logistics"]["items"] = reduced_logistics
    _record(records, logistics_path, "pair-with-location-closure", logistics, reduced_logistics)

    commands = _filter_commands(source["commands"], pairs)
    result["commands"] = commands
    _record(records, "case/commands", "command-all-references-contained", source["commands"], commands)
    for source_day, output_day in zip(source["days"], result["days"]):
        before = source_day["raw_daily"]
        after = _filter_pair(before, "case/days/*/raw_daily", pairs)
        output_day["raw_daily"] = after
        _record(records, "case/days/*/raw_daily", "exact-pair", before, after)
        accepted = source_day["accepted_feed"]
        if accepted:
            raise ValueError("Unclassified accepted feed became nonempty")
        _record(records, "case/days/*/accepted_feed", "assert-empty", accepted, accepted)
        for name in ("phase_in_requests", "phase_requests", "phase_stops", "season_requests"):
            path = "case/days/*/control_requests/" + name
            before = source_day["control_requests"][name]
            after = _filter_dependencies(before, path, pairs)
            output_day["control_requests"][name] = after
            _record(records, path, "request-all-references-contained", before, after)
        for name in ("new_force_requests", "order_feed"):
            path = "case/days/*/" + name
            before = source_day[name]
            after = _filter_dependencies(before, path, pairs)
            output_day[name] = after
            _record(records, path, "request-all-references-contained", before, after)

    ledger = result["external_fact_ledger"]
    ledger["shipments_sha256"] = digest(ledger["shipments"])
    ledger["reconciliation_sha256"] = digest(ledger["daily_reconciliation"])
    ledger["counts"] = {
        "identities": len(TARGET_PAIRS),
        "fact_rows": len(ledger["daily_reconciliation"]),
        "shipments": len(ledger["shipments"]),
    }
    return result


def reduce_document(raw: bytes):
    actual_sha = _sha256(raw)
    if actual_sha != SOURCE_SHA256:
        raise ValueError("Retained sizeable artifact identity differs")
    payload = json.loads(raw)
    if (set(payload) != {"case", "cohort_assignment", "identity_guard",
                         "manifest_contract_sha256", "retained_identity", "schema"}
            or payload["schema"] != SOURCE_SCHEMA):
        raise ValueError("Retained sizeable input schema differs")
    records = {}
    reduced_case = _reduce_case(payload["case"], records)
    cohort = _filter_pair(payload["cohort_assignment"], "cohort_assignment", set(TARGET_PAIRS))
    _record(records, "cohort_assignment", "exact-pair", payload["cohort_assignment"], cohort)

    raw_master = reduced_case["static_day"]["raw_master"]
    if [(str(row["SKUCode"]), str(row["WhCode"])) for row in raw_master] != list(TARGET_PAIRS):
        raise ValueError("Qualified ten-pair source order differs")
    parents = {str(row["ParentWhCode"]) for row in raw_master
               if (TARGET_SKU, str(row["ParentWhCode"])) not in set(TARGET_PAIRS)}
    if parents != {EXTERNAL_PARENT}:
        raise ValueError("External parent closure differs")

    derivative = {
        "schema": SOURCE_SCHEMA,
        "case": reduced_case,
        "cohort_assignment": cohort,
    }
    classifications = {
        path: {
            "strategy": entry["strategy"], "occurrences": len(entry["source"]),
            "source_rows": sum(len(rows) for rows in entry["source"]),
            "derived_rows": sum(len(rows) for rows in entry["output"]),
            "source_digest": digest(entry["source"]),
            "derived_digest": digest(entry["output"]),
        }
        for path, entry in sorted(records.items())
    }
    ledger_validation = validate(derivative)
    provenance = {
        "schema": "fresh-daily-smoke-derivative-provenance-v1",
        "recipe": RECIPE,
        "source_path": SOURCE.as_posix(),
        "source_sha256": actual_sha,
        "source_schema": payload["schema"],
        "source_case": payload["case"]["case"],
        "source_manifest_contract_sha256": payload["manifest_contract_sha256"],
        "target_pairs": [list(pair) for pair in TARGET_PAIRS],
        "external_parent_locations": [EXTERNAL_PARENT],
        "removed_full_identity_fields": ["identity_guard", "retained_identity"],
        "classification_digest": digest(classifications),
        "ledger_validation": ledger_validation,
    }
    derivative["derivative_provenance"] = provenance
    receipt = {
        "schema": "fresh-daily-smoke-reduction-receipt-v1",
        "source_sha256": actual_sha,
        "recipe": RECIPE,
        "classifications": classifications,
        "derivative_payload_digest": digest(derivative),
        "ledger_validation": ledger_validation,
    }
    return derivative, receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    derivative, receipt = reduce_document(raw)
    encoded = (json.dumps(derivative, separators=(",", ":"),
                          ensure_ascii=False) + "\n").encode("utf-8")
    receipt = {**receipt, "derivative_file_sha256": _sha256(encoded),
               "derivative_bytes": len(encoded)}
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.destination.open("xb") as stream:
        stream.write(encoded)
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"destination": str(args.destination), "receipt": str(args.receipt),
                      "sha256": receipt["derivative_file_sha256"]}))


if __name__ == "__main__":
    main()
