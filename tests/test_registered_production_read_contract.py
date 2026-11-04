"""Registered V1 custody survives a compatible production reader patch."""
from copy import deepcopy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
import django
django.setup()
from django.db.backends.base.base import BaseDatabaseWrapper
from mta.presentation import registered_report_view as view, scoped_selection, scoped_view
from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import read_request
from mta.serialization import digest
from tests.test_production_scope_policy import reference
from tests.test_runtime_report_request import fixture


def configuration(ref=None):
    ref = reference() if ref is None else ref
    return dict(schema=view.SCHEMA, configuration_digest=ref['configuration_digest'],
        reference=ref, registration_request={'owned': 'captured separately'},
        post_importer={'id': 'owned importer', 'digest': 'a' * 64},
        post_bpr={'id': 'owned BPR', 'digest': 'b' * 64})


class ProductionRegisteredReadContractTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(BaseDatabaseWrapper, 'connect',
            side_effect=AssertionError('Metadata unit proof must not connect')))

    def test_terminal_planning_reader_preserves_exact_prior_expedite_recipe(self):
        from mta.presentation import registered_read_compatibility as historical, scoped_expedite
        prior, current = historical.TERMINAL_PLANNING_EXPEDITE_READER
        self.assertEqual(scoped_expedite.recipe_digest(), current)
        accepts = historical.compatible_guard_recipe
        self.assertTrue(accepts('scoped_expedite', prior, current))
        self.assertFalse(accepts('scoped_expedite', prior, 'unknown-current'))
        self.assertFalse(accepts('scoped_expedite', 'unknown-prior', current))
        self.assertFalse(accepts('scoped_planning', prior, current))

    def test_production_v1_identity_is_not_a_whole_module_permission(self):
        from mta.presentation import registered_read_compatibility as historical
        config = configuration()
        self.assertEqual(view.recipe_digest(config),
            '4a8e21999d14a0aae89b6c5850bb2db38b3a34cd0073a15c91c4d46dc7ed2f38')
        self.assertEqual(scoped_selection.registered_recipe_digest(config),
            'b2a0a38bb20c045eefc00d22b6dc5fcab3bc4f01634dbbf00a03cf9462ca678b')
        with patch.object(historical, 'recipe', side_effect=AssertionError('Historical source profile')), \
                patch.object(scoped_selection, '_current_recipe_digest',
                    side_effect=AssertionError('Unrelated source is not an anchor format')), \
                read_request('/api/readyz'):
            for _ in range(2):
                self.assertEqual(view.recipe_digest(config), historical.RECIPE)
                self.assertEqual(scoped_view.recipe_for_configuration(config), historical.RECIPE)
                self.assertEqual(scoped_selection.registered_recipe_digest(config), historical.SELECTION_RECIPE)
            with patch.object(view, 'applicable_run', return_value=True), \
                    patch.object(view, 'configuration', return_value=(config, 'request')):
                self.assertEqual(scoped_selection.recipe_for_run('owned run'), historical.SELECTION_RECIPE)

    def test_closed_configuration_and_actual_production_policy_remain_required(self):
        valid = configuration()
        invalid = [dict(valid, extra=True), dict(valid, schema='unknown-v99'),
                   dict(valid, configuration_digest='f' * 64)]
        for key, value in [('purpose', 'unknown'), ('hook_json', '{}'),
                           ('disposition_json', '{}'), ('authority_sha256', 'bad')]:
            changed = deepcopy(valid); changed['reference'][key] = value; invalid.append(changed)
        for changed in invalid:
            with self.subTest(value=changed), self.assertRaises(PublicationUnavailable):
                view.recipe_digest(changed)
            with self.assertRaises(PublicationUnavailable):
                scoped_selection.registered_recipe_digest(changed)

    def test_guided_cache_identity_uses_the_admitted_reference_contract_and_permissions(self):
        from datetime import date
        from mta.presentation import scoped_guided, registered_read_compatibility as historical
        generation = SimpleNamespace(pk='generation', digest='generation digest')
        parent = SimpleNamespace(predecessor=SimpleNamespace(pk='own predecessor'))
        bpr = SimpleNamespace(read_identity={'owned': 'BPR'}, reports=SimpleNamespace(generation=generation))
        owned = SimpleNamespace(run=SimpleNamespace(pk='run', business_date=date(2026, 10, 19)),
            reference=SimpleNamespace(metadata={'runtime_reports': configuration()}),
            read_identity={'owned': 'reference'}, action_revision='revision', bpr=bpr)
        suggestions = SimpleNamespace(btr=parent, images=[], context=SimpleNamespace(dbm={'DBMMaster': []}))
        availability = SimpleNamespace(btr=parent, aggregate={}, receipt=SimpleNamespace(
            source_digest='source', schema_digest='schema', rows_digest='rows', row_count=1, reference_count=1))
        bound = scoped_guided.GuidedBinding(owned, suggestions, {}, availability, SimpleNamespace(history=[]))
        catalogue = {'products': {'records': [{'id': 1}]}, 'locations': {'records': [{'id': 2}]}}
        with patch.object(scoped_guided, 'permission_catalogue', return_value=catalogue), \
                patch.object(historical, 'recipe', side_effect=AssertionError('Historical alias')):
            value = bound.identity({'product_permissions': [1], 'location_permissions': [2]}, 'actor')
            self.assertEqual(value['recipe'], historical.RECIPE)
            self.assertEqual(value['action_revision'], 'revision')
            self.assertEqual(value['permissions']['location_permissions'], [2])
            with self.assertRaisesRegex(ValueError, 'invalid_permission'):
                bound.identity({'product_permissions': [True]}, 'actor')
            with self.assertRaisesRegex(PublicationUnavailable, 'permission_hierarchy'):
                bound.identity({'location_permissions': [3]}, 'actor')

    def test_historical_default_and_test_paths_keep_their_finite_profile(self):
        from mta.presentation import registered_read_compatibility as historical
        for config in (None, configuration(fixture())):
            with patch.object(historical, 'recipe', side_effect=PublicationUnavailable('finite historical profile')):
                with self.assertRaisesRegex(PublicationUnavailable, 'finite historical'):
                    view.recipe_digest(config)
                with self.assertRaisesRegex(PublicationUnavailable, 'finite historical'):
                    scoped_selection.registered_recipe_digest(config)

    def test_reference_binding_still_requires_captured_custody_and_original_seal(self):
        from mta.presentation import scoped_read_graph
        config = configuration()
        metadata = dict(runtime_reports=config, phase_digest='owned phase', transition=None)
        row = SimpleNamespace(metadata=metadata, digest=digest(metadata), recipe_digest=view.recipe_digest(config),
            report_generation=SimpleNamespace(run='owned run', phase='owned phase'),
            runtime_reports_digest=config['configuration_digest'], action_command=None, previous_reference=None)
        with patch.object(scoped_view, 'verify_guards') as guards, \
                patch.object(view, 'configuration', return_value=(config, 'request')) as captured, \
                patch.object(scoped_read_graph, 'bind', return_value=('bpr', 'planning', 'git', 'expedite')) as graph, \
                patch.object(scoped_view, '_files', return_value='files'), \
                patch.object(scoped_view, '_metadata', return_value=metadata):
            self.assertIs(view.bind(row, row.digest).reference, row)
            guards.assert_called_with(registered=True)
            graph.assert_called_with(row, retained_parent=False)
            captured.side_effect = PublicationUnavailable('foreign captured registration')
            with self.assertRaisesRegex(PublicationUnavailable, 'foreign captured'):
                view.bind(row, row.digest)
            captured.side_effect = None
            row.recipe_digest = 'f' * 64
            with self.assertRaisesRegex(PublicationUnavailable, 'identity_differs'):
                view.bind(row, row.digest)
            row.recipe_digest = view.recipe_digest(config)
            with self.assertRaisesRegex(PublicationUnavailable, 'identity_differs'):
                view.bind(row, 'f' * 64)
            row.runtime_reports_digest = 'f' * 64
            with self.assertRaisesRegex(PublicationUnavailable, 'dependencies_differ'):
                view.bind(row, row.digest)

    def test_component_and_live_cut_checks_are_not_bypassed_by_a_format_match(self):
        from mta.presentation import scoped_read_graph
        config = configuration(); metadata = dict(runtime_reports=config)
        row = SimpleNamespace(metadata=metadata, digest=digest(metadata), recipe_digest=view.recipe_digest(config),
            report_generation=SimpleNamespace(run='owned run'))
        with patch.object(scoped_view, 'verify_guards'), \
                patch.object(view, 'configuration', return_value=(config, 'request')), \
                patch.object(scoped_read_graph, 'bind',
                    side_effect=PublicationUnavailable('altered phase action or remark cut')):
            with self.assertRaisesRegex(PublicationUnavailable, 'altered phase'):
                view.bind(row, row.digest)
        with patch.object(scoped_view, 'verify_guards', side_effect=PublicationUnavailable('missing SQL guard')):
            with self.assertRaisesRegex(PublicationUnavailable, 'missing SQL guard'):
                view.bind(row, row.digest)
