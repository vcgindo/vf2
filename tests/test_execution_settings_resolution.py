"""Settings resolution is bounded; mutable profile seals remain exhaustive."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests.test_execution_settings_bindings import execution_settings as settings, UnreadablePopulation
from mta.runtime.execution_setting_catalogue import extract
from mta.runtime.execution_setting_values import rows_digest
from mta.serialization import digest


class ResolutionTests(unittest.TestCase):
    def fixture(self):
        original={'delivery':{'batch':{'AutoDBMActive':0}}}
        cells=extract(original)
        owner=SimpleNamespace(pk='owner',configuration_digest=digest(original))
        version=SimpleNamespace(pk='version',initialization_id='owner',revision=1,effective_date=None,
            values_digest=rows_digest(cells),profile_digest=digest(original))
        return original,cells,owner,version

    def test_one_statement_resolves_values_and_handoff_without_visiting_population(self):
        original,cells,owner,version=self.fixture()
        original['daily']={'module_sources':{'large':UnreadablePopulation()}}
        rows=[('version',1,None,version.values_digest,version.profile_digest,
               *(cell.as_dict()[key] for key in settings.CELL_FIELDS)) for cell in cells]
        cursor=Mock();cursor.fetchall.return_value=rows
        with patch.object(settings.connection,'cursor',return_value=nullcontext(cursor)):
            profile,ref,actual=settings.resolve(owner,original,date(2037,4,11),with_cells=True)
        cursor.execute.assert_called_once()
        self.assertEqual(actual,cells)
        self.assertEqual(ref,settings.reference(version))
        self.assertIs(profile['daily'],original['daily'])

    def test_supplied_exact_cells_need_no_second_values_query_and_tampering_fails(self):
        original,cells,owner,version=self.fixture()
        ref=settings.reference(version)
        with patch.object(settings,'frozen_cells',side_effect=AssertionError('No second values load')):
            self.assertEqual(settings.require_cells(owner,ref,date(2037,4,11),cells),cells)
            with self.assertRaisesRegex(ValueError,'cell set differs'):
                settings.require_cells(owner,dict(ref,values_digest='0'*64),date(2037,4,11),cells)
            with self.assertRaisesRegex(ValueError,'no owned version'):
                settings.require_cells(owner,None,date(2037,4,11),cells)

    def test_locked_snapshot_still_detects_nested_inplace_mutation(self):
        original,cells,owner,version=self.fixture()
        original['daily']={'module_sources':{'large':[{'value':None},{'value':0}]}}
        version.profile_digest=digest(original);ref=settings.reference(version)
        with patch('mta.runtime.execution_setting_models.ExecutionSettingsVersion.objects.get',return_value=version):
            settings.require_snapshot(owner,original,ref,date(2037,4,11))
            original['daily']['module_sources']['large'][0]['value']=False
            with self.assertRaisesRegex(ValueError,'profile differs'):
                settings.require_snapshot(owner,original,ref,date(2037,4,11))

    def test_compatible_projection_hashes_current_once_and_rejects_nonmanaged_changes(self):
        previous,cells,owner,version=self.fixture()
        current=deepcopy(previous);current['delivery']['batch']['AutoDBMActive']=1
        version.profile_digest=digest(current);ref=settings.reference(version)
        observed=[]
        def hashing(value):
            observed.append(value)
            return digest(value)
        with patch('mta.runtime.execution_setting_models.ExecutionSettingsVersion.objects.get',return_value=version), \
             patch.object(settings,'digest',side_effect=hashing):
            settings.compatible_profiles(owner,previous,current,ref,date(2037,4,11))
            self.assertEqual(sum(value is current for value in observed),1)
            previous['nonmanaged']=[None]
            with self.assertRaisesRegex(ValueError,'nonmanaged'):
                settings.compatible_profiles(owner,previous,current,ref,date(2037,4,11))

    def test_frozen_retry_never_selects_current_version(self):
        profile,cells,owner,version=self.fixture();ref=settings.reference(version)
        with patch('mta.runtime.models.CalculationRun.objects.get',return_value=object()), \
             patch('mta.runtime.input_reader.read_execution_input',return_value={'profile':profile,'execution_settings':ref}), \
             patch('mta.runtime.execution_setting_models.ExecutionSettingsVersion.objects.get',return_value=version), \
             patch.object(settings,'_rows',return_value=cells), \
             patch.object(settings,'resolve',side_effect=AssertionError('Active values selected')), \
             patch.object(settings,'resolve_header',side_effect=AssertionError('Active header selected')):
            result=settings.daily_frame(owner,{},date(2037,4,11),retry_capture_id='old-run')
        self.assertEqual(result,dict(profile=profile,execution_settings=ref,settings_cells=cells))


if __name__=='__main__':unittest.main()
