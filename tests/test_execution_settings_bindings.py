"""Focused owner-binding proofs; no database connection or native acceptance."""
from collections.abc import Sequence
from copy import deepcopy
from datetime import date
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'execution-settings-bindings-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.application import persistent_master
from mta.runtime import capture_preparation, execution_settings, run_input_references
from mta.runtime.input_v3 import PROFILE_POPULATION_PATHS
from mta.serialization import digest


class UnreadablePopulation(Sequence):
    """Any population access would invalidate this metadata-only proof."""
    def __len__(self):
        raise AssertionError('Population length must not be inspected')

    def __iter__(self):
        raise AssertionError('Population must not be enumerated')

    def __getitem__(self, index):
        raise AssertionError('Population must not be indexed')


class ProfilePopulationReferenceTests(unittest.TestCase):
    def fixture(self):
        initialized = SimpleNamespace(pk='initialized-owner', input_manifest_digest='a' * 64,
            input_digest='b' * 64, configuration_digest='c' * 64)
        raw = dict(profile={}, opening=None,
                   execution_settings={'profile_digest': 'd' * 64})
        for path in PROFILE_POPULATION_PATHS:
            owner = raw
            keys = path.split('/')[1:]
            for key in keys[:-1]:
                owner = owner.setdefault(key, {})
            owner[keys[-1]] = UnreadablePopulation()
        return initialized, raw

    def test_changed_profile_references_every_present_finite_population_without_reading(self):
        initialized, raw = self.fixture()
        self.assertEqual(len(PROFILE_POPULATION_PATHS), 13)
        with patch('mta.runtime.ingestion_models.MasterInputRevision.objects.get',
                   side_effect=AssertionError('No ORM lookup is needed')):
            result = run_input_references.owners(initialized, raw, 'unused', unchanged=False)
        self.assertEqual(set(result), set(PROFILE_POPULATION_PATHS))
        self.assertNotIn('input/profile', result)
        for path, reference in result.items():
            self.assertEqual(reference, dict(kind='INITIALIZATION', owner_id=str(initialized.pk),
                path=path, manifest_digest=initialized.input_manifest_digest,
                content_digest=initialized.input_digest))

    def test_absent_optional_sources_stay_absent_and_opening_keeps_its_owner(self):
        initialized, raw = self.fixture()
        del raw['profile']['daily']['module_sources']
        raw['opening'] = {'state': UnreadablePopulation()}
        result = run_input_references.owners(initialized, raw, 'unused', unchanged=False)
        expected = {path for path in PROFILE_POPULATION_PATHS if '/module_sources/' not in path}
        self.assertEqual(set(result), expected | {'input/opening'})
        self.assertEqual(result['input/opening']['owner_id'], str(initialized.pk))

    def test_unchanged_and_historical_profiles_keep_the_original_whole_alias(self):
        for has_settings in (False, True):
            initialized, raw = self.fixture()
            if has_settings:
                raw['execution_settings']['profile_digest'] = initialized.configuration_digest
            else:
                raw.pop('execution_settings')
            with self.subTest(has_settings=has_settings):
                result = run_input_references.owners(initialized, raw, 'unused', unchanged=False)
                self.assertEqual(set(result), {'input/profile'})
                self.assertEqual(result['input/profile']['path'], 'input/profile')


class CaptureConfigurationBindingTests(unittest.TestCase):
    def state(self):
        return SimpleNamespace(initialization_id='installation', source_digest='a' * 64,
            certification_digest='b' * 64, master_revision_id='master', configuration_digest='c' * 64)

    def test_original_seed_format_is_exactly_unchanged_without_settings(self):
        state = self.state()
        expected = dict(contract=capture_preparation.CONTRACT, initialization_id='installation',
            source_digest='a' * 64, certification_digest='b' * 64, base_revision_id='master',
            configuration_digest='c' * 64, qualified_master_reuse=False)
        actual = capture_preparation.seed(state, reused=False)
        self.assertEqual(actual, expected)
        self.assertEqual(capture_preparation.effective_configuration(actual), state.configuration_digest)
        self.assertNotIn('execution_settings', actual)

    def test_frozen_effective_reference_is_separate_from_root_certificate_digest(self):
        state = self.state()
        reference = dict(contract=execution_settings.CONTRACT, id='version', initialization_id='installation',
                         revision=2, effective_date='2026-04-09', values_digest='d' * 64,
                         profile_digest='e' * 64)
        body = capture_preparation.seed(state, reused=True, execution_settings=reference)
        self.assertEqual(body['configuration_digest'], 'c' * 64)
        self.assertEqual(body['certification_digest'], 'b' * 64)
        self.assertEqual(body['execution_settings'], reference)
        self.assertEqual(capture_preparation.effective_configuration(body), 'e' * 64)
        self.assertTrue(body['qualified_master_reuse'])


