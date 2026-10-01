"""The four active ExcessInventoryProcessor queries and response mapping."""
from collections import defaultdict
from decimal import Decimal
import re


SECTIONS = (
    ('location_count', 'WHCode', False, 'topTenLocationsWithExcessInventorySkuCount', 'WHDescription', 'SKUCounts'),
    ('location_value', 'WHCode', True, 'topTenLocationsWithExcessInventoryValue', 'WHDescription', 'SumOfAmount'),
    ('sku_count', 'SKUCode', False, 'topTenProductsWithExcessInventoryNumberOfLocations', 'SKUDescription', 'WHCount'),
    ('sku_value', 'SKUCode', True, 'topTenProductsWithExcessInventoryInValue', 'SKUDescription', 'SumAmount'),
)


def excess_chart_queries(rows, location_descriptions, sku_descriptions, location_attributes, sku_attributes,
                         report_date, *, sku_codes=None, location_codes=None):
    """Aggregate before the outer attribute join; retain duplicate output rows.

    Despite the chart names, the selected binary has no TOP 10. SQL NULL
    sums remain NULL. Its chart population has no Norm/VirtualNorm gate.
    """
    eligible = [r for r in rows if r['ReportDate'] == report_date
                and (sku_codes is None or r['SKUCode'] in sku_codes)
                and (location_codes is None or r['WHCode'] in location_codes)]
    result = {}
    for section, field, amount, _, _, _ in SECTIONS:
        descriptions = location_descriptions if field == 'WHCode' else sku_descriptions
        attributes = location_attributes if field == 'WHCode' else sku_attributes
        grouped = defaultdict(list)
        for row in eligible:
            if row[field] in descriptions:
                grouped[row[field]].append(row)
        output = []
        for code, members in grouped.items():
            desc = descriptions[code]
            if desc is not None:
                desc = desc.replace("'", '') if field == 'WHCode' else re.sub('-ND-', lambda _: code, desc, flags=re.IGNORECASE)
            values = [Decimal(str(r['Amount'])) for r in members if r['Amount'] is not None]
            counts = (sum(values) if values else None) if amount else len(members)
            for attrs in attributes:
                if attrs[field] == code:
                    prefix = 'll' if field == 'WHCode' else 'sl'
                    output.append({field: code, 'Details': desc, 'counts': counts,
                                   **{f'{prefix}{i}': attrs[f'{prefix}{i}'] for i in range(1, 6)}})
        result[section] = sorted(output, key=lambda r: (r['counts'] is None, -(r['counts'] or 0)))
    return result


def excess_chart_response(queries):
    result = {}
    for section, field, _, response_key, description_key, count_key in SECTIONS:
        prefix = 'll' if field == 'WHCode' else 'sl'
        config = [dict(header=f'{prefix.upper()}{i}', colCode=f'{prefix}{i}') for i in range(1, 6)]
        data = []
        for row in queries[section]:
            item = {description_key: '' if row['Details'] is None else row['Details'],
                    count_key: '' if row['counts'] is None else str(row['counts'])}
            # Match the selected processor's configured-name lookup.
            item.update({c['colCode']: '' if row[c['colCode']] is None else str(row[c['colCode']])
                         for c in config if c['colCode'] in row})
            data.append(item)
        result[response_key] = dict(data=data, uiconfig=config)
    return result
