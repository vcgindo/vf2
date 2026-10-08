"""Native scalar contracts for the bounded ASCII synthetic daily population.

No SQL calls occur in modern production. Inputs outside this declared text/date
domain fail explicitly rather than inheriting Python Unicode/locale defaults.
Native differential qualification is separate from these implementations.
"""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext
import math
import re
import sys

NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z', re.ASCII)
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
STYLE_ZERO = re.compile(r'([A-Za-z]{3})\s+(\d{1,2}) (\d{4}) (\d{1,2}):(\d{2})(AM|PM)\Z')


def ascii_equal(left, right):
    """CI ASCII identifier/colour equality, including SQL trailing-space pads."""
    if left is None or right is None:
        return False
    if not isinstance(left, str) or not isinstance(right, str) or not left.isascii() or not right.isascii():
        raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ASCII SQL text equality')
    return left.rstrip(' ').upper() == right.rstrip(' ').upper()


def identifier_sort_key(value):
    # Only alphanumeric SKU identifiers are ordered by the production script.
    # Punctuation/Unicode collation weights are not Python lexicographic order.
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9]+ *', value) is None:
        raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: alphanumeric SKU ordering')
    return value.rstrip(' ').upper()


def try_cast_float(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.isascii():
        raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ASCII nvarchar to FLOAT')
    # Native NVARCHAR conversion pads/trims ordinary trailing spaces only.
    # Its numeric parser accepts leading C whitespace, but TAB/CR/LF alone
    # and numeric text followed by those characters are conversion failures.
    text = value.rstrip(' ')
    if not text:
        return 0.0
    text = text.lstrip(' \t\r\n\v\f')
    if NUMBER.fullmatch(text) is None:
        return None
    result = float(text)
    if not math.isfinite(result):
        return None
    # SQL text-to-FLOAT flushes subnormals/underflow to positive zero. Literal
    # signed zero is retained, so distinguish a nonzero underflowing decimal.
    if abs(result) < sys.float_info.min and not Decimal(text).is_zero():
        return 0.0
    return result


def round_float_zero(value):
    if type(value) is not float or not math.isfinite(value):
        raise ValueError('Finite native FLOAT required')
    if value == 0:
        return value
    whole = math.trunc(value)
    fraction = value - whole
    if abs(fraction) >= 0.5:
        whole += 1 if value > 0 else -1
    return float(whole)


def float_to_nvarchar(value):
    """Default FLOAT style0: six significant digits and three exponent digits."""
    if type(value) is not float or not math.isfinite(value):
        raise ValueError('Finite native FLOAT required')
    if value == 0:
        return '-0' if math.copysign(1.0, value) < 0 else '0'
    # SQL style0 rounds an exact binary midpoint away from zero. Python's .6g
    # rounds it to even (123456.5 ->123456), so it is not the native contract.
    with localcontext() as context:
        context.prec = 80
        exact = Decimal.from_float(value)
        rounded = exact.quantize(Decimal(1).scaleb(exact.adjusted()-5), rounding=ROUND_HALF_UP)
        exponent = rounded.adjusted()
        scientific = exponent < -4 or exponent >= 6
        text = format(rounded.scaleb(-exponent) if scientific else rounded, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text + (f'e{exponent:+04d}' if scientific else '')


def datetime_to_nvarchar(value):
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise ValueError('Native timezone-naive datetime required')
    value = _datetime_storage(value)
    # This is the canonical implicit datetime -> nvarchar style0. Seconds are
    # omitted by SQL as well, so a non-minute run timestamp can fail its gate.
    return (f'{MONTHS[value.month-1]} {value.day:2d} {value.year:04d} '
            f'{value.hour % 12 or 12:2d}:{value.minute:02d}'
            + ('AM' if value.hour < 12 else 'PM'))


def _datetime_storage(value):
    if value < datetime(1753, 1, 1):
        raise ValueError('SQL datetime range starts in 1753')
    ticks = (value.microsecond * 300 + 500_000) // 1_000_000
    milliseconds = (ticks * 1000 + 150) // 300
    return value.replace(microsecond=0) + timedelta(milliseconds=milliseconds)


def parse_datetime(value):
    if not isinstance(value, str) or not value.isascii():
        raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: run-date text')
    match = STYLE_ZERO.fullmatch(value)
    if match:
        month, day, year, hour, minute, half = match.groups()
        if month not in MONTHS or not 1 <= int(hour) <= 12:
            raise ValueError('Invalid native style0 run date')
        return _datetime_storage(datetime(int(year), MONTHS.index(month)+1, int(day),
                        int(hour) % 12 + (12 if half == 'PM' else 0), int(minute)))
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)?', value):
        return _datetime_storage(datetime.fromisoformat(value))
    raise ValueError('UNQUALIFIED_SCALAR_DOMAIN: ISO or native style0 run date')
