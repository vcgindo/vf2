"""Canonical custom Expedite terminal read over retained relational populations."""
from collections import defaultdict
from decimal import Decimal

from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import sql_key


def _index(rows, *fields):
    result = defaultdict(list)
    for row in rows:
        key = sql_key(*(row.get(field) for field in fields))
        if key is not None:
            result[key].append(row)
    return result


def _empty_nms_rows(rows, *, products, locations, paging, stable_producer_order):
    """Retain the separately approved terminal empty-NMS presentation boundary."""
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
        keys.extend([sql_key(row['SKUCode'], row['WhCode'], row['ParentWhCode'])] * weight)
    if paging is not None:
        page, size = paging
        lower, upper = (page-1)*size+1, page*size
        if upper < max(1, lower) or lower > len(values):
            return []
    # Native ROW_NUMBER keys are all NULL here. This ordering is the explicit
    # terminal presentation exception and does not transfer to populated NMS.
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


def _joined_value(expedite, nms, bpr, site):
    value = {}
    fields = (
        ('sc', nms, 'SKUCode'), ('sd', nms, 'SKUDescription'),
        ('pwc', nms, 'ParentWhCode'), ('pn', site, 'WHDescription'),
        ('wc', nms, 'WhCode'), ('wd', nms, 'WHDescription'),
        ('n', nms, 'Norm'), ('sk', bpr, 'Stock'), ('mn', nms, 'MinNorm'),
        ('rlt', nms, 'RLT'), ('rcp', nms, 'RCP'), ('acp', nms, 'GCP'),
        ('ocp', nms, 'OCP'), ('moc', nms, 'MinOrderCount'),
        ('ps', nms, 'PackSize'), ('frf', nms, 'FGRMFlag'),
        ('da', nms, 'DBMActive'),
        ('pt', expedite, 'PhysicalInventoryColor'),
        ('tpp', expedite, 'PhysicalInventoryPen'), ('git', expedite, 'GIT'),
        ('ep', expedite, 'PipelineInventoryColor'),
        ('epp', expedite, 'PipelineInventoryPen'), ('rq', expedite, 'RationedQty'),
    )
    for alias, source, field in fields:
        if source is not None and source.get(field) is not None:
            value[alias] = source[field]
    for number in range(1, 6):
        for prefix, field_prefix in (('sl', 'SL'), ('ll', 'LL')):
            field = field_prefix + str(number)
            if nms is not None and nms.get(field) is not None:
                value[prefix + str(number)] = nms[field]
    for field in ('tpp', 'epp'):
        if field in value:
            value[field] = Decimal(str(value[field]))
    return value


def custom_rows(rows, *, nms, products, locations, paging,
                stable_producer_order=False, bpr_rows=None, site_descriptions=None,
                visible_dynamic_attributes=None):
    """Apply the deployed custom Expedite LEFT joins without collapsing bags.

    A populated NMS call must pass retained BPR_Table and SiteDescriptionTbl
    populations, plus the caller-verified visible AdminBPR attribute config.
    Only an empty visible attribute sequence is currently admitted.
    """
    if not nms:
        return _empty_nms_rows(rows, products=products, locations=locations,
                               paging=paging, stable_producer_order=stable_producer_order)
    if visible_dynamic_attributes is None:
        raise ValueError('expedite_custom_nonempty_nms_dynamic_config_not_verified')
    if visible_dynamic_attributes:
        raise ValueError('expedite_custom_visible_dynamic_attributes_unsupported')
    if bpr_rows is None:
        raise ValueError('expedite_custom_bpr_table_not_available')
    if site_descriptions is None:
        raise ValueError('expedite_custom_site_descriptions_not_available')

    nms_by_position = _index(nms, 'SKUCode', 'WhCode')
    bpr_by_position = _index(bpr_rows, 'SKUCode', 'WhCode')
    sites_by_code = _index(site_descriptions, 'WHCode')
    joined = []
    for expedite in rows:
        if (expedite['RationedQty'] is None or expedite['RationedQty'] <= 0 or
                expedite['IsReceiving'] != 1 or
                sql_key(expedite['PipelineInventoryColor']) not in
                (sql_key('Black'), sql_key('Red'))):
            continue
        weight = (permission_multiplicity(products, expedite['SKUCode']) *
                  permission_multiplicity(locations, expedite['ParentWhCode']))
        if not weight:
            continue
        matches = nms_by_position.get(sql_key(expedite['SKUCode'], expedite['WhCode']), [None])
        for nms_row in matches:
            position = (sql_key(nms_row.get('SKUCode'), nms_row.get('WhCode'))
                        if nms_row is not None else None)
            bpr_matches = (bpr_by_position.get(position, [None]) if position is not None else [None])
            parent = sql_key(nms_row.get('ParentWhCode')) if nms_row is not None else None
            site_matches = sites_by_code.get(parent, [None]) if parent is not None else [None]
            for bpr in bpr_matches:
                for site in site_matches:
                    value = _joined_value(expedite, nms_row, bpr, site)
                    joined.extend((position, dict(value)) for _ in range(weight))

    # ROW_NUMBER orders only by the normalized A.SKUCode/A.WhCode pair. NULLs
    # sort first. A tie with different payloads has no reproducible RN/page and
    # is unavailable; identical duplicates retain their full bag multiplicity.
    seen = {}
    for key, value in joined:
        if key in seen and seen[key] != value:
            raise ValueError('expedite_custom_conflicting_row_number_key')
        seen[key] = value
    joined.sort(key=lambda item: (item[0] is not None, item[0] or ()))
    numbered = [dict(RN=i, **value) for i, (_, value) in enumerate(joined, 1)]
    if paging is None:
        return numbered
    page, size = paging
    lower, upper = (page - 1) * size + 1, page * size
    if upper < max(1, lower):
        return []
    return [row for row in numbered if lower <= row['RN'] <= upper]
