"""Project each engine's generated daily population into its R1 consumers."""
from copy import deepcopy
from itertools import chain

from mta.application.r1_daily_input import STAGES, PRIOR_TABLES, validate_daily_entry
from mta.application.r1_importer_master import _sql_key
from mta.application.r1_supplier_entry import RAW_SUPPLIER_SCHEMA, validate_supplier_run
from mta.row_sequences import history_rows

RAW_DAILY_SCHEMA = "r1-current-day-input-v8"
DAILY_CONSUMPTION_FIELDS = PRIOR_TABLES["DailyConsumption"]


def supplier_input_skeleton(payload):
    """Structural adapter only, shared safely with the independent oracle."""
    view = deepcopy(payload)
    del view["raw_daily_entry"]
    view.update(schema=RAW_SUPPLIER_SCHEMA, vendor_codes=deepcopy(payload["raw_daily_entry"]["vendor_codes"]))
    view["foundation"]["inventory_positions"] = []
    return view


def validate_daily_run(payload):
    if not isinstance(payload, dict) or payload.get("schema") != RAW_DAILY_SCHEMA or "raw_daily_entry" not in payload:
        raise ValueError("Invalid R1 v8 daily entry")
    if "vendor_codes" in payload or set(payload.get("foundation", {})) != {"snapshot", "skus", "locations"}:
        raise ValueError("R1 v8 daily/membership facts have one owner; no supplied inventory projection")
    if any("stock" in r for r in payload.get("stock_openings", [])):
        raise ValueError("R1 v8 stock is generated from raw daily data, not supplied in stock_openings")
    skeleton = supplier_input_skeleton(payload)
    validate_supplier_run(skeleton)
    validate_daily_entry(payload["raw_daily_entry"], payload["raw_master_entry"]["business_date"])


def generated_daily_view(payload, master_validation, daily_stages):
    """No daily calculation here: consume only this engine's generated tables.

    The existing downstream spine requires a unique, nonmissing current-day
    row at every physical master key. Guard other populations explicitly until
    their downstream missing-stock semantics are ported; never fill with zero.
    """
    validate_daily_run(payload)
    if any(s["outcome"] == "SQL_ERROR" for s in daily_stages.values()):
        raise ValueError("R1 daily SQL_ERROR: full-entry failed-state persistence remains unproven")
    day = payload["raw_master_entry"]["business_date"]
    master = master_validation["tables"]["MasterData"]
    processed = daily_stages[STAGES[-1]]["tables"]["DailyDataProcessed"]
    processed_by_key = {}
    for row in processed:
        processed_by_key.setdefault((_sql_key(row["SKUCode"]), _sql_key(row["WhCode"])), []).append(row)
    view = supplier_input_skeleton(payload)
    inventory = []
    stocks = {}
    for row in master:
        key = row["SKUCode"], row["WhCode"]
        matches = [r for r in processed_by_key.get(tuple(_sql_key(v) for v in key),())
                   if r["ReportDate"] == day]
        if len(matches) != 1 or matches[0]["Stock"] is None:
            raise ValueError("R1 daily missing/duplicate current physical stock: downstream integration unproven; no invented default")
        source = matches[0]
        stocks[key] = source["Stock"]
        inventory.append({"sku_code": key[0], "location_code": key[1], "business_date": day,
                          "stock_quantity": source["Stock"], "goods_in_transit_quantity": source["GIT"]})
    view["foundation"]["inventory_positions"] = inventory
    for row in view["stock_openings"]:
        row["stock"] = stocks[(row["sku_code"], row["location_code"])]
    return view


def generated_bpr_daily_state(payload, daily_stages):
    """01.ImportData: retain prior dates, import processed current date only."""
    day = payload["raw_master_entry"]["business_date"]
    previous = payload["raw_daily_entry"]["prior_bpr"]["DailyConsumption"]
    retained = (deepcopy(r) for r in previous if r["ReportDate"] != day)
    def current():
        for row in daily_stages[STAGES[-1]]["tables"]["DailyDataProcessed"]:
            if row["ReportDate"] == day:
                result = {**row, "WHCode": row["WhCode"], "BlueZone": 0}
                del result["WhCode"]
                yield result
    return history_rows(chain(retained,current()),like=previous)


