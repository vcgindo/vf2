"""The optional alert projection observes pre-clear state without altering it."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from mta.application import timeline_controls as controls


class ForceCaptureTests(unittest.TestCase):
    def run_stages(self, sink):
        state = {name: [] for name in controls.TABLES}
        state.update(force_requests=[dict(SKUCode='A', WhCode='L', NewNorm=12,
            Approved=True, RequestedBy='fixture')], dbm_master=[dict(Norm=12)],
            raw_master=[dict(Norm=12)])
        extra = {name: [] for name in controls.EXTRA_TABLES}
        day = dict(control_requests={name: [] for name in controls.REQUEST_TABLES},
                   accepted_feed=[], new_force_requests=[])
        profile = dict(from_ui=True, start_percent=100, force_flags={}, history_horizon=90)
        def stages(*args):
            current = deepcopy(state)
            yield 'UpdateNormChanges.sql', current
            current['force_requests'].clear()
            yield 'ClearForceNormChange.sql', current
        names = ('collect_phase_out', 'process_phase_out', 'collect_phase_in',
                 'process_phase_in', 'collect_seasons', 'process_seasons',
                 'apply_seasons', 'clear_phase_inputs')
        from contextlib import ExitStack
        with ExitStack() as stack:
            for name in names:
                stack.enter_context(patch.object(controls, name, side_effect=lambda value, *a, **k: value))
            stack.enter_context(patch.object(controls, 'control_stages', side_effect=stages))
            stack.enter_context(patch.object(controls, 'phase_exception_rows', return_value=[]))
            stack.enter_context(patch.object(controls, 'failed_force_rows', return_value=[]))
            return list(controls.timeline_control_stages('2026-06-06', '2026-06-05',
                state, extra, day, profile, [], [], force_alert_capture=sink))

    def test_capture_survives_clear_without_changing_output(self):
        sink = {}
        captured = self.run_stages(sink)
        self.assertEqual(captured, self.run_stages(None))
        self.assertEqual(captured[-1][1]['force_requests'], [])
        self.assertEqual(len(sink['ForceNormChange']), 1)
        self.assertTrue(sink['ForceNormChange'][0]['Approved'])
        self.assertEqual(set(sink), {'ForceNormChange', 'DBMMaster', 'MasterDataRaw'})

    def test_nonempty_sink_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'new empty'):
            self.run_stages({'ForceNormChange': []})
