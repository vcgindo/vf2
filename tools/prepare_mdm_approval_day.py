"""Prepare the governed MDM approval-day input package without executing it.

The recipe is deliberately narrow.  It reduces the retained sizeable temporal
input to the twenty approved SKU/location identities, replaces supplier inputs
with the already-registered ten-pair supplier rows, applies the approved NMS
flags, and declares only the two approved day-zero bootstrap requests.  The
thirteen later requests are emitted as a workflow sidecar; they are never added
to an engine day feed by this tool.
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
from tools.reduce_daily_smoke import (
    EMPTY_PATHS,
    GLOBAL_PATHS,
    LOCATION_PATHS,
    PAIR_PATHS,
    SKU_PATHS,
    SPECIAL_PATHS,
    _get,
    _leaf_populations,
    _location,
    _record,
    _set,
    _sha256,
    _sku,
    _validate_intermediate_directory,
)


SOURCE = Path("F:/vflow_integrated/.local-stage7/block3-sizeable/v1/sizeable-input.json")
CATALOGUE = Path(
    "F:/vflow_integrated/.local-stage7/block1-selected-consumers/permission-input-v1.json"
)
SUPPLIER_REFERENCE = Path(
    "D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/ten-pair-input-v1.json"
)
REQUEST_MAP = ROOT / "docs/MDM_APPROVAL_DAY_SOURCE_EXIT_MAP.json"
DECISION = ROOT / "docs/MDM_APPROVAL_DAY_SOURCE_DECISION.md"
OUTPUT_DIR = Path("D:/freshvcf-build/evidence/mdm-approval-day-20261010-001")

SOURCE_SHA256 = "0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546"
CATALOGUE_SHA256 = "18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356"
SUPPLIER_REFERENCE_SHA256 = (
    "7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc"
)
REQUEST_MAP_SHA256 = "fbf504c44b8d2c64ca3555d41d03fac091bac73eb9a5ea97a45bec65289b11fc"
DECISION_SHA256 = "2df5dd266c5ff328cba9384cf3080d8eb38d73065b01b6a2669dccde67342a4a"
SOURCE_SCHEMA = "block3-sizeable-input-v1"
RECIPE = "fresh-mdm-approval-day-package-v1"

TARGET_SKUS = ("337", "6120")
TARGET_LOCATIONS = (
    "AG515802",
    "DP010290",
    "DP020819",
    "LDC001",
    "LDC002",
    "LDC006",
    "LP001",
    "LP002",
    "MT0513",
    "PPI000604",
)
PARENT_LOCATIONS = ("PL001", "PL002")
TARGET_PAIRS = tuple(
    (sku, location) for sku in TARGET_SKUS for location in TARGET_LOCATIONS
)
PROPOSED_EXECUTION_DATES = ("2026-06-06", "2026-06-07", "2026-06-08")

SUPPLIER_PATHS = {
    "case/opening/supplier/MOQData",
    "case/opening/supplier/SOBData",
    "case/static_day/supplier_feeds/MOQDataRaw1",
    "case/static_day/supplier_feeds/SOBDataRaw",
}

D0_PHASE_REQUEST = {
    "Approved": True,
    "PhaseInSKUCode": None,
    "SKUCode": "6120",
    "WhCode": "DP010290",
}
D0_SEASON_REQUEST = {
    "ActivateDBM": False,
    "Approved": True,
    "BuildupDuration": 1,
    "DeltaNormPercentage": None,
    "EndDate": "2026-06-20",
    "SKUCode": "6120",
    "StartDate": "2026-06-06",
    "TargetNorm": 300,
    "UpperLowerCap": None,
    "WhCode": "AG515802",
}

ARTIFACT_NAME = "mdm-approval-day-input-v1.json"
RECEIPT_NAME = "mdm-approval-day-reduction-v1.json"
HIERARCHY_NAME = "mdm-approval-day-hierarchy-v1.json"
REQUESTS_NAME = "mdm-approval-day-post-d0-requests-v1.json"
MANIFEST_NAME = "mdm-approval-day-package-manifest-v1.json"


def _read_pinned(path: Path, expected_sha256: str, description: str) -> bytes:
    raw = path.read_bytes()
    if _sha256(raw) != expected_sha256:
        raise ValueError(description + " identity differs")
    return raw


def _filter_pair(rows, path, pairs):
    output = []
    target_skus = set(TARGET_SKUS)
    for row in rows:
        sku = _sku(row, path)
        pair = (sku, _location(row, path))
        if sku in target_skus and pair not in pairs:
            raise ValueError("Selected SKU has an external pair dependency: " + path)
        if pair in pairs:
            output.append(row)
    return output


def _set_parameter(rows, parameter, expected, replacement, path):
    matches = [row for row in rows if row.get("Parameter") == parameter]
    if len(matches) != 1 or matches[0].get("Value") != expected:
        raise ValueError(f"{path} {parameter} authority differs")
    matches[0]["Value"] = replacement


def _supplier_rows(reference):
    case = reference["case"]
    return {
        "case/opening/supplier/MOQData": deepcopy(case["opening"]["supplier"]["MOQData"]),
        "case/opening/supplier/SOBData": deepcopy(case["opening"]["supplier"]["SOBData"]),
        "case/static_day/supplier_feeds/MOQDataRaw1": deepcopy(
            case["static_day"]["supplier_feeds"]["MOQDataRaw1"]
        ),
        "case/static_day/supplier_feeds/SOBDataRaw": deepcopy(
            case["static_day"]["supplier_feeds"]["SOBDataRaw"]
        ),
    }


def _assert_supplier_contract(rows):
    raw_moq = rows["case/static_day/supplier_feeds/MOQDataRaw1"]
    raw_sob = rows["case/static_day/supplier_feeds/SOBDataRaw"]
    if raw_moq != [{
        "MOQ": 10,
        "SKUCode": "6120",
        "SupplierCode": "PL001",
        "SupplierDescription": "Plant Jakarta & Karawang",
    }]:
        raise ValueError("Registered supplier MOQ reference differs")
    expected_locations = ["LDC001", "LDC002", "LDC006"]
    if [row.get("WHCode") for row in raw_sob] != expected_locations:
        raise ValueError("Registered supplier SOB location order differs")
    for row in raw_sob:
        if (
            row.get("SKUCode") != "6120"
            or row.get("SOB") != 100
            or row.get("SupplierCode") != "PL001"
            or row.get("SupplierDescription") != "Plant Jakarta & Karawang"
        ):
            raise ValueError("Registered supplier SOB reference differs")
    for path, path_rows in rows.items():
        if any(str(row.get("SKUCode")) == "337" for row in path_rows):
            raise ValueError("Supplier reference contains an inferred SKU 337 row: " + path)


def _hierarchy_projection(catalogue):
    if set(catalogue) != {
        "contract", "evidence_boundary", "identities", "input_sha256", "locations",
        "parent_code", "products", "receiving_code", "version",
    }:
        raise ValueError("Retained hierarchy catalogue schema differs")
    products = [
        deepcopy(row)
        for row in catalogue["products"]["attributes"]
        if str(row.get("code")) in TARGET_SKUS
    ]
    locations = [
        deepcopy(row)
        for row in catalogue["locations"]["attributes"]
        if str(row.get("code")) in set(TARGET_LOCATIONS) | set(PARENT_LOCATIONS)
    ]
    if [str(row["code"]) for row in products] != list(TARGET_SKUS):
        raise ValueError("Retained product hierarchy coverage or order differs")
    expected_location_order = [
        code
        for code in (row["code"] for row in catalogue["locations"]["attributes"])
        if code in set(TARGET_LOCATIONS) | set(PARENT_LOCATIONS)
    ]
    if [str(row["code"]) for row in locations] != expected_location_order:
        raise ValueError("Retained location hierarchy order differs")
    if set(expected_location_order) != set(TARGET_LOCATIONS) | set(PARENT_LOCATIONS):
        raise ValueError("Retained location hierarchy coverage differs")
    for row in products:
        if set(row) != {"code", "level_1", "level_2", "level_3"}:
            raise ValueError("Product hierarchy exposes an unapproved field")
    for row in locations:
        if set(row) != {"code", "level_1", "level_2", "level_3"}:
            raise ValueError("Location hierarchy exposes an unapproved field")
    return {
        "schema": "fresh-mdm-approval-day-hierarchy-v1",
        "authority": {
            "path": CATALOGUE.as_posix(),
            "sha256": CATALOGUE_SHA256,
            "contract": catalogue["contract"],
            "version": catalogue["version"],
        },
        "allowed_fields": {
            "product": ["code", "level_1", "level_2", "level_3"],
            "location": ["code", "level_1", "level_2", "level_3"],
        },
        "products": products,
        "locations": locations,
    }


def _reduce_case(source, supplier_reference, records):
    if set(source) != {
        "case", "commands", "days", "external_fact_ledger", "opening",
        "opening_date", "profile", "static_day",
    }:
        raise ValueError("Temporal case schema differs")
    pairs = set(TARGET_PAIRS)
    required_locations = set(TARGET_LOCATIONS) | set(PARENT_LOCATIONS)
    classified = (
        set(PAIR_PATHS) | set(SKU_PATHS) | set(LOCATION_PATHS) |
        set(GLOBAL_PATHS) | set(EMPTY_PATHS) | set(SPECIAL_PATHS)
    )
    classified.discard("cohort_assignment")
    actual = _leaf_populations(source)
    if actual != classified:
        raise ValueError("Unclassified temporal populations: " + repr(sorted(actual ^ classified)))

    result = deepcopy(source)
    result["case"] = "mdm-approval-day-20261010-001"
    reference_rows = _supplier_rows(supplier_reference)
    _assert_supplier_contract(reference_rows)

    for full_path in PAIR_PATHS:
        if full_path in {"case/days/*/raw_daily", "cohort_assignment"}:
            continue
        path = full_path.removeprefix("case/")
        before = _get(source, path)
        if full_path in SUPPLIER_PATHS:
            after = reference_rows[full_path]
            strategy = "exact-registered-supplier-reference"
        else:
            after = _filter_pair(before, full_path, pairs)
            strategy = "exact-pair"
        _set(result, path, after)
        _record(records, full_path, strategy, before, after)
    for full_path in SKU_PATHS:
        path = full_path.removeprefix("case/")
        before = _get(source, path)
        if full_path in SUPPLIER_PATHS:
            after = reference_rows[full_path]
            strategy = "exact-registered-supplier-reference"
        else:
            after = [row for row in before if _sku(row, full_path) in set(TARGET_SKUS)]
            strategy = "target-SKU-directory"
        _set(result, path, after)
        _record(records, full_path, strategy, before, after)
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
        if sku in set(TARGET_SKUS):
            if (sku, location) not in pairs or any(
                str(row[name]) not in required_locations
                for name in ("from_location", "to_location", "logistics_location")
            ):
                raise ValueError("Selected logistics row references an external location")
            reduced_logistics.append(row)
    result["profile"]["calculation"]["logistics"]["items"] = reduced_logistics
    _record(records, logistics_path, "pair-with-location-closure", logistics, reduced_logistics)

    # Source commands and control requests belong to the full-size scenario.  The
    # approved package has its own explicit bootstrap queues and no action command.
    _record(records, "case/commands", "approved-empty-bootstrap-queue", source["commands"], [])
    result["commands"] = []
    for day_index, (source_day, output_day) in enumerate(zip(source["days"], result["days"])):
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
            before_requests = source_day["control_requests"][name]
            after_requests = []
            if day_index == 0 and name == "phase_requests":
                after_requests = [deepcopy(D0_PHASE_REQUEST)]
            elif day_index == 0 and name == "season_requests":
                after_requests = [deepcopy(D0_SEASON_REQUEST)]
            output_day["control_requests"][name] = after_requests
            _record(
                records, path, "approved-explicit-bootstrap-queue",
                before_requests, after_requests,
            )
        path = "case/days/*/new_force_requests"
        before_requests = source_day["new_force_requests"]
        selected_requests = _filter_pair(before_requests, path, pairs)
        if selected_requests:
            raise ValueError("Selected source force request is outside the approved bootstrap")
        output_day["new_force_requests"] = selected_requests
        _record(
            records, path, "exact-pair-assert-empty-approved-bootstrap",
            before_requests, selected_requests,
        )
        path = "case/days/*/order_feed"
        before_orders = source_day["order_feed"]
        selected_orders = _filter_pair(before_orders, path, pairs)
        output_day["order_feed"] = selected_orders
        _record(records, path, "exact-pair", before_orders, selected_orders)
        # Status remains native and truthful even when the selected order rows are empty.
        if output_day.get("order_feed_status") != source_day.get("order_feed_status"):
            raise ValueError("Order feed status changed during reduction")

    _set_parameter(
        result["opening"]["importer_settings"], "NMSActive", "0", "1",
        "case/opening/importer_settings",
    )
    _set_parameter(
        result["opening"]["controls"]["importer_settings"], "NMSActive", "0", "1",
        "case/opening/controls/importer_settings",
    )
    _set_parameter(
        result["opening"]["controls"]["dbm_settings"], "FNC_MatchMasterNorm", "1", "0",
        "case/opening/controls/dbm_settings",
    )
    _set_parameter(
        result["opening"]["dbm"]["DBMSettingsTbl"], "FNC_MatchMasterNorm", "1", "0",
        "case/opening/dbm/DBMSettingsTbl",
    )
    for full_path in (
        "case/opening/importer_settings",
        "case/opening/controls/importer_settings",
        "case/opening/controls/dbm_settings",
        "case/opening/dbm/DBMSettingsTbl",
    ):
        entry = records[full_path]
        entry["strategy"] = "approved-parameter-overlay"
        entry["output"][-1] = _get(result, full_path.removeprefix("case/"))
    force_flags = result["profile"].get("force_flags")
    if force_flags != {
        "from_ui": True, "ignore_master_norm": False, "nms_active": False,
    }:
        raise ValueError("Source force flag profile differs")
    force_flags["ignore_master_norm"] = True
    force_flags["nms_active"] = True
    for path in (
        result["opening"]["importer_settings"],
        result["opening"]["controls"]["importer_settings"],
    ):
        values = {row["Parameter"]: row["Value"] for row in path}
        if values.get("PI_PO_UploadApproved") != "0":
            raise ValueError("PI_PO_UploadApproved changed from the approved disabled state")
        if values.get("NMSMOQInputDataFormat") != "WithoutDestLoc":
            raise ValueError("NMS MOQ input format differs")
        if values.get("ActivateNMSUIUploadLogs") != "1":
            raise ValueError("NMS upload-log activation differs")

    ledger = result["external_fact_ledger"]
    ledger["shipments_sha256"] = digest(ledger["shipments"])
    ledger["reconciliation_sha256"] = digest(ledger["daily_reconciliation"])
    ledger["counts"] = {
        "identities": len(TARGET_PAIRS),
        "fact_rows": len(ledger["daily_reconciliation"]),
        "shipments": len(ledger["shipments"]),
    }
    return result


def build_package(
    source_raw: bytes,
    catalogue_raw: bytes,
    supplier_reference_raw: bytes,
    request_map_raw: bytes,
    decision_raw: bytes,
):
    identities = {
        "source": (_sha256(source_raw), SOURCE_SHA256),
        "catalogue": (_sha256(catalogue_raw), CATALOGUE_SHA256),
        "supplier reference": (_sha256(supplier_reference_raw), SUPPLIER_REFERENCE_SHA256),
        "request map": (_sha256(request_map_raw), REQUEST_MAP_SHA256),
        "decision": (_sha256(decision_raw), DECISION_SHA256),
    }
    for name, (actual, expected) in identities.items():
        if actual != expected:
            raise ValueError(name + " identity differs")
    payload = json.loads(source_raw)
    catalogue = json.loads(catalogue_raw)
    supplier_reference = json.loads(supplier_reference_raw)
    request_map = json.loads(request_map_raw)
    if (
        set(payload) != {
            "case", "cohort_assignment", "identity_guard",
            "manifest_contract_sha256", "retained_identity", "schema",
        }
        or payload["schema"] != SOURCE_SCHEMA
    ):
        raise ValueError("Retained sizeable input schema differs")
    if request_map.get("schema") != "fresh-mdm-approval-day-source-exit-map-v1":
        raise ValueError("MDM request map schema differs")
    if len(request_map.get("families", [])) != 13:
        raise ValueError("MDM request map no longer contains exactly thirteen families")
    if (
        request_map.get("new_days_authorized") != 0
        or request_map.get("serving_change_authorized") is not False
    ):
        raise ValueError("MDM request map execution boundary differs")

    records = {}
    reduced_case = _reduce_case(payload["case"], supplier_reference, records)
    cohort = _filter_pair(
        payload["cohort_assignment"], "cohort_assignment", set(TARGET_PAIRS)
    )
    _record(records, "cohort_assignment", "exact-pair", payload["cohort_assignment"], cohort)
    raw_master = reduced_case["static_day"]["raw_master"]
    actual_pairs = [
        (str(row["SKUCode"]), str(row["WhCode"])) for row in raw_master
    ]
    if actual_pairs != list(TARGET_PAIRS):
        raise ValueError("Approved twenty-pair source coverage or order differs")
    parents = {
        str(row["ParentWhCode"])
        for row in raw_master
        if (str(row["SKUCode"]), str(row["ParentWhCode"])) not in set(TARGET_PAIRS)
    }
    if parents != set(PARENT_LOCATIONS):
        raise ValueError("Approved physical parent closure differs")
    parent_by_sku = {
        sku: {
            str(row["ParentWhCode"])
            for row in raw_master
            if str(row["SKUCode"]) == sku
            and str(row["WhCode"]) in {"LDC001", "LDC002", "LDC006"}
        }
        for sku in TARGET_SKUS
    }
    if parent_by_sku != {"337": {"PL002"}, "6120": {"PL001"}}:
        raise ValueError("Approved per-SKU physical parent mapping differs")

    derivative = {
        "schema": SOURCE_SCHEMA,
        "case": reduced_case,
        "cohort_assignment": cohort,
    }
    classifications = {
        path: {
            "strategy": entry["strategy"],
            "occurrences": len(entry["source"]),
            "source_rows": sum(len(rows) for rows in entry["source"]),
            "derived_rows": sum(len(rows) for rows in entry["output"]),
            "source_digest": digest(entry["source"]),
            "derived_digest": digest(entry["output"]),
        }
        for path, entry in sorted(records.items())
    }
    ledger_validation = validate(derivative)
    dates = [day["business_date"] for day in derivative["case"]["days"]]
    if dates[:3] != list(PROPOSED_EXECUTION_DATES) or len(dates) != 12:
        raise ValueError("Retained temporal horizon or proposed first three dates differs")
    hierarchy = _hierarchy_projection(catalogue)
    workflow_requests = {
        "schema": "fresh-mdm-approval-day-post-d0-requests-v1",
        "authority": {
            "path": REQUEST_MAP.as_posix(),
            "sha256": REQUEST_MAP_SHA256,
            "schema": request_map["schema"],
        },
        "boundary": {
            "delivery": "authenticated workflow inputs after accepted D0",
            "engine_day_feed": False,
            "new_days_authorized": 0,
            "registration_authorized": False,
            "runtime_mutation_authorized": False,
            "serving": False,
        },
        "families": deepcopy(request_map["families"]),
    }
    derivative["derivative_provenance"] = {
        "schema": "fresh-mdm-approval-day-derivative-provenance-v1",
        "recipe": RECIPE,
        "source_path": SOURCE.as_posix(),
        "source_sha256": SOURCE_SHA256,
        "source_schema": payload["schema"],
        "source_case": payload["case"]["case"],
        "source_manifest_contract_sha256": payload["manifest_contract_sha256"],
        "decision_path": DECISION.as_posix(),
        "decision_sha256": DECISION_SHA256,
        "target_pairs": [list(pair) for pair in TARGET_PAIRS],
        "external_parent_locations": list(PARENT_LOCATIONS),
        "proposed_execution_dates": list(PROPOSED_EXECUTION_DATES),
        "retained_ledger_dates": dates,
        "removed_full_identity_fields": ["identity_guard", "retained_identity"],
        "supplier_reference_sha256": SUPPLIER_REFERENCE_SHA256,
        "hierarchy_projection_digest": digest(hierarchy),
        "post_d0_request_plan_digest": digest(workflow_requests),
        "classification_digest": digest(classifications),
        "ledger_validation": ledger_validation,
    }
    receipt = {
        "schema": "fresh-mdm-approval-day-reduction-receipt-v1",
        "recipe": RECIPE,
        "authorities": {
            "source": {"path": SOURCE.as_posix(), "sha256": SOURCE_SHA256},
            "decision": {"path": DECISION.as_posix(), "sha256": DECISION_SHA256},
            "hierarchy": {"path": CATALOGUE.as_posix(), "sha256": CATALOGUE_SHA256},
            "supplier": {
                "path": SUPPLIER_REFERENCE.as_posix(),
                "sha256": SUPPLIER_REFERENCE_SHA256,
            },
            "request_map": {"path": REQUEST_MAP.as_posix(), "sha256": REQUEST_MAP_SHA256},
        },
        "approved_scope": {
            "opening_date": derivative["case"]["opening_date"],
            "pairs": [list(pair) for pair in TARGET_PAIRS],
            "proposed_execution_dates": list(PROPOSED_EXECUTION_DATES),
            "retained_horizon_dates": dates,
            "d0_phase_requests": [deepcopy(D0_PHASE_REQUEST)],
            "d0_season_requests": [deepcopy(D0_SEASON_REQUEST)],
            "flag_overlays": {
                "NMSActive": "1",
                "FNC_MatchMasterNorm": "0",
                "force_flags": {
                    "from_ui": True,
                    "ignore_master_norm": True,
                    "nms_active": True,
                },
                "preserved": {
                    "PI_PO_UploadApproved": "0",
                    "NMSMOQInputDataFormat": "WithoutDestLoc",
                    "ActivateNMSUIUploadLogs": "1",
                },
            },
            "new_days_authorized": 0,
            "execution_authorized": False,
            "registration_authorized": False,
            "serving": False,
        },
        "classifications": classifications,
        "derivative_payload_digest": digest(derivative),
        "hierarchy_payload_digest": digest(hierarchy),
        "workflow_request_payload_digest": digest(workflow_requests),
        "ledger_validation": ledger_validation,
    }
    return derivative, receipt, hierarchy, workflow_requests


def _json_bytes(value, *, pretty=False):
    if pretty:
        text = json.dumps(value, indent=2, ensure_ascii=False)
    else:
        text = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return (text + "\n").encode("utf-8")


def prepare(output_dir: Path, source: Path, catalogue: Path,
            supplier_reference: Path, request_map: Path, decision: Path):
    # Pin before parsing and construct every payload before creating the owned directory.
    source_raw = _read_pinned(source, SOURCE_SHA256, "Retained sizeable artifact")
    catalogue_raw = _read_pinned(catalogue, CATALOGUE_SHA256, "Hierarchy catalogue")
    supplier_raw = _read_pinned(
        supplier_reference, SUPPLIER_REFERENCE_SHA256, "Registered supplier reference"
    )
    request_raw = _read_pinned(request_map, REQUEST_MAP_SHA256, "MDM request map")
    decision_raw = _read_pinned(decision, DECISION_SHA256, "MDM source decision")
    derivative, receipt, hierarchy, workflow_requests = build_package(
        source_raw, catalogue_raw, supplier_raw, request_raw, decision_raw
    )
    encoded = {
        ARTIFACT_NAME: _json_bytes(derivative),
        HIERARCHY_NAME: _json_bytes(hierarchy, pretty=True),
        REQUESTS_NAME: _json_bytes(workflow_requests, pretty=True),
    }
    receipt = {
        **receipt,
        "files": {
            name: {"sha256": _sha256(raw), "bytes": len(raw)}
            for name, raw in encoded.items()
        },
    }
    encoded[RECEIPT_NAME] = _json_bytes(receipt, pretty=True)
    manifest = {
        "schema": "fresh-mdm-approval-day-package-manifest-v1",
        "recipe": RECIPE,
        "draft": True,
        "registration_authorized": False,
        "execution_authorized": False,
        "files": [
            {"path": name, "sha256": _sha256(raw), "bytes": len(raw)}
            for name, raw in encoded.items()
        ],
    }
    encoded[MANIFEST_NAME] = _json_bytes(manifest, pretty=True)
    if output_dir.exists() and not output_dir.is_dir():
        raise FileExistsError("Package destination is not a directory: " + str(output_dir))
    destinations = [output_dir / name for name in encoded]
    existing = [str(path) for path in destinations if path.exists()]
    if existing:
        raise FileExistsError("Refusing to replace package file(s): " + repr(existing))
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, raw in encoded.items():
        with (output_dir / name).open("xb") as stream:
            stream.write(raw)
    return {
        "output_dir": str(output_dir),
        "files": {
            name: {"sha256": _sha256(raw), "bytes": len(raw)}
            for name, raw in encoded.items()
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--catalogue", type=Path, default=CATALOGUE)
    parser.add_argument("--supplier-reference", type=Path, default=SUPPLIER_REFERENCE)
    parser.add_argument("--request-map", type=Path, default=REQUEST_MAP)
    parser.add_argument("--decision", type=Path, default=DECISION)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    result = prepare(
        args.output_dir, args.source, args.catalogue, args.supplier_reference,
        args.request_map, args.decision,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
