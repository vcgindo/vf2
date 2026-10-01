"""Matched ReportsController/BORProcessor RRR CSV contract, not a grid dump."""
from decimal import Decimal
from itertools import chain
import json

from mta.presentation.legacy_ui import RRR_UI_CONFIG
from mta.presentation.rrr import DIRECT_FIELDS, ALIASES

FIELDS = (*DIRECT_FIELDS, *ALIASES,
          *(p + str(i) for p in ('sl','ll') for i in range(1,6)),
          *(p + str(i) for p in ('SKULocAttr','SKUAttr','LocAttr') for i in range(1,16)))


def selected_headers(state, fields):
    try:
        layout = json.loads(state) if state else None
    except (ValueError, TypeError):
        layout = None
    visible = [r for r in RRR_UI_CONFIG if r['Visible']]
    if not isinstance(layout, (dict, list)):
        selected = [(r['Header'] or '', r['Col_Code'], r['Col_Position']) for r in visible]
    else:
        selected = []
        columns = layout.get('columns', []) if isinstance(layout, dict) else []
        if not isinstance(columns, (dict, list)):
            columns = []
        if isinstance(columns, dict):
            # OPENJSON's non-integer keys yield NULL TRY_CAST position. This
            # malformed-layout branch has no selected ordering proof.
            from mta.presentation.context import PublicationUnavailable
            raise PublicationUnavailable('RRR_EXPORT_LAYOUT_OBJECT_NOT_VERIFIED')
        for position, column in enumerate(columns, 1):
            if not isinstance(column, dict):
                continue
            code = column.get('colId')
            hide = column.get('hide')
            if hide is None or isinstance(hide, (dict, list)):
                hide = False
            if code is None or str(hide).lower() != 'false':
                continue
            matches = [r for r in visible if r['Col_Code'].casefold() == str(code).casefold()]
            selected.extend((r['Header'] or '', code, position) for r in matches)
            if not matches:
                selected.append(('', code, position))
    # StreamCsvFromQueryAsync re-sorts by Position after the SQL pinned order.
    return [(header, code) for header, code, _ in sorted(selected, key=lambda r:r[2])
            if code and str(code).strip() and code in fields]


def invariant(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'True' if value else 'False'
    if isinstance(value, float):
        # .NET's invariant general representation suppresses integral .0.
        return str(int(value)) if value.is_integer() else str(value)
    if isinstance(value, Decimal):
        return format(value, 'f')
    return str(value)


def csv_chunks(rows, headers):
    def field(value):
        # CsvHelper's default ShouldQuote includes leading/trailing spaces;
        # an empty singleton record is a blank line (Python csv differs).
        if any(c in value for c in ',"\r\n') or value.startswith(' ') or value.endswith(' '):
            return '"' + value.replace('"', '""') + '"'
        return value
    for values in chain(([header for header, _ in headers],),
                        ([invariant(row[code]) for _, code in headers] for row in rows)):
        yield (','.join(field(value) for value in values) + '\r\n').encode('utf-8')