class PersistentMasterSettingsBindingTests(unittest.TestCase):
    def fixture(self):
        original = dict(import_non_nms=False, delivery=dict(batch=dict(AutoDBMActive=0)))
        current = dict(import_non_nms=False, delivery=dict(batch=dict(AutoDBMActive=1)))
        previous = dict(contract=persistent_master.CONTRACT, qualified=True,
                        configuration_digest=digest(original), master_cut=[5, 10])
        parent = SimpleNamespace(production_manifest={'master_preparation': previous})
        owner = SimpleNamespace(pk='owner', configuration_digest=digest(original))
        base = {'contract': 'accepted-static-master', 'root': 'unchanged'}
        prior = SimpleNamespace(pk='prior', master_epoch=5, configuration_epoch=10, partitions=base)
        revision = SimpleNamespace(pk='new', master_epoch=5, configuration_epoch=13,
            partitions=dict(contract=execution_settings.PARTITION_CONTRACT, base=base))
        version = SimpleNamespace(pk='version', initialization_id=owner.pk, revision=2,
            effective_date=date(2026, 4, 9), values_digest='f' * 64, profile_digest=digest(current))
        reference = execution_settings.reference(version)
        day = dict(business_date='2026-04-09', raw_non_nms=[], raw_no_norm=[])
        snapshot = dict(nms_active=True, rows={
            'sku': {'approved': []}, 'location': {'approved': []},
            'skuloc': {'additions': [], 'modifications': [], 'removals': []}})
        return SimpleNamespace(**locals())

    def admitted_basis(self, fixture):
        # Only persisted-owner retrieval is mocked. Actual reference/date/profile
        # validation and the finite catalogue projection run unchanged.
        with patch('mta.runtime.ingestion_models.MasterInputRevision.objects.get', return_value=fixture.revision), \
             patch('mta.runtime.ingestion_models.MasterInputRevision.objects.filter') as revisions, \
             patch('mta.runtime.execution_setting_models.ExecutionSettingsVersion.objects.get', return_value=fixture.version):
            revisions.return_value.first.return_value = fixture.prior
            return execution_settings.master_basis(fixture.owner, fixture.parent, fixture.original,
                fixture.current, fixture.reference, fixture.revision.pk, fixture.day['business_date'])

    def test_admitted_basis_allows_only_previous_qualified_master_identity(self):
        f = self.fixture()
        basis = self.admitted_basis(f)
        self.assertIs(type(basis), execution_settings.MasterSettingsBasis)
        self.assertEqual(basis.cut, (5, 10))
        self.assertEqual(basis.previous_profile_digest, digest(f.original))
        self.assertFalse(persistent_master.eligible(f.current, f.day, f.snapshot, f.previous, (5, 13)))
        self.assertTrue(persistent_master.eligible(f.current, f.day, f.snapshot, f.previous,
                                                 (5, 13), settings_basis=basis))
        for change in ({'qualified': False}, {'configuration_digest': '0' * 64},
                       {'master_cut': [5, 9]}, {'contract': 'unqualified'}):
            with self.subTest(change=change):
                self.assertFalse(persistent_master.eligible(f.current, f.day, f.snapshot,
                    dict(f.previous, **change), (5, 13), settings_basis=basis))
        with self.assertRaisesRegex(ValueError, 'admitted owner'):
            persistent_master.eligible(f.current, f.day, f.snapshot, f.previous, (5, 13),
                                       settings_basis=dict(previous_profile_digest=digest(f.original), cut=(5, 10)))

    def test_original_source_and_queue_decisions_still_apply_with_basis(self):
        f = self.fixture()
        basis = self.admitted_basis(f)
        for family, names in (('sku', ('approved',)), ('location', ('approved',)),
                              ('skuloc', ('additions', 'modifications', 'removals'))):
            for name in names:
                for approved in (0, 1):
                    snapshot = deepcopy(f.snapshot)
                    snapshot['rows'][family][name] = [{'Approved': approved}]
                    with self.subTest(family=family, name=name, approved=approved):
                        original_decision = persistent_master.eligible(f.original, f.day, snapshot,
                            f.previous, (5, 10))
                        self.assertEqual(original_decision, approved == 0)
                        self.assertEqual(persistent_master.eligible(f.current, f.day, snapshot,
                            f.previous, (5, 13), settings_basis=basis), original_decision)
        for day in (dict(f.day, raw_non_nms=[{'fact': 'present'}]),
                    dict(f.day, raw_no_norm=[{'fact': 'present'}])):
            self.assertFalse(persistent_master.eligible(f.current, day, f.snapshot, f.previous,
                                                       (5, 13), settings_basis=basis))
        self.assertFalse(persistent_master.eligible(dict(f.current, import_non_nms=True), f.day,
            f.snapshot, f.previous, (5, 13), settings_basis=basis))
        self.assertFalse(persistent_master.eligible(f.current, f.day, dict(f.snapshot, nms_active=False),
            f.previous, (5, 13), settings_basis=basis))
        prior = {'consumer_context': {'NMSAllItems': [{'SKUCode': 'SKU', 'WhCode': 'LOC', 'Norm': None}]}}
        self.assertIsNone(persistent_master.select(prior, f.original, f.day, f.snapshot,
            f.previous, (5, 10)))
        self.assertIsNone(persistent_master.select(prior, f.current, f.day, f.snapshot,
            f.previous, (5, 13), settings_basis=basis))

    def test_basis_owner_rejects_stale_unqualified_or_foreign_profile(self):
        f = self.fixture()
        f.parent.production_manifest['master_preparation']['configuration_digest'] = '0' * 64
        self.assertIsNone(self.admitted_basis(f))
        f = self.fixture()
        f.revision.master_epoch = 6
        self.assertIsNone(self.admitted_basis(f))
        f = self.fixture()
        f.revision.partitions['base'] = {'root': 'different'}
        self.assertIsNone(self.admitted_basis(f))
        f = self.fixture()
        f.version.profile_digest = '0' * 64
        with self.assertRaisesRegex(ValueError, 'ownership/date/profile'):
            self.admitted_basis(f)
        f = self.fixture()
        f.version.effective_date = date(2026, 4, 10)
        f.reference = execution_settings.reference(f.version)
        with self.assertRaisesRegex(ValueError, 'ownership/date/profile'):
            self.admitted_basis(f)


if __name__ == '__main__':
    unittest.main()
