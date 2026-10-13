"""R1 master-state transition; separate from raw-file/master validation.

The v5 synthetic entry supplies processed Importer facts and prior DBM state.
Neither source is replaced with current-day additional-master/calculation rows.
Optional forced-Norm ingestion emits its own trigger delta before downstream
calculation. Other ordered control producers remain explicit integration work.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation


MASTER_SCHEMA = "r1-current-day-input-v5"
MASTER_FIELDS = ("sku_code", "location_code", "norm", "min_norm", "rlt", "rcp", "gcp",
                 "ocp", "min_order_count", "parent_location_code", "sku_intro_date")
MASTER_NUMERIC = ("norm", "min_norm", "rlt", "rcp", "gcp", "ocp", "min_order_count")
OPTIONAL_IMPORTER_FIELDS = ("elephant_order_capping",)
REFRESH_FIELDS = ("min_norm", "rlt", "rcp", "gcp", "ocp", "min_order_count", "parent_location_code")


def _date(value):
    if not isinstance(value, str):
        raise ValueError("R1 master dates must be ISO date strings")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("R1 master dates must be YYYY-MM-DD")
    return parsed


def _master_rows(rows, *, importer=False):
    if not isinstance(rows, list):
        raise ValueError("R1 master rows must be lists")
    result = {}
    for row in rows:
        allowed = set(MASTER_FIELDS) | ({"pack_size"} if importer else set())
        if importer:
            allowed |= set(OPTIONAL_IMPORTER_FIELDS)
        if not isinstance(row, dict) or not set(MASTER_FIELDS).issubset(row) or set(row) - allowed or (importer and "pack_size" not in row):
            raise ValueError("Invalid R1 source master fields")
        key = (row["sku_code"], row["location_code"])
        if any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in key) or key in result:
            raise ValueError("R1 master grain must be unique nonblank SKU/location")
        for field in (*MASTER_NUMERIC, *(("pack_size",) if importer else ()),
                      *(("elephant_order_capping",) if importer and "elephant_order_capping" in row else ())):
            value = row[field]
            if value is None and field in {"ocp", "min_order_count", "elephant_order_capping"}:
                continue
            try:
                numeric = Decimal(str(value))
            except (InvalidOperation, ValueError):
                raise ValueError(f"Invalid R1 master {field}") from None
            if (isinstance(value, bool) or not numeric.is_finite() or numeric != numeric.to_integral_value()
                    or not (0 <= numeric <= 2147483647) or field == "pack_size" and numeric == 0):
                raise ValueError(f"R1 master {field} must be a nonnegative SQL integer (pack positive)")
        parent = row["parent_location_code"]
        if parent is not None and (not isinstance(parent, str) or not parent.strip() or parent != parent.strip()):
            raise ValueError("Invalid R1 source parent identity")
        if importer and parent is None:
            raise ValueError("R1 v5 requires an explicit importer parent")
        if row["sku_intro_date"] is not None:
            _date(row["sku_intro_date"])
        result[key] = {f: (None if row[f] is None else int(Decimal(str(row[f]))))
                       if f in (*MASTER_NUMERIC, "pack_size", "elephant_order_capping") else row[f] for f in row}
    return result


def validate_master_entry(payload, *, _order_types_reconciled=False):
    state = payload.get("master_state")
    required = {"importer_master", "dbm_opening", "opening_provenance"}
    if not isinstance(state, dict) or not required <= set(state) or set(state) - required - {'force_norm_input','phase_control_input','accepted_norm_input','season_control_input','transit_tag_input','control_diagnostics','phase_out_membership'}:
        raise ValueError("R1 v5 requires separate importer master and prior DBM opening")
    if "force_norm_input" in state:
        validate_force_norm_input(state["force_norm_input"])
    if 'control_diagnostics' in state and (state['control_diagnostics'] is not True or 'phase_control_input' not in state or 'force_norm_input' not in state):
        raise ValueError('Selected diagnostics require explicit phase and force inputs')
    if 'transit_tag_input' in state:
        from mta.application.r1_transit_tags import validate_tag_input
        validate_tag_input(state['transit_tag_input'])
    if 'season_control_input' in state:
        from mta.application.r1_seasonality import validate_season_input
        validate_season_input(state['season_control_input'], payload['foundation']['snapshot']['business_date'])
        if 'phase_control_input' in state:
            projected = [{f:r[f] for f in ('SKUCode','WhCode','Status')} for r in state['season_control_input']['seasonality']]
            if state['phase_control_input']['seasonality'] != projected:
                raise ValueError('Phase and season opening projections must have the same source owner')
    if 'phase_control_input' in state:
        from mta.application.r1_phase_entry import validate_phase_input
        validate_phase_input(state['phase_control_input'], payload['foundation']['snapshot']['business_date'])
    if 'accepted_norm_input' in state:
        from mta.application.r1_parent_suggestions import validate_accepted_input
        validate_accepted_input(state['accepted_norm_input'], payload['foundation']['snapshot']['business_date'])
    provenance = state["opening_provenance"]
    foundation = payload.get("foundation")
    if not isinstance(foundation, dict) or not isinstance(foundation.get("snapshot"), dict):
        raise ValueError("R1 v5 requires a foundation snapshot")
    snapshot = foundation["snapshot"]
    if (not isinstance(provenance, dict) or set(provenance) != {"kind", "identity", "business_date"}
            or provenance["kind"] != "SYNTHETIC_PRIOR_DBM"
            or not isinstance(provenance["identity"], str) or not provenance["identity"].strip()
            or snapshot.get("source_kind") != "SYNTHETIC_R1"):
        raise ValueError("R1 v5 master opening requires labelled synthetic prior-state provenance")
    if _date(provenance["business_date"]) >= _date(snapshot.get("business_date")):
        raise ValueError("R1 DBM opening must precede the current business date")
    importer = _master_rows(state["importer_master"], importer=True)
    opening = _master_rows(state["dbm_opening"])
    membership = state.get('phase_out_membership', [])
    if (not isinstance(membership, list)
            or any(not isinstance(row, dict) or set(row) != {'SKUCode','WhCode'} for row in membership)):
        raise ValueError('Invalid PhaseOutTbl calculation membership')
    membership_keys = [(row['SKUCode'], row['WhCode']) for row in membership]
    if (len(membership_keys) != len(set(membership_keys))
            or any(key not in importer for key in membership_keys)):
        raise ValueError('PhaseOutTbl calculation membership must be unique within master closure')
    if not importer:
        raise ValueError("R1 v5 empty processed master requires the uncovered entry/abort contract")
    for section in ("policies", "stock_openings"):
        if not isinstance(payload.get(section), list) or any(not isinstance(row, dict) for row in payload[section]):
            raise ValueError(f"R1 v5 {section} must be a list of source rows")
    if any(row.get("controls") for row in payload["policies"]):
        raise ValueError("R1 v5 control events require the ordered pre-BPR producer; no downstream reapplication")
    # Public raw orders must pass the order-state producer. Internally owned
    # orders have already been reconciled, including manual Elephant acceptance;
    # their unchanged quantity must not trigger this raw-entry restriction again.
    for order in (() if _order_types_reconciled else payload.get("orders", [])):
        cap = importer.get((order.get("sku_code"), order.get("location_code")), {}).get("elephant_order_capping")
        if cap is not None and Decimal(str(order.get("outstanding_quantity"))) > cap:
            raise ValueError("R1 v5 Elephant order requires the pending order-state producer")
    # The public v5 contract must not contain the old calculated/mirrored seam.
    if set(payload["foundation"]) != {"snapshot", "skus", "locations", "inventory_positions"}:
        raise ValueError("R1 v5 foundation must not supply calculated master/hierarchy")
    if any("norm" in row for row in payload["stock_openings"]):
        raise ValueError("R1 v5 stock input must not duplicate master Norm")
    for section, rows in (("policies", payload["policies"]), ("stock_openings", payload["stock_openings"]),
                          ("inventory_positions", foundation.get("inventory_positions"))):
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Invalid R1 v5 {section}")
        keys = [(row.get("sku_code"), row.get("location_code")) for row in rows]
        if any(not isinstance(value, str) for key in keys for value in key) or len(keys) != len(set(keys)) or set(keys) != set(importer):
            raise ValueError(f"R1 v5 {section} must have exactly one row per processed master key")
    return importer, opening


def validate_force_norm_input(value):
    """Bounded approved-ingestion contract, not a UI approval workflow.

    No phase/season/suggestion state is inferred from this field. Their nonempty
    integration remains a separate R1-02/04 obligation within the same goal.
    """
    if not isinstance(value, dict) or set(value) != {
            'raw_master', 'requests', 'from_ui', 'ignore_master_norm', 'nms_active'}:
        raise ValueError('Invalid forced-Norm source contract')
    for flag in ('from_ui', 'ignore_master_norm', 'nms_active'):
        if not isinstance(value[flag], bool):
            raise ValueError('Forced-Norm configuration must be explicit booleans')
    for name, fields in (('raw_master', {'SKUCode', 'WhCode', 'Norm', 'MinNorm'}),
                         ('requests', {'SKUCode', 'WhCode', 'NewNorm', 'Approved'})):
        if not isinstance(value[name], list):
            raise ValueError('Forced-Norm source rows must be lists')
        for row in value[name]:
            if not isinstance(row, dict) or set(row) != fields:
                raise ValueError('Invalid forced-Norm source fields')
            for field in ('SKUCode', 'WhCode'):
                if not isinstance(row[field], str) or not row[field].strip() or row[field] != row[field].strip():
                    raise ValueError('Forced-Norm source identity must be nonblank')
            for field in fields - {'SKUCode', 'WhCode'}:
                number = row[field]
                if number is not None and (type(number) is not int or not -2147483648 <= number <= 2147483647):
                    raise ValueError('Forced-Norm source values must be SQL integers or null')
                if field == 'Approved' and number not in (None, 0, 1):
                    raise ValueError('Approval must be 0, 1 or null')


def forced_norm_state(dbm, importer, source):
    """Translate source/master fields without calculating an oracle output."""
    def master(rows):
        return [dict(SKUCode=r['sku_code'], WhCode=r['location_code'], Norm=r['norm'], MinNorm=r['min_norm'])
                for r in rows]
    return dict(dbm_master=master(dbm), importer_master=master(importer),
                raw_master=source['raw_master'], force_requests=source['requests'],
                accepted=[], suggestions=[], reason_codes=[], acceptance=[], phase_out=[],
                phase_in=[], seasonality=[], forced=[], log=[], triggers=[], upload_log=[])


def source_calculation_view(payload, *, _order_types_reconciled=False):
    """Project ONLY inbound source facts for old validation and oracle seeding.

    No DBM reconciliation/Norm-control calculation happens here. The oracle
    loads dbm_opening separately and independently executes pinned SQL.
    """
    importer, _ = validate_master_entry(payload, _order_types_reconciled=_order_types_reconciled)
    view = deepcopy(payload)
    del view["master_state"]
    view["schema"] = "r1-current-day-input-v4"
    foundation = view["foundation"]
    day = foundation["snapshot"]["business_date"]
    foundation.update(sku_locations=[], hierarchy=[], orders=[], norm_controls=[])
    policies = {(r["sku_code"], r["location_code"]): r["policy"] for r in payload["policies"]}
    routes = {}
    for key, row in sorted(importer.items()):
        foundation["sku_locations"].append({"sku_code": key[0], "location_code": key[1],
            "effective_from": day, "effective_to": None, "base_norm": row["norm"],
            "replenishment_lead_time_days": row["rlt"], "pack_size": row["pack_size"]})
        parent = row["parent_location_code"]
        foundation["hierarchy"].append({"sku_code": key[0], "child_location_code": key[1],
            "parent_location_code": parent, "effective_from": day, "effective_to": None})
        policy = policies[key]
        threshold = policy["spike_override"]
        if threshold is None:
            threshold = policy["spike_high"] if row["norm"] >= 3 else policy["spike_low"]
        routes[key] = {"sku_code": key[0], "location_code": key[1], "has_bpr_master": True,
            "norm": row["norm"], "spike_threshold_percent": threshold,
            "parent_location_code": parent, "rlt_to_parent_days": row["rlt"]}
    for key, row in importer.items():
        parent = (key[0], row["parent_location_code"])
        if parent not in importer:
            routes[parent] = {"sku_code": parent[0], "location_code": parent[1], "has_bpr_master": False,
                "norm": None, "spike_threshold_percent": None, "parent_location_code": None, "rlt_to_parent_days": None}
    view["routing"] = [routes[k] for k in sorted(routes)]
    for stock in view["stock_openings"]:
        stock["norm"] = importer[(stock["sku_code"], stock["location_code"])]["norm"]
    return view


def reconcile_master_state(payload, *, _order_types_reconciled=False):
    """01.ImportMasterData: refresh structural fields, retain existing Norm.

    A Norm difference never manufactures a trigger. Only explicitly supplied
    control requests can emit a delta through their canonical producer.
    """
    importer, opening = validate_master_entry(payload, _order_types_reconciled=_order_types_reconciled)
    dbm = {}
    for key, row in importer.items():
        if key in opening:
            dbm[key] = {**opening[key], **{f: row[f] for f in REFRESH_FIELDS}}
        else:
            dbm[key] = {f: row[f] for f in MASTER_FIELDS}
    result = {
        "dbm_master": [dbm[k] for k in sorted(dbm)],
        "importer_master": [{f: importer[k][f] for f in MASTER_FIELDS} for k in sorted(importer)],
        "norm_change_export": [],
        "norm_change_export_remaining": [],
        "bpr_master": [{f: importer[k][f] for f in ("sku_code", "location_code", "norm",
                        "parent_location_code", "sku_intro_date")} for k in sorted(importer)],
    }
    source = payload['master_state'].get('force_norm_input')
    phase = payload['master_state'].get('phase_control_input')
    accepted = payload['master_state'].get('accepted_norm_input')
    season = payload['master_state'].get('season_control_input')
    tags = payload['master_state'].get('transit_tag_input')
    if source is not None or phase is not None or accepted is not None or season is not None or tags is not None:
        from mta.application.r1_norm_updates import import_forced_norms, apply_norm_updates, clear_force_requests
        source = source or dict(raw_master=[], requests=[], from_ui=True, ignore_master_norm=False, nms_active=False)
        flags = {k: source[k] for k in ('from_ui', 'ignore_master_norm', 'nms_active')}
        state = forced_norm_state(result['dbm_master'], result['importer_master'], source)
        if phase is not None:
            from mta.application.r1_phase_entry import attach_phase_sources
            from mta.application.r1_phase_out import collect_phase_out, process_phase_out
            from mta.application.r1_phase_in import collect_phase_in, process_phase_in
            day = payload['foundation']['snapshot']['business_date']
            state = attach_phase_sources(state, phase, payload)
            state = process_phase_out(collect_phase_out(state, day, phase['run_timestamp'], from_ui=phase['from_ui']), day)
            state = process_phase_in(collect_phase_in(state, day, from_ui=phase['from_ui'], start_percent=phase['start_percent']), day)
            if payload['master_state'].get('control_diagnostics'):
                from mta.application.r1_control_diagnostics import phase_exception_rows
                result['phase_diagnostic_state'] = [dict(table='phase_report',rows=phase_exception_rows(state,phase['run_timestamp']))]
        if season is not None:
            from mta.application.r1_seasonality import collect_seasons, process_seasons, apply_seasons
            state.update({name:deepcopy(season[name]) for name in ('seasonality','season_requests')})
            source_master = {(r['sku_code'],r['location_code']):r for r in payload['master_state']['importer_master']}
            for row in state['importer_master']:
                row['RLT'] = source_master[(row['SKUCode'],row['WhCode'])]['rlt']
            day = payload['foundation']['snapshot']['business_date']
            state = apply_seasons(process_seasons(collect_seasons(state, day), day), day)
        state = import_forced_norms(state, **flags)
        if accepted is not None:
            from mta.application.r1_parent_suggestions import ACCEPTED_FIELDS, insert_parent_suggestions
            state.update({name: deepcopy(accepted[name]) for name in ACCEPTED_FIELDS})
            for row in state['dbm_master']:
                row['ParentWhCode'] = dbm[(row['SKUCode'],row['WhCode'])]['parent_location_code']
            state = insert_parent_suggestions(state, payload['foundation']['snapshot']['business_date'])
        state = apply_norm_updates(state, payload['foundation']['snapshot']['business_date'])
        if payload['master_state'].get('control_diagnostics'):
            from mta.application.r1_control_diagnostics import failed_force_rows
            result['force_diagnostic_state'] = [dict(table='force_report',rows=failed_force_rows(state,payload['foundation']['snapshot']['business_date']))]
        state = clear_force_requests(state, **flags)
        if tags is not None:
            from mta.application.r1_transit_tags import update_transit_tags
            result['transit_tag_state'] = update_transit_tags(tags, state['seasonality'], state['phase_out'])
        if season is not None:
            from mta.application.r1_seasonality import seasonal_checkpoint
            result['season_control_state'] = seasonal_checkpoint(state)
        if accepted is not None:
            from mta.application.r1_parent_suggestions import accepted_checkpoint
            result['accepted_control_state'] = accepted_checkpoint(state)
        if phase is not None:
            from mta.application.r1_phase_entry import clear_phase_inputs, phase_checkpoint
            state = clear_phase_inputs(state, day, history_horizon=phase.get('history_horizon'))
            result['phase_control_state'] = phase_checkpoint(state)
        for name in ('dbm_master', 'importer_master'):
            values = {(r['SKUCode'], r['WhCode']): r for r in state[name]}
            for row in result[name]:
                changed = values[(row['sku_code'], row['location_code'])]
                row.update(norm=changed['Norm'], min_norm=changed['MinNorm'])
                if 'SKUIntroDate' in changed:
                    row['sku_intro_date'] = changed['SKUIntroDate']
        result['norm_change_export'] = [dict(sku_code=r['SKUCode'], location_code=r['WhCode'],
            new_norm=r['NewNorm'], reason=r['Reason']) for r in state['export']]
        norms = {(r['sku_code'], r['location_code']): r['norm'] for r in result['importer_master']}
        for row in result['bpr_master']:
            row['norm'] = norms[(row['sku_code'], row['location_code'])]
    return result
