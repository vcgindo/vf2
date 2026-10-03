"""Selected GuidedInsightsProcessor projections over persisted BTR tables.

Joins keep bag multiplicity. Callers apply permissions and filters to joined
rows before aggregation. SQL FOR JSON omits NULL properties.
"""
from collections import defaultdict
from itertools import product
from decimal import Decimal


def _key(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode', row.get('LocCode')))


def _native_index(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[key(row)].append(row)
    return result


def availability_rows(btr, *, filter_owners=False):
    """GetAvailabilityTrend's attribute joins over the computed BPR history."""
    result = []
    skus = _native_index(btr['SkuAttributeData'], lambda r: r['SKUCode'])
    locations = _native_index(btr['LocationAttributeData'], lambda r: r['WHCode'])
    pairs = _native_index(btr['SkuLocAttributeData'], _key)
    for row in btr['BPR']:
        sku, loc = _key(row)
        for sa, la, sla in product(
                skus.get(sku, []), locations.get(loc, []),
                pairs.get((sku, loc), []) or [{}]):
            value = {**row, **la, 'WhCode': loc}
            value.update({f'SKUAttribute{i}': sa.get(f'c{i}') for i in range(1, 16)})
            value.update({f'LocAttribute{i}': la.get(f'c{i}') for i in range(1, 16)})
            value.update({f'SkuLocAttribute{i}': sla.get(f'c{i}') for i in range(1, 16)})
            if filter_owners:
                value.update(_a=row, _sku=sa, _location=la, _pair=sla)
            result.append(value)
    return result


def availability_trend(rows):
    """Pinned SQL groups by ReportDate and counts every non-Black colour."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row['ReportDate'], row.get('LocationType'))].append(row['PhysicalInventoryColor'])
    result = []
    for (day, location_type), colours in groups.items():
        count = sum(c is not None for c in colours)
        if count:
            item = {'week': day, 'percentage': int(Decimal(sum(c is not None and c != 'Black' for c in colours)) / count * 100)}
            if location_type is not None:
                item['locationtype'] = location_type
            result.append(item)
    return sorted(result, key=lambda r: r['week'])


def availability_ageing(rows, snapshots, minimum_age, *, predicate=None):
    """The current snapshot age qualifies all selected history for that key."""
    groups = defaultdict(list)
    by_pair = _native_index(snapshots, _key)
    for row in rows:
        for snapshot in by_pair.get(_key(row), []):
            if (snapshot['AgePhysicalInv'] is not None
                    and snapshot['AgePhysicalInv'] >= minimum_age):
                multiplicity = predicate({**row, '_snapshot': snapshot}) if predicate else 1
                if multiplicity:
                    groups[row['ReportDate']].extend([row['PhysicalInventoryColor']] * multiplicity)
    return [{'date': day, 'black': colours.count('Black'),
             'red': colours.count('Red'), 'white': colours.count('White')}
            for day, colours in sorted(groups.items())]


def joined_rows(btr, dbm, kind, *, filter_owners=False):
    table = 'ChronicUnavalabilityData' if kind.startswith('chronic') else 'DBMNormSuggestionsData'
    chronic_loc = None
    if kind == 'chronic-loc':
        chronic_loc = dict(
            skus=_native_index(btr['SkuAttributeData'], lambda r: r['SKUCode']),
            locations=_native_index(btr['LocationAttributeData'], lambda r: r['WHCode']),
            pairs=_native_index(btr['SkuLocAttributeData'], _key),
            descriptions=_native_index(btr['SiteDescriptionTbl'], lambda r: r['WHCode']))
    result = []
    for row in btr[table]:
        sku, loc = _key(row)
        if chronic_loc is not None:
            populations = [
                chronic_loc['skus'].get(sku, []),
                chronic_loc['locations'].get(loc, []),
                chronic_loc['pairs'].get((sku, loc), []) or [{}],
            ]
        else:
            populations = [
                [r for r in btr['SkuAttributeData'] if r['SKUCode'] == sku],
                [r for r in btr['LocationAttributeData'] if r['WHCode'] == loc],
                [r for r in btr['SkuLocAttributeData'] if _key(r) == (sku, loc)] or [{}],
            ]
        if kind.endswith('loc'):
            populations.append(chronic_loc['descriptions'].get(loc, []) if chronic_loc is not None
                               else [r for r in btr['SiteDescriptionTbl'] if r['WHCode'] == loc])
        elif kind.endswith('sku'):
            populations.append([r for r in btr['SKUDescriptionTbl'] if r['SKUCode'] == sku])
        else:
            populations.append([{}])
        populations.append([r for r in dbm['DBMMaster'] if _key(r) == (sku, loc)]
                           if table == 'DBMNormSuggestionsData' else [{}])
        for sa, la, sla, description, master in product(*populations):
            value = {**row, 'WHCode': loc, 'ParentWhCode': master.get('ParentWhCode', row.get('ParentWhCode')),
                     '_sku': sa, '_loc': la, '_description': description}
            value.update({f'SKUAttribute{i}': sa.get(f'c{i}') for i in range(1, 16)})
            value.update({f'LocAttribute{i}': la.get(f'c{i}') for i in range(1, 16)})
            value.update({f'SkuLocAttribute{i}': sla.get(f'c{i}') for i in range(1, 16)})
            value.update({k: v for k, v in sa.items() if not k.startswith('c')})
            value.update({k: v for k, v in la.items() if not k.startswith('c')})
            if filter_owners:
                value.update(_a=row, _location=la, _pair=sla, _master=master)
            result.append(value)
    return result


def _max(rows, owner, name):
    values = [r[owner].get(name) for r in rows if r[owner].get(name) is not None]
    return max(values) if values else None


def chronic_grid(btr, nms, *, filter_owners=False):
    result = []
    for row in btr['ChronicUnavalabilityData']:
        populations = (
            [r for r in nms if _key(r) == _key(row)] or [{}],
            [r for r in btr['LocationAttributeData'] if r['WHCode'] == _key(row)[1]] or [{}],
            [r for r in btr['SkuAttributeData'] if r['SKUCode'] == row['SKUCode']] or [{}],
            [r for r in btr['SkuLocAttributeData'] if _key(r) == _key(row)] or [{}],
        )
        for n, la, sa, sla in product(*populations):
            result.append({'SKUCode': row['SKUCode'], 'WHCode': _key(row)[1],
                'skucode': row['SKUCode'], 'skudesc': n.get('SKUDescription'),
                'location': _key(row)[1], 'parentloc': row['ParentWhCode'],
                'RLT': row['RLT'], 'BlackRedAgeing': row['BRAge'],
                'PhysicalInventoryPen': row['PhysicalInventoryPen'], 'Techcolor': row['PhysicalInventoryColor'],
                'PipelineInventoryPen': row['PipelineInventoryPen'], 'ecocolor': row['PipelineInventoryColor'],
                'RationedStockatparent': row['RationedQty']})
            if filter_owners:
                result[-1].update(_a=row, _sku=sa, _location=la, _pair=sla, _description=n)
    return result


def _attributes(rows, location):
    owner = '_loc' if location else '_sku'
    aliases = ({'LogisticsLocation': 'LogisticsLocation', **{f'LL{i}': f'LL{i}' for i in range(1, 6)}}
               if location else {'elephantOrderCapping': 'ElephantOrderCapping', 'weight': 'Weight',
                                 'volume': 'Volume', **{f'SL{i}': f'SL{i}' for i in range(1, 6)}})
    aliases.update({('c1' if i == 1 else f'C{i}'): f'c{i}' for i in range(1, 16)})
    return {alias: _max(rows, owner, field) for alias, field in aliases.items()}


def project(rows, kind):
    groups = defaultdict(list)
    chronic = kind.startswith('chronic')
    for row in rows:
        if chronic and (row['RLT'] is None or row['BRAge'] is None or row['BRAge'] <= row['RLT']):
            continue
        if kind.endswith('loc'):
            key = row['WHCode']
        elif kind.endswith('sku'):
            key = row['SKUCode']
        elif kind == 'pie':
            key = row['Suggestion']
        elif kind == 'ageing':
            age = row['SuggestionGenerationAge']
            if row['Suggestion'] in (None, 'No Suggestion') or age is None:
                continue
            key = '0-1' if age < 2 else '2-3' if age < 4 else '3-6' if age < 7 else '7+'
        else:
            raise ValueError('Unknown selected insight projection')
        groups[key].append(row)
    output = []
    for key, values in groups.items():
        counts = ({'redCount': sum(r['PhysicalInventoryColor'] == 'Red' for r in values),
                   'blackCount': sum(r['PhysicalInventoryColor'] == 'Black' for r in values)}
                  if chronic else {'NormInc': sum(r['Suggestion'] == 'Increase' for r in values),
                                   'NormDec': sum(r['Suggestion'] == 'Decrease' for r in values)})
        if kind.endswith('loc'):
            item = {'whcode': key, 'location': _max(values, '_description', 'WHDescription'),
                    **counts, **_attributes(values, True)}
            if chronic: item['countSku'] = len(values)
        elif kind.endswith('sku'):
            item = {'sku': key, 'SKUDescription': _max(values, '_description', 'SKUDescription'),
                    **counts, **_attributes(values, False)}
            if chronic: item['countloc'] = len(values)
        elif kind == 'pie':
            item = {'suggestion': key, 'count': len(values) if key is not None else 0}
        else:
            item = {'age': key, **counts}
        output.append({k: v for k, v in item.items() if v is not None})
    if kind.endswith('loc'):
        output.sort(key=lambda r: r['countSku'] if chronic else r['NormInc'] + r['NormDec'], reverse=True)
    elif kind == 'chronic-sku':
        output.sort(key=lambda r: r['countloc'], reverse=True)
    elif kind == 'ageing':
        output.sort(key=lambda r: ('0-1', '2-3', '3-6', '7+').index(r['age']))
    return output
