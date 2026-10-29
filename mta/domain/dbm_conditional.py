"""Conditional order/consumption recommendations, using explicit owned inputs."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext
import re
from mta.domain.complete_daily_scalars import ascii_equal

MULTIPLIERS = ('Norm1Increase_MultipleRLT', 'Norm2Decrease_MultipleRLT')
THRESHOLDS = ('Norm1IncreaseCountThreshold', 'Norm2DecreaseCountThreshold',
              'Norm2DecreaseDataPointPercent')


def enabled(settings):
    # Activation is COUNT = 1, including the canonical inactive duplicate case.
    return sum(ascii_equal(r['Parameter'], 'NormZeroOneRuleActive')
               and ascii_equal(r['Value'], '1') for r in settings) == 1


def integer(value):
    if type(value) is str:
        text = value.strip()
        if text and re.fullmatch(r'[+-]?[0-9]+', text) is None:
            raise ValueError('Conditional DBM integer conversion differs')
        value = int(text) if text else 0
    if type(value) is not int or not -(2**31) <= value < 2**31:
        raise ValueError('Conditional DBM signed32-bit integer required')
    return value


def scalar_setting(rows, name, *, percentage=False):
    values = [r['Value'] for r in rows if ascii_equal(r['Parameter'], name)]
    if len(values) > 1:
        raise ValueError('Conditional DBM scalar setting has multiple rows: ' + name)
    if not values or values[0] is None:
        return None  # Scalar assignment from zero rows is NULL, never a default.
    value = values[0]
    if not percentage:
        return integer(value)
    if type(value) is not str:
        raise ValueError('Conditional DBM percentage text required')
    text = value.strip()
    if text and re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)', text) is None:
        raise ValueError('Conditional DBM decimal conversion differs')
    with localcontext() as context:
        context.prec = 50
        result = Decimal(text or '0').quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
    if not result.is_finite() or abs(result) >= 10**10:
        raise ValueError('Conditional DBM decimal(13,3) overflow')
    return result


def configuration(batch, importer_vf_settings):
    if not isinstance(batch, dict) or any(name not in batch for name in MULTIPLIERS):
        raise ValueError('Explicit conditional DBM RLT multipliers required')
    validate_settings_rows(importer_vf_settings)
    for name in MULTIPLIERS:
        if type(batch[name]) is not int:
            raise ValueError('Explicit integer conditional RLT multiplier required')
        integer(batch[name])
    for name in THRESHOLDS:
        scalar_setting(importer_vf_settings, name, percentage=name.endswith('Percent'))


def validate_settings_rows(rows):
    """Exact projected Importer table columns, NOT NULL and UTF16 widths."""
    from mta.application.accepted_inputs import accepted
    if accepted():
        return
    widths = {'Parameter': 50, 'Value': 50, 'Description': 200}
    if not isinstance(rows, list):
        raise ValueError('Explicit Importer conditional VFSettings bag required')
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(widths):
            raise ValueError('Complete Importer VFSettings fields required')
        for name, width in widths.items():
            if type(row[name]) is not str or '\0' in row[name] or len(row[name].encode('utf-16-le')) > 2*width:
                raise ValueError('Importer VFSettings NOT NULL text/width differs: '+name)


def _today(today, state):
    today = date.fromisoformat(today) if type(today) is str else today
    if type(today) is not date or state['LastBatchRunTbl'] != [{'LastRunDate': today.isoformat()+'T00:00:00'}]:
        raise ValueError('Conditional DBM singleton midnight business date required')
    return today


def _date(value):
    return date.fromisoformat(value) if type(value) is str else value


def _key(row, location='WhCode'):
    values = (row['SKUCode'], row[location])
    for value in values:
        if value is not None:
            ascii_equal(value, value)
    return tuple(value.rstrip(' ').upper() if value is not None else None for value in values)


def _index(rows):
    result = {}
    for row in rows:
        key = _key(row)
        if None not in key:
            result.setdefault(key, []).append(row)
    return result


def _sum(values):
    values = [integer(value) for value in values if value is not None]
    return integer(sum(values)) if values else None


def _cutoff(today, period):
    if period is None:
        return None
    period = integer(period)
    integer(-period)
    return today - timedelta(days=period)


def _after(day, cutoff):
    return day is not None and cutoff is not None and _date(day) >= _date(cutoff)


def _scratch(state, populations=None):
    rows = [{'table': r['table'], 'rows': []} for r in state['IntermediateTables']]
    for name, values in (populations or {}).items():
        target = next((r for r in rows if r['table'] == 'dbo.'+name), None)
        if target is None:
            target = dict(table='dbo.'+name, rows=[])
            rows.append(target)
        target['rows'] = deepcopy(values)
    return rows


def order_norm_zero_increase(today, state):
    """Order counts roll upward; the recommendation uses the node's own ratio."""
    today = _today(today, state)
    result = deepcopy(state)
    result['Suggestions'] = [r for r in result['Suggestions'] if r['Type'] is None or r['Type'] < 7]
    summary = [dict(SKUCode=m['SKUCode'], WhCode=m['WhCode'], NodeOrderCount=0,
        CummOrderCount=0, NodeConsumption=0, OCPStartDate=_cutoff(today, m['OCP']).isoformat(),
        ConsumptionStartDate=None, StartingStock=None) for m in state['DBMMaster']
        if m['Norm'] == 0 and m['OCP'] is not None]
    result['OrderRuleSummary'] = summary
    daily, members, masters, orders = (_index(state[n]) for n in
        ('DailyConsumption', 'SuspendOrderType', 'DBMMaster', 'OrderData'))
    summaries = _index(summary)
    for key, nodes in summaries.items():
        starts = [_date(f['ReportDate']) for f in daily.get(key, []) for b in members.get(key, [])
            for node in nodes if f['Stock'] is not None and _after(f['ReportDate'], node['OCPStartDate'])
            and _after(f['ReportDate'], b['RedResumeDate'])]
        start = min(starts) if starts else None
        stocks = [f['Stock'] for f in daily.get(key, []) if start is not None and _date(f['ReportDate']) == start]
        if len(set(stocks)) > 1:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: conditional starting-stock update')
        count = integer(sum(1 for o in orders.get(key, []) for b in members.get(key, []) for m in masters.get(key, [])
            if _after(o['ImportDate'], b['RedResumeDate']) and _after(o['ImportDate'], _cutoff(today, m['OCP']))))
        consumed = [f['Consumption'] for f in daily.get(key, []) if _after(f['ReportDate'], start)]
        total = _sum(consumed)
        total = None if total is None else integer(total * len(nodes))
        for node in nodes:
            node['ConsumptionStartDate'] = start.isoformat() if start is not None else None
            node['StartingStock'] = stocks[0] if stocks else None
            if count:
                node['NodeOrderCount'] = node['CummOrderCount'] = count
            if consumed:
                node['NodeConsumption'] = total
    hierarchy = [{n: m[n] for n in ('SKUCode', 'WhCode', 'ParentWhCode')} for m in state['DBMMaster']]
    leaf = []
    counter = 0
    while hierarchy and counter < 100:
        parents = {_key(r, 'ParentWhCode') for r in hierarchy if None not in _key(r, 'ParentWhCode')}
        leaf = [r for r in hierarchy if _key(r) not in parents or None in _key(r)]
        totals = {}
        for row in leaf:
            parent = _key(row, 'ParentWhCode')
            if None not in parent:
                values = [n['CummOrderCount'] for n in summaries.get(_key(row), [])]
                if values:
                    totals.setdefault(parent, []).extend(values)
        for parent, values in totals.items():
            for node in summaries.get(parent, []):
                child_count = _sum(values)
                node['CummOrderCount'] = (None if node['CummOrderCount'] is None or child_count is None
                                          else integer(node['CummOrderCount'] + child_count))
        removed = {_key(r) for r in leaf if None not in _key(r)}
        hierarchy = [r for r in hierarchy if _key(r) not in removed]
        counter += 1
    populations = dict(ParentHeirarchy=hierarchy, LeafNode=leaf, ImageOrderRuleSummary=[])
    result['IntermediateTables'] = _scratch(state, populations)
    if counter >= 100:
        return result  # Source-defined return retains partial roll-up and scratch.
    images = []
    prior = _index(result['Suggestions'])
    for node in summary:
        if node['NodeConsumption'] is None or node['StartingStock'] is None or node['NodeConsumption'] <= node['StartingStock']:
            continue
        key = _key(node)
        if any(b['RedEnabled'] == 0 for b in members.get(key, [])) or key in prior:
            continue
        if any(m['MinOrderCount'] is not None and node['CummOrderCount'] is not None
               and node['CummOrderCount'] < m['MinOrderCount'] for m in masters.get(key, [])):
            continue
        images.append(node)
    for node in images:
        consumption, count = node['NodeConsumption'], node['NodeOrderCount']
        if consumption != 0 and count != 0:
            # CEILING of the source's signed integer ratio, without float loss.
            new_norm = integer(-(-consumption // count))
            result['Suggestions'].append(dict(SKUCode=node['SKUCode'], WhCode=node['WhCode'], Type=7, NewNorm=new_norm))
    result['IntermediateTables'] = _scratch(result)
    return result


def _periods(state, norm, multiple):
    multiple = integer(multiple)
    return [{**m, 'CheckPeriod': None if m['RLT'] is None else integer(multiple * integer(m['RLT']))}
            for m in state['DBMMaster'] if m['Norm'] == norm]


def _groups(today, state, candidates, resume_field):
    masters, members = _index(candidates), _index(state['SuspendOrderType'])
    groups, spellings = {}, {}
    for fact in state['DailyConsumption']:
        key = _key(fact)
        for member in members.get(key, []):
            for master in masters.get(key, []):
                if not (_after(fact['ReportDate'], member[resume_field])
                        and _after(fact['ReportDate'], _cutoff(today, master['CheckPeriod']))):
                    continue
                spelling = fact['SKUCode'], fact['WhCode']
                if key in spellings and spelling != spellings[key]:
                    raise ValueError('SOURCE_ORDER_AMBIGUITY: conditional grouped key spelling')
                spellings[key] = spelling
                group = groups.setdefault(key, dict(sales=0, stockouts=0, points=0, period=None))
                group['sales'] += fact['Consumption'] is not None and fact['Consumption'] > 0
                group['stockouts'] += fact['Stock'] == 0
                group['points'] += 1
                period = master['CheckPeriod']
                if period is not None:
                    group['period'] = period if group['period'] is None else max(group['period'], period)
    return [(spellings[key], values) for key, values in groups.items()]


def norm_one_consumption_increase(today, state, *, multiple_rlt, importer_vf_settings):
    today = _today(today, state)
    threshold = scalar_setting(importer_vf_settings, THRESHOLDS[0])
    result = deepcopy(state)
    result['Suggestions'] = [r for r in result['Suggestions'] if r['Type'] is None or r['Type'] < 10]
    prior, members = _index(result['Suggestions']), _index(state['SuspendOrderType'])
    candidates = [m for m in _periods(state, 1, multiple_rlt) if _key(m) not in prior
                  and not any(b['RedEnabled'] == 0 for b in members.get(_key(m), []))]
    for (sku, wh), values in _groups(today, state, candidates, 'RedResumeDate'):
        count = integer(values['sales'])
        if threshold is not None and count >= threshold:
            result['Suggestions'].append(dict(SKUCode=sku, WhCode=wh, Type=10, NewNorm=2))
    result['IntermediateTables'] = _scratch(result)
    return result


def norm_two_consumption_decrease(today, state, *, multiple_rlt, importer_vf_settings):
    today = _today(today, state)
    threshold = scalar_setting(importer_vf_settings, THRESHOLDS[1])
    percentage = scalar_setting(importer_vf_settings, THRESHOLDS[2], percentage=True)
    result = deepcopy(state)
    result['Suggestions'] = [r for r in result['Suggestions'] if r['Type'] is None or r['Type'] < 11]
    candidates = _periods(state, 2, multiple_rlt)
    twos = _index(candidates)
    result['Suggestions'] = [r for r in result['Suggestions'] if not (r['NewNorm'] == 2 and _key(r) in twos)]
    prior, members = _index(result['Suggestions']), _index(state['SuspendOrderType'])
    candidates = [m for m in candidates if _key(m) not in prior
                  and not any(b['GreenEnabled'] == 0 for b in members.get(_key(m), []))]
    for (sku, wh), values in _groups(today, state, candidates, 'GreenResumeDate'):
        count, stockouts, points = (integer(values[n]) for n in ('sales', 'stockouts', 'points'))
        period = values['period']
        if threshold is not None and percentage is not None and period is not None and count < threshold and stockouts == 0 and points >= period*percentage/100:
            result['Suggestions'].append(dict(SKUCode=sku, WhCode=wh, Type=11, NewNorm=1))
    result['IntermediateTables'] = _scratch(result)
    return result
