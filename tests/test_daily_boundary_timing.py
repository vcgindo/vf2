import unittest

from tools.daily_boundary_timing import DailyTiming


class DailyTimingTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.timing = DailyTiming(clock=lambda: self.now)

    def test_nested_intervals_partition_real_total_once(self):
        self.now = 2
        with self.timing.boundary('opening_calculation', 'execute_day'):
            self.now = 5
            with self.timing.boundary('diagnostics', 'capture'):
                self.now = 9
            self.now = 12
        self.now = 13
        result = self.timing.finish(published_consumable=False)
        self.assertEqual(result['elapsed_invocation_seconds'], 13)
        self.assertEqual(sum(result['exclusive_seconds'].values()), 13)
        self.assertEqual(result['exclusive_seconds']['opening_calculation'], 6)
        self.assertEqual(result['exclusive_seconds']['diagnostics'], 4)
        self.assertEqual(result['exclusive_seconds']['startup_orchestration'], 3)
        self.assertEqual(result['boundaries'][0]['elapsed_seconds'], 10)
        self.assertFalse(result['published_consumable'])

    def test_failure_retains_elapsed_and_propagates(self):
        with self.assertRaisesRegex(RuntimeError, 'denied'):
            with self.timing.boundary('presentation_publication_readiness', 'admit'):
                self.now = 3
                raise RuntimeError('denied')
        result = self.timing.finish(published_consumable=False)
        self.assertEqual(result['boundaries'][0]['status'], 'FAILED')
        self.assertEqual(result['elapsed_invocation_seconds'], 3)

    def test_invalid_or_unfinished_boundaries_are_not_silently_recorded(self):
        with self.assertRaises(ValueError):
            with self.timing.boundary('made_up', 'x'):
                pass
        with self.timing.boundary('actions', 'Apply/Sleep'):
            with self.assertRaises(ValueError):
                self.timing.finish(published_consumable=True)
        self.timing.finish(published_consumable=False)
        with self.assertRaises(ValueError):
            with self.timing.boundary('actions', 'late'):
                pass


if __name__ == '__main__':
    unittest.main()
