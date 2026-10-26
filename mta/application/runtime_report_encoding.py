"""Retained RuntimeReports SQLCMD cells and headers, streamed without CSV quoting.

The query identity owns the SQL result types. Projection owns data/ordering;
this adapter only serializes those values using the qualified operational scalar
encoder. It does not select a phase, evaluate arbitrary SQL or publish files.
"""
import re

from mta.application import report_encoding
from mta.application.runtime_report_projection import describe

N50, N125, V125, V127 = 'nvarchar(50)', 'nvarchar(125)', 'varchar(125)', 'varchar(127)'
D = 'decimal(10,2)'
EFFICIENCY_TYPES = (N50, N125, N50, N125, N50, N125, 'bit', 'int',
    N50, N50, N50, N50, 'int', D, 'nvarchar(10)', 'int', 'date', 'varchar(3)',
    'int', 'int', 'int', 'int', 'int', 'int')
BOR_TYPES = (N50, V127, N50, V127, N50, V127) + ('int',)*17 + ('nvarchar(10)',) + (N50,)*7
SPIKE_TYPES = ('int', N50, 'int', 'bit', 'bit', 'int', 'int', N50, N50, N50, 'date', 'date')
HISTORY_TYPES = ((N50, V125, N50, V125, N50, V125) + ('int',)*17
    + ('nvarchar(10)', 'int', N50, N50, 'nvarchar(max)', N50, N50, N50, N50, N50, 'date'))
# One-based native SELECT positions; the final 45 cells are C/D/E.c1..c15.
_TOTAL_OVERRIDES = {1:N50, 2:N125, 3:N50, 4:N125, 8:D, 9:D, 14:D,
    15:'nvarchar(10)', 16:D, 17:'nvarchar(10)', 18:D, 19:'nvarchar(10)',
    24:N50, 25:V125, 27:D, 28:'nvarchar(10)', 29:D, 30:'nvarchar(10)', 42:'bit'}
TOTAL_TYPES = tuple(_TOTAL_OVERRIDES.get(i, 'int') for i in range(1, 63)) + (N50,)*45


def types(definition):
    spec = describe(definition)
    identity = spec['captured_source_id']
    kinds = (EFFICIENCY_TYPES if identity in (2, 3) else BOR_TYPES if identity in (4, 5, 6)
             else SPIKE_TYPES if identity == 7 else HISTORY_TYPES if identity == 8 else TOTAL_TYPES)
    if len(kinds) != len(spec['columns']):
        raise ValueError('Runtime query type/column roster differs')
    return kinds


def headers(value):
    """Only the captured SQL string-literal SELECT grammar, including doubled '.

    NULL means no header SELECT. Empty SQL text or expressions are not silently
    treated as empty headers; other header-query forms need their own projection.
    """
    if value is None:
        return None
    if type(value) is not str or not value.strip():
        raise ValueError('Qualified literal RuntimeReports HeaderList required')
    cells, offset = [], 0
    while offset < len(value):
        match = re.match(r"\s*'((?:[^']|'')*)'\s*", value[offset:])
        if match is None:
            raise ValueError('Unsupported RuntimeReports header SQL expression')
        cells.append(match[1].replace("''", "'"))
        offset += match.end()
        if offset == len(value):
            break
        if value[offset] != ',' or not value[offset+1:].strip():
            raise ValueError('Invalid RuntimeReports header literal separator')
        offset += 1
    return tuple(cells)


def cell(value, kind):
    if kind == 'nvarchar(max)':
        # SQLCMD's large-value display width is not the source's storage width.
        # Preserve the untruncated domain; do not guess >256 display behavior.
        if value is not None and (type(value) is not str or len(value) > 256):
            raise ValueError('Runtime max-text display truncation requires native qualification')
        kind = 'nvarchar'
    return report_encoding.scalar(value, kind)


def chunks(definition, rows):
    """Yield exact CRLF/CP1252 lines lazily; late failures never imply readiness.

    Header and data are distinct SELECT resultsets, so header width does not
    coerce data types. Literal values are not stripped, escaped or deduplicated.
    """
    kinds = types(definition)
    if (definition.get('Extension') != 'csv' or definition.get('TemplateName') is not None
            or definition.get('TemplateLoc') is not None
            or definition.get('Delimeter') not in (None, '', ',')):
        raise ValueError('Qualified comma-delimited flat runtime report required')
    head = headers(definition['HeaderList'])
    def lines():
        if head is not None:
            yield report_encoding._bytes(','.join(cell(value, 'varchar-literal') for value in head)+'\r\n')
        for row in rows:
            if len(row) != len(kinds):
                raise ValueError('Runtime report data row width differs')
            yield report_encoding._bytes(','.join(cell(value, kind) for value, kind in zip(row, kinds, strict=True))+'\r\n')
    return lines()
