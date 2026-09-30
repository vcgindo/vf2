"""Connect generated Importer validation state to the existing R1 spine.

Projection is shared, calculation is not: the modern side passes its own
producer tables; the oracle passes tables captured after executing pinned SQL.
"""
from copy import deepcopy
from decimal import Decimal

from mta.application.r1_importer_master import validate_master_input
from mta.application.r1_master_state import MASTER_SCHEMA, MASTER_FIELDS

RAW_MASTER_SCHEMA = "r1-current-day-input-v6"
MASTER_SOURCE_FIELDS = ("SKUCode", "WhCode", "Norm", "MinNorm", "RLT", "RCP", "GCP", "OCP",
                        "MinOrderCount", "ParentWhCode", "SKUIntroDate")
MASTER_SOURCE_MAP = dict(zip(MASTER_FIELDS, MASTER_SOURCE_FIELDS))


def validate_raw_master_run(payload):
    required = {"schema", "foundation", "orders", "policies", "stock_openings", "allocation", "sourcing", "logistics",
                "supplier_openings", "stock_configuration", "replenishment_exclusions", "master_state", "raw_master_entry"}
    if not isinstance(payload, dict) or set(payload) != required or payload["schema"] != RAW_MASTER_SCHEMA:
        raise ValueError("Invalid R1 v6 raw-master contract")
    validate_master_input(payload["raw_master_entry"])
    state = payload["master_state"]
    required_state = {"dbm_opening", "opening_provenance"}
    control_fields = {"accepted_norm_input", "phase_control_input", "force_norm_input",
                      "season_control_input", "transit_tag_input", "control_diagnostics"}
    if (not isinstance(state, dict) or not required_state <= set(state)
            or set(state) - required_state - control_fields):
        raise ValueError("R1 v6 must not supply a processed Importer master")
    # R1-02/04: source requests and labelled prior control state travel through
    # raw validation unchanged. Only each engine's generated MasterData enters
    # the ordered control producer; never accept a caller's exported Norm here.
    if 'accepted_norm_input' in state:
        from mta.application.r1_parent_suggestions import validate_accepted_input
        validate_accepted_input(state['accepted_norm_input'], payload['raw_master_entry']['business_date'])
    if 'phase_control_input' in state:
        from mta.application.r1_phase_entry import validate_phase_input
        validate_phase_input(state['phase_control_input'], payload['raw_master_entry']['business_date'])
    if 'force_norm_input' in state:
        flags = state['force_norm_input']
        if (not isinstance(flags, dict) or set(flags) != {'from_ui','ignore_master_norm','nms_active'}
                or any(type(v) is not bool for v in flags.values())):
            raise ValueError('Raw entry force input owns flags only; requests and raw Norms belong to the master producer')
        nms = any(r['Parameter'] == 'NMSActive' and r['Value'] == 1 for r in payload['raw_master_entry']['settings'])
        if flags['nms_active'] != nms:
            raise ValueError('Forced-Norm NMS flag disagrees with selected raw master profile')
    if 'season_control_input' in state:
        from mta.application.r1_seasonality import validate_season_input
        validate_season_input(state['season_control_input'], payload['foundation']['snapshot']['business_date'])
    if 'transit_tag_input' in state:
        from mta.application.r1_transit_tags import validate_tag_input
        validate_tag_input(state['transit_tag_input'])
    if 'control_diagnostics' in state and (state['control_diagnostics'] is not True
            or not {'phase_control_input','force_norm_input'} <= state.keys()):
        raise ValueError('Selected diagnostics require explicit phase and force inputs')
    foundation = payload["foundation"]
    if not isinstance(foundation, dict) or set(foundation) != {"snapshot", "skus", "locations", "inventory_positions"}:
        raise ValueError("R1 v6 must not supply calculated foundation masters")
    if foundation["snapshot"]["business_date"] != payload["raw_master_entry"]["business_date"]:
        raise ValueError("R1 raw-master and calculation dates disagree")
    for section in ("policies", "stock_openings", "sourcing", "supplier_openings", "orders"):
        if not isinstance(payload[section], list) or any(not isinstance(r, dict) for r in payload[section]):
            raise ValueError(f"Invalid R1 v6 source section: {section}")
    for row in payload["policies"]:
        if row.get("controls") or not isinstance(row.get("policy"), dict) or set(row["policy"]) != {"spike_high", "spike_low", "pso_high", "pso_low"}:
            raise ValueError("R1 v6 local thresholds/controls must come from their upstream producers")
    if any(set(r) & {"norm", "stock_percent_reservation", "norm_percent_reservation"} for r in payload["stock_openings"]):
        raise ValueError("R1 v6 stock master fields belong to Importer validation")
    if any("pack_size" in r for section in ("sourcing", "supplier_openings") for r in payload[section]):
        raise ValueError("R1 v6 pack size belongs to Importer validation")
    if not isinstance(payload["logistics"], dict) or not isinstance(payload["logistics"].get("items"), list):
        raise ValueError("Invalid R1 v6 logistics source")
    if any(not isinstance(r, dict) or set(r) & {"weight", "volume", "pack_size", "logistics_location"} for r in payload["logistics"]["items"]):
        raise ValueError("R1 v6 logistics attributes belong to Importer validation")


