"""Finite source profile and actual old-reference write refusal, offline only."""
import unittest
from unittest.mock import patch
from django import conf


@unittest.skipUnless(conf.settings.configured, 'Offline Django settings required; no database used')
class LegacyScopeReadCompatibilityTests(unittest.TestCase):
    def test_exact_candidate_keeps_original_read_recipe_identities(self):
        from mta.presentation import legacy_scope_read_compatibility as profile
        from mta.presentation import runtime_report_view, scoped_view, scoped_selection
        profile.verify()
        self.assertEqual(runtime_report_view.recipe_digest(),
                         '31fee0cee1f8b9008fd969da3585537af75a0321bbb3f2664a2d4490e03eff38')
        self.assertEqual(scoped_view.recipe_digest(),
                         'c0cb3006571037d08bbee122ffc2db414363347cc5d6d63932bb060d468a97bd')
        self.assertEqual(scoped_selection.recipe_digest(),
                         '885c44e7e2c5c4788eaa861d5e41785b6e5ba619f69017f6f3f20a958146adad')
        self.assertEqual(scoped_selection.publication_recipe_digest(),
                         '2027c2fa7f1c192636249b928bbe19af0ecd0a98ddb464e7197df0b9c8bf2d1a')
        self.assertEqual(runtime_report_view.LEGACY_DEPENDENCIES['mta.presentation.scoped_dbm_view'],
                         '20eb399e4b0b3b7a0d9f150d0d032ca91bea026b920b85838aea90bf7101a9e0')

    def test_changed_adapter_and_unchanged_dependency_both_fail_closed(self):
        from mta.presentation import legacy_scope_read_compatibility as profile
        from mta.presentation.context import PublicationUnavailable
        with patch.dict(profile.ADAPTED_DEPENDENCIES, {'mta.presentation.scoped_dbm_view':'f'*64}):
            with self.assertRaises(PublicationUnavailable): profile.verify()
        actual = profile.inspect.getsource
        def changed(module):
            source = actual(module)
            return source + '\n# changed' if module.__name__ == 'mta.presentation.boroa_sql' else source
        with patch.object(profile.inspect,'getsource',side_effect=changed):
            with self.assertRaises(PublicationUnavailable): profile.verify()

    def test_old_reference_preparation_and_refresh_cannot_use_read_profile_to_write(self):
        from mta.presentation import runtime_report_view, scoped_view
        from mta.presentation.context import PublicationUnavailable
        from tests.test_scope_runtime_reports import reference
        with self.assertRaisesRegex(PublicationUnavailable,'legacy_scope_mutation_requires_original_build'):
            runtime_report_view.prepare.__wrapped__('unread-phase', expected_digest='a'*64,action_revision=0)
        with self.assertRaisesRegex(PublicationUnavailable,'legacy_scope_mutation_requires_original_build'):
            scoped_view._save_reference(None,None,None,None,None,
                reference(),'b'*64)


if __name__ == '__main__': unittest.main()
