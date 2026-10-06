"""Prepare evidence for a retained ten-pair daily smoke; never execute it.

The resulting manifest deliberately remains BLOCKED until a reduced artifact,
MDM source revision and MDM-aware parity admission are pinned.  This tool only
qualifies an unchanged retained source slice and its external facts.
"""
from __future__ import annotations

from collections import Counter
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
SOURCE_MANIFEST = SOURCE.with_name("manifest.json")
DESTINATION = Path("D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/smoke-preparation-001.json")
TARGET_SKU = "6120"
EXPECTED_LOCATIONS = (
    "AG515802", "DP010290", "DP020819", "LDC001", "LDC002",
    "LDC006", "LP001", "LP002", "MT0513", "PPI000604",
)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identity(row):
    return str(row["SKUCode"]), str(row.get("WhCode", row.get("WHCode")))


def selected(rows, pairs):
    return [row for row in rows if identity(row) in pairs]


def main() -> None:
    actual_sha = sha256(SOURCE)
    if actual_sha != SOURCE_SHA256:
        raise ValueError("Retained sizeable artifact identity differs")
    baseline = json.loads((ROOT / "baseline/manifest.json").read_text(encoding="utf-8"))
    registrations = [row for row in baseline["retained_resources"] if row["sha256"] == actual_sha]
    if registrations != [{
        "path": SOURCE.as_posix(),
        "role": "full-depth external facts and opening state",
        "sha256": SOURCE_SHA256,
        "bytes": SOURCE.stat().st_size,
    }]:
        raise ValueError("Retained sizeable artifact baseline registration differs")

    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    case = payload["case"]
    full_fact_validation = validate(payload)
    rows = [row for row in case["static_day"]["raw_master"] if str(row["SKUCode"]) == TARGET_SKU]
    pairs = [identity(row) for row in rows]
    expected_pairs = [(TARGET_SKU, location) for location in EXPECTED_LOCATIONS]
    if pairs != expected_pairs:
        raise ValueError("Qualified ten-pair source order differs")
    pair_set = set(pairs)

    edges = []
    for row in rows:
        parent = str(row["ParentWhCode"])
        parent_pair = (TARGET_SKU, parent)
        edges.append({
            "child": list(identity(row)), "parent_location": parent,
            "parent_pair_present": parent_pair in pair_set,
        })
    internal_edges = [edge for edge in edges if edge["parent_pair_present"]]
    external_edges = [edge for edge in edges if not edge["parent_pair_present"]]
    if len(internal_edges) != 7 or len(external_edges) != 3:
        raise ValueError("Qualified parent dependency counts differ")
    if {edge["parent_location"] for edge in external_edges} != {"PL001"}:
        raise ValueError("Qualified external parent reference differs")

    command_pairs = {tuple(pair) for command in case["commands"] for pair in command["selected"]}
    phase_pairs = set()
    for day in case["days"][:2]:
        requests = day["control_requests"]
        for name in ("phase_in_requests", "phase_requests", "phase_stops"):
            for row in requests.get(name, []):
                location = row.get("WhCode")
                for key in ("SKUCode", "PhaseInSKUCode"):
                    if row.get(key) is not None and location is not None:
                        phase_pairs.add((str(row[key]), str(location)))
    if pair_set & command_pairs or pair_set & phase_pairs:
        raise ValueError("Selected smoke pairs gained a retained command or phase request")

    ledger = case["external_fact_ledger"]
    fact_sets = {
        "raw_master": rows,
        "shipments": selected(ledger["shipments"], pair_set),
        "daily_reconciliation": selected(ledger["daily_reconciliation"], pair_set),
        "opening_bpr_daily_consumption": selected(case["opening"]["bpr"]["DailyConsumption"], pair_set),
        "opening_dbm_daily_consumption": selected(case["opening"]["dbm"]["DailyConsumption"], pair_set),
        "daily_raw": [row for day in case["days"] for row in selected(day["raw_daily"], pair_set)],
    }
    daily_counts = Counter()
    for day in case["days"]:
        daily_counts[day["business_date"]] = len(selected(day["raw_daily"], pair_set))
    if set(daily_counts.values()) != {10}:
        raise ValueError("A retained smoke day lacks an exact ten-pair raw fact bag")

    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    result = {
        "schema": "fresh-daily-smoke-preparation-v1",
        "status": "BLOCKED",
        "claim": "Source selection and external facts qualified; no smoke execution, calculation, publication, UI read, or parity PASS was performed.",
        "source": {
            "artifact": SOURCE.as_posix(), "artifact_sha256": actual_sha,
            "artifact_bytes": SOURCE.stat().st_size,
            "baseline_registration": registrations[0],
            "manifest": SOURCE_MANIFEST.as_posix(), "manifest_sha256": sha256(SOURCE_MANIFEST),
            "artifact_manifest_contract_sha256": payload["manifest_contract_sha256"],
            "canonical_configuration": manifest["canonical_configuration"],
        },
        "selection": {
            "sku": TARGET_SKU, "source_ordered_pairs": [list(pair) for pair in pairs],
            "target_pair_count": len(pairs), "raw_pair_closure_count": len(pair_set),
            "internal_parent_edge_count": len(internal_edges),
            "external_parent_edge_count": len(external_edges),
            "external_parent_locations": ["PL001"], "parent_edges": edges,
            "max_rlt": max(row["RLT"] for row in rows),
            "qualified_fact_horizon_days": len(case["days"]),
            "fixed_command_intersection_count": len(pair_set & command_pairs),
            "day1_successor_phase_intersection_count": len(pair_set & phase_pairs),
        },
        "boundaries": {
            "opening_date": case["opening_date"],
            "day1": case["days"][0]["business_date"],
            "successor": case["days"][1]["business_date"],
            "retained_last_day": case["days"][-1]["business_date"],
            "actor_label_in_existing_runner": "retained-synthetic-trial",
            "actor_account_binding": None,
        },
        "qualified_external_facts": {
            name: {"rows": len(value), "sha256": digest(value)} for name, value in fact_sets.items()
        } | {"daily_raw_counts": dict(daily_counts)},
        "full_registered_source_fact_validation": full_fact_validation,
        "blockers": [
            {
                "code": "NO_QUALIFIED_REDUCTION_RECIPE",
                "detail": "No reviewed table-by-table recipe exists for reducing every opening/profile/static/control population while preserving exact engine semantics. This manifest therefore does not create a derivative business artifact.",
            },
            {
                "code": "DERIVATIVE_NOT_REGISTERED_FOR_PARITY",
                "detail": "parity.replay_temporal.replay requires the unchanged expected SHA to be present in baseline/manifest.json; the only registered SHA is the full 1,240-pair artifact.",
            },
            {
                "code": "NO_PINNED_MDM_SOURCE",
                "detail": "The retained artifact does not bind an installed MdmSource, frozen three-family capture revisions, or pair-exclusion source revision for this smoke.",
            },
            {
                "code": "RUNNER_CANNOT_BIND_MDM",
                "detail": "run_temporal calls execute_day without mdm_source/mdm_retry arguments, so it cannot exercise the newly required daily MDM capture/consumption path.",
            },
            {
                "code": "NO_AUTHENTICATED_ACTOR_BINDING",
                "detail": "The runner has an audit actor label, but the artifact has no exact authenticated account and permission grant binding for smoke UI admission.",
            },
        ],
        "genuine_admission_path": [
            "Approve and implement an exact table-by-table reduction recipe; preserve source order, NULLs, duplicates, opening state and all dependencies.",
            "Install and pin an explicit MDM source plus immutable three-family and pair-exclusion revision identities for the reduced input.",
            "Register the immutable derivative artifact SHA through the baseline governance path and validate its external ledger.",
            "Use an MDM-aware root runner that passes the pinned mdm_source to execute_day for day1, then uses that run as the sole successor predecessor.",
            "Produce the matching independent canonical legacy replay for the same registered derivative; only record parity after every required comparison passes.",
            "Prepare and seal the required publication roster, select explicitly, then verify the authenticated UI with the pinned actor and scopes.",
        ],
        "execution_command": None,
    }
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with DESTINATION.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"destination": str(DESTINATION), "status": result["status"], "pairs": len(pairs)}))


if __name__ == "__main__":
    main()
