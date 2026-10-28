"""Original-factory source/contract identity; no arbitrary run/database pins."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from mta.runtime import generic_capture_compatibility as compatible
from mta.serialization import digest


class GenericCaptureCompatibilityTests(unittest.TestCase):
    def value(self,scope):
        from mta.runtime.production_scope_policy import SCHEMA
        value=dict(schema='captured-schema',scope=scope,command_key='one-command',
            runtime_reports={'configuration_digest':'c'*64},report_hooks={'mode':'unchanged'},
            dispositions={'schema':SCHEMA},publication_recipe='p'*64)
        value['compatibility_digest']=digest(dict(request=dict(value),
            release=compatible.ORIGIN_RELEASE,phase_recipe='r'*64))
        expected=dict(value,compatibility_digest='new-release-digest')
        return value,expected

    def test_both_prefix_factories_retain_their_exact_original_digest(self):
        for scope in ('UptoBPR','UptoDBM'):
            value,expected=self.value(scope);before=deepcopy(value)
            compatible.require_factory(value,expected,'r'*64)
            self.assertEqual(value,before)
            for key in ('scope','command_key','runtime_reports','report_hooks','dispositions','publication_recipe'):
                changed=deepcopy(value);changed[key]='foreign'
                with self.subTest(scope=scope,key=key),self.assertRaises(ValueError):
                    compatible.require_factory(changed,expected,'r'*64)
            with self.assertRaises(ValueError):compatible.require_factory(value,expected,'changed-recipe')
            changed=dict(value,compatibility_digest='0'*64)
            with self.assertRaises(ValueError):compatible.require_factory(changed,expected,'r'*64)

    def test_full_and_unselected_client_policies_do_not_enter_this_profile(self):
        value,expected=self.value('Full')
        self.assertFalse(compatible.applicable(value))
        value['scope']='UptoBPR';value['dispositions']['schema']='legacy-client-policy'
        self.assertFalse(compatible.applicable(value))
        self.assertFalse(compatible.applicable(None))

    def test_reconstruction_authenticates_every_unchanged_file_and_roster(self):
        original={'producer.py':'p'*64,'guard.py':'g'*64}
        release=dict(compatible.ORIGIN_RELEASE,source_files_digest=digest(original))
        current={'producer.py':'p'*64,'guard.py':'corrected-guard','new-guard.py':'n'*64}
        with patch.object(compatible,'ORIGIN_RELEASE',release), \
                patch.object(compatible,'ORIGIN_OVERRIDES',{'guard.py':'g'*64}), \
                patch.object(compatible,'ADDED_FILES',{'new-guard.py'}):
            compatible.require_original_sources(current)
            for mutation in ('producer','extra','missing','missing_guard'):
                changed=dict(current)
                if mutation=='producer':changed['producer.py']='different'
                elif mutation=='extra':changed['unreviewed.py']='a'*64
                elif mutation=='missing':changed.pop('producer.py')
                else:changed.pop('guard.py')
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                    compatible.require_original_sources(changed)

    def test_original_profile_has_no_run_id_or_database_name_roster(self):
        self.assertEqual(set(compatible.ORIGIN_RELEASE),{'schema','source_commit','manifest_sha256',
            'source_files_digest','migrations_digest','implementation_sha256'})
        self.assertTrue(all(name.startswith(('mta/','release/')) for name in compatible.ORIGIN_OVERRIDES))
        self.assertNotIn('mta/temporal/chain.py',compatible.ORIGIN_OVERRIDES)
        self.assertNotIn('mta/temporal/day_phases.py',compatible.ORIGIN_OVERRIDES)

    def test_only_the_exact_source_qualified_publication_recipe_transfers(self):
        with patch('mta.runtime.retained_registered_execution_compatibility._recipe_sources') as qualified:
            self.assertEqual(compatible.production_publication_recipe(compatible.OBSERVED_PRODUCTION_PUBLICATION_RECIPE),
                compatible.ORIGINAL_PRODUCTION_PUBLICATION_RECIPE)
            qualified.assert_called_once_with()
            with self.assertRaises(ValueError):compatible.production_publication_recipe('unknown-recipe')
        with patch('mta.runtime.retained_registered_execution_compatibility._recipe_sources',side_effect=ValueError('source changed')):
            with self.assertRaises(ValueError):compatible.production_publication_recipe(compatible.OBSERVED_PRODUCTION_PUBLICATION_RECIPE)
