from copy import deepcopy
import unittest

from mta.domain.complete_daily_fullkit import (
    initialise_fullkit, file_availability, fullkit_outcome, post_run_fullkit)
from mta.domain.complete_daily_scalars import ascii_equal


class FullkitTests(unittest.TestCase):
    def settings(self):
        return [dict(Parameter='FullkitAvailable', Value='0'),
                dict(Parameter='FullkitCheckdate', Value='2026-06-05')]

    def test_initialise_updates_existing_rows_and_resets_resolution(self):
        settings = self.settings()
        files = [dict(Id=1, Type='DataFiles', Path='owned', FileName='daily.csv',
                      Exists=True, ResolvedPath='old', ResolvedFileName='old')]
        before = deepcopy((settings, files))
        result = initialise_fullkit(settings, files, '2026-06-06', equal=ascii_equal)
        self.assertEqual(result['CriticalFiles'][0], files[0] | dict(
            Exists=False, ResolvedPath=None, ResolvedFileName=None))
        self.assertEqual(result['ImporterSettingsTbl'][1]['Value'], '2026-06-06')
        self.assertEqual((settings, files), before)
        self.assertEqual(initialise_fullkit([], [], '2026-06-06', equal=ascii_equal),
                         dict(ImporterSettingsTbl=[], CriticalFiles=[]))

    def test_missing_goahead_cannot_be_erased_by_present_data(self):
        files = [dict(Type='GoAheadFiles', Exists=False), dict(Type='DataFiles', Exists=True),
                 dict(Type='DataFiles', Exists=None)]
        go = file_availability(files, 'GoAheadFiles', previous=True, equal=ascii_equal)
        data = file_availability(files, 'DataFiles', previous=go['files_available'], equal=ascii_equal)
        self.assertEqual(go, dict(missing_count=1, files_available=False))
        self.assertEqual(data, dict(missing_count=0, files_available=False))

    def test_failure_marks_existing_flags_and_requires_local_alert_intent(self):
        for checks in ((False, True, True), (True, False, True), (True, True, False)):
            result = fullkit_outcome(self.settings(), go_ahead=checks[0],
                files_available=checks[1], daily_data_available=checks[2], equal=ascii_equal)
            self.assertTrue(result['AbortRun'])
            self.assertTrue(result['daily_unavailability_alert_required'])
            self.assertEqual(result['ImporterSettingsTbl'][0]['Value'], '0')
        with self.assertRaisesRegex(ValueError, 'Actual fullkit'):
            fullkit_outcome([], go_ahead=None, files_available=True,
                            daily_data_available=True, equal=ascii_equal)

    def test_post_run_duplicate_count_quirk_and_skipped_scopes_preserved(self):
        # Two matching duplicate flags pass native COUNT=2 even without a date;
        # adding the matching date makes three and fails. Do not silently fix it.
        rows = [dict(Parameter='FullkitAvailable', Value='1')] * 2
        self.assertFalse(post_run_fullkit(rows, '2026-06-06', scope='PostDBM',
                                         equal=ascii_equal)['AbortPostRun'])
        rows.append(dict(Parameter='FullkitCheckdate', Value='2026-06-06'))
        self.assertTrue(post_run_fullkit(rows, '2026-06-06', scope='PostDBM',
                                        equal=ascii_equal)['AbortPostRun'])
        for scope in ('UptoBPR', 'UptoDBM', ''):
            self.assertEqual(post_run_fullkit([], '2026-06-06', scope=scope, equal=ascii_equal),
                             dict(checked=False, matching_count=None, AbortPostRun=False))

    def test_current_and_stale_date(self):
        rows = initialise_fullkit(self.settings(), [], '2026-06-06', equal=ascii_equal)['ImporterSettingsTbl']
        self.assertFalse(post_run_fullkit(rows, '2026-06-06', scope='PostBPR', equal=ascii_equal)['AbortPostRun'])
        self.assertTrue(post_run_fullkit(rows, '2026-06-07', scope='PostBPR', equal=ascii_equal)['AbortPostRun'])


if __name__ == '__main__':
    unittest.main()
