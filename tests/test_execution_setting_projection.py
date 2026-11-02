from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import gzip
import json
from pathlib import Path
import unittest

from mta.row_sequences import RecordRows, ReadOnlyRow
from mta.runtime.execution_setting_values import SettingCell
from mta.runtime.execution_setting_owners import extract
from mta.runtime.execution_setting_projection import expected_owner_rows, project_state


class NeverRead:
    def __iter__(self):
        raise AssertionError('Excluded population enumerated')
    def __len__(self):
        raise AssertionError('Excluded population measured')
    def __getitem__(self, key):
        raise AssertionError('Excluded population indexed')


class OwnerProjectionTests(unittest.TestCase):
    def fixture(self):
        state = dict(importer_settings=[dict(Parameter='NMSActive', Value='1'),
            dict(Parameter='UpdatePWh_RLT_RCP_GCP', Value='1'),
            dict(Parameter='NMSActive', Value='1'), dict(Parameter='TaskStatusLogHorizon', Value=' 7 ')],
            controls=dict(importer_settings=[]), dbm=dict(VFSettings=[
                dict(Parameter='SuperDelayFactor', Value=None, Description='exact'),
                dict(Parameter='SuperDelayFactor', Value=Decimal('1.00'), Description=None)]))
        return state, extract(state)

    def test_exact_central_rows_preserve_null_duplicate_types_and_share_large_owners(self):
        state, cells = self.fixture()
        large = NeverRead()
        state['dbm']['DBMMaster'] = large
        state['dbm']['DailyConsumption'] = large
        state['importer'] = {'MasterData': large}
        original_importer = state['importer']
        projected = project_state(state, cells)
        self.assertEqual(projected['importer_settings'], state['importer_settings'])
        self.assertIsNot(projected['importer_settings'], state['importer_settings'])
        self.assertIsNot(projected['importer_settings'][0], state['importer_settings'][0])
        self.assertIs(projected['importer_settings'][1], state['importer_settings'][1])
        self.assertIs(projected['importer'], original_importer)
        self.assertIs(projected['dbm']['DBMMaster'], large)
        self.assertIs(projected['dbm']['DailyConsumption'], large)
        self.assertEqual(projected['dbm']['VFSettings'][1]['Value'].as_tuple(), Decimal('1.00').as_tuple())
        self.assertIsNone(projected['dbm']['VFSettings'][0]['Value'])

    def test_runtime_rows_may_clear_shift_ordinals_and_mutate_without_reinsertion(self):
        state, cells = self.fixture()
        state['importer_settings'].pop(1)
        state['importer_settings'].insert(0, dict(Parameter='IsBatchFileExecuted', Value='1'))
        state['importer_settings'] = [row for row in state['importer_settings']
                                      if row['Parameter'] != 'TaskStatusLogHorizon']
        expected = deepcopy(state)
        result = project_state(state, cells)
        self.assertEqual(result, expected)
        self.assertFalse(any(row['Parameter'] == 'TaskStatusLogHorizon' for row in result['importer_settings']))

    def test_no_owner_cells_absent_and_empty_roots_remain_strict_noops(self):
        state, cells = self.fixture()
        sentinel = NeverRead()
        self.assertIs(project_state(sentinel, None), sentinel)
        self.assertIs(project_state(sentinel, ()), sentinel)
        profile_cell = SettingCell.from_value('/delivery/batch/AutoDBMActive', 'DBM', 'AutoDBMActive', 0, 1)
        self.assertIs(project_state(sentinel, (profile_cell,)), sentinel)
        for current in ({}, {'importer_settings': []}, {'dbm': {}}, {'dbm': {'VFSettings': []}}):
            self.assertIs(project_state(current, cells), current)
        other = {'controls': {'dbm_settings': [{'Parameter': 'SpikeRuleHorizon', 'Value': '9'}]}}
        self.assertIs(project_state(other, cells), other)  # No cross-owner alias.

    def test_fixed_source_conflicts_types_multiplicity_and_namespace_are_rejected(self):
        for mutation in ('value', 'type', 'duplicate', 'missing', 'field', 'foreign'):
            state, cells = self.fixture()
            if mutation == 'value':
                state['importer_settings'][0]['Value'] = '0'
            elif mutation == 'type':
                state['importer_settings'][0]['Value'] = 1
            elif mutation == 'duplicate':
                state['importer_settings'].append(dict(Parameter='NMSActive', Value='1'))
            elif mutation == 'missing':
                state['importer_settings'].pop(0)
            elif mutation == 'field':
                state['importer_settings'][0]['Description'] = 'extra'
            else:
                cells = (replace(cells[0], path='/owners/foreign/0/Parameter'),) + cells[1:]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                project_state(state, cells)

    def test_owner_sequence_cannot_be_sorted_or_deduplicated(self):
        state = {'dbm': {'DBMSettingsTbl': [dict(Parameter='SpikeRuleHorizon', Value='7'),
            dict(Parameter='NormZeroOneRuleActive', Value='1'), dict(Parameter='SpikeRuleHorizon', Value='7')]}}
        cells = extract(state)
        state['dbm']['DBMSettingsTbl'].sort(key=lambda row: row['Parameter'])
        with self.assertRaisesRegex(ValueError, 'occurrence sequence'):
            project_state(state, cells)

    def test_native_record_rows_and_readonly_rows_are_preserved_without_mutation(self):
        state, cells = self.fixture()
        rows = state['dbm']['VFSettings']
        state['dbm']['VFSettings'] = RecordRows(len(rows), lambda: iter(rows))
        original = state['dbm']['VFSettings']
        result = project_state(state, cells)
        self.assertIsInstance(result['dbm']['VFSettings'], RecordRows)
        self.assertIsInstance(result['dbm']['VFSettings'][0], ReadOnlyRow)
        self.assertEqual(result['dbm']['VFSettings'], rows)
        self.assertIs(state['dbm']['VFSettings'], original)

    def test_expected_rows_are_fresh_namespace_bound_and_ordinal_ordered(self):
        state, cells = self.fixture()
        rows = expected_owner_rows(reversed(cells))
        self.assertEqual([row['Parameter'] for row in rows[('importer_settings',)]],
                         ['NMSActive', 'NMSActive', 'TaskStatusLogHorizon'])
        self.assertNotIn(('controls', 'dbm_settings'), rows)
        rows[('importer_settings',)][0]['Value'] = 'changed'
        self.assertEqual(expected_owner_rows(cells)[('importer_settings',)][0]['Value'], '1')

    def test_actual_g_two_date_fixed_control_projection_is_exact_when_available(self):
        root = Path('D:/freshvcf-build/evidence/execution-settings-part1-20261102/tiny-g')
        header_path = root / 'P12-SETTINGS.json'
        if not header_path.is_file():
            self.skipTest('Retained G owner snapshot unavailable')
        header = json.loads(header_path.read_text(encoding='utf-8'))
        cells = tuple(SettingCell.from_dict({key: row[key] for key in
            ('path', 'module', 'parameter', 'ordinal', 'value_kind', 'value_text', 'value_state')})
            for row in header['rows'])
        self.assertEqual(sum(cell.path.startswith('/owners/') for cell in cells), 22)
        for day in ('2026-10-18', '2026-10-19'):
            with gzip.open(root / 'days' / (day + '-frames.json.gz'), 'rt', encoding='utf-8') as stream:
                state = json.load(stream)['ClosingState'][0]
            before = deepcopy(state)
            projected = project_state(state, cells)
            with self.subTest(day=day):
                self.assertEqual(projected, before)
                self.assertEqual(state, before)
                self.assertIs(projected['dbm']['DBMMaster'], state['dbm']['DBMMaster'])
                self.assertIs(projected['dbm']['DailyConsumption'], state['dbm']['DailyConsumption'])
                self.assertIs(projected['controls']['dbm_settings'], state['controls']['dbm_settings'])


if __name__ == '__main__':
    unittest.main()
