"""Bounded publication custody tests; persisted PostgreSQL proof is separate."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date
import os
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'settings-publication-unit-only')
import django
django.setup()

from django.test import override_settings
from mta.presentation import native_publication, report_verification
from mta.runtime import capture_preparation, execution_settings, input_v3
from mta.runtime.input_storage import SCHEMA as V2
from mta.serialization import digest
from tests import test_report_verification as legacy_harness


def put_node(tree, path, node):
    current = tree
    keys = path.split('/')[1:]
    for key in keys[:-1]:
        children = current.setdefault('object', [])
        match = next((child for name, child in children if name == key), None)
        if match is None:
            match = {'object': []}
            children.append([key, match])
        current = match
    current.setdefault('object', []).append([keys[-1], node])


class SettingsPublicationReferenceTests(unittest.TestCase):
    def fixture(self):
        owner = NS(pk=uuid4(), input_digest='a' * 64, configuration_digest='c' * 64,
            source=NS(digest='source'), input_sha256='opening-input', opening_date=date(2026, 4, 8))
        owner_tree, run_tree = {'object': []}, {'object': []}
        images = {}
        for path in input_v3.PROFILE_POPULATION_PATHS:
            # These are physical image descriptors, not population payloads.
            # The guard authenticates metadata custody; row audit is separate.
            if path.endswith(('_codes', 'replenishment_exclusions')):
                node = {'scalars': path + '/values'}
            else:
                node = dict(shape_image=path + '/shape', records=path + '/values',
                    shapes=[['dict', [['SKUCode', ['value', ['SKUCode']]]]]], children=[])
            put_node(owner_tree, path, node)
            put_node(run_tree, path, {'owner_reference': path})
            images[path + '/values'] = dict(image=path + '/values', count=97097,
                digest='f' * 64, table='input/sku', fields=[])
        owner.input_payload = dict(schema=V2, content_digest=owner.input_digest,
                                   tree=owner_tree, images=images)
        owner.input_manifest_digest = digest(owner.input_payload)
        version = NS(pk=uuid4(), initialization_id=owner.pk, revision=2,
            effective_date=date(2026, 4, 9), values_digest='d' * 64, profile_digest='e' * 64)
        ref = execution_settings.reference(version)
        references = {path: dict(kind='INITIALIZATION', path=path, owner_id=str(owner.pk),
            manifest_digest=owner.input_manifest_digest, content_digest=owner.input_digest)
            for path in input_v3.PROFILE_POPULATION_PATHS}
        manifest = dict(schema=input_v3.V3, content_digest='b' * 64,
                        tree=run_tree, owner_references=references)
        run = NS(pk=uuid4(), input_payload=manifest, input_digest='b' * 64,
            input_manifest_digest=digest(manifest), business_date=date(2026, 4, 9),
            predecessor_id=None, production_manifest={}, kind='DAILY_CHAIN',
            status='SUCCEEDED', evidence_mode='production', output_digest='output', production_digest='production')
        body = dict(contract=capture_preparation.CONTRACT, initialization_id=str(owner.pk),
            configuration_digest=owner.configuration_digest, run_id=str(run.pk), execution_settings=ref)
        body['receipt_digest'] = digest(body)
        run.production_manifest['ingestion_preparation'] = body
        frozen = {'execution_settings': deepcopy(ref)}
        return NS(owner=owner, run=run, version=version, ref=ref, body=body, frozen=frozen)

    def guards(self, f, reader=None):
        stack = ExitStack()
        stack.enter_context(patch('mta.runtime.input_reader.read_execution_input',
                                 side_effect=reader if reader is not None else lambda run, **kwargs: f.frozen))
        stack.enter_context(patch('mta.runtime.execution_setting_models.ExecutionSettingsVersion.objects.get',
                                 return_value=f.version))
        for path in ('mta.runtime.execution_settings.resolve', 'mta.runtime.execution_settings._rows',
                     'mta.runtime.opening_storage.load_image', 'mta.runtime.relational_state.load_image',
                     'mta.runtime.accepted_input_read.read_accepted_input'):
            stack.enter_context(patch(path, side_effect=AssertionError('Unexpected hydration/current lookup: ' + path)))
        return stack

    def reseal_body(self, f):
        f.body['receipt_digest'] = digest({key: value for key, value in f.body.items() if key != 'receipt_digest'})

    def test_all_thirteen_direct_roots_admit_without_profile_or_population_hydration(self):
        f = self.fixture()
        calls = []
        def frozen_only(run, *, components):
            self.assertIs(run, f.run)
            self.assertEqual(components, ('execution_settings',))
            calls.append(components)
            return f.frozen
        with self.guards(f, frozen_only):
            self.assertTrue(report_verification.profile_reference(f.run, f.owner))
            self.assertTrue(report_verification._settings_profile_reference(f.run, f.run, f.owner))
        self.assertEqual(calls, [('execution_settings',)] * 2)

    def test_tampered_capture_raw_reference_root_and_manifests_are_denied(self):
        for mutation in ('body-receipt', 'raw-reference', 'wrong-initialization', 'wrong-root',
                         'missing-population', 'dangling-node', 'run-manifest', 'owner-manifest'):
            f = self.fixture()
            if mutation == 'body-receipt':
                f.body['configuration_digest'] = '0' * 64
            elif mutation == 'raw-reference':
                f.frozen['execution_settings']['revision'] = 99
            elif mutation == 'wrong-initialization':
                f.body['initialization_id'] = str(uuid4())
                self.reseal_body(f)
            elif mutation == 'wrong-root':
                f.body['configuration_digest'] = '0' * 64
                self.reseal_body(f)
            elif mutation == 'missing-population':
                f.run.input_payload['owner_references'].pop(input_v3.PROFILE_POPULATION_PATHS[0])
                f.run.input_manifest_digest = digest(f.run.input_payload)
            elif mutation == 'dangling-node':
                path = input_v3.PROFILE_POPULATION_PATHS[0]
                parent, leaf = path.rsplit('/', 1)
                node = input_v3._node_at(f.run.input_payload, parent)
                node['object'] = [[name, child] for name, child in node['object'] if name != leaf]
                f.run.input_manifest_digest = digest(f.run.input_payload)
            elif mutation == 'run-manifest':
                f.run.input_payload['changed'] = True
            else:
                f.owner.input_payload['changed'] = True
            with self.subTest(mutation=mutation), self.guards(f), self.assertRaises(ValueError):
                report_verification.profile_reference(f.run, f.owner)

    def test_each_present_population_requires_its_own_exact_reference(self):
        for path in input_v3.PROFILE_POPULATION_PATHS:
            f = self.fixture()
            f.run.input_payload['owner_references'].pop(path)
            f.run.input_manifest_digest = digest(f.run.input_payload)
            with self.subTest(path=path), self.guards(f), \
                 self.assertRaisesRegex(ValueError, 'population custody differs'):
                report_verification.profile_reference(f.run, f.owner)

    def test_foreign_or_future_immutable_header_is_denied_by_require_reference(self):
        for mutation in ('foreign', 'future'):
            f = self.fixture()
            if mutation == 'foreign':
                f.version.initialization_id = uuid4()
            else:
                f.version.effective_date = date(2026, 4, 10)
                f.ref = execution_settings.reference(f.version)
                f.body['execution_settings'] = f.ref
                f.frozen['execution_settings'] = deepcopy(f.ref)
                self.reseal_body(f)
            with self.subTest(mutation=mutation), self.guards(f), \
                 self.assertRaisesRegex(ValueError, 'ownership/date/profile'):
                report_verification.profile_reference(f.run, f.owner)

    def test_foreign_population_owner_and_nonphysical_opening_root_are_denied(self):
        for mutation in ('owner', 'physical'):
            f = self.fixture()
            path = input_v3.PROFILE_POPULATION_PATHS[0]
            if mutation == 'owner':
                f.run.input_payload['owner_references'][path]['owner_id'] = str(uuid4())
                f.run.input_manifest_digest = digest(f.run.input_payload)
            else:
                node = input_v3._node_at(f.owner.input_payload, path)
                node.clear()
                node['owner_reference'] = path
                f.owner.input_manifest_digest = digest(f.owner.input_payload)
                for ref in f.run.input_payload['owner_references'].values():
                    ref['manifest_digest'] = f.owner.input_manifest_digest
                f.run.input_manifest_digest = digest(f.run.input_payload)
            with self.subTest(mutation=mutation), self.guards(f), self.assertRaises(ValueError):
                report_verification.profile_reference(f.run, f.owner)

    def test_legacy_whole_profile_alias_is_still_strict_and_uses_no_settings_lookup(self):
        for tamper in (False, True):
            run, owner, ref = legacy_harness.ProfileReferenceTests().fixture()
            if tamper:
                ref['owner_id'] = str(uuid4())
                run.input_manifest_digest = digest(run.input_payload)
            with patch('mta.runtime.input_reader.read_execution_input', side_effect=AssertionError('hydrate')), \
                 patch('mta.runtime.execution_settings.require_reference', side_effect=AssertionError('new header')):
                if tamper:
                    with self.assertRaises(ValueError):
                        report_verification.profile_reference(run, owner)
                else:
                    self.assertTrue(report_verification.profile_reference(run, owner))

    @override_settings(VF_MTA_SYNTHETIC_ROSTER='')
    def test_terminal_native_identity_uses_root_binding_and_frozen_reference_guard(self):
        f = self.fixture()
        binding = dict(id=str(f.owner.pk), source_digest=f.owner.source.digest,
            input_sha256=f.owner.input_sha256, content_digest=f.owner.input_digest,
            configuration_digest=f.owner.configuration_digest)
        capture = NS(status='CONSUMED', source=NS(receipt={'schema': 'fresh-production-mdm-source-v1'}))
        def reader(run, *, components):
            self.assertIs(run, f.run)
            if components == ('execution_settings',):
                return f.frozen
            self.assertEqual(components, ('initialization_binding', 'lineage'))
            return {'initialization_binding': binding, 'lineage': {}}
        with self.guards(f, reader), \
             patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.select_related') as captures, \
             patch('mta.runtime.initialization_models.ProductionInitialization.objects.select_related') as owners, \
             patch('mta.presentation.daily_sources.receipt', return_value=NS(images_digest='images', recipe_digest='recipe')):
            captures.return_value.filter.return_value.first.return_value = capture
            owners.return_value.filter.return_value.first.return_value = f.owner
            identity = native_publication.identity(f.run)
        self.assertEqual(identity['initialization'], binding)
        self.assertEqual(identity['run_id'], str(f.run.pk))
        self.assertEqual(identity['sources_digest'], 'images')


if __name__ == '__main__':
    unittest.main()
