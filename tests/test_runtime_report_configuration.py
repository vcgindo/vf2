"""Configuration/placement qualification, not native query or file parity."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from mta.application import runtime_report_configuration as reports
from mta.serialization import digest

FIXTURE = Path(__file__).parent / 'fixtures/runtime_reports_retained_20261019.json'
PIN = '1f036745abadf0224d9778a8fabf3cc93ad632d106a61127973f08b2baa9af55'


def configuration():
    return dict(schema=reports.SCHEMA, RuntimeReports=json.loads(FIXTURE.read_bytes()),
                DownloadableUIReportSettings=[])


class RuntimeReportConfigurationTests(unittest.TestCase):
    def test_retained_native_rows_and_all_fields_are_preserved_without_adoption(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), PIN)
        original = configuration()
        checked = reports.configuration(original)
        self.assertEqual(digest(checked), digest(original))
        schema = json.loads((Path(__file__).parents[1] /
            'mta/config/initialization_storage_v1.json').read_text())
        native_fields = {name for name, kind in schema['tables']['complete/BPR/RuntimeReports']}
        self.assertEqual(set(checked['RuntimeReports'][0]), native_fields)
        checked['RuntimeReports'][0]['Query'] = 'changed copy'
        self.assertNotEqual(checked, original)
        self.assertEqual(original['RuntimeReports'][5]['FileName'], 'Spiker_Order_Dump')
        self.assertIsNone(original['RuntimeReports'][0]['TemplateName'])
        # This configuration cannot bypass the separate owned-TEST declaration.
        from mta.runtime.scope_runtime_reports import configuration as test_only
        with self.assertRaises(ValueError):
            test_only(original)

    def test_full_equals_both_split_placement_sequences_without_duplicate_stages(self):
        value = configuration()
        # Witness every placement, not only the two populated in the capture.
        for identity, placement in ((11, 'PostImporter'), (12, 'PostDBM'), (13, 'Final')):
            row = dict(value['RuntimeReports'][0], Id=identity, Placement=placement)
            value['RuntimeReports'].append(row)
        value['RuntimeReports'].reverse()
        full = reports.plan(value, 'Full')
        self.assertEqual([row['placement'] for row in full], list(reports.PLACEMENTS))
        self.assertEqual(full, reports.plan(value, 'UptoBPR') + reports.plan(value, 'PostBPR'))
        self.assertEqual(full, reports.plan(value, 'UptoDBM') + reports.plan(value, 'PostDBM'))
        self.assertEqual([[r['Id'] for r in stage['RuntimeReports']] for stage in full],
                         [[11], [7, 10], [12], [2, 3, 4, 5, 6, 8], [13]])
        self.assertEqual(reports.plan(value, 'PostBPR')[0]['placement'], 'PostDBM')
        self.assertEqual(reports.plan(value, 'PostDBM')[0]['placement'], 'PostBTR')
        for scope in ('', 'postbpr', None, [], True):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                reports.plan(value, scope)

    def test_active_selection_uses_sql_ci_and_space_padding_and_preserves_types(self):
        value = configuration()
        value['RuntimeReports'][0].update(Placement='postbtr ', Active=1)
        value['RuntimeReports'][1].update(Placement='unused-private-stage', Active=False)
        value['DownloadableUIReportSettings'] = [
            dict(ReportName='RRR', Active=1, GenerationScope='postbpr ', DestFolder='%ReportsDownloadLoc%'),
            dict(ReportName='Disabled', Active=None, GenerationScope=None, DestFolder=''),
        ]
        plan = reports.plan(value, 'Full')
        self.assertEqual([r['Id'] for r in plan[3]['RuntimeReports']], [2, 4, 5, 6, 8])
        self.assertIs(type(plan[3]['RuntimeReports'][0]['Active']), int)
        self.assertEqual(plan[1]['DownloadableUIReportSettings'], value['DownloadableUIReportSettings'][:1])
        self.assertEqual(plan[0]['DownloadableUIReportSettings'], [])
        self.assertEqual(value['RuntimeReports'][0]['Placement'], 'postbtr ')

    def test_generated_file_state_is_separate_but_complete_capture_identity_changes(self):
        before = configuration()
        after = deepcopy(before)
        after['RuntimeReports'][7]['LastGeneratedFileName'] = 'TotalReqReport_2026-10-26'
        self.assertNotEqual(digest(before), digest(after))
        self.assertEqual(reports.definition_digest(before), reports.definition_digest(after))
        self.assertNotEqual(reports.last_generated(before), reports.last_generated(after))
        for field, replacement in (('FileName', 'renamed'), ('Query', 'SELECT 1'),
                                   ('Placement', 'Final'), ('HeaderList', None)):
            changed = deepcopy(before)
            changed['RuntimeReports'][0][field] = replacement
            self.assertNotEqual(reports.definition_digest(before), reports.definition_digest(changed))

    def test_missing_configuration_is_not_empty_and_no_native_fields_are_defaulted(self):
        empty = dict(schema=reports.SCHEMA, RuntimeReports=[], DownloadableUIReportSettings=[])
        self.assertEqual(reports.configuration(empty), empty)
        self.assertEqual(len(reports.plan(empty, 'Full')), 5)
        for key in empty:
            value = dict(empty); del value[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                reports.configuration(value)
        for key in configuration()['RuntimeReports'][0]:
            value = configuration(); del value['RuntimeReports'][0][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                reports.configuration(value)

    def test_native_type_null_width_and_primary_key_failures_deny(self):
        for key, invalid in (
                ('Id', True), ('Id', 2**31), ('Active', 1.0), ('Compression', '1'),
                ('DeleteOldFile', None), ('ReportName', None), ('Query', None),
                ('ReportName', 'x' * 51), ('ReportName', '\U0001f600' * 26),
                ('DestFolder', 'x\0y'), ('Placement', 'Unknown'), ('Placement', '\u00e9')):
            value = configuration(); value['RuntimeReports'][0][key] = invalid
            with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                reports.configuration(value)
        value = configuration(); value['RuntimeReports'].append(deepcopy(value['RuntimeReports'][0]))
        with self.assertRaisesRegex(ValueError, 'Unique native'):
            reports.configuration(value)
        value = configuration()
        value['DownloadableUIReportSettings'] = [
            dict(ReportName=name, Active=False, GenerationScope=None, DestFolder='')
            for name in ('RRR', 'rrr ')]
        with self.assertRaisesRegex(ValueError, 'Unique qualified'):
            reports.configuration(value)
        value['DownloadableUIReportSettings'] = [
            dict(ReportName='RRR', Active=True, GenerationScope=None, DestFolder='')]
        with self.assertRaisesRegex(ValueError, 'placement'):
            reports.configuration(value)

    def test_exact_bytes_duplicate_keys_nonfinite_and_reference_tampering_deny(self):
        raw = json.dumps(configuration()).encode()
        checksum = hashlib.sha256(raw).hexdigest()
        reference = reports.decode(raw, checksum)
        self.assertEqual(reports.validate_reference(reference), reference)
        for changed in (raw + b' ', b' ' * (reports.LIMIT + 1), raw.decode()):
            with self.assertRaises(ValueError):
                reports.decode(changed, checksum)
        for changed in (raw[:-1] + b',"RuntimeReports":[]}', raw[:-1] + b',"invalid":NaN}'):
            with self.assertRaises(ValueError):
                reports.decode(changed, hashlib.sha256(changed).hexdigest())
        for field in ('configuration_digest', 'definition_digest'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                reports.validate_reference(dict(reference, **{field: 'f' * 64}))
        mutated = deepcopy(reference)
        mutated['configuration']['RuntimeReports'][0]['Query'] = 'SELECT changed'
        with self.assertRaisesRegex(ValueError, 'identity'):
            reports.validate_reference(mutated)
        for checksum in (True, 'F' * 64, 'short'):
            with self.assertRaises(ValueError):
                reports.decode(raw, checksum)

    def test_downloadable_settings_remain_independent_of_runtime_rows(self):
        value = dict(schema=reports.SCHEMA, RuntimeReports=[], DownloadableUIReportSettings=[
            dict(ReportName='RRR', Active=True, GenerationScope='PostBPR', DestFolder='%ReportsDownloadLoc%')])
        plan = reports.plan(value, 'UptoBPR')
        self.assertEqual(plan[1]['RuntimeReports'], [])
        self.assertEqual(plan[1]['DownloadableUIReportSettings'], value['DownloadableUIReportSettings'])
        plan[1]['DownloadableUIReportSettings'][0]['DestFolder'] = 'changed copy'
        self.assertEqual(value['DownloadableUIReportSettings'][0]['DestFolder'], '%ReportsDownloadLoc%')
