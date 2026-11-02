from dataclasses import replace
from decimal import Decimal
import csv
import json
from pathlib import Path
import unittest

from mta.runtime.execution_setting_catalogue import (
    AUTO_DBM_CELL_PATH, BATCH_KEYS, EXCLUSIONS, ROOTS, describe, extract, project,
)
from mta.runtime.execution_setting_values import SettingCell
from mta.row_sequences import RecordRows, ReadOnlyRow


class ProfileCatalogueTests(unittest.TestCase):
    def profile(self):
        return dict(import_non_nms=False,
            daily=dict(settings=[dict(Parameter='MissingDailyDataHandling', Value='1'),
                                 dict(Parameter='DBM_MissingDailyDataHandling', Value='')],
                       vf_settings=[dict(Parameter='GenerateBPRForMissingInventoryLoc', Value='0')],
                       shell_flags=dict(DistributorSystemActive=0, VendorSystemActive=0, VectorDMSActive=0),
                       module_sources={'do_not_visit': object()}, distributor_codes=['LOC']),
            calculation=dict(stock_configuration=dict(reservation_type=2, reservation_for_rationing_only=True),
                             allocation=dict(advance_stock_threshold_percent=Decimal('1.00')),
                             skus=tuple(range(100000)), policies=object()),
            force_flags=dict(from_ui=True, ignore_master_norm=False, nms_active=True),
            delivery=dict(site_code='日本語', batch=dict(AutoDBMActive=0, Norm1Increase_MultipleRLT=4),
                          controls=dict(from_ui=True, start_percent='66.67', history_horizon=90),
                          conditional_dbm=dict(importer_vf_settings=[
                              dict(Parameter='Norm1IncreaseCountThreshold', Value='2', Description='閾値'),
                              dict(Parameter='Norm1IncreaseCountThreshold', Value='2', Description='閾値')]),
                          btr_settings=dict(NormSuggestion_Upward='1,2,2', CaptureDispatchExecutionEfficiency=0)),
            complete_daily=dict(policy='generic-finalization-active-nms-v1', consumption_days=370, remark_days=90),
            complete_pick=dict(policy='canonical-tied-order-v1'), daily_publication=True,
            daily_publication_config=dict(bpr_remark_horizon=90),
            native_upload_audit=dict(horizon=90, timezone='Asia/Kolkata', client_folder=None),
            operational_sources='cohort2-operational-sources-v1')

    def changed(self, cells, path=AUTO_DBM_CELL_PATH, value=1):
        return tuple(SettingCell.from_value(cell.path, cell.module, cell.parameter, cell.ordinal, value)
                     if cell.path == path else cell for cell in cells)

    def test_adoption_is_lossless_and_does_not_copy_populations(self):
        profile = self.profile()
        cells = extract(profile)
        self.assertIs(type(cells), tuple)
        self.assertIs(project(profile, cells), profile)
        self.assertIs(project(profile, reversed(cells)), profile)
        self.assertTrue(all(type(cell) is SettingCell for cell in cells))
        null = next(cell for cell in cells if cell.path.endswith('/client_folder'))
        self.assertEqual(null.value_state, 'NULL')
        self.assertIsNone(null.value())
        decimal = next(cell for cell in cells if cell.parameter == 'advance_stock_threshold_percent')
        self.assertEqual(decimal.value().as_tuple(), Decimal('1.00').as_tuple())

    def test_auto_dbm_projects_one_genuine_path_and_shares_other_branches(self):
        profile = self.profile()
        effective = project(profile, self.changed(extract(profile)))
        self.assertEqual(effective['delivery']['batch']['AutoDBMActive'], 1)
        self.assertEqual(profile['delivery']['batch']['AutoDBMActive'], 0)
        self.assertIsNot(effective['delivery']['batch'], profile['delivery']['batch'])
        for key in ('daily', 'calculation', 'force_flags', 'complete_daily', 'native_upload_audit'):
            self.assertIs(effective[key], profile[key])
        self.assertIs(effective['delivery']['controls'], profile['delivery']['controls'])
        self.assertIs(effective['delivery']['conditional_dbm'], profile['delivery']['conditional_dbm'])

    def test_preserves_duplicate_bag_rows_fields_and_ordinals(self):
        profile = self.profile()
        cells = extract(profile)
        matching = [cell for cell in cells if cell.parameter == 'Norm1IncreaseCountThreshold']
        self.assertEqual(len(matching), 6)
        self.assertEqual({cell.ordinal for cell in matching}, {0, 1})
        self.assertEqual(len({cell.path for cell in matching}), 6)
        effective = project(profile, self.changed(cells))
        self.assertEqual(effective['delivery']['conditional_dbm'], profile['delivery']['conditional_dbm'])

    def test_native_record_rows_stream_once_without_population_copy(self):
        profile = self.profile()
        ordinary_cells = extract(profile)
        originals = profile['delivery']['conditional_dbm']['importer_vf_settings']
        traversals = []

        def records():
            traversals.append(True)
            yield from originals

        def no_ordinal_access(index):
            self.fail('Settings extraction must iterate rather than index a population')

        rows = RecordRows(len(originals), records, getitem=no_ordinal_access)
        profile['delivery']['conditional_dbm']['importer_vf_settings'] = rows
        self.assertEqual(extract(profile), ordinary_cells)
        self.assertEqual(len(traversals), 1)
        self.assertIsInstance(next(iter(rows)), ReadOnlyRow)
        effective = project(profile, self.changed(ordinary_cells))
        self.assertIs(effective['delivery']['conditional_dbm']['importer_vf_settings'], rows)

    def test_retained_native_profile_scalar_roster_when_available(self):
        # Read only the bounded manifest and its declared small setting bags.
        # Master/fact CSVs remain placeholders and are never loaded here.
        root = Path('D:/freshvcf-build/evidence/btr-copy64-integration-20261101/input/opening')
        manifest_path = root / 'opening-manifest.json'
        if not manifest_path.is_file():
            self.skipTest('Retained local native profile is unavailable')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        profile = manifest['template']['configuration']
        for definition in ROOTS:
            if not definition.bag:
                continue
            owner = profile
            for key in definition.path[:-1]:
                if key not in owner:
                    break
                owner = owner[key]
            else:
                key = definition.path[-1]
                if key not in owner:
                    continue
                filename = owner[key]['$csv']
                population = manifest['populations'][filename]
                self.assertTrue(all(column['kind'] == 'text' for column in population['columns']))
                with (root / filename).open(encoding='utf-8-sig', newline='') as stream:
                    owner[key] = list(csv.DictReader(stream))
                self.assertEqual(len(owner[key]), population['rows'])
        self.assertEqual(set(profile['delivery']['batch']), set(BATCH_KEYS))
        cells = extract(profile)
        self.assertIs(project(profile, cells), profile)
        self.assertEqual(project(profile, self.changed(cells))['delivery']['batch']['AutoDBMActive'], 1)

    def test_missing_optional_fields_are_not_defaulted(self):
        profile = {'delivery': {'batch': {'AutoDBMActive': 0}}}
        cells = extract(profile)
        self.assertEqual(len(cells), 1)
        self.assertEqual(project(profile, self.changed(cells)), {'delivery': {'batch': {'AutoDBMActive': 1}}})
        self.assertEqual(extract({}), ())

    def test_rejects_missing_duplicate_unknown_or_metadata_edited_cells(self):
        profile = self.profile()
        cells = extract(profile)
        for altered in (cells[:-1], cells + cells[:1], cells + (replace(cells[0], path='/unknown'),),
                        (replace(cells[0], module='other'),) + cells[1:],
                        (replace(cells[0], parameter='other'),) + cells[1:],
                        (replace(cells[0], ordinal=7),) + cells[1:],
                        tuple(cell.as_dict() for cell in cells)):
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                project(profile, altered)

    def test_all_other_controls_and_metadata_are_locked(self):
        profile = self.profile()
        cells = extract(profile)
        paths = ['/import_non_nms', '/force_flags/from_ui', '/delivery/controls/from_ui',
                 '/delivery/batch/Norm1Increase_MultipleRLT',
                 '/daily/settings/0/Parameter', '/delivery/conditional_dbm/importer_vf_settings/0/Description']
        for path in paths:
            with self.subTest(path=path), self.assertRaises(ValueError):
                project(profile, self.changed(cells, path, 'edited'))

    def test_auto_dbm_rejects_coercions_null_absent_and_outside_domain(self):
        profile = self.profile()
        cells = extract(profile)
        for value in (False, True, '1', 1.0, Decimal('1'), None, -1, 2):
            with self.subTest(value=value), self.assertRaises(ValueError):
                project(profile, self.changed(cells, value=value))
        altered = tuple(replace(cell, value_kind='absent', value_text=None, value_state='ABSENT')
                        if cell.path == AUTO_DBM_CELL_PATH else cell for cell in cells)
        with self.assertRaises(ValueError):
            project(profile, altered)

    def test_undeclared_fields_and_payloads_inside_catalogue_are_rejected(self):
        for profile in ({'delivery': {'batch': {'unreleased': 1}}},
                        {'daily': {'settings': [{'Parameter': 'x', 'Value': '1', 'extra': 1}]}},
                        {'delivery': {'batch': {'AutoDBMActive': []}}},
                        {'delivery': {'batch': {'AutoDBMActive': True}}},
                        {'daily': {'settings': {'Parameter': 'x', 'Value': '1'}}},
                        {'native_upload_audit': {'client_folder': object()}},
                        {'delivery': []}):
            with self.subTest(profile=profile), self.assertRaises((ValueError, TypeError)):
                extract(profile)

    def test_metadata_is_finite_release_owned_and_only_auto_dbm_mutable(self):
        profile = self.profile()
        metadata = describe(profile)
        self.assertEqual([row['path'] for row in metadata if row['mutable']], [AUTO_DBM_CELL_PATH])
        self.assertEqual(len(metadata), len(extract(profile)))
        self.assertTrue(EXCLUSIONS)
        metadata[0]['mutable'] = True
        self.assertFalse(describe(profile)[0]['mutable'])


if __name__ == '__main__':
    unittest.main()
