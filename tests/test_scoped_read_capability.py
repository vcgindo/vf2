"""Admit the original invoker aggregate without adding workflow authority."""
from copy import deepcopy
from importlib import import_module
import unittest
from mta.mdm import owned_namespace as owned


def revision_helper():
    sql = import_module('mta.runtime.migrations.0191_scoped_action_ownership').SQL
    return dict(name='mta.scope_action_revision(target uuid)',
        body=sql.split('AS $body$', 1)[1].split('$body$;', 1)[0], security_definer=False,
        returns='bigint', language=14, configuration=['search_path=pg_catalog, mta'])


def finite_helper():
    sql = import_module('mta.runtime.migrations.0163_finite_capture_admission').SQL
    return dict(name='mta.finite_capture_prefix_digest(leaf uuid)',
        body=sql.split('AS $$', 1)[1].split('$$;', 1)[0], security_definer=False,
        returns='text', configuration=['search_path=pg_catalog, mta', 'TimeZone=UTC', 'DateStyle=ISO, YMD'])


class ScopedReadCapabilityTests(unittest.TestCase):
    def test_absent_old_schema_and_original_finite_helper_preserve_baseline(self):
        before = owned._application_profile_digest()
        grants = deepcopy(owned.APPLICATION_GRANTS)
        self.assertEqual(owned.application_functions(dict(functions=[])), owned.APPLICATION_FUNCTIONS)
        finite = finite_helper()
        self.assertEqual(owned.application_functions(dict(functions=[finite])),
            owned.APPLICATION_FUNCTIONS | {finite['name']})
        self.assertEqual(owned.APPLICATION_GRANTS, grants)
        self.assertEqual(owned._application_profile_digest(), before)

    def test_exact_revision_and_both_helpers_add_only_read_execution(self):
        before = owned._application_profile_digest()
        revision = revision_helper(); finite = finite_helper()
        self.assertEqual(owned.application_functions(dict(functions=[revision])),
            owned.APPLICATION_FUNCTIONS | {revision['name']})
        self.assertEqual(owned.application_functions(dict(functions=[revision, finite])),
            owned.APPLICATION_FUNCTIONS | {revision['name'], finite['name']})
        self.assertEqual(owned._application_profile_digest(), before)

    def test_revision_body_language_definer_result_and_path_drift_deny(self):
        for changed in (dict(body='SELECT 0'), dict(security_definer=True), dict(returns='integer'),
                dict(language=12), dict(configuration=['search_path=public, mta'])):
            for finite in ([], [finite_helper()]):
                with self.subTest(changed=changed, finite=bool(finite)), self.assertRaisesRegex(
                        ValueError, 'Scoped revision read helper implementation differs'):
                    owned.application_functions(dict(functions=[dict(revision_helper(), **changed), *finite]))

    def test_original_finite_helper_validation_and_unlisted_helpers_remain_strict(self):
        with self.assertRaisesRegex(ValueError, 'Finite metadata helper implementation differs'):
            owned.application_functions(dict(functions=[dict(finite_helper(), body='SELECT 0'), revision_helper()]))
        workflow = dict(revision_helper(), name='mta.actionable_scope_phase(target uuid, accepted uuid)')
        self.assertEqual(owned.application_functions(dict(functions=[workflow])), owned.APPLICATION_FUNCTIONS)
