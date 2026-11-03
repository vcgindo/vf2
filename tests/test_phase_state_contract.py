"""Implementation provenance cannot impersonate a supported logical contract."""
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from mta.runtime import phase_state, phase_state_contract as contract
from mta.runtime.phase_image_storage import FORMAT
from tests import phase_state_v1_reference as legacy
from tests.test_phase_state import MemoryImages, native_prepared
from mta.application.native_output_contracts import native_assignments


class PhaseContractTests(TestCase):
    def test_exact_legacy_bootstrap_and_new_recipe_keep_separate_provenance(self):
        self.assertEqual(legacy.recipe_digest(), contract.LEGACY_RECIPE)
        self.assertEqual(contract.logical_digest(), contract.LEGACY_LOGICAL)
        self.assertNotEqual(phase_state.recipe_digest(), contract.LEGACY_RECIPE)
        with native_assignments(True):
            prepared, _opening, _refs = native_prepared()
        memory = MemoryImages()
        original = legacy.encode(prepared, None, row_writer=memory.rows, export_writer=memory.export)
        accepted = deepcopy(original)
        current = phase_state.encode(prepared, None, row_writer=memory.rows, export_writer=memory.export)
        self.assertEqual(contract.effective(legacy.recipe_digest(), original),
                         contract.effective(phase_state.recipe_digest(), current))
        self.assertEqual(original, accepted)
        self.assertEqual(current['phase_contract'], contract.describe())
        self.assertEqual(current['storage_format'], FORMAT)

    def test_unknown_legacy_changed_semantics_unknown_format_and_false_identity_refuse(self):
        old = dict(schema='fresh-native-phase-state-v1')
        new = dict(old, phase_contract=contract.describe(), storage_format=FORMAT)
        snapshot = lambda code, manifest: SimpleNamespace(recipe_digest=code, manifest=manifest)
        self.assertFalse(contract.compatible(snapshot('f'*64, old)))
        self.assertFalse(contract.compatible(snapshot(contract.LEGACY_RECIPE, new)))
        self.assertFalse(contract.compatible(snapshot('c'*64, dict(new, storage_format='unknown'))))
        self.assertFalse(contract.compatible(snapshot('c'*64,
            dict(new, phase_contract=dict(schema=contract.SCHEMA, digest='b'*64)))))
        self.assertFalse(contract.compatible(snapshot('c'*64,
            dict(new, phase_contract=dict(new['phase_contract'], extra='not-admitted')))))
        with patch.object(contract, 'logical_digest', return_value='d'*64):
            self.assertFalse(contract.compatible(snapshot(contract.LEGACY_RECIPE, old)))
            self.assertFalse(contract.compatible(snapshot('c'*64, new)))

    def test_supported_storage_patch_records_its_actual_implementation(self):
        manifest = dict(schema='fresh-native-phase-state-v1',
                        phase_contract=contract.describe(), storage_format=FORMAT)
        for actual in ('1'*64, '2'*64):
            snapshot = SimpleNamespace(recipe_digest=actual, manifest=manifest)
            self.assertTrue(contract.compatible(snapshot))
            contract.require(snapshot)
            self.assertEqual(snapshot.recipe_digest, actual)

    def test_prior_v2_storage_remains_readable_without_relabeling(self):
        manifest=dict(schema='fresh-native-phase-state-v1',
                      phase_contract=contract.describe(),storage_format='fresh-phase-image-references-v2')
        before=deepcopy(manifest)
        snapshot=SimpleNamespace(recipe_digest='2'*64,manifest=manifest)
        self.assertTrue(contract.compatible(snapshot))
        self.assertEqual(manifest,before)
        self.assertEqual(FORMAT,'fresh-phase-image-references-v3')

    def test_inherited_reference_requires_v3_and_its_control_owner(self):
        path='phase/BPR/controls/suggestions_log'
        item=dict(image='phase/PRE_BPR/controls/suggestions_log',
                  storage_format='inherited-control-history-v1',run_id='child')
        manifest=dict(schema='fresh-native-phase-state-v1',phase='BPR',metadata={'identity':'child'},
                      phase_contract=contract.describe(),storage_format=FORMAT,images={path:item})
        accepted=lambda value:contract.compatible(SimpleNamespace(recipe_digest='3'*64,manifest=value))
        self.assertTrue(accepted(manifest))
        self.assertFalse(accepted(dict(manifest,storage_format='fresh-phase-image-references-v2')))
        legacy=dict(manifest);legacy.pop('phase_contract');legacy.pop('storage_format')
        self.assertFalse(contract.compatible(SimpleNamespace(recipe_digest=contract.LEGACY_RECIPE,manifest=legacy)))
        self.assertFalse(accepted(dict(manifest,images={'phase/BPR/dbm/SuggestionsLog':item})))
        self.assertFalse(accepted(dict(manifest,metadata={'identity':'different-child'})))
