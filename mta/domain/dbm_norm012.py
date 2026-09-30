"""Selected Norm0/1/2 report stages; unordered source outcomes are not invented."""
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from itertools import product

BUSINESS_TABLES = ('DBMMaster', 'DailyConsumption', 'LastBatchRunTbl',
                   'SKUDescriptionTbl', 'SiteDescriptionTbl', 'SkuAttributeData',
                   'SkuLocAttributeData', 'LocationAttributeData',
                   'Norm0Norm1Norm2Report', 'Norm0_1_2ReportDetails', 'ui_ReportConfigurations')


class AmbiguousReport(ValueError):
    pass


def _day(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def data_stage(today, state, norm, horizon, occurrence_order_exclusions=(),
               exclude_all_occurrence_order=False):
    if norm not in (0, 1, 2) or horizon != 30:
        raise ValueError('Selected report requires Norm0/1/2 and horizon30')
    today = _day(today)
    if state['LastBatchRunTbl'] != [{'LastRunDate': today.isoformat() + 'T00:00:00'}]:
        raise ValueError('Selected report requires singleton midnight run date')
    out = deepcopy(state)
    image = defaultdict(list)
    for master in state['DBMMaster']:
        if master['Norm'] == norm:
            for description in state['SKUDescriptionTbl']:
                if master['SKUCode'] == description['SKUCode']:
                    image[master['SKUCode'], master['WhCode']].append(description['SKUDescription'])
    observations = defaultdict(list)
    for row in state['DailyConsumption']:
        key = row['SKUCode'], row['WhCode']
        if _day(row['ReportDate']) > today - timedelta(days=horizon):
            observations[key].extend([row] * len(image[key]))
    excluded = {tuple(key) for key in occurrence_order_exclusions}
    result = []
    for key, rows in observations.items():
        if not rows:
            continue
        positive = [r for r in rows if r['Consumption'] > 0]
        fragments = ['[' + _day(r['ReportDate']).strftime('%d/%m/%y') + ' - '
                     + str(r['Consumption']) + ']' for r in positive]
        ambiguous = len(set(fragments)) > 1
        if ambiguous and not exclude_all_occurrence_order and key not in excluded:
            raise AmbiguousReport('Unordered occurrence STRING_AGG has distinct fragments')
        for description in image[key]:
            result.append({'SKUCode': key[0], 'WHCode': key[1], 'Count': len(positive),
                           'Occurances': None if ambiguous else ', '.join(fragments),
                           'TotalSale': sum(r['Consumption'] for r in rows),
                           'SKUName': description if description is not None else '-'})
    out['Norm0Norm1Norm2Report'] = result
    out['IntermediateTables'] = [{'table': row['table'], 'rows': []} for row in state['IntermediateTables']]
    return out


def detail_stage(state):
    out = deepcopy(state)
    result = []
    for row in state['Norm0Norm1Norm2Report']:
        sku, loc = row['SKUCode'], row['WHCode']
        matches = [
            [v for v in state['SkuAttributeData'] if v['SKUCode'] == sku] or [None],
            [v for v in state['SkuLocAttributeData'] if (v['SKUCode'], v['LocCode']) == (sku, loc)] or [None],
            [v for v in state['LocationAttributeData'] if v['WHCode'] == loc] or [None],
            [v for v in state['SiteDescriptionTbl'] if v['WHCode'] == loc] or [None],
            [v for v in state['DBMMaster'] if (v['SKUCode'], v['WhCode']) == (sku, loc)] or [None],
        ]
        for sa, sla, la, site, master in product(*matches):
            parent = master['ParentWhCode'] if master else None
            norms = {v['Norm'] for v in state['DBMMaster']
                     if v['SKUCode'] == sku and parent is not None and v['WhCode'] == parent}
            if len(norms) > 1:
                raise AmbiguousReport('Conflicting parent Norm UPDATE')
            detail = {'SKUCode': sku, 'SKUName': row['SKUName'], 'WhCode': loc,
                      'WhName': site['WHDescription'] if site else None,
                      'ParentWhCode': parent, 'ParentNorm': next(iter(norms), None),
                      'NumOfDaysSold': row['Count'], 'TotalSale': row['TotalSale'],
                      'Occurances': row['Occurances'][:255] if row['Occurances'] is not None else None}
            for prefix, attrs in (('SKUAttr', sa), ('SKULocAttr', sla), ('LocAttr', la)):
                detail.update({prefix + str(i): attrs['c' + str(i)] if attrs else None for i in range(1, 16)})
            result.append(detail)
    out['Norm0_1_2ReportDetails'] = result
    return out


def _quote(value):
    if value is None or len(value.encode('utf-16-le')) // 2 > 128:
        return ' '
    return '"' + value.replace('"', '""') + '"'


def export_stage(state):
    out = deepcopy(state)
    config = [r for r in state['ui_ReportConfigurations'] if r['ReportName'] == 'Norm_0_1_2Report']
    visible = sorted((r for r in config if r['Visible']), key=lambda r: r['Col_Position'])
    if len({r['Col_Code'] for r in config}) != len(config) or len({r['Col_Position'] for r in visible}) != len(visible):
        raise AmbiguousReport('Report configuration columns/positions are not unique')
    selected = ['SKUCode', 'SKUName', 'WHCode', 'WhName', 'ParentWhCode', 'ParentNorm', 'NumOfDaysSold', 'TotalSale', 'Occurances']
    if [r['Col_Code'] for r in visible] != selected:
        raise ValueError('Different report configuration requires its own selected contract')
    out['ReportHeader'] = [{'values': [r['Header'] for r in visible]}]
    rows = []
    for detail in state['Norm0_1_2ReportDetails']:
        values = []
        for name in selected:
            value = detail['WhCode' if name == 'WHCode' else name]
            values.append(_quote(value) if name in ('SKUName', 'WhName', 'Occurances')
                          else ' ' if value is None else str(value).replace(',', ' '))
        rows.append({'values': values})
    out['ReportRows'] = rows
    return out


def clear_stage(state):
    out = deepcopy(state)
    out['Norm0Norm1Norm2Report'] = []
    out['Norm0_1_2ReportDetails'] = []
    return out


def norm012_stages(today, state, norm, horizon, occurrence_order_exclusions=(),
                   exclude_all_occurrence_order=False):
    current = data_stage(today, state, norm, horizon, occurrence_order_exclusions,
                         exclude_all_occurrence_order)
    yield 'data', deepcopy(current)
    current = detail_stage(current)
    yield 'detail', deepcopy(current)
    current = export_stage(current)
    yield 'export', deepcopy(current)
    current = clear_stage(current)
    yield 'clear', deepcopy(current)


def norm012_report(today, state, norm, horizon):
    stages = list(norm012_stages(today, state, norm, horizon))
    return {**stages[-1][1], 'ReportStages': [{'stage': name, 'state': value} for name, value in stages]}
