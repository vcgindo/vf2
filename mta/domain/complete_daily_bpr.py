"""Optional, unintegrated complete-day BPR success-path SQL producers.

Authority: GulfOil/BPR/CalculatedAttributes.sql and BPR/ProdOrderSuggestions.sql.
No I/O, engine execution, hidden populations, or legacy exception recovery occurs
here. SQL TRY/CATCH errors are exposed to the caller rather than represented as a
successful empty result. Dynamic execution-flag SQL remains the completion owner.
Native collation and FLOAT conversions must be supplied explicitly: these are
semantic inputs, not permission to approximate SQL formatting or repair data.
Statement snapshots retain scratch rows; final scratch populations are empty.
Production consumes live stage values with final_stage; validation snapshots them.
"""
from copy import deepcopy
from mta.evidence import snapshot, final_stage
from datetime import date, datetime
import math


def _match(left, right, fields, equal):
    # SQL equality is UNKNOWN for NULL, regardless of the collation adapter.
    return all(left[a] is not None and right[b] is not None
               and equal(left[a], right[b]) for a, b in fields)


def _update(targets, sources, fields, value, field, equal, label):
    for target in targets:
        outcomes = [value(source) for source in sources
                    if _match(target, source, fields, equal)]
        if not outcomes:
            continue
        if any(outcome != outcomes[0] for outcome in outcomes[1:]):
            raise ValueError('SOURCE_ORDER_AMBIGUITY: ' + label)
        target[field] = outcomes[0]


def _int(value, label, nullable=False):
    if value is None and nullable:
        return None
    if value is None:
        raise ValueError('NONNULL_CONSTRAINT: ' + label)
    if type(value) is not int:
        raise ValueError('TYPED_INPUT_REQUIRED: SQL int ' + label)
    if not -2147483648 <= value <= 2147483647:
        raise ValueError('ARITHMETIC_OVERFLOW: SQL int ' + label)
    return value


def _text(value, label, size, nullable=False):
    if value is None and nullable:
        return None
    if value is None:
        raise ValueError('NONNULL_CONSTRAINT: ' + label)
    if not isinstance(value, str):
        raise ValueError('TYPED_INPUT_REQUIRED: SQL nvarchar ' + label)
    if len(value.encode('utf-16-le')) // 2 > size:
        raise ValueError('STRING_TRUNCATION: ' + label)
    return value


