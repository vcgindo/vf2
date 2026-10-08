"""Bounded policy identity/denial checks, separate from real PostgreSQL proof."""
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import unittest
from uuid import UUID

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.test import override_settings
from mta.presentation import qualified_consumption as policy, daily_publication
from mta.presentation.context import PublicationUnavailable


class QualifiedConsumptionTests(unittest.TestCase):
    def owner(self):
        row = policy.pins()['runs'][0]
        return SimpleNamespace(pk=UUID(row['run_id']), business_date=date.fromisoformat(row['date']),
            kind='DAILY_CHAIN', status='SUCCEEDED', predecessor_id=None, parity_summary={},
            **{k: row[k] for k in ('input_digest', 'output_digest', 'production_digest')})

    def opt_in(self, **overrides):
        values = dict(VF_MTA_CONSUMPTION_POLICY=policy.POLICY, VF_MTA_DAILY_PUBLICATION=True,
                      VF_MTA_SYNTHETIC_ROSTER='core-without-bor-v1', VF_MTA_ACTIONS_ENABLED=False,
                      VF_MTA_PERMISSIONS_SHA256='', VF_MTA_HIERARCHY_SHA256='')
        values.update(overrides)
        return override_settings(**values)

    def test_default_and_unknown_policy_never_supply_missing_images(self):
        with override_settings(VF_MTA_CONSUMPTION_POLICY=''):
            self.assertFalse(policy.enabled())
            self.assertIsNone(policy.empty_metadata(object(), policy.REMARKS))
            with self.assertRaisesRegex(PublicationUnavailable, 'not_enabled'):
                policy.owner(self.owner())
        with override_settings(VF_MTA_CONSUMPTION_POLICY='unapproved'):
            with self.assertRaisesRegex(PublicationUnavailable, 'unknown_consumption_policy'):
                policy.enabled()

    def test_only_exact_approved_owner_and_native_qualification(self):
        with self.opt_in():
            run = self.owner()
            self.assertEqual(policy.owner(run)['run_id'], str(run.pk))
            for name, bad in (('output_digest', 'x'*64), ('business_date', date(2026,6,8)),
                              ('predecessor_id', UUID(int=1)), ('status', 'RUNNING'),
                              ('parity_summary', {'status': 'PASS'})):
                previous = getattr(run, name)
                setattr(run, name, bad)
                with self.assertRaisesRegex(PublicationUnavailable, 'owner_changed'):
                    policy.owner(run)
                setattr(run, name, previous)
            run.pk = UUID(int=1)
            with self.assertRaisesRegex(PublicationUnavailable, 'not_approved'):
                policy.owner(run)

    def test_no_action_roster_or_access_expansion(self):
        for change in (dict(VF_MTA_ACTIONS_ENABLED=True), dict(VF_MTA_DAILY_PUBLICATION=False),
                       dict(VF_MTA_SYNTHETIC_ROSTER=''), dict(VF_MTA_HIERARCHY_SHA256='wrong'),
                       dict(VF_MTA_PERMISSIONS_SHA256='wrong')):
            with self.opt_in(**change), self.assertRaises(PublicationUnavailable):
                policy.owner(self.owner())

    def test_hierarchy_is_bound_to_exact_two_outputs(self):
        raw = (Path(__file__).resolve().parents[1]/'baseline/cohort3-hierarchy-v1.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), policy.HIERARCHY_SHA)
        manifest = json.loads(raw)
        self.assertEqual(manifest['publications'], [dict(run_id=r['run_id'],
            business_date=r['date'], output_digest=r['output_digest']) for r in policy.pins()['runs']])
        self.assertEqual(manifest['allowed_fields'], {'products':['SL1','SL2','SL3'],
                                                     'locations':['LL1','LL2','LL3']})

    def test_qualified_config_and_recipe_cannot_reuse_strict_seals(self):
        with override_settings(VF_MTA_CONSUMPTION_POLICY=''):
            strict = daily_publication.configuration_identity(), daily_publication.recipe_identity()
        with self.opt_in():
            qualified = daily_publication.configuration_identity(), daily_publication.recipe_identity()
        self.assertNotEqual(strict[0], qualified[0])
        self.assertNotEqual(strict[1], qualified[1])
        with override_settings(VF_MTA_CONSUMPTION_POLICY=''):
            self.assertEqual(strict, (daily_publication.configuration_identity(), daily_publication.recipe_identity()))
