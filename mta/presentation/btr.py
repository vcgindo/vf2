"""Deployed BORProcessor.GetBTRDataAsync joins over a completed daily run."""
from datetime import date
from itertools import product


def key(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode', row.get('LocCode')))


def horizon_columns(today, payload):
    filters = (payload.get('filters') or {}).get('horizonFilter') or {}
    values = {r['attributeName']: r['value'] for r in filters.get('filters', [])}
    start = 90 - (date.fromisoformat(today) - date.fromisoformat(values['startDate'][:10])).days if 'startDate' in values else 1
    end = 90 - (date.fromisoformat(today) - date.fromisoformat(values['endDate'][:10])).days if 'endDate' in values else 90
    if not 1 <= start <= end <= 90:
        raise ValueError('BTR horizon is outside the persisted 90-day columns')
    return tuple(f'D{i}' for i in range(start, end + 1))


def joined_rows(output, name):
    btr, closing = output['BTRFinal'][0], output['ClosingState'][0]
    trend = 'PhysicalInv' if name == 'tech' else 'Dispatch'
    report = output['BPRStages'][-1]['state']['vf_RationedReqReport']
    result = []
    for a in btr['BPPTrend' + trend]:
        k = key(a)
        populations = (
            [r for r in btr['BufferTrend' + trend] if key(r) == k] or [{}],
            [r for r in report if key(r) == k] or [{}],
            [r for r in btr['LocationAttributeData'] if r['WHCode'] == k[1]] or [{}],
            [r for r in btr['SkuAttributeData'] if r['SKUCode'] == k[0]] or [{}],
            [r for r in btr['SkuLocAttributeData'] if key(r) == k] or [{}],
            [r for r in closing['dbm']['SKULocStandardAttributes'] if key(r) == k] or [{}],
        )
        for t, req, la, sa, sla, standard in product(*populations):
            row = {**req, 'SKUCode': k[0], 'WHCode': k[1], 'WhCode': k[1],
                   '_bpp': a, '_trend': t, '_standard': standard}
            row.update({f'SKUAttribute{i}': sa.get(f'c{i}') for i in range(1, 16)})
            row.update({f'LocAttribute{i}': la.get(f'c{i}') for i in range(1, 16)})
            row.update({f'SkuLocAttribute{i}': sla.get(f'c{i}') for i in range(1, 16)})
            row.update({k: v for k, v in la.items() if not k.startswith('c')})
            row.update({k: v for k, v in sa.items() if not k.startswith('c')})
            result.append(row)
    return sorted(result, key=key)


def category_alias_text(category, categories):
    """Map retained category codes in their persisted sequence."""
    if category in (None, ''):
        return None
    if not isinstance(category, str):
        raise ValueError('Invalid persisted Category value')
    codes = category.split('|')
    if any(code == '' for code in codes):
        raise ValueError('Invalid empty Category code')
    if len(set(codes)) != len(codes):
        raise ValueError('Duplicate persisted Category code')

    aliases = []
    for code in codes:
        matches = [row for row in categories if str(row.get('CategoryId')) == code]
        if not matches:
            raise ValueError(f'Unknown Category code: {code}')
        if len(matches) != 1:
            raise ValueError(f'Duplicate Category metadata mapping: {code}')
        alias = matches[0].get('CategoryAlias')
        if not isinstance(alias, str) or alias == '':
            raise ValueError(f'Unmapped Category alias: {code}')
        aliases.append(alias)
    return '|'.join(aliases)


def project_rows(output, name, selected, columns, limit):
    """The deployed CTE pages keys, then rejoins and limits the result again."""
    closing = output['ClosingState'][0]
    importer = closing['importer']
    categories = closing['consumer_context']['CategoryColDescription']
    all_rows = joined_rows(output, name)
    result = []
    for selected_row in selected:
        for row in all_rows:
            if key(row) != key(selected_row):
                continue
            standard, t, a = row['_standard'], row['_trend'], row['_bpp']
            category = category_alias_text(standard.get('Category'), categories)
            populations = (
                [r for r in importer['SKUDescriptionTbl'] if r['SKUCode'] == row['SKUCode']] or [{}],
                [r for r in importer['SiteDescriptionTbl'] if r['WHCode'] == row['WhCode']] or [{}],
                [r for r in importer['SiteDescriptionTbl'] if r['WHCode'] == row.get('ParentWhCode')] or [{}],
            )
            for sku, location, parent in product(*populations):
                value = {'Source': name, 'Category': category,
                    'Availability': None, 'Tags': standard.get('Tags'), 'SKUCode': row['SKUCode'],
                    'SKUDescription': sku.get('SKUDescription'), 'WhCode': row['WhCode'],
                    'LocationName': location.get('WHDescription'), 'Norm': row.get('Norm'),
                    'VirtualNorm': row.get('VirtualNorm'), 'pc': t.get('ParentWhCode'),
                    'pn': parent.get('WHDescription'), 'age': t.get('Age'),
                    **{c: a[c] for c in columns}, **{'C' + c: t.get(c) for c in columns},
                    **{alias: t.get(colour + 'Count') for alias, colour in
                       (('bc', 'Black'), ('rc', 'Red'), ('yc', 'Yellow'), ('gc', 'Green'), ('blc', 'Blue'), ('wc', 'White'))}}
                # SqlDataReader.ToString(), including DBNull -> empty string.
                result.append({k: '' if v is None else str(v) for k, v in value.items()})
    return sorted(result, key=key)[:limit]
