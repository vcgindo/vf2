"""Dated BTR pivot operands from the original BPR import.

A cell belongs to a date and the producer's grouping key. Its multiplicity
counts source observations, not grid rows, export rows or permission matches.
An absent date has no cell. An observed row can contain SQL NULLs throughout.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from collections.abc import Iterable, Mapping

from mta.domain.btr_finalization import _day
from mta.domain.sql_identity_keys import group_key


@dataclass(frozen=True, slots=True)
class DayCell:
    business_date: date
    sku: str | None
    location: str | None
    observations: int
    physical_pen: Decimal | int | float | str | None
    physical_colour: str | None
    dispatch_pen: Decimal | int | float | str | None
    dispatch_colour: str | None
    tech_pen: Decimal | int | float | str | None
    tech_colour: str | None
    eco_pen: Decimal | int | float | str | None
    eco_colour: str | None


def daily_cells(business_date, rows):
    """Reduce one explicit date with the same MAX, NULL and spelling rules.

    Apply the original pivot comparisons before display conversion. A
    numeric-looking wire string must not be coerced to float before MAX.
    Iteration and scratch storage are bounded by the newly supplied date.
    """
    if type(business_date) is not date or not isinstance(rows, Iterable) or isinstance(rows, (str, bytes, Mapping)):
        raise ValueError('Explicit BTR date and BPR rows required')
    fields = ('PhysicalInventoryPen', 'PhysicalInventoryColor', 'DispatchPen', 'DispatchColor',
              'TechPen', 'TechColor', 'EcoPen', 'EcoColor')
    groups = {}
    for row in rows:
        if _day(row['ReportDate']) != business_date:
            raise ValueError('BTR observation belongs to a different date')
        spelling = row['SKUCode'], row['WHCode']
        key = group_key(*spelling)
        if key not in groups:
            groups[key] = spelling, 1, [row[field] for field in fields]
            continue
        original, count, maxima = groups[key]
        if original != spelling:
            raise ValueError(f'SOURCE_ORDER_AMBIGUITY: BTR pivot identity spelling {key}')
        for i, field in enumerate(fields):
            value = row[field]
            if value is not None and (maxima[i] is None or value > maxima[i]):
                maxima[i] = value
        groups[key] = original, count + 1, maxima
    for (sku, location), count, maxima in groups.values():
        yield DayCell(business_date, sku, location, count, *maxima)
