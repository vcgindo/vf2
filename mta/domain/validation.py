"""Exact, bounded domain inputs; never round or coerce a business input silently."""
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

ZERO = Decimal(0)


class RuleBlocked(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def number(value, name="quantity", *, integer=False, positive=False):
    if type(value) is int:
        value = Decimal(value)
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal or integer")
    if value < 0 or value >= Decimal("1e14") or (positive and value == 0):
        raise ValueError(f"{name} outside supported nonnegative range")
    if value.as_tuple().exponent < -6 or (integer and value != value.to_integral_value()):
        raise ValueError(f"{name} requires {'integer' if integer else 'at most six-decimal'} units")
    return value


def signed_number(value, name="quantity", *, integer=False):
    """Validate signed source quantities without relaxing ``number`` globally."""
    if type(value) is int:
        value = Decimal(value)
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal or integer")
    if abs(value) >= Decimal("1e14"):
        raise ValueError(f"{name} outside supported signed range")
    if value.as_tuple().exponent < -6 or (integer and value != value.to_integral_value()):
        raise ValueError(f"{name} requires {'integer' if integer else 'at most six-decimal'} units")
    return value


def percent(value, name="percentage"):
    value = number(value, name)
    if value > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return value


def day(value):
    if type(value) is not date:
        raise ValueError("Explicit business date required (not a timestamp)")
    return value


def identity(value):
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 100:
        raise ValueError("Nonempty unpadded identifier of at most 100 characters required")
    return value


def ceiling(value):
    return value.to_integral_value(rounding=ROUND_CEILING)


def floor(value):
    return value.to_integral_value(rounding=ROUND_FLOOR)