def generated_master_view(payload, validation):
    """Map generated tables, not raw Norms or caller-supplied processed state."""
    validate_raw_master_run(payload)
    if validation["outcome"] == "SQL_ERROR":
        raise ValueError("R1 source master SQL_ERROR requires the entry failure contract; calculation not certified")
    tables = validation["tables"]
    if tables["ForceNormChange"] and "force_norm_input" not in payload["master_state"]:
        raise ValueError("R1 v6 force requests require the ordered pre-BPR control producer")
    view = deepcopy(payload)
    del view["raw_master_entry"]
    view["schema"] = MASTER_SCHEMA
    attrs = {(r["SKUCode"], r["LocCode"]): r for r in tables["SkuLocAttributeData"]}
    sku_attrs = {r["SKUCode"]: r for r in tables["SkuAttributeData"]}
    loc_attrs = {r["WHCode"]: r for r in tables["LocationAttributeData"]}
    importer = []
    for row in tables["MasterData"]:
        key = row["SKUCode"], row["WhCode"]
        if key not in attrs:
            raise ValueError("Produced Importer master lacks SKU/location attributes")
        importer.append({**{f: row[s] for f, s in MASTER_SOURCE_MAP.items()}, "pack_size": attrs[key]["PackSize"]})
    view["master_state"]["importer_master"] = importer
    if 'force_norm_input' in view['master_state']:
        view['master_state']['force_norm_input'].update(
            raw_master=[{f:r[f] for f in ('SKUCode','WhCode','Norm','MinNorm')} for r in tables['MasterDataRaw']],
            requests=[{f:r[f] for f in ('SKUCode','WhCode','NewNorm','Approved')} for r in tables['ForceNormChange']])
    for row in view["policies"]:
        source = attrs[(row["sku_code"], row["location_code"])]
        row["policy"].update(spike_override=source["SpikeThreshold"], pso_override=source["PSOThreshold"])
    for row in view["stock_openings"]:
        source = attrs[(row["sku_code"], row["location_code"])]
        row.update(stock_percent_reservation=source["StockPercentForRationing"], norm_percent_reservation=source["NormPercentReservation"])
    for section in ("sourcing", "supplier_openings"):
        for row in view[section]:
            row["pack_size"] = attrs[(row["sku_code"], row["location_code"])]["PackSize"]
    for row in view["logistics"]["items"]:
        sku, location = sku_attrs[row["sku_code"]], loc_attrs[row["to_location"]]
        row.update(weight=sku["Weight"], volume=sku["Volume"], logistics_location=location["LogisticsLocation"],
                   pack_size=attrs[(row["sku_code"], row["location_code"])]["PackSize"])
        if any(row[f] is None for f in ("weight", "volume", "logistics_location")):
            raise ValueError("Produced Importer lacks required logistics attributes; no invented defaults")
    for order in view["orders"]:
        cap = sku_attrs[order["sku_code"]]["ElephantOrderCapping"]
        if cap is not None and Decimal(order["outstanding_quantity"]) > cap:
            raise ValueError("R1 v6 Elephant order requires the pending order-state producer")
    return view
