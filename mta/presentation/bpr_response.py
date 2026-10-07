"""Selected AdminBPR wire types from the deployed async reader.

Pinned DLL StreamResults IL_015f..IL_01c3; UI_ReportColumnTypes_2.0.sql
SHA51883c78e5effbb55b303f07b99df9c84a3a336b0525d19b0540a9b95df02a19.
Number preserves the SQL value; other fields use DBNull.ToString() / ToString.
"""
from decimal import Decimal
import json
from mta.presentation.context import PublicationUnavailable

NUMBERS = frozenset(name.casefold() for name in '''Norm Stock TechPen GIT EcoPen Req
RationedQTY LeftoverParentStock ResidualSnP NormReq BlueReq vn'''.split())


TRANSIT_FIELDS = ('lc', 'cd', 'slt', 'tlt', 'ag', 'eta', 'cl', 'qty',
                  'exeecocolor', 'remarks')


def transit_json(rows):
    # Exact deployed scalar FOR JSON PATH, INCLUDE_NULL_VALUES property order.
    # Daily source date fields are ISO dates and quantities/durations are ints.
    return json.dumps([{name: row[name] for name in TRANSIT_FIELDS} for row in rows],
        ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('/', '\\/')


def response_row(row, *, daily_transit=False):
    if row['intransit'] is not None and not daily_transit:
        raise PublicationUnavailable('nonempty_BPR_transit_wire_not_yet_validated')
    result = {}
    for key, value in row.items():
        if key == 'intransit' and value is not None:
            result[key] = transit_json(value)
        elif key.casefold() in NUMBERS:
            if isinstance(value, Decimal):
                value = int(value) if value == value.to_integral_value() else float(value)
            result[key] = value
        else:
            result[key] = '' if value is None else str(value)
    return result
