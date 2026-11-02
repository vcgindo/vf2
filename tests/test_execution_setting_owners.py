from dataclasses import replace
from decimal import Decimal
import unittest

from mta.row_sequences import RecordRows
from mta.runtime.execution_setting_values import SettingCell
from mta.runtime.execution_setting_owners import OWNER_PREFIX, describe, extract, validate


class NeverRead:
    def __iter__(self):
        raise AssertionError('Excluded population enumerated')

    def __len__(self):
        raise AssertionError('Excluded population length inspected')

    def __getitem__(self, key):
        raise AssertionError('Excluded population indexed')


class OutsideOwnerCatalogueTests(unittest.TestCase):
    def fixture(self):
        return dict(importer_settings=[
            dict(Parameter='IsBatchFileExecuted', Value='1'),
            dict(Parameter='NMSActive', Value='1'), dict(Parameter='NMSActive', Value='1'),
            dict(Parameter='TaskStatusLogHorizon', Value=' 7 '),
            dict(Parameter='UpdatePWh_RLT_RCP_GCP', Value='0')],
            controls=dict(importer_settings=[dict(Parameter='NMSActive', Value=1)],
                dbm_settings=[dict(Parameter='FNC_MatchMasterNorm', Value='0')]),
            dbm=dict(DBMSettingsTbl=[dict(Parameter='SpikeRuleHorizon', Value=''),
                                    dict(Parameter='SpikeRuleParCount', Value=None),
                                    dict(Parameter='NormZeroOneRuleActive', Value=False),
                                    dict(Parameter='DelistingofNormRuleActive', Value=Decimal('1.00'))],
                VFSettings=[dict(Parameter='SuperDelayFactor', Value='1.50', Description=None),
                            dict(Parameter='DBMDelistingDataPointPercent', Value='050', Description='閾値'),
                            dict(Parameter='IsMTOEnvironment', Value='0', Description='Part2')],
                FirstReplenishmentPercentageTbl=[dict(ReplenishmentPercentage=50)],
                DBMMaster=NeverRead(), DailyConsumption=NeverRead()),
            importer={'MasterData': NeverRead()}, complete={'ScriptExecutedFlag': NeverRead()})

    def test_preserves_occurrences_null_types_lexemes_and_full_fields(self):
        state = self.fixture()
        cells = extract(state)
        self.assertIs(type(cells), tuple)
        self.assertEqual(validate(cells), cells)
        nms = [cell for cell in cells if cell.parameter == 'NMSActive' and cell.path.endswith('/Value')]
        self.assertEqual([cell.ordinal for cell in nms], [1, 2, 0])
        self.assertEqual([(cell.value_kind, cell.value()) for cell in nms], [('text', '1'), ('text', '1'), ('int', 1)])
        values = {cell.parameter: cell for cell in cells if cell.path.endswith('/Value')}
        self.assertIsNone(values['SpikeRuleParCount'].value())
        self.assertIs(values['NormZeroOneRuleActive'].value(), False)
        self.assertEqual(values['DelistingofNormRuleActive'].value().as_tuple(), Decimal('1.00').as_tuple())
        self.assertEqual(values['TaskStatusLogHorizon'].value(), ' 7 ')
        self.assertEqual(values['DBMDelistingDataPointPercent'].value(), '050')
        self.assertEqual(len([cell for cell in cells if cell.parameter == 'SuperDelayFactor']), 3)
        self.assertTrue(all(cell.path.startswith(OWNER_PREFIX + '/') for cell in cells))

    def test_runtime_markers_seed_names_and_unrelated_owners_are_excluded(self):
        cells = extract(self.fixture())
        self.assertFalse({'IsBatchFileExecuted', 'UpdatePWh_RLT_RCP_GCP', 'IsMTOEnvironment'}
                         & {cell.parameter for cell in cells})
        self.assertEqual(extract({}), ())
        self.assertEqual(extract({'dbm': {}}), ())
        self.assertEqual(extract({'importer_settings': []}), ())

    def test_record_rows_are_iterated_once_and_shared(self):
        state = self.fixture()
        original = state['dbm']['VFSettings']
        expected = extract(state)
        visits = []
        def records():
            visits.append(True)
            yield from original
        rows = RecordRows(len(original), records,
                          getitem=lambda index: self.fail('No ordinal lookup needed'))
        state['dbm']['VFSettings'] = rows
        self.assertEqual(extract(state), expected)
        self.assertEqual(visits, [True])
        self.assertIs(state['dbm']['VFSettings'], rows)

    def test_present_malformed_sources_and_singleton_fail_without_defaults(self):
        for state in ({'controls': None}, {'dbm': []}, {'importer_settings': {}},
                      {'importer_settings': [{'Parameter': 'NMSActive'}]},
                      {'importer_settings': [{'Parameter': 'NMSActive', 'Value': {}, 'extra': 1}]},
                      {'importer_settings': [{'Parameter': 'NMSActive', 'Value': []}]},
                      {'dbm': {'VFSettings': [{'Parameter': 'SuperDelayFactor', 'Value': '1'}]}},
                      {'dbm': {'FirstReplenishmentPercentageTbl': []}},
                      {'dbm': {'FirstReplenishmentPercentageTbl': [{'ReplenishmentPercentage': 50}] * 2}}):
            with self.subTest(state=state), self.assertRaises((ValueError, TypeError)):
                extract(state)

    def test_namespace_parameter_path_ordinal_and_complete_row_are_strict(self):
        cells = extract({'importer_settings': [dict(Parameter='NMSActive', Value='1')]})
        bad_rows = [cells[:1], cells + cells[:1],
            (replace(cells[0], module='DBM/DBMSettingsTbl'),) + cells[1:],
            (replace(cells[0], path='/owners/unknown/0/Parameter'),) + cells[1:],
            (replace(cells[0], path='/owners/importer_settings/00/Parameter'),) + cells[1:],
            (replace(cells[0], ordinal=1),) + cells[1:],
            (replace(cells[0], parameter='DBMActive'),) + cells[1:],
            (replace(cells[0], value_text='DBMActive'),) + cells[1:],
            cells[:1] + (replace(cells[1], value_kind='absent', value_text=None, value_state='ABSENT'),),
            tuple(cell.as_dict() for cell in cells)]
        for row in bad_rows:
            with self.subTest(row=row), self.assertRaises(ValueError):
                validate(row)

    def test_singleton_percentage_keeps_null_and_scalar_tags_but_not_extra_occurrences(self):
        for value in (None, 50, '50.00', Decimal('50.00')):
            cells = extract({'dbm': {'FirstReplenishmentPercentageTbl': [{'ReplenishmentPercentage': value}]}})
            self.assertIs(type(cells[0].value()), type(value))
            with self.assertRaises(ValueError):
                validate([replace(cells[0], ordinal=1,
                    path='/owners/dbm/FirstReplenishmentPercentageTbl/1/ReplenishmentPercentage')])

    def test_description_is_locked_code_metadata_and_preserves_physical_table_identity(self):
        metadata = describe(self.fixture())
        self.assertTrue(all(row['mutable'] is False and row['activation'] == 'OWNER_TRANSITION_LOCKED'
                            and row['effect'] for row in metadata))
        factor = next(row for row in metadata if row['parameter'] == 'SuperDelayFactor')
        self.assertEqual(factor['source'], 'dbm/VFSettings')
        self.assertEqual(factor['table'], 'Importer/VFSettings')
        self.assertEqual(factor['module'], 'DBM/VFSettings')
        factor['mutable'] = True
        self.assertFalse(next(row for row in describe(self.fixture()) if row['parameter'] == 'SuperDelayFactor')['mutable'])


if __name__ == '__main__':
    unittest.main()
