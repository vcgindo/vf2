"""Qualified SQL text identities for daily DBM/BTR joins and groups.

Keys retain the source values for output spelling and tuple ordering.  Equality
and hashing use the retained ASCII CI/trailing-ordinary-space contract.  JOIN
keys containing NULL are deliberately incomparable; GROUP BY keys group NULLs.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.
"""
from itertools import count

from mta.domain.complete_daily_scalars import ascii_equal


_null_ordinals = count()


def _normalized(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("Canonical SQL identity must be text or NULL")
    # Keep qualification and error behavior owned by the pinned scalar helper.
    ascii_equal(value, value)
    return value.rstrip(" ").upper()


class _SqlIdentity:
    __slots__ = ("values", "_identity")
    group_nulls = False

    def __init__(self, values):
        self.values = tuple(values)
        normalized = tuple(_normalized(value) for value in self.values)
        if not self.group_nulls and None in normalized:
            normalized = (*normalized, ("JOIN_NULL", next(_null_ordinals)))
        self._identity = normalized

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __getitem__(self, item):
        return self.values[item]

    def __repr__(self):
        return repr(self.values)

    @property
    def normalized(self):
        return self._identity[:len(self.values)]

    def __lt__(self, other):
        if isinstance(other, _SqlIdentity):
            return self.values < other.values
        return NotImplemented

    def __hash__(self):
        return hash(self._identity)

    def __eq__(self, other):
        if not isinstance(other, _SqlIdentity):
            return NotImplemented
        return self._identity == other._identity


class SqlJoinKey(_SqlIdentity):
    pass


class SqlGroupKey(_SqlIdentity):
    group_nulls = True


def join_key(*values):
    return SqlJoinKey(values)


def group_key(*values):
    return SqlGroupKey(values)


def row_join_key(row):
    return join_key(row["SKUCode"], row.get("WhCode", row.get("WHCode")))


def value_join_key(value):
    return join_key(value)