def _date(value):
    """Cast retained typed datetime/date (or their ISO reconstruction) to date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return datetime.fromisoformat(value).date().isoformat()
    raise ValueError('TYPED_INPUT_REQUIRED: SQL date/datetime')


def post_bpr_stages(*, sku_loc_attributes, pick_list_report, master_data_raw,
                    bpr_table, importer_sku_loc_attributes, nms_all_items,
                    intermediate_tables, equal, try_cast_float,
                    float_to_nvarchar, round_float):
    """Ordered PostBPR assignments over typed native populations.

    Adapters implement SQL collation equality, TRY_CAST(... AS FLOAT), implicit
    FLOAT to nvarchar(50) style 0, and ROUND(FLOAT,0) respectively. NULL cast
    failures become zero exactly at ISNULL, never at downstream arithmetic.
    Callers must qualify these adapters against their actual native runtime.
    """
    state = deepcopy({'SkuLocAttributeData': sku_loc_attributes,
                      'BPR_Table': bpr_table,
                      'ImporterSkuLocAttributeData': importer_sku_loc_attributes,
                      'NMSAllItems': nms_all_items,
                      'IntermediateTables': intermediate_tables})
    state['IntermediateTables'] = {name: [] for name in intermediate_tables}
    yield 'truncate-intermediate-before', snapshot(state)
    nonself = [r for r in pick_list_report
               if r['WhCode'] is not None and r['ParentWhCode'] is not None
               and not equal(r['WhCode'], r['ParentWhCode'])]
    pair = (('SKUCode', 'SKUCode'), ('LocCode', 'WhCode'))
    _update(state['SkuLocAttributeData'], nonself, pair,
            lambda r: str(_int(r['RationedReq'], 'Pick.RationedReq')),
            'c3', equal, 'PostBPR rationed c3')
    yield 'rationed-c3', snapshot(state)
    dispatch = []
    raw_fields = (('SKUCode', 'SKUCode'), ('WhCode', 'WhCode'),
                  ('ParentWhCode', 'ParentWhCode'))
    for pick in nonself:
        for raw in master_data_raw:
            if not _match(pick, raw, raw_fields, equal):
                continue
            if pick['ParentWhCode'] is None or raw['SKULocAtt01'] is None or not equal(
                    pick['ParentWhCode'], raw['SKULocAtt01']):
                continue
            percent = try_cast_float(raw['SKULocAtt02'])
            percent = 0.0 if percent is None else percent
            if type(percent) is not float or not math.isfinite(percent):
                raise ValueError('TYPED_INPUT_REQUIRED: native TRY_CAST FLOAT')
            norm, stock, git, pack, available = [
                _int(pick[f], 'Pick.' + f, nullable=f in ('VirtualNorm', 'ParentPackSize'))
                for f in ('VirtualNorm', 'Stock', 'GIT', 'ParentPackSize',
                          'ParentStockForRationing')]
            qty = None if any(v is None for v in (norm, stock, git)) else (
                round_float(percent * norm / 100) - stock - git)
            if qty is not None and qty < 0:
                qty = 0.0
            if pack == 0 and available is not None:
                raise ValueError('DIVIDE_BY_ZERO: PostBPR ParentPackSize')
            if pack is None:
                up = down = cap = None
            else:
                up = None if qty is None else float(math.ceil(qty / pack) * pack)
                down = None if qty is None else float(math.floor(qty / pack) * pack)
                # 1.0 * int / int is decimal in this branch; use integer floor
                # division to avoid a binary FLOAT rounding error on the cap.
                cap = None if available is None else float((available // pack) * pack)
            value = (up if up is not None and available is not None and up <= available
                     else down if down is not None and available is not None and down <= available
                     else cap)
            text = None if value is None else float_to_nvarchar(value)
            dispatch.append({'SKUCode': pick['SKUCode'], 'WhCode': pick['WhCode'],
                             'c3': _text(text, 'SkuLocAttributeData.c3', 50, nullable=True)})
    _update(state['SkuLocAttributeData'], dispatch, pair, lambda r: r['c3'],
            'c3', equal, 'PostBPR dispatch c3')
    yield 'dispatch-c3', snapshot(state)
    attrs = state['SkuLocAttributeData']
    for table, loc, field in (('BPR_Table', 'WhCode', 'SKULocAttr3'),
                              ('ImporterSkuLocAttributeData', 'LocCode', 'c3'),
                              ('NMSAllItems', 'WhCode', 'SKULocAtt03')):
        _update(state[table], attrs, (('SKUCode', 'SKUCode'), (loc, 'LocCode')),
                lambda r: r['c3'], field, equal, 'PostBPR propagation ' + table)
        yield 'propagate-' + table, snapshot(state)
    state['IntermediateTables'] = {name: [] for name in intermediate_tables}
    yield 'truncate-intermediate-after', snapshot(state)


def post_bpr_calculated_attributes(**populations_and_adapters):
    """Return final PostBPR populations without retaining diagnostic snapshots."""
    return final_stage(post_bpr_stages(**populations_and_adapters))[-1][1]


def production_suggestion_stages(*, supplier_dispatch_req, plants,
                                 rationed_req_report, daily_consumption,
                                 last_batch_run, prod_order_suggestions,
                                 intermediate_tables, equal, sort_key):
    """Native int success path, preserving join multiplicity and update order.

    Unordered TOP(1) is accepted only when every candidate date is identical.
    Input rows must already have their native schema types; no guessed casts.
    EcoCol in the source is a SELECT alias for positional EcoColor insertion.
    Unqualified ReqTopOfRed/Yellow/Green resolve to SupplierDispatchReq A;
    vf_RationedReqReport C owns only the selected Norm/Stock/GIT values.
    This does not establish compatibility with order-data-based planning.
    """
    today = _date(last_batch_run[0]['LastRunDate']) if last_batch_run else None
    if any(_date(r['LastRunDate']) != today for r in last_batch_run[1:]):
        raise ValueError('SOURCE_ORDER_AMBIGUITY: TOP1 LastBatchRunTbl')
    state = deepcopy({'ProdOrderSuggestions': prod_order_suggestions,
                      'IntermediateTables': intermediate_tables})
    scratch = state['IntermediateTables'] = {name: [] for name in intermediate_tables}
    required = ('TempProductionOrderReq', 'TempConsolidatedProdOrderReq', 'PlantStock')
    if any(name not in scratch for name in required):
        raise ValueError('SCHEMA_REQUIRED: production suggestion intermediate tables')
    yield 'truncate-intermediate-before', snapshot(state)
    state['ProdOrderSuggestions'] = []
    yield 'truncate-suggestions', snapshot(state)
    for req in supplier_dispatch_req:
        for plant in plants:
            if not _match(req, plant, (('SupplierCode', 'PlantCode'),), equal):
                continue
            for report in rationed_req_report:
                if not _match(req, report, (('SKUCode', 'SKUCode'), ('WHCode', 'WhCode')), equal):
                    continue
                row = {'SKUCode': _text(req['SKUCode'], 'TempProductionOrderReq.SKUCode', 50),
                       'WHCode': _text(req['WHCode'], 'TempProductionOrderReq.WHCode', 50),
                       'PlantCode': _text(plant['PlantCode'], 'TempProductionOrderReq.PlantCode', 50)}
                for target, source in (('Norm', 'Norm'), ('Stock', 'Stock'), ('GIT', 'GIT'),
                                       ('Red', 'ReqTopOfRed'), ('Yellow', 'ReqTopOfYellow'),
                                       ('Green', 'ReqTopOfGreen')):
                    owner = req if target in ('Red', 'Yellow', 'Green') else report
                    row[target] = _int(owner[source], 'TempProductionOrderReq.' + target,
                                       nullable=target == 'Stock')
                scratch['TempProductionOrderReq'].append(row)
    yield 'insert-production-req', snapshot(state)
    consolidated = scratch['TempConsolidatedProdOrderReq']
    for row in scratch['TempProductionOrderReq']:
        hits = [r for r in consolidated if _match(row, r,
                (('SKUCode', 'SKUCode'), ('PlantCode', 'PlantCode')), equal)]
        if not hits:
            consolidated.append({k: row[k] for k in ('SKUCode', 'PlantCode', 'Red', 'Yellow', 'Green')}
                                | {'TotalReq': 0, 'RemPlantEcoStk': 0, 'EcoColor': 'Green'})
        else:
            if any(hits[0][k] != row[k] for k in ('SKUCode', 'PlantCode')):
                raise ValueError('SOURCE_ORDER_AMBIGUITY: grouped production key representative')
            for color in ('Red', 'Yellow', 'Green'):
                hits[0][color] = _int(hits[0][color] + row[color], 'SUM(' + color + ')')
    consolidated.sort(key=lambda r: sort_key(r['SKUCode']))
    yield 'consolidate-production-req', snapshot(state)
    for daily in daily_consumption:
        if today is None or daily['ReportDate'] is None or _date(daily['ReportDate']) != today:
            continue
        for plant in plants:
            if _match(daily, plant, (('WHCode', 'PlantCode'),), equal):
                scratch['PlantStock'].append({
                    'SKUCode': _text(daily['SKUCode'], 'PlantStock.SKUCode', 50),
                    'WHCode': _text(daily['WHCode'], 'PlantStock.WHCode', 50),
                    'Stock': _int(0 if daily['Stock'] is None else daily['Stock'], 'PlantStock.Stock'),
                    'GIT': _int(daily['GIT'], 'PlantStock.GIT')})
    yield 'insert-plant-stock', snapshot(state)
    _update(consolidated, scratch['PlantStock'],
            (('SKUCode', 'SKUCode'), ('PlantCode', 'WHCode')),
            lambda r: _int(r['Stock'] + r['GIT'], 'PlantStock.Stock+GIT'),
            'RemPlantEcoStk', equal, 'production plant stock')
    yield 'update-plant-eco-stock', snapshot(state)
    for color in ('Red', 'Yellow', 'Green'):
        for row in consolidated:
            eligible = (row['Red'] > 0 if color == 'Red' else
                        row['Red'] == 0 and row['Yellow'] > 0 if color == 'Yellow' else
                        row['Red'] == 0 and row['Yellow'] == 0)
            if eligible:
                stock, req = row['RemPlantEcoStk'], row[color]
                row[color] = 0 if stock >= req else _int(req - stock, color + '-stock')
                row['RemPlantEcoStk'] = _int(stock - req, 'stock-' + color) if stock >= req else 0
                row['EcoColor'] = color
        yield 'net-' + color.lower(), snapshot(state)
    for row in consolidated:
        row['TotalReq'] = _int(_int(row['Red'] + row['Yellow'], 'Red+Yellow') + row['Green'], 'TotalReq')
    yield 'total-production-req', snapshot(state)
    if today is None and any(r['TotalReq'] > 0 for r in consolidated):
        raise ValueError('NONNULL_CONSTRAINT: ProdOrderSuggestions.ReportDate')
    state['ProdOrderSuggestions'] = [{k: r[k] for k in (
        'SKUCode', 'PlantCode', 'Red', 'Yellow', 'Green', 'TotalReq', 'EcoColor')}
        | {'ReportDate': today} for r in consolidated if r['TotalReq'] > 0]
    yield 'insert-suggestions', snapshot(state)
    state['IntermediateTables'] = {name: [] for name in intermediate_tables}
    yield 'truncate-intermediate-after', snapshot(state)


def production_order_suggestions(**populations_and_settings):
    """Return final suggestions and cleared scratch populations."""
    return final_stage(production_suggestion_stages(**populations_and_settings))[-1][1]
