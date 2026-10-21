"""Recovered BOR, DBM and FlowPick rules used by the Stage 5 shadow seam.

This module intentionally mirrors the recovered SQL, including its ordering,
rounding and suspension semantics.  It is not a redesigned planning model.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, localcontext


ZERO = Decimal("0")


def d(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, str, Decimal)):
        raise ValueError("Exact integer/decimal input required")
    result = Decimal(value)
    if not result.is_finite() or result < 0:
        raise ValueError("Non-negative finite value required")
    return result


def d_signed(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, str, Decimal)):
        raise ValueError("Exact integer/decimal input required")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Finite signed value required")
    return result


def ceil(value: Decimal) -> Decimal:
    return value.to_integral_value(rounding=ROUND_CEILING)


def text(value: Decimal) -> str:
    return format(value, "f")


def calculate_bor(case: dict, *, allow_negative_stock_for_requirement=False) -> list[dict]:
    rows = []
    for item in case["items"]:
        norm, virtual = d(item["norm"]), d(item["virtual_norm"])
        sob, moq = d(item["sob"]), d(item["moq"])
        requirement = d(item["requirement"])
        original = ceil(requirement * sob / 100)
        if original == 0:
            continue
        dispatch = original
        requirement_stock = (d_signed(item["stock_for_requirement"]) if allow_negative_stock_for_requirement
                             else d(item["stock_for_requirement"]))
        vn_req = max(ZERO, ceil((virtual - requirement_stock - d(item["git"])) * sob / 100))
        colour = item["dispatch_color"].upper()
        if dispatch < moq and (colour in {"BLACK", "RED", "YELLOW"} or norm == 0):
            dispatch = moq
        if dispatch < moq:
            dispatch = ZERO
        if dispatch == 0:
            continue
        supplier_norm = ceil(sob * virtual / 100)
        red_band = ceil(supplier_norm / 3)
        yellow_band = ceil(supplier_norm * 2 / 3) - red_band
        green_band = supplier_norm - yellow_band - red_band
        remainder = vn_req
        green = min(remainder, green_band); remainder -= green
        yellow = min(remainder, yellow_band); remainder -= yellow
        red = remainder
        blue = ZERO
        if dispatch > vn_req:
            green += dispatch - vn_req
        if colour == "BLUE":
            blue += green + yellow + red; green = yellow = red = ZERO
        elif colour == "GREEN":
            green += yellow + red; yellow = red = ZERO
        elif colour == "YELLOW":
            yellow += red; red = ZERO
        rows.append({
            "case": item["case"], "sku": item["sku"], "location": item["location"],
            "supplier": item["supplier"], "original_requirement": text(original),
            "dispatch_requirement": text(dispatch), "to_red": text(red),
            "to_yellow": text(yellow), "to_green": text(green), "to_blue": text(blue),
        })
    return sorted(rows, key=lambda row: row["case"])


def calculate_bor_oa(case: dict) -> list[dict]:
    rows = []
    for item in case["items"]:
        bands = item["bands"]
        sob, norm = d(item["sob"]), d(item["norm"])
        order_black, order_red = d(bands["order_black"]), d(bands["order_red"])
        order_yellow, order_green, order_blue = (d(bands[k]) for k in ("order_yellow", "order_green", "order_blue"))
        norm_black, norm_red = d(bands["norm_black"]), d(bands["norm_red"])
        norm_yellow, norm_green = d(bands["norm_yellow"]), d(bands["norm_green"])
        total = order_black + order_red + order_yellow + order_green + order_blue + norm_black + norm_red + norm_yellow + norm_green
        original = ceil(total * sob / 100)
        colour = ("BLACK" if order_black + norm_black > 0 else "RED" if order_red + norm_red > 0
                  else "YELLOW" if order_yellow + norm_yellow > 0 else "GREEN" if order_green + norm_green > 0
                  else "BLUE" if order_blue > 0 else "WHITE")
        # ``CollectBOR_OrderAllocationData.sql`` runs from the BPR opening
        # SOB/MOQ state, before the later importer-fed supplier refresh.  Its
        # own MOQ rule expands a Black/Red/Yellow (or zero-Norm) dispatch to
        # MOQ, then assigns the increment to Blue.  Do not conflate this
        # calculation with the later ``GenSupplierWiseReq.sql`` producer.
        moq = d(item["moq"])
        dispatch = original
        if dispatch > 0 and dispatch < moq and (colour in {"BLACK", "RED", "YELLOW"} or norm == 0):
            dispatch = moq
        if dispatch < moq:
            dispatch = ZERO
        req_tob = ceil((order_black + norm_black) * sob / 100)
        req_tor = ceil((order_red + norm_red) * sob / 100)
        req_toy = ceil((order_yellow + norm_yellow) * sob / 100)
        req_tog = ceil((order_green + norm_green) * sob / 100)
        req_blue = ceil(order_blue * sob / 100)
        out = [req_tob, req_tor, req_toy, req_tog, req_blue] if dispatch > 0 else [ZERO] * 5
        if dispatch > original:
            out[4] += dispatch - original
        def pct(req_name, band_name):
            denominator = d(bands[band_name])
            if denominator == 0:
                return "0.00"
            return format((d(bands[req_name]) * 100 / denominator).quantize(Decimal("0.01")), "f")
        rows.append({
            "case": item["case"], "sku": item["sku"], "location": item["location"], "supplier": item["supplier"],
            "norm": text(norm), "virtual_norm": text(d(item["virtual_norm"])), "stock": text(d(item["stock"])),
            "git": text(d(item["git"])), "requirement": text(original), "dispatch_requirement": text(dispatch),
            "requirement_buckets": {"to_black": text(req_tob), "to_red": text(req_tor), "to_yellow": text(req_toy), "to_green": text(req_tog), "to_blue": text(req_blue)},
            "dispatch_buckets": {"to_black": text(out[0]), "to_red": text(out[1]), "to_yellow": text(out[2]), "to_green": text(out[3]), "to_blue": text(out[4])},
            "dispatch_colour": colour,
            "order_unsatisfied_percent": {"black": pct("order_black", "order_black_band"), "red": pct("order_red", "order_red_band"), "yellow": pct("order_yellow", "order_yellow_band"), "green": pct("order_green", "order_green_band")},
        })
    return sorted(rows, key=lambda row: row["case"])


def calculate_dbm(case: dict) -> list[dict]:
    item = case["items"][0]
    evaluation = date.fromisoformat(case["evaluation_date"])
    timeline = sorted(item["timeline"], key=lambda row: row["date"])
    norm = d(item["norm"])
    red_enabled = not item.get("suspension")
    green_enabled = red_enabled
    resume = date.fromisoformat(item.get("resume_date", item["introduced_on"]))
    rule = item["rule"]
    recommendation = None
    reason = None
    rows = [(date.fromisoformat(row["date"]), d(row["stock"]), d(row.get("consumption", 0)), d(row.get("blue_zone", 0))) for row in timeline]
    if rule == "stockout_today" and red_enabled:
        today = [row for row in rows if row[0] == evaluation]
        if today and today[-1][1] == 0:
            recommendation, reason = ceil(norm * Decimal(4) / 3), 1
    elif rule == "red_persistence" and red_enabled:
        rcp = item["rcp"]
        start = evaluation - timedelta(days=rcp - 1)
        window = [row for row in rows if max(start, resume) <= row[0] <= evaluation]
        if sum(row[1] <= norm / 3 for row in window) == rcp:
            recommendation, reason = ceil(norm * Decimal(4) / 3), 4
    elif rule == "green_persistence" and green_enabled:
        gcp = item["gcp"]
        start = evaluation - timedelta(days=2 * gcp)
        window = [row for row in rows if row[0] > start and row[0] >= resume]
        recent_non_green = start
        for row in window:
            if not (row[1] > norm * 2 / 3 and row[1] <= norm + row[3]):
                recent_non_green = max(recent_non_green, row[0])
        if sum(row[0] > recent_non_green for row in window) >= gcp:
            recommendation, reason = ceil(norm * Decimal(2) / 3), 5
    elif rule == "norm0" and red_enabled:
        ocp_start = evaluation - timedelta(days=item["ocp"])
        window = [row for row in rows if row[0] >= max(ocp_start, resume)]
        orders = [o for o in item.get("orders", []) if date.fromisoformat(o["date"]) >= max(ocp_start, resume)]
        if window and len(orders) >= item["min_order_count"]:
            consumption = sum((row[2] for row in window), ZERO)
            if consumption > window[0][1] and len(orders):
                recommendation, reason = ceil(consumption / len(orders)), 7
    elif rule == "norm1" and red_enabled:
        start = evaluation - timedelta(days=4 * item["rlt"])
        count = sum(row[2] > 0 for row in rows if row[0] >= max(start, resume))
        if count >= 2:
            recommendation, reason = Decimal(2), 10
    elif rule == "norm2" and green_enabled:
        period = 4 * item["rlt"]
        start = evaluation - timedelta(days=period)
        window = [row for row in rows if row[0] >= max(start, resume)]
        sales = sum(row[2] > 0 for row in window)
        stockouts = sum(row[1] == 0 for row in window)
        if sales < 1 and stockouts == 0 and len(window) >= period * Decimal("0.75"):
            recommendation, reason = Decimal(1), 11
    return [{
        "case": item["case"], "sku": item["sku"], "location": item["location"],
        "evaluation_date": case["evaluation_date"], "old_norm": text(norm),
        "recommendation": None if recommendation is None else text(recommendation),
        "rule_type": reason, "suspended": bool(item.get("suspension")),
    }]


def calculate_pick_list(case: dict) -> list[dict]:
    return _calculate_pick_list(case)


def calculate_pick_list_state(case: dict, *, allow_priority_ties=False) -> dict:
    """Capture native truck fields from the existing allocation calculation.

    This additive seam requires qualified native join occurrences.
    Priority ties require explicit
    opt-in under the bounded canonical-order witness qualification; opting in
    retains the existing input-order choice and adds no business tie-break. It is
    not the native-table input adapter. Missing-volume queues use the approved
    weight-only policy. Other ambiguous updates/nontermination still fail.
    """
    result = calculate_pick_cases_state([case], allow_priority_ties=allow_priority_ties)
    for row in result['allocations']:
        row.pop('vehicle')
    return result


def calculate_pick_cases_state(cases, *, allow_priority_ties=False):
    """One canonical global truck loop across all parent/vehicle queues."""
    state = {'LogisticPickList': [], 'PickListDataForTruckFormation': [],
             '_allow_priority_ties': allow_priority_ties}
    allocations = _calculate_native_pick_cases(cases, state)
    multiplicities = {}
    for case in cases:
        for item in case['items']:
            key = item['sku'].rstrip(' ').upper()
            value = item.get('_join_multiplicity', 1)
            if key in multiplicities and multiplicities[key] != value:
                raise ValueError('Inconsistent native SKU join multiplicity')
            multiplicities[key] = value
    groups = {}
    for row in state['LogisticPickList']:
        groups.setdefault((*_native_partition(row['ParentWHCode'], row['LogisticLocation']), row['TruckCount'], row['VehicleName'].rstrip(' ').upper()), []).append(row)
    # Native division of the SUM(decimal(13,3)) values yields decimal(38,6).
    with localcontext() as context:
        context.prec = 80
        for rows in groups.values():
            if any(row['TransportLoadType'] == 'WEIGHT_ONLY' for row in rows):
                # Missing volume is never converted to zero or a density guess.
                # Persist the qualification in the existing typed text column.
                for row in rows:
                    row['TransportLoadType'] = 'WEIGHT_ONLY'
                continue
            weight = _pick_sum(None if row['TotalWeight'] is None else row['TotalWeight'] *
                              multiplicities[row['SKUCode'].rstrip(' ').upper()] for row in rows)
            volume = _pick_sum(None if row['TotalVolume'] is None else row['TotalVolume'] *
                              multiplicities[row['SKUCode'].rstrip(' ').upper()] for row in rows)
            ratio = None if weight is None or volume is None else (weight / volume).quantize(
                Decimal('.000001'), rounding=ROUND_HALF_UP)
            for row in rows:
                row['TransportLoadType'] = 'MXL' if ratio is not None and ratio >= Decimal('4.5') else 'SXL'
    state.pop('_allow_priority_ties')
    order_native_pick_state(state)
    return dict(allocations=allocations, **state)


def _native_partition(parent, location):
    from mta.domain.complete_daily_scalars import identifier_sort_key
    return identifier_sort_key(parent), identifier_sort_key(location)


def order_native_pick_state(state):
    """Retain the canonical round's prefix INSERT then boundary INSERT order.

    These are existing SQL ORDER BY columns, never a SKU business tie-break.
    Queue rank choices have already been made before this storage projection.
    """
    state['LogisticPickList'].sort(key=lambda row: (row['TruckCount'], row['IsTruckFormed'] is True,
        *_native_partition(row['ParentWHCode'], row['LogisticLocation']), row['NewSRNo']))
    state['PickListDataForTruckFormation'].sort(key=lambda row: (
        *_native_partition(row['ParentWHCode'], row['LogisticLocation']), row['NewSRNo']))


def _native_decimal(value):
    if value is None:
        return None
    rounded = d_signed(value).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
    if abs(rounded) >= Decimal('10000000000'):
        raise ValueError('Native Pick decimal(13,3) overflow')
    return rounded


def _pick_product(quantity, dimension):
    return None if dimension is None else quantity * d(dimension)


def _pick_sum(values):
    present = [value for value in values if value is not None]
    return sum(present, ZERO) if present else None


def _pick_compare(value, other, *, greater=False):
    return value is not None and (value > other if greater else value >= other)


def _native_queue(flattened, vehicle, *, allow_priority_ties=False):
    priorities = set()
    for number, row in enumerate(flattened, 1):
        if row['priority'] in priorities and not allow_priority_ties:
            raise ValueError('Native Pick priority-rank tie requires source-order qualification')
        priorities.add(row['priority'])
        if row['weight'] is None and row['volume'] is None:
            raise ValueError('Both-NULL native Pick dimensions must be excluded by the source join')
        for field in ('weight', 'volume'):
            if row[field] is None:
                continue
            value = d(row[field])
            if value < 0 or _native_decimal(value) != value:
                raise ValueError('Native Pick state requires qualified positive scale3 dimensions')
        if row['quantity'] != int(row['quantity']) or not 0 < row['quantity'] < 2**31:
            raise ValueError('Native Pick quantity must be a positive SQL int')
        for field in ('sku', 'from_location', 'to_location', 'logistics_location', 'dispatch_color'):
            value = row[field]
            if value is None and field == 'dispatch_color':
                continue
            if not isinstance(value, str):
                raise ValueError('Native Pick text metadata required: ' + field)
            if len(value.encode('utf-16-le')) // 2 > (20 if field == 'dispatch_color' else 50):
                raise ValueError('Native Pick text exceeds column size: ' + field)
        row['_native_sr_no'] = number
    if not isinstance(vehicle['name'], str) or len(vehicle['name'].encode('utf-16-le')) // 2 > 50:
        raise ValueError('Native vehicle name required')
    for field in ('weight_capacity', 'volume_capacity'):
        value = d(vehicle[field])
        if value <= 0 or _native_decimal(value) != value:
            raise ValueError('Native Pick state requires qualified positive scale3 capacities')


def _native_pick_identity(row, vehicle):
    return dict(NewSRNo=row['_native_sr_no'], SKUCode=row['sku'], WHCode=row['to_location'],
        ParentWHCode=row['from_location'], VehicleWeightCapacity=_native_decimal(vehicle['weight_capacity']),
        VehicleVolumeCapacity=_native_decimal(vehicle['volume_capacity']),
        DispatchColor=row['dispatch_color'], VehicleName=vehicle['name'], Priority=row['priority'],
        LogisticLocation=row['logistics_location'])


def _pick_text_key(value):
    if not isinstance(value, str) or not value.isascii():
        raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ASCII SQL text equality')
    return value.rstrip(' ').upper()


def _append_multimap(index, key, row):
    index.setdefault(key, []).append(row)


def _calculate_native_pick_cases(cases, state):
    """Literal staged-loop semantics; source joins have one qualified SKU row.

    NoTruckFlag is sticky and its UPDATE is set-based. All partitions advance
    together, including a flagged partition while another partition keeps the
    canonical global loop alive. Ambiguous UPDATE values are not invented.
    """
    queues = {}
    buckets = ('to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue')
    for case in cases:
        for item_index, item in enumerate(case['items']):
            for priority, bucket in enumerate(buckets, 1):
                quantity = d(item['buckets'].get(bucket, 0))
                if quantity <= 0:
                    continue
                key = _native_partition(item['from_location'], item['logistics_location'])
                queues.setdefault(key, []).append(dict(item, quantity=quantity, priority=priority,
                    item_index=item_index, _vehicle=case['vehicle'],
                    _vehicles=case.get('vehicles', [case['vehicle']]), _no_truck_flag=False))
    rows = []
    for key in sorted(queues):
        queue = queues[key]
        queue.sort(key=lambda row: row['priority'])  # stable permitted tie order
        weight_only = any(row['volume'] is None for row in queue)
        if weight_only and any(row['weight'] is None or d(row['weight']) <= 0 for row in queue):
            raise ValueError('Weight-only Pick requires known positive weight for every queue item')
        for row in queue:
            row['_weight_only'] = weight_only
        vehicle = queue[0]['_vehicle']
        _native_queue(queue, vehicle, allow_priority_ties=state['_allow_priority_ties'])
        # Canonical ROW_NUMBER precedes the vehicle join: all vehicle
        # occurrences derived from one ranked row share that rank.
        for row in queue:
            for configured in row['_vehicles']:
                _native_queue([dict(row)], configured, allow_priority_ties=True)
                expanded = dict(row, _vehicle=configured)
                expanded.update(_partition_key=_native_partition(row['from_location'], row['logistics_location']),
                    _vehicle_key=_pick_text_key(configured['name']), _sku_key=_pick_text_key(row['sku']),
                    _to_key=_pick_text_key(row['to_location']), _from_key=_pick_text_key(row['from_location']))
                rows.append(expanded)
    originals = {(*r['_partition_key'], r['_native_sr_no'], r['_vehicle_key']): dict(r)
                 for r in rows}
    expanded_rows = len(rows)
    truck = 0
    while rows:
        before_state = [(id(r), r['quantity'], r['_no_truck_flag']) for r in rows]
        truck += 1
        groups, snapshots, snapshots_by_group = {}, [], {}
        for row in rows:
            groups.setdefault((*row['_partition_key'], row['_vehicle_key']), []).append(row)
        for group in groups.values():
            cw = cv = None
            ranks = {}
            for row in group:
                ranks.setdefault(row['_native_sr_no'], []).append(row)
            for peers in ranks.values():
                cw = _pick_sum([cw] + [_pick_product(r['quantity']*r.get('_join_multiplicity',1),r['weight']) for r in peers])
                cv = (None if group[0]['_weight_only'] else
                      _pick_sum([cv] + [_pick_product(r['quantity']*r.get('_join_multiplicity',1),r['volume']) for r in peers]))
                for row in peers:
                    snapshot = dict(row, cw=cw, cv=cv)
                    snapshots.append(snapshot)
                    group_key = (*snapshot['_partition_key'], snapshot['_vehicle_key'])
                    _append_multimap(snapshots_by_group, group_key, snapshot)
        flag_snapshots = {}
        for snapshot in snapshots:
            key = (snapshot['_vehicle_key'], snapshot['_sku_key'], snapshot['priority'],
                   *snapshot['_partition_key'])
            _append_multimap(flag_snapshots, key, snapshot)
        # Native join omits WHCode/NewSRNo: preserve cross-occurrence flags.
        for row in rows:
            key = (row['_vehicle_key'], row['_sku_key'], row['priority'], *row['_partition_key'])
            for snap in flag_snapshots.get(key, ()):
                vehicle = snap['_vehicle']
                if (snap['cw'] is not None and snap['cw'] < d(vehicle['weight_capacity']) and
                        (snap['_weight_only'] or
                         (snap['cv'] is not None and snap['cv'] < d(vehicle['volume_capacity'])))):
                    row['_no_truck_flag'] = True
        start = len(state['LogisticPickList'])
        for key, group in groups.items():
            current = snapshots_by_group.get(key, ())
            crossing = [s['_native_sr_no'] for s in current
                        if _pick_compare(s['cw'],d(s['_vehicle']['weight_capacity']))
                        or _pick_compare(s['cv'],d(s['_vehicle']['volume_capacity']))]
            if not crossing:
                continue
            minimum = min(crossing)
            distinct = []
            for row in current:
                if row['_native_sr_no'] > minimum:
                    continue
                boundary = row['_native_sr_no']==minimum
                vehicle = row['_vehicle']
                weight_cap, volume_cap = d(vehicle['weight_capacity']), d(vehicle['volume_capacity'])
                allocation = row['quantity']
                if boundary:
                    over_w = _pick_compare(row['cw'],weight_cap,greater=True)
                    over_v = _pick_compare(row['cv'],volume_cap,greater=True)
                    within_w = row['cw'] is not None and row['cw'] <= weight_cap
                    within_v = row['cv'] is not None and row['cv'] <= volume_cap
                    tw, tv = _pick_product(row['quantity'],row['weight']), _pick_product(row['quantity'],row['volume'])
                    tw = None if tw is None else tw-(row['cw']-weight_cap) if over_w else tw
                    tv = None if tv is None else tv-(row['cv']-volume_cap) if over_v else tv
                    if row['_weight_only'] and over_w:
                        # Cumulative rows retain the native second attribute
                        # join's multiplicity. Use that same effective weight
                        # at the boundary, never a negative residual allocation.
                        unit_weight = d(row['weight']) * row.get('_join_multiplicity', 1)
                        before_weight = row['cw'] - row['quantity'] * unit_weight
                        allocation = max(ZERO, min(row['quantity'],
                            (weight_cap - before_weight) / unit_weight))
                    elif over_w and over_v:
                        allocation = min(tw/d(row['weight']),tv/d(row['volume']))
                    elif over_w and within_v:
                        allocation = tw/d(row['weight'])
                    elif over_v and within_w:
                        allocation = tv/d(row['volume'])
                allocation = Decimal(int(allocation))
                native = _native_pick_identity(row,vehicle)
                native.update(MinSRNo=minimum,TotalWeight=_native_decimal(_pick_product(allocation,row['weight'])),
                    TotalVolume=_native_decimal(_pick_product(allocation,row['volume'])),
                    CumulativeWeight=_native_decimal(row['cw']),CumulativeVolume=_native_decimal(row['cv']),
                    IsTruckFormed=True if boundary else None,TruckCount=truck,
                    RemainingWeigt=_native_decimal(row['cw']-weight_cap) if boundary and row['cw'] is not None else None,
                    RemainingVolume=_native_decimal(row['cv']-volume_cap) if boundary and row['cv'] is not None else None,
                    TransportLoadType='WEIGHT_ONLY' if row['_weight_only'] else None,
                    ColorWiseAlloction=int(allocation))
                # Both native INSERTs SELECT DISTINCT the full projection.
                if native not in distinct:
                    distinct.append(native)
            state['LogisticPickList'].extend(distinct)
        formed = state['LogisticPickList'][start:]
        # Canonical residual UPDATE omits SKU/logistics from B/C join keys.
        residual_snapshots, residual_formed = {}, {}
        for snapshot in snapshots:
            key = (snapshot['_vehicle_key'], snapshot['_to_key'], snapshot['_from_key'],
                   snapshot['_native_sr_no'])
            _append_multimap(residual_snapshots, key, snapshot)
        for picked in formed:
            key = (_pick_text_key(picked['VehicleName']), _pick_text_key(picked['WHCode']),
                   _pick_text_key(picked['ParentWHCode']), picked['NewSRNo'])
            if picked['NewSRNo'] == picked['MinSRNo']:
                _append_multimap(residual_formed, key, picked)
        changes = []
        for row in rows:
            candidates = []
            key = (row['_vehicle_key'], row['_to_key'], row['_from_key'], row['_native_sr_no'])
            for snap in residual_snapshots.get(key, ()):
                for picked in residual_formed.get(key, ()):
                    cap = snap['_vehicle']
                    candidates.append(row['quantity']-picked['ColorWiseAlloction'] if
                        _pick_compare(snap['cw'],d(cap['weight_capacity'])) or
                        _pick_compare(snap['cv'],d(cap['volume_capacity'])) else snap['quantity'])
            if candidates and any(value != candidates[0] for value in candidates):
                raise ValueError('Canonical Pick residual UPDATE has differing candidate values; '
                                 f"target={(row['sku'],row['to_location'],row['from_location'],row['_native_sr_no'])!r}, "
                                 f"candidates={sorted(set(candidates))!r}; rank qualification does not cover it")
            changes.append(candidates[0] if candidates else row['quantity'])
        for row, quantity in zip(rows, changes):
            row['quantity'] = quantity
        formed_by_row = {}
        for picked in state['LogisticPickList']:
            key = (_pick_text_key(picked['VehicleName']), _pick_text_key(picked['SKUCode']),
                   _pick_text_key(picked['WHCode']), _pick_text_key(picked['ParentWHCode']),
                   picked['Priority'])
            _append_multimap(formed_by_row, key, picked)
        kept = []
        for row in rows:
            key = (row['_vehicle_key'], row['_sku_key'], row['_to_key'], row['_from_key'], row['priority'])
            matches = formed_by_row.get(key, ())
            if any(row['_native_sr_no'] < r['MinSRNo'] or
                   (row['_native_sr_no']==r['MinSRNo'] and row['quantity']==0) for r in matches):
                continue
            kept.append(row)
        rows = kept
        if not any(not row['_no_truck_flag'] for row in rows):
            break
        if before_state == [(id(r),r['quantity'],r['_no_truck_flag']) for r in rows]:
            raise ValueError('Canonical Pick nontermination: zero progress or NULL underfilled queue')
    picks = []
    for native in state['LogisticPickList']:
        row = originals[(*_native_partition(native['ParentWHCode'],native['LogisticLocation']),native['NewSRNo'], native['VehicleName'].rstrip(' ').upper())]
        if native['ColorWiseAlloction'] > 0:
            picks.append({**_pick_row(row,native['TruckCount'],Decimal(native['ColorWiseAlloction']),native=True),
                          'vehicle':native['VehicleName']})
    for row in rows:
        native = _native_pick_identity(row,row['_vehicle'])
        native.update(TotalWeight=_native_decimal(_pick_product(row['quantity'],row['weight'])),
            TotalVolume=_native_decimal(_pick_product(row['quantity'],row['volume'])),
            RemainingWeight=Decimal('0.000'),
            RemainingVolume=None if row['_weight_only'] else Decimal('0.000'),
            ColorWiseAlloction=int(row['quantity']),NoTruckFlag=row['_no_truck_flag'])
        state['PickListDataForTruckFormation'].append(native)
        picks.append({**_pick_row(row,None,ZERO,remaining=row['quantity'],native=True), 'vehicle':row['_vehicle']['name']})
    from mta.application.stage_observation import summary
    summary('Pick', partitions=len(queues), expanded_rows=expanded_rows,
            iterations=truck, allocations=len(state['LogisticPickList']), residual_rows=len(rows))
    return sorted(picks,key=lambda row:(row['truck'] is None,row['truck'] or 999999,row['priority'],row['case'],row['remaining_quantity']))


def _calculate_pick_list(case: dict) -> list[dict]:
    vehicle = case["vehicle"]
    weight_cap, volume_cap = d(vehicle["weight_capacity"]), d(vehicle["volume_capacity"])
    grouped: dict[tuple[str, str], list[dict]] = {}
    bucket_priority = (("to_black", 1), ("to_red", 2), ("to_yellow", 3), ("to_green", 4), ("to_blue", 5))
    for item_index, item in enumerate(case["items"]):
        for bucket, priority in bucket_priority:
            qty = d(item["buckets"].get(bucket, 0))
            if qty > 0:
                # ``GenerateLogisticPickList.sql`` builds cumulative capacity
                # windows by ParentWHCode + LogisticsLocation.  A queue at a
                # different logistics location must never fill this queue's
                # vehicle, even when both use the same parent and vehicle.
                grouped.setdefault((item["from_location"], item["logistics_location"]), []).append(
                    {**item, "quantity": qty, "priority": priority, "item_index": item_index}
                )
    picks = []
    for group in grouped.values():
        picks.extend(_calculate_pick_group(group, weight_cap, volume_cap))
    return sorted(picks, key=lambda row: (row["truck"] is None, row["truck"] or 999999, row["priority"], row["case"], row["remaining_quantity"]))


def _calculate_pick_group(flattened: list[dict], weight_cap: Decimal, volume_cap: Decimal) -> list[dict]:
    """Form vehicles for one legacy ParentWHCode/LogisticsLocation queue."""
    flattened.sort(key=lambda row: (row["priority"], row["item_index"]))
    remaining = [dict(row) for row in flattened]
    picks, truck = [], 0
    while remaining:
        cumulative_weight = cumulative_volume = ZERO
        boundary = None
        for index, row in enumerate(remaining):
            cumulative_weight += row["quantity"] * d(row["weight"])
            cumulative_volume += row["quantity"] * d(row["volume"])
            if cumulative_weight >= weight_cap or cumulative_volume >= volume_cap:
                boundary = index
                break
        if boundary is None:
            break
        truck += 1
        before = remaining[:boundary]
        for row in before:
            picks.append(_pick_row(row, truck, row["quantity"]))
        row = remaining[boundary]
        weight_before = sum((x["quantity"] * d(x["weight"]) for x in before), ZERO)
        volume_before = sum((x["quantity"] * d(x["volume"]) for x in before), ZERO)
        available_by_weight = (weight_cap - weight_before) / d(row["weight"]) if d(row["weight"]) else row["quantity"]
        available_by_volume = (volume_cap - volume_before) / d(row["volume"]) if d(row["volume"]) else row["quantity"]
        allocation = min(row["quantity"], available_by_weight, available_by_volume)
        # ColorWiseAlloction is an int in the recovered table: assignment truncates.
        allocation = max(ZERO, Decimal(int(allocation)))
        if allocation > 0:
            picks.append(_pick_row(row, truck, allocation))
        residual = row["quantity"] - allocation
        remaining = remaining[boundary + 1:]
        if residual > 0:
            remaining.insert(0, {**row, "quantity": residual})
    for row in remaining:
        picks.append(_pick_row(row, None, ZERO, remaining=row["quantity"]))
    return picks


def _pick_row(row, truck, quantity, remaining=ZERO, *, native=False):
    total_weight = _pick_product(quantity,row['weight']) if native else quantity * d(row["weight"])
    total_volume = _pick_product(quantity,row['volume']) if native else quantity * d(row["volume"])
    return {
        "case": row["case"], "sku": row["sku"], "from_location": row["from_location"],
        "to_location": row["to_location"], "logistics_location": row["logistics_location"],
        "truck": truck, "priority": row["priority"], "picked_quantity": text(quantity),
        "remaining_quantity": text(remaining),
        "total_weight": "0" if quantity == 0 else None if total_weight is None else format(total_weight.quantize(Decimal("0.001")), "f"),
        "total_volume": "0" if quantity == 0 else None if total_volume is None else format(total_volume.quantize(Decimal("0.001")), "f"),
    }


def execute_capability(case: dict) -> list[dict]:
    capability = case["capability"]
    if capability == "bor":
        return calculate_bor(case)
    if capability == "bor_oa":
        return calculate_bor_oa(case)
    if capability == "dbm":
        return calculate_dbm(case)
    if capability == "pick_list":
        return calculate_pick_list(case)
    raise ValueError("Unsupported remaining capability")
