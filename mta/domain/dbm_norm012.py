"""Selected Norm0/1/2 report stages; unordered source outcomes are not invented.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from collections import defaultdict
from contextlib import ExitStack
from copy import deepcopy
from datetime import date, timedelta
from itertools import product
from mta.domain.sql_identity_keys import join_key, row_join_key, value_join_key
from mta.domain.ordinal_lookup import OrderedIndex

BUSINESS_TABLES = ('DBMMaster', 'DailyConsumption', 'LastBatchRunTbl',
                   'SKUDescriptionTbl', 'SiteDescriptionTbl', 'SkuAttributeData',
                   'SkuLocAttributeData', 'LocationAttributeData',
                   'Norm0Norm1Norm2Report', 'Norm0_1_2ReportDetails', 'ui_ReportConfigurations')

NORM0_EXPORT_STAGES = {30: 'norm0-export', 60: 'norm0-60-export', 90: 'norm0-90-export'}
CHRONOLOGICAL_RULE = 'production-norm0-date-ascending-source-ties-v1'


def report_stage(norm, horizon, step):
    if norm==0 and horizon in (60,90):
        return f'norm0-{horizon}-{step}'
    return f'norm{norm}-{step}'


def report_int(value,name):
    if type(value) is not int or not -2147483648<=value<=2147483647:
        raise ValueError('Norm0 '+name+' requires a non-NULL signed32-bit integer')
    return value


def report_total(rows):
    # Retain the source's inner SUM(int) per quantity, followed by outer SUM(int)
    # and NOT NULL report assignment. No widened/zero-default aggregate output.
    groups=defaultdict(int)
    for row in rows:
        value=row['Consumption']
        if value is not None:
            report_int(value,'Consumption')
            groups[value]+=value
    for value in groups.values():report_int(value,'consumption group sum')
    total=sum(groups.values()) if groups else None
    report_int(total,'TotalSale')
    # Without a declared numeric group order, do not bless cancellation that
    # might overflow an intermediate source accumulator. No sort is invented.
    report_int(sum(v for v in groups.values() if v>0),'positive subtotal')
    report_int(sum(v for v in groups.values() if v<0),'negative subtotal')
    return total


class AmbiguousReport(ValueError):
    pass


def _day(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def data_stage(today, state, norm, horizon, occurrence_order_exclusions=(),
               exclude_all_occurrence_order=False):
    chronological=norm==0 and horizon in (60,90)
    if norm not in (0, 1, 2) or not (horizon==30 or chronological):
        raise ValueError('Selected report requires Norm0 horizon30/60/90 or Norm1/2 horizon30')
    if chronological and (occurrence_order_exclusions or exclude_all_occurrence_order):
        raise ValueError('Chronological production report cannot use occurrence exclusions')
    today = _day(today)
    if state['LastBatchRunTbl'] != [{'LastRunDate': today.isoformat() + 'T00:00:00'}]:
        raise ValueError('Selected report requires singleton midnight run date')
    out = deepcopy(state)
    image = defaultdict(list)
    image_spelling = {}
    with OrderedIndex(state['SKUDescriptionTbl'], key=lambda r:(r['SKUCode'],)) as description_index:
        for master in state['DBMMaster']:
            if master['Norm'] == norm:
                if not state['SKUDescriptionTbl']:continue
                # This validation preceded the description equality in the source.
                key = row_join_key(master)
                for description in description_index.candidates((master['SKUCode'],)):
                    key = row_join_key(master)
                    if value_join_key(master['SKUCode']) == value_join_key(description['SKUCode']):
                        spelling=master['SKUCode'],master['WhCode']
                        if key in image_spelling and image_spelling[key]!=spelling:
                            raise AmbiguousReport('Conflicting Norm0/1/2 grouped key spelling')
                        image_spelling[key]=spelling
                        image[key].append(description['SKUDescription'])
    observations = defaultdict(list)
    for row in state['DailyConsumption']:
        key = row_join_key(row)
        if any(value is None for value in key):
            continue  # SQL equality joins do not match NULL keys.
        if row['ReportDate'] is None:
            continue  # SQL WHERE denies NULL dates; no invented date.
        if _day(row['ReportDate']) > today - timedelta(days=horizon):
            observations[key].extend([row] * len(image[key]))
    excluded = {join_key(*key) for key in occurrence_order_exclusions if None not in key}
    result = []
    for key, rows in observations.items():
        if not rows:
            continue
        positive = [r for r in rows if r['Consumption'] is not None
                    and r['Consumption'] > 0]
        if chronological:
            # Approved60/90 production rule, not canonical unordered text parity.
            # Python's stable sort retains supplied order for equal dates, and
            # the joined list retains every duplicate fragment.
            positive=sorted(positive,key=lambda r:_day(r['ReportDate']))
        fragments = ['[' + _day(r['ReportDate']).strftime('%d/%m/%y') + ' - '
                     + str(r['Consumption']) + ']' for r in positive]
        ambiguous = not chronological and len(set(fragments)) > 1
        if ambiguous and not exclude_all_occurrence_order and key not in excluded:
            raise AmbiguousReport('Unordered occurrence STRING_AGG has distinct fragments')
        # Both source branches use SUM(int), ignoring NULL inputs. An all-NULL
        # group still fails the native NOT NULL TotalSale target; never seed 0.
        total=report_total(rows)
        report_int(len(positive),'Count')
        sku,loc=image_spelling[key]
        for description in image[key]:
            result.append({'SKUCode': sku, 'WHCode': loc, 'Count': len(positive),
                           'Occurances': None if ambiguous else ', '.join(fragments),
                           'TotalSale': total,
                           'SKUName': description if description is not None else '-'})
    out['Norm0Norm1Norm2Report'] = result
    out['IntermediateTables'] = [{'table': row['table'], 'rows': []} for row in state['IntermediateTables']]
    return out


def detail_stage(state):
    out = deepcopy(state)
    result = []
    if not state['Norm0Norm1Norm2Report']:
        out['Norm0_1_2ReportDetails'] = result
        return out
    with ExitStack() as stack:
        indexes = {name:stack.enter_context(OrderedIndex(state[name],key=key)) for name,key in (
            ('SkuAttributeData',lambda r:(r['SKUCode'],)), ('SkuLocAttributeData',lambda r:(r['SKUCode'],r['LocCode'])),
            ('LocationAttributeData',lambda r:(r['WHCode'],)), ('SiteDescriptionTbl',lambda r:(r['WHCode'],)),
            ('DBMMaster',lambda r:(r['SKUCode'],r['WhCode'])))}
        for row in state['Norm0Norm1Norm2Report']:
            sku, loc = row['SKUCode'], row['WHCode']
            key=join_key(sku,loc)
            matches = [
                [v for v in indexes['SkuAttributeData'].candidates((sku,)) if value_join_key(v['SKUCode']) == value_join_key(sku)] or [None],
                [v for v in indexes['SkuLocAttributeData'].candidates((sku,loc)) if join_key(v['SKUCode'], v['LocCode']) == key] or [None],
                [v for v in indexes['LocationAttributeData'].candidates((loc,)) if value_join_key(v['WHCode']) == value_join_key(loc)] or [None],
                [v for v in indexes['SiteDescriptionTbl'].candidates((loc,)) if value_join_key(v['WHCode']) == value_join_key(loc)] or [None],
                [v for v in indexes['DBMMaster'].candidates((sku,loc)) if row_join_key(v) == key] or [None],
            ]
            for sa, sla, la, site, master in product(*matches):
                parent = master['ParentWhCode'] if master else None
                norms = {v['Norm'] for v in (indexes['DBMMaster'].candidates((sku,parent)) if parent is not None else ())
                         if parent is not None and join_key(v['SKUCode'],v['WhCode'])==join_key(sku,parent)}
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


def selected_report_configuration(rows):
    """The existing export layout gate, shared with input preflight."""
    config = [r for r in rows if r['ReportName'] == 'Norm_0_1_2Report']
    visible = sorted((r for r in config if r['Visible']), key=lambda r: r['Col_Position'])
    if len({r['Col_Code'] for r in config}) != len(config) or len({r['Col_Position'] for r in visible}) != len(visible):
        raise AmbiguousReport('Report configuration columns/positions are not unique')
    selected = ['SKUCode', 'SKUName', 'WHCode', 'WhName', 'ParentWhCode', 'ParentNorm', 'NumOfDaysSold', 'TotalSale', 'Occurances']
    if [r['Col_Code'] for r in visible] != selected:
        raise ValueError('Different report configuration requires its own selected contract')
    return visible


def export_stage(state):
    out = deepcopy(state)
    visible = selected_report_configuration(state['ui_ReportConfigurations'])
    selected = [r['Col_Code'] for r in visible]
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
                   exclude_all_occurrence_order=False, *, _defer_export=False):
    current = data_stage(today, state, norm, horizon, occurrence_order_exclusions,
                         exclude_all_occurrence_order)
    yield 'data', current
    current = detail_stage(current)
    yield 'detail', current
    if _defer_export:
        from mta.domain.deferred_dbm_exports import defer
        current = defer(today,current,'norm012')
    else:
        current = export_stage(current)
    yield 'export', current
    current = clear_stage(current)
    yield 'clear', current


def norm012_report(today, state, norm, horizon):
    for _, current in norm012_stages(today, state, norm, horizon):
        pass
    return current
