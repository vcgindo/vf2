"""Storage correspondence for qualified, already-calculated DBM history bags.

This is not a business producer or a database writer. These seven producers
retain an ordered subsequence of their own prior occurrences and then append
today's occurrences. No pair/date key, deduplication, row matching heuristic or
ancestor replay establishes identity. A caller must consume the entire stream
atomically: only the final Counts event certifies complete correspondence.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
import json
import math
from pathlib import Path

from mta.domain.dbm_report_dates import horizon_cutoff
from mta.serialization import storage, digest


# (date field, cutoff rule, NULL membership). These are storage correspondence
# contracts for the terminal images, not overrides of the producer's controls.
# Source owners: dbm_ingestion, dbm_daily_cleanup, dbm_order_summary,
# dbm_postrules, dbm_suspension_history. Aliases and phase images are deliberately
# not activated merely because they use the same physical column schema.
FAMILIES = {
    'closing/dbm/DailyConsumption': ('ReportDate', 'configured-strict', True),
    'closing/dbm/OrderData': ('ImportDate', 'none', True),
    'closing/dbm/OrderDataSummary': ('ImportDate', 'ninety-inclusive', False),
    'closing/dbm/SuggestionsLog': ('SuggestionDate', 'literal-current', True),
    'closing/dbm/DiscardedSuggestions': ('SuggestionDate', 'literal-current', True),
    'closing/dbm/SpikeReport': ('SuspendFromDate', 'literal-current', True),
    'closing/dbm/SuspendHistory': ('ReportDate', 'ninety-strict', False),
}


@dataclass(frozen=True, order=True)
class Occurrence:
    position: int
    ordinal: int

    def __post_init__(self):
        if any(type(v) is not int or v < 0 for v in (self.position, self.ordinal)):
            raise ValueError('History occurrence requires nonnegative integer coordinates')


@dataclass(frozen=True)
class Fact:
    occurrence: Occurrence
    values: dict


@dataclass(frozen=True)
class Removal:
    occurrence: Occurrence


@dataclass(frozen=True)
class Counts:
    prior: int
    retained: int
    inserted: int
    removed: int
    closing: int


@cache
def _tables():
    catalogue = json.loads((Path(__file__).resolve().parents[1] /
                           'config/production_state_schema_v1.json').read_text())
    if digest(catalogue) != '84f01ea82866a3898dd134eafac32bca4e35daa193aca9d55da4716074b1e512':
        raise ValueError('Pinned history column schema differs')
    return catalogue['tables']


@cache
def fields(family):
    if family not in FAMILIES:
        raise ValueError('Unqualified dated history family')
    return tuple(name for name, _ in _tables()['DBM/'+family.rsplit('/', 1)[1]])


def supports_descriptor(family, descriptors, count):
    """Qualify the complete native shape before selecting the future writer.

    Existing typed transport also supports subsets and case-mapped field names.
    Those are not silently padded or admitted here; they need the exact old
    image path until their producer correspondence is separately qualified.
    """
    if type(count) is not int or count < 0 or not isinstance(descriptors, list):
        return False
    expected = fields(family)
    if not descriptors:
        return count == 0
    if len(descriptors) != len(expected):
        return False
    if any(not isinstance(d, (list, tuple)) or len(d) != 3 or
           d[0] != d[1] or d[2] not in ('str', 'int', 'float', 'bool') for d in descriptors):
        return False
    return {d[0] for d in descriptors} == set(expected)


def _date(value):
    if value is None or type(value) is date:
        return value
    if type(value) is str:
        return date.fromisoformat(value)
    raise ValueError('History date wire type differs')


def _row(value, columns):
    if not isinstance(value, dict) or set(value) != set(columns):
        raise ValueError('History field roster differs')
    result = storage(value)
    if any(v is not None and type(v) not in (str, int, float, bool) for v in result.values()):
        raise ValueError('History requires typed scalar fields')
    if any(type(v) is float and not math.isfinite(v) for v in result.values()):
        raise ValueError('History requires finite scalar fields')
    return result


def _same(left, right):
    # Python equality alone collapses -0.0 and +0.0, whose persisted canonical
    # bytes differ. Decimal scale has already been retained as wire text.
    return type(left) is type(right) and (left.hex() == right.hex() if type(left) is float else left == right)


def changes(prior, closing, *, family, today, position, horizon=None):
    """Emit only additions/removals from a qualified ordered history transition.

    ``prior`` yields (Occurrence, row), authenticated by its existing storage
    owner. ``closing`` is the unchanged engine's complete terminal image.
    A negative/zero configured horizon can remove today's new observations too;
    this classifier neither restores them nor substitutes a default horizon.
    Runtime integration must bind horizon to this run's frozen settings.
    """
    columns = fields(family)
    field, rule, nullable = FAMILIES[family]
    today = _date(today)
    if today is None or type(position) is not int or position < 1:
        raise ValueError('History requires a business date and positive cut position')
    if rule == 'configured-strict':
        cutoff = horizon_cutoff(today, horizon, inclusive=False)
    else:
        if horizon is not None:
            raise ValueError('Unexpected history horizon override')
        cutoff = today-timedelta(days=90) if rule.startswith('ninety-') else None

    def in_window(day):
        if day is None:
            if not nullable:
                raise ValueError('NULL date has no qualified retention correspondence')
            return True
        if cutoff is None:
            return True
        return day >= cutoff if rule == 'ninety-inclusive' else day > cutoff

    current = iter(closing)
    missing = object()
    previous_occurrence = None
    seen = retained = inserted = removed = 0
    for occurrence, original in prior:
        if (type(occurrence) is not Occurrence or occurrence.position >= position or
                previous_occurrence is not None and occurrence <= previous_occurrence):
            raise ValueError('History prior occurrence ownership/order differs')
        previous_occurrence = occurrence
        before = _row(original, columns)
        stamp = _date(before[field]) if rule != 'literal-current' else before[field]
        seen += 1
        # Postrules compare str(value), unlike ingestion's parsed SQL dates.
        # Preserve that owner distinction even for noncanonical direct inputs.
        keep = stamp != today.isoformat() if rule == 'literal-current' else stamp != today and in_window(stamp)
        if not keep:
            removed += 1
            yield Removal(occurrence)
            continue
        raw = next(current, missing)
        if raw is missing:
            raise ValueError('Retained history occurrence is missing')
        after = _row(raw, columns)
        if any(not _same(before[k], after[k]) for k in columns):
            raise ValueError('Retained history values/type/order differ')
        retained += 1
    for raw in current:
        row = _row(raw, columns)
        current_day = row[field] == today.isoformat() if rule == 'literal-current' else _date(row[field]) == today
        if not current_day or not in_window(today):
            raise ValueError('New history fact must belong to the current retained producer')
        yield Fact(Occurrence(position, inserted), row)
        inserted += 1
    yield Counts(seen, retained, inserted, removed, retained+inserted)
