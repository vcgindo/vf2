"""Certified opening reads reuse admission; strict readers remain diagnostic."""
from contextlib import ExitStack
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4

from tests.test_accepted_input_read import Images
from mta.mdm import production_families as production
from mta.mdm.initialization_contract import CURRENT_LIST_PATHS
from mta.runtime import accepted_input_read, input_storage
from mta.runtime.opening_scope import opening_scope, certify_opening, immutable
from mta.serialization import digest


def owner():
    return SimpleNamespace(pk=uuid4(), source_id=1,
        source=SimpleNamespace(digest='source-fixture'), input_digest='input-fixture',
        input_manifest_digest='manifest-fixture', receipt_digest='receipt-fixture',
        configuration_digest='configuration-fixture', recipe_sha256='recipe-fixture',
        implementation_digest='implementation-fixture', input_sha256='file-fixture',
        opening_identity='opening-fixture', opening_date=date(2026, 4, 8))


def certify(value):
    return certify_opening(value, (str(value.pk), value.source.digest,
        value.configuration_digest, 'certificate', 'revision', 'receipt', 'root', 'binding'))


class CertifiedDailyFrameTests(TestCase):
    def test_inspection_parent_profile_is_strict_only_without_private_certification(self):
        from mta.runtime import production_daily
        initialized = owner()
        parent = SimpleNamespace(pk=uuid4(), business_date=date(2026, 4, 8),
            kind='DAILY_CHAIN', status='SUCCEEDED', output_digest='output-fixture',
            production_manifest={'version': 3}, mdm_input_capture=SimpleNamespace(
                source=initialized.source, status='CAPTURED'))
        binding = dict(id=str(initialized.pk), source_digest=initialized.source.digest,
            input_sha256=initialized.input_sha256, content_digest=initialized.input_digest,
            configuration_digest=initialized.configuration_digest)
        frame = {'profile': {'fixture': 'profile'}}
        for certified in (False, True):
            with self.subTest(certified=certified), opening_scope(), ExitStack() as stack:
                if certified:
                    certify(initialized)
                manager = MagicMock()
                manager.select_related.return_value.get.return_value = initialized
                stack.enter_context(patch('mta.runtime.models.ProductionInitialization.objects', manager))
                stack.enter_context(patch('mta.runtime.models.CalculationRun.objects.get', return_value=parent))
                stack.enter_context(patch.object(production_daily, '_inspection_frame', return_value=frame))
                for name in ('require_initialization', 'require_binding'):
                    stack.enter_context(patch.object(production, name))
                stack.enter_context(patch.object(production_daily, 'inspect_completed_request', return_value=True))
                stack.enter_context(patch('mta.runtime.production_preflight.daily', return_value='report'))
                stack.enter_context(patch('mta.runtime.accepted_state_read.read_accepted_daily',
                    return_value={'ClosingState': [{'fixture': 'closing'}]}))
                def read_parent(value, *, components):
                    if components == ('initialization_binding',):
                        return {'initialization_binding': binding}
                    if certified:
                        raise AssertionError('Certified parent profile reread')
                    return {'profile': frame['profile']}
                read = stack.enter_context(patch('mta.runtime.input_reader.read_execution_input', side_effect=read_parent))
                hashing = stack.enter_context(patch.object(production_daily, 'digest', wraps=digest))
                result = production_daily.inspect_execution(b'fixture', 'fixture',
                    initialization_id=initialized.pk, source_digest=initialized.source.digest,
                    configuration_digest=initialized.configuration_digest, pick_output_root='fixture',
                    predecessor_id=parent.pk)
                self.assertEqual(result[0], 'report')
                self.assertEqual(read.call_count, 1 if certified else 2)
                self.assertEqual(hashing.call_count, 0 if certified else 2)

    def strict_forbidden(self):
        stack = ExitStack()
        for path in ('mta.mdm.initialization.read_initialized_input',
                     'mta.runtime.input_storage.read_input',
                     'mta.runtime.opening_storage.load_image',
                     'mta.runtime.opening_storage.iter_image',
                     'mta.mdm.production_families.digest'):
            stack.enter_context(patch(path, side_effect=AssertionError(path)))
        return stack

    def test_certified_root_has_separate_cache_and_successor_reads_only_profile(self):
        initialized = owner()
        frame = {'profile': {'policy': ['fixture']}, 'opening': {'state': {}}}
        with opening_scope():
            certify(initialized)
            immutable(initialized, 'frame', lambda: {'strict': True})
            with self.strict_forbidden(), patch.object(accepted_input_read,
                    'read_accepted_input', return_value=frame) as read:
                self.assertIs(production.frame_for_daily(initialized, None), frame)
                self.assertIs(production.frame_for_daily(initialized, None), frame)
                read.assert_called_once_with(initialized, materialized_roots=(
                    *CURRENT_LIST_PATHS, 'input/profile', 'input/pair_exclusions'))
                read.reset_mock()
                self.assertEqual(production.frame_for_daily(initialized, object()), {
                    'profile': frame['profile'], 'opening': {'identity': 'opening-fixture',
                    'opening_date': '2026-04-08'}})
                read.assert_called_once_with(initialized, components=('profile',),
                    materialized_roots=('input/profile',))

    def test_no_handle_uses_strict_root_and_successor(self):
        initialized = owner()
        with patch.object(production, '_opening_input', return_value={'strict': True}) as read, \
                patch.object(accepted_input_read, 'read_accepted_input') as accepted:
            for predecessor in (None, object()):
                self.assertEqual(production.frame_for_daily(initialized, predecessor), {'strict': True})
            self.assertEqual(read.call_count, 2)
            accepted.assert_not_called()

    def test_foreign_or_wrong_metadata_handle_rejected_before_decode(self):
        initialized = owner()
        with opening_scope(), patch.object(accepted_input_read, 'read_accepted_input') as read:
            foreign = certify(owner())
            with self.assertRaisesRegex(ValueError, 'absent or stale'):
                production.certified_profile(initialized, foreign)
            certify_opening(initialized, ('wrong', initialized.source.digest,
                initialized.configuration_digest, 'a', 'b', 'c', 'd', 'e'))
            with self.assertRaisesRegex(ValueError, 'identity differs'):
                production.frame_for_daily(initialized, None)
            read.assert_not_called()

    def test_accepted_root_matches_diagnostic_values_order_duplicates_and_lists(self):
        initialized, images = owner(), Images()
        duplicate = {'Code': 'fixture', 'nullable': None, 'integer': 0,
                     'boolean': False, 'floating': 1.25, 'text': '1.230'}
        raw = {'profile': {'delivery': {'site_code': 'fixture'}, 'list': ['fixture', None]}, 'pair_exclusions': [None, 'fixture'],
            'opening': {'state': {'importer': {'MasterData': [duplicate, duplicate]},
                                  'orders': {'SpikeOrderData': [duplicate]}}}}
        initialized.input_payload = input_storage.save_input(initialized, raw, version=2,
            image_writer=images.write, table_selector=lambda fields, path, rows: 'fixture' if rows else None)
        initialized.input_manifest_digest = digest(initialized.input_payload)
        roots = (*CURRENT_LIST_PATHS, 'input/profile', 'input/pair_exclusions')
        expected = input_storage.read_input(initialized, image_reader=images.read, materialized_roots=roots)
        decode = accepted_input_read.read_accepted_input
        with opening_scope():
            certify(initialized)
            with self.strict_forbidden(), patch.object(accepted_input_read, 'read_accepted_input',
                    side_effect=lambda value, **kw: decode(value, _image_reader=images.read, **kw)):
                actual = production.frame_for_daily(initialized, None)
        self.assertEqual(actual, expected)
        self.assertIsInstance(actual['opening']['state']['importer']['MasterData'], list)
        self.assertEqual(len(actual['opening']['state']['importer']['MasterData']), 2)
        row = actual['opening']['state']['importer']['MasterData'][0]
        values = [row[key] for key in ('integer', 'boolean', 'floating', 'text')]
        self.assertEqual([type(value) for value in values], [int, bool, float, str])
        self.assertIsNone(actual['opening']['state']['importer']['MasterData'][0]['nullable'])
