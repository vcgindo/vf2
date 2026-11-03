"""Real phase effects across storage codecs; not frozen-request qualification."""
from unittest.mock import patch

from tests.test_phase_contract_postgresql import PhaseContractPostgresTests
from tests.test_prepared_effects_postgresql import PreparedEffectsPostgresTests
from tests.test_calculation_effects_postgresql import CalculationEffectsPostgresTests


class PreparedContractEffectsTests(PreparedEffectsPostgresTests):
    setUp = PhaseContractPostgresTests.setUp


class CalculationContractEffectsTests(CalculationEffectsPostgresTests):
    setUp = PhaseContractPostgresTests.setUp

    def test_old_accepted_prepared_and_bpr_continue_with_new_dbm_without_resealing(self):
        from tests import phase_state_v1_reference as legacy
        from mta.runtime import phase_state
        from mta.runtime.models import DailyPhaseSnapshot
        from mta.temporal.day_phases import DbmDay

        current_save = phase_state.save
        originals = {}
        new = []

        def save(run, phase, sources, **kwargs):
            if isinstance(phase, DbmDay):
                result = current_save(run, phase, sources, **kwargs)
                new.append(result)
            else:
                result = legacy.save(run, phase, sources, **kwargs)
                originals[result.pk] = DailyPhaseSnapshot.objects.values().get(pk=result.pk)
            return result

        with patch.object(phase_state, 'save', side_effect=save):
            self.test_actual_bpr_then_restored_dbm_copies_keep_capture_unconsumed()

        self.assertEqual(len(originals), 2)
        self.assertEqual(len(new), 1)
        for key, value in originals.items():
            self.assertEqual(DailyPhaseSnapshot.objects.values().get(pk=key), value)
            self.assertEqual(value['recipe_digest'], phase_state.contract.LEGACY_RECIPE)
        self.assertNotEqual(new[0].recipe_digest, phase_state.contract.LEGACY_RECIPE)
