"""Optional pure success path for GulfOil CalculateAttributeBasedonBTR.sql.

Opening FG history, all populations and native text equality are explicit.
No inferred history, FGRM filtering of RM branches, prior-colour copying, or
business-rule repair. Errors are exposed, not converted into legacy CATCH rows;
partial-write/error orchestration and native differential proof remain external.
Production consumes live stage values with final_stage; validation snapshots them.
"""
from copy import deepcopy
from mta.evidence import snapshot, final_stage
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext

from mta.domain.complete_daily_bpr import _date, _int, _text

ATTRS = ('c9', 'c10', 'c12', 'c13')
DAY_FIELDS = tuple('D' + str(i) for i in range(61, 91))
SCRATCH = 'GulfOil_TechColorData'


def _v(row, field):
    hits = [value for key, value in row.items() if key.casefold() == field.casefold()]
    if not hits:
        raise KeyError(field)
    if len(hits) != 1:
        raise ValueError('COLUMN_AMBIGUITY: ' + field)
    return hits[0]


def _set(row, field, value):
    hits = [key for key in row if key.casefold() == field.casefold()]
    if len(hits) > 1:
        raise ValueError('COLUMN_AMBIGUITY: ' + field)
    row[hits[0] if hits else field] = value


def _eq(a, b, equal):
    return a is not None and b is not None and equal(a, b)


def _group_eq(a, b, equal):
    return a is None and b is None or _eq(a, b, equal)


def _join(a, b, fields, equal):
    return all(_eq(_v(a, x), _v(b, y), equal) for x, y in fields)


def _in(value, choices, equal):
    return any(_eq(value, choice, equal) for choice in choices)


def _distinct(rows, fields, equal):
    output = []
    for row in rows:
        hits = [r for r in output if all(_group_eq(_v(r, f), _v(row, f), equal)
                                         for f in fields)]
        if hits:
            if any(_v(hits[0], f) != _v(row, f) for f in fields):
                raise ValueError('SOURCE_ORDER_AMBIGUITY: DISTINCT PostBTR representative')
        else:
            output.append(row)
    return output


def _assign(targets, sources, fields, target_fields, source_fields, equal, label):
    for target in targets:
        outcomes = [tuple(_v(source, f) for f in source_fields) for source in sources
                    if _join(target, source, fields, equal)]
        if outcomes:
            if any(value != outcomes[0] for value in outcomes[1:]):
                raise ValueError('SOURCE_ORDER_AMBIGUITY: ' + label)
            for field, value in zip(target_fields, outcomes[0]):
                _set(target, field, value)


def _colour_rows(trends, dates, equal):
    rows = []
    for trend in trends:
        if not _in(_v(trend, 'D90'), ('Black', 'Red'), equal):
            continue
        for calendar in dates:
            for field in DAY_FIELDS:
                value = _v(trend, field)
                rows.append({'ReportDate': _date(_v(calendar, field)),
                             'SKUCode': _text(_v(trend, 'SKUCode'), SCRATCH + '.SKUCode', 50, nullable=True),
                             'WhCode': _text(_v(trend, 'WhCode'), SCRATCH + '.WhCode', 50, nullable=True),
                             'TechColor': 'NA' if value is None else
                             _text(value, 'GulfOil_TechColorData.TechColor', 10, nullable=True)})
    return _distinct(rows, ('ReportDate', 'SKUCode', 'WhCode', 'TechColor'), equal)


def _fill_pass(rows, equal):
    # One UPDATE reads the statement's opening source, not already-updated rows.
    before = deepcopy(rows)
    for row in rows:
        when = _v(row, 'ReportDate')
        if when is None or not _eq(_v(row, 'TechColor'), 'NA', equal):
            continue
        previous = (date.fromisoformat(when) - timedelta(days=1)).isoformat()
        if any(_join(row, r, (('SKUCode', 'SKUCode'), ('WhCode', 'WhCode')), equal)
               and _v(r, 'ReportDate') == previous
               and _v(r, 'TechColor') is not None
               and not _eq(_v(r, 'TechColor'), 'NA', equal) for r in before):
            _set(row, 'TechColor', '0')


