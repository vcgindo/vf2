"""A frozen retry retains its independent checks under compatible code."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from mta.runtime.production_daily import _inspection_frame


class NativeRetryOpeningAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.owner = SimpleNamespace(source=SimpleNamespace(digest='explicit-source'))

    def test_normal_and_retry_use_same_fresh_private_admission_before_frame(self):
        for retry in (None, 'preserved-failed-capture'):
            with self.subTest(retry=retry):
                calls = Mock()
                with patch('mta.runtime.ingestion_admission.preparation_source', return_value='fresh-readiness') as admit, \
                        patch('mta.mdm.production_families.certified_state_handle') as handle, \
                        patch('mta.mdm.production_families.frame_for_daily', return_value='frame') as frame:
                    calls.attach_mock(admit, 'admit')
                    calls.attach_mock(handle, 'handle')
                    calls.attach_mock(frame, 'frame')
                    self.assertEqual(_inspection_frame(self.owner, 'own-parent', retry), 'frame')
                self.assertEqual([call[0] for call in calls.mock_calls], ['admit', 'handle', 'frame'])
                admit.assert_called_once_with('explicit-source')
                handle.assert_called_once_with(self.owner, 'fresh-readiness')
                frame.assert_called_once_with(self.owner, 'own-parent')

    def test_no_certificate_preserves_original_exact_opening_path(self):
        with patch('mta.runtime.ingestion_admission.preparation_source', return_value=None), \
                patch('mta.mdm.production_families.certified_state_handle') as handle, \
                patch('mta.mdm.production_families.frame_for_daily', return_value='old-exact-frame') as frame:
            self.assertEqual(_inspection_frame(self.owner, None, 'failed-capture'), 'old-exact-frame')
        handle.assert_not_called()
        frame.assert_called_once_with(self.owner, None)

    def test_invalid_activated_authority_never_falls_back_to_old_frame(self):
        with patch('mta.runtime.ingestion_admission.preparation_source', side_effect=ValueError('authority differs')), \
                patch('mta.mdm.production_families.certified_state_handle') as handle, \
                patch('mta.mdm.production_families.frame_for_daily') as frame:
            with self.assertRaisesRegex(ValueError, 'authority differs'):
                _inspection_frame(self.owner, None, 'failed-capture')
        handle.assert_not_called()
        frame.assert_not_called()

    def test_invalid_private_handle_never_returns_frame(self):
        with patch('mta.runtime.ingestion_admission.preparation_source', return_value='fresh-readiness'), \
                patch('mta.mdm.production_families.certified_state_handle', side_effect=ValueError('seal differs')), \
                patch('mta.mdm.production_families.frame_for_daily') as frame:
            with self.assertRaisesRegex(ValueError, 'seal differs'):
                _inspection_frame(self.owner, None, 'failed-capture')
        frame.assert_not_called()
