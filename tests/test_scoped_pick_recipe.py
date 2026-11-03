"""File recipe compatibility does not rewrite old custody or skip byte checks."""
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.runtime import scoped_pick_files as files
from mta.serialization import digest


class ScopedPickRecipeTests(unittest.TestCase):
    def test_known_old_formats_require_identical_formatter(self):
        self.assertEqual(files._formatter_digest(),files._LEGACY_FORMATTER)
        for recipe in files._LEGACY_RECIPES:
            self.assertTrue(files._compatible_recipe(recipe))
        self.assertTrue(files._compatible_recipe(files.recipe_digest()))
        self.assertFalse(files._compatible_recipe('a'*64))
        with patch.object(files,'_formatter_digest',return_value='b'*64):
            for recipe in files._LEGACY_RECIPES:
                self.assertFalse(files._compatible_recipe(recipe))

    def test_legacy_receipt_keeps_identity_and_checks_whole_bundle(self):
        phase=SimpleNamespace(pk='phase',digest='source',snapshot=SimpleNamespace(state_digest='snapshot'))
        receipt=SimpleNamespace(source_digest='source',recipe_digest=sorted(files._LEGACY_RECIPES)[0],
            directory='directory',files={'one':{'size':4,'sha256':'a'*64}})
        receipt.digest=digest(files._identity(phase,receipt.recipe_digest,receipt.directory,receipt.files))
        original=vars(receipt).copy()
        @contextmanager
        def directory(*args):yield 'opened'
        with patch.object(files,'_binding',return_value=(phase,'root')) as binding, \
                patch('mta.runtime.models.ScopePickFiles.objects') as objects, \
                patch.object(files,'_directory',side_effect=directory), \
                patch.object(files,'_files',return_value=receipt.files) as bundle:
            objects.filter.return_value.first.return_value=receipt
            self.assertIs(files.read('phase',expected_digest='source'),receipt)
            binding.assert_called_once_with('phase','source');bundle.assert_called_once_with('opened')
            self.assertEqual(vars(receipt),original)
            bundle.return_value={}
            with self.assertRaisesRegex(files.PickFilesUnavailable,'contents differ'):
                files.read('phase',expected_digest='source')
            bundle.return_value=receipt.files;receipt.digest='corrupt'
            with self.assertRaisesRegex(files.PickFilesUnavailable,'receipt differs'):
                files.read('phase',expected_digest='source')
