"""Sparse opening occurrence bookkeeping for the Norm log producers."""
from heapq import merge


class NormLogRemovals:
    """The ordered surviving opening prefix precedes every new occurrence."""

    def __init__(self, opening_count):
        if type(opening_count) is not int or opening_count < 0:
            raise ValueError('Explicit Norm log opening count required')
        self.opening_count = opening_count
        self._removed = []

    @property
    def remaining_prefix(self):
        return self.opening_count - len(self._removed)

    @property
    def removed_ordinals(self):
        return tuple(self._removed)

    def retain(self, rows, remove):
        prefix = self.remaining_prefix
        if len(rows) < prefix:
            raise ValueError('Norm log opening prefix is incomplete')

        retained = []
        removed = []
        earlier = iter(self._removed)
        gap = next(earlier, None)
        skipped = 0
        for ordinal, row in enumerate(rows):
            if not remove(row):
                retained.append(row)
            elif ordinal < prefix:
                # Map today's prefix index past holes left by earlier stages.
                original = ordinal + skipped
                while gap is not None and gap <= original:
                    skipped += 1
                    original += 1
                    gap = next(earlier, None)
                removed.append(original)

        if removed:
            self._removed = list(merge(self._removed, removed))
        return retained


def retain_norm_log(rows, remove, removals):
    if removals is None:
        return [row for row in rows if not remove(row)]
    return removals.retain(rows, remove)
