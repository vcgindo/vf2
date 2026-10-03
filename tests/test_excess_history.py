"""Manifest boundaries; publication additionally requires PostgreSQL transaction proof."""
import os
import unittest
from datetime import date, timedelta
from types import SimpleNamespace

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-test-only-not-a-serving-secret')
import django
django.setup()

from mta.presentation.context import PublicationUnavailable
from mta.presentation.excess_history import checked_chain, run_identity, OPENING, TERMINAL_ID, TERMINAL_DIGEST
from mta.presentation.excess import PRODUCER_SHA


class ExcessHistoryTests(unittest.TestCase):
    def setUp(self):
        self.runs = []
        for index in range(12):
            prior = self.runs[-1] if self.runs else None
            self.runs.append(SimpleNamespace(pk=TERMINAL_ID if index == 11 else str(index),
                predecessor=prior, predecessor_id=prior.pk if prior else None,
                business_date=date(2026, 6, 6) + timedelta(days=index), kind='DAILY_CHAIN',
                status='SUCCEEDED', parity_summary={'status': 'PASS'}, input_digest='input',
                production_digest='production', output_digest=TERMINAL_DIGEST if index == 11 else str(index)))
        self.manifest = dict(version='fresh-excess-history-v1', opening=OPENING,
            retention_days=90, producer_sha256=PRODUCER_SHA, runs=list(map(run_identity, self.runs)))

    def test_exact_approved_chain(self):
        self.assertEqual(checked_chain(self.runs[-1], self.manifest), self.runs)

    def test_same_date_trial_identity_cannot_replace_accepted_run(self):
        self.manifest['runs'][0] = {**self.manifest['runs'][0], 'run_id': 'shallow-trial'}
        with self.assertRaisesRegex(PublicationUnavailable, 'chain_mismatch'):
            checked_chain(self.runs[-1], self.manifest)

    def test_missing_day_and_changed_opening_are_denied(self):
        self.runs[4].business_date += timedelta(days=1)
        with self.assertRaisesRegex(PublicationUnavailable, 'chain_mismatch'):
            checked_chain(self.runs[-1], self.manifest)
        self.manifest['opening'] = {'business_date': '2026-06-05', 'ExcessInventoryDetails': []}
        with self.assertRaisesRegex(PublicationUnavailable, 'approval_binding_mismatch'):
            checked_chain(self.runs[-1], self.manifest)
