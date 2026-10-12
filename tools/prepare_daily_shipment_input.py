"""Build the approved immutable ten-pair daily shipment-input derivative.

This generator adds declared shipment metadata to the registered ten-pair
artifact.  It does not calculate shipments, fill SLT/Price, execute an engine,
or alter the retained seven-field external ledger.

Authority: ``docs/DAILY_SHIPMENT_INPUT_CONTRACT.md`` and the explicit approval
recorded for convention ``fresh-ten-pair-daily-shipment-input-v1``.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application.daily_transit import RAW_FIELDS
from mta.presentation.daily_shipment_input import (
    CONVENTION, OUTPUT_SCHEMA, PARENT_SHA256, RAW_SCHEMA, SOURCE_SHA256,
    APPROVAL_SOURCE_SHA256, APPROVAL_CONVENTION, APPROVAL_OUTPUT_SCHEMA, validate_supplement,
)
from mta.serialization import digest
from parity.temporal_ledger import validate as validate_ledger


SOURCE = Path(
    "D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/"
    "ten-pair-input-v1.json"
)
REDUCTION_RECEIPT = SOURCE.with_name("ten-pair-reduction-v1.json")
REDUCTION_RECEIPT_SHA256 = "2991f82c0caa452c8a83fbdfc5e80f730c794303b01985a104cff73370d0541b"
APPROVAL_REDUCTION_SHA256 = '9040342fe26170beaf4d9fa0839a2ad6ecc11157d586ebb30c310240a70750b7'
RECEIPT_SCHEMA = "fresh-ten-pair-shipment-input-receipt-v1"
LEDGER_FIELDS = (
    "SKUCode", "WhCode", "dispatch_date", "git_duration_days", "quantity",
    "receipt_date", "shipment_id",
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _transporter_index(shipment_id: str, count: int) -> int:
    first_eight = hashlib.sha256(shipment_id.encode("utf-8")).digest()[:8]
    return int.from_bytes(first_eight, "big", signed=False) % count


def _source_contract(source_raw: bytes, reduction_raw: bytes):
    if _sha256(source_raw) == APPROVAL_SOURCE_SHA256:
        _require(_sha256(reduction_raw) == APPROVAL_REDUCTION_SHA256,
                 'Approved MDM reduction receipt identity differs')
        source, reduction = json.loads(source_raw), json.loads(reduction_raw)
        # The reduction receipt describes the preserved pre-amendment package.
        # Strip only the separately approved initial-NMS delta when checking it.
        base = deepcopy(source)
        amendment = base['derivative_provenance'].pop('initial_nms_owner')
        _require(amendment['base_artifact_sha256'] ==
                 '7586426e7b061499e17d5d89d73c33b77c89d8c5671ffa65b3f929c9a536f100'
                 and digest(base['case']['opening']['consumer_context']['NMSAllItems']) ==
                 amendment['output_digest'], 'Approved initial NMS amendment differs')
        base['case']['opening']['consumer_context']['NMSAllItems'] = []
        _require(digest(base) == reduction['derivative_payload_digest'],
                 'Approved MDM reduction payload differs')
        return source
    _require(_sha256(source_raw) == SOURCE_SHA256,
             "Registered ten-pair artifact identity differs")
    _require(_sha256(reduction_raw) == REDUCTION_RECEIPT_SHA256,
             "Registered ten-pair reduction receipt identity differs")
    source = json.loads(source_raw)
    reduction = json.loads(reduction_raw)
    provenance = source.get("derivative_provenance", {})
    _require(source.get("schema") == "block3-sizeable-input-v1",
             "Registered ten-pair schema differs")
    _require(provenance.get("source_sha256") == PARENT_SHA256,
             "Full retained parent identity differs")
    _require(reduction.get("source_sha256") == PARENT_SHA256
             and reduction.get("derivative_file_sha256") == SOURCE_SHA256,
             "Ten-pair reduction lineage differs")
    _require(digest(source) == reduction.get("derivative_payload_digest"),
             "Ten-pair reduction payload digest differs")
    return source


def _catalogue(case, expected_count=10):
    rows = case["static_day"]["raw_master"]
    _require(isinstance(rows, list) and len(rows) == expected_count,
             "Ten-pair current catalogue population differs")
    parents = {}
    for row in rows:
        _require(all(name in row for name in ("SKUCode", "WhCode", "ParentWhCode")),
                 "Catalogue parent mapping is incomplete")
        key = str(row["SKUCode"]), str(row["WhCode"])
        _require(key not in parents, "Catalogue pair is ambiguous")
        _require(row["ParentWhCode"] is not None,
                 "Catalogue parent mapping is NULL")
        parents[key] = row["ParentWhCode"]
    opening = case["opening"]["importer"]["MasterData"]
    opening_parents = {
        (str(row["SKUCode"]), str(row["WhCode"])): row["ParentWhCode"]
        for row in opening
    }
    _require(len(opening_parents) == len(opening)
             and opening_parents == parents,
             "Opening and current catalogue parent mappings differ")
    projection = [
        {"SKUCode": row["SKUCode"], "WhCode": row["WhCode"],
         "ParentWhCode": row["ParentWhCode"]}
        for row in rows
    ]
    return rows, projection, parents


def _directory(case):
    rows = case["opening"]["consumer_context"]["GoodsInTransitTransporterMaster"]
    _require(isinstance(rows, list) and len(rows) == 4,
             "Retained transporter directory must contain exactly four rows")
    expected = {"TransporterCode", "TransporterName", "TransporterContact"}
    codes = []
    for row in rows:
        _require(set(row) == expected, "Transporter directory shape differs")
        code = row["TransporterCode"]
        _require(isinstance(code, str) and code and code not in codes,
                 "Transporter directory code is missing or duplicated")
        codes.append(code)
    return rows, codes


def _raw_row(shipment, business_date, parent, transporter):
    values = {
        "SKUCode": shipment["SKUCode"],
        "ToLocationCode": shipment["WhCode"],
        "FromLocationCode": parent,
        "CurrentLocationCode": None,
        "LRCode": shipment["shipment_id"],
        "OrderNo": shipment["shipment_id"],
        "CreationDate": shipment["dispatch_date"],
        "GateOutDate": shipment["dispatch_date"],
        "InTransitQty": shipment["quantity"],
        "TransporterCode": transporter,
        "Remark": None,
        "ReportDate": business_date,
    }
    return {name: values[name] for name in RAW_FIELDS}


def build_derivative(source_raw: bytes, reduction_raw: bytes, *, generator_sha256: str):
    """Return the standalone supplement and its hash-independent receipt body."""
    _require(isinstance(generator_sha256, str) and len(generator_sha256) == 64,
             "Generator SHA256 is required")
    source = _source_contract(source_raw, reduction_raw)
    source_sha = _sha256(source_raw)
    active = source_sha == APPROVAL_SOURCE_SHA256
    convention = APPROVAL_CONVENTION if active else CONVENTION
    output_schema = APPROVAL_OUTPUT_SCHEMA if active else OUTPUT_SCHEMA
    reduction_sha = APPROVAL_REDUCTION_SHA256 if active else REDUCTION_RECEIPT_SHA256
    # This also proves that adding metadata never repairs or replaces the ledger.
    ledger_validation = validate_ledger(source)
    case = source["case"]
    catalogue, parent_projection, parents = _catalogue(case, 20 if active else 10)
    directory, transporter_codes = _directory(case)
    shipments = case["external_fact_ledger"]["shipments"]
    _require(isinstance(shipments, list), "Shipment ledger must be a list")
    for shipment in shipments:
        _require(set(shipment) == set(LEDGER_FIELDS),
                 "Shipment ledger row shape differs")
        _require(type(shipment["quantity"]) is int and shipment["quantity"] > 0,
                 "Shipment quantity must be a positive integer")
        _require(isinstance(shipment["shipment_id"], str)
                 and shipment["shipment_id"], "Shipment ID is required")
    _require(len(case['days']) == 12, "Retained conserved source horizon differs")
    days = case['days'][:3] if active else case['days']
    if active:
        _require([day['business_date'] for day in days] ==
                 ['2026-06-06', '2026-06-07', '2026-06-08'],
                 "Approved shipment execution dates differ")
    _require(all("shipment_input" not in day for day in days),
             "Source already contains shipment input")

    common = {
        "schema": 'fresh-mdm-approval-day-shipment-provenance-v1' if active else "fresh-ten-pair-shipment-input-provenance-v1",
        "convention": convention,
        "source_artifact_sha256": source_sha,
        "parent_artifact_sha256": PARENT_SHA256,
        "reduction_receipt_sha256": reduction_sha,
        "generator_sha256": generator_sha256,
        "catalogue_path": "case/static_day/raw_master",
        "catalogue_count": len(catalogue),
        "catalogue_digest": digest(catalogue),
        "parent_mapping_digest": digest(parent_projection),
        "directory_path": (
            "case/opening/consumer_context/GoodsInTransitTransporterMaster"
        ),
        "directory_count": len(directory),
        "directory_digest": digest(directory),
        "ledger_shipments_digest": digest(shipments),
    }
    supplement_days = []
    daily = []
    for source_day in days:
        business_date = source_day["business_date"]
        date.fromisoformat(business_date)
        active = [
            shipment for shipment in shipments
            if shipment["dispatch_date"] <= business_date < shipment["receipt_date"]
        ]
        rows = []
        for shipment in active:
            key = str(shipment["SKUCode"]), str(shipment["WhCode"])
            _require(key in parents, "Shipment pair is absent from the catalogue")
            index = _transporter_index(shipment["shipment_id"], len(transporter_codes))
            rows.append(_raw_row(shipment, business_date, parents[key],
                                 transporter_codes[index]))
        expected_quantity = sum(shipment["quantity"] for shipment in active)
        actual_quantity = sum(row["InTransitQty"] for row in rows)
        expected_ids = [shipment["shipment_id"] for shipment in active]
        _require([row["OrderNo"] for row in rows] == expected_ids,
                 "Daily shipment occurrence order differs")
        _require(actual_quantity == expected_quantity,
                 "Daily shipment quantity differs from the ledger")
        aggregate_git = sum(row["GIT"] for row in source_day["raw_daily"])
        _require(actual_quantity == aggregate_git,
                 "Daily shipment quantity differs from retained aggregate GIT")
        reconciliation = {
            "business_date": business_date,
            "occurrences": len(rows),
            "quantity": actual_quantity,
            "shipment_ids_digest": digest(expected_ids),
            "rows_digest": digest(rows),
        }
        shipment_input = {
            "schema": RAW_SCHEMA,
            "business_date": business_date,
            "provenance": {**common, "daily_reconciliation": reconciliation},
            "rows": rows,
        }
        supplement_days.append({"business_date": business_date,
                                "shipment_input": shipment_input})
        daily.append(reconciliation)

    derivative = {
        "schema": output_schema,
        "base_artifact_sha256": source_sha,
        "provenance": {
            **common,
            "daily_reconciliation": daily,
            "ledger_validation": ledger_validation,
            "excluded_fields": ["SLT", "Price"],
        },
        "days": supplement_days,
    }
    validate_supplement(derivative, base_artifact_sha256=source_sha)
    receipt = {
        "schema": 'fresh-mdm-approval-day-shipment-receipt-v1' if active else RECEIPT_SCHEMA,
        "convention": convention,
        "source_artifact_sha256": source_sha,
        "parent_artifact_sha256": PARENT_SHA256,
        "reduction_receipt_sha256": reduction_sha,
        "generator_sha256": generator_sha256,
        "catalogue": {
            "path": common["catalogue_path"], "count": len(catalogue),
            "digest": common["catalogue_digest"],
            "parent_mapping_digest": common["parent_mapping_digest"],
        },
        "directory": {
            "path": common["directory_path"], "count": len(directory),
            "digest": common["directory_digest"],
        },
        "ledger_validation": ledger_validation,
        "daily_reconciliation": daily,
        "derivative_payload_digest": digest(derivative),
    }
    return derivative, receipt


def encode_derivative(derivative) -> bytes:
    return (json.dumps(derivative, ensure_ascii=False, separators=(",", ":"))
            + "\n").encode("utf-8")


def write_derivative(source: Path, reduction_receipt: Path,
                     destination: Path, receipt_path: Path):
    generator_sha = _sha256(Path(__file__).read_bytes())
    derivative, receipt = build_derivative(
        source.read_bytes(), reduction_receipt.read_bytes(),
        generator_sha256=generator_sha,
    )
    encoded = encode_derivative(derivative)
    receipt = {
        **receipt,
        "derivative_file_sha256": _sha256(encoded),
        "derivative_bytes": len(encoded),
        "derivative_path": destination.as_posix(),
    }
    receipt_bytes = (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(encoded)
    with receipt_path.open("xb") as stream:
        stream.write(receipt_bytes)
    domain = 'twenty-pair three-date MDM' if _sha256(source.read_bytes()) == APPROVAL_SOURCE_SHA256 else 'ten-pair'
    manifest_records = [
        {
            "path": destination.as_posix(),
            "role": f"approved {domain} immutable daily shipment-input derivative",
            "sha256": receipt["derivative_file_sha256"],
            "bytes": len(encoded),
        },
        {
            "path": receipt_path.as_posix(),
            "role": f"{domain} daily shipment-input generation provenance",
            "sha256": _sha256(receipt_bytes),
            "bytes": len(receipt_bytes),
        },
    ]
    return receipt, manifest_records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--reduction-receipt", type=Path,
                        default=REDUCTION_RECEIPT)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt, records = write_derivative(
        args.source, args.reduction_receipt, args.destination, args.receipt
    )
    print(json.dumps({"receipt": receipt, "manifest_records": records}))


if __name__ == "__main__":
    main()
