"""Storage correspondence for already-calculated rationing history.

This module neither runs the business producer nor authorizes a database write.
Its caller must bind the accepted lineage and consume the entire stream inside
the existing atomic writer. A late mismatch invalidates ALL preceding events.
Only the final Counts event certifies that the input streams were exhausted.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from mta.domain.btr_rationing_history import FIELDS, integer
from mta.serialization import storage


@dataclass(frozen=True, order=True)
class Occurrence:
    position: int
    ordinal: int

    def __post_init__(self):
        if any(type(value) is not int or value < 0
               for value in (self.position, self.ordinal)):
            raise ValueError('Rationing occurrence requires nonnegative integer coordinates')


@dataclass(frozen=True)
class Fact:
    occurrence: Occurrence
    values: dict


@dataclass(frozen=True)
class DispatchRevision:
    occurrence: Occurrence
    dispatch: int | None


@dataclass(frozen=True)
class Expiry:
    occurrence: Occurrence


@dataclass(frozen=True)
class Counts:
    prior: int
    retained: int
    inserted: int
    revised: int
    expired: int
    closing: int


def _date(value):
    if value is None:
        return None
    if type(value) is str:
        return date.fromisoformat(value)
    if type(value) is date:
        return value
    raise ValueError('Rationing storage date representation differs')


def _row(value, inherited_order=FIELDS):
    if not isinstance(value, dict) or tuple(value) not in (FIELDS, inherited_order):
        raise ValueError('Rationing storage ordered field roster differs')
    # Match the existing persisted wire contract, including date/Decimal to
    # strings. Do not coerce bool to int, normalize codes or collapse NULLs.
    result = storage(value)
    _date(result['ReportDate'])
    if result['Dispatch'] is not None:
        integer(result['Dispatch'], 'stored Dispatch')
    return result


def _equal(left, right, *, allow_dispatch):
    return all(name == 'Dispatch' and allow_dispatch or
               type(left[name]) is type(right[name]) and left[name] == right[name]
               for name in FIELDS)


def changes(prior, closing, *, today, position, capture_enabled, horizon=None, inherited_order=FIELDS):
    """Yield only actual changes, followed by Counts; never retain whole bags.

    ``prior`` yields (Occurrence, row) in accepted occurrence order. ``closing``
    yields the unchanged engine's complete output. Membership follows the
    producer's ordered retained-prefix/current-append contract, not key matching.
    Foreign-lineage and accepted-owner checks remain the database owner's job.
    """
    if inherited_order != FIELDS and (len(inherited_order) != len(FIELDS) or set(inherited_order) != set(FIELDS)):
        raise ValueError('Rationing predecessor descriptor roster differs')
    if type(position) is not int or position < 1:
        raise ValueError('Rationing cut position must be a positive integer')
    if type(capture_enabled) is not bool:
        raise ValueError('Rationing capture selection must be explicit')
    today = _date(today)
    if today is None:
        raise ValueError('Rationing cut requires a business date')
    cutoff = None
    if capture_enabled:
        integer(horizon, 'RationingHistoryHorizonBTR')
        integer(-horizon, 'negative horizon')
        try:
            cutoff = today - timedelta(days=horizon)
        except (OverflowError, ValueError) as error:
            raise ValueError('BTR history cutoff outside date range') from error

    current = iter(closing)
    absent = object()
    previous_occurrence = None
    seen = retained = inserted = revised = expired = 0
    for occurrence, original in prior:
        if (type(occurrence) is not Occurrence or occurrence.position >= position
                or previous_occurrence is not None and occurrence <= previous_occurrence):
            raise ValueError('Rationing prior occurrence ownership/order differs')
        previous_occurrence = occurrence
        before = _row(original, inherited_order)
        seen += 1
        day = _date(before['ReportDate'])
        keep = not capture_enabled or day is None or (day != today and day > cutoff)
        if not keep:
            expired += 1
            yield Expiry(occurrence)
            continue
        raw = next(current, absent)
        if raw is absent:
            raise ValueError('Rationing retained occurrence is missing')
        after = _row(raw, inherited_order)
        if not _equal(before, after, allow_dispatch=capture_enabled):
            raise ValueError('Rationing retained immutable values/type/order differ')
        retained += 1
        if before['Dispatch'] != after['Dispatch']:
            revised += 1
            yield DispatchRevision(occurrence, after['Dispatch'])

    for raw in current:
        if not capture_enabled:
            raise ValueError('Disabled rationing capture cannot append facts')
        row = _row(raw)
        if _date(row['ReportDate']) != today or row['Dispatch'] is not None:
            raise ValueError('Rationing new fact must belong to the current producer')
        yield Fact(Occurrence(position, inserted), row)
        inserted += 1
    yield Counts(seen, retained, inserted, revised, expired, retained + inserted)
