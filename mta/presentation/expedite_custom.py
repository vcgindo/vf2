"""Canonical custom Expedite terminal read; no invented NMS identifiers/order."""
from decimal import Decimal

from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import sql_key


def custom_rows(rows, *, nms, products, locations, paging, stable_producer_order=False):
    # Only the admitted terminal native-empty NMS boundary has been proved.
    # A later populated source requires its actual LEFT joins and typed fields.
    if nms:
        raise ValueError('expedite_custom_nonempty_nms_not_verified')
    values = []
    keys = []
    for row in rows:
        if (row['RationedQty'] is None or row['RationedQty'] <= 0 or
                row['IsReceiving'] != 1 or sql_key(row['PipelineInventoryColor']) not in
                (sql_key('Black'), sql_key('Red'))):
            continue
        weight = permission_multiplicity(products, row['SKUCode']) * permission_multiplicity(locations, row['ParentWhCode'])
        value = {alias: row[field] for alias, field in (
            ('pt', 'PhysicalInventoryColor'), ('tpp', 'PhysicalInventoryPen'),
            ('git', 'GIT'), ('ep', 'PipelineInventoryColor'),
            ('epp', 'PipelineInventoryPen'), ('rq', 'RationedQty')) if row[field] is not None}
        for field in ('tpp', 'epp'):
            if field in value:
                value[field] = Decimal(str(value[field]))
        values.extend(dict(value) for _ in range(weight))
        keys.extend([tuple(sql_key(row[field]) for field in ('SKUCode', 'WhCode', 'ParentWhCode'))]*weight)
    if paging is not None:
        page, size = paging
        lower, upper = (page-1)*size+1, page*size
        if upper < max(1, lower) or lower > len(values):
            return []
    # All A.SKUCode/A.WhCode sort keys are NULL. Identical rows remain a bag;
    # distinct rows cannot receive a fabricated deterministic RN/page position.
    if stable_producer_order:
        # Explicit presentation exception; never fill missing native NMS fields.
        seen = {}
        for key, value in zip(keys, values):
            if key in seen and seen[key] != value:
                raise ValueError('expedite_custom_conflicting_producer_key')
            seen[key] = value
        values = [value for key, value in sorted(zip(keys, values), key=lambda item:
                  tuple((part is not None, part or ()) for part in item[0]))]
    elif values and any(row != values[0] for row in values[1:]):
        raise ValueError('LEG-EXPEDITE-CUSTOM-UNORDERED-NMS: distinct rows share NULL ROW_NUMBER keys; NOT_PARITY')
    return [dict(RN=i, **row) for i, row in enumerate(values, 1)
            if paging is None or lower <= i <= upper]
