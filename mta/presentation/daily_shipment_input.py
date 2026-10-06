"""Read the registered standalone ten-pair shipment-input supplement."""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path

from mta.application.daily_transit import RAW_FIELDS
from mta.serialization import digest


SOURCE_SHA256 = "7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc"
PARENT_SHA256 = "0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546"
CONVENTION = "fresh-ten-pair-daily-shipment-input-v1"
OUTPUT_SCHEMA = "fresh-ten-pair-shipment-input-derivative-v1"
RAW_SCHEMA = "daily-transit-raw-v1"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_supplement(payload, *, base_artifact_sha256: str):
    """Validate the immutable standalone wire shape without reading the base."""
    _require(isinstance(payload, dict)
             and set(payload) == {"schema", "base_artifact_sha256", "provenance", "days"},
             "Shipment supplement shape differs")
    _require(payload["schema"] == OUTPUT_SCHEMA,
             "Shipment supplement schema differs")
    _require(payload["base_artifact_sha256"] == base_artifact_sha256 == SOURCE_SHA256,
             "Shipment supplement base artifact differs")
    provenance = payload["provenance"]
    _require(isinstance(provenance, dict)
             and provenance.get("convention") == CONVENTION
             and provenance.get("source_artifact_sha256") == SOURCE_SHA256
             and provenance.get("parent_artifact_sha256") == PARENT_SHA256,
             "Shipment supplement provenance differs")
    days = payload["days"]
    _require(isinstance(days, list) and len(days) == 12,
             "Shipment supplement must contain twelve days")
    dates = []
    for item in days:
        _require(isinstance(item, dict)
                 and set(item) == {"business_date", "shipment_input"},
                 "Shipment supplement day shape differs")
        business_date = item["business_date"]
        date.fromisoformat(business_date)
        shipment_input = item["shipment_input"]
        _require(isinstance(shipment_input, dict)
                 and set(shipment_input) == {"schema", "business_date", "provenance", "rows"}
                 and shipment_input["schema"] == RAW_SCHEMA
                 and shipment_input["business_date"] == business_date,
                 "Dated shipment input shape differs")
        rows = shipment_input["rows"]
        _require(isinstance(rows, list)
                 and all(list(row) == list(RAW_FIELDS) for row in rows),
                 "Daily shipment row fields or order differ")
        reconciliation = shipment_input["provenance"].get("daily_reconciliation", {})
        _require(reconciliation.get("business_date") == business_date
                 and reconciliation.get("occurrences") == len(rows)
                 and reconciliation.get("quantity") == sum(row["InTransitQty"] for row in rows)
                 and reconciliation.get("shipment_ids_digest")
                 == digest([row["OrderNo"] for row in rows])
                 and reconciliation.get("rows_digest") == digest(rows),
                 "Daily shipment reconciliation differs")
        dates.append(business_date)
    _require(len(set(dates)) == 12 and dates == sorted(dates),
             "Shipment supplement dates differ")
    _require(provenance.get("daily_reconciliation") == [
        item["shipment_input"]["provenance"]["daily_reconciliation"]
        for item in days
    ], "Top-level shipment reconciliation differs")
    return payload


def load_day(path: Path, *, expected_sha256: str, business_date,
             base_artifact_sha256: str = SOURCE_SHA256):
    """Load one registered daily source after full supplement verification."""
    raw = Path(path).read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == expected_sha256,
             "Registered shipment supplement identity differs")
    payload = validate_supplement(json.loads(raw),
                                  base_artifact_sha256=base_artifact_sha256)
    target = business_date.isoformat() if isinstance(business_date, date) else str(business_date)
    matches = [item["shipment_input"] for item in payload["days"]
               if item["business_date"] == target]
    _require(len(matches) == 1, "Shipment supplement business date is unavailable")
    return deepcopy(matches[0])
