"""Pure production producer for the native ``AllocatedOrders`` table.

The public function consumes the source-shaped table images used by the daily
order-allocation stage.  It deliberately models SQL NULL joins, insertion
multiplicity, the source pack arithmetic (including its integer-division
defect), and the established ``OrderKey`` ordering.  Database reads, runtime
paths, and report publication belong to the caller.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_DOWN

from mta.application.r1_importer_master import _sql_key
from mta.application.stage_observation import summary
from mta.row_sequences import is_record_rows


OUTPUT_FIELDS = (
    "SKUCode", "DestWhCode", "SrcWhCode", "OrderKey", "DueDate",
    "CustomerOrderId", "IsSpike", "Qty", "OrderWiseAllocatedQty", "BPP",
    "OrderColor", "DueDateAtDest", "PackSizeWiseAllocatedQty",
)
INPUT_TABLE_FIELDS = {
    "DailyConsumption": ("SKUCode", "WHCode", "Stock", "GIT", "ReportDate"),
    "Vf_StockCalculation": ("SKUCode", "WHCode", "StockForRationing"),
    "SpikeOrderData": ("SKUCode", "WhCode", "OrderKey", "DueDate", "Qty",
                       "CustomerOrderId", "IsSpike", "CustomerExpectedDate"),
    "SpikeOrderRouteOriginal": ("OrderKey", "DestWhCode", "SrcWhCode", "DueDate"),
    "SpikeOrderRouteDaily": ("OrderKey", "DestWhCode", "SrcWhCode", "DueDate", "Qty", "Type"),
    "RequirementInColorBand": ("SKUCode", "WhCode", "ParentWhCode", "Norm", "RelCNR",
                               "RelPSO", "OrderBlackBand", "ResidualChildrenSnP"),
    "OrderRequirementColor": ("SKUCode", "DestWhCode", "SrcWhCode", "OrderKey",
                              "DueDate", "BPP", "OrderColor"),
    "DBMMaster": ("SKUCode", "WHCode", "Norm", "RLT"),
    "SkuLocAttributeData": ("SKUCode", "LocCode", "PackSize"),
}
INT_FIELDS = {
    "Stock", "GIT", "StockForRationing", "OrderKey", "Qty", "IsSpike", "Norm",
    "RelCNR", "RelPSO", "OrderBlackBand", "ResidualChildrenSnP", "RLT", "PackSize",
}


def _k(*values):
    if any(value is None for value in values):
        return None
    return tuple(_sql_key(value) for value in values)


def _same(left, right):
    key = _k(left, right)
    return key is not None and key[0] == key[1]


def _as_date(value, owner, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError(f"{owner} must be a native date")


def _integer(value, owner, nullable=False):
    if value is None and nullable:
        return None
    if type(value) is not int or not -(2 ** 31) <= value <= 2 ** 31 - 1:
        raise ValueError(f"{owner} must be a native SQL int")
    return value


def _validate(rows, table):
    if not (is_record_rows(rows) or isinstance(rows, tuple)):
        raise ValueError(f"{table} must be an ordered row table")
    fields = INPUT_TABLE_FIELDS[table]
    for ordinal, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{table}[{ordinal}] must be a row")
        missing = [field for field in fields if field not in row]
        if missing:
            raise ValueError(f"{table}[{ordinal}] lacks canonical fields: {missing}")
        for field in fields:
            value = row[field]
            if field == "IsSpike":
                if value not in (0, 1) or not isinstance(value, (bool, int)):
                    raise ValueError(f"{table}.IsSpike must be a native SQL bit")
            elif field in INT_FIELDS:
                _integer(value, f"{table}.{field}", nullable=field not in
                         {"OrderKey", "Qty", "IsSpike"})
            elif field in {"DueDate", "CustomerExpectedDate", "ReportDate"}:
                _as_date(value, f"{table}.{field}", nullable=field in
                         {"CustomerExpectedDate", "DueDate"} and table == "SpikeOrderData")
            elif field == "BPP":
                if value is not None:
                    number = Decimal(str(value))
                    if (not number.is_finite() or number.as_tuple().exponent < -2
                            or not Decimal("-99999999.99") <= number <= Decimal("99999999.99")):
                        raise ValueError(f"{table}.BPP exceeds native decimal(10,2)")
            elif field == "Type":
                if not isinstance(value, str):
                    raise ValueError(f"{table}.Type must be native non-null text")
            elif value is not None and not isinstance(value, str):
                raise ValueError(f"{table}.{field} must be native text or NULL")
        if table in {"SpikeOrderRouteOriginal", "SpikeOrderRouteDaily"} and row["SrcWhCode"] is None:
            raise ValueError(f"{table}.SrcWhCode is NOT NULL")


def _matches(rows, fields, values):
    wanted = _k(*values)
    return [] if wanted is None else [row for row in rows if _k(*(row[f] for f in fields)) == wanted]


def _winner(values, owner):
    """Return an UPDATE winner only when all possible SQL winners agree."""
    if not values:
        return None
    first = values[0]
    if any(value != first for value in values[1:]):
        raise ValueError(f"{owner} has undefined differing UPDATE winners")
    return first


def _positive(value):
    return value is not None and value > 0


def _sql_sort_date(value):
    # SQL Server ASC places NULL first. Dates used as DueDate are non-null.
    return (value is not None, date.min if value is None else _as_date(value, "sort date"))


def _ceil_div_decimal(left, right):
    if right == 0:
        raise ValueError("PackSize causes native divide by zero")
    return int((Decimal(left) / Decimal(right)).to_integral_value(rounding=ROUND_CEILING))


def _floor_decimal(left, right):
    if right == 0:
        raise ValueError("PackSize causes native divide by zero")
    return int((Decimal(left) / Decimal(right)).to_integral_value(rounding=ROUND_FLOOR))


def _int_div(left, right):
    if right == 0:
        raise ValueError("PackSize causes native divide by zero")
    return int((Decimal(left) / Decimal(right)).to_integral_value(rounding=ROUND_DOWN))


def _rank(rows, partition, ordering, field):
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[name] for name in partition), []).append(row)
    for members in groups.values():
        members.sort(key=ordering)
        for number, row in enumerate(members, 1):
            row[field] = number


def _available(rows, stock_field="AvailableStock", quantity_field="RemainingQty"):
    groups = {}
    for row in rows:
        groups.setdefault(_k(row["SKUCode"], row["SrcWhCode"]), []).append(row)
    for members in groups.values():
        members.sort(key=lambda row: row["RowNo"])
        initial = members[0][stock_field]
        consumed = 0
        for index, row in enumerate(members):
            if index:
                row[stock_field] = max(initial - consumed, 0)
            consumed += row[quantity_field]


def _pack_allocate(rows):
    """Apply the three repeated allocation CTE blocks from the source."""
    eligible = [row for row in rows if row["AvailableStock"] > 0]
    groups = {}
    for row in eligible:
        groups.setdefault(_k(row["SKUCode"], row["DestWhCode"], row["SrcWhCode"]), []).append(row)
    for members in groups.values():
        members.sort(key=lambda row: row["RowNo"])
        prior_initial = None
        cumulative_remaining = 0
        cumulative_prev = 0
        cumulative_allocation = 0
        for row in members:
            remaining, pack, available = row["RemainingQty"], row["ParentPackSize"], row["AvailableStock"]
            floored_available = _floor_decimal(available, pack) * pack
            initial = (_ceil_div_decimal(remaining, pack) * pack
                       if remaining < floored_available else floored_available)
            initial_excess = max(_ceil_div_decimal(remaining, pack) * pack - remaining, 0)
            prev = row.get("ExcessQty") if prior_initial is None else prior_initial
            cumulative_remaining += remaining
            if prev is not None:
                cumulative_prev += prev
            previous_remaining = cumulative_remaining - remaining
            if prev is None:
                balance = remaining
            elif cumulative_remaining < pack:
                balance = 0
            elif cumulative_remaining > pack and cumulative_prev > pack and cumulative_prev > cumulative_remaining:
                balance = remaining - (pack - previous_remaining)
            elif cumulative_prev > cumulative_remaining and cumulative_prev < pack:
                balance = cumulative_remaining - pack
            elif cumulative_prev > remaining and cumulative_prev > pack:
                balance = remaining - (cumulative_prev - pack)
            elif cumulative_prev > remaining and cumulative_prev < pack:
                balance = 0
            elif cumulative_prev < remaining and cumulative_prev > pack:
                balance = remaining - (cumulative_prev - pack)
            else:
                balance = remaining - cumulative_prev
            # Canonical defect: both operands are ints, so division occurs before CEILING.
            rounded_balance = _int_div(balance, pack) * pack
            final = rounded_balance if balance < floored_available else floored_available
            cumulative_allocation += final
            row["PackSizeWiseAllocatedQty"] = final
            row["CumulativeRemainingQty"] = cumulative_remaining
            row["TotalAllocation"] = cumulative_allocation
            row["OrderWiseAllocatedQty"] = (final if final > 0 else
                remaining if final == 0 and cumulative_remaining <= cumulative_allocation else 0)
            prior_initial = initial_excess


def _output(row, quantity, *, bpp=None, colour=None, due_at_dest=None, pack_quantity=None):
    return dict(SKUCode=row["SKUCode"], DestWhCode=row["DestWhCode"],
                SrcWhCode=row["SrcWhCode"], OrderKey=row["OrderKey"], DueDate=row["DueDate"],
                CustomerOrderId=row["CustomerOrderId"], IsSpike=int(row["IsSpike"]), Qty=row["Qty"],
                OrderWiseAllocatedQty=quantity, BPP=bpp, OrderColor=colour,
                DueDateAtDest=due_at_dest,
                PackSizeWiseAllocatedQty=quantity if pack_quantity is None else pack_quantity)


def _canonical_output(row, ordinal):
    """Return one exact typed BPR AllocatedOrders DDL row."""
    if tuple(row) != OUTPUT_FIELDS:
        raise ValueError(f"AllocatedOrders[{ordinal}] fields/order do not match native DDL")
    result = dict(row)
    for field in ("SKUCode", "DestWhCode", "SrcWhCode", "CustomerOrderId"):
        value = result[field]
        if not isinstance(value, str) or len(value.encode('utf-16-le')) // 2 > 50:
            raise ValueError(f"AllocatedOrders[{ordinal}].{field} is not nvarchar(50) NOT NULL")
    colour = result["OrderColor"]
    if colour is not None and (not isinstance(colour, str) or len(colour.encode('utf-16-le')) // 2 > 10):
        raise ValueError(f"AllocatedOrders[{ordinal}].OrderColor is not nullable nvarchar(10)")
    for field in ("OrderKey", "IsSpike", "Qty", "OrderWiseAllocatedQty",
                  "PackSizeWiseAllocatedQty"):
        _integer(result[field], f"AllocatedOrders[{ordinal}].{field}")
    # The target column is SQL int, even though the source order table stores bit.
    if type(result["IsSpike"]) is not int:
        raise ValueError(f"AllocatedOrders[{ordinal}].IsSpike must be a native SQL int")
    result["DueDate"] = _as_date(result["DueDate"],
                                  f"AllocatedOrders[{ordinal}].DueDate").isoformat()
    if result["DueDateAtDest"] is not None:
        result["DueDateAtDest"] = _as_date(
            result["DueDateAtDest"], f"AllocatedOrders[{ordinal}].DueDateAtDest").isoformat()
    bpp = result["BPP"]
    if bpp is not None:
        number = Decimal(str(bpp))
        if (not number.is_finite() or number.as_tuple().exponent < -2
                or not Decimal("-99999999.99") <= number <= Decimal("99999999.99")):
            raise ValueError(f"AllocatedOrders[{ordinal}].BPP exceeds decimal(10,2)")
        result["BPP"] = number.quantize(Decimal("0.01"))
    return result


def allocated_orders(*, business_date, daily_consumption, stock_calculation, spike_orders,
                     route_original, route_daily, requirement_bands, order_colours,
                     dbm_master, sku_loc_attributes):
    """Produce the complete native ``AllocatedOrders`` image for one same-run day.

    Input row order is the persisted source ordinal. It is retained whenever the
    SQL has no explicit sort and used only after every canonical ORDER BY field.
    """
    today = _as_date(business_date, "business_date")
    tables = (("DailyConsumption", daily_consumption),
              ("Vf_StockCalculation", stock_calculation),
              ("SpikeOrderData", spike_orders),
              ("SpikeOrderRouteOriginal", route_original),
              ("SpikeOrderRouteDaily", route_daily),
              ("RequirementInColorBand", requirement_bands),
              ("OrderRequirementColor", order_colours), ("DBMMaster", dbm_master),
              ("SkuLocAttributeData", sku_loc_attributes))
    for name, rows in tables:
        _validate(rows, name)
    order_keys = [row["OrderKey"] for row in spike_orders]
    if len(order_keys) != len(set(order_keys)):
        raise ValueError("SpikeOrderData OrderKey must retain its unique persisted identity")

    orders = deepcopy(list(spike_orders)); routes = deepcopy(list(route_original))
    colours = deepcopy(list(order_colours)); bands = deepcopy(list(requirement_bands))
    for row in colours:
        if row["BPP"] is not None:
            row["BPP"] = Decimal(str(row["BPP"])).quantize(Decimal("0.01"))
    masters = deepcopy(list(dbm_master)); attributes = deepcopy(list(sku_loc_attributes))
    output = []
    eco = []
    for source in daily_consumption:
        if _as_date(source["ReportDate"], "DailyConsumption.ReportDate") == today:
            eco.append(dict(SKUCode=source["SKUCode"], WHCode=source["WHCode"],
                            EcoStock=None if source["Stock"] is None or source["GIT"] is None else source["Stock"] + source["GIT"],
                            StockForRationing=source["Stock"], GIT=source["GIT"], ExcessAllocation=None))
    grains = [_k(row["SKUCode"], row["WHCode"]) for row in eco]
    if len(grains) != len(set(grains)):
        raise ValueError("DailyConsumption has duplicate current-day EcoStock grain")
    # Validated immutable stock population: ordered multimap, SQL NULLs never
    # join. Keep all duplicate candidates for the existing _winner denial.
    stock_by_grain = {}
    join_work = dict(index_builds=1, indexed_rows=len(stock_calculation),
                     lookup_probes=len(eco), matched_rows=0)
    for match in stock_calculation:
        grain = _k(match["SKUCode"], match["WHCode"])
        if grain is not None:
            stock_by_grain.setdefault(grain, []).append(match)
    for row in eco:
        values = [match["StockForRationing"] for match in
                  stock_by_grain.get(_k(row["SKUCode"], row["WHCode"]), ())]
        join_work['matched_rows'] += len(values)
        winner = _winner(values, "Vf_StockCalculation StockForRationing")
        if winner is not None:
            row["StockForRationing"] = winner

    del stock_by_grain

    # OrderKey uniqueness was checked above. The owned copies and join-key
    # fields below never change; EcoStock quantities do change in place.
    orders_by_key = {row["OrderKey"]: row for row in orders}
    join_indexes = {}

    def lookup(rows, fields, values):
        # Only the fixed owned eco/master/attribute/band/colour populations
        # enter here. Membership/key generations are immutable throughout this
        # call; ordered buckets retain original references and SQL join bags.
        join_work['lookup_probes'] += 1
        wanted = _k(*values)
        if wanted is None:
            return ()
        owner = (id(rows), fields)
        if owner not in join_indexes:
            index = {}
            for row in rows:
                grain = _k(*(row[field] for field in fields))
                if grain is not None:
                    index.setdefault(grain, []).append(row)
            join_indexes[owner] = index
            join_work['index_builds'] += 1
            join_work['indexed_rows'] += len(rows)
        matches = join_indexes[owner].get(wanted, ())
        join_work['matched_rows'] += len(matches)
        return matches

    def order_for(key):
        return orders_by_key.get(key)

    # Advance/GIT net-off is grouped after the route-to-order join.
    net = {}
    adv_by_order = {}
    for route in route_daily:
        if route["Type"] not in ("adv-stock", "GIT"):
            continue
        order = order_for(route["OrderKey"])
        if order is None:
            continue
        key = _k(order["SKUCode"], route["SrcWhCode"])
        values = net.setdefault(key, [0, 0])
        values[0 if route["Type"] == "adv-stock" else 1] += route["Qty"]
        adv_by_order[route["OrderKey"]] = adv_by_order.get(route["OrderKey"], 0) + route["Qty"]
    for row in eco:
        key = _k(row["SKUCode"], row["WHCode"])
        if key not in net:
            continue
        stock_qty, git_qty = net[key]
        row["EcoStock"] = max(row["EcoStock"] - stock_qty - git_qty, 0) if row["EcoStock"] is not None else 0
        row["StockForRationing"] = max(row["StockForRationing"] - stock_qty, 0) if row["StockForRationing"] is not None else 0
        row["GIT"] = max(row["GIT"] - git_qty, 0) if row["GIT"] is not None else 0

    node_orders = []
    for order in orders:
        if order["DueDate"] is None or _as_date(order["DueDate"], "SpikeOrderData.DueDate") > today:
            continue
        for stock in lookup(eco, ("SKUCode", "WHCode"), (order["SKUCode"], order["WhCode"])):
            if _positive(stock["EcoStock"]):
                node_orders.append(dict(order, DestWhCode=order["WhCode"], SrcWhCode=order["WhCode"],
                                        AvailableStock=stock["EcoStock"], RemainingQty=order["Qty"]))
    _rank(node_orders, ("SKUCode", "WhCode"), lambda r: (
        _sql_sort_date(r["DueDate"]), _sql_sort_date(r["CustomerExpectedDate"]), r["OrderKey"]), "RowNo")
    _available(node_orders)
    for row in node_orders:
        row["RemainingQty"] = max(row["Qty"] - (row["AvailableStock"] or 0), 0)
        allocated = row["Qty"] - row["RemainingQty"] if row["RemainingQty"] > 0 else row["Qty"]
        if allocated > 0:
            output.append(_output(row, allocated, bpp=Decimal("100.00"), colour="Black"))
    # Source defect: this update deducts AllocatedOrders.Qty, not allocated quantity.
    self_totals = {}
    for row in output:
        grain = _k(row["SKUCode"], row["SrcWhCode"])
        self_totals[grain] = self_totals.get(grain, 0) + row["Qty"]
    for stock in eco:
        total = self_totals.get(_k(stock["SKUCode"], stock["WHCode"]), 0)
        if total:
            stock["StockForRationing"] = max(stock["StockForRationing"] - total, 0) if stock["StockForRationing"] is not None else 0
            stock["EcoStock"] = max(stock["EcoStock"] - total, 0) if stock["EcoStock"] is not None else 0

    due_routes = [deepcopy(row) for row in routes if row["DueDate"] is not None and
                  _as_date(row["DueDate"], "route DueDate") <= today]
    fully_self = {row["OrderKey"] for row in node_orders if row["RemainingQty"] <= 0}
    due_routes = [row for row in due_routes if row["OrderKey"] not in fully_self]
    due_routes = [row for row in due_routes if row["OrderKey"] not in adv_by_order or
                  order_for(row["OrderKey"])["Qty"] - adv_by_order[row["OrderKey"]] > 0]

    node_orders_by_key = {}
    for node in node_orders:
        node_orders_by_key.setdefault(node["OrderKey"], []).append(node)
    eligible = []
    for route in due_routes:
        order = order_for(route["OrderKey"])
        if order is None:
            continue
        nodes = [row for row in node_orders_by_key.get(route["OrderKey"], ()) if
                 _same(route["SrcWhCode"], row["WhCode"]) and row["RemainingQty"] > 0]
        for node in nodes:
            eligible.append(dict(node, DestWhCode=node["WhCode"], SrcWhCode=route["SrcWhCode"],
                                 Qty=node["RemainingQty"]))
    del node_orders_by_key, self_totals
    existing = {row["OrderKey"] for row in eligible}
    seen_fresh = set()
    for route in due_routes:
        order = order_for(route["OrderKey"])
        if order is None or order["OrderKey"] in existing:
            continue
        projection = (order["SKUCode"], route["DestWhCode"] or order["WhCode"], route["SrcWhCode"],
                      order["OrderKey"], route["DueDate"], order["CustomerOrderId"], order["IsSpike"],
                      order["Qty"], order["CustomerExpectedDate"])
        signature = tuple(_sql_key(value) if isinstance(value, str) else value for value in projection)
        if signature in seen_fresh:
            continue
        seen_fresh.add(signature)
        eligible.append(dict(SKUCode=projection[0], DestWhCode=projection[1], SrcWhCode=projection[2],
                             OrderKey=projection[3], DueDate=projection[4], CustomerOrderId=projection[5],
                             IsSpike=projection[6], Qty=projection[7], CustomerExpectedDate=projection[8]))

    # Residual child rows are source rows derived by the same joins.
    residual = []
    for band in bands:
        if not band["ResidualChildrenSnP"] or band["ResidualChildrenSnP"] <= 0:
            continue
        for colour in lookup(colours, ("SKUCode", "SrcWhCode"), (band["SKUCode"], band["WhCode"])):
            order = order_for(colour["OrderKey"])
            for master in lookup(masters, ("SKUCode", "WHCode"), (band["SKUCode"], band["WhCode"])):
                due = _as_date(colour["DueDate"], "OrderRequirementColor.DueDate")
                shifted = due.fromordinal(due.toordinal() - master["RLT"])
                if order is not None and _same(order["SKUCode"], band["SKUCode"]) and shifted <= today:
                    residual.append(dict(SKUCode=band["SKUCode"], DestWhCode=band["WhCode"],
                        SrcWhCode=band["ParentWhCode"], OrderKey=order["OrderKey"], DueDate=shifted,
                        CustomerOrderId=order["CustomerOrderId"], IsSpike=order["IsSpike"], Qty=order["Qty"],
                        CustomerExpectedDate=None))
    join_indexes.pop((id(colours), ("SKUCode", "SrcWhCode")), None)
    residual = [row for row in residual if row["OrderKey"] not in fully_self]
    pre_residual_keys = {_k(*(row[f] for f in ("SKUCode", "SrcWhCode", "DestWhCode", "OrderKey")))
                         for row in eligible}
    for row in residual:
        if _k(*(row[f] for f in ("SKUCode", "SrcWhCode", "DestWhCode", "OrderKey"))) not in pre_residual_keys:
            eligible.append(deepcopy(row))
    for row in eligible:
        if row["OrderKey"] in adv_by_order:
            row["Qty"] = order_for(row["OrderKey"])["Qty"] - adv_by_order[row["OrderKey"]]
    eligible = [row for row in eligible if lookup(eco, ("SKUCode", "WHCode"),
                                                    (row["SKUCode"], row["DestWhCode"]))]

    def eco_one(sku, wh, owner):
        matches = lookup(eco, ("SKUCode", "WHCode"), (sku, wh))
        if len(matches) > 1:
            raise ValueError(owner + " has undefined EcoStock join multiplicity")
        return matches[0] if matches else None

    overdue = []
    by_order = {}
    for row in eligible:
        stock = eco_one(row["SKUCode"], row["DestWhCode"], "SpikeOrdersOverDueAtParent")
        if stock and (_positive(stock["StockForRationing"]) or _positive(stock["GIT"])):
            item = dict(row, AvailableStock=stock["StockForRationing"],
                        GIT=min(stock["EcoStock"], stock["GIT"]), ExcessQty=stock["ExcessAllocation"])
            by_order.setdefault(row["OrderKey"], []).append(item)
            overdue.append(item)
    for members in by_order.values():
        members.sort(key=lambda r: (_sql_sort_date(r["DueDate"]), r["OrderKey"]), reverse=True)
        for number, row in enumerate(members, 1):
            row["RowNoForHierarchy"] = number
    overdue = [row for row in overdue if not any(
        colour["OrderColor"] == "White" and not _same(colour["DestWhCode"], colour["SrcWhCode"])
        for colour in lookup(colours, ("OrderKey", "DestWhCode"),
                               (row["OrderKey"], row["DestWhCode"])))]
    join_indexes.pop((id(colours), ("OrderKey", "DestWhCode")), None)
    routes_by_order = {}
    for route in routes:
        routes_by_order.setdefault(route["OrderKey"], []).append(route)
    for row in overdue:
        updates = [(route["DestWhCode"] or route["SrcWhCode"], route["SrcWhCode"])
                   for route in routes_by_order.get(row["OrderKey"], ()) if
                   _same(route["SrcWhCode"], row["DestWhCode"])]
        winner = _winner(updates, "SpikeOrdersOverDueAtParent route promotion")
        if winner is not None:
            row["DestWhCode"], row["SrcWhCode"] = winner

    def pack_variants(sku, source, destination):
        matches = lookup(attributes, ("SKUCode", "LocCode"), (sku, source))
        # The source LEFT JOIN emits one work row per matching attribute row;
        # ISNULL supplies one only for a missing row or NULL PackSize.
        if not matches:
            return [1]
        return [1 if _same(destination, source) or row["PackSize"] is None else row["PackSize"]
                for row in matches]

    def allocation_winners(rows, owner):
        grouped = {}
        for row in rows:
            if row.get("OrderWiseAllocatedQty", 0) > 0:
                grouped.setdefault(row["OrderKey"], []).append(row["OrderWiseAllocatedQty"])
        return {key: _winner(values, owner) for key, values in grouped.items()}

    def refresh_excess():
        totals = {}
        for row in output:
            key = _k(row["SKUCode"], row["DestWhCode"])
            pair = totals.setdefault(key, [0, 0]); pair[0] += row["PackSizeWiseAllocatedQty"]; pair[1] += row["OrderWiseAllocatedQty"]
        for stock in eco:
            key = _k(stock["SKUCode"], stock["WHCode"])
            if key in totals:
                stock["ExcessAllocation"] = max(totals[key][0] - totals[key][1], 0)

    norm_req = {}
    for band in bands:
        value = None if any(band[f] is None for f in ("Norm", "RelCNR", "RelPSO")) else band["Norm"] + band["RelCNR"] + band["RelPSO"]
        key = _k(band["SKUCode"], band["WhCode"])
        if value is not None: norm_req[key] = norm_req.get(key, 0) + value
    max_level = max((row["RowNoForHierarchy"] for row in overdue), default=0)
    overdue_by_level = {}
    for row in overdue:
        overdue_by_level.setdefault(row["RowNoForHierarchy"], []).append(row)
    live_overdue = {id(row) for row in overdue}
    level = 1
    while max_level > 0:
        # Stock pass.
        black = {}
        for row in eligible:
            if _as_date(row["DueDate"], "eligible DueDate") <= today:
                key = _k(row["SKUCode"], row["SrcWhCode"]); black[key] = black.get(key, 0) + row["Qty"]
        inter = []
        for source in [r for r in overdue_by_level.get(level, ()) if id(r) in live_overdue and _positive(r["AvailableStock"])]:
            cs = lookup(colours, ("SKUCode", "DestWhCode", "SrcWhCode", "OrderKey"),
                          (source["SKUCode"], source["DestWhCode"], source["SrcWhCode"], source["OrderKey"]))
            ds = lookup(masters, ("SKUCode", "WHCode"), (source["SKUCode"], source["DestWhCode"]))
            bs = lookup(bands, ("SKUCode", "WhCode"), (source["SKUCode"], source["DestWhCode"]))
            stock = eco_one(source["SKUCode"], source["DestWhCode"], "InterNode stock pass")
            for colour in cs:
                for master in ds:
                    for band in bs:
                        if stock is None or any(band[f] is None for f in ("Norm", "RelCNR", "RelPSO")):
                            continue
                        black_qty = black.get(_k(source["SKUCode"], source["SrcWhCode"]), 0)
                        parent_norm = norm_req.get(_k(source["SKUCode"], source["SrcWhCode"]), 0)
                        allowed = ((black_qty + parent_norm > source["AvailableStock"] and colour["OrderColor"] != "White") or
                                   black_qty + parent_norm <= source["AvailableStock"] or
                                   (_same(source["DestWhCode"], source["SrcWhCode"]) and colour["OrderColor"] == "White"))
                        if not allowed: continue
                        available = (int(black_qty + max(source["AvailableStock"] - parent_norm - black_qty, 0))
                                     if source["AvailableStock"] > black_qty and not _same(source["DestWhCode"], source["SrcWhCode"])
                                     else source["AvailableStock"])
                        total_band = band["Norm"] + band["RelCNR"] + band["RelPSO"] + black.get(_k(band["SKUCode"], band["WhCode"]), 0)
                        white = max(stock["EcoStock"] - total_band, 0) if not _same(source["DestWhCode"], source["SrcWhCode"]) else 0
                        for pack in pack_variants(source["SKUCode"], source["SrcWhCode"], source["DestWhCode"]):
                            inter.append(dict(source, AvailableStock=available, RemainingQty=source["Qty"],
                                ParentPackSize=pack, WhiteStockAtDest=white,
                                ExcessQty=stock["ExcessAllocation"], RLT=master["RLT"], Norm=master["Norm"]))
        _rank(inter, ("SKUCode", "SrcWhCode"), lambda r: (_sql_sort_date(r["DueDate"]),
            _sql_sort_date(r["CustomerExpectedDate"]), r["OrderKey"], -r["RLT"], -r["Norm"]), "RowNo")
        _available(inter)
        dest_groups = {}
        for row in inter: dest_groups.setdefault(_k(row["SKUCode"], row["DestWhCode"]), []).append(row)
        for members in dest_groups.values():
            members.sort(key=lambda r:r["RowNo"]); initial=members[0]["WhiteStockAtDest"]; consumed=0
            for index,row in enumerate(members):
                if index: row["WhiteStockAtDest"] = max(initial-consumed,0)
                consumed += row["RemainingQty"]
                row["RemainingQty"] = max(row["RemainingQty"] - row["WhiteStockAtDest"], 0)
        zero = {row["OrderKey"] for row in inter if row["RemainingQty"] == 0}
        overdue = [row for row in overdue if row["OrderKey"] not in zero]
        eligible = [row for row in eligible if row["OrderKey"] not in zero]
        _pack_allocate(inter)
        for row in inter:
            if row.get("OrderWiseAllocatedQty", 0) > 0:
                output.append(_output(row, row["OrderWiseAllocatedQty"], pack_quantity=row["PackSizeWiseAllocatedQty"]))
        allocated_rows = [row for row in inter if row.get("OrderWiseAllocatedQty", 0) > 0]
        allocations = allocation_winners(allocated_rows, "InterNode stock allocation")
        for collection in (overdue, eligible):
            for row in collection:
                if row["OrderKey"] in allocations: row["Qty"] -= allocations[row["OrderKey"]]
        overdue = [row for row in overdue if row["Qty"] != 0]
        totals = {}
        for row in allocated_rows:
            key=_k(row["SKUCode"],row["SrcWhCode"]); totals[key]=totals.get(key,0)+row["PackSizeWiseAllocatedQty"]
        for stock in eco:
            amount=totals.get(_k(stock["SKUCode"],stock["WHCode"]),0)
            stock["StockForRationing"]=max(stock["StockForRationing"]-amount,0);stock["EcoStock"]=max(stock["EcoStock"]-amount,0)
        refresh_excess()
        for row in overdue:
            stock=eco_one(row["SKUCode"],row["SrcWhCode"],"stock refresh")
            if stock: row["AvailableStock"],row["ExcessQty"]=stock["StockForRationing"],stock["ExcessAllocation"]

        # Reconcile membership after this stock statement's deletes. Buckets
        # retain current quantities through their original mutable references.
        live_overdue = {id(row) for row in overdue}
        # GIT pass; it is intentionally not inserted into AllocatedOrders.
        git_rows=[]
        for source in [r for r in overdue_by_level.get(level, ()) if id(r) in live_overdue and _positive(r["GIT"])]:
            for master in lookup(masters,("SKUCode","WHCode"),(source["SKUCode"],source["DestWhCode"])):
                stock=eco_one(source["SKUCode"],source["DestWhCode"],"InterNode GIT pass")
                for pack in pack_variants(source["SKUCode"],source["SrcWhCode"],source["DestWhCode"]):
                    git_rows.append(dict(source,AvailableStock=source["GIT"],RemainingQty=source["Qty"],
                        ParentPackSize=pack, ExcessQty=None if stock is None else stock["ExcessAllocation"],
                        RLT=master["RLT"],Norm=master["Norm"]))
        _rank(git_rows,("SKUCode","SrcWhCode"),lambda r:(_sql_sort_date(r["DueDate"]),
            _sql_sort_date(r["CustomerExpectedDate"]),r["OrderKey"],-r["RLT"],-r["Norm"]),"RowNo")
        _available(git_rows);_pack_allocate(git_rows)
        git_allocated_rows=[row for row in git_rows if row.get("OrderWiseAllocatedQty",0)>0]
        git_alloc=allocation_winners(git_allocated_rows,"InterNode GIT allocation")
        for collection in (overdue,eligible):
            for row in collection:
                if row["OrderKey"] in git_alloc:row["Qty"]-=git_alloc[row["OrderKey"]]
        overdue=[row for row in overdue if row["Qty"]!=0]
        totals={}
        for row in git_allocated_rows:
            key=_k(row["SKUCode"],row["SrcWhCode"]);totals[key]=totals.get(key,0)+row["PackSizeWiseAllocatedQty"]
        for stock in eco:
            amount=totals.get(_k(stock["SKUCode"],stock["WHCode"]),0)
            stock["EcoStock"]=max(stock["EcoStock"]-amount,0);stock["GIT"]=max(stock["GIT"]-amount,0)
        refresh_excess()
        for row in overdue:
            stock=eco_one(row["SKUCode"],row["SrcWhCode"],"GIT refresh")
            if stock:row["GIT"],row["ExcessQty"]=stock["GIT"],stock["ExcessAllocation"]
        live_overdue = {id(row) for row in overdue}
        level += 1; max_level -= level - 1

    join_indexes.pop((id(bands), ("SKUCode", "WhCode")), None)
    del overdue_by_level, live_overdue, norm_req
    eligible=[row for row in eligible if row["Qty"]>0]
    for row in eligible:
        stock=eco_one(row["SKUCode"],row["SrcWhCode"],"parent stock refresh")
        row["ParentStockForRationing"]=None if stock is None else stock["StockForRationing"]
    hierarchy=[]
    for row in eligible:
        if not row["ParentStockForRationing"] or row["ParentStockForRationing"]<=0:continue
        for master in lookup(masters,("SKUCode","WHCode"),(row["SKUCode"],row["DestWhCode"])):
            for pack in pack_variants(row["SKUCode"],row["SrcWhCode"],row["DestWhCode"]):
                hierarchy.append(dict(row,Norm=master["Norm"],RLT=master["RLT"],ParentPackSize=pack))
    join_indexes.pop((id(masters), ("SKUCode", "WHCode")), None)
    join_indexes.pop((id(attributes), ("SKUCode", "LocCode")), None)
    by_order={}
    for row in hierarchy:by_order.setdefault(row["OrderKey"],[]).append(row)
    for members in by_order.values():
        members.sort(key=lambda r:(_sql_sort_date(r["DueDate"]),r["OrderKey"]),reverse=True)
        for number,row in enumerate(members,1):row["RowNoForHierarchy"]=number
    hierarchy_by_level = {}
    for row in hierarchy:
        hierarchy_by_level.setdefault(row["RowNoForHierarchy"], []).append(row)
    live_hierarchy = {id(row) for row in hierarchy}
    max_level=max((r["RowNoForHierarchy"] for r in hierarchy),default=0);level=1
    while max_level>0:
        rows=[dict(r,AvailableStock=r["ParentStockForRationing"],RemainingQty=r["Qty"],
                   ExcessQty=(eco_one(r["SKUCode"],r["DestWhCode"],"final excess") or {}).get("ExcessAllocation"))
              for r in hierarchy_by_level.get(level, ()) if id(r) in live_hierarchy]
        _rank(rows,("SKUCode","SrcWhCode"),lambda r:(_sql_sort_date(r["DueDate"]),
            _sql_sort_date(r["CustomerExpectedDate"]),r["OrderKey"],-r["RLT"],-r["Norm"]),"RowNo")
        _available(rows);_pack_allocate(rows)
        for row in rows:
            if row.get("OrderWiseAllocatedQty",0)>0:
                output.append(_output(row,row["OrderWiseAllocatedQty"],pack_quantity=row["PackSizeWiseAllocatedQty"]))
        remaining_by_order = {}
        for source in rows:
            if source.get("CumulativeRemainingQty", 1) <= source.get("TotalAllocation", 0):
                remaining_by_order.setdefault(source["OrderKey"], []).append(source["RemainingQty"])
        for target in hierarchy:
            values = [target["Qty"] - remaining for remaining in
                      remaining_by_order.get(target["OrderKey"], ())]
            winner = _winner(values, "WhlevelwiseSortedOrders remaining quantity")
            if winner is not None:
                target["Qty"] = winner
        hierarchy=[r for r in hierarchy if r["Qty"] != 0]
        live_hierarchy = {id(row) for row in hierarchy}
        level+=1;max_level-=level-1

    # The final colour updates do not consume stock or attribute populations.
    join_indexes.pop((id(eco), ("SKUCode", "WHCode")), None)
    del hierarchy_by_level, live_hierarchy
    # Advance allocation UPDATE/INSERT and final source colour/date updates.
    advances = [r for r in route_daily if r["Type"] == "adv-stock"]
    advance_counts = {}
    for route in advances:
        grain = (route["OrderKey"], _k(route["DestWhCode"] or route["SrcWhCode"], route["SrcWhCode"]))
        advance_counts[grain] = advance_counts.get(grain, 0) + 1
    output_by_route = {}
    def output_grain(row):
        return row["OrderKey"], _k(row["SKUCode"], row["DestWhCode"], row["SrcWhCode"])
    for row in output:
        output_by_route.setdefault(output_grain(row), []).append(row)
    for route in advances:
        order=order_for(route["OrderKey"])
        if order is None:continue
        dest=route["DestWhCode"] or route["SrcWhCode"]
        grain = (route["OrderKey"], _k(order["SKUCode"], dest, route["SrcWhCode"]))
        matches=output_by_route.get(grain, ())
        if matches:
            if advance_counts[route["OrderKey"], _k(dest, route["SrcWhCode"])] > 1:
                raise ValueError("Advance allocation has undefined repeated UPDATE winners")
            for row in matches:
                row["OrderWiseAllocatedQty"]+=route["Qty"];row["Qty"]+=route["Qty"];row["PackSizeWiseAllocatedQty"]+=route["Qty"]
        else:
            row = dict(SKUCode=order["SKUCode"],DestWhCode=dest,SrcWhCode=route["SrcWhCode"],
                OrderKey=order["OrderKey"],DueDate=order["DueDate"],CustomerOrderId=order["CustomerOrderId"],
                IsSpike=int(order["IsSpike"]),Qty=order["Qty"],OrderWiseAllocatedQty=route["Qty"],BPP=None,
                OrderColor=None,DueDateAtDest=None,PackSizeWiseAllocatedQty=route["Qty"])
            output.append(row)
            output_by_route.setdefault(grain, []).append(row)
    del advances, advance_counts, output_by_route
    daily_by_order = {}
    for route in route_daily:
        daily_by_order.setdefault(route["OrderKey"], []).append(route)
    residual_keys={_k(r["OrderKey"],r["SKUCode"],r["DestWhCode"],r["SrcWhCode"]) for r in residual}
    for row in output:
        due_values=[r["DueDate"] for r in routes_by_order.get(row["OrderKey"], ()) if _same(row["DestWhCode"],r["SrcWhCode"])]
        due=_winner(due_values,"AllocatedOrders DueDateAtDest")
        if due is not None:row["DueDateAtDest"]=due
        matches=lookup(colours,("SKUCode","DestWhCode","SrcWhCode","OrderKey"),
                         (row["SKUCode"],row["DestWhCode"],row["SrcWhCode"],row["OrderKey"]))
        update=_winner([(r["BPP"],r["OrderColor"]) for r in matches],"AllocatedOrders colour/BPP")
        if update is not None:row["BPP"],row["OrderColor"]=update
        if row["BPP"] is None and _k(row["OrderKey"],row["SKUCode"],row["DestWhCode"],row["SrcWhCode"]) in residual_keys:
            row["BPP"],row["OrderColor"]=Decimal("100.00"),"Black"
        if any(r["OrderKey"]==row["OrderKey"] and r["Type"] in ("adv-stock","GIT") and
               _k(r["SrcWhCode"],r["DestWhCode"] or r["SrcWhCode"])==_k(row["SrcWhCode"],row["DestWhCode"])
               and lookup(colours,("OrderKey","SrcWhCode","DestWhCode"),
                            (r["OrderKey"],r["SrcWhCode"],r["DestWhCode"] or r["SrcWhCode"]))
               for r in daily_by_order.get(row["OrderKey"], ())):row["OrderColor"]="White"
    summary('r1_native_order_indexes', **join_work, output_rows=len(output))
    # Release disposable lookup/group graphs before copying canonical output
    # rows. No derived index crosses the production handoff boundary.
    join_indexes.clear()
    del daily_by_order, residual_keys, routes_by_order, orders_by_key, by_order
    del eco, orders, routes, colours, bands, masters, attributes
    del eligible, overdue, node_orders, hierarchy
    return [_canonical_output(row, ordinal) for ordinal, row in enumerate(output)]
