"""Focused source/identity contract; native transaction proof remains separate."""
from importlib import import_module
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'registered-read-action-component')
import django
django.setup()


class RegisteredReadActionCutTests(unittest.TestCase):
    def test_forward_guard_changes_only_the_two_distinct_revision_comparison(self):
        old = import_module('mta.runtime.migrations.0235_registered_scope_read_attachment')
        new = import_module('mta.runtime.migrations.0238_registered_read_action_cut')
        self.assertEqual(new.OLD, old.BODY)
        self.assertEqual(new.BODY.replace('BPR.action_revision<=H.action_revision',
                                         'BPR.action_revision=H.action_revision'), old.BODY)
        self.assertIn('mta.runtime_report_publication_source(BPR)', new.BODY)
        self.assertIn('mta.runtime_report_publication_source(Importer)', new.BODY)
        self.assertIn('P.action_revision<>H.action_revision', new.REVERSE)

    def test_read_and_selection_recipes_are_preserved_under_exact_profile(self):
        from mta.presentation import registered_read_compatibility as profile
        from mta.presentation import registered_report_view, scoped_selection
        self.assertEqual(registered_report_view.recipe_digest(), profile.RECIPE)
        self.assertEqual(scoped_selection.registered_recipe_digest(), profile.SELECTION_RECIPE)
        self.assertEqual(profile.RECIPE, '4a8e21999d14a0aae89b6c5850bb2db38b3a34cd0073a15c91c4d46dc7ed2f38')
        self.assertEqual(profile.SELECTION_RECIPE, 'b2a0a38bb20c045eefc00d22b6dc5fcab3bc4f01634dbbf00a03cf9462ca678b')

    def test_changed_adapter_dependency_and_forward_guard_are_rejected(self):
        from mta.presentation import registered_read_compatibility as profile
        from mta.presentation.context import PublicationUnavailable
        source = profile.inspect.getsource
        for name in ('mta.presentation.scoped_view', 'mta.presentation.registered_report_view',
                     'mta.presentation.scoped_action_writer', 'mta.presentation.boroa_sql',
                     'mta.runtime.migrations.0238_registered_read_action_cut'):
            def changed(module):
                text = source(module)
                return text + '\n# changed' if module.__name__ == name else text
            with self.subTest(name=name), patch.object(profile.inspect, 'getsource', side_effect=changed):
                with self.assertRaisesRegex(PublicationUnavailable, 'registered_read_profile_source_differs'):
                    profile.recipe()


if __name__ == '__main__':
    unittest.main()
