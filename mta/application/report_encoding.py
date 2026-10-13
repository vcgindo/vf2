"""Bounded whitespace-trimmed comma encoding for operational reports."""
from datetime import date, datetime
from decimal import Decimal
import re

from mta.application.operational_inputs import typed_value
from mta.domain.complete_daily_scalars import datetime_to_nvarchar, float_to_nvarchar, _datetime_storage


def _bytes(text):
    if '\0' in text:
        raise ValueError('NUL requires separate native output qualification')
    try:
        return text.encode('cp1252')
    except UnicodeEncodeError as error:
        raise ValueError('Unqualified report encoding best-fit text conversion') from error


def _text(value):
    if not isinstance(value, str):
        raise ValueError('Native text value required')
    _bytes(value)
    return value


def scalar(value, kind):
    if value is None:
        return 'NULL'
    text = re.fullmatch(r'(?:n?varchar|n?char)\((\d+)\)', kind)
    if text:
        value = _text(value)
        if len(value) > int(text[1]):
            raise ValueError('Native text exceeds source width')
        return value
    if kind in ('varchar-literal', 'nvarchar', 'nvarchar-export', 'iso-date-text'):
        return _text(value)
    if kind == 'int':
        return str(typed_value(value, dict(name='value', type='int', nullable=False)))
    if kind == 'bit':
        return '1' if typed_value(value, dict(name='value', type='bit', nullable=False)) else '0'
    decimal = re.fullmatch(r'(?:decimal|numeric)\((\d+),(\d+)\)', kind)
    if decimal:
        value = typed_value(value, dict(name='value', type='decimal', nullable=False,
                                       parameters=decimal[1] + ',' + decimal[2]))
        if value.as_tuple().exponent != -int(decimal[2]):
            raise ValueError('Native SQL decimal stored scale required')
        result = format(abs(value) if value == 0 else value, 'f')
        return result[1:] if result.startswith('0.') else '-' + result[2:] if result.startswith('-0.') else result
    if kind == 'date':
        return typed_value(value, dict(name='value', type='date', nullable=False)).isoformat()
    if kind == 'datetime':
        value = typed_value(value, dict(name='value', type='datetime', nullable=False))
        return _datetime_storage(value).isoformat(sep=' ', timespec='milliseconds')
    raise ValueError('Unqualified direct report encoding type: ' + str(kind))


def converted_text(value, kind):
    """SQL CONVERT nvarchar style0, distinct from report encoding numeric/date display."""
    if value is None:
        return None
    if kind in ('nvarchar', 'varchar', 'char', 'nchar'):
        return _text(value)
    if kind in ('int', 'bigint', 'smallint', 'tinyint'):
        return str(typed_value(value, dict(name='value', type=kind, nullable=False)))
    if kind == 'bit':
        return scalar(value, kind)
    if kind in ('decimal', 'numeric'):
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError('Exact stored decimal required for SQL conversion')
        return format(abs(value) if value == 0 else value, 'f')
    if kind == 'float':
        return float_to_nvarchar(value)
    if kind == 'datetime':
        return datetime_to_nvarchar(value)
    if kind == 'date':
        return scalar(value, kind)
    raise ValueError('Unqualified native text conversion: ' + str(kind))


def resultset_bytes(resultsets):
    lines = []
    for resultset in resultsets:
        kinds = resultset['types']
        if len(resultset['fields']) != len(kinds):
            raise ValueError('Native resultset field/type roster differs')
        for row in resultset['rows']:
            if len(row) != len(kinds):
                raise ValueError('Native resultset row width differs')
            lines.append(','.join(scalar(value, kind) for value, kind in zip(row, kinds, strict=True)) + '\r\n')
    return _bytes(''.join(lines))


def norm_report_bytes(report):
    header = ','.join(scalar(cell['value'], cell['native_type']) for cell in report['header_result_set'])
    lines = [header + '\r\n']
    for row in report['data_result_set']:
        lines.append(','.join(scalar(cell['value'], cell['native_type']) for cell in row) + '\r\n')
    return _bytes(''.join(lines))


def bor_report_bytes(report):
    from mta.application.operational_bor import BOR_REPORT_HEADER
    return resultset_bytes([
        dict(fields=BOR_REPORT_HEADER, types=['varchar-literal'] * 25,
             rows=report['header_resultset']),
        dict(fields=BOR_REPORT_HEADER,
             types=['nvarchar'] * 6 + ['int'] * 17 + ['nvarchar', 'int'],
             rows=report['data_resultset']),
    ])


def upload_log_bytes(report):
    lines = []
    for row in (*report['header_result_set'], *report['data_result_set']):
        fields = []
        for cell in row:
            value = cell['value']
            if cell.get('native_conversion') is not None:
                value = converted_text(value, cell['source_type'])
            # The exporter explicitly CONVERTs each data text cell to nvarchar256.
            # This is SQL expression width, not report encoding's default display width.
            if cell['sql_type'] == 'nvarchar(256)' and value is not None:
                value = _text(value)[:256]
            fields.append(scalar(value, cell['sql_type']))
        lines.append(','.join(fields) + '\r\n')
    return _bytes(''.join(lines))


def input_table_bytes(columns, rows):
    """Approved four table exports, no WHERE clause, source metadata order."""
    names = [column['name'] for column in columns]
    header = ','.join(names)
    if len(header) > 4000:
        raise ValueError('Input table PRINT header truncation outside approved roster')
    lines = [header + '\r\n']
    for row in rows:
        if set(row) != set(names):
            raise ValueError('Input table complete row required')
        values = []
        for column in columns:
            value = typed_value(row[column['name']], column, reserve_null_token=False)
            converted = converted_text(value, column['type'])
            values.append('NULL' if converted is None else converted.replace(',', ' '))
        lines.append(','.join(values) + '\r\n')
    return _bytes(''.join(lines))


def no_norm_parent_bytes(rows):
    if not rows:
        return b''  # Native SQL does not execute SELECT when its population is empty.
    names = ('SKUCode', 'WhCode', 'Norm', 'ParentWhCode')
    kinds = ('nvarchar(50)', 'nvarchar(50)', 'int', 'nvarchar(50)')
    lines = [','.join(names) + '\r\n', ','.join('-' * len(name) for name in names) + '\r\n']
    for row in rows:
        if set(row) != set(names):
            raise ValueError('Complete NoNormAtParentReport row required')
        lines.append(','.join(scalar(row[name], kind) for name, kind in zip(names, kinds)) + '\r\n')
    return _bytes(''.join(lines))
