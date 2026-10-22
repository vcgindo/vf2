"""Ordered candidate bags for the existing ASCII SQL equality adapter.

Only candidate selection changes. Callers still apply their original predicate,
arithmetic, duplicate handling and ambiguous-update checks. Other comparators
and unqualified values retain the original scan and its error behavior.
"""
from mta.domain.complete_daily_scalars import ascii_equal

_UNQUALIFIED = object()


def _key(values):
    if any(value is not None and (not isinstance(value, str) or not value.isascii())
           for value in values):
        return _UNQUALIFIED
    return None if None in values else tuple(value.rstrip(' ').upper() for value in values)


class AsciiBagLookup:
    def __init__(self, rows, fields, equal):
        self.rows, self.fields = rows, fields
        self.index = {} if equal is ascii_equal else None
        if self.index is not None:
            for row in rows:
                self.add(row)

    def add(self, row):
        if self.index is None:
            return
        key = _key(tuple(row[field] for field in self.fields))
        if key is _UNQUALIFIED:
            self.index = None
        elif key is not None:
            self.index.setdefault(key, []).append(row)

    def candidates(self, row, fields):
        if self.index is None:
            return self.rows
        key = _key(tuple(row[field] for field in fields))
        if key is _UNQUALIFIED:
            return self.rows
        return self.index.get(key, ()) if key is not None else ()
