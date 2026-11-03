from contextlib import ExitStack
from copy import deepcopy
import unittest
from unittest.mock import patch

from mta.application import timeline_controls
from mta.application.history_removals import NormLogRemovals
from mta.serialization import digest


DAY = '2026-10-26'
OPENING_DAY = '2026-10-25'


def pair(sku, **fields):
    return dict(SKUCode=sku, WhCode='DP010290', **fields)


def log(sku, reason, *, day=DAY, old=10, new=8):
    return pair(sku, OldNorm=old, NewNorm=new, NormChangeDate=day, NormChangeReason=reason)


class NormLogRemovalsTests(unittest.TestCase):
    def test_all_five_predicates_keep_the_exact_typed_log(self):
        opening = [log('A', None), log('O', 102), log('F', 101), log('O', 102),
                   log('S', 104), log('I', 103), log('A', 5),
                   log('A', 5, day=OPENING_DAY), log('S', 104, day='2026-10-27'),
                   log('B', 5), log('F', 101, day=None)]
        state = {name: [] for name in timeline_controls.TABLES}
        state.update(log=opening, IntermediateTables={},
            last_batch=[dict(LastRunDate=OPENING_DAY+'T00:00:00')],
            dbm_master=[pair(sku, Norm=10, ParentWhCode=None) for sku in ('A', 'F', 'S')],
            phase_out=[pair('O', OldNorm=10, NewNorm=10)],
            phase_in=[pair('I', OldNorm=10, NewNorm=None)],
            seasonality=[pair('S', Status=1, LastProcessedOn=DAY, NewNorm=8)],
            suggestions=[pair('A', Type=5, NewNorm=8)], reason_codes=[dict(Id=5)],
            forced=[pair('F', OldNorm=10, NewNorm=8, ChangeDate=OPENING_DAY)])
        extra = {name: [] for name in timeline_controls.EXTRA_TABLES}
        day = dict(control_requests={name: [] for name in timeline_controls.REQUEST_TABLES},
                   accepted_feed=[pair('A')], new_force_requests=[])
        profile = dict(from_ui=True, start_percent=100, history_horizon=None,
                       force_flags=dict(from_ui=True, ignore_master_norm=False, nms_active=False))
        removals = NormLogRemovals(len(opening))
        before = deepcopy(state)

        # Isolate the five log writers while retaining the real stage dispatch.
        with ExitStack() as stack:
            for collector in ('collect_phase_out', 'collect_phase_in', 'collect_seasons', 'process_seasons'):
                stack.enter_context(patch.object(timeline_controls, collector,
                    side_effect=lambda state, *args, **kwargs: state))
            args = (DAY, OPENING_DAY, state, extra, day, profile, [], [])
            baseline = list(timeline_controls.timeline_control_stages(*args))
            captured = list(timeline_controls.timeline_control_stages(*args, norm_log_removals=removals))

        self.assertEqual(digest(captured), digest(baseline))
        self.assertEqual(state, before)
        stages = {name: rows['log'] for name, rows, _ in captured}
        self.assertEqual(stages['ProcessPhaseOut.sql'], [opening[i] for i in (0, 2, 4, 5, 6, 7, 8, 9, 10)])
        self.assertEqual(stages['ProcessPhaseIn.sql'], [opening[i] for i in (0, 2, 4, 6, 7, 8, 9, 10)])
        self.assertEqual(removals.removed_ordinals, (1, 2, 3, 4, 5, 6))
        self.assertEqual(removals.remaining_prefix, 5)
        self.assertEqual(captured[-1][1]['log'], [opening[i] for i in (0, 7, 8, 9, 10)] +
                         [log('S', 104), log('A', 5), log('F', 101)])

    def test_later_filter_distinguishes_suffix_rows_from_opening_occurrences(self):
        removals = NormLogRemovals(5)
        rows = removals.retain(['x', 'a', 'x', 'b', 'x'], lambda row: row == 'x')
        rows.extend(['a', 'c', 'b'])
        self.assertEqual(removals.retain(rows, lambda row: row == 'a'), ['b', 'c', 'b'])
        self.assertEqual(removals.removed_ordinals, (0, 1, 2, 4))
        self.assertEqual(removals.remaining_prefix, 1)
        self.assertEqual(removals.retain(['b', 'c', 'b'], lambda row: row == 'b'), ['c'])
        self.assertEqual(removals.removed_ordinals, (0, 1, 2, 3, 4))
        self.assertEqual(removals.remaining_prefix, 0)