def _ages(rows, eligible, equal):
    groups = []
    for row in rows:
        hits = [g for g in groups if all(_group_eq(_v(g[0], f), _v(row, f), equal)
                                       for f in ('SKUCode', 'WhCode'))]
        if hits:
            if any(_v(hits[0][0], f) != _v(row, f) for f in ('SKUCode', 'WhCode')):
                raise ValueError('SOURCE_ORDER_AMBIGUITY: grouped PostBTR key representative')
            hits[0].append(row)
        else:
            groups.append([row])
    result = []
    for group in groups:
        changed = [r['ReportDate'] for r in group if r['ReportDate'] is not None
                   and r['TechColor'] is not None
                   and not _in(r['TechColor'], (*eligible, '0'), equal)]
        latest = max(changed) if changed else None
        # MAX of all suffix sums equals the total of these nonnegative CASE
        # contributions, even with tied dates. No tie ordering is invented.
        count = sum(_in(r['TechColor'], eligible, equal) and r['ReportDate'] is not None
                    and (latest is None or r['ReportDate'] >= latest) for r in group)
        result.append({'SKUCode': group[0]['SKUCode'], 'WhCode': group[0]['WhCode'],
                       'Age': str(_int(count, 'PostBTR Age'))})
    return result


def _penetration(row, eco):
    child, norm = (_int(row[f], 'FGTrendData.' + f, nullable=True)
                   for f in ('ChildVN', 'CurrentNodeNorm'))
    if child is None or norm is None:
        return None
    denominator = _int(child + norm, 'FGTrendData.ChildVN+CurrentNodeNorm')
    if denominator == 0:
        return None
    fields = ('ChildStock', 'ChildGIT', 'CurrentNodeStock') + (('CurrentNodeGIT',) if eco else ())
    values = [_int(row[f], 'FGTrendData.' + f, nullable=True) for f in fields]
    if any(value is None for value in values):
        return None
    with localcontext() as context:
        context.prec = 60
        numerator = Decimal(100) * (Decimal(child) - sum(values) + norm)
        # Literal 1.0 is decimal(2,1); every int subtraction/addition increases
        # precision. Native division reduces p39/s12 -> p38/s11 (technical),
        # p40/s12 -> p38/s10 (economic), before decimal(13,3) assignment.
        intermediate = (numerator / denominator).quantize(
            Decimal(1).scaleb(-10 if eco else -11), rounding=ROUND_HALF_UP)
        value = intermediate.quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
    if abs(value) >= Decimal('10000000000'):
        raise ValueError('ARITHMETIC_OVERFLOW: FGTrendData decimal(13,3)')
    return value


def _band(value):
    if value is None:
        return 'White'
    for threshold, color in ((Decimal('100'), 'Black'), (Decimal('66.67'), 'Red'),
                              (Decimal('33.33'), 'Yellow'), (Decimal('0'), 'Green')):
        if value >= threshold:
            return color
    return 'White'


def _fg_grid(history, dates, today, color, equal):
    selected = _distinct([{'SKUCode': r['CurrentNodeSKU'], 'WhCode': r['CurrentNodeWhCode']}
                          for r in history if today is not None and _date(r['ReportDate']) == today
                          and _in(r[color], ('Black', 'Red'), equal)], ('SKUCode', 'WhCode'), equal)
    rows = []
    for key in selected:
        for calendar in dates:
            for field in DAY_FIELDS:
                when = _date(_v(calendar, field))
                # UNPIVOT drops NULL values; RM CROSS APPLY does not.
                if when is None:
                    continue
                hits = [r for r in history if _join(key, r,
                        (('SKUCode', 'CurrentNodeSKU'), ('WhCode', 'CurrentNodeWhCode')), equal)
                        and _date(r['ReportDate']) == when]
                rows.extend(key | {'ReportDate': when, 'TechColor': 'NA' if r[color] is None else r[color]}
                            for r in hits)
                if not hits:
                    rows.append(key | {'ReportDate': when, 'TechColor': 'NA'})
    return _distinct(rows, ('ReportDate', 'SKUCode', 'WhCode', 'TechColor'), equal)


def _fg_assign(attributes, history, bor, ages, field, eligible, equal):
    sources = []
    for fg in history:
        key = {'SKUCode': fg['CurrentNodeSKU'], 'WhCode': fg['CurrentNodeWhCode']}
        counts = [r['Age'] for r in ages if _join(key, r,
                  (('SKUCode', 'SKUCode'), ('WhCode', 'WhCode')), equal)] or ['0']
        orders = [r for r in bor if _join(key, r,
                  (('SKUCode', 'SKUCode'), ('WhCode', 'WhCode')), equal)]
        colors = [_v(r, 'DispatchColor') for r in orders] or [None]
        for count in counts:
            for color in colors:
                # NULL comparisons are UNKNOWN; CASE follows ELSE.
                value = '0' if color is not None and not _in(color, eligible, equal) else count
                sources.append(key | {'Age': value})
    _assign(attributes, sources, (('SKUCode', 'SKUCode'), ('LocCode', 'WhCode')),
            (field,), ('Age',), equal, 'FG PostBTR ' + field)


