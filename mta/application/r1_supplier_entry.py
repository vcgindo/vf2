"""R1 raw supplier facts and independent prior BPR supplier-state boundary."""
from copy import deepcopy
from datetime import date

from mta.application.r1_raw_master_entry import RAW_MASTER_SCHEMA, validate_raw_master_run
from mta.application.r1_supplier_input import OPENING_TABLES, typed_supplier_tables

RAW_SUPPLIER_SCHEMA = "r1-current-day-input-v7"
SUPPLIER_STATE_FIELDS = {"prior_sob": OPENING_TABLES["SOBData"], "prior_moq": OPENING_TABLES["MOQData"],
                         "refreshed_sob": OPENING_TABLES["SOBData"], "refreshed_moq": OPENING_TABLES["MOQData"]}


def master_input_skeleton(payload):
    """No supplier business projection: safe for either independent producer."""
    view = deepcopy(payload)
    for field in ("raw_supplier_entry", "supplier_state", "vendor_codes"):
        del view[field]
    view.update(schema=RAW_MASTER_SCHEMA, sourcing=[], supplier_openings=[])
    return view


def validate_supplier_run(payload):
    if not isinstance(payload, dict) or payload.get("schema") != RAW_SUPPLIER_SCHEMA:
        raise ValueError("Invalid R1 v7 supplier entry")
    if {"sourcing", "supplier_openings"} & set(payload):
        raise ValueError("R1 v7 cannot supply derived supplier projections")
    if not {"raw_supplier_entry", "supplier_state", "vendor_codes"} <= set(payload):
        raise ValueError("R1 v7 requires raw supplier feeds, prior state and VendorList")
    validate_raw_master_run(master_input_skeleton(payload))
    typed_supplier_tables(payload["raw_supplier_entry"])
    state = payload["supplier_state"]
    if not isinstance(state, dict) or set(state) != {*OPENING_TABLES, "opening_provenance"}:
        raise ValueError("Independent SOBData/MOQData prior state required")
    typed_supplier_tables({k: state[k] for k in OPENING_TABLES}, OPENING_TABLES)
    provenance = state["opening_provenance"]
    if (not isinstance(provenance, dict) or set(provenance) != {"kind", "identity", "business_date"}
            or provenance["kind"] != "SYNTHETIC_PRIOR_BPR_SUPPLIER"
            or not isinstance(provenance["identity"], str) or not provenance["identity"].strip()
            or date.fromisoformat(provenance["business_date"]) >= date.fromisoformat(payload["raw_master_entry"]["business_date"])):
        raise ValueError("Supplier opening must be explicitly labelled prior synthetic BPR state")
    codes = payload["vendor_codes"]
    if (not isinstance(codes, list) or any(not isinstance(c, str) or not c.isascii() or len(c) > 50 for c in codes)
            or len({c.rstrip(' ').upper() for c in codes}) != len(codes)):
        raise ValueError("VendorList requires explicit SQL-key-unique codes")
