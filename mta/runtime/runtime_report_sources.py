"""Typed report cells from verified immutable images, without owner selection.

The caller authenticates the accepted phase/run and chooses its source image.
This adapter checks that physical table/field contract, uses the legacy full
checksum reader or the accepted immutable cut, then decodes requested cells. It never changes
stored wire values, supplies a missing column or substitutes another image.
"""
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from mta.application.operational_inputs import typed_value, TEXT_TYPES, INTEGER_LIMITS
from mta.row_sequences import RecordRows
from mta.runtime import relational_state


def _key(value):
    if type(value) is not str or not value or not value.isascii():
        raise ValueError('Explicit ASCII report source column required')
    return value.lower()


def scalar(value, kind):
    """Decode a stored cell according to its declared native SQL type.

    Storage's registry has scalar kinds, not source precision/scale/NULLability.
    Those remain the qualified producer/serializer's contract; this adapter
    neither rounds a decimal nor invents a display scale or NOT NULL default.
    """
    if kind not in (*TEXT_TYPES, *INTEGER_LIMITS, 'bit', 'decimal', 'numeric',
                    'float', 'real', 'date', 'datetime', 'datetime2'):
        raise ValueError('Unsupported stored report scalar type')
    if kind in ('decimal', 'numeric'):
        if value is None:
            return None
        if type(value) not in (str, int, Decimal):
            raise ValueError('Exact finite stored report decimal required')
        try:
            number = Decimal(value)
        except (InvalidOperation, ValueError) as error:
            raise ValueError('Exact finite stored report decimal required') from error
        if not number.is_finite():
            raise ValueError('Exact finite stored report decimal required')
        return number
    return typed_value(value, dict(name='report cell', type=kind, nullable=True),
                       reserve_null_token=False)


def image_rows(run, metadata, *, expected_table, fields, registry=None):
    """Return a reiterable typed projection with original ordinal multiplicity.

    An existing empty image uses its declared registry schema; an absent image
    or unknown requested column still denies. SQL column identifier case is
    reconciled explicitly; values and business keys are never normalized.
    """
    registry = relational_state.STORAGE_TABLES if registry is None else registry
    if (not isinstance(metadata, Mapping) or expected_table not in registry
            or metadata.get('table') != expected_table
            or type(metadata.get('count')) is not int or metadata['count'] < 0
            or type(metadata.get('fields')) is not list):
        raise ValueError('Exact report source image/table contract required')
    if type(fields) not in (tuple, list) or not fields:
        raise ValueError('Explicit nonempty report source field roster required')
    requested = [_key(field) for field in fields]
    if len(set(requested)) != len(requested):
        raise ValueError('Duplicate report source field requested')
    declared = {}
    for name, kind in registry[expected_table]:
        key = _key(name)
        if key in declared:
            raise ValueError('Ambiguous report source schema column')
        declared[key] = (name, kind)
    if not set(requested) <= declared.keys():
        raise ValueError('Report source field absent from declared table')
    available = {}
    for item in metadata['fields']:
        if type(item) not in (tuple, list) or len(item) != 3:
            raise ValueError('Report source image column metadata differs')
        wire_name, physical_name, _wire_kind = item
        physical_key = _key(physical_name)
        if physical_key not in declared or physical_key in available:
            raise ValueError('Report source physical column absent or ambiguous')
        # A SQL field projects its actual physical column, not a caller alias.
        _key(wire_name)
        available[physical_key] = wire_name
    if metadata['count'] and not set(requested) <= available.keys():
        raise ValueError('Required report source image columns missing')
    # An explicit nonempty metadata roster may not silently omit a requested
    # column just because a particular image currently contains zero rows.
    if metadata['fields'] and not set(requested) <= available.keys():
        raise ValueError('Required report source image columns missing')
    from mta.runtime.rationing_reader import uses_occurrences
    from mta.runtime import btr_import_image, dated_history_reader, inherited_history_image
    if inherited_history_image.owns(metadata):
        # The exact predecessor/anchor cut and this sealed phase still own it.
        original = inherited_history_image.load_image(run,metadata)
    elif dated_history_reader.owns(metadata):
        cut = dated_history_reader.require_image(run,metadata)
        names = tuple(available[key] for key in requested) if available else ()
        original = dated_history_reader.load_cut(cut,names=names)
    elif btr_import_image.owns(metadata):
        original = btr_import_image.load(run,metadata,audit=True)
    elif uses_occurrences(metadata):
        # The new immutable cut was fully verified at commit. Its selected
        # header and indexed relation replace a repeated full-prefix audit.
        from mta.runtime.rationing_reader import load_cut, require_image
        cut = require_image(run, metadata)
        names = tuple(available[key] for key in requested) if available else ()
        original = load_cut(cut, names=names)
    else:
        original = relational_state.load_image(run, metadata, table_registry=registry)
    if len(original) != metadata['count']:
        raise ValueError('Report source row count differs')

    def records():
        for row in original:
            if not isinstance(row, Mapping):
                raise ValueError('Report source row mapping required')
            result = {}
            for label, key in zip(fields, requested, strict=True):
                wire_name = available[key]
                if wire_name not in row:
                    raise ValueError('Required report source row field missing')
                result[label] = scalar(row[wire_name], declared[key][1])
            yield result
    return RecordRows(metadata['count'], records)