def auxiliary_stock_balances(daily_consumption, physical_balances, attributes, business_date):
    """R1-04 StockCalculation starts from *all* current DailyConsumption rows.

    Prior plants/NoNorm items retained by daily validation are not necessarily
    current BPRMaster nodes. Keep their stock checkpoint without manufacturing
    master/requirement nodes. The selected raw entry owns AdditionalDailyData
    only at physical master keys, so these rows have no absolute/override join.
    Uncovered attribute-bearing or NULL-stock auxiliary cases remain explicit.
    """
    key = lambda sku, loc: (_sql_key(sku), _sql_key(loc))
    physical = {key(r['sku_code'], r['location_code']) for r in physical_balances}
    attr_keys = {key(r['SKUCode'], r['LocCode']) for r in attributes}
    output, seen = [], set()
    for row in daily_consumption:
        if row['ReportDate'] != business_date:
            continue
        identity = key(row['SKUCode'], row['WHCode'])
        if identity in physical:
            continue
        if identity in seen:
            raise ValueError('Duplicate auxiliary daily stock grain requires source-state discrimination')
        seen.add(identity)
        if identity in attr_keys:
            raise ValueError('Auxiliary stock with SKU/location reservation attributes remains unverified')
        stock = row['Stock']
        if stock is None:
            raise ValueError('Auxiliary NULL-stock downstream consumer remains unverified; no invented zero')
        # Canonical initialized ReservedStock=0 survives both percentage UPDATE
        # joins here: neither matching attributes nor a BPR master exists.
        output.append(dict(sku_code=row['SKUCode'], location_code=row['WHCode'],
                           stock_for_requirement=str(stock), stock_for_rationing=str(max(stock, 0)),
                           reserved_stock='0'))
    return tuple(output)


def native_auxiliary_stock_balances(daily_consumption, physical_balances, attributes,
                                   business_date, reservation_type):
    """Owned native daily rows outside BPRMaster, without invented master nodes.

    Native stock overrides/absolute reservations are explicitly configured only
    at physical master keys. Norm-percent reservation cannot join a nonmaster
    row; stock-percent reservation can join the supplied attribute owner.
    """
    from decimal import Decimal
    if type(reservation_type) is not int or reservation_type not in (0, 1, 2):
        raise ValueError('Explicit native stock reservation type required')
    key = lambda sku, loc: (_sql_key(sku), _sql_key(loc))
    physical = {key(r['sku_code'], r['location_code']) for r in physical_balances}
    output, seen = [], {}
    for row in daily_consumption:
        if row['ReportDate'] != business_date:
            continue
        identity = key(row['SKUCode'], row['WHCode'])
        if identity in physical:
            continue
        stock = row['Stock']
        if type(stock) is not int or not -2**31 <= stock < 2**31:
            raise ValueError('Auxiliary stock requires its actual non-NULL signed32 quantity')
        rationing = max(stock, 0)
        reserved = 0
        if reservation_type == 1:
            values = [r['StockPercentForRationing'] for r in attributes
                      if key(r['SKUCode'], r['LocCode']) == identity]
            if values:
                if any(v != values[0] for v in values[1:]):
                    raise ValueError('SOURCE_ORDER_AMBIGUITY: auxiliary stock-percent reservation')
                if values[0] is None:
                    raise ValueError('Auxiliary NULL reservation reaches an unqualified downstream consumer')
                percentage = values[0]
                if type(percentage) is not int or not -2**31 <= percentage < 2**31:
                    raise ValueError('Auxiliary stock percentage requires signed32')
                factor = 100-percentage
                product = rationing*factor
                if not -2**31 <= factor < 2**31 or not -2**31 <= product < 2**31:
                    raise ValueError('Auxiliary reservation signed32 intermediate overflow')
                reserved = int(Decimal(product) / 100)
                if not -2**31 <= reserved < 2**31:
                    raise ValueError('Auxiliary reserved stock signed32 overflow')
        rationing -= reserved
        if not -2**31 <= rationing < 2**31:
            raise ValueError('Auxiliary rationing stock signed32 overflow')
        result = dict(sku_code=row['SKUCode'], location_code=row['WHCode'],
            stock_for_requirement=str(stock), stock_for_rationing=str(rationing), reserved_stock=str(reserved))
        effective = (result['stock_for_requirement'], result['stock_for_rationing'], result['reserved_stock'])
        if identity in seen and seen[identity] != effective:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: duplicate auxiliary stock join')
        seen[identity] = effective
        output.append(result)  # Identical occurrences remain separate stock rows.
    return tuple(output)
