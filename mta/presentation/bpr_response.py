"""Selected AdminBPR wire types from the deployed async reader.

Pinned DLL StreamResults IL_015f..IL_01c3; UI_ReportColumnTypes_2.0.sql
SHA51883c78e5effbb55b303f07b99df9c84a3a336b0525d19b0540a9b95df02a19.
Number preserves the SQL value; other fields use DBNull.ToString() / ToString.
"""
from decimal import Decimal
from mta.presentation.context import PublicationUnavailable

NUMBERS = frozenset(name.casefold() for name in '''Norm Stock TechPen GIT EcoPen Req
RationedQTY LeftoverParentStock ResidualSnP NormReq BlueReq vn'''.split())


def response_row(row):
    if row['intransit'] is not None:
        raise PublicationUnavailable('nonempty_BPR_transit_wire_not_yet_validated')
    result = {}
    for key, value in row.items():
        if key.casefold() in NUMBERS:
            if isinstance(value, Decimal):
                value = int(value) if value == value.to_integral_value() else float(value)
            result[key] = value
        else:
            result[key] = '' if value is None else str(value)
    return result
