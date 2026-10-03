"""Canonical Guided Excess aggregates over already joined/scoped report history."""
from collections import defaultdict

from mta.presentation.rrr import sql_key


def project(rows, *, value=False):
    groups = defaultdict(list)
    for row in rows:
        if not value and sql_key(row.get('PhysicalInventoryColor')) != sql_key('white'):
            continue
        groups[(row['ReportDate'], row.get('LocationType'))].append(row)
    result = []
    for (day, location_type), members in groups.items():
        item = {'locationtype': '-' if location_type is None else location_type, 'date': day}
        if value:
            amounts = [r['Amount'] for r in members if r['Amount'] is not None]
            if amounts:
                total = sum(amounts)
                if not -(2**63) <= total < 2**63:
                    raise OverflowError('Canonical BIGINT SUM overflow')
                item['value'] = total
        else:
            item['countSku'] = sum(r['SKUCode'] is not None for r in members)
        result.append(item)
    return sorted(result, key=lambda r: (r['date'], r['locationtype']))
