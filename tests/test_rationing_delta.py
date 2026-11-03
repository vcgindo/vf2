"""Storage correspondence, with independent witnesses and the real producer."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import unittest

from mta.domain import btr_rationing_history as business
from mta.row_sequences import RecordRows
from mta.runtime.rationing_delta import changes, Occurrence, Fact, DispatchRevision, Expiry, Counts
from mta.serialization import storage


def row(day='2026-01-14', **overrides):
    values = {c['name']: (False if c['type'] == 'bit' else
                         0 if c['type'] == 'int' else
                         '0.00' if c['type'] == 'decimal' else None)
              for c in business.COLUMNS}
    values.update(ReportDate=day, SKUCode='S', WhCode='W', ParentWhCode='P',
                  GIT=10, Dispatch=None)
    values.update(overrides)
    return values


def prior(rows, position=0):
    return ((Occurrence(position, n), value) for n, value in enumerate(rows))


def apply_for_test(original, events, position=0):
    # Independent simple reconstruction: update/remove identified occurrences,
    # retain original insertion order, and append each new fact distinctly.
    values = {Occurrence(position, n): storage(deepcopy(r)) for n, r in enumerate(original)}
    for event in events:
        if isinstance(event, Fact):
            if event.occurrence in values:
                raise AssertionError('Duplicate occurrence')
            values[event.occurrence] = event.values
        elif isinstance(event, Expiry):
            del values[event.occurrence]
        elif isinstance(event, DispatchRevision):
            values[event.occurrence]['Dispatch'] = event.dispatch
    return list(values.values())


class RationingDeltaTests(unittest.TestCase):
    def classify(self, before, after, **options):
        args = dict(today='2026-01-15', position=1, capture_enabled=True, horizon=30)
        args.update(options)
        return list(changes(prior(before), after, **args))

    def test_empty_initialization_and_first_duplicate_facts(self):
        self.assertEqual(self.classify([], []), [Counts(0, 0, 0, 0, 0, 0)])
        today = row('2026-01-15')
        events = self.classify([], [today, today])
        self.assertEqual([e.occurrence for e in events[:-1]], [Occurrence(1, 0), Occurrence(1, 1)])
        self.assertEqual(events[-1], Counts(0, 0, 2, 0, 0, 2))
        self.assertEqual(apply_for_test([], events), [today, today])

    def test_real_producer_dispatch_seven_and_unchanged_payloads_not_emitted(self):
        before = [row(), row(), row(None), row('2026-01-13')]
        saved = deepcopy(before)
        incoming = {name: row('2026-01-15', GIT=14)[name] for name in business.SOURCE_FIELDS}
        after = business.collect('2026-01-15', before, [incoming],
            [dict(SKUCode='S', WHCode='W', ReportDate='2026-01-15', Receipts=3, Consumption=2)], [], 30)
        events = self.classify(before, after)
        # 14 - 10 + 3 = 7 for BOTH original duplicate occurrences.
        self.assertEqual(events[:2], [DispatchRevision(Occurrence(0, 0), 7),
                                     DispatchRevision(Occurrence(0, 1), 7)])
        self.assertEqual(sum(isinstance(e, Fact) for e in events), 1)
        self.assertEqual(events[-1], Counts(4, 4, 1, 2, 0, 5))
        self.assertEqual(apply_for_test(before, events), storage(after))
        self.assertEqual(before, saved)

    def test_own_successor_preserves_occurrences_and_old_publication(self):
        first = [row('2026-01-15'), row('2026-01-15')]
        second = [dict(r, Dispatch=7) for r in first] + [row('2026-01-16')]
        events = list(changes(prior(first, position=1), second,
            today='2026-01-16', position=2, capture_enabled=True, horizon=30))
        self.assertEqual(events[:2], [DispatchRevision(Occurrence(1, 0), 7),
                                     DispatchRevision(Occurrence(1, 1), 7)])
        self.assertEqual(events[2].occurrence, Occurrence(2, 0))
        self.assertEqual(apply_for_test(first, events, position=1), second)
        self.assertEqual([r['Dispatch'] for r in first], [None, None])

    def test_cutoff_today_replacement_null_and_future_order(self):
        before = [row('2025-12-16'), row('2025-12-17'), row('2026-01-15'),
                  row(None), row('2026-01-20')]
        after = [before[1], before[3], before[4], row('2026-01-15', GIT=22)]
        events = self.classify(before, after)
        self.assertEqual([e.occurrence for e in events if isinstance(e, Expiry)],
                         [Occurrence(0, 0), Occurrence(0, 2)])
        self.assertEqual(events[-1], Counts(5, 3, 1, 0, 2, 4))
        self.assertEqual(apply_for_test(before, events), after)

    def test_zero_negative_horizon_and_no_resurrection_after_expiry(self):
        before = [row('2026-01-14'), row(None), row('2026-01-20')]
        for horizon in (0, -1):
            events = self.classify(before, before[1:], horizon=horizon)
            self.assertEqual(events, [Expiry(Occurrence(0, 0)), Counts(3, 2, 0, 0, 1, 2)])
        # Enlarging the horizon does not rediscover an expired payload: the
        # accepted predecessor stream contains only its then-visible members.
        after = before[1:] + [row('2026-01-16')]
        events = list(changes([(Occurrence(0, 1), before[1]), (Occurrence(0, 2), before[2])],
            after, today='2026-01-16', position=2, capture_enabled=True, horizon=90))
        self.assertEqual(events[-1], Counts(2, 2, 1, 0, 0, 3))

    def test_actual_global_negative_dispatch_clamp_and_disabled_passthrough(self):
        before = [row(None, Dispatch=-9), row('2026-01-13', Dispatch=-2)]
        after = business.collect('2026-01-15', before, [], [], [], 30)
        events = self.classify(before, after)
        self.assertEqual(events[:2], [DispatchRevision(Occurrence(0, 0), 0),
                                     DispatchRevision(Occurrence(0, 1), 0)])
        self.assertEqual(apply_for_test(before, events), after)
        self.assertEqual(self.classify(before, before, capture_enabled=False, horizon=None),
                         [Counts(2, 2, 0, 0, 0, 2)])
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.classify(before, after, capture_enabled=False)
        with self.assertRaisesRegex(ValueError, 'cannot append'):
            self.classify([], [row('2026-01-15')], capture_enabled=False)

    def test_driver_date_decimal_wire_values_and_typed_drift(self):
        original = row(date(2026, 1, 14), DispatchPen=Decimal('1.00'))
        after = storage(original)
        self.assertEqual(self.classify([original], [after]), [Counts(1, 1, 0, 0, 0, 1)])
        bit = next(c['name'] for c in business.COLUMNS if c['type'] == 'bit')
        for change in ({bit: 0}, {'DispatchPen': '1.0'}, {'SKUCode': 's '}, {'GIT': None}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'immutable'):
                self.classify([original], [dict(after, **change)])

    def test_late_mismatch_has_no_terminal_counts_and_never_mutates_inputs(self):
        before = [row(Dispatch=None), row('2026-01-13')]
        after = [dict(before[0], Dispatch=7), dict(before[1], GIT=999)]
        saved = deepcopy((before, after))
        stream = changes(prior(before), after, today='2026-01-15', position=1,
                         capture_enabled=True, horizon=30)
        self.assertEqual(next(stream), DispatchRevision(Occurrence(0, 0), 7))
        with self.assertRaisesRegex(ValueError, 'immutable'):
            next(stream)
        self.assertEqual((before, after), saved)

    def test_streaming_more_than_ten_thousand_rows_without_indexing(self):
        count = 10001
        visits = dict(prior=0, closing=0)
        def previous():
            for n in range(count):
                visits['prior'] += 1
                yield row(None)
        def output():
            for _ in range(count):
                visits['closing'] += 1
                yield row(None)
        # This is the actual runtime's lazy collection type, not a list stub.
        lazy = RecordRows(count, output)
        events = list(changes(prior(RecordRows(count, previous)), lazy, today='2026-01-15', position=1,
                             capture_enabled=True, horizon=30))
        self.assertEqual(events, [Counts(count, count, 0, 0, 0, count)])
        self.assertEqual(visits, dict(prior=count, closing=count))

    def test_occurrence_guards_and_missing_retained_member(self):
        for coordinates in ((True, 0), (0, -1), (1.0, 0)):
            with self.subTest(coordinates=coordinates), self.assertRaises(ValueError):
                Occurrence(*coordinates)
        for source in ([(Occurrence(1, 0), row())],
                       [(Occurrence(0, 0), row()), (Occurrence(0, 0), row())],
                       [(Occurrence(0, 1), row()), (Occurrence(0, 0), row())]):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'ownership/order'):
                list(changes(source, [row(), row()], today='2026-01-15', position=1,
                             capture_enabled=True, horizon=30))
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.classify([row()], [])

    def test_new_fact_and_roster_refusals(self):
        for invalid in (row('2026-01-14'), row('2026-01-15', Dispatch=7)):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'current producer'):
                self.classify([], [invalid])
        for invalid in ({}, dict(reversed(list(row().items())))):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'roster'):
                self.classify([row()], [invalid])
        for horizon in (-(2**31), 2**31 - 1, None, True):
            with self.subTest(horizon=horizon), self.assertRaises(ValueError):
                self.classify([], [], horizon=horizon)


if __name__ == '__main__':
    unittest.main()
