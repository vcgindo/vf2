"""Source-backed v3 wrappers for the finite H4 PostgreSQL lifecycle proof."""
from copy import deepcopy
from datetime import date, timedelta

from mta.application.production_source_inputs import SCHEMA
from mta.runtime.production_daily import SOURCE_SCHEMA
from tests.production_h3_fixture import (
    supplied_day, supplied_input as h3_supplied_input, CHILD, PARENT, ROOT,
)


def supplied_input():
    """Add the current DBM setting consumed by the native transit producer."""
    value = deepcopy(h3_supplied_input())
    value["opening"]["state"]["dbm"]["VFSettings"].append({
        "Parameter": "SuperDelayFactor",
        "Value": "2",
        "Description": "Declared H4 transit source setting",
    })
    value["recipe"]["version"] = "supplied-h4-source-report-integration-v1"
    value["opening"]["identity"] = "SUPPLIED-H4-SOURCE-REPORT"
    return value


def supplied_source_day(day, *, root=False):
    value = supplied_day(day, root=root)
    value["intake_schema"] = value["schema"]
    value["schema"] = SOURCE_SCHEMA
    value["producer_sources"] = {
        "schema": SCHEMA,
        "report_policy": {"bor_history_horizon": 90, "rrr_history_horizon": 90},
        "report_opening": {
            "BOR_OrderAllocationHistory": [], "RRR_OrderAllocationHistory": [],
        } if root else None,
        "shipments": {
            "schema": "daily-transit-raw-v1", "business_date": day,
            "provenance": {"source": "owned H4 external shipment fixture", "revision": day},
            "rows": [{
                "SKUCode": "SUPPLIED-Z9", "ToLocationCode": CHILD,
                "FromLocationCode": PARENT, "CurrentLocationCode": None,
                "LRCode": "H4-LR-" + day, "OrderNo": "H4-SHIP-" + day,
                "CreationDate": (date.fromisoformat(day) - timedelta(days=2)).isoformat(),
                "GateOutDate": (date.fromisoformat(day) - timedelta(days=1)).isoformat(),
                "InTransitQty": 4, "TransporterCode": "H4-CARRIER", "Remark": None,
                "ReportDate": day,
            }],
        },
        "transporters": {
            "schema": "daily-transporter-raw-v1", "business_date": day,
            "provenance": {"source": "owned H4 transporter fixture", "revision": day},
            "rows": [{"TransporterCode": "H4-CARRIER", "TransporterName": "H4 Carrier",
                      "TransporterContact": None}],
        },
    }
    if root:
        prior = (date.fromisoformat(day) - timedelta(days=1)).isoformat() + "T09:10:11+00:00"
        value["consumer_opening"]["remarks"] = {
            "bpr": [{"SKUCode": "SUPPLIED-Z9", "WhCode": CHILD, "Remark": "H4 opening",
                     "Username": "h4-proof", "RemarkDate": prior}],
            "bor": [{"SKUCode": "SUPPLIED-Z9", "WhCode": PARENT, "SupplierCode": ROOT,
                     "Remark": None, "Username": "h4-proof", "RemarkDate": prior}] * 2,
            "boroa": [{"SKUCode": "SUPPLIED-Z9", "WhCode": PARENT, "SupplierCode": ROOT,
                       "Remark": "H4 opening", "Username": None, "RemarkDate": prior}],
        }
    return value