def post_btr_stages(*, buffer_trend_report, buffer_trend_report_econ,
                    buffer_trend_dates, last_batch_run, sku_loc_attributes,
                    location_attributes, req_calculation,
                    importer_sku_loc_attributes, fg_trend_data,
                    bor_with_order_allocation, bpr_table, bpr_sku_loc_attributes,
                    supplier_dispatch_req, dbm_sku_loc_attributes, nms_all_items,
                    intermediate_tables, equal):
    """Yield ordered SQL statement outputs, without mutating any input.

    `equal` must implement the actual native collation (including trailing-space
    semantics). Native typed integer inputs and nullable decimal history are
    required. Reconstructed dates/datetimes may use ISO strings. Supplying an
    empty FG opening is an explicit caller decision, not a producer default.
    """
    state = deepcopy({'SkuLocAttributeData': sku_loc_attributes, 'FGTrendData': fg_trend_data,
                      'BPR_Table': bpr_table, 'BPRSkuLocAttributeData': bpr_sku_loc_attributes,
                      'SupplierDispatchReq': supplier_dispatch_req,
                      'DBMSkuLocAttributeData': dbm_sku_loc_attributes,
                      'ImporterSkuLocAttributeData': importer_sku_loc_attributes,
                      'NMSAllItems': nms_all_items, 'IntermediateTables': intermediate_tables})
    state['IntermediateTables'] = {name: [] for name in intermediate_tables}
    if SCRATCH not in intermediate_tables:
        raise ValueError('SCHEMA_REQUIRED: ' + SCRATCH)
    yield 'truncate-intermediate-before', snapshot(state)
    if len(last_batch_run) > 1:
        raise ValueError('SCALAR_SUBQUERY_MULTIPLE_ROWS: LastBatchRunTbl')
    today = _date(_v(last_batch_run[0], 'LastRunDate')) if last_batch_run else None
    attributes = state['SkuLocAttributeData']
    for label, trends, black_field, br_field in (
            ('rm-tech', buffer_trend_report, 'c12', 'c13'),
            ('rm-econ', buffer_trend_report_econ, 'c9', 'c10')):
        state['IntermediateTables'][SCRATCH] = _colour_rows(trends, buffer_trend_dates, equal)
        yield label + '-insert-colors', snapshot(state)
        for step in range(1, 4):
            _fill_pass(state['IntermediateTables'][SCRATCH], equal)
            yield label + '-fill-' + str(step), snapshot(state)
        for field, eligible in ((black_field, ('Black',)), (br_field, ('Black', 'Red'))):
            _assign(attributes, _ages(state['IntermediateTables'][SCRATCH], eligible, equal),
                    (('SKUCode', 'SKUCode'), ('LocCode', 'WhCode')), (field,), ('Age',), equal,
                    'RM PostBTR ' + field)
            yield label + '-update-' + field, snapshot(state)
        if label == 'rm-tech':
            state['IntermediateTables'][SCRATCH] = []
            yield 'rm-tech-truncate-colors', snapshot(state)
    history = state['FGTrendData']
    history[:] = [r for r in history if today is None or _date(r['ReportDate']) != today]
    yield 'fg-delete-today', snapshot(state)
    for current in req_calculation:
        for location in location_attributes:
            if not _join(current, location, (('WhCode', 'WhCode'),), equal):
                continue
            link = _v(location, 'c1')
            if link is None or _eq(link, '', equal):
                continue
            for child in req_calculation:
                if not (_join(current, child, (('SKUCode', 'SKUCode'), ('WhCode', 'ParentWhCode')), equal)
                        and _eq(_v(child, 'WhCode'), link, equal)):
                    continue
                for attr in importer_sku_loc_attributes:
                    if not (_join(current, attr, (('SKUCode', 'SKUCode'), ('WhCode', 'LocCode')), equal)
                            and _eq(_v(attr, 'FGRMFlag'), 'FG', equal)):
                        continue
                    if today is None:
                        raise ValueError('NONNULL_CONSTRAINT: FGTrendData.ReportDate')
                    row = {'CurrentNodeSKU': _text(_v(current, 'SKUCode'), 'vf_ReqCalculation.SKUCode', 50),
                           'CurrentNodeWhCode': _text(_v(current, 'WhCode'), 'vf_ReqCalculation.WhCode', 50),
                           'ChildNodeSKU': _text(_v(child, 'SKUCode'), 'vf_ReqCalculation.SKUCode', 50),
                           'ChildNodeWhCode': _text(_v(child, 'WhCode'), 'vf_ReqCalculation.WhCode', 50),
                           'ReportDate': today, 'TechPen': None, 'TechColor': None,
                           'EcoPen': None, 'EcoColor': None}
                    for field, source, source_field in (
                            ('CurrentNodeStock', current, 'Stock'), ('CurrentNodeGIT', current, 'GIT'),
                            ('ChildStock', child, 'Stock'), ('ChildGIT', child, 'GIT'),
                            ('ChildVN', child, 'VirtualNorm'), ('CurrentNodeNorm', current, 'Norm')):
                        row[field] = _int(_v(source, source_field), 'vf_ReqCalculation.' + source_field,
                                          nullable=source_field == 'VirtualNorm')
                    history.append(row)
    yield 'fg-insert-today', snapshot(state)
    for row in history:
        if today is not None and _date(row['ReportDate']) == today:
            row['TechPen'], row['EcoPen'] = _penetration(row, False), _penetration(row, True)
    yield 'fg-update-penetration', snapshot(state)
    for row in history:
        if today is not None and _date(row['ReportDate']) == today:
            row['TechColor'], row['EcoColor'] = _band(row['TechPen']), _band(row['EcoPen'])
    yield 'fg-update-colors', snapshot(state)
    if today is not None:
        cutoff = (date.fromisoformat(today) - timedelta(days=30)).isoformat()
        history[:] = [r for r in history if _date(r['ReportDate']) >= cutoff]
    yield 'fg-prune-history', snapshot(state)
    for label, color, black_field, br_field in (
            ('fg-tech', 'TechColor', 'c12', 'c13'), ('fg-econ', 'EcoColor', 'c9', 'c10')):
        state['IntermediateTables'][SCRATCH] = []
        yield label + '-truncate-colors', snapshot(state)
        state['IntermediateTables'][SCRATCH] = _fg_grid(history, buffer_trend_dates, today, color, equal)
        yield label + '-insert-colors', snapshot(state)
        for step in range(1, 4):
            _fill_pass(state['IntermediateTables'][SCRATCH], equal)
            yield label + '-fill-' + str(step), snapshot(state)
        for field, eligible in ((black_field, ('Black',)), (br_field, ('Black', 'Red'))):
            _fg_assign(attributes, history, bor_with_order_allocation,
                       _ages(state['IntermediateTables'][SCRATCH], eligible, equal),
                       field, eligible, equal)
            yield label + '-update-' + field, snapshot(state)
    for table, location, fields in (
            ('BPR_Table', 'WhCode', ('SKULocAttr9', 'SKULocAttr10', 'SKULocAttr12', 'SKULocAttr13')),
            ('BPRSkuLocAttributeData', 'LocCode', ATTRS),
            ('SupplierDispatchReq', 'WhCode', ('SKULocAtt09', 'SKULocAtt10', 'SKULocAtt12', 'SKULocAtt13')),
            ('DBMSkuLocAttributeData', 'LocCode', ATTRS), ('ImporterSkuLocAttributeData', 'LocCode', ATTRS),
            ('NMSAllItems', 'WhCode', ('SKULocAtt09', 'SKULocAtt10', 'SKULocAtt12', 'SKULocAtt13'))):
        _assign(state[table], attributes, (('SKUCode', 'SKUCode'), (location, 'LocCode')),
                fields, ATTRS, equal, 'PostBTR propagation ' + table)
        yield 'propagate-' + table, snapshot(state)
    state['IntermediateTables'] = {name: [] for name in intermediate_tables}
    yield 'truncate-intermediate-after', snapshot(state)


def post_btr_calculated_attributes(**populations_and_settings):
    """Return final independent populations; statement capture is optional."""
    return final_stage(post_btr_stages(**populations_and_settings))[-1][1]
