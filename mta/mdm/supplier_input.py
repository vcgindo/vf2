"""Supplier intake, with the approved destination-MOQ Modify correction.

This consumer neither activates NMS nor executes a day. Its caller must supply
the captured queue bags, persisted raw opening and Intermediate LocationMaster.
Other marker/format behavior retains pinned NMSImportData.sql (500–568).
"""
from copy import deepcopy

SQL_DIGEST = 'c86d014b1f7ee921821f83936a53d1d4da566ba9b2558db9252853260c3c3801'
FORMATS = ('WithDestLoc', 'WithoutDestLoc')
QUEUES = ('NMSSOB', 'NMSMOQWithDestination', 'NMSMOQWithoutDestination')
RAW = ('SOBDataRaw', 'MOQDataRaw1', 'MOQDataRaw2')


def _key(value):
    return value.rstrip(' ').lower() if value is not None else None


def _identity(row, destination, *, queue=False):
    names = ('SKUCode', 'WhCode' if queue else 'WHCode', 'SupplierCode') if destination else ('SKUCode', 'SupplierCode')
    values = tuple(_key(row[name]) for name in names)
    return values if None not in values else None


def compose_supplier_inputs(raw, queues, *, moq_format, locations):
    """Delete-before-insert; preserve every occurrence and native marker value."""
    if moq_format not in FORMATS:
        raise ValueError('Explicit canonical NMSMOQInputDataFormat required')
    if any(name not in raw for name in RAW) or any(name not in queues for name in QUEUES):
        raise ValueError('Explicit supplier raw and approval populations required')
    result = deepcopy(raw)
    selected = [('SOBDataRaw', 'NMSSOB', 'SOB', True),
                ('MOQDataRaw2', 'NMSMOQWithDestination', 'MOQ', True)
                if moq_format == 'WithDestLoc' else
                ('MOQDataRaw1', 'NMSMOQWithoutDestination', 'MOQ', False)]
    descriptions = {}
    for row in locations:
        key = _key(row['WHCode'])
        if key is not None:
            descriptions.setdefault(key, []).append(row['WHDescription'])
    resolved_descriptions = {}
    for raw_name, queue_name, scalar, destination in selected:
        eligible = [row for row in queues[queue_name] if row['Approved'] == 1]
        deleted = {_identity(row, destination, queue=True) for row in eligible}
        deleted.discard(None)  # SQL NULL does not join to NULL.
        rows = [row for row in result[raw_name] if _identity(row, destination) not in deleted]
        for row in eligible:
            # Authorized correction: a destination MOQ modification replaces
            # the matching raw value; it must not silently delete the MOQ.
            if row['ActionType'] != 1 and not (
                    queue_name == 'NMSMOQWithDestination' and row['ActionType'] == 2):
                continue
            item = {'SKUCode': row['SKUCode'], 'SupplierCode': row['SupplierCode'],
                    'SupplierDescription': 'ND', scalar: row[scalar]}
            if destination:
                item['WHCode'] = row['WhCode']
            rows.append(item)
        for row in rows:
            key = _key(row['SupplierCode'])
            if key not in resolved_descriptions:
                matches = descriptions.get(key, (None,))
                values = ['ND' if value is None else value for value in matches]
                if any(value != values[0] for value in values[1:]):
                    raise ValueError('SOURCE_ORDER_AMBIGUITY: supplier description UPDATE')
                resolved_descriptions[key] = values[0]
            row['SupplierDescription'] = resolved_descriptions[key]
        result[raw_name] = rows
    return result


def archive_populations(queues, *, moq_format):
    """NMSArchiveInputData archives all rows, not only approved rows."""
    if moq_format not in FORMATS:
        raise ValueError('Explicit canonical NMSMOQInputDataFormat required')
    selected = 'NMSMOQWithDestination' if moq_format == 'WithDestLoc' else 'NMSMOQWithoutDestination'
    return {name: deepcopy(queues[name]) for name in ('NMSSOB', selected)}


def cleared_populations(queues):
    """Canonical clear applies to both MOQ formats, irrespective of selection."""
    return {name: [deepcopy(row) for row in queues[name] if row['Approved'] != 1]
            for name in QUEUES}
