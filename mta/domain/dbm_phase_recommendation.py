"""Computed phase recommendations; no phase workflow or Norm change is applied.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date
from itertools import product
from mta.domain.dbm_report_dates import report_cutoff
from mta.domain.complete_daily_scalars import ascii_equal
from mta.domain.ordinal_lookup import OrderedIndex

HORIZONS = (30, 60, 90)
TOLERANCES = tuple(f'PhaseOutRecommendationTolerance{h}Days' for h in HORIZONS)
FIELDS = ('SKUCode', 'SKUName', 'WhCode', 'WHName', 'StockDays', 'TotalSale',
          'CurrentNorm', 'CurrentStock') + tuple(
    f'{prefix}{index:02}' for prefix in ('SKUAtt', 'LocAtt', 'SKULocAtt') for index in range(1, 16))


def integer(value, label):
    if type(value) is not int or not -(2**31) <= value < 2**31:
        raise ValueError('Phase recommendation signed32 integer required: '+label)
    return value


def configuration(batch):
    if not isinstance(batch, dict):
        raise ValueError('Explicit phase recommendation configuration required')
    for horizon, tolerance in zip(HORIZONS, TOLERANCES):
        flag = batch.get(f'PhaseOutRecommendation{horizon}Days')
        if type(flag) is not int or flag not in (0, 1):
            raise ValueError('Explicit phase recommendation flag0/1 required')
        if flag == 1:
            integer(batch.get(tolerance), tolerance)
            integer(horizon-batch[tolerance], 'horizon minus tolerance')


def identity(value):
    if value is None:
        return None
    ascii_equal(value, value)  # Deny unqualified collations, not a new locale rule.
    return value.rstrip(' ').upper()


def pair(row, loc='WhCode'):
    sku, wh = identity(row['SKUCode']), identity(row[loc])
    return None if sku is None or wh is None else (sku, wh)


def row_date(value):
    return date.fromisoformat(value) if type(value) is str else value


def text(value):
    return None if value is None else value.replace(',', '')


def validate_target(row):
    from mta.application.accepted_inputs import accepted
    if accepted():
        return
    for name in FIELDS:
        value = row[name]
        if name in ('StockDays', 'TotalSale', 'CurrentNorm', 'CurrentStock'):
            if value is not None:
                integer(value, name)
        else:
            width = 250 if name in ('SKUName', 'WHName') else 100
            if value is None:
                if name in ('SKUCode', 'WhCode'):
                    raise ValueError('Phase recommendation NOT NULL identifier required')
            elif type(value) is not str or '\0' in value or len(value.encode('utf-16-le')) > width:
                raise ValueError('Phase recommendation target text width/type differs: '+name)


def phase_recommendation(today, state, horizon, tolerance):
    if horizon not in HORIZONS:
        raise ValueError('Phase recommendation horizon30/60/90 required')
    integer(tolerance, 'tolerance')
    threshold = integer(horizon-tolerance, 'horizon minus tolerance')
    cutoff = report_cutoff(today, state, horizon, inclusive=False)
    today = row_date(today)
    excluded = {identity(row['SKUCode']) for name in ('PhaseInTbl', 'PhaseOutTbl') for row in state[name]}
    groups = {}
    first = True
    with OrderedIndex(state['DailyConsumption']) as daily_index:
        for master in state['DBMMaster']:
            key = pair(master)
            if key is None or master['Norm'] is None or master['Norm'] <= 0 or key[0] in excluded:
                continue
            candidates = state['DailyConsumption'] if first else daily_index.candidates((master['SKUCode'], master['WhCode']))
            currents = [row['Stock'] for row in candidates if pair(row)==key
                        and row_date(row['ReportDate']) == today] or [None]
            candidates = state['DailyConsumption'] if first else daily_index.candidates((master['SKUCode'], master['WhCode']))
            for fact in candidates:
                day = row_date(fact['ReportDate'])
                if pair(fact)!=key or day is None or day <= cutoff:
                    continue
                for stock in currents:
                    group_key = (*key, master['Norm'], stock)
                    spelling = (master['SKUCode'], master['WhCode'])
                    if group_key not in groups:
                        groups[group_key] = dict(spelling=spelling, sales=[], stock_days=0)
                    group = groups[group_key]
                    if group['spelling'] != spelling:
                        raise ValueError('SOURCE_ORDER_AMBIGUITY: grouped phase identifier spelling')
                    if fact['Consumption'] is not None:
                        group['sales'].append(integer(fact['Consumption'], 'Consumption'))
                    group['stock_days'] += int(fact['Stock'] is not None and fact['Stock'] > 0)
            # The first eligible master's original passes validate all keys and
            # dates in their original order, including unrelated observations.
            first = False
    rows = []
    with ExitStack() as stack:
        indexes = {name:stack.enter_context(OrderedIndex(state[name], key=key)) for name,key in (
            ('SKUDescriptionTbl',lambda r:(r['SKUCode'],)), ('SiteDescriptionTbl',lambda r:(r['WHCode'],)),
            ('SkuAttributeData',lambda r:(r['SKUCode'],)), ('LocationAttributeData',lambda r:(r['WHCode'],)),
            ('SkuLocAttributeData',lambda r:(r['SKUCode'],r['LocCode'])))}
        for (sku, wh, norm, current_stock), group in groups.items():
            sales = group['sales']
            # SUM(int) excludes NULL and returns NULL for an all-NULL group. Retain
            # overflow denial without choosing an unordered cancellation policy.
            for subtotal in (sum(v for v in sales if v>0), sum(v for v in sales if v<0)):
                integer(subtotal, 'consumption subtotal')
            total = integer(sum(sales), 'TotalSale') if sales else None
            count = integer(group['stock_days'], 'StockDays')
            if total is None or total >= 1 or count < threshold:
                continue
            matches = (
                [r for r in indexes['SKUDescriptionTbl'].candidates((sku,)) if identity(r['SKUCode']) == sku],
                [r for r in indexes['SiteDescriptionTbl'].candidates((wh,)) if identity(r['WHCode']) == wh],
                [r for r in indexes['SkuAttributeData'].candidates((sku,)) if identity(r['SKUCode']) == sku],
                [r for r in indexes['LocationAttributeData'].candidates((wh,)) if identity(r['WHCode']) == wh],
                [r for r in indexes['SkuLocAttributeData'].candidates((sku,wh)) if pair(r, 'LocCode') == (sku, wh)])
            for description, site, sku_attributes, loc_attributes, pair_attributes in product(*matches):
                row = dict(SKUCode=group['spelling'][0], SKUName=text(description['SKUDescription']),
                    WhCode=group['spelling'][1], WHName=text(site['WHDescription']), StockDays=count,
                    TotalSale=total, CurrentNorm=norm, CurrentStock=current_stock)
                for prefix, attributes in (('SKUAtt', sku_attributes), ('LocAtt', loc_attributes), ('SKULocAtt', pair_attributes)):
                    row.update({f'{prefix}{index:02}':text(attributes[f'c{index}']) for index in range(1,16)})
                validate_target(row)
                rows.append(row)
    result = deepcopy(state)
    result['PhaseOutRecommendation'] = rows
    return result


def phase_stages(today, state, batch):
    configuration(batch)
    current = state
    for horizon, tolerance in zip(HORIZONS, TOLERANCES):
        if batch[f'PhaseOutRecommendation{horizon}Days'] == 1:
            current = phase_recommendation(today, current, horizon, batch[tolerance])
            yield f'phase-recommendation-{horizon}', current
