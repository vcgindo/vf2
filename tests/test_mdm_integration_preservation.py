"""Bounded family seams; no business-day execution or source installation."""
import os
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.mdm import families, integration_source
from mta.mdm import stop_pipo_capture, phase_controls_capture
from mta.serialization import digest


class IntegrationPreservationTests(unittest.TestCase):
    def test_all_registered_families_resolve_existing_workflow_boundaries(self):
        self.assertEqual(set(families.NAMES), set(range(1, 14)))
        for master_id in families.NAMES:
            for boundary in ('current', 'tasks', 'reads'):
                with self.subTest(master_id=master_id, boundary=boundary):
                    self.assertTrue(families.module(master_id, boundary).__name__.startswith('mta.mdm.'))
            self.assertIsNotNone(families.draft_model(master_id)[0])

    def test_invalid_season_anchor_cannot_partially_apply_force_opening(self):
        apply_force = Mock()
        prior = {'sentinel': [None, 0, 0]}
        before = deepcopy(prior)
        with patch('mta.mdm.force_capture.prepare_working_input', return_value=apply_force), \
             patch('mta.mdm.season_capture.prepare_working_input', side_effect=ValueError('wrong predecessor')):
            with self.assertRaisesRegex(ValueError, 'wrong predecessor'):
                integration_source.replace_working_inputs({}, prior, {}, None)
        apply_force.assert_not_called()
        self.assertEqual(prior, before)

    def test_uninstalled_captures_leave_original_openings_unchanged(self):
        prior = {'control_aux': {'phase_stops': [None], 'phase_requests': [0]}}
        before = deepcopy(prior)
        integration_source.replace_working_inputs({}, prior, {}, None)
        self.assertEqual(prior, before)

    def test_stop_and_phase_reject_foreign_predecessor_before_mutation(self):
        for key, module in (('stop_pipo', stop_pipo_capture), ('phase_controls', phase_controls_capture)):
            frozen = {'anchor': {'run_id': 'owned', 'output_digest': 'a'*64,
                                 'queue_digest': 'b'*64, 'generation': 1}}
            frozen['digest'] = digest(frozen)
            prior = {'control_aux': {'phase_stops': [None, 0]}}
            before = deepcopy(prior)
            with self.subTest(family=key), self.assertRaisesRegex(ValueError, 'own'):
                module.replace_working_input({key: frozen}, prior, {},
                    SimpleNamespace(pk='foreign', output_digest='a'*64))
            self.assertEqual(prior, before)

    def test_sealed_roster_does_not_allow_missing_or_extra_family_captures(self):
        source = SimpleNamespace(pk=7, digest='c'*64)
        identity = {'families': {'1': 'a', '2': 'b', '3': 'c', '13': 'd'}}
        snapshot = {'integration': identity, 'source_id': 7, 'source_digest': source.digest}
        with patch.object(integration_source, 'capture_identity', return_value=identity):
            with self.assertRaisesRegex(ValueError, 'roster'):
                integration_source.verify_capture(source, snapshot)
            snapshot['force'] = {}
            integration_source.verify_capture(source, snapshot)
            snapshot['season'] = {}
            with self.assertRaisesRegex(ValueError, 'roster'):
                integration_source.verify_capture(source, snapshot)
