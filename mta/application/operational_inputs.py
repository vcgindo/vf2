"""Approved Cohort2 physical CSV interface; not the native SQLCMD exporter.

Column metadata belongs to the pinned source schema. No defaults, reordering,
deduplication or value sanitation are applied to producer rows.
"""
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import io
import math
import re


NULL = '\\N'
PHYSICAL_TABLES = ('MasterDataRaw', 'DailyDataRaw', 'SOBDataRaw', 'MOQDataRaw1')
TEXT_TYPES = ('varchar', 'nvarchar', 'char', 'nchar', 'xml')
INTEGER_LIMITS = {'int': (-2**31, 2**31), 'bigint': (-2**63, 2**63),
                  'smallint': (-2**15, 2**15), 'tinyint': (0, 256)}


def typed_value(value, column, *, reserve_null_token=True):
    """Admit a lossless typed/wire value, rejecting silent database coercions."""
    name, kind = column['name'], column['type']
    if value is None:
        if not column['nullable']:
            raise ValueError('NULL in required column: ' + name)
        return None
    if kind in TEXT_TYPES:
        if not isinstance(value, str) or (reserve_null_token and value == NULL):
            raise ValueError('Invalid text or reserved NULL token: ' + name)
        width = column.get('parameters')
        if width and width.lower() != 'max':
            length = len(value.encode('utf-16-le')) // 2 if kind.startswith('n') else len(value)
            if length > int(width):
                raise ValueError('Text exceeds declared width: ' + name)
        return value
    if kind in INTEGER_LIMITS:
        if isinstance(value, str) and re.fullmatch(r'-?(?:0|[1-9][0-9]*)', value):
            value = int(value)
        lower, upper = INTEGER_LIMITS[kind]
        if type(value) is not int or not lower <= value < upper:
            raise ValueError('Invalid native integer: ' + name)
        return value
    if kind == 'bit':
        if value in ('0', '1'):
            value = int(value)
        if type(value) not in (int, bool) or value not in (0, 1):
            raise ValueError('Invalid native bit: ' + name)
        return bool(value)
    if kind in ('decimal', 'numeric'):
        if isinstance(value, (bool, float)):
            raise ValueError('Exact decimal required: ' + name)
        try:
            number = Decimal(value)
            precision, scale = map(int, column['parameters'].split(','))
            if (not number.is_finite() or number.as_tuple().exponent < -scale
                    or abs(number) >= Decimal(10) ** (precision - scale)):
                raise ValueError('Decimal exceeds declared precision/scale: ' + name)
        except (InvalidOperation, TypeError) as error:
            raise ValueError('Invalid decimal: ' + name) from error
        return number
    if kind in ('float', 'real'):
        if isinstance(value, bool):
            raise ValueError('Invalid floating value: ' + name)
        value = float(value)
        if not math.isfinite(value):
            raise ValueError('Nonfinite floating value: ' + name)
        return value
    if kind == 'date':
        if isinstance(value, str):
            value = date.fromisoformat(value)
        if type(value) is not date:
            raise ValueError('Date required: ' + name)
        return value
    if kind in ('datetime', 'datetime2'):
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime) or value.tzinfo is not None:
            raise ValueError('Naive native timestamp required: ' + name)
        return value
    raise ValueError('Unsupported physical column type: ' + kind)


def _cell(value):
    if value is None:
        return NULL
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, 'f')
    return str(value)


def encode_csv(columns, rows):
    names = [column['name'] for column in columns]
    if not names or len(names) != len(set(names)):
        raise ValueError('Unique nonempty physical column roster required')
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(names)
    for row in rows:
        if set(row) != set(names):
            raise ValueError('Physical row column roster differs')
        writer.writerow([_cell(typed_value(row[column['name']], column)) for column in columns])
    return output.getvalue().encode('utf-8')


def decode_csv(columns, payload):
    if not isinstance(payload, bytes) or payload.startswith(b'\xef\xbb\xbf'):
        raise ValueError('UTF-8 without BOM bytes required')
    reader = csv.reader(io.StringIO(payload.decode('utf-8'), newline=''), strict=True)
    names = [column['name'] for column in columns]
    if next(reader, None) != names:
        raise ValueError('Physical CSV header differs')
    rows = []
    for values in reader:
        if len(values) != len(columns):
            raise ValueError('Physical CSV row width differs')
        rows.append({column['name']: typed_value(None if value == NULL else value, column)
                     for column, value in zip(columns, values, strict=True)})
    # Reject noncanonical encodings/newlines/number spellings rather than silently
    # accepting a second interface whose byte reconstruction would differ.
    if encode_csv(columns, rows) != payload:
        raise ValueError('Noncanonical physical CSV representation')
    return rows


def physical_files(schema, populations, transit_columns):
    expected = {*PHYSICAL_TABLES, 'InTransitRaw'}
    if set(populations) != expected:
        raise ValueError('All five explicit physical populations required')
    result = {}
    for name in (*PHYSICAL_TABLES, 'InTransitRaw'):
        columns = transit_columns if name == 'InTransitRaw' else schema['tables']['Importer/' + name]
        payload = encode_csv(columns, populations[name])
        decode_csv(columns, payload)
        result[name + '.csv'] = payload
    return result
